"""The timeline on epochs.html (B29) and the two architecture diagrams on architecture.html (B30).

The site is built once for this module by running tools/build.py into a temp directory.
"""

import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

# --------------------------------------------------------------------------
# Inline helpers. Duplicated on purpose in every test_charts_* module (no
# conftest, no shared helper module); reconcile may collapse them.
# --------------------------------------------------------------------------

REPO = Path(__file__).resolve().parent.parent
DATA_DIR = REPO / "data"
RK = json.loads((DATA_DIR / "rk.json").read_text(encoding="utf-8"))
NOVEL = json.loads((DATA_DIR / "novel.json").read_text(encoding="utf-8"))
SOURCES = json.loads((DATA_DIR / "sources.json").read_text(encoding="utf-8"))

_VOID = frozenset("area base br col embed hr img input link meta param source track wbr".split())
_P_CLOSERS = frozenset(
    "address article aside blockquote details div dl fieldset figcaption figure footer form "
    "h1 h2 h3 h4 h5 h6 header hr main nav ol p pre section table ul".split()
)


class Node:
    """One element of a page parsed with html.parser."""

    def __init__(self, tag, attrs, parent):
        self.tag = tag
        self.attrs = attrs
        self.parent = parent
        self.children = []

    def iter(self):
        """This node and every descendant element, in document order."""
        stack = [self]
        while stack:
            node = stack.pop()
            yield node
            stack.extend(reversed([c for c in node.children if isinstance(c, Node)]))

    def text(self, skip=()):
        """Text of the subtree; element boundaries become spaces; subtrees tagged in `skip` are dropped."""
        parts = []
        for child in self.children:
            if isinstance(child, str):
                parts.append(child)
            elif child.tag not in skip:
                parts.append(" " + child.text(skip) + " ")
        return "".join(parts)

    def classes(self):
        return (self.attrs.get("class") or "").split()


class _TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#document", {}, None)
        self.stack = [self.root]

    def _close_open(self, names, stop):
        for i in range(len(self.stack) - 1, 0, -1):
            tag = self.stack[i].tag
            if tag in names:
                del self.stack[i:]
                return
            if tag in stop:
                return

    def _implicit_ends(self, tag):
        if tag in ("td", "th"):
            self._close_open({"td", "th"}, {"tr", "table"})
        elif tag == "tr":
            self._close_open({"tr"}, {"table"})
        elif tag in ("thead", "tbody", "tfoot"):
            self._close_open({"thead", "tbody", "tfoot"}, {"table"})
        elif tag == "li":
            self._close_open({"li"}, {"ul", "ol"})
        elif tag in ("dt", "dd"):
            self._close_open({"dt", "dd"}, {"dl"})
        if tag in _P_CLOSERS and self.stack[-1].tag == "p":
            self.stack.pop()

    def _add(self, tag, attrs):
        self._implicit_ends(tag)
        node = Node(tag, {k: ("" if v is None else v) for k, v in attrs}, self.stack[-1])
        self.stack[-1].children.append(node)
        return node

    def handle_starttag(self, tag, attrs):
        node = self._add(tag, attrs)
        if tag not in _VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self._add(tag, attrs)

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


class _Site:
    def __init__(self, out, proc):
        self.out = out
        self.proc = proc
        self._pages = {}

    def page(self, slug):
        if slug not in self._pages:
            path = self.out / slug
            if not path.is_file():
                pytest.fail(
                    f"the build wrote no {slug} (exit code {self.proc.returncode}).\n"
                    f"stderr:\n{self.proc.stderr[-3000:]}"
                )
            self._pages[slug] = parse_html(path.read_text(encoding="utf-8"))
        return self._pages[slug]


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("site_charts_diagrams")
    proc = subprocess.run(
        [sys.executable, "tools/build.py", "--out", str(out)],
        cwd=REPO,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
    return _Site(out, proc)


def norm(s):
    return " ".join(s.split())


def find_id(root, ident):
    for node in root.iter():
        if node.attrs.get("id") == ident:
            return node
    return None


def svg_nodes(container):
    """Every element inside any <svg> within `container` (each once, nested svgs included)."""
    seen = set()
    out = []
    for node in container.iter():
        if node.tag != "svg" or id(node) in seen:
            continue
        for n in node.iter():
            if id(n) not in seen:
                seen.add(id(n))
                out.append(n)
    return out


def marks(fig):
    """Data marks: svg elements whose class list contains the token "mark"."""
    return [n for n in svg_nodes(fig) if "mark" in n.classes()]


def title_of(node):
    """Text of the node's direct <title> child, or "" when it has none."""
    for child in node.children:
        if isinstance(child, Node) and child.tag == "title":
            return norm(child.text())
    return ""


def describe(ms, limit=40):
    return "\n".join(f"  <{m.tag}> {title_of(m)!r}" for m in ms[:limit]) or "  (no marks)"


def svg_label_text(fig):
    """Lower-cased text of every <text> element in the figure's svgs."""
    parts = [n.text(skip=("title", "desc")) for n in svg_nodes(fig) if n.tag == "text"]
    return norm(" ".join(parts)).lower()


def assign(rows, cands, accepts):
    """Match each row to a distinct candidate that accepts it (bipartite matching).
    Returns ({row index: candidate index}, [unmatched row indices])."""
    ok = [[accepts(r, c) for c in cands] for r in rows]
    owner = {}

    def place(ri, seen):
        for ci in range(len(cands)):
            if ok[ri][ci] and ci not in seen:
                seen.add(ci)
                if ci not in owner or place(owner[ci], seen):
                    owner[ci] = ri
                    return True
        return False

    unmatched = [ri for ri in range(len(rows)) if not place(ri, set())]
    return {ri: ci for ci, ri in owner.items()}, unmatched


# --------------------------------------------------------------------------
# Expectations
# --------------------------------------------------------------------------

SNAPSHOT = SOURCES["snapshot_date"]

# B29, with its dates as the spec writes them (they match data/novel.json repo.active_*,
# data/rk.json epochs.* and down_days, and data/sources.json snapshot_date).
TIMELINE_EVENTS = [
    ("the 2025 project's active window", ("2025-09-13", "2025-09-21")),
    ("epoch 1", ("2026-08-29", "2026-09-10")),
    ("the epoch 1 freeze", ("2026-09-15",)),
    ("epoch 2's start", ("2026-09-17",)),
    ("the stopped window", ("2026-09-17", "2026-09-23")),
    ("the snapshot date", (SNAPSHOT,)),
]

ARCH_WORDS = {
    "arch-rk": ["watchdog", "container", "verifier", "runner", "archive", "findings site"],
    "arch-novel": ["generator", "evolution", "stepper", "reference solver", "composite score"],
}


def event_accepts(event, mark):
    title = title_of(mark)
    return all(date in title for date in event[1])


def latest_data_date():
    found = []

    def walk(v):
        if isinstance(v, dict):
            for x in v.values():
                walk(x)
        elif isinstance(v, list):
            for x in v:
                walk(x)
        elif isinstance(v, str):
            found.extend(re.findall(r"(?<!\d)(?:19|20)\d{2}-\d{2}-\d{2}(?!\d)", v))

    for doc in (RK, NOVEL, SOURCES):
        walk(doc)
    return max(found)


def timeline(site):
    fig = find_id(site.page("epochs.html"), "timeline")
    assert fig is not None, "epochs.html has no element with id='timeline'"
    assert fig.tag == "figure", f"id='timeline' is on <{fig.tag}>, want <figure>"
    assert "chart" in fig.classes(), f"figure#timeline has class={fig.attrs.get('class')!r}, want it to include 'chart'"
    return fig


# --------------------------------------------------------------------------
# B29: the timeline
# --------------------------------------------------------------------------


def test_b29_timeline_has_a_mark_for_each_event(site):
    """B29: <figure id="timeline" class="chart"> has marks for the 2025 active window, epoch 1, the epoch 1
    freeze, epoch 2's start, the stopped window and the snapshot date (a window's mark gives both ends)."""
    fig = timeline(site)
    ms = marks(fig)
    missing = [
        f"{name} ({' to '.join(dates)})" for name, dates in TIMELINE_EVENTS if not any(event_accepts((name, dates), m) for m in ms)
    ]
    assert not missing, "no timeline mark for: " + "; ".join(missing) + f"\n{describe(ms)}"


def test_b29_no_single_timeline_mark_stands_for_two_events(site):
    """B29: the six events get six different marks; one bar from 2026-09-17 to 2026-09-23 cannot also be
    epoch 2's start and the snapshot date."""
    fig = timeline(site)
    ms = marks(fig)
    _, unmatched = assign(TIMELINE_EVENTS, ms, event_accepts)
    assert not unmatched, (
        "events without a mark of their own: " + "; ".join(TIMELINE_EVENTS[i][0] for i in unmatched) + f"\n{describe(ms)}"
    )


def test_b29_no_timeline_mark_is_dated_after_the_data(site):
    """B29: every timeline date comes from the data; no mark is dated later than the latest date in
    rk.json, novel.json or sources.json (the snapshot date), which would mean a clock read."""
    fig = timeline(site)
    latest = latest_data_date()
    late = []
    for m in marks(fig):
        for date in re.findall(r"\d{4}-\d{2}-\d{2}", title_of(m)):
            if date > latest:
                late.append(f"{date}: {title_of(m)!r}")
    assert not late, f"timeline marks dated after {latest}:\n  " + "\n  ".join(late)


# --------------------------------------------------------------------------
# B30: architecture diagrams
# --------------------------------------------------------------------------


@pytest.mark.parametrize("figure_id", sorted(ARCH_WORDS))
def test_b30_architecture_figure_is_an_inline_svg_whose_text_names_its_parts(site, figure_id):
    """B30: architecture.html has <figure id="arch-rk"> and <figure id="arch-novel">, each with an inline svg
    whose <text> elements include the named parts (case-insensitive substring)."""
    fig = find_id(site.page("architecture.html"), figure_id)
    assert fig is not None, f"architecture.html has no element with id={figure_id!r}"
    assert fig.tag == "figure", f"id={figure_id!r} is on <{fig.tag}>, want <figure>"
    assert any(n.tag == "svg" for n in fig.iter()), f"figure#{figure_id} has no inline <svg>"
    text = svg_label_text(fig)
    missing = [w for w in ARCH_WORDS[figure_id] if w not in text]
    assert not missing, f"figure#{figure_id} svg <text> lacks {missing}; svg text: {text[:600]!r}"
