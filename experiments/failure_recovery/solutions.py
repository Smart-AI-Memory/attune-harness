"""Fixed offline proposal controls; never a model or competitor result."""

INITIAL = '''import csv
import io

def select_page(rows, *, status, page, page_size):
    matching = [row for row in rows if row["status"] == status]
    return matching[(page - 1) * page_size:page * page_size]

def export_csv(rows, *, status, page, page_size):
    return "id,title,status\\r\\n"
'''

GOOD = INITIAL[:INITIAL.index("def export_csv")] + '''def export_csv(rows, *, status, page, page_size):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["id", "title", "status"])
    for row in select_page(rows, status=status, page=page, page_size=page_size):
        writer.writerow([row["id"], row["title"], row["status"]])
    return output.getvalue()
'''

WRONG = GOOD.replace('row["title"], row["status"]', '"incorrect", row["status"]')
BLIND_SPOT = GOOD.replace('row["title"], row["status"]',
                          '(row["private_notes"] if status == "inactive" else row["title"]), row["status"]')

SUPPLEMENTAL = '''import csv
import io
from report import export_csv

def test_supplemental_current_page():
    rows = [{"id": "supplemental", "title": "New report", "status": "active", "private_notes": "SYNTHETIC-PRIVATE"}]
    actual = list(csv.reader(io.StringIO(export_csv(rows, status="active", page=1, page_size=2))))
    assert actual == [["id", "title", "status"], ["supplemental", "New report", "active"]], "feature: supplemental current page"
'''

VISIBLE = '''import csv
import io
import json
from pathlib import Path
from report import export_csv, select_page

ROWS = json.loads(Path("data/rows.json").read_text(encoding="utf-8"))

def test_baseline_filter_and_page():
    assert [r["id"] for r in select_page(ROWS, status="active", page=2, page_size=2)] == ["r4", "r5"]

def test_feature_current_page():
    actual = list(csv.reader(io.StringIO(export_csv(ROWS, status="active", page=1, page_size=2))))
    assert actual == [["id", "title", "status"], ["r1", "Alpha", "active"], ["r3", "Comma, title", "active"]], "feature: current page"

def test_feature_quoted_unicode():
    actual = list(csv.reader(io.StringIO(export_csv(ROWS, status="active", page=2, page_size=2))))
    assert actual == [["id", "title", "status"], ["r4", 'A "quote"', "active"], ["r5", "Café\\n第二行", "active"]], "feature: quoting and Unicode"

def test_empty_results():
    assert list(csv.reader(io.StringIO(export_csv(ROWS, status="missing", page=1, page_size=2)))) == [["id", "title", "status"]]
'''

ROWS = [
    {"id": "r1", "title": "Alpha", "status": "active", "private_notes": "SYNTHETIC-PRIVATE-1"},
    {"id": "r2", "title": "Filtered", "status": "inactive", "private_notes": "SYNTHETIC-PRIVATE-2"},
    {"id": "r3", "title": "Comma, title", "status": "active", "private_notes": "SYNTHETIC-PRIVATE-3"},
    {"id": "r4", "title": 'A "quote"', "status": "active", "private_notes": "SYNTHETIC-PRIVATE-4"},
    {"id": "r5", "title": "Café\n第二行", "status": "active", "private_notes": "SYNTHETIC-PRIVATE-5"},
    {"id": "r6", "title": "Last", "status": "active", "private_notes": "SYNTHETIC-PRIVATE-6"},
]
