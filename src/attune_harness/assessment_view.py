"""Read-only presentation of a completed assessment's recorded evidence."""

import html
import re


def _sections(task):
    request, run = task["request"], task["execution"]
    verification = run.get("verification", {})
    yield "Recorded outcomes", [
        ("Execution", task["status"], False),
        ("Document check verdict", verification.get("status", "Not recorded"), False),
        ("Semantic acceptance", "Unverified; participant judgments are not automatically adjudicated.", False),
        ("Scope", "Recorded checks cover supported document claims. This inspection does not rerun checks or establish current source freshness.", False),
    ]
    yield "Goal and criteria", [
        ("Goal", request["answers"]["goal"], False),
        ("Criteria", request["answers"]["criteria"], False),
    ]
    yield "Saved assessment", [
        ("Task", request["task_id"], True),
        ("Revision", request["revision"], True),
        ("Checkpoint", task["checkpoint_digest"], True),
        ("Record", task["record_path"], True),
    ]
    for name in ("document", "context"):
        source = request["evidence"][name]
        yield "Accepted " + name, [
            ("Path", source["path"], True),
            ("SHA-256", source["sha256"], True),
            ("Record pointer", "/request/evidence/" + name, True),
        ]
    claims = verification.get("result", {}).get("claims", [])
    if not claims:
        yield "Recorded document checks", [("Claims", "No individual claim checks recorded.", False)]
    for index, claim in enumerate(claims):
        yield "Document claim " + str(index + 1), [
            ("Kind", claim.get("kind", "Not recorded"), False),
            ("Subject", claim.get("subject", "Not recorded"), True),
            ("Verdict", claim.get("status", "Not recorded"), False),
            ("Location", claim.get("location") or "Not recorded", bool(claim.get("location"))),
            ("Evidence", claim.get("evidence", "Not recorded"),
             claim.get("kind") in ("links", "flags", "imports")),
            ("Detail", claim.get("detail") or "No additional detail recorded.", False),
            ("Record pointer", "/execution/verification/result/claims/" + str(index), True),
        ]
    retrieval = run.get("initial_retrieval", {})
    yield "Recorded retrieval", [
        ("Outcome", retrieval.get("status", "Not recorded"), False),
        ("Meaning", "Retrieved sources are references, not proof that a participant's judgment is correct.", False),
        ("Record pointer", "/execution/initial_retrieval", True),
    ]
    for index, source in enumerate(retrieval.get("sources", [])):
        rows = [("Record pointer", "/execution/initial_retrieval/sources/" + str(index), True)]
        for key in ("path", "repo_id", "revision", "sha256", "file_sha256",
                    "passage_id", "start_byte", "end_byte", "passage_sha256"):
            if key in source:
                rows.append((key, source[key], True))
        yield "Retrieved source " + str(index + 1), rows
    for role, participant in run.get("participants", {}).items():
        pointer = role.replace("~", "~0").replace("/", "~1")
        yield "Attributed participant judgment", [
            ("Role", role, True),
            ("Participant", participant["participant_id"], True),
            ("Judgment", participant.get("text", "No narrative recorded."),
             request.get("result_profile") == "assessment-findings-v1"),
            ("Trust", "Participant-authored content; findings and evidence references are not host-verified conclusions or execution permission.", False),
            ("Record pointer", "/execution/participants/" + pointer + "/text", True),
        ]


def _markdown(value, technical):
    text = str(value)
    if technical:
        width = max((len(v) for v in re.findall(r"`+", text)), default=0) + 1
        if "\n" not in text and text.strip():
            marker = "`" * width
            return marker + " " + text + " " + marker
        fence = "`" * max(3, width)
        return fence + "\n" + text + "\n" + fence
    # Escape each line as literal prose, including leading indentation that could
    # otherwise turn an answer into a code block. Preserve meaningful line breaks.
    lines = []
    for line in text.split("\n"):
        escaped = html.escape(line, quote=False)
        escaped = re.sub(r"([\\`*_{}\[\]()#+.!|~=$-])", r"\\\1", escaped)
        prefix = re.match(r"[ \t]*", escaped).group()
        escaped = "".join("&#32;" if c == " " else "&#9;" for c in prefix) + escaped[len(prefix):]
        lines.append(escaped)
    return "  \n".join(lines)


def render(task, format):
    """Use only the record returned by the existing inspection owner; never dispatch."""
    sections = list(_sections(task))
    if format == "markdown":
        lines = ["# Assessment evidence"]
        for title, rows in sections:
            lines.extend(["", "## " + title])
            for label, value, technical in rows:
                lines.extend(["", "**" + label + ":**", "", _markdown(value, technical)])
        return "\n".join(lines) + "\n"
    from .task_view import _document
    body = ['<header><p class="eyebrow">Attune Harness</p><h1>Assessment evidence</h1></header><article class="brief">']
    for title, rows in sections:
        body.append("<section><h2>" + html.escape(title) + "</h2><dl>")
        for label, value, technical in rows:
            text = html.escape(str(value))
            if technical:
                text = "<code>" + text + "</code>"
                if "\n" in str(value):
                    text = "<pre>" + text + "</pre>"
            else:
                text = text.replace("\n", "<br>")
            body.append("<dt>" + html.escape(label) + "</dt><dd>" + text + "</dd>")
        body.append("</dl></section>")
    body.append("</article>")
    return _document("".join(body), title="Assessment evidence") + "\n"
