"""Chart rules that hold on every page.

B19: every <figure class="chart"> has the figure / svg / title / desc / figcaption / data-table
structure from the spec's "Chart rules", and every .mark has a <title> child.
B20: no inline <svg> on any page carries a literal color.

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
    out = tmp_path_factory.mktemp("site_charts_common")
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


def css_value(style, prop):
    """Last value of `prop` in an inline style string, or None."""
    found = None
    for decl in (style or "").split(";"):
        if ":" in decl:
            key, val = decl.split(":", 1)
            if key.strip().lower() == prop:
                found = val.strip()
    return found


def css_decls(text):
    """(property, value) pairs from a style attribute or the body of a <style> element."""
    out = []
    for block in re.split(r"[{}]", text or ""):
        for decl in block.split(";"):
            if ":" in decl:
                key, val = decl.split(":", 1)
                key = key.strip().lower()
                if re.fullmatch(r"[a-z-]+", key):
                    out.append((key, val.strip()))
    return out


def inherited(node, prop):
    """Nearest explicit value of a presentation property (inline style wins over the attribute),
    looking at the node and its ancestors up to the enclosing <svg>."""
    n = node
    while n is not None:
        val = css_value(n.attrs.get("style"), prop)
        if val is None:
            val = n.attrs.get(prop)
        if val is not None and val.strip():
            return val.strip()
        if n.tag == "svg":
            return None
        n = n.parent
    return None


# --------------------------------------------------------------------------
# Module fixtures and constants
# --------------------------------------------------------------------------

PAGES = ["index.html", "rk.html", "novel.html", "architecture.html", "epochs.html", "claims.html", "repos.html"]
NO_CHARTS = 'no <figure class="chart"> on any page, so there is nothing to check'
NO_SVG = "no inline <svg> on any page, so there is nothing to check"

COLOR_ATTRS = ("fill", "stroke", "stop-color", "flood-color", "lighting-color", "color")
HEX = re.compile(r"#(?:[0-9a-f]{8}|[0-9a-f]{6}|[0-9a-f]{3,4})(?![0-9a-z_-])", re.I)
URL_REF = re.compile(r"url\([^)]*\)", re.I)
RGB_HSL = re.compile(r"\b(?:rgba?|hsla?)\s*\(", re.I)

# The CSS named colors (CSS Color 4). "transparent", "inherit", "none" and "currentColor" are not in it.
NAMED_COLORS = frozenset(
    """aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue blueviolet
    brown burlywood cadetblue chartreuse chocolate coral cornflowerblue cornsilk crimson cyan darkblue
    darkcyan darkgoldenrod darkgray darkgreen darkgrey darkkhaki darkmagenta darkolivegreen darkorange
    darkorchid darkred darksalmon darkseagreen darkslateblue darkslategray darkslategrey darkturquoise
    darkviolet deeppink deepskyblue dimgray dimgrey dodgerblue firebrick floralwhite forestgreen fuchsia
    gainsboro ghostwhite gold goldenrod gray green greenyellow grey honeydew hotpink indianred indigo
    ivory khaki lavender lavenderblush lawngreen lemonchiffon lightblue lightcoral lightcyan
    lightgoldenrodyellow lightgray lightgreen lightgrey lightpink lightsalmon lightseagreen lightskyblue
    lightslategray lightslategrey lightsteelblue lightyellow lime limegreen linen magenta maroon
    mediumaquamarine mediumblue mediumorchid mediumpurple mediumseagreen mediumslateblue
    mediumspringgreen mediumturquoise mediumvioletred midnightblue mintcream mistyrose moccasin
    navajowhite navy oldlace olive olivedrab orange orangered orchid palegoldenrod palegreen
    paleturquoise palevioletred papayawhip peachpuff peru pink plum powderblue purple rebeccapurple red
    rosybrown royalblue saddlebrown salmon sandybrown seagreen seashell sienna silver skyblue slateblue
    slategray slategrey snow springgreen steelblue tan teal thistle tomato turquoise violet wheat white
    whitesmoke yellow yellowgreen""".split()
)


def is_named_color(value):
    v = value.strip().lower()
    if v.endswith("!important"):
        v = v[: -len("!important")].strip()
    return v in NAMED_COLORS


@pytest.fixture(scope="module")
def charts(site):
    found = []
    for slug in PAGES:
        for node in site.page(slug).iter():
            if node.tag == "figure" and "chart" in node.classes():
                found.append((slug, node))
    return found


@pytest.fixture(scope="module")
def page_svg_nodes(site):
    """(slug, element) for every element inside an inline <svg> on any of the seven pages."""
    out = []
    for slug in PAGES:
        for node in svg_nodes(site.page(slug)):
            out.append((slug, node))
    return out


def where(slug, fig):
    return f"{slug}#{fig.attrs.get('id') or '<figure.chart without id>'}"


def first_svg(fig):
    for node in fig.iter():
        if node.tag == "svg":
            return node
    return None


def data_details(fig):
    for node in fig.iter():
        if node.tag == "details" and "data" in node.classes():
            return node
    return None


def style_texts(slug_nodes):
    """(slug, css text) for every style attribute and <style> element inside the svgs."""
    out = []
    for slug, node in slug_nodes:
        if node.attrs.get("style"):
            out.append((slug, node.attrs["style"]))
        if node.tag == "style":
            out.append((slug, node.text()))
    return out


# --------------------------------------------------------------------------
# B19: chart structure
# --------------------------------------------------------------------------


def test_b19_chart_svg_is_inline_with_role_img_viewbox_720_and_aria_labelledby(charts):
    """B19: each chart figure has an id and an inline <svg role="img" viewBox="0 0 720 H"
    aria-labelledby="<id>-title <id>-desc">."""
    assert charts, NO_CHARTS
    problems = []
    for slug, fig in charts:
        cid = fig.attrs.get("id", "")
        if not cid:
            problems.append(f"{slug}: a figure.chart has no id")
            continue
        svg = first_svg(fig)
        if svg is None:
            problems.append(f"{where(slug, fig)}: no inline <svg> in the figure")
            continue
        if svg.attrs.get("role") != "img":
            problems.append(f"{where(slug, fig)}: svg role={svg.attrs.get('role')!r}, want 'img'")
        box = svg.attrs.get("viewbox", "").replace(",", " ").split()
        try:
            nums = [float(v) for v in box]
        except ValueError:
            nums = []
        if len(nums) != 4 or nums[:3] != [0.0, 0.0, 720.0] or nums[3] <= 0:
            problems.append(f"{where(slug, fig)}: viewBox={svg.attrs.get('viewbox')!r}, want '0 0 720 H'")
        labelled = svg.attrs.get("aria-labelledby", "").split()
        if labelled != [f"{cid}-title", f"{cid}-desc"]:
            problems.append(
                f"{where(slug, fig)}: aria-labelledby={svg.attrs.get('aria-labelledby')!r}, "
                f"want '{cid}-title {cid}-desc'"
            )
    assert not problems, "\n".join(problems)


def test_b19_chart_svg_has_title_and_desc_carrying_the_chart_ids(charts):
    """B19: the svg holds exactly one <title id="<id>-title"> and one <desc id="<id>-desc">, both non-empty."""
    assert charts, NO_CHARTS
    problems = []
    for slug, fig in charts:
        cid = fig.attrs.get("id", "")
        svg = first_svg(fig)
        if not cid or svg is None:
            problems.append(f"{where(slug, fig)}: no id or no svg, so no title/desc to find")
            continue
        for tag in ("title", "desc"):
            want = f"{cid}-{tag}"
            hits = [n for n in svg.iter() if n.tag == tag and n.attrs.get("id") == want]
            if len(hits) != 1:
                problems.append(f"{where(slug, fig)}: want one <{tag} id=\"{want}\"> in the svg, found {len(hits)}")
            elif not norm(hits[0].text()):
                problems.append(f"{where(slug, fig)}: <{tag} id=\"{want}\"> is empty")
    assert not problems, "\n".join(problems)


def test_b19_chart_has_a_figcaption_after_the_svg_and_before_the_data_table(charts):
    """B19: a non-empty <figcaption> follows the svg and precedes the <details class="data">."""
    assert charts, NO_CHARTS
    problems = []
    for slug, fig in charts:
        order = {id(n): i for i, n in enumerate(fig.iter())}
        caps = [n for n in fig.iter() if n.tag == "figcaption"]
        if not caps:
            problems.append(f"{where(slug, fig)}: no <figcaption>")
            continue
        cap = caps[0]
        if not norm(cap.text()):
            problems.append(f"{where(slug, fig)}: <figcaption> is empty")
        svg = first_svg(fig)
        if svg is not None and order[id(cap)] < order[id(svg)]:
            problems.append(f"{where(slug, fig)}: <figcaption> comes before the svg")
        det = data_details(fig)
        if det is not None and order[id(cap)] > order[id(det)]:
            problems.append(f"{where(slug, fig)}: <figcaption> comes after the data table")
    assert not problems, "\n".join(problems)


def test_b19_chart_has_a_details_data_table_with_summary_and_rows(charts):
    """B19: <details class="data"><summary>Data table</summary><table> with at least one data row."""
    assert charts, NO_CHARTS
    problems = []
    for slug, fig in charts:
        det = data_details(fig)
        if det is None:
            problems.append(f'{where(slug, fig)}: no <details class="data">')
            continue
        summaries = [c for c in det.children if isinstance(c, Node) and c.tag == "summary"]
        if not summaries or norm(summaries[0].text()) != "Data table":
            got = norm(summaries[0].text()) if summaries else None
            problems.append(f"{where(slug, fig)}: details summary is {got!r}, want 'Data table'")
        tables = [n for n in det.iter() if n.tag == "table"]
        if not tables:
            problems.append(f"{where(slug, fig)}: the data details holds no <table>")
            continue
        rows = [
            tr
            for tr in tables[0].iter()
            if tr.tag == "tr" and any(isinstance(c, Node) and c.tag == "td" for c in tr.children)
        ]
        if not rows:
            problems.append(f"{where(slug, fig)}: the data table has no row with a <td>")
    assert not problems, "\n".join(problems)


def test_b19_no_mark_lacks_a_title_child(charts):
    """B19: no element with class "mark" in a chart svg is missing a non-empty <title> child."""
    assert charts, NO_CHARTS
    total = 0
    problems = []
    for slug, fig in charts:
        for m in marks(fig):
            total += 1
            if not title_of(m):
                problems.append(f"{where(slug, fig)}: <{m.tag} class={m.attrs.get('class')!r}> has no <title> child with text")
    assert total, 'no element with class "mark" in any chart svg'
    assert not problems, "\n".join(problems[:40])


def test_b19_no_mark_is_anything_but_a_circle_rect_or_path(charts):
    """B19 (chart rules): every data mark is a <circle>, <rect> or <path>; class="mark" on anything else is wrong."""
    assert charts, NO_CHARTS
    total = 0
    problems = []
    for slug, fig in charts:
        for m in marks(fig):
            total += 1
            if m.tag not in ("circle", "rect", "path"):
                problems.append(f'{where(slug, fig)}: class="mark" on <{m.tag}> ({title_of(m)!r})')
    assert total, 'no element with class "mark" in any chart svg'
    assert not problems, "\n".join(problems[:40])


def test_b19_no_chart_uses_series_4_or_skips_a_series_slot(charts):
    """B19 (chart rules): series slots are used in order 1, 2, 3 and never more than three per chart."""
    assert charts, NO_CHARTS
    slot = re.compile(r"--series-(\d+)")
    problems = []
    for slug, fig in charts:
        used = set()
        for n in svg_nodes(fig):
            for val in n.attrs.values():
                used.update(int(x) for x in slot.findall(val))
            if n.tag == "style":
                used.update(int(x) for x in slot.findall(n.text()))
        if used - {1, 2, 3}:
            problems.append(f"{where(slug, fig)}: uses series slots {sorted(used)}; at most 1, 2, 3 allowed")
        elif used and used != set(range(1, max(used) + 1)):
            problems.append(f"{where(slug, fig)}: uses series slots {sorted(used)}; slots must be taken in order from 1")
    assert not problems, "\n".join(problems)


def test_b19_no_chart_text_has_an_off_token_fill_or_a_font_size_other_than_12_or_13(charts):
    """B19 (chart rules): svg text uses fill currentColor or a text token, font-size 12 or 13, wherever set inline."""
    assert charts, NO_CHARTS
    checked = 0
    problems = []
    for slug, fig in charts:
        for n in svg_nodes(fig):
            if n.tag not in ("text", "tspan"):
                continue
            checked += 1
            label = norm(n.text())[:40]
            size = inherited(n, "font-size")
            if size is not None:
                try:
                    px = float(size.lower().removesuffix("px").strip())
                except ValueError:
                    px = None
                if px not in (12.0, 13.0):
                    problems.append(f"{where(slug, fig)}: <{n.tag}> {label!r} has font-size {size!r}, want 12 or 13")
            fill = inherited(n, "fill")
            if fill is not None:
                compact = fill.lower().replace(" ", "")
                if not compact.startswith(("currentcolor", "var(--text-1", "var(--text-2")):
                    problems.append(f"{where(slug, fig)}: <{n.tag}> {label!r} has fill {fill!r}, want currentColor or a text token")
    assert checked, "no <text> in any chart svg (axis labels are text)"
    assert not problems, "\n".join(problems[:40])


# --------------------------------------------------------------------------
# B20: no literal colors inside any svg on any page
# --------------------------------------------------------------------------


def test_b20_no_svg_color_attribute_holds_a_hex_color(page_svg_nodes):
    """B20: no fill/stroke/stop-color/... attribute inside an svg holds a hex color."""
    assert page_svg_nodes, NO_SVG
    problems = []
    for slug, n in page_svg_nodes:
        for attr in COLOR_ATTRS:
            val = n.attrs.get(attr)
            if val and HEX.search(URL_REF.sub(" ", val)):
                problems.append(f"{slug}: <{n.tag} {attr}={val!r}>")
    assert not problems, "\n".join(problems[:40])


def test_b20_no_svg_inline_style_or_style_element_holds_a_hex_color(page_svg_nodes):
    """B20: no style attribute or <style> element inside an svg declares a hex color."""
    assert page_svg_nodes, NO_SVG
    problems = []
    for slug, css in style_texts(page_svg_nodes):
        for prop, val in css_decls(css):
            if HEX.search(URL_REF.sub(" ", val)):
                problems.append(f"{slug}: {prop}: {val}")
    assert not problems, "\n".join(problems[:40])


def test_b20_no_svg_uses_rgb_or_hsl(page_svg_nodes):
    """B20: no attribute value, style attribute or <style> element inside an svg contains rgb( or hsl( (or rgba/hsla)."""
    assert page_svg_nodes, NO_SVG
    problems = []
    for slug, n in page_svg_nodes:
        for attr, val in n.attrs.items():
            if RGB_HSL.search(val or ""):
                problems.append(f"{slug}: <{n.tag} {attr}={val!r}>")
        if n.tag == "style" and RGB_HSL.search(n.text()):
            problems.append(f"{slug}: <style> inside an svg uses rgb()/hsl()")
    assert not problems, "\n".join(problems[:40])


def test_b20_no_svg_fill_or_stroke_attribute_is_a_named_color(page_svg_nodes):
    """B20: fill= and stroke= inside an svg are none, currentColor or var(--...), never a named color."""
    assert page_svg_nodes, NO_SVG
    problems = []
    for slug, n in page_svg_nodes:
        for attr in ("fill", "stroke"):
            val = n.attrs.get(attr)
            if val and is_named_color(val):
                problems.append(f"{slug}: <{n.tag} {attr}={val!r}>")
    assert not problems, "\n".join(problems[:40])


def test_b20_no_svg_fill_or_stroke_declaration_is_a_named_color(page_svg_nodes):
    """B20: fill/stroke declared in a style attribute or <style> element inside an svg is never a named color."""
    assert page_svg_nodes, NO_SVG
    problems = []
    for slug, css in style_texts(page_svg_nodes):
        for prop, val in css_decls(css):
            if prop in ("fill", "stroke") and is_named_color(val):
                problems.append(f"{slug}: {prop}: {val}")
    assert not problems, "\n".join(problems[:40])
