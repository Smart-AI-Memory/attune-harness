"""New synthetic behaviors crossed with two preservation surfaces; no provider use."""

from textwrap import dedent

# These helpers perform useful work; the embedded variant increases unrelated
# behavior to preserve without padding the target or changing its required fix.
SURFACE = '''
import json
from functools import wraps

def audited(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        value = function(*args, **kwargs)
        return value
    return wrapped

@audited
def encode_record(record):
    return json.dumps(record, ensure_ascii=False, sort_keys=True) + "\\n"

def decode_records(text):
    records = []
    for line in text.splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records

async def emit_records(records, send):
    sent = 0
    for record in records:
        await send(encode_record(record))
        sent += 1
    return sent

class RecordBuffer:
    def __init__(self, limit):
        if limit < 1:
            raise ValueError("positive limit required")
        self.limit = limit
        self.rows = []

    def append(self, record):
        self.rows.append(dict(record))
        ready = len(self.rows) >= self.limit
        return ready

    def flush(self):
        rows, self.rows = self.rows, []
        return "".join(encode_record(row) for row in rows)
'''

FAMILIES = [
    {
        "id": "time-window", "symbol": "contains",
        "behavior": "For timezone-aware ISO timestamps, return whether the instant is in the half-open interval [start, end). Compare actual instants, including differing UTC offsets. Reject any naive timestamp with ValueError. An empty interval contains nothing.",
        "source": '''
from datetime import datetime
def contains(value, start, end):
    instant, lower, upper = [datetime.fromisoformat(item) for item in (value, start, end)]
    if any(item.utcoffset() is None for item in (instant, lower, upper)):
        raise ValueError("timezone required")
    return lower <= instant < upper
''',
        "before": "lower <= instant < upper", "after": "lower <= instant <= upper",
        "checks": [
            'self.assertFalse(subject.contains("2026-01-01T11:00:00+00:00", "2026-01-01T10:00:00+00:00", "2026-01-01T11:00:00+00:00"))',
            'self.assertTrue(subject.contains("2026-01-01T05:30:00-05:00", "2026-01-01T10:00:00+00:00", "2026-01-01T11:00:00+00:00"))',
            'self.assertTrue(subject.contains("2026-01-01T10:00:00+00:00", "2026-01-01T10:00:00+00:00", "2026-01-01T11:00:00+00:00"))',
            'with self.assertRaises(ValueError): subject.contains("2026-01-01T10:00:00", "2026-01-01T10:00:00+00:00", "2026-01-01T11:00:00+00:00")',
            'self.assertFalse(subject.contains("2026-01-01T10:00:00+00:00", "2026-01-01T10:00:00+00:00", "2026-01-01T10:00:00+00:00"))',
            'self.assertFalse(subject.contains("2026-01-01T09:59:59+00:00", "2026-01-01T10:00:00+00:00", "2026-01-01T11:00:00+00:00"))',
        ],
    },
    {
        "id": "explicit-false", "symbol": "resolve",
        "behavior": "Resolve a configuration key: use fallback only when the key is absent or its value is None. Preserve False, numeric zero, empty strings and empty containers, preserve object identity, and do not mutate settings.",
        "source": '''
def resolve(settings, key, fallback):
    value = settings.get(key)
    return fallback if value is None else value
''',
        "before": "value is None", "after": "not value",
        "checks": [
            'self.assertIs(subject.resolve({"enabled": False}, "enabled", True), False)',
            'self.assertEqual(subject.resolve({}, "n", 7), 7)',
            'self.assertEqual(subject.resolve({"n": None}, "n", 7), 7)',
            'self.assertEqual(subject.resolve({"n": 0}, "n", 7), 0)',
            'x = []; settings = {"x": x}; self.assertIs(subject.resolve(settings, "x", [1]), x); self.assertEqual(settings, {"x": []})',
            'self.assertEqual(subject.resolve({"x": ""}, "x", "default"), "")',
        ],
    },
    {
        "id": "csv-record", "symbol": "csv_record",
        "behavior": "Serialize one sequence of string fields as a CSV record using comma delimiter and standard doubled-quote escaping. Preserve embedded commas, quotes, Unicode and newlines. Terminate the record with exactly the writer's CRLF delimiter; do not change field contents or the input sequence.",
        "source": '''
import csv
import io
def csv_record(fields):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\\r\\n")
    writer.writerow(fields)
    return stream.getvalue()
''',
        "before": "writer.writerow(fields)", "after": 'stream.write(",".join(fields) + "\\r\\n")',
        "checks": [
            'self.assertEqual(subject.csv_record(["a,b", "c"]), \'"a,b",c\\r\\n\')',
            'self.assertEqual(subject.csv_record([\'a"b\']), \'"a""b"\\r\\n\')',
            'self.assertEqual(subject.csv_record(["é", "x"]), "é,x\\r\\n")',
            'self.assertEqual(subject.csv_record([]), "\\r\\n")',
            'self.assertEqual(subject.csv_record(["line\\nbreak"]), \'"line\\nbreak"\\r\\n\')',
            'x = ["a", "b"]; subject.csv_record(x); self.assertEqual(x, ["a", "b"])',
        ],
    },
    {
        "id": "terminal-suffix", "symbol": "strip_suffix",
        "behavior": "Remove exactly one terminal occurrence of suffix from text, only when suffix is nonempty and text ends with it. Preserve internal occurrences, Unicode, and text without a terminal match. Empty suffix must leave text unchanged.",
        "source": '''
def strip_suffix(text, suffix):
    if suffix and text.endswith(suffix):
        return text[:-len(suffix)]
    return text
''',
        "before": "return text[:-len(suffix)]", "after": 'return text.replace(suffix, "")',
        "checks": [
            'self.assertEqual(subject.strip_suffix("a.log.log", ".log"), "a.log")',
            'self.assertEqual(subject.strip_suffix("a.log", ""), "a.log")',
            'self.assertEqual(subject.strip_suffix("a.log.txt", ".log"), "a.log.txt")',
            'self.assertEqual(subject.strip_suffix("", "x"), "")',
            'self.assertEqual(subject.strip_suffix("éé", "é"), "é")',
            'self.assertEqual(subject.strip_suffix("ab", "abcd"), "ab")',
        ],
    },
]


def cases():
    for family in FAMILIES:
        source = dedent(family["source"]).lstrip()
        assert source.count(family["before"]) == 1
        for variant in ("isolated", "embedded"):
            correct = source + (SURFACE if variant == "embedded" else "")
            yield {**family, "id": family["id"] + "-" + variant,
                   "family": family["id"], "variant": variant,
                   "correct": correct,
                   "broken": correct.replace(family["before"], family["after"])}
