"""Charts on novel.html: B27 (novel-benchmark, novel-runtime, novel-metrics-log) and
B28 (the novel-benchmark data table).

Expected marks, rows and values come from data/novel.json. A mark or cell "states a value" when
it contains the value in one of the forms web/fmt.py can produce (sig / ratio at 2, 3 or 4
digits, count, or the plain integer), which is the B9 set of renderings.

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
    out = tmp_path_factory.mktemp("site_charts_novel")
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
# Expectations from data/novel.json
# --------------------------------------------------------------------------

NOVEL_PAGE = "novel.html"
NOVEL_CHART_IDS = ["novel-benchmark", "novel-runtime", "novel-metrics-log"]

BENCH_ROWS = NOVEL["benchmark"]["rows"]
GL3 = next(r for r in BENCH_ROWS if r["label"] == "Gauss-Legendre 3")
GL3_SHOWN = "8.31e+211"  # the value B27 names; equals f_sig(GL3["mean_max_error"]) at 3 digits
LEAK = re.compile(r"\b(?:None|nan|NaN|null|inf|Infinity|undefined)\b")


def bench_mark_accepts(row, mark):
    title = title_of(mark)
    return has_words(title, row["label"]) and states(title, row["mean_max_error"])


def bench_table_accepts(row, text):
    toks = num_tokens(text)
    return (
        has_words(text, row["label"])
        and str(int(row["stages"])) in toks
        and bool(formats(row["mean_max_error"]) & toks)
        and bool(formats(row["runtime_s"]) & toks)
    )


def identical_error_rows():
    """Benchmark rows whose mean max error equals another row's (RK4 = Trials 12, 14, 15; Dormand-Prince = Trial 13; Trial 8 = Trial 9)."""
    groups = {}
    for r in BENCH_ROWS:
        groups.setdefault(r["mean_max_error"], []).append(r)
    return [r for g in groups.values() if len(g) > 1 for r in g]


# --------------------------------------------------------------------------
# B27: figures
# --------------------------------------------------------------------------


def test_b27_novel_page_has_the_three_chart_figures(site):
    """B27: novel.html has <figure class="chart"> with ids novel-benchmark, novel-runtime and novel-metrics-log."""
    root = site.page(NOVEL_PAGE)
    problems = []
    for cid in NOVEL_CHART_IDS:
        node = find_id(root, cid)
        if node is None:
            problems.append(f"no element with id={cid!r}")
        elif node.tag != "figure":
            problems.append(f"id={cid!r} is on <{node.tag}>, want <figure>")
        elif "chart" not in node.classes():
            problems.append(f"figure#{cid} has class={node.attrs.get('class')!r}, want it to include 'chart'")
    assert not problems, "\n".join(problems)


# --------------------------------------------------------------------------
# B27: novel-benchmark
# --------------------------------------------------------------------------


def test_b27_benchmark_has_exactly_one_mark_per_benchmark_row(site):
    """B27: mean max error is plotted per benchmark row: 12 rows, 12 marks (Gauss-Legendre 3's off-scale marker included)."""
    fig = get_chart(site, NOVEL_PAGE, "novel-benchmark")
    ms = marks(fig)
    assert len(ms) == len(BENCH_ROWS), f"novel-benchmark has {len(ms)} marks, want {len(BENCH_ROWS)}\n{describe(ms)}"


def test_b27_each_benchmark_row_has_its_own_mark_stating_label_and_error(site):
    """B27: every benchmark row has a distinct mark whose title gives its label and mean max error."""
    fig = get_chart(site, NOVEL_PAGE, "novel-benchmark")
    ms = marks(fig)
    _, unmatched = assign(BENCH_ROWS, ms, bench_mark_accepts)
    missing = [f"{BENCH_ROWS[i]['label']}: {f_sig(BENCH_ROWS[i]['mean_max_error'])}" for i in unmatched]
    assert not missing, "rows without a mark of their own: " + "; ".join(missing) + f"\n{describe(ms)}"


def test_b27_rows_with_identical_errors_keep_separate_marks(site):
    """B27: rows that share an error (RK4 with Trials 12, 14, 15; Dormand-Prince with Trial 13; Trials 8 and 9)
    are each drawn, not collapsed into one mark."""
    fig = get_chart(site, NOVEL_PAGE, "novel-benchmark")
    rows = identical_error_rows()
    assert rows, "data/novel.json should hold benchmark rows with identical errors"
    _, unmatched = assign(rows, marks(fig), bench_mark_accepts)
    assert not unmatched, "collapsed or missing marks for: " + ", ".join(rows[i]["label"] for i in unmatched) + f"\n{describe(marks(fig))}"


def test_b27_benchmark_axis_says_log_scale(site):
    """B27: novel-benchmark plots mean max error on a log scale and its axis label says so."""
    fig = get_chart(site, NOVEL_PAGE, "novel-benchmark")
    text = svg_label_text(fig)
    assert "log scale" in text, f"no novel-benchmark axis label says 'log scale': {text[:400]!r}"


def test_b27_benchmark_legend_names_baselines_and_trials(site):
    """B27: baselines and trial entries are separate series with a legend."""
    fig = get_chart(site, NOVEL_PAGE, "novel-benchmark")
    text = legend_text(fig)
    missing = [w for w in ("baseline", "trial") if w not in text]
    assert not missing, f"novel-benchmark legend/figure text lacks {missing}: {text[:400]!r}"


def test_b27_baseline_and_trial_marks_are_not_styled_identically(site):
    """B27: baseline marks and trial marks are distinguishable as two series."""
    fig = get_chart(site, NOVEL_PAGE, "novel-benchmark")
    ms = marks(fig)
    mapping, _ = assign(BENCH_ROWS, ms, bench_mark_accepts)
    baselines = [ms[ci] for ri, ci in mapping.items() if BENCH_ROWS[ri]["baseline"]]
    trials = [ms[ci] for ri, ci in mapping.items() if not BENCH_ROWS[ri]["baseline"]]
    assert_styled_apart(baselines, trials, "baseline", "trial")


def test_b27_gauss_legendre_3_shows_its_value_and_is_called_an_artifact(site):
    """B27: the Gauss-Legendre 3 marker carries its value 8.31e+211 in the svg, and the caption or table says "artifact"."""
    assert f_sig(GL3["mean_max_error"]) == GL3_SHOWN, "precondition: fmt.sig renders Gauss-Legendre 3 as 8.31e+211"
    fig = get_chart(site, NOVEL_PAGE, "novel-benchmark")
    svg_all = " ".join(norm(n.text()) for n in svg_nodes(fig) if n.tag == "svg")
    assert GL3_SHOWN in svg_all, f"novel-benchmark svg never shows {GL3_SHOWN}"
    caption = " ".join(norm(n.text()) for n in fig.iter() if n.tag == "figcaption")
    table = " ".join(table_rows(fig))
    assert "artifact" in (caption + " " + table).lower(), "neither the figcaption nor the data table says 'artifact'"


def test_b27_gauss_legendre_3_is_not_drawn_to_scale(site):
    """B27: Gauss-Legendre 3 is an off-scale marker, so no axis or label text reaches toward 1e+211.
    Every other row is at most 5,577; a text value over a million times that, other than
    Gauss-Legendre 3's own value, means the axis was stretched to fit it."""
    fig = get_chart(site, NOVEL_PAGE, "novel-benchmark")
    gl3 = GL3["mean_max_error"]
    limit = max(r["mean_max_error"] for r in BENCH_ROWS if r is not GL3) * 1e6
    stretched = []
    for tok in num_tokens(svg_label_text(fig)):
        value = float(tok.rstrip("x%").replace(",", ""))
        if value > limit and abs(value - gl3) > 0.01 * gl3:
            stretched.append(tok)
    assert not stretched, f"novel-benchmark axis text shows {sorted(stretched)}: the chart is drawn to Gauss-Legendre 3's scale"


def test_b27_benchmark_marks_never_show_inf_or_nan(site):
    """B27: Gauss-Legendre 3's huge value is shown as a number, never as inf/nan/None in a mark or svg label."""
    fig = get_chart(site, NOVEL_PAGE, "novel-benchmark")
    texts = [title_of(m) for m in marks(fig)]
    texts += [norm(n.text(skip=("title",))) for n in svg_nodes(fig) if n.tag == "text"]
    bad = [t for t in texts if LEAK.search(t)]
    assert not bad, "novel-benchmark shows inf/nan/None: " + "; ".join(repr(t) for t in bad)


# --------------------------------------------------------------------------
# B27: novel-metrics-log
# --------------------------------------------------------------------------


def test_b27_metrics_log_says_log_scale_and_names_the_median_series(site):
    """B27: novel-metrics-log plots min and median of max_error per epoch on a log scale (two series, legend)."""
    fig = get_chart(site, NOVEL_PAGE, "novel-metrics-log")
    ms = marks(fig)
    assert len(ms) >= 2, f"novel-metrics-log has {len(ms)} marks; two series need at least two\n{describe(ms)}"
    text = svg_label_text(fig)
    assert "log scale" in text, f"no novel-metrics-log axis label says 'log scale': {text[:400]!r}"
    assert "median" in legend_text(fig), "novel-metrics-log legend/figure text never names the median series"


def test_b27_metrics_log_min_and_median_marks_are_not_styled_identically(site):
    """B27: the min and median series are distinguishable (marks titled with "median" versus the rest)."""
    fig = get_chart(site, NOVEL_PAGE, "novel-metrics-log")
    ms = marks(fig)
    median = [m for m in ms if "median" in title_of(m).lower()]
    minimum = [m for m in ms if "median" not in title_of(m).lower()]
    assert_styled_apart(minimum, median, "min", "median")


# --------------------------------------------------------------------------
# B28: the novel-benchmark data table
# --------------------------------------------------------------------------


def test_b28_benchmark_table_has_every_row_with_label_stages_error_and_runtime(site):
    """B28: all 12 benchmark rows appear in the data table, each with label, stages, mean max error and runtime."""
    fig = get_chart(site, NOVEL_PAGE, "novel-benchmark")
    rows = table_rows(fig)
    _, unmatched = assign(BENCH_ROWS, rows, bench_table_accepts)
    missing = [
        f"{BENCH_ROWS[i]['label']} (stages {BENCH_ROWS[i]['stages']}, error {f_sig(BENCH_ROWS[i]['mean_max_error'])}, "
        f"runtime {f_sig(BENCH_ROWS[i]['runtime_s'])})"
        for i in unmatched
    ]
    assert not missing, "table rows missing or incomplete:\n  " + "\n  ".join(missing) + "\ntable:\n  " + "\n  ".join(rows)


def test_b28_rows_with_identical_errors_are_not_merged_in_the_table(site):
    """B28: rows that share an error value (RK4 and Trials 12, 14, 15; Dormand-Prince and Trial 13; Trials 8 and 9) each keep a row."""
    fig = get_chart(site, NOVEL_PAGE, "novel-benchmark")
    rows = identical_error_rows()
    assert rows, "data/novel.json should hold benchmark rows with identical errors"
    table = table_rows(fig)
    _, unmatched = assign(rows, table, lambda r, text: has_words(text, r["label"]) and states(text, r["mean_max_error"]))
    assert not unmatched, "merged or missing table rows: " + ", ".join(rows[i]["label"] for i in unmatched) + "\ntable:\n  " + "\n  ".join(table)


def test_b28_gauss_legendre_3_row_keeps_its_real_value(site):
    """B28: the Gauss-Legendre 3 row states its mean max error (8.31e+211), not a clipped or placeholder value."""
    fig = get_chart(site, NOVEL_PAGE, "novel-benchmark")
    rows = [r for r in table_rows(fig) if has_words(r, GL3["label"])]
    assert rows, "no Gauss-Legendre 3 row in the novel-benchmark data table"
    assert any(states(r, GL3["mean_max_error"]) for r in rows), f"Gauss-Legendre 3 row does not state 8.31e+211: {rows}"


def test_b28_no_benchmark_table_cell_reads_inf_nan_or_none(site):
    """B28: no cell in the benchmark data table is rendered as inf, nan, None or null."""
    fig = get_chart(site, NOVEL_PAGE, "novel-benchmark")
    bad = [r for r in table_rows(fig) if LEAK.search(r)]
    assert not bad, "table rows with inf/nan/None: " + "; ".join(repr(r) for r in bad)
