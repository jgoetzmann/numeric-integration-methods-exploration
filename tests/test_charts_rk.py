"""Charts on rk.html: B21 (the six figures), B22 (frontier), B23 (counterfactual),
B24 (validation, Q15 and float64), B25 (floor vs round), B26 (archive growth).

Expected marks and values come from data/rk.json. A mark "states its value" when its <title>
contains the value in one of the forms web/fmt.py can produce (sig / ratio at 2, 3 or 4 digits,
count, or the plain integer), which is the B9 set of renderings.

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
    out = tmp_path_factory.mktemp("site_charts_rk")
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


def get_chart(site, slug, chart_id):
    fig = find_id(site.page(slug), chart_id)
    assert fig is not None, f"{slug} has no element with id={chart_id!r}"
    assert fig.tag == "figure", f"{slug}: id={chart_id!r} is on <{fig.tag}>, want <figure>"
    return fig


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
    """Lower-cased text of every <text> element in the figure's svgs: axis labels, legend, direct labels."""
    parts = [n.text(skip=("title", "desc")) for n in svg_nodes(fig) if n.tag == "text"]
    return norm(" ".join(parts)).lower()


def legend_text(fig):
    """Lower-cased figure text outside <title>, <desc> and the data table (svg text plus figcaption)."""
    return norm(fig.text(skip=("title", "desc", "details"))).lower()


def data_table(fig):
    for node in fig.iter():
        if node.tag == "details" and "data" in node.classes():
            for t in node.iter():
                if t.tag == "table":
                    return t
    return None


def table_rows(fig):
    """Text of each <tr> holding a <td>, cells joined by ' | '."""
    table = data_table(fig)
    assert table is not None, f"figure #{fig.attrs.get('id')} has no <details class=\"data\"> <table>"
    rows = []
    for tr in table.iter():
        if tr.tag != "tr":
            continue
        cells = [c for c in tr.children if isinstance(c, Node) and c.tag in ("td", "th")]
        if any(c.tag == "td" for c in cells):
            rows.append(" | ".join(norm(c.text()) for c in cells))
    return rows


def f_count(n):
    return f"{int(n):,}"


def f_sig(x, digits=3):
    if x == 0:
        return "0"
    a = abs(x)
    if 1e-4 <= a < 1000:
        return f"{x:.{digits}g}"
    if 1000 <= a < 1e15:
        return f_count(round(x))
    return f"{x:.{digits - 1}e}"


def f_ratio(x, digits=3):
    return f_sig(x, digits) + "x"


def formats(value):
    """Strings the spec's fmt functions may render `value` as: sig and ratio at 2, 3, 4 digits,
    count() when |value| >= 1, str(int()) when integral (the B9 set without pct)."""
    v = float(value)
    out = set()
    for d in (2, 3, 4):
        out.add(f_sig(v, d))
        out.add(f_ratio(v, d))
    if abs(v) >= 1:
        out.add(f_count(v))
    if v.is_integer():
        out.add(str(int(v)))
    return out


_ISO = re.compile(r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?")
_NUM = re.compile(r"\d(?:[\d,]*\d)?(?:\.\d+)?(?:e[+-]\d+)?[x%]?")


def num_tokens(text):
    """Number tokens in `text` (the B9 token shape). ISO dates are removed first, and a token glued
    to a preceding letter, underscore or hyphen-letter (rk4, Q15, heun2) is skipped."""
    text = _ISO.sub(" ", text)
    out = set()
    for m in _NUM.finditer(text):
        s = m.start()
        before = text[s - 1] if s >= 1 else " "
        before2 = text[s - 2] if s >= 2 else " "
        if before.isalpha() or before == "_" or (before == "-" and before2.isalpha()):
            continue
        out.add(m.group(0))
    return out


def states(text, value):
    return bool(formats(value) & num_tokens(text))


def has_words(text, label):
    """True when the alphanumeric words of `label` occur in `text` in order (case-insensitive)."""
    want = re.findall(r"[a-z0-9]+", label.lower())
    i = 0
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if i < len(want) and w == want[i]:
            i += 1
    return i == len(want)


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


_GEOMETRY = frozenset("x y x1 x2 y1 y2 cx cy r rx ry width height d points transform id tabindex role focusable".split())


def style_signature(node):
    """Tag plus every non-geometry attribute of the node and its ancestors up to the svg
    (class tokens other than "mark", fill, stroke, style, ...): what can tell two series apart."""
    items = {("<tag>", node.tag)}
    n = node
    while n is not None:
        for key, val in n.attrs.items():
            if key in _GEOMETRY or key.startswith("aria-"):
                continue
            if key == "class":
                items.update(("class", t) for t in val.split() if t != "mark")
            else:
                items.add((key, val))
        if n.tag == "svg":
            break
        n = n.parent
    return frozenset(items)


def assert_styled_apart(group_a, group_b, name_a, name_b):
    assert group_a and group_b, f"could not find marks for both {name_a} ({len(group_a)}) and {name_b} ({len(group_b)})"
    shared = {style_signature(m) for m in group_a} & {style_signature(m) for m in group_b}
    assert not shared, (
        f"{name_a} and {name_b} marks are styled identically (same tag, class, fill, stroke, style): "
        f"{sorted(next(iter(shared)))}; the two series cannot be told apart"
    )


# --------------------------------------------------------------------------
# Expectations from data/rk.json
# --------------------------------------------------------------------------

RK_PAGE = "rk.html"
RK_CHART_IDS = [
    "rk-frontier",
    "rk-counterfactual",
    "rk-validation-q15",
    "rk-validation-f64",
    "rk-floor-round",
    "rk-archive-growth",
]

CLASSICAL = RK["frontier"]["classical"]
DISCOVERED = RK["frontier"]["discovered"]
FRONTIER_ROWS = [("classical", r) for r in CLASSICAL] + [("discovered", r) for r in DISCOVERED]
CHAMPION_HASH = RK["champion"]["hash"]

CELLS = RK["counterfactual"]["cells"]

PROBLEMS = RK["validation"]["problems"]
PLOTTED_PROBLEMS = [p for p in PROBLEMS if not p["champion_overflowed"]]
OVERFLOWED_PROBLEMS = [p for p in PROBLEMS if p["champion_overflowed"]]
VALIDATION_KEYS = {
    "rk-validation-q15": ("champion_q15", "best_classical_q15"),
    "rk-validation-f64": ("champion_float64", "rk4_float64"),
}
VALIDATION_IDS = sorted(VALIDATION_KEYS)

SEARCH_RMS = RK["floor_vs_round"]["search_rms"]
HELDOUT_RMS = RK["floor_vs_round"]["heldout_rms"]
FLOOR_ROUND_ROWS = [(mode, method, SEARCH_RMS[mode][method]) for mode in sorted(SEARCH_RMS) for method in sorted(SEARCH_RMS[mode])]

EPOCH1_DAYS = RK["epochs"]["epoch1"]["archive_days"]
EPOCH2_DAYS = RK["epochs"]["epoch2"]["archive_days"]
ARCHIVE_ROWS = [(1, d) for d in EPOCH1_DAYS] + [(2, d) for d in EPOCH2_DAYS]


def frontier_accepts(row, mark):
    kind, r = row
    title = title_of(mark)
    if not states(title, r["heldout_error"]):
        return False
    return kind != "classical" or has_words(title, r["name"])


def describe_frontier_row(row):
    kind, r = row
    if kind == "classical":
        who = r["name"]
    else:
        who = f"{r['stages']}-stage order {r['order']} at {r['cycles']} cycles"
    return f"{kind} {who}: held-out error {f_sig(r['heldout_error'])}"


def overflow_mark(mark):
    # B24 names robertson_scaled as the problem where the champion overflowed.
    return "robertson" in title_of(mark).lower()


def validation_rows(chart_id):
    return [(p["problem"], key, p[key]) for p in PLOTTED_PROBLEMS for key in VALIDATION_KEYS[chart_id]]


def value_accepts(row, mark):
    return states(title_of(mark), row[-1])


def floor_round_accepts(row, mark):
    mode, method, value = row
    title = title_of(mark)
    return has_words(title, method) and states(title, value)


def archive_accepts(row, mark):
    _epoch, day = row
    title = title_of(mark)
    return day["day"] in title and states(title, day["cumulative"])


# --------------------------------------------------------------------------
# B21
# --------------------------------------------------------------------------


def test_b21_rk_page_has_the_six_chart_figures(site):
    """B21: rk.html has <figure class="chart"> with ids rk-frontier, rk-counterfactual,
    rk-validation-q15, rk-validation-f64, rk-floor-round and rk-archive-growth."""
    root = site.page(RK_PAGE)
    problems = []
    for cid in RK_CHART_IDS:
        node = find_id(root, cid)
        if node is None:
            problems.append(f"no element with id={cid!r}")
        elif node.tag != "figure":
            problems.append(f"id={cid!r} is on <{node.tag}>, want <figure>")
        elif "chart" not in node.classes():
            problems.append(f"figure#{cid} has class={node.attrs.get('class')!r}, want it to include 'chart'")
    assert not problems, "\n".join(problems)


# --------------------------------------------------------------------------
# B22: rk-frontier
# --------------------------------------------------------------------------


def test_b22_frontier_has_exactly_one_mark_per_frontier_row(site):
    """B22: 8 classical + 16 discovered rows give exactly 24 marks, no more and no fewer."""
    fig = get_chart(site, RK_PAGE, "rk-frontier")
    ms = marks(fig)
    assert len(ms) == len(FRONTIER_ROWS), (
        f"rk-frontier has {len(ms)} marks, want {len(CLASSICAL)} classical + {len(DISCOVERED)} discovered "
        f"= {len(FRONTIER_ROWS)}\n{describe(ms)}"
    )


def test_b22_each_frontier_row_has_its_own_mark_stating_its_heldout_error(site):
    """B22: every classical row (by name) and every discovered row has a distinct mark whose title states its held-out error."""
    fig = get_chart(site, RK_PAGE, "rk-frontier")
    ms = marks(fig)
    _, unmatched = assign(FRONTIER_ROWS, ms, frontier_accepts)
    missing = [describe_frontier_row(FRONTIER_ROWS[i]) for i in unmatched]
    assert not missing, "rows without a mark of their own:\n  " + "\n  ".join(missing) + f"\nmarks:\n{describe(ms)}"


def test_b22_ralston2_and_rk4_whose_errors_round_alike_keep_separate_marks(site):
    """B22: ralston2 and rk4 both round to a held-out error of 0.0919; each still gets its own mark."""
    fig = get_chart(site, RK_PAGE, "rk-frontier")
    rows = [("classical", r) for r in CLASSICAL if r["name"] in ("ralston2", "rk4")]
    assert len(rows) == 2, "data/rk.json frontier.classical should hold ralston2 and rk4"
    _, unmatched = assign(rows, marks(fig), frontier_accepts)
    assert not unmatched, (
        "no separate mark for " + ", ".join(rows[i][1]["name"] for i in unmatched) + f"\n{describe(marks(fig))}"
    )


def test_b22_discovered_rows_sharing_a_cycle_count_keep_separate_marks(site):
    """B22: discovered rows at the same cost (63 and 65 cycles, two rows each) are not merged into one mark."""
    fig = get_chart(site, RK_PAGE, "rk-frontier")
    by_cycles = {}
    for r in DISCOVERED:
        by_cycles.setdefault(r["cycles"], []).append(r)
    rows = [("discovered", r) for group in by_cycles.values() if len(group) > 1 for r in group]
    assert rows, "data/rk.json should hold discovered rows that share a cycle count"
    _, unmatched = assign(rows, marks(fig), frontier_accepts)
    missing = [f"{rows[i][1]['cycles']} cycles, error {f_sig(rows[i][1]['heldout_error'])}" for i in unmatched]
    assert not missing, "merged or missing marks for: " + "; ".join(missing) + f"\n{describe(marks(fig))}"


def test_b22_frontier_axes_are_cycles_and_log_scale_error(site):
    """B22: cycles per step on x, held-out error on y with the axis label saying "log scale"."""
    fig = get_chart(site, RK_PAGE, "rk-frontier")
    text = svg_label_text(fig)
    missing = [w for w in ("cycles", "error", "log scale") if w not in text]
    assert not missing, f"rk-frontier svg text lacks {missing}; svg text was: {text[:400]!r}"


def test_b22_frontier_legend_names_classical_and_discovered(site):
    """B22: classical and discovered are two series with a legend."""
    fig = get_chart(site, RK_PAGE, "rk-frontier")
    text = legend_text(fig)
    missing = [w for w in ("classical", "discovered") if w not in text]
    assert not missing, f"rk-frontier legend/figure text lacks {missing}: {text[:400]!r}"


def test_b22_classical_and_discovered_marks_are_not_styled_identically(site):
    """B22: the classical and discovered series are distinguishable, not one undifferentiated set of marks."""
    fig = get_chart(site, RK_PAGE, "rk-frontier")
    ms = marks(fig)
    mapping, _ = assign(FRONTIER_ROWS, ms, frontier_accepts)
    classical = [ms[ci] for ri, ci in mapping.items() if FRONTIER_ROWS[ri][0] == "classical"]
    discovered = [ms[ci] for ri, ci in mapping.items() if FRONTIER_ROWS[ri][0] == "discovered"]
    assert_styled_apart(classical, discovered, "classical", "discovered")


def test_b22_champion_has_a_direct_text_label(site):
    """B22: the champion carries a text label (svg <text> naming "champion" or its hash)."""
    fig = get_chart(site, RK_PAGE, "rk-frontier")
    text = svg_label_text(fig)
    assert "champion" in text or CHAMPION_HASH.lower() in text, (
        f"no svg <text> in rk-frontier names the champion or {CHAMPION_HASH}; svg text: {text[:400]!r}"
    )


# --------------------------------------------------------------------------
# B23: rk-counterfactual
# --------------------------------------------------------------------------


def test_b23_counterfactual_has_exactly_one_mark_per_cell(site):
    """B23: one mark per counterfactual cell (6), no more and no fewer."""
    fig = get_chart(site, RK_PAGE, "rk-counterfactual")
    ms = marks(fig)
    assert len(ms) == len(CELLS), f"rk-counterfactual has {len(ms)} marks, want {len(CELLS)}\n{describe(ms)}"


def test_b23_each_counterfactual_cell_has_its_own_mark_stating_its_ratio(site):
    """B23: every cell's ratio is stated by a distinct mark."""
    fig = get_chart(site, RK_PAGE, "rk-counterfactual")
    ms = marks(fig)
    rows = [(c["weighting"], c["basis"], c["ratio"]) for c in CELLS]
    _, unmatched = assign(rows, ms, value_accepts)
    missing = [f"{rows[i][0]} / {rows[i][1]}: {f_ratio(rows[i][2])}" for i in unmatched]
    assert not missing, "cells without a mark of their own: " + "; ".join(missing) + f"\n{describe(ms)}"


def test_b23_cell_far_below_ratio_1_is_still_plotted(site):
    """B23: the cell whose ratio sits below 1 (0.0494, champion does not lead) is drawn, not clipped away."""
    fig = get_chart(site, RK_PAGE, "rk-counterfactual")
    rows = [(c["weighting"], c["basis"], c["ratio"]) for c in CELLS if c["ratio"] < 1]
    assert rows, "data/rk.json counterfactual.cells should hold a ratio below 1"
    _, unmatched = assign(rows, marks(fig), value_accepts)
    assert not unmatched, (
        "no mark for " + "; ".join(f"{rows[i][0]} / {rows[i][1]} = {f_ratio(rows[i][2])}" for i in unmatched)
        + f"\n{describe(marks(fig))}"
    )


def test_b23_counterfactual_ratio_axis_says_log_scale(site):
    """B23: the ratio axis is log scale and its label says so."""
    fig = get_chart(site, RK_PAGE, "rk-counterfactual")
    text = svg_label_text(fig)
    missing = [w for w in ("ratio", "log scale") if w not in text]
    assert not missing, f"rk-counterfactual svg text lacks {missing}: {text[:400]!r}"


def test_b23_reference_line_at_1_reads_above_1_champion_leads(site):
    """B23: the reference line at ratio 1 is labelled so that it reads "above 1: champion leads"."""
    fig = get_chart(site, RK_PAGE, "rk-counterfactual")
    text = svg_label_text(fig)
    assert "above 1: champion leads" in text, f"no svg text reading 'above 1: champion leads': {text[:400]!r}"


# --------------------------------------------------------------------------
# B24: rk-validation-q15 and rk-validation-f64
# --------------------------------------------------------------------------


@pytest.mark.parametrize("chart_id", VALIDATION_IDS, ids=["f64", "q15"])
def test_b24_validation_chart_has_two_marks_per_problem_that_did_not_overflow(site, chart_id):
    """B24: two plotted values per problem where champion_overflowed is false (7 problems -> 14 marks);
    robertson_scaled adds none."""
    fig = get_chart(site, RK_PAGE, chart_id)
    ms = marks(fig)
    numeric = [m for m in ms if not overflow_mark(m)]
    want = len(VALIDATION_KEYS[chart_id]) * len(PLOTTED_PROBLEMS)
    assert len(numeric) == want, f"{chart_id} has {len(numeric)} marks outside robertson_scaled, want {want}\n{describe(ms)}"


@pytest.mark.parametrize("chart_id", VALIDATION_IDS, ids=["f64", "q15"])
def test_b24_each_plotted_validation_value_has_its_own_mark(site, chart_id):
    """B24: Q15 chart: champion_q15 and best_classical_q15; float64 chart: champion_float64 and rk4_float64,
    each stated by a distinct mark, for every problem that did not overflow."""
    fig = get_chart(site, RK_PAGE, chart_id)
    ms = [m for m in marks(fig) if not overflow_mark(m)]
    rows = validation_rows(chart_id)
    _, unmatched = assign(rows, ms, value_accepts)
    missing = [f"{rows[i][0]} {rows[i][1]} = {f_sig(rows[i][2])}" for i in unmatched]
    assert not missing, f"{chart_id}: values without a mark of their own:\n  " + "\n  ".join(missing) + f"\n{describe(ms)}"


def test_b24_servo_load_step_nearly_equal_q15_errors_keep_two_marks(site):
    """B24: servo_load_step's champion and best-classical Q15 errors differ only in the fourth digit; both are drawn."""
    fig = get_chart(site, RK_PAGE, "rk-validation-q15")
    rows = [r for r in validation_rows("rk-validation-q15") if r[0] == "servo_load_step"]
    assert len(rows) == 2, "data/rk.json validation should hold servo_load_step"
    _, unmatched = assign(rows, [m for m in marks(fig) if not overflow_mark(m)], value_accepts)
    assert not unmatched, (
        "servo_load_step lost a mark: " + "; ".join(f"{rows[i][1]} = {f_sig(rows[i][2], 4)}" for i in unmatched)
        + f"\n{describe(marks(fig))}"
    )


@pytest.mark.parametrize("chart_id", VALIDATION_IDS, ids=["f64", "q15"])
def test_b24_robertson_scaled_row_says_overflow_in_the_data_table(site, chart_id):
    """B24: robertson_scaled appears in the chart's data table with the word "overflow"."""
    fig = get_chart(site, RK_PAGE, chart_id)
    rows = table_rows(fig)
    hits = [r for r in rows if "robertson_scaled" in r]
    assert hits, f"{chart_id} data table has no robertson_scaled row; rows: {rows}"
    assert any("overflow" in r.lower() for r in hits), f"{chart_id}: robertson_scaled row lacks 'overflow': {hits}"


@pytest.mark.parametrize("chart_id", VALIDATION_IDS, ids=["f64", "q15"])
def test_b24_robertson_scaled_is_not_plotted_as_a_number(site, chart_id):
    """B24: robertson_scaled is not plotted as a number: any mark about it says overflow, and no mark
    states its surviving value (best classical Q15 error 0.0894 on the Q15 chart)."""
    fig = get_chart(site, RK_PAGE, chart_id)
    ms = marks(fig)
    problems = [
        f"mark about robertson_scaled without 'overflow': {title_of(m)!r}"
        for m in ms
        if overflow_mark(m) and "overflow" not in title_of(m).lower()
    ]
    keys = set(VALIDATION_KEYS[chart_id])
    if chart_id == "rk-validation-q15":
        keys |= {"best_classical_q15", "best_discovered_q15"}
    banned = set()
    for p in OVERFLOWED_PROBLEMS:
        for key in keys:
            if p[key] is not None:
                banned |= formats(p[key])
    for row in validation_rows(chart_id):
        banned -= formats(row[-1])
    for m in ms:
        hit = banned & num_tokens(title_of(m))
        if hit:
            problems.append(f"mark states robertson_scaled's value {sorted(hit)}: {title_of(m)!r}")
    assert not problems, f"{chart_id}:\n  " + "\n  ".join(problems)


@pytest.mark.parametrize("chart_id", VALIDATION_IDS, ids=["f64", "q15"])
def test_b24_no_missing_validation_value_is_rendered_as_none_nan_or_inf(site, chart_id):
    """B24: the null values of robertson_scaled never leak into a mark title, svg label or table cell as None/nan/inf/null."""
    fig = get_chart(site, RK_PAGE, chart_id)
    leak = re.compile(r"\b(?:None|nan|NaN|null|inf|Infinity|undefined)\b")
    texts = [("mark title", title_of(m)) for m in marks(fig)]
    texts += [("svg text", n.text(skip=("title",))) for n in svg_nodes(fig) if n.tag == "text"]
    texts += [("table row", r) for r in table_rows(fig)]
    bad = [f"{kind}: {norm(t)!r}" for kind, t in texts if leak.search(t)]
    assert not bad, f"{chart_id}:\n  " + "\n  ".join(bad)


@pytest.mark.parametrize("chart_id", VALIDATION_IDS, ids=["f64", "q15"])
def test_b24_validation_chart_says_log_scale_because_values_span_over_two_decades(site, chart_id):
    """B24 with the chart rules: plotted values span more than two decades, so the axis label says "log scale"."""
    values = [row[-1] for row in validation_rows(chart_id)]
    assert max(values) / min(values) > 100, "precondition: plotted values span more than two decades"
    fig = get_chart(site, RK_PAGE, chart_id)
    text = svg_label_text(fig)
    assert "log scale" in text, f"{chart_id} spans {max(values) / min(values):.0f}x but no axis label says 'log scale': {text[:400]!r}"


# --------------------------------------------------------------------------
# B25: rk-floor-round
# --------------------------------------------------------------------------


def test_b25_floor_round_has_exactly_one_mark_per_method_and_mode(site):
    """B25: four methods under two rounding modes give exactly 8 marks."""
    fig = get_chart(site, RK_PAGE, "rk-floor-round")
    ms = marks(fig)
    assert len(ms) == len(FLOOR_ROUND_ROWS), f"rk-floor-round has {len(ms)} marks, want {len(FLOOR_ROUND_ROWS)}\n{describe(ms)}"


def test_b25_each_method_and_mode_has_its_own_mark_stating_search_rms(site):
    """B25: each (rounding mode, method) search_rms value is a distinct mark naming the method."""
    fig = get_chart(site, RK_PAGE, "rk-floor-round")
    ms = marks(fig)
    _, unmatched = assign(FLOOR_ROUND_ROWS, ms, floor_round_accepts)
    missing = [f"{FLOOR_ROUND_ROWS[i][0]} {FLOOR_ROUND_ROWS[i][1]} = {f_sig(FLOOR_ROUND_ROWS[i][2])}" for i in unmatched]
    assert not missing, "without a mark of their own: " + "; ".join(missing) + f"\n{describe(ms)}"


def test_b25_heldout_rms_is_not_plotted_in_place_of_search_rms(site):
    """B25: the chart plots search_rms; no mark states only a heldout_rms value."""
    fig = get_chart(site, RK_PAGE, "rk-floor-round")
    search_forms = set().union(*(formats(v) for mode in SEARCH_RMS.values() for v in mode.values()))
    heldout_only = set().union(*(formats(v) for mode in HELDOUT_RMS.values() for v in mode.values())) - search_forms
    bad = []
    for m in marks(fig):
        toks = num_tokens(title_of(m))
        if toks & heldout_only and not toks & search_forms:
            bad.append(title_of(m))
    assert not bad, "marks stating held-out RMS instead of search RMS: " + "; ".join(repr(t) for t in bad)


def test_b25_legend_names_floor_and_round(site):
    """B25: the two rounding modes are two series with a legend naming them."""
    fig = get_chart(site, RK_PAGE, "rk-floor-round")
    text = legend_text(fig)
    missing = [w for w in ("floor", "round") if w not in text]
    assert not missing, f"rk-floor-round legend/figure text lacks {missing}: {text[:400]!r}"


def test_b25_rounding_modes_are_not_styled_identically(site):
    """B25: floor and round-to-nearest marks are distinguishable as two series."""
    fig = get_chart(site, RK_PAGE, "rk-floor-round")
    ms = marks(fig)
    mapping, _ = assign(FLOOR_ROUND_ROWS, ms, floor_round_accepts)
    modes = sorted(SEARCH_RMS)
    groups = {mode: [ms[ci] for ri, ci in mapping.items() if FLOOR_ROUND_ROWS[ri][0] == mode] for mode in modes}
    assert_styled_apart(groups[modes[0]], groups[modes[1]], modes[0], modes[1])


# --------------------------------------------------------------------------
# B26: rk-archive-growth
# --------------------------------------------------------------------------


def test_b26_archive_growth_has_exactly_one_mark_per_archive_day(site):
    """B26: one mark per archive day: 13 epoch-1 days + 2 epoch-2 days = 15 marks."""
    fig = get_chart(site, RK_PAGE, "rk-archive-growth")
    ms = marks(fig)
    assert len(ms) == len(ARCHIVE_ROWS), (
        f"rk-archive-growth has {len(ms)} marks, want {len(EPOCH1_DAYS)} + {len(EPOCH2_DAYS)} = {len(ARCHIVE_ROWS)}\n{describe(ms)}"
    )


def test_b26_each_archive_day_mark_states_its_day_and_cumulative_records(site):
    """B26: every archive day has a distinct mark whose title gives the day and the cumulative record count."""
    fig = get_chart(site, RK_PAGE, "rk-archive-growth")
    ms = marks(fig)
    _, unmatched = assign(ARCHIVE_ROWS, ms, archive_accepts)
    missing = [f"epoch {ARCHIVE_ROWS[i][0]} {ARCHIVE_ROWS[i][1]['day']}: {f_count(ARCHIVE_ROWS[i][1]['cumulative'])}" for i in unmatched]
    assert not missing, "days without a mark of their own:\n  " + "\n  ".join(missing) + f"\n{describe(ms)}"


def test_b26_no_mark_for_a_day_without_archive_records(site):
    """B26: marks exist only for archive days; the stopped days between 2026-09-17 and 2026-09-23 get none."""
    fig = get_chart(site, RK_PAGE, "rk-archive-growth")
    days = {d["day"] for _, d in ARCHIVE_ROWS}
    bad = []
    for m in marks(fig):
        for date in re.findall(r"\d{4}-\d{2}-\d{2}", title_of(m)):
            if date not in days:
                bad.append(f"{date}: {title_of(m)!r}")
    assert not bad, "marks for days with no archive records:\n  " + "\n  ".join(bad)


def test_b26_epoch_2_counts_restart_rather_than_continue_epoch_1(site):
    """B26: epoch 1 and epoch 2 are separate series; no mark states epoch 1's total plus an epoch-2 count."""
    fig = get_chart(site, RK_PAGE, "rk-archive-growth")
    e1_total = max(d["cumulative"] for d in EPOCH1_DAYS)
    wrong = set().union(*(formats(e1_total + d["cumulative"]) for d in EPOCH2_DAYS))
    bad = [title_of(m) for m in marks(fig) if wrong & num_tokens(title_of(m))]
    assert not bad, "marks that carry epoch 1's total into epoch 2: " + "; ".join(repr(t) for t in bad)


def test_b26_legend_names_epoch_1_and_epoch_2(site):
    """B26: epoch 1 and epoch 2 are separate series with a legend naming them."""
    fig = get_chart(site, RK_PAGE, "rk-archive-growth")
    text = legend_text(fig)
    missing = [w for w in ("epoch 1", "epoch 2") if w not in text]
    assert not missing, f"rk-archive-growth legend/figure text lacks {missing}: {text[:400]!r}"


def test_b26_epoch_1_and_epoch_2_marks_are_not_styled_identically(site):
    """B26: the two epochs are distinguishable as separate series."""
    fig = get_chart(site, RK_PAGE, "rk-archive-growth")
    ms = marks(fig)
    mapping, _ = assign(ARCHIVE_ROWS, ms, archive_accepts)
    e1 = [ms[ci] for ri, ci in mapping.items() if ARCHIVE_ROWS[ri][0] == 1]
    e2 = [ms[ci] for ri, ci in mapping.items() if ARCHIVE_ROWS[ri][0] == 2]
    assert_styled_apart(e1, e2, "epoch 1", "epoch 2")


def test_b26_archive_growth_says_log_scale_because_counts_span_over_two_decades(site):
    """B26 with the chart rules: cumulative records run from 22 to 141,364 (over two decades), so the axis label says "log scale"."""
    values = [d["cumulative"] for _, d in ARCHIVE_ROWS]
    assert max(values) / min(values) > 100, "precondition: cumulative records span more than two decades"
    fig = get_chart(site, RK_PAGE, "rk-archive-growth")
    text = svg_label_text(fig)
    assert "log scale" in text, f"rk-archive-growth spans {max(values) / min(values):.0f}x but no axis label says 'log scale': {text[:400]!r}"
