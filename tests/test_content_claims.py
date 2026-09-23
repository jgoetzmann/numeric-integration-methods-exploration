"""Claims audit page content tests: B14, B15, B16, B17, B18.

Written from .fullsend/SPEC.md alone. Every expectation is driven by
data/claims.json and data/sources.json, which are frozen spec inputs.
The site is built once for this module by running tools/build.py as a
subprocess into a temporary directory.
"""

import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

import pytest

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"

CLAIMS_DOC = json.loads((DATA / "claims.json").read_text(encoding="utf-8"))
SOURCES = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
CLAIMS = CLAIMS_DOC["claims"]
CLAIM_IDS = [c["id"] for c in CLAIMS]
CLAIM_ID_SET = frozenset(CLAIM_IDS)
PROJECT_OF = {c["id"]: c["project"] for c in CLAIMS}
REPO_BY_NAME = {r["name"]: r for r in SOURCES["repos"]}

# B15: the four verdict labels, keyed by the verdict value in claims.json.
VERDICT_LABELS = {
    "supported": "Supported",
    "supported-with-limits": "Supported with limits",
    "not-supported": "Not supported",
    "artifact": "Artifact",
}

# B16 subsets.
REJECTED = [c for c in CLAIMS if c["verdict"] in ("not-supported", "artifact")]
WORDED = [c for c in CLAIMS if c.get("original_wording")]
LIMITED = [c for c in CLAIMS if c["verdict"] == "supported-with-limits"]

# B18: group headings, as (h2 id, h2 text). The id equals the claim's `project`.
GROUPS = [
    ("rk", "The rk run"),
    ("novel", "The 2025 ML project"),
    ("both", "Across both projects"),
]
GROUP_IDS = frozenset(g for g, _ in GROUPS)


# ---------------------------------------------------------------------------
# B17 expectations
# ---------------------------------------------------------------------------

def is_multi(path):
    """B17: a path is not a single file when it has ';' or '*' or ends with '/'."""
    return ";" in path or "*" in path or path.endswith("/")


def expected_href(ev):
    """B17: blob link for a single file, tree link otherwise, at the sources.json commit."""
    repo = REPO_BY_NAME[ev["repo"]]
    if is_multi(ev["path"]):
        return f"{repo['url']}/tree/{repo['commit']}"
    return f"{repo['url']}/blob/{repo['commit']}/{ev['path']}"


MULTI = [
    (c["id"], i, ev)
    for c in CLAIMS
    for i, ev in enumerate(c["evidence"])
    if is_multi(ev["path"])
]


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


class Node:
    def __init__(self, tag, attrs, parent):
        self.tag = tag
        self.attrs = {k: (v if v is not None else "") for k, v in attrs}
        self.children = []
        self.parent = parent

    def classes(self):
        return self.attrs.get("class", "").split()


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


def norm(s):
    return re.sub(r"\s+", " ", s or "").strip()


def _collect(node, skip, parts):
    for child in node.children:
        if isinstance(child, str):
            parts.append(child)
            continue
        if child.tag in skip or child.tag in SKIP_ALWAYS:
            parts.append(" ")
            continue
        block = child.tag not in INLINE_TAGS
        if block:
            parts.append(" ")
        _collect(child, skip, parts)
        if block:
            parts.append(" ")


def text_of(node, skip=()):
    """Whitespace-normalized text under `node`, leaving out elements named in `skip`."""
    parts = []
    _collect(node, frozenset(skip), parts)
    return norm("".join(parts))


def text_after(root, target):
    """Text under `root` that comes after the element `target` in document order."""
    parts = []
    state = [False]

    def walk(node):
        for child in node.children:
            if isinstance(child, str):
                if state[0]:
                    parts.append(child)
                continue
            if child is target:
                state[0] = True
                parts.append(" ")
                continue
            if child.tag in SKIP_ALWAYS:
                continue
            block = child.tag not in INLINE_TAGS
            if block and state[0]:
                parts.append(" ")
            walk(child)
            if block and state[0]:
                parts.append(" ")

    walk(root)
    return norm("".join(parts))


def clean_href(href):
    """href without its #fragment, percent-decoded."""
    return unquote((href or "").split("#", 1)[0])


def labels_in(text):
    """Which B15 verdict labels a piece of text carries."""
    found = set()
    if re.search(r"\bSupported with limits\b", text):
        found.add("supported-with-limits")
    if re.search(r"\bNot supported\b", text):
        found.add("not-supported")
    if re.search(r"\bArtifact\b", text):
        found.add("artifact")
    if re.search(r"(?<!Not )\bSupported\b(?! with limits)", text):
        found.add("supported")
    return found


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("content_claims_site")
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
def claims_page(site):
    path = site / "claims.html"
    assert path.is_file(), "tools/build.py did not write claims.html"
    return parse_html(path.read_text(encoding="utf-8"))


def claim_section(page, cid):
    matches = [
        el for el in elements(page)
        if el.tag in ("section", "article") and el.attrs.get("id") == cid
    ]
    assert matches, f"claims.html has no <section> or <article> with id={cid!r}"
    return matches[0]


def claim_groups(page):
    """(claim id, id of the nearest preceding group <h2>) for each claim section, in document order."""
    current = None
    seen = []
    for el in elements(page):
        if el.tag == "h2" and el.attrs.get("id") in GROUP_IDS:
            current = el.attrs["id"]
        elif el.tag in ("section", "article") and el.attrs.get("id") in CLAIM_ID_SET:
            seen.append((el.attrs["id"], current))
    return seen


# ---------------------------------------------------------------------------
# B14: every claim in its own <section>/<article>, id = claim id
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("claim", CLAIMS, ids=CLAIM_IDS)
def test_b14_claim_rendered_in_section_with_its_id_and_text(claims_page, claim):
    """B14: claims.html renders the claim in a <section> or <article> whose id is the claim id, showing the id and the claim."""
    section = claim_section(claims_page, claim["id"])
    text = text_of(section)
    id_pattern = r"(?<![A-Za-z0-9])" + re.escape(claim["id"]) + r"(?![0-9])"
    assert re.search(id_pattern, text), f"section {claim['id']} does not show its id; text: {text[:300]!r}"
    assert norm(claim["claim"]) in text, (
        f"section {claim['id']} does not show the claim text {claim['claim']!r}"
    )


@pytest.mark.parametrize("claim", CLAIMS, ids=CLAIM_IDS)
def test_b14_claim_id_names_exactly_one_element(claims_page, claim):
    """B14: the claim id is used by one element only, so claims.html#<id> cannot land on a duplicate."""
    hits = [el.tag for el in elements(claims_page) if el.attrs.get("id") == claim["id"]]
    assert len(hits) == 1, f"id={claim['id']!r} appears on {len(hits)} elements: {hits}"


def test_b14_no_claim_section_for_an_id_missing_from_claims_json(claims_page):
    """B14: claims.html renders the claims in claims.json and no claim ids that are not in it."""
    stray = sorted({
        el.attrs["id"]
        for el in elements(claims_page)
        if el.tag in ("section", "article")
        and re.fullmatch(r"[RNU][0-9]+", el.attrs.get("id", ""))
        and el.attrs["id"] not in CLAIM_ID_SET
    })
    assert stray == [], f"claim sections with ids not in claims.json: {stray}"


# ---------------------------------------------------------------------------
# B15: verdict labels are text inside class="verdict verdict-<verdict>"
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("claim", CLAIMS, ids=CLAIM_IDS)
def test_b15_claim_verdict_label_is_text_in_verdict_element(claims_page, claim):
    """B15: the claim's verdict label is written as text inside an element with class="verdict verdict-<verdict>"."""
    section = claim_section(claims_page, claim["id"])
    wanted = {"verdict", "verdict-" + claim["verdict"]}
    badges = [el for el in elements(section) if wanted <= set(el.classes())]
    assert badges, (
        f"section {claim['id']} has no element with class=\"verdict verdict-{claim['verdict']}\""
    )
    label = VERDICT_LABELS[claim["verdict"]]
    texts = [text_of(el) for el in badges]
    assert any(labels_in(t) == {claim["verdict"]} for t in texts), (
        f"section {claim['id']}: verdict element text {texts!r} does not carry the label {label!r}"
    )


@pytest.mark.parametrize("claim", CLAIMS, ids=CLAIM_IDS)
def test_b15_claim_carries_no_other_verdict(claims_page, claim):
    """B15: a claim's section shows no verdict class or verdict label other than its own."""
    section = claim_section(claims_page, claim["id"])
    other_classes = {"verdict-" + v for v in VERDICT_LABELS if v != claim["verdict"]}
    wrong = []
    for el in elements(section):
        classes = set(el.classes())
        if classes & other_classes:
            wrong.append(sorted(classes & other_classes))
        elif "verdict" in classes:
            extra = labels_in(text_of(el)) - {claim["verdict"]}
            if extra:
                wrong.append(sorted(extra))
    assert wrong == [], f"section {claim['id']} ({claim['verdict']}) also shows {wrong}"


def test_b15_no_verdict_element_relies_on_color_alone(claims_page):
    """B15: every element with class "verdict" names exactly one known verdict and writes its label as text."""
    bad = []
    for el in elements(claims_page):
        classes = el.classes()
        if "verdict" not in classes:
            continue
        kinds = [c[len("verdict-"):] for c in classes if c.startswith("verdict-")]
        kinds = [k for k in kinds if k in VERDICT_LABELS]
        text = text_of(el)
        if len(kinds) != 1 or labels_in(text) != {kinds[0]}:
            bad.append((el.attrs.get("class"), text))
    assert bad == [], f"verdict elements without a matching text label: {bad}"


# ---------------------------------------------------------------------------
# B16: rejected claims quoted and corrected; wording in blockquote; limits shown
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("claim", REJECTED, ids=[c["id"] for c in REJECTED])
def test_b16_rejected_claim_is_quoted_then_corrected(claims_page, claim):
    """B16: for not-supported and artifact claims the claim text is inside <q> and the correction follows it."""
    section = claim_section(claims_page, claim["id"])
    claim_text = norm(claim["claim"])
    quotes = [el for el in elements(section) if el.tag == "q" and claim_text in text_of(el)]
    assert quotes, f"section {claim['id']}: the claim text is not inside a <q>"
    after = text_after(section, quotes[0])
    assert norm(claim["correction"]) in after, (
        f"section {claim['id']}: the correction does not follow the quoted claim"
    )


@pytest.mark.parametrize("claim", REJECTED, ids=[c["id"] for c in REJECTED])
def test_b16_rejected_claim_text_never_shown_unquoted(claims_page, claim):
    """B16: a not-supported or artifact claim's own text appears on claims.html only inside <q>."""
    outside = text_of(claims_page, skip=("q", "blockquote"))
    assert norm(claim["claim"]) not in outside, (
        f"{claim['id']}: rejected claim text appears outside <q>"
    )


@pytest.mark.parametrize("claim", REJECTED, ids=[c["id"] for c in REJECTED])
def test_b16_correction_is_not_inside_a_quote(claims_page, claim):
    """B16: the correction follows the quoted claim in the page's own voice, not inside <q> or <blockquote>."""
    section = claim_section(claims_page, claim["id"])
    outside = text_of(section, skip=("q", "blockquote"))
    assert norm(claim["correction"]) in outside, (
        f"section {claim['id']}: the correction is missing or sits inside <q>/<blockquote>"
    )


@pytest.mark.parametrize("claim", WORDED, ids=[c["id"] for c in WORDED])
def test_b16_original_wording_is_in_blockquote(claims_page, claim):
    """B16: original_wording, when present, is shown inside a <blockquote> in the claim's section."""
    section = claim_section(claims_page, claim["id"])
    wording = norm(claim["original_wording"])
    quotes = [text_of(el) for el in elements(section) if el.tag == "blockquote"]
    assert any(wording in q for q in quotes), (
        f"section {claim['id']}: original_wording not inside a <blockquote>; blockquotes: {quotes!r}"
    )


@pytest.mark.parametrize("claim", WORDED, ids=[c["id"] for c in WORDED])
def test_b16_original_wording_never_outside_blockquote(claims_page, claim):
    """B16: original_wording does not appear on claims.html outside a <blockquote>."""
    outside = text_of(claims_page, skip=("blockquote",))
    assert norm(claim["original_wording"]) not in outside, (
        f"{claim['id']}: original_wording appears outside <blockquote>"
    )


@pytest.mark.parametrize("claim", LIMITED, ids=[c["id"] for c in LIMITED])
def test_b16_supported_with_limits_shows_limits(claims_page, claim):
    """B16: for supported-with-limits claims the limits text is shown in the claim's section."""
    section = claim_section(claims_page, claim["id"])
    assert norm(claim["limits"]) in text_of(section), (
        f"section {claim['id']}: limits text not shown: {claim['limits']!r}"
    )


# ---------------------------------------------------------------------------
# B17: evidence links pinned to the sources.json commit
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("claim", CLAIMS, ids=CLAIM_IDS)
def test_b17_every_evidence_entry_links_to_pinned_file_or_tree(claims_page, claim):
    """B17: each evidence entry links to <url>/blob/<commit>/<path> (single file) or <url>/tree/<commit>, and the link text shows the path and the at value."""
    section = claim_section(claims_page, claim["id"])
    anchors = [
        (clean_href(a.attrs.get("href")), text_of(a))
        for a in elements(section)
        if a.tag == "a"
    ]
    missing = []
    for ev in claim["evidence"]:
        want = expected_href(ev)
        path = norm(ev["path"])
        at = norm(ev.get("at") or "")
        if not any(href == want and path in text and at in text for href, text in anchors):
            missing.append({"href": want, "path": ev["path"], "at": ev.get("at", "")})
    assert missing == [], (
        f"section {claim['id']}: evidence without a matching link: {missing}; links found: {anchors}"
    )


@pytest.mark.parametrize("claim", CLAIMS, ids=CLAIM_IDS)
def test_b17_evidence_links_never_use_a_branch_or_another_commit(claims_page, claim):
    """B17: every blob/tree link in a claim's section uses the commit sources.json pins for that repo."""
    section = claim_section(claims_page, claim["id"])
    bad = []
    for a in elements(section):
        if a.tag != "a":
            continue
        href = clean_href(a.attrs.get("href"))
        for repo in SOURCES["repos"]:
            for kind in ("/blob/", "/tree/"):
                prefix = repo["url"] + kind
                if href.startswith(prefix):
                    ref = href[len(prefix):].split("/", 1)[0]
                    if ref != repo["commit"]:
                        bad.append(href)
    assert bad == [], f"section {claim['id']}: links not pinned to the sources.json commit: {bad}"


@pytest.mark.parametrize(
    "cid,index,ev", MULTI, ids=[f"{cid}-evidence{i}" for cid, i, _ in MULTI]
)
def test_b17_multi_file_evidence_is_not_linked_as_one_file(claims_page, cid, index, ev):
    """B17: an evidence path with ';', '*' or a trailing '/' links to the repo tree at the commit, never to a blob."""
    section = claim_section(claims_page, cid)
    repo = REPO_BY_NAME[ev["repo"]]
    tree = f"{repo['url']}/tree/{repo['commit']}"
    path = norm(ev["path"])
    bad = []
    for a in elements(section):
        if a.tag != "a":
            continue
        href = clean_href(a.attrs.get("href"))
        if path in text_of(a) and href != tree:
            bad.append(href)
        elif href.startswith(repo["url"] + "/blob/") and (";" in href or "*" in href or href.endswith("/")):
            bad.append(href)
    assert bad == [], f"{cid} evidence {ev['path']!r} linked as a file: {bad}"


def test_b17_no_blob_link_names_a_path_list_glob_or_directory(claims_page):
    """B17: no /blob/ link on claims.html points at a ';' list, a '*' glob or a directory."""
    bad = []
    for a in elements(claims_page):
        if a.tag != "a":
            continue
        href = clean_href(a.attrs.get("href"))
        if "/blob/" in href and (";" in href or "*" in href or href.endswith("/")):
            bad.append(href)
    assert bad == [], f"blob links to multi-file paths: {bad}"


# ---------------------------------------------------------------------------
# B18: grouped under three h2 headings, claims.json order within each
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("gid,title", GROUPS, ids=[g for g, _ in GROUPS])
def test_b18_group_heading_has_id_and_text(claims_page, gid, title):
    """B18: claims.html has an <h2 id="<group>"> with the group's heading text."""
    heads = [el for el in elements(claims_page) if el.tag == "h2" and el.attrs.get("id") == gid]
    assert len(heads) == 1, f"expected one <h2 id={gid!r}>, found {len(heads)}"
    assert text_of(heads[0]) == title, f"<h2 id={gid!r}> reads {text_of(heads[0])!r}, expected {title!r}"


@pytest.mark.parametrize("gid,title", GROUPS, ids=[g for g, _ in GROUPS])
def test_b18_group_lists_its_claims_in_claims_json_order(claims_page, gid, title):
    """B18: under each group heading come that project's claims, in claims.json order."""
    got = [cid for cid, g in claim_groups(claims_page) if g == gid]
    want = [c["id"] for c in CLAIMS if c["project"] == gid]
    assert got == want, f"group {gid!r}: claims in order {got}, expected {want}"


@pytest.mark.parametrize("gid,title", GROUPS, ids=[g for g, _ in GROUPS])
def test_b18_no_claim_filed_under_another_group(claims_page, gid, title):
    """B18: no claim from another project sits under this group's heading."""
    wrong = [cid for cid, g in claim_groups(claims_page) if g == gid and PROJECT_OF[cid] != gid]
    assert wrong == [], f"group {gid!r} holds claims from other projects: {wrong}"


def test_b18_no_claim_before_the_first_group_heading(claims_page):
    """B18: every claim sits under one of the three group headings."""
    orphans = [cid for cid, g in claim_groups(claims_page) if g is None]
    assert orphans == [], f"claims outside any group heading: {orphans}"
