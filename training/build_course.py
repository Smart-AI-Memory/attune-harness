"""Project the six maintained lesson JSON files into local HTML and presenter text."""

import argparse
import hashlib
from html import escape
import json
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent
COURSE = ROOT / "1.7.0-preparation"
SLUGS = ("01-define", "02-build", "03-return", "04-review", "05-deliver", "06-improve")


def project():
    lessons = [json.loads((COURSE / slug / "lesson.json").read_text(encoding="utf-8"))
               for slug in SLUGS]
    titles = [lesson["title"] for lesson in lessons]
    shell = (ROOT / "lesson-template.html").read_text(encoding="utf-8")
    outputs = {}
    for position, (slug, lesson) in enumerate(zip(SLUGS, lessons), 1):
        sections = lesson["sections"]
        if [s["id"] for s in sections] != [f"section-{i}" for i in range(1, len(sections) + 1)]:
            raise ValueError(f"{slug}: section IDs must be unique and ordered")
        if not sections or any(not s.get(k) for s in sections
                               for k in ("title", "intro", "html", "navTitle", "phase")):
            raise ValueError(f"{slug}: empty lesson content")
        lesson.update(coursePosition=position, coursePath=titles,
                      courseRoutes=[f"../{name}/" for name in SLUGS])
        for section in sections:
            section["html"] = section["html"].replace("../../README.md", "../setup.html")
        outputs[COURSE / slug / "lesson.json"] = json.dumps(lesson, ensure_ascii=False, indent=2) + "\n"
        outputs[COURSE / slug / "index.html"] = shell
        readable = [f'<h1>{escape(lesson["title"])}</h1>',
                    '<p>Harness 1.7.0 preparation · current course · November 5, 2026</p>',
                    f'<p>{escape(lesson["subtitle"])}</p>',
                    '<p>This full-text reading copy does not save answers. '
                    '<a href="./">Open the interactive lesson</a> for saved browser notes.</p>']
        notes = [f'# Presenter notes: {lesson["title"]}', '',
                 'Current 1.7.0 preparation. Derived from this lesson’s JSON.', '']
        for section in sections:
            reading_body = re.sub(
                r'<label\b[^>]*>(.*?)</label>\s*<textarea\b[^>]*>.*?</textarea>',
                r'<h3>\1</h3><p>Write your answer in your own notes, or use the interactive lesson.</p>',
                section["html"], flags=re.DOTALL,
            ).replace('These notes stay in this browser.',
                      'In the interactive lesson, these notes stay in your browser.')
            readable.extend([f'<section id="{section["id"]}">',
                             f'<h2>{escape(section["title"])}</h2>',
                             f'<p>{escape(section["intro"])}</p>', reading_body])
            for copy in section.get("copies", []):
                readable.append(f'<h3>{escape(copy["label"])}</h3><pre><code>{escape(copy["text"])}</code></pre>')
            if section.get("check"):
                check = section["check"]
                readable.append(f'<details><summary>{escape(check["question"])}</summary>')
                for option in check["options"]:
                    readable.append(f'<p><strong>{escape(option["text"])}</strong> {escape(option["feedback"])}</p>')
                readable.append('</details>')
            readable.append('</section>')
            notes += [f'## {section["id"]}: {section["title"]}', '', section["intro"], '']
            notes += [f'- {note}' for note in section.get("presenterNotes", [])] + ['']
        outputs[COURSE / slug / "read.html"] = page(lesson["title"], '\n'.join(readable), '../assets/styles.css', '../')
        outputs[COURSE / slug / "presenter.md"] = '\n'.join(notes).rstrip() + '\n'
    cards = ['<h1>Harness in practice</h1>',
             '<p>Learn to direct a useful reporting project, inspect its results and choose the next step.</p>',
             '<section class="starting-paths" aria-labelledby="starting-paths-title">',
             '<h2 id="starting-paths-title">Choose how to start</h2>',
             '<div class="development-path-grid">',
             '<a class="development-path" href="development-paths.html#goal-driven">'
             '<h3>Goal-driven development</h3>'
             '<p>Start with a clear result. Define its scope and checks before building.</p>'
             '<span class="path-action">Explore the approach <span aria-hidden="true">→</span></span></a>',
             '<a class="development-path" href="development-paths.html#spec-driven">'
             '<h3>Spec-driven development</h3>'
             '<p>Develop requirements, dependencies and acceptance examples before implementation.</p>'
             '<span class="path-action">Explore the approach <span aria-hidden="true">→</span></span></a>',
             '</div><p class="path-comparison"><a href="development-paths.html">'
             'Compare the paths and their review points</a></p></section>',
             '<p>Harness 1.7.0 preparation · November 5, 2026. Use the separate reviewed-wheel setup before command practice.</p>',
             '<p><a href="setup.html">Get ready for the course</a> · <a href="assets/current-checks.json">Current software checks</a></p>',
             '<h2>Follow the learning path</h2>', '<ol>']
    for slug, lesson in zip(SLUGS, lessons):
        cards.append(f'<li><h2><a href="{slug}/">{escape(lesson["title"])}</a></h2><p>{escape(lesson["subtitle"])}</p></li>')
    cards += ['</ol>', '<p>Reading progress and notes stay in your browser. Lesson controls do not run commands or approve Harness work.</p>',
              '<p><a href="../archive/">Historical documents</a></p>']
    style_revision = hashlib.sha256((COURSE / "assets/styles.css").read_bytes()).hexdigest()[:12]
    outputs[COURSE / "index.html"] = page(
        'Harness in practice', '\n'.join(cards), f'assets/styles.css?v={style_revision}', None,
    )
    outputs[ROOT / "archive/index.html"] = page(
        'Historical training documents',
        '<h1>Historical training documents</h1>'
        '<p>These superseded documents preserve earlier instructions and evidence. '
        'Use the <a href="../1.7.0-preparation/">current course</a> for current practice.</p>'
        '<h2>Build your first report</h2>'
        '<p><a href="build-your-first-report-1.5.1-r5.zip">Download the original HTML lesson</a>. '
        'Harness 1.5.1, revision r5 with the folder-step correction, October 29, 2026.</p>'
        '<h2>Your first task with Harness</h2>'
        '<p>Retained planning records identify the original r2 lesson. Its original '
        'HTML/package was not recovered; the current definition lesson is newly authored.</p>'
        '<h2>Come back tomorrow</h2>'
        '<p>The earlier addition-based lesson is recorded in planning material, but '
        'its package was not recovered. The current course has its own reporting lesson.</p>'
        '<p><a href="README.md">Archive inventory and provenance</a></p>',
        '../1.7.0-preparation/assets/styles.css', None,
    )
    return outputs


def page(title, content, stylesheet, course):
    navigation = '<p><a href="https://smartaimemory.com/harness/help/">Help Center</a></p>'
    if course:
        navigation += f'<p><a href="{course}">Course overview</a></p>'
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<meta name="robots" content="noindex,follow">'
            f'<title>{escape(title)} · Attune Harness</title><link rel="stylesheet" href="{stylesheet}">'
            '</head><body><main style="max-width:900px;margin:auto;padding:2rem">'
            + navigation + content + '</main></body></html>\n')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Refuse stale derived files without writing")
    args = parser.parse_args()
    expected = project()
    if args.check:
        stale = [str(path.relative_to(ROOT)) for path, text in expected.items()
                 if not path.is_file() or path.read_text(encoding="utf-8") != text]
        if stale:
            raise SystemExit("Regenerate the course: " + ", ".join(stale))
        print(f"{len(expected)} derived course files match their sources")
    else:
        for path, text in expected.items():
            path.write_text(text, encoding="utf-8")
        print(f"Generated {len(expected)} course files")
