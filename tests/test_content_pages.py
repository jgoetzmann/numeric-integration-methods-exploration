"""Page content tests: B13, B31, B32, B33, B36.

Written from .fullsend/SPEC.md alone. Expectations come from data/claims.json
and data/sources.json. The site is built once for this module by running
tools/build.py as a subprocess into a temporary directory.
"""

import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"

CLAIMS_DOC = json.loads((DATA / "claims.json").read_text(encoding="utf-8"))
SOURCES = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
CLAIMS = CLAIMS_DOC["claims"]
CLAIM_BY_ID = {c["id"]: c for c in CLAIMS}
REPOS = SOURCES["repos"]
REPO_NAMES = [r["name"] for r in REPOS]
SITE_REPOS = [r for r in REPOS if r.get("site")]

# B31
LINKED_PAGES = ["rk.html", "novel.html", "architecture.html", "epochs.html", "claims.html", "repos.html"]
HEADLINE_IDS = [c["id"] for c in CLAIMS if c.get("headline") is True]

# B32
NOVEL_LINKED_IDS = ["N2", "N3", "N4", "N5", "N6", "N7", "N8"]
NOVEL_QUOTED_IDS = ["N2", "N4"]

# B13
NO_BLIND_PAGES = ["index.html", "rk.html", "architecture.html", "epochs.html", "repos.html"]
NEGATED_BLIND_PAGES = ["claims.html", "novel.html"]
BLIND_RE = re.compile(r"\bblind(?:ed)?\b", re.IGNORECASE)
NEGATION_RE = re.compile(r"\b(?:not|no|neither)\b", re.IGNORECASE)

# B36
SNAPSHOT_PAGES = ["index.html", "rk.html", "epochs.html"]
FINDINGS_URL = "https://jgoetzmann.github.io/rk-findings/"


# ---------------------------------------------------------------------------
# Minimal DOM on top of html.parser
# ---------------------------------------------------------------------------

VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
})
INLINE_TAGS = frozenset({
    "a", "abbr", "b", "bdi", "bdo", "cite", "code", "data", "dfn", "em", "i",
    "kbd", "mark", "q", "s", "samp", "small", "span", "strong", "sub", "sup",
    "time", "u", "var",
})
SKIP_ALWAYS = frozenset({"script", "style", "head", "template"})
BLOCK_MARK = "\x00"


class Node:
    def __init__(self, tag, attrs, parent):
        self.tag = tag
        self.attrs = {k: (v if v is not None else "") for k, v in attrs}
        self.children = []
        self.parent = parent


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#document", [], None)
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        node = Node(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(node)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def parse_html(text):
    builder = _TreeBuilder()
    builder.feed(text)
    builder.close()
    return builder.root


def elements(node):
    """Every element below `node`, in document order."""
    for child in node.children:
        if isinstance(child, Node):
            yield child
            yield from elements(child)


def ancestors(node):
    parent = node.parent
    while parent is not None:
        yield parent
        parent = parent.parent


def norm(s):
    return re.sub(r"\s+", " ", s or "").strip()


def _collect(node, skip, parts, mark):
    for child in node.children:
        if isinstance(child, str):
            parts.append(child)
            continue
        if child.tag in skip or child.tag in SKIP_ALWAYS:
            parts.append(" " if child.tag in INLINE_TAGS else mark)
            continue
        block = child.tag not in INLINE_TAGS
        if block:
            parts.append(mark)
        _collect(child, skip, parts, mark)
        if block:
            parts.append(mark)


def text_of(node, skip=()):
    """Whitespace-normalized text under `node`, leaving out elements named in `skip`."""
    parts = []
    _collect(node, frozenset(skip), parts, " ")
    return norm("".join(parts))


def sentences(node, skip=()):
    """Sentences of the text under `node`: split at block elements, then after . ! or ?."""
    parts = []
    _collect(node, frozenset(skip), parts, BLOCK_MARK)
    out = []
    for block in "".join(parts).split(BLOCK_MARK):
        block = norm(block)
        if not block:
            continue
        out.extend(s for s in re.split(r"(?<=[.!?])\s+", block) if s)
    return out


def rel(href):
    href = (href or "").strip()
    return href[2:] if href.startswith("./") else href


def main_of(doc, name):
    mains = [el for el in elements(doc) if el.tag == "main"]
    assert mains, f"{name} has no <main>"
    return mains[0]


def link_hrefs(node, outside_nav=False):
    out = []
    for a in elements(node):
        if a.tag != "a":
            continue
        if outside_nav and any(p.tag == "nav" for p in ancestors(a)):
            continue
        out.append(a.attrs.get("href", ""))
    return out


def repo_card(main, repo):
    """The smallest element around a link to the repo's url that shows its role and
    commit and links no other repo's url; None when there is no such element."""
    role = norm(repo["role"])
    others = {r["url"] for r in REPOS if r["name"] != repo["name"]}
    for a in elements(main):
        if a.tag != "a" or a.attrs.get("href") != repo["url"]:
            continue
        node = a
        while node is not None and node is not main:
            text = text_of(node)
            if role in text and repo["commit"] in text:
                hrefs = {x.attrs.get("href") for x in elements(node) if x.tag == "a"}
                if not (hrefs & others):
                    return node
                break
            node = node.parent
    return None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("content_pages_site")
    proc = subprocess.run(
        [sys.executable, "tools/build.py", "--out", str(out)],
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
    assert proc.returncode == 0, (
        f"tools/build.py exited {proc.returncode}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
    return out


@pytest.fixture(scope="module")
def page(site):
    cache = {}

    def get(name):
        if name not in cache:
            path = site / name
            assert path.is_file(), f"tools/build.py did not write {name}"
            cache[name] = parse_html(path.read_text(encoding="utf-8"))
        return cache[name]

    return get


# ---------------------------------------------------------------------------
# B13: "blind" / "blinded"
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", NO_BLIND_PAGES)
def test_b13_blind_absent_outside_quotes(page, name):
    """B13: "blind" and "blinded" appear nowhere in this page's visible text outside <q> and <blockquote>."""
    doc = page(name)
    text = text_of(doc, skip=("q", "blockquote"))
    assert text, f"{name} has no visible text"
    hits = [s for s in sentences(doc, skip=("q", "blockquote")) if BLIND_RE.search(s)]
    assert hits == [], f"{name} uses blind/blinded outside quotes: {hits}"


@pytest.mark.parametrize("name", NEGATED_BLIND_PAGES)
def test_b13_blind_only_in_negated_sentences(page, name):
    """B13: on claims.html and novel.html, every sentence with "blind" or "blinded" outside quotes also contains "not", "no" or "neither"."""
    doc = page(name)
    bad = [
        s for s in sentences(doc, skip=("q", "blockquote"))
        if BLIND_RE.search(s) and not NEGATION_RE.search(s)
    ]
    assert bad == [], f"{name} has un-negated sentences with blind/blinded: {bad}"


# ---------------------------------------------------------------------------
# B31: index links every page and every headline claim
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("target", LINKED_PAGES)
def test_b31_index_body_links_page(page, target):
    """B31: index.html links to each other page from its body, outside the nav."""
    main = main_of(page("index.html"), "index.html")
    hrefs = [rel(h).split("#", 1)[0] for h in link_hrefs(main, outside_nav=True)]
    assert target in hrefs, f"index.html body has no link to {target}; links: {hrefs}"


@pytest.mark.parametrize("cid", HEADLINE_IDS)
def test_b31_index_links_headline_claim(page, cid):
    """B31: index.html links every headline claim as claims.html#<id>."""
    main = main_of(page("index.html"), "index.html")
    hrefs = [rel(h) for h in link_hrefs(main, outside_nav=True)]
    assert f"claims.html#{cid}" in hrefs, (
        f"index.html does not link headline claim {cid} as claims.html#{cid}"
    )


# ---------------------------------------------------------------------------
# B32: novel.html links N2-N8 and quotes N2 and N4
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cid", NOVEL_LINKED_IDS)
def test_b32_novel_links_audit_claim(page, cid):
    """B32: novel.html links claims.html#N2 through claims.html#N8."""
    hrefs = [rel(h) for h in link_hrefs(page("novel.html"))]
    assert f"claims.html#{cid}" in hrefs, f"novel.html does not link claims.html#{cid}"


@pytest.mark.parametrize("cid", NOVEL_QUOTED_IDS)
def test_b32_novel_quotes_original_wording_in_blockquote(page, cid):
    """B32: novel.html shows the original_wording of N2 and N4 inside <blockquote>."""
    doc = page("novel.html")
    wording = norm(CLAIM_BY_ID[cid]["original_wording"])
    quotes = [text_of(el) for el in elements(doc) if el.tag == "blockquote"]
    assert any(wording in q for q in quotes), (
        f"novel.html: {cid} original_wording not inside a <blockquote>; blockquotes: {quotes!r}"
    )


@pytest.mark.parametrize("cid", NOVEL_QUOTED_IDS)
def test_b32_novel_original_wording_not_outside_blockquote(page, cid):
    """B32: the 2025 project's original wording for N2 and N4 is not stated on novel.html outside a <blockquote>."""
    outside = text_of(page("novel.html"), skip=("blockquote",))
    wording = norm(CLAIM_BY_ID[cid]["original_wording"])
    assert wording not in outside, f"novel.html shows {cid} original_wording outside <blockquote>"


# ---------------------------------------------------------------------------
# B33: repos.html
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("repo", REPOS, ids=REPO_NAMES)
def test_b33_repo_listed_with_url_role_and_commit(page, repo):
    """B33: repos.html lists the repo with a link to its url, its role and its commit."""
    main = main_of(page("repos.html"), "repos.html")
    hrefs = link_hrefs(main)
    text = text_of(main)
    assert repo["url"] in hrefs, f"repos.html does not link {repo['url']}"
    assert norm(repo["role"]) in text, f"repos.html does not state the role of {repo['name']}"
    assert repo["commit"] in text, f"repos.html does not show the commit of {repo['name']}"
    assert repo_card(main, repo) is not None, (
        f"repos.html: no single element holds {repo['name']}'s link, role and commit apart from the other repos"
    )


@pytest.mark.parametrize("repo", REPOS, ids=REPO_NAMES)
def test_b33_repo_entry_shows_no_other_repo_commit(page, repo):
    """B33: a repo's entry on repos.html shows its own commit and not another repo's."""
    main = main_of(page("repos.html"), "repos.html")
    card = repo_card(main, repo)
    assert card is not None, f"repos.html: no entry for {repo['name']} with its link, role and commit"
    text = text_of(card)
    foreign = [r["name"] for r in REPOS if r["name"] != repo["name"] and r["commit"] in text]
    assert foreign == [], f"{repo['name']}'s entry also shows the commit of {foreign}"


@pytest.mark.parametrize("repo", SITE_REPOS, ids=[r["name"] for r in SITE_REPOS])
def test_b33_repo_live_site_linked(page, repo):
    """B33: repos.html links each repo's live site when `site` is set."""
    main = main_of(page("repos.html"), "repos.html")
    assert repo["site"] in link_hrefs(main), f"repos.html does not link {repo['name']}'s site {repo['site']}"


def test_b33_private_workspace_sentence_stated(page):
    """B33: repos.html states the private_workspace sentence from sources.json."""
    main = main_of(page("repos.html"), "repos.html")
    sentence = norm(SOURCES["private_workspace"])
    assert sentence in text_of(main), f"repos.html does not state: {sentence!r}"


def test_b33_no_link_to_rk_dev(page):
    """B33: repos.html states the private workspace without a link to rk-dev."""
    doc = page("repos.html")
    bad = [
        (a.attrs.get("href", ""), text_of(a))
        for a in elements(doc)
        if a.tag == "a"
        and ("rk-dev" in a.attrs.get("href", "").lower() or "rk-dev" in text_of(a).lower())
    ]
    assert bad == [], f"repos.html links rk-dev: {bad}"


# ---------------------------------------------------------------------------
# B36: snapshot note on index, rk and epochs
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", SNAPSHOT_PAGES)
def test_b36_page_states_snapshot_date(page, name):
    """B36: the page body states the snapshot date from sources.json."""
    main = main_of(page(name), name)
    date = SOURCES["snapshot_date"]
    assert date in text_of(main), f"{name} body does not state the snapshot date {date}"


@pytest.mark.parametrize("name", SNAPSHOT_PAGES)
def test_b36_page_links_findings_site(page, name):
    """B36: the page links to https://jgoetzmann.github.io/rk-findings/ for current numbers."""
    main = main_of(page(name), name)
    assert FINDINGS_URL in link_hrefs(main), f"{name} body does not link {FINDINGS_URL}"
