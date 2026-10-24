"""Build the release-pinned, static Harness Help Center without network access."""

import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from string import Template
from urllib.parse import unquote, urljoin, urlsplit

import markdown

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "help"
HELP_ROOT = "/harness/help/"
GOAL_ASSETS = (
    "intake-filled.jpg",
    "request-review.jpg",
    "state-check.json",
    "BRIEF.md",
    "CSV-CONTRACT-NOTES.md",
)
VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


class PageLinks(HTMLParser):
    """Read rendered links and anchors, including generated contents links."""

    def __init__(self, text: str):
        super().__init__()
        self.ids = set()
        self.links = []
        self.stack = []
        self.detail_owners = {}
        self.testing_owners = []
        self.feed(text)
        if self.stack:
            raise ValueError("Unclosed rendered HTML element")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Collect IDs and anchor targets from trusted generated HTML."""
        values = dict(attrs)
        owners = [identity for name, identity in self.stack if name == "details"]
        if values.get("id"):
            self.ids.add(values["id"])
            self.detail_owners[values["id"]] = owners
        if tag == "details" and "testing-goal" in (values.get("class") or "").split():
            self.testing_owners.append(owners)
        if tag in {"a", "link"} and values.get("href"):
            self.links.append(values["href"])
        if tag in {"img", "script"} and values.get("src"):
            self.links.append(values["src"])
        if tag not in VOID_TAGS:
            self.stack.append((tag, values.get("id")))

    def handle_endtag(self, tag: str) -> None:
        """Refuse malformed nesting before a browser can repair ownership."""
        if tag in VOID_TAGS:
            return
        if not self.stack or self.stack[-1][0] != tag:
            raise ValueError(f"Unbalanced rendered HTML element: {tag}")
        self.stack.pop()


class GoalGuide(PageLinks):
    """Validate the trusted HTML master before adding its local controls."""

    def __init__(self, text: str):
        self.targets = []
        self.counts = [0, 0]
        super().__init__(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag in {"script", "iframe", "form"}:
            raise ValueError(f"Executable or submitting goal element: {tag}")
        if any(
            name.startswith("on")
            or (value and value.strip().lower().startswith("javascript:"))
            for name, value in attrs
        ):
            raise ValueError("Executable goal attribute")
        if values.get("id") in self.ids:
            raise ValueError("Duplicate goal ID")
        if tag == "details":
            classes = (values.get("class") or "").split()
            self.counts[0] += "goal-item" in classes
            self.counts[1] += "testing-goal" in classes
        self.targets.extend(
            values[key] for key in ("data-copy", "data-status") if values.get(key)
        )
        super().handle_starttag(tag, attrs)


def render_goals(content: Path, manifest: dict) -> str:
    """Project the goals master, retaining its wording and historical captures."""
    body = (content / "goals/guide.html").read_text(encoding="utf-8")
    replacements = {
        "HARNESS_VERSION": manifest["version"],
        "HARNESS_SOURCE_REF": manifest["behavior_commit"],
        "RELEASE_SLUG": "1-5-1",
        "RELEASE_NOTICE": (
            "Published guidance."
            if manifest["status"] == "published"
            else f"Preparation only; this version is not yet released. Use published {manifest['published_version']} until publication."
        ),
    }
    for key, value in replacements.items():
        body = body.replace("{{" + key + "}}", html.escape(value))
    body = body.replace("/harness-help-assets/", HELP_ROOT + "assets/")
    if re.search(r"\{\{[A-Z_]+\}\}", body):
        raise ValueError("Unresolved goal placeholder")
    check = GoalGuide(body)
    check.targets.extend(href[1:] for href in check.links if href.startswith("#"))
    if set(check.targets) - check.ids or check.counts != [21, 6]:
        raise ValueError("Goal guide requires 21 goals, six FAQs and valid bindings")
    required = {
        "wording-choices",
        "spec-output",
        "output-details",
        "draft-status",
        "decision-summary",
        "choice-progress",
        "result-heading",
        "topic-status",
        "open-topics",
        "close-topics",
        "prepare-draft",
        "reset-choices",
        "download-draft",
    }
    if not required.issubset(check.ids):
        raise ValueError("Missing goal worksheet control")
    data = json.loads((content / "goals/data.json").read_text(encoding="utf-8"))
    if (
        not isinstance(data, dict)
        or not isinstance(data.get("proposals"), dict)
        or not isinstance(data.get("initial"), str)
        or any(
            not isinstance(data.get("proposals", {}).get(key, {}).get(field), str)
            for key in ("p1", "p2")
            for field in ("before", "after")
        )
    ):
        raise ValueError("Invalid goal worksheet data")
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    return (
        '<noscript><p class="help-callout">Open each topic to read its guidance. The local worksheet, copy and download controls require JavaScript; they record no approval.</p></noscript>'
        + body
        + f'<script type="application/json" id="goal-guide-data">{payload}</script>'
    )


def validate_pages(rendered: dict[str, str], resources: set[str] | None = None) -> None:
    """Refuse a build with a broken local route or heading fragment."""
    pages = {
        HELP_ROOT + (slug + "/" if slug else ""): PageLinks(text)
        for slug, text in rendered.items()
    }
    goals = pages.get(HELP_ROOT + "goals/")
    if goals and (
        any(
            "project-spec" not in goals.detail_owners.get(identity, [])
            for identity in (
                "compare",
                "review-copy",
                "output-details",
                "wording-choices",
                "spec-output",
            )
        )
        or len(goals.testing_owners) != 6
        or any("check-change" not in owners for owners in goals.testing_owners)
    ):
        raise ValueError("Goal section left its owning disclosure")
    for path, page in pages.items():
        for href in page.links:
            target = urlsplit(urljoin("https://smartaimemory.com" + path, href))
            if target.netloc != "smartaimemory.com" or not target.path.startswith(
                HELP_ROOT
            ):
                continue
            allowed = resources or {HELP_ROOT + "verification.json"}
            if target.path in allowed and not target.fragment:
                continue
            if target.path not in pages or (
                target.fragment
                and unquote(target.fragment) not in pages[target.path].ids
            ):
                raise ValueError(f"Broken Help Center link on {path}: {href}")


def build_site(output: Path, content: Path = CONTENT) -> dict:
    """Render trusted repository Markdown into a new, portable output directory."""
    output = output.expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise ValueError(
            "Choose a new output directory; existing evidence is not replaced"
        )
    if any(parent.is_symlink() for parent in output.parents):
        raise ValueError("Use a canonical output path without symlink parents")
    manifest = json.loads((content / "manifest.json").read_text(encoding="utf-8"))
    topics = manifest["topics"]
    current_topics = [topic for topic in topics if not topic.get("archived")]
    slugs = [topic["slug"] for topic in topics]
    if len(slugs) != len(set(slugs)) or any(
        not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) for slug in slugs
    ):
        raise ValueError("Help topic slugs must be unique, simple path segments")
    template = Template((content / "template.html").read_text(encoding="utf-8"))
    sources = [
        content / name
        for name in (
            "manifest.json",
            "template.html",
            "help.css",
            "verification.json",
            "preparation.json",
            "release-1.5.1.json",
        )
    ]
    pages = [
        (
            "",
            "Harness Help Center",
            "Choose a task and follow its setup, steps and expected result.",
            "overview.md",
        )
    ]
    pages.extend(
        (t["slug"], t["title"], t["goal"], t.get("source", f'{t["slug"]}.md'))
        for t in topics
    )
    assets = {f"assets/{name}": content / "assets" / name for name in GOAL_ASSETS}
    assets.update(
        {
            f"goals/{name}": content / "goals" / name
            for name in ("goals.css", "controls.js")
        }
    )
    sources.extend(assets.values())
    sources.extend(
        content / "goals" / name
        for name in ("data.json", "origin.json", "origin-release.json")
    )
    rendered = {}
    for slug, title, goal, filename in pages:
        source = content / filename
        if not source.resolve().is_relative_to(content.resolve()):
            raise ValueError("Help source leaves its content directory")
        sources.append(source)
        renderer = markdown.Markdown(
            extensions=["fenced_code", "tables", "toc", "sane_lists"],
            extension_configs={"toc": {"toc_depth": "2-3", "permalink": True}},
        )
        topic = next((t for t in topics if t["slug"] == slug), {})
        is_goals = slug == "goals"
        body = (
            render_goals(content, manifest)
            if is_goals
            else renderer.convert(source.read_text(encoding="utf-8"))
        )
        aliases = (
            manifest.get("overview_anchors", {})
            if not slug
            else next(t for t in topics if t["slug"] == slug).get("legacy_anchors", {})
        )
        for old, current in aliases.items():
            if not re.fullmatch(r"[a-z0-9-]+", old) or not re.fullmatch(
                r"[a-z0-9-]+", current
            ):
                raise ValueError("Invalid legacy heading alias")
            heading = re.search(r'<h[23] id="' + re.escape(current) + '"', body)
            if heading is None:
                raise ValueError(f"Missing target for legacy heading: {old}")
            body = (
                body[: heading.start()]
                + f'<span class="help-anchor" id="{old}" aria-hidden="true"></span>'
                + body[heading.start() :]
            )
        if not slug:
            cards = (
                '<div class="help-cards">'
                + "".join(
                    f'<section class="help-card"><p class="help-eyebrow">{html.escape(t["kind"])} · {html.escape(t.get("version", manifest["version"]))}</p>'
                    f'<h2><a href="{HELP_ROOT}{t["slug"]}/">{html.escape(t["title"])}</a></h2>'
                    f'<p>{html.escape(t["goal"])}</p></section>'
                    for t in current_topics
                )
                + "</div>"
            )
            body = body.replace("<p>[TOPICS]</p>", cards)
        if not is_goals:
            body = body.replace(
                "<table>",
                '<div class="help-table-scroll" tabindex="0" role="region" aria-label="Reference table, scroll horizontally if needed"><table>',
            )
            body = body.replace("</table>", "</table></div>")
        navigation = "".join(
            f'<li><a href="{HELP_ROOT}{t["slug"]}/"'
            + (' aria-current="page"' if t["slug"] == slug else "")
            + f'>{html.escape(t["title"])}</a></li>'
            for t in current_topics
        )
        version = topic.get("version", manifest["version"])
        published = topic.get("status", manifest["status"]) == "published"
        notice = (
            f"These instructions describe published <strong>Harness {html.escape(version)}</strong>. Check each walkthrough's verification limits."
            if published
            else f'Guidance target: <strong>Harness {html.escape(version)}</strong> preparation. Unpublished; use published {html.escape(manifest["published_version"])} until release.'
        )
        if topic.get("archived"):
            original = (
                f"published <strong>Harness {html.escape(version)}</strong>"
                if published
                else f"Harness {html.escape(version)} preparation before publication"
            )
            notice = (
                f"Archived guide: these instructions describe {original}. "
                "Keep their original evidence limits. "
                '<a href="/harness/help/archive/">Browse the archive</a> or '
                '<a href="/harness/help/1-5-1/">use current 1.5.1 guidance</a>.'
            )
        rendered[slug] = template.substitute(
            title=html.escape(title),
            goal=html.escape(goal),
            site_version=html.escape(manifest["version"]),
            site_notice=(
                "Published release."
                if manifest["status"] == "published"
                else "Preparation; publication pending."
            ),
            robots=(
                "index,follow"
                if published and not topic.get("archived")
                else "noindex,follow"
            ),
            navigation=navigation,
            body=body,
            page_intro=(
                ""
                if is_goals
                else f'<nav aria-label="Breadcrumb" class="help-breadcrumb"><a href="/harness/help/">Help Center</a> / <span aria-current="page">{html.escape(title)}</span></nav><p class="help-eyebrow">Attune Harness · {html.escape(version)}</p><h1>{html.escape(title)}</h1><p class="help-lead">{html.escape(goal)}</p><p class="help-version-note">{notice}</p>'
            ),
            contents=(
                ""
                if is_goals
                else f'<nav class="help-contents" aria-label="On this page"><h2>On this page</h2>{renderer.toc}</nav>'
            ),
            head=(
                '<link rel="stylesheet" href="/harness/help/goals/goals.css">'
                if is_goals
                else ""
            ),
            scripts=(
                '<script type="module" src="/harness/help/goals/controls.js"></script>'
                if is_goals
                else ""
            ),
            canonical=f'https://smartaimemory.com{HELP_ROOT}{slug + "/" if slug else ""}',
            breadcrumb=html.escape(title),
        )
    for source in sources:
        if not source.is_file() or not source.resolve().is_relative_to(
            content.resolve()
        ):
            raise ValueError("Unavailable or nonlocal Help source asset")
    validate_pages(
        rendered,
        {
            HELP_ROOT + name
            for name in (
                *assets,
                "help.css",
                "verification.json",
                "preparation.json",
                "release-1.5.1.json",
            )
        },
    )
    output.mkdir(parents=True, exist_ok=False)
    root = output / "harness" / "help"
    root.mkdir(parents=True)
    (root / "help.css").write_bytes((content / "help.css").read_bytes())
    (root / "verification.json").write_bytes(
        (content / "verification.json").read_bytes()
    )
    (root / "preparation.json").write_bytes((content / "preparation.json").read_bytes())
    (root / "release-1.5.1.json").write_bytes(
        (content / "release-1.5.1.json").read_bytes()
    )
    for name, source in assets.items():
        target = root / name
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(source.read_bytes())
    for slug, page in rendered.items():
        directory = root / slug
        directory.mkdir(exist_ok=True)
        (directory / "index.html").write_text(page, encoding="utf-8")
    record = {
        "version": manifest["version"],
        "status": manifest["status"],
        "published_version": manifest["published_version"],
        "behavior_commit": manifest["behavior_commit"],
        "source_repository": "Smart-AI-Memory/attune-harness",
        "pages": len(rendered),
        "renderer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "sources": {
            p.relative_to(content)
            .as_posix(): hashlib.sha256(p.read_bytes())
            .hexdigest()
            for p in sources
        },
    }
    record["files"] = {
        path.relative_to(output)
        .as_posix(): hashlib.sha256(path.read_bytes())
        .hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }
    (root / "build.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    return record


def main() -> None:
    """Render a fresh build whose output can be served by any static host."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build_site(args.output), indent=2))


if __name__ == "__main__":
    main()
