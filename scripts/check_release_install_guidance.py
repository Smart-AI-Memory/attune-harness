"""Validate the current install surfaces against an exact final release."""

import argparse
from email import policy
from email.parser import BytesParser
import hashlib
from html.parser import HTMLParser
from importlib import metadata
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
from zipfile import BadZipFile, ZipFile

REPO = "https://github.com/Smart-AI-Memory/attune-harness"
SITE = "https://smartaimemory.com"
GET_STARTED = SITE + "/harness/help/get-started/"
DEPENDENCIES = SITE + "/harness/help/dependencies/"
LEARN = SITE + "/harness/learn/"
LEARN_REDIRECT = GET_STARTED + "#set-up-the-practice-folder"
FINAL = r"[0-9]+\.[0-9]+\.[0-9]+"
PIN = re.compile(r"\battune-harness(?:\[([a-z0-9,-]+)\])?(?:==([^\s'\x22`<>&|)]+))?")
LINK = re.compile(
    rf"(?:https://pypi\.org/project/attune-harness/|{re.escape(REPO)}/(?:releases/tag|blob|tree)/v)"
    rf"({FINAL}(?:rc[0-9]+)?)(?=/|[#)\s]|$)"
)
ATTUNE = re.compile(r"(attune[-_][a-z0-9_-]+)\s*==\s*([a-zA-Z0-9.!+_-]+)", re.I)
INSTALL = re.compile(r"\b(?:pipx?|uv tool) install\b")
GUIDE_ANCHOR = re.compile(r"/docs/installation\.md#install-(\d+)-with-pipx-or-a-virtual-environment$")
DEPENDENCY_ROW = re.compile(r"^\| `(attune-[a-z0-9-]+)` \| `([^ `]+)` \|", re.M)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_surface(label, commands, links, version, *, profiles=(), expected_links=()):
    found = set()
    for command in commands:
        if INSTALL.search(command):
            for match in PIN.finditer(command):
                found.add(match.group(1) or "base")
                require(match.group(2) == version, f"{label}: expected {version}, found {match[0]}")
    require(set(profiles) <= found, f"{label}: missing install examples for {sorted(set(profiles) - found)}")
    for href in links:
        if anchor := GUIDE_ANCHOR.search(href):
            require(anchor[1] == version.replace(".", ""), f"{label}: stale installation anchor {href}")
        match = LINK.search(href)
        if match:
            require(match[1] == version, f"{label}: stale release link {href}")
    require(set(expected_links) <= set(links), f"{label}: missing expected links {sorted(set(expected_links) - set(links))}")
    return {"profiles": sorted(found), "release_links": sorted({href for href in links if LINK.search(href)})}


def markdown_links(text):
    return re.findall(r"\]\((https://[^)\s]+)\)", text)


def wheel_metadata(wheel, version):
    with ZipFile(wheel) as archive:
        paths = [name for name in archive.namelist() if PurePosixPath(name).parts[-1:] == ("METADATA",)]
        expected = f"attune_harness-{version}.dist-info/METADATA"
        require(paths == [expected], "Expected one release wheel metadata file")
        message = BytesParser(policy=policy.default).parsebytes(archive.read(expected))
    require(message["Name"] == "attune-harness" and message["Version"] == version, "Wrong wheel identity")
    return message


def archive_links(readme, version):
    return {
        href
        for found, section in re.findall(
            r"^## What changes in (" + FINAL + r")\s*\n(.*?)(?=^## |\Z)", readme, re.M | re.S
        )
        if found != version
        for href in markdown_links(section)
        if (match := LINK.search(href)) and match[1] == found
    }


def candidate(root, wheel, version):
    pypi = f"https://pypi.org/project/attune-harness/{version}/"
    release = f"{REPO}/releases/tag/v{version}"
    message = wheel_metadata(wheel, version)
    readme = (root / "README.md").read_text(encoding="utf-8")
    published_readme = message.get_payload(decode=True).decode("utf-8")
    require(published_readme.rstrip("\n") == readme.rstrip("\n"), "Wheel README differs from reviewed source")
    dependencies = (root / "help/dependencies.md").read_text(encoding="utf-8")
    require(dict(DEPENDENCY_ROW.findall(dependencies)) == direct_attune_pins(message.get_all("Requires-Dist", [])),
            "Help Dependencies: direct Attune table does not match release wheel metadata")
    specs = [
        ("README / wheel description", readme, ("base", "redis"), (pypi, release, GET_STARTED, LEARN)),
        ("Help Get Started", (root / "help/get-started.md").read_text(encoding="utf-8"), ("base",), (pypi,)),
        ("Help Dependencies", dependencies, ("redis",), (pypi,)),
    ]
    installation = (root / "docs/installation.md").read_text(encoding="utf-8")
    # Explicit section boundaries keep archived releases, including their pinned installs, intact.
    before, old, after = installation.partition("\n## Install the 1.7.0 runtime\n")
    _old_body, current_heading, after = after.partition("\n## Build your first report offline\n")
    current, historical, _ = after.partition("\n## Reproduce the pre-release setup\n")
    require(old and current_heading and historical, "Installation guidance: current/archive boundaries changed; review this gate")
    specs.append(("Installation guide", before + current, ("base", "redis", "voyage", "all"), (pypi, release)))
    # Current installation links can be pinned to either the new tag or a reviewed older tree
    # only if they do not advertise an older release as current. Leave explicitly historical lines alone.
    exempt = archive_links(readme, version)
    result = {}
    for label, body, profiles, links in specs:
        lines = [line for line in body.splitlines() if not (
            label == "Installation guide" and line.startswith(("[1.8.0 installation guide]", "The [1.8.0 release]"))
        )]
        urls = markdown_links("\n".join(lines))
        if label == "README / wheel description":
            urls = [url for url in urls if url not in exempt]
        result[label] = check_surface(label, lines, urls, version,
                                      profiles=profiles, expected_links=links)
    return result


def direct_attune_pins(requirements):
    pins = {}
    for requirement in requirements:
        name = re.match(r"attune[-_][a-z0-9_-]+", requirement, re.I)
        if not name or name[0].lower().replace("_", "-") == "attune-harness":
            continue
        match = ATTUNE.fullmatch(requirement.strip())
        require(match, f"Direct Attune requirement must be an unconditional exact pin: {requirement}")
        key = match[1].lower().replace("_", "-")
        require(key not in pins, f"Duplicate direct Attune requirement: {key}")
        pins[key] = match[2]
    require(pins, "Published metadata did not declare direct Attune dependencies")
    return pins


def verify_install(version, published, *, read_version=metadata.version, read_requires=metadata.requires):
    require(read_version("attune-harness") == version, "Installed Harness version differs")
    pins = direct_attune_pins(published)
    require(direct_attune_pins(read_requires("attune-harness")) == pins, "Installed Attune pins differ from PyPI metadata")
    resolved = {name: read_version(name) for name in pins}
    require(resolved == pins, f"Installed Attune versions differ: expected {pins}, found {resolved}")
    return resolved


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.links = set()
        self.anchors = set()
        self.commands = []
        self.code = None
        self.code_tag = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if anchor := attrs.get("id"):
            self.anchors.add(anchor)
        if tag == "a" and (href := attrs.get("href")):
            self.links.add(href)
        if tag in ("code", "pre") and self.code is None:
            self.code_tag = tag
            self.code = []

    def handle_endtag(self, tag):
        if tag == self.code_tag and self.code is not None:
            self.commands.extend("".join(self.code).splitlines())
            self.code = None
            self.code_tag = None

    def handle_data(self, data):
        if self.code is not None:
            self.code.append(data)


def read_public(url):
    # No auth, no cached receipt substitute. A network error is not a pass.
    try:
        with urlopen(Request(url, headers={"Cache-Control": "no-cache"}), timeout=20) as response:
            # Learn intentionally leads to the current Help course setup rather
            # than a second copy of the tutorial. Do not accept arbitrary redirects.
            learn_redirect = url == LEARN and response.url == LEARN_REDIRECT
            require(response.url == url or learn_redirect, f"Unexpected redirect destination: {response.url}")
            body = response.read(8_000_001)
            require(len(body) <= 8_000_000, "Public response too large")
            text = body.decode("utf-8")
            if learn_redirect:
                require("set-up-the-practice-folder" in Page(text).anchors,
                        "Learn destination has no course setup anchor")
            return text
    except (OSError, ValueError) as error:
        raise ValueError(f"{url}: {error}") from error


def public_docs(version, *, historical=(), pypi_description=None, read=read_public):
    pypi = f"https://pypi.org/project/attune-harness/{version}/"
    release = f"{REPO}/releases/tag/v{version}"
    pages = {}
    for url, profiles, wanted in (
        (pypi, ("base", "redis"), (release, GET_STARTED, LEARN)),
        (GET_STARTED, ("base",), (pypi,)),
        (DEPENDENCIES, ("redis",), (pypi,)),
        (LEARN, ("base",), (GET_STARTED, SITE + "/harness/learn/reporting/")),
    ):
        if url == pypi and pypi_description is not None:
            # The authoritative public PyPI JSON description is compared to the
            # verified artifact in main(); rendering is a distinct manual QA.
            commands, links = pypi_description.splitlines(), markdown_links(pypi_description)
            source = "public PyPI JSON description"
        else:
            page = Page(read(url))
            commands, links = page.commands, [urljoin(url, href) for href in page.links]
            source = "live HTML"
        if url == pypi:
            links = [href for href in links if href not in historical]
        pages[url] = check_surface(url, commands, links, version, profiles=profiles, expected_links=wanted)
        pages[url]["source"] = source
    # Release-tag links from these current surfaces are all on a fixed trusted origin.
    destinations = {release}
    for page in pages.values():
        destinations.update(url.split("#", 1)[0] for url in page["release_links"] if url.startswith(REPO + "/"))
    for url in sorted(destinations):
        read(url)
    return pages


def completion_inputs(identity, installs, published_requirements):
    require({record.get("profile") for record in installs} == {"base", "redis"} and len(installs) == 2,
            "Expected evidence for both base and Redis clean installs")
    for record in installs:
        require(record.get("pip_check") == "passed"
                and all(record.get(key) == identity[key] for key in ("commit", "version", "wheel_sha256"))
                and record.get("stage") == "installed" and record.get("status") == "passed"
                and record.get("direct_attune_dependencies") == direct_attune_pins(published_requirements),
                "Missing or mismatched clean/install dependency evidence")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("candidate", "installed", "website"))
    parser.add_argument("--version", required=True)
    parser.add_argument("--release-sha", required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--install-report", type=Path)
    parser.add_argument("--installed-evidence", type=Path, nargs=2)
    args = parser.parse_args()
    version = args.version
    receipt = {"stage": args.stage, "version": version, "commit": args.release_sha}
    try:
        require(re.fullmatch(FINAL, version), "This check applies to final versions, not development or RC")
        require(re.fullmatch(r"[0-9a-f]{40}", args.release_sha), "A full release SHA is required")
        receipt["wheel_sha256"] = hashlib.sha256(args.wheel.read_bytes()).hexdigest()
        if args.stage == "candidate":
            receipt["surfaces"] = candidate(Path.cwd(), args.wheel, version)
        else:
            endpoint = f"https://pypi.org/pypi/attune-harness/{version}/json"
            published = json.loads(read_public(endpoint))
            require(published["info"]["version"] == version, "PyPI metadata version differs")
            require(any(file["filename"] == args.wheel.name and
                        file["digests"]["sha256"] == receipt["wheel_sha256"] and not file["yanked"]
                        for file in published["urls"]), "Published wheel does not match the approved bytes")
            if args.stage == "installed":
                report = json.loads(args.install_report.read_text(encoding="utf-8"))
                installs = [item for item in report["install"] if item["metadata"]["name"] == "attune-harness"]
                require(len(installs) == 1 and installs[0]["requested"], "Expected one requested Harness install")
                download = installs[0]["download_info"]
                require(urlsplit(download["url"]).scheme == "https"
                        and urlsplit(download["url"]).hostname == "files.pythonhosted.org"
                        and download["archive_info"]["hashes"]["sha256"] == receipt["wheel_sha256"],
                        "Installed wheel was not the reviewed PyPI artifact")
                receipt["profile"] = "redis" if "redis" in installs[0].get("requested_extras", []) else "base"
                subprocess.run([sys.executable, "-m", "pip", "--isolated", "check"], check=True)
                receipt["direct_attune_dependencies"] = verify_install(version, published["info"]["requires_dist"])
                receipt["python"] = sys.version.split()[0]
                receipt["pip_check"] = "passed"
            else:
                require(args.installed_evidence, "Both post-PyPI install receipts are required")
                installs = [json.loads(path.read_text(encoding="utf-8")) for path in args.installed_evidence]
                completion_inputs(receipt, installs, published["info"]["requires_dist"])
                description = wheel_metadata(args.wheel, version).get_payload(decode=True).decode("utf-8")
                public_description = published["info"]["description"]
                require(public_description.rstrip("\n") == description.rstrip("\n"),
                        "Public PyPI README differs from the approved wheel description")
                receipt["surfaces"] = public_docs(
                    version, historical=archive_links(description, version), pypi_description=public_description, read=read_public
                )
        receipt["status"] = "passed"
    except (ValueError, OSError, KeyError, TypeError, RuntimeError, AttributeError, BadZipFile, subprocess.CalledProcessError) as error:
        receipt.update(status="failed", error=str(error))
    args.report.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    if receipt["status"] != "passed":
        raise SystemExit(receipt["error"])


if __name__ == "__main__":
    main()
