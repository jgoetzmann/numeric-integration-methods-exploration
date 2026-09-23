"""SVG chart primitives shared by every page: scales, ticks, axes, legend, marks, figure.

Deterministic: no clock reads, no randomness, data order or sorted order only.
Page SVGs paint only through CSS custom properties (var(--series-N), var(--grid),
var(--text-2)) and currentColor. The standalone copies carry a <style> block
with the light-theme values, because they are viewed outside the site's
stylesheet (the README embeds them).
"""

import math

from web.fmt import esc

W = 720
CHAR_W = 6.8  # rough width of one character at font-size 12

_STANDALONE_STYLE = (
    "<style>"
    "svg{--series-1:#2a78d6;--series-2:#eb6834;--series-3:#1baf7a;--series-4:#eda100;"
    "--surface:#fcfcfb;--text-1:#0b0b0b;--text-2:#52514e;--grid:#e4e3df;"
    "color:#0b0b0b;font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif}"
    ".rk-bg{fill:#fcfcfb}"
    ".rk-s1{fill:#2a78d6}.rk-s2{fill:#eb6834}.rk-s3{fill:#1baf7a}"
    ".rk-l1{stroke:#2a78d6;fill:none}.rk-l2{stroke:#eb6834;fill:none}.rk-l3{stroke:#1baf7a;fill:none}"
    ".rk-grid,.rk-connector{stroke:#e4e3df}"
    ".rk-axis,.rk-ref{stroke:#52514e}"
    ".rk-muted{fill:#52514e}"
    ".rk-band{fill:#e4e3df}"
    "</style>"
)


def table(headers, rows, caption=None):
    cap = f"<caption>{caption}</caption>" if caption else ""
    head = "".join(f'<th scope="col">{h}</th>' for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return f"<table>{cap}<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


# ---------------------------------------------------------------- numbers and scales

def num(v):
    """A coordinate as a short, stable string."""
    v = round(float(v), 2)
    if v == 0:
        return "0"
    return f"{v:.2f}".rstrip("0").rstrip(".")


def mv(m, e):
    return m * 10.0 ** e


class Linear:
    def __init__(self, lo, hi, a, b):
        self.lo = lo
        self.hi = hi
        self.a = a
        self.b = b

    def __call__(self, v):
        return self.a + (v - self.lo) / (self.hi - self.lo) * (self.b - self.a)


class Log:
    """Base-10 log scale."""

    def __init__(self, lo, hi, a, b):
        self.l0 = math.log10(lo)
        self.l1 = math.log10(hi)
        self.a = a
        self.b = b

    def __call__(self, v):
        return self.a + (math.log10(v) - self.l0) / (self.l1 - self.l0) * (self.b - self.a)


def log_floor(v):
    """Largest 1-2-5 value at or below v, as (mantissa, exponent)."""
    e = math.floor(math.log10(v))
    for m in (5, 2, 1):
        if mv(m, e) <= v * (1 + 1e-9):
            return (m, e)


def log_ceil(v):
    """Smallest 1-2-5 value at or above v, as (mantissa, exponent)."""
    e = math.floor(math.log10(v))
    for m, ee in ((1, e), (2, e), (5, e), (1, e + 1)):
        if mv(m, ee) >= v * (1 - 1e-9):
            return (m, ee)


def log_domain(values):
    return log_floor(min(values)), log_ceil(max(values))


def log_label(m, e):
    if e < -4 or e >= 6:
        return f"{m}e{e}"
    if e >= 0:
        return f"{m * 10 ** e:,}"
    return "0." + "0" * (-e - 1) + str(m)


def log_ticks(lo, hi):
    """Ticks between two (mantissa, exponent) bounds: 1-2-5 when the span is at
    most three decades, whole decades otherwise."""
    lo_v, hi_v = mv(*lo), mv(*hi)
    decades = math.log10(hi_v / lo_v)
    mants = (1, 2, 5) if decades <= 3 else (1,)
    out = []
    for e in range(lo[1], hi[1] + 1):
        for m in mants:
            v = mv(m, e)
            if lo_v * (1 - 1e-9) <= v <= hi_v * (1 + 1e-9):
                out.append((v, log_label(m, e)))
    return out


def lin_domain(vmax, target):
    """(top, step, n, decimals) for a zero-based linear axis with about `target` steps."""
    raw = vmax / target
    e = math.floor(math.log10(raw))
    for m in (1, 2, 5, 10):
        step = mv(m, e)
        if step >= raw * (1 - 1e-9):
            break
    n = int(math.ceil(vmax / step - 1e-9))
    decimals = max(0, -int(math.floor(math.log10(step) + 1e-9)))
    return step * n, step, n, decimals


def lin_ticks(step, n, decimals):
    out = []
    for i in range(n + 1):
        v = i * step
        if i == 0:
            lab = "0"
        elif decimals == 0:
            lab = f"{int(round(v)):,}"
        else:
            lab = f"{v:.{decimals}f}"
        out.append((v, lab))
    return out


# ---------------------------------------------------------------- SVG primitives

def text(x, y, s, anchor="start", muted=False, size=12):
    if muted:
        paint = 'class="rk-muted" fill="var(--text-2)"'
    else:
        paint = 'fill="currentColor"'
    return (f'<text x="{num(x)}" y="{num(y)}" font-size="{size}" text-anchor="{anchor}" {paint}>'
            f"{esc(s)}</text>")


def line(x1, y1, x2, y2, cls, color, width=1):
    return (f'<line class="{cls}" x1="{num(x1)}" y1="{num(y1)}" x2="{num(x2)}" y2="{num(y2)}" '
            f'stroke="{color}" stroke-width="{width}"/>')


def dot(cx, cy, n, label):
    """A data mark: an 8px point with a native tooltip."""
    return (f'<circle class="mark rk-s{n}" cx="{num(cx)}" cy="{num(cy)}" r="4" '
            f'fill="var(--series-{n})"><title>{esc(label)}</title></circle>')


def bar(x, y, w, h, n, label):
    """A data mark: a bar with a native tooltip."""
    return (f'<rect class="mark rk-s{n}" x="{num(x)}" y="{num(y)}" width="{num(w)}" '
            f'height="{num(max(h, 0))}" fill="var(--series-{n})"><title>{esc(label)}</title></rect>')


def series_line(points, n):
    """A 2px connector through a series' points. Not a data mark."""
    d = " ".join(("M" if i == 0 else "L") + f"{num(x)} {num(y)}" for i, (x, y) in enumerate(points))
    return (f'<path class="rk-l{n}" d="{d}" fill="none" stroke="var(--series-{n})" '
            f'stroke-width="2"/>')


def legend(items, right, y):
    """Right-aligned legend row: small square swatches, then labels."""
    out = []
    x = right
    for n, label in reversed(items):
        tx = x - len(label) * CHAR_W
        sx = tx - 14
        out.append(f'<rect class="rk-swatch rk-s{n}" x="{num(sx)}" y="{num(y - 9)}" width="10" '
                   f'height="10" rx="2" fill="var(--series-{n})"/>' + text(tx, y, label))
        x = sx - 18
    return "".join(reversed(out))


def y_grid(scale, ticks, left, right):
    out = []
    for v, lab in ticks:
        y = scale(v)
        out.append(line(left, y, right, y, "rk-grid", "var(--grid)"))
        out.append(text(left - 8, y + 4, lab, anchor="end", muted=True))
    return "".join(out)


def x_grid(scale, ticks, top, bottom):
    out = []
    for v, lab in ticks:
        x = scale(v)
        out.append(line(x, top, x, bottom, "rk-grid", "var(--grid)"))
        out.append(text(x, bottom + 16, lab, anchor="middle", muted=True))
    return "".join(out)


def x_axis(scale, ticks, left, right, bottom):
    out = [line(left, bottom, right, bottom, "rk-axis", "var(--text-2)")]
    for v, lab in ticks:
        x = scale(v)
        out.append(line(x, bottom, x, bottom + 4, "rk-axis", "var(--text-2)"))
        out.append(text(x, bottom + 18, lab, anchor="middle", muted=True))
    return "".join(out)


# ---------------------------------------------------------------- figure wrappers

def svg_markup(chart, standalone=False):
    cid = chart["id"]
    h = chart["height"]
    labelled = f'aria-labelledby="{cid}-title {cid}-desc"'
    head = (f'<title id="{cid}-title">{esc(chart["title"])}</title>'
            f'<desc id="{cid}-desc">{esc(chart["desc"])}</desc>')
    if standalone:
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" '
                f'viewBox="0 0 {W} {h}" role="img" {labelled}>'
                + head + _STANDALONE_STYLE
                + f'<rect class="rk-bg" x="0" y="0" width="{W}" height="{h}" fill="var(--surface)"/>'
                + chart["inner"] + "</svg>\n")
    return f'<svg viewBox="0 0 {W} {h}" role="img" {labelled}>' + head + chart["inner"] + "</svg>"


def figure(chart):
    return (f'<figure id="{chart["id"]}" class="chart">'
            + svg_markup(chart)
            + f'<figcaption>{chart["caption"]}</figcaption>'
            + '<details class="data"><summary>Data table</summary>'
            + chart["table"]
            + "</details></figure>")


def standalone(chart):
    """The chart as a self-contained SVG file with literal light-theme colors."""
    return svg_markup(chart, standalone=True)
