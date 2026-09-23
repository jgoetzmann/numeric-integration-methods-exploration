"""Structure tests for the built site: B1-B7 and B12 of .fullsend/SPEC.md.

The site is built once per module by running tools/build.py as a subprocess
into a temporary directory. web.shell, web.data and the page packages are
imported inside tests only, so a missing module fails the tests that need it.
HTML is parsed with html.parser from the standard library.
"""
from __future__ import annotations

import copy
import importlib
import json
import os
import posixpath
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

SITE_NAME = "Numeric integration methods"
PAGES = [
    ("index.html", "Story"),
    ("rk.html", "The rk run"),
    ("novel.html", "The 2025 ML project"),
    ("architecture.html", "Architecture"),
    ("epochs.html", "Epochs and research"),
    ("claims.html", "Claims audit"),
    ("repos.html", "Repositories"),
]
SLUGS = [slug for slug, _ in PAGES]
SOURCES = json.loads((REPO / "data" / "sources.json").read_text(encoding="utf-8"))
VOID = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
)
SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
EXTERNAL = re.compile(r"^(?:https?:)?//", re.IGNORECASE)


# --------------------------------------------------------------------------- helpers


class _Doc(HTMLParser):
    """Every element with its attributes, its ancestor tags and its text content."""

    def __init__(self, html: str):
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.open_elements: list[dict] = []
        self.elements: list[dict] = []
        self.feed(html)
        self.close()

    def _record(self, tag, attrs):
        pairs = [(name, value if value is not None else "") for name, value in attrs]
        element = {
            "tag": tag,
            "pairs": pairs,
            "attrs": dict(pairs),
            "ancestors": tuple(self.stack),
            "text": [],
        }
        self.elements.append(element)
        return element

    def handle_starttag(self, tag, attrs):
        element = self._record(tag, attrs)
        if tag not in VOID:
            self.stack.append(tag)
            self.open_elements.append(element)

    def handle_startendtag(self, tag, attrs):
        self._record(tag, attrs)

    def handle_endtag(self, tag):
        if tag not in self.stack:
            return
        while self.stack:
            self.stack.pop()
            if self.open_elements.pop()["tag"] == tag:
                break

    def handle_data(self, data):
        for element in self.open_elements:
            element["text"].append(data)

    def tags(self, tag):
        return [el for el in self.elements if el["tag"] == tag]

    def anchors_in(self, container):
        return [el for el in self.elements if el["tag"] == "a" and container in el["ancestors"]]


def _text(element) -> str:
    return " ".join("".join(element["text"]).split())


def _run_build(out: Path, seed: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONIOENCODING="utf-8")
    return subprocess.run(
        [sys.executable, "tools/build.py", "--out", str(out)],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("build_structure_a")
    return {"out": out, "proc": _run_build(out, seed="0")}


@pytest.fixture(scope="module")
def second_site(tmp_path_factory):
    out = tmp_path_factory.mktemp("build_structure_b")
    return {"out": out, "proc": _run_build(out, seed="1")}


def _require_build(built) -> Path:
    proc = built["proc"]
    if proc.returncode != 0:
        pytest.fail(
            f"tools/build.py exited {proc.returncode}\n"
            f"stderr:\n{proc.stderr[-4000:]}\nstdout:\n{proc.stdout[-2000:]}"
        )
    return built["out"]


def _pages(built) -> dict[str, str]:
    out = _require_build(built)
    pages = {}
    for slug in SLUGS:
        path = out / slug
        if not path.is_file():
            pytest.fail(f"{slug} was not written to the output directory")
        pages[slug] = path.read_text(encoding="utf-8")
    return pages


def _data() -> dict:
    return importlib.import_module("web.data").load(REPO)


def _shell():
    return importlib.import_module("web.shell")


def _page_module(slug: str):
    return importlib.import_module("web.pages." + slug[: -len(".html")])


def _tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _href_path(href: str) -> str:
    path = href.split("#", 1)[0].split("?", 1)[0]
    return path[2:] if path.startswith("./") else path


def _nav_matches(doc: _Doc) -> list[dict]:
    """Nav anchors that list PAGES in order as (href, label) pairs; extra nav links are ignored."""
    matched = []
    for anchor in doc.anchors_in("nav"):
        if len(matched) == len(PAGES):
            break
        slug, label = PAGES[len(matched)]
        if _href_path(anchor["attrs"].get("href", "")) == slug and _text(anchor) == label:
            matched.append(anchor)
    return matched


def _nav_problems(label: str, html: str, current: str) -> list[str]:
    doc = _Doc(html)
    if not doc.tags("nav"):
        return [f"{label}: no <nav>"]
    matched = _nav_matches(doc)
    if len(matched) != len(PAGES):
        found = [(_href_path(a["attrs"].get("href", "")), _text(a)) for a in doc.anchors_in("nav")]
        return [f"{label}: nav lists {len(matched)} of the seven PAGES in order; nav links are {found}"]
    problems = []
    for (slug, _), anchor in zip(PAGES, matched):
        aria = anchor["attrs"].get("aria-current")
        if slug == current and aria != "page":
            problems.append(f"{label}: link to {slug} lacks aria-current=\"page\" (has {aria!r})")
        if slug != current and aria == "page":
            problems.append(f"{label}: link to {slug} carries aria-current=\"page\" but is not the current page")
    return problems


def _footer_problems(label: str, html: str, sources: dict) -> list[str]:
    doc = _Doc(html)
    footers = doc.tags("footer")
    if not footers:
        return [f"{label}: no <footer>"]
    text = " ".join("".join(footer["text"]) for footer in footers)
    anchors = doc.anchors_in("footer")
    problems = []
    for repo in sources["repos"]:
        if repo["name"] not in text:
            problems.append(f"{label}: footer does not name {repo['name']}")
        want = f"{repo['url']}/tree/{repo['commit']}"
        if not any(
            a["attrs"].get("href") == want and repo["commit"] in "".join(a["text"]) for a in anchors
        ):
            problems.append(f"{label}: footer has no link to {want} whose text includes {repo['commit']}")
    return problems


def _resolve(slug: str, href: str):
    """Return (target path relative to the output dir, fragment, error)."""
    path, _, fragment = href.partition("#")
    path = path.split("?", 1)[0]
    if path == "":
        return slug, unquote(fragment), None
    if path.startswith("/"):
        return None, fragment, "is root-relative, so it does not resolve inside the output directory"
    target = posixpath.normpath(posixpath.join(posixpath.dirname(slug), unquote(path)))
    if target == ".." or target.startswith("../"):
        return None, fragment, "points outside the output directory"
    return target, unquote(fragment), None


def _relative_hrefs(doc: _Doc):
    for element in doc.elements:
        for name, value in element["pairs"]:
            if name in ("href", "xlink:href"):
                href = value.strip()
                if SCHEME.match(href) or href.startswith("//"):
                    continue
                yield href


# --------------------------------------------------------------------------- B1


def test_b1_build_exits_zero(site):
    """B1: python tools/build.py --out DIR exits 0."""
    proc = site["proc"]
    assert proc.returncode == 0, f"stderr:\n{proc.stderr[-4000:]}"


def test_b1_writes_all_seven_pages(site):
    """B1: index, rk, novel, architecture, epochs, claims and repos .html are written, non-empty."""
    out = _require_build(site)
    missing = [slug for slug in SLUGS if not (out / slug).is_file()]
    assert missing == [], f"pages not written: {missing}"
    empty = [slug for slug in SLUGS if (out / slug).stat().st_size == 0]
    assert empty == [], f"pages written empty: {empty}"


def test_b1_style_css_is_copied_verbatim(site):
    """B1: DIR/style.css is written, a byte-for-byte copy of web/style.css (Surface: copied verbatim)."""
    out = _require_build(site)
    assert (out / "style.css").is_file()
    assert (out / "style.css").read_bytes() == (REPO / "web" / "style.css").read_bytes()


def test_b1_nojekyll_is_written_empty(site):
    """B1: an empty DIR/.nojekyll is written."""
    out = _require_build(site)
    marker = out / ".nojekyll"
    assert marker.is_file()
    assert marker.stat().st_size == 0


def test_b1_every_asset_a_page_returns_is_written(site):
    """B1: DIR/assets/<name> is written for every asset returned by a page's assets(data)."""
    out = _require_build(site)
    data = _data()
    expected: dict[str, str] = {}
    for slug in SLUGS:
        assets = getattr(_page_module(slug), "assets", None)
        if assets is not None:
            expected.update(assets(data))
    problems = []
    for name, text in sorted(expected.items()):
        path = out / "assets" / name
        if not path.is_file():
            problems.append(f"assets/{name} missing")
        elif path.read_text(encoding="utf-8") != text:
            problems.append(f"assets/{name} differs from what assets() returned")
    assert problems == []


# --------------------------------------------------------------------------- B2


def test_b2_two_builds_write_the_same_files(site, second_site):
    """B2: builds into two different directories (different hash seeds) write the same file set."""
    first = _tree(_require_build(site))
    second = _tree(_require_build(second_site))
    assert set(SLUGS) <= set(first)
    assert sorted(first) == sorted(second)


def test_b2_two_builds_are_byte_identical(site, second_site):
    """B2: every file from two builds into two directories is byte-identical."""
    first = _tree(_require_build(site))
    second = _tree(_require_build(second_site))
    assert set(SLUGS) <= set(first) & set(second)
    differing = sorted(name for name in set(first) & set(second) if first[name] != second[name])
    assert differing == [], f"files that differ between two builds: {differing}"


# --------------------------------------------------------------------------- B3


def test_b3_every_page_has_the_document_head(site):
    """B3: doctype first, html lang=en, meta charset utf-8, viewport meta, style.css link, one <main>."""
    problems = []
    for slug, html in _pages(site).items():
        doc = _Doc(html)
        if html[:15].lower() != "<!doctype html>":
            problems.append(f"{slug}: does not start with <!doctype html> (starts {html[:20]!r})")
        roots = doc.tags("html")
        if not roots or roots[0]["attrs"].get("lang") != "en":
            problems.append(f"{slug}: no <html lang=\"en\">")
        metas = doc.tags("meta")
        if not any(m["attrs"].get("charset", "").lower() == "utf-8" for m in metas):
            problems.append(f"{slug}: no <meta charset=\"utf-8\">")
        if not any(
            m["attrs"].get("name", "").lower() == "viewport" and m["attrs"].get("content", "").strip()
            for m in metas
        ):
            problems.append(f"{slug}: no viewport meta with content")
        if not any(
            "stylesheet" in link["attrs"].get("rel", "").lower().split()
            and link["attrs"].get("href") == "style.css"
            for link in doc.tags("link")
        ):
            problems.append(f"{slug}: no <link rel=\"stylesheet\" href=\"style.css\">")
        mains = len(doc.tags("main"))
        if mains != 1:
            problems.append(f"{slug}: {mains} <main> elements, expected exactly one")
    assert problems == []


def test_b3_title_and_description_come_from_the_page_package(site):
    """B3: <title> is 'TITLE | Numeric integration methods' and the description meta holds DESCRIPTION."""
    problems = []
    for slug, html in _pages(site).items():
        module = _page_module(slug)
        if module.SLUG != slug:
            problems.append(f"{slug}: package SLUG is {module.SLUG!r}")
        doc = _Doc(html)
        titles = [t for t in doc.tags("title") if "svg" not in t["ancestors"]]
        want = " ".join(f"{module.TITLE} | {SITE_NAME}".split())
        if len(titles) != 1 or _text(titles[0]) != want:
            problems.append(f"{slug}: document titles {[_text(t) for t in titles]}, expected [{want!r}]")
        descriptions = [
            m for m in doc.tags("meta") if m["attrs"].get("name", "").lower() == "description"
        ]
        if not any(m["attrs"].get("content") == module.DESCRIPTION for m in descriptions):
            problems.append(f"{slug}: no <meta name=\"description\"> whose content is DESCRIPTION")
    assert problems == []


def test_b3_descriptions_are_non_empty_and_under_160_characters():
    """B3: each page's DESCRIPTION (used in the description meta) is non-empty and under 160 characters."""
    problems = []
    for slug in SLUGS:
        description = _page_module(slug).DESCRIPTION
        if not isinstance(description, str) or not description.strip():
            problems.append(f"{slug}: DESCRIPTION is empty")
        elif len(description) >= 160:
            problems.append(f"{slug}: DESCRIPTION is {len(description)} characters")
    assert problems == []


def test_b3_site_name_constant():
    """B3: web.shell.SITE_NAME is the title suffix 'Numeric integration methods'."""
    assert _shell().SITE_NAME == "Numeric integration methods"


def test_b3_shell_page_builds_a_complete_document_around_the_body():
    """B3: shell.page returns a complete HTML5 document with the given title and description, body inside <main>."""
    html = _shell().page(
        "rk.html",
        "Probe title",
        "Probe description sentence.",
        '<h1>Probe heading</h1><p id="probe-body">Probe body text</p>',
        _data(),
    )
    assert html[:15].lower() == "<!doctype html>"
    doc = _Doc(html)
    assert [r["attrs"].get("lang") for r in doc.tags("html")] == ["en"]
    titles = [t for t in doc.tags("title") if "svg" not in t["ancestors"]]
    assert [_text(t) for t in titles] == ["Probe title | Numeric integration methods"]
    assert any(
        m["attrs"].get("name", "").lower() == "description"
        and m["attrs"].get("content") == "Probe description sentence."
        for m in doc.tags("meta")
    )
    assert len(doc.tags("main")) == 1
    probe = [p for p in doc.tags("p") if p["attrs"].get("id") == "probe-body"]
    assert len(probe) == 1
    assert "main" in probe[0]["ancestors"]
    assert _text(probe[0]) == "Probe body text"


# --------------------------------------------------------------------------- B4


def test_b4_no_script_elements(site):
    """B4: no page contains <script."""
    offenders = [slug for slug, html in _pages(site).items() if "<script" in html.lower()]
    assert offenders == []


def test_b4_no_inline_event_handler_attributes(site):
    """B4: no element on any page carries an on...= event-handler attribute."""
    problems = []
    for slug, html in _pages(site).items():
        for element in _Doc(html).elements:
            for name, _ in element["pairs"]:
                if name.lower().startswith("on"):
                    problems.append(f"{slug}: <{element['tag']} {name}=...>")
    assert problems == []


def test_b4_no_javascript_urls(site):
    """B4: no attribute value on any page is a javascript: URL."""
    problems = []
    for slug, html in _pages(site).items():
        for element in _Doc(html).elements:
            for name, value in element["pairs"]:
                if re.sub(r"\s+", "", value).lower().startswith("javascript:"):
                    problems.append(f"{slug}: <{element['tag']} {name}={value!r}>")
    assert problems == []


def test_b4_external_urls_appear_only_in_anchor_href(site):
    """B4: no src= or <link href=> points at http(s); external URLs appear only in <a href>."""
    problems = []
    for slug, html in _pages(site).items():
        for element in _Doc(html).elements:
            for name, value in element["pairs"]:
                if not EXTERNAL.match(value.strip()):
                    continue
                if name == "xmlns" or name.startswith("xmlns:"):
                    continue
                if element["tag"] == "a" and name == "href":
                    continue
                problems.append(f"{slug}: <{element['tag']} {name}={value!r}>")
    assert problems == []


# --------------------------------------------------------------------------- B5


def test_b5_pages_constant_lists_the_seven_pages_in_order():
    """B5: web.shell.PAGES is the seven (slug, label) pairs in the spec's order."""
    pages = _shell().PAGES
    assert isinstance(pages, list)
    assert pages == PAGES


def test_b5_every_page_nav_lists_all_pages_in_order_and_marks_the_current_one(site):
    """B5: each page's <nav> links all seven PAGES in order; only the current page's link has aria-current=page."""
    problems = []
    for slug, html in _pages(site).items():
        problems += _nav_problems(slug, html, slug)
    assert problems == []


def test_b5_shell_page_marks_whichever_slug_it_is_given():
    """B5: shell.page puts aria-current=page on the link for the slug passed in, for each of the seven slugs."""
    shell = _shell()
    data = _data()
    problems = []
    for slug in SLUGS:
        html = shell.page(slug, "Probe", "Probe description.", "<h1>Probe</h1>", data)
        problems += _nav_problems(f"shell.page({slug!r})", html, slug)
    assert problems == []


# --------------------------------------------------------------------------- B6


def test_b6_relative_hrefs_resolve_to_files_in_the_output(site):
    """B6: every relative href on every page resolves to a file in the output directory."""
    out = _require_build(site)
    problems = []
    checked = 0
    for slug, html in _pages(site).items():
        for href in _relative_hrefs(_Doc(html)):
            checked += 1
            target, _, error = _resolve(slug, href)
            if error:
                problems.append(f"{slug}: href {href!r} {error}")
            elif not (out / target).is_file():
                problems.append(f"{slug}: href {href!r} -> {target!r} is not a file in the output")
    assert checked > 0, "no relative hrefs found on any page"
    assert problems == []


def test_b6_fragments_resolve_to_element_ids(site):
    """B6: every #fragment, same-page or cross-page, names an element id on the target page."""
    out = _require_build(site)
    ids: dict[str, set[str]] = {}

    def ids_on(target: str) -> set[str]:
        if target not in ids:
            path = out / target
            ids[target] = (
                {el["attrs"]["id"] for el in _Doc(path.read_text(encoding="utf-8")).elements if "id" in el["attrs"]}
                if path.is_file()
                else set()
            )
        return ids[target]

    problems = []
    fragments = 0
    for slug, html in _pages(site).items():
        for href in _relative_hrefs(_Doc(html)):
            target, fragment, error = _resolve(slug, href)
            if error or not fragment:
                continue
            fragments += 1
            if fragment not in ids_on(target):
                problems.append(f"{slug}: href {href!r} names no id on {target}")
    assert fragments > 0, "no #fragment links found on any page (claims.html#<id> links are required)"
    assert problems == []


# --------------------------------------------------------------------------- B7


def test_b7_every_footer_links_each_repo_at_its_commit(site):
    """B7: every page's <footer> names each repo in sources.json and links <url>/tree/<commit> with the commit in the text."""
    problems = []
    for slug, html in _pages(site).items():
        problems += _footer_problems(slug, html, SOURCES)
    assert problems == []


def test_b7_every_footer_states_the_snapshot_date(site):
    """B7: every page's <footer> states the snapshot date from sources.json."""
    date = SOURCES["snapshot_date"][:10]
    problems = []
    for slug, html in _pages(site).items():
        footers = _Doc(html).tags("footer")
        text = " ".join("".join(f["text"]) for f in footers)
        if date not in text:
            problems.append(f"{slug}: footer does not state {date}")
    assert problems == []


def test_b7_shell_page_footer_follows_the_sources_data_it_is_given():
    """B7: the footer is built from the data passed to shell.page: changed commits, an added repo and a new date all show."""
    data = copy.deepcopy(_data())
    sources = data["sources"]
    for repo in sources["repos"]:
        repo["commit"] = repo["commit"][::-1]
    sources["repos"].append(
        {
            "name": "probe-repo",
            "url": "https://github.com/example/probe-repo",
            "commit": "0123456789ab",
            "role": "a probe repository",
            "site": None,
        }
    )
    sources["snapshot_date"] = "2031-02-03"
    html = _shell().page("repos.html", "Probe", "Probe description.", "<h1>Probe</h1>", data)
    problems = _footer_problems("shell.page", html, sources)
    footer_text = " ".join("".join(f["text"]) for f in _Doc(html).tags("footer"))
    if "2031-02-03" not in footer_text:
        problems.append("shell.page: footer does not state the snapshot date it was given")
    assert problems == []


# --------------------------------------------------------------------------- B12


def test_b12_every_page_has_exactly_one_h1(site):
    """B12: every page has exactly one <h1>."""
    counts = {slug: len(_Doc(html).tags("h1")) for slug, html in _pages(site).items()}
    assert {slug: n for slug, n in counts.items() if n != 1} == {}


def test_b12_every_h2_has_an_id(site):
    """B12: every <h2> on every page has a non-empty id."""
    missing = [
        f"{slug}: <h2> {_text(h2)!r}"
        for slug, html in _pages(site).items()
        for h2 in _Doc(html).tags("h2")
        if not h2["attrs"].get("id", "").strip()
    ]
    assert missing == []


def test_b12_each_page_build_returns_exactly_one_h1():
    """B12: each page package's build(data) returns inner <main> HTML with exactly one <h1>."""
    data = _data()
    counts = {slug: len(_Doc(_page_module(slug).build(data)).tags("h1")) for slug in SLUGS}
    assert {slug: n for slug, n in counts.items() if n != 1} == {}


def test_b12_shell_page_adds_no_h1_and_no_h2_without_id():
    """B12: shell.page adds no <h1> of its own, and any <h2> it adds has an id."""
    html = _shell().page(
        "index.html",
        "Probe",
        "Probe description.",
        '<h1>Probe</h1><section><h2 id="probe-section">Probe section</h2></section>',
        _data(),
    )
    doc = _Doc(html)
    assert len(doc.tags("h1")) == 1
    assert [h2 for h2 in doc.tags("h2") if not h2["attrs"].get("id", "").strip()] == []
