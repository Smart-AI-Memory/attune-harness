"""Known-good offline proposal, not a model response or the scoring oracle."""

import csv
import io


def export_csv(rows, *, status, page, page_size, scope):
    selected = [row for row in rows if row["status"] == status]
    if scope == "current_page":
        start = (page - 1) * page_size
        selected = selected[start:start + page_size]
    elif scope != "all_matching":
        raise ValueError("Unknown export scope")
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(["id", "title", "status"])
    writer.writerows([row["id"], row["title"], row["status"]] for row in selected)
    return output.getvalue()
