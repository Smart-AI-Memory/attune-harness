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


class PageLinks(HTMLParser):
    """Read rendered links and anchors, including generated contents links."""

    def __init__(self, text: str):
        super().__init__()
        self.ids = set()
        self.links = []
        self.feed(text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Collect IDs and anchor targets from trusted generated HTML."""
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])


def validate_pages(rendered: dict[str, str]) -> None:
    """Refuse a build with a broken local route or heading fragment."""
    pages = {
        HELP_ROOT + (slug + "/" if slug else ""): PageLinks(text)
        for slug, text in rendered.items()
    }
    for path, page in pages.items():
        for href in page.links:
            target = urlsplit(urljoin("https://smartaimemory.com" + path, href))
            if target.netloc != "smartaimemory.com" or not target.path.startswith(
                HELP_ROOT
            ):
                continue
            if target.path == HELP_ROOT + "verification.json" and not target.fragment:
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
    slugs = [topic["slug"] for topic in topics]
    if len(slugs) != len(set(slugs)) or any(
        not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) for slug in slugs
    ):
        raise ValueError("Help topic slugs must be unique, simple path segments")
    template = Template((content / "template.html").read_text(encoding="utf-8"))
    sources = [
        content / name
        for name in ("manifest.json", "template.html", "help.css", "verification.json")
    ]
    pages = [
        (
            "",
            "Harness Help Center",
            "Choose a task and follow its setup, steps and expected result.",
            "overview.md",
        )
    ]
    pages.extend((t["slug"], t["title"], t["goal"], f'{t["slug"]}.md') for t in topics)
    rendered = {}
    for slug, title, goal, filename in pages:
        source = content / filename
        sources.append(source)
        renderer = markdown.Markdown(
            extensions=["fenced_code", "tables", "toc", "sane_lists"],
            extension_configs={"toc": {"toc_depth": "2-3", "permalink": True}},
        )
        body = renderer.convert(source.read_text(encoding="utf-8"))
        if not slug:
            cards = (
                '<div class="help-cards">'
                + "".join(
                    f'<section class="help-card"><p class="help-eyebrow">{html.escape(t["kind"])} · {html.escape(manifest["version"])}</p>'
                    f'<h2><a href="{HELP_ROOT}{t["slug"]}/">{html.escape(t["title"])}</a></h2>'
                    f'<p>{html.escape(t["goal"])}</p></section>'
                    for t in topics
                )
                + "</div>"
            )
            body = body.replace("<p>[TOPICS]</p>", cards)
        body = body.replace(
            "<table>",
            '<div class="help-table-scroll" tabindex="0" role="region" aria-label="Reference table, scroll horizontally if needed"><table>',
        )
        body = body.replace("</table>", "</table></div>")
        navigation = "".join(
            f'<li><a href="{HELP_ROOT}{t["slug"]}/"'
            + (' aria-current="page"' if t["slug"] == slug else "")
            + f'>{html.escape(t["title"])}</a></li>'
            for t in topics
        )
        rendered[slug] = template.substitute(
            title=html.escape(title),
            goal=html.escape(goal),
            version=html.escape(manifest["version"]),
            navigation=navigation,
            body=body,
            contents=f'<nav class="help-contents" aria-label="On this page"><h2>On this page</h2>{renderer.toc}</nav>',
            canonical=f'https://smartaimemory.com{HELP_ROOT}{slug + "/" if slug else ""}',
            breadcrumb=html.escape(title),
        )
    validate_pages(rendered)
    output.mkdir(parents=True, exist_ok=False)
    root = output / "harness" / "help"
    root.mkdir(parents=True)
    (root / "help.css").write_bytes((content / "help.css").read_bytes())
    (root / "verification.json").write_bytes(
        (content / "verification.json").read_bytes()
    )
    for slug, page in rendered.items():
        directory = root / slug
        directory.mkdir(exist_ok=True)
        (directory / "index.html").write_text(page, encoding="utf-8")
    record = {
        "version": manifest["version"],
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
