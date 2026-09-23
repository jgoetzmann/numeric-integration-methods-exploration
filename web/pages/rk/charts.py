"""Inline SVG charts for rk.html, and standalone copies of some of them.

Deterministic: no clock reads, no randomness, data order or sorted order only.
Page SVGs paint only through CSS custom properties (var(--series-N), var(--grid),
var(--text-2)) and currentColor. The standalone copies carry a <style> block
with the light-theme values, because they are viewed outside the site's
stylesheet (for example from the README).
"""

import datetime
import math

from web import fmt

W = 720
CHAR_W = 6.8  # rough width of one character at font-size 12

_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

_WORDS = {0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
          6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
          11: "eleven", 12: "twelve"}

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

_WEIGHTING = {
    "magnitude": "magnitude",
    "equal_median_anchor": "median-anchor",
    "equal_reference_norm": "reference-norm",
}
_BASIS = {
    "analytic": "analytic cost basis",
    "traced_whole_step": "traced whole-step basis",
}
_MODE = {
    "floor": "floor rounding",
    "round_to_nearest": "round-to-nearest",
}


# ---------------------------------------------------------------- small text helpers

def esc(s):
    return fmt.esc(s)


def code(s):
    return f"<code>{fmt.esc(s)}</code>"


def word(n):
    """Small structural counts as words; anything larger through fmt.count."""
    n = int(n)
    return _WORDS.get(n, fmt.count(n))


def and_list(items):
    items = list(items)
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def claim_ref(*ids):
    links = ", ".join(f'<a href="claims.html#{esc(i)}">{esc(i)}</a>' for i in ids)
    label = "claim" if len(ids) == 1 else "claims"
    return f"({label} {links})"


def label_of(mapping, key):
    return mapping.get(key, str(key).replace("_", " "))


def source_note(src):
    """A 'Source:' sentence linking the file a block was read from."""
    if not src:
        return ""
    path = src.get("path", "") or ""
    single = bool(path) and ";" not in path and "*" not in path and not path.endswith("/")
    if single:
        href = f"{src['url']}/blob/{src['commit']}/{path}"
    else:
        href = f"{src['url']}/tree/{src['commit']}"
    key = src.get("key") or ""
    key_part = f", key {code(key)}" if key else ""
    return (f' Source: <a href="{esc(href)}">{code(src["repo"] + "/" + path)}</a>'
            f" at commit {code(src['commit'])}{key_part}.")


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
    return (5, e - 1)


def log_ceil(v):
    """Smallest 1-2-5 value at or above v, as (mantissa, exponent)."""
    e = math.floor(math.log10(v))
    for m, ee in ((1, e), (2, e), (5, e), (1, e + 1)):
        if mv(m, ee) >= v * (1 - 1e-9):
            return (m, ee)
    return (2, e + 1)


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
    step = mv(10, e)
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
    return svg_markup(chart, standalone=True)


# ---------------------------------------------------------------- the six charts

def frontier_chart(rk):
    """B22: cycles per step against held-out error, classical and discovered."""
    fr = rk["frontier"]
    champ = rk["champion"]
    setup = rk["setup"]
    classical = fr["classical"]
    discovered = fr["discovered"]
    rows = classical + discovered
    best = champ.get("best_classical")

    H = 390
    L, R, T, B = 64, 704, 52, H - 52
    top_c, step, n, dec = lin_domain(max(r["cycles"] for r in rows), 8)
    xs = Linear(0, top_c, L, R)
    lo, hi = log_domain([r["heldout_error"] for r in rows])
    ys = Log(mv(*lo), mv(*hi), B, T)

    parts = [
        legend([(1, "classical methods"), (2, "discovered cell elites")], R, 16),
        text(8, 38, "held-out RMS error (log scale)"),
        y_grid(ys, log_ticks(lo, hi), L, R),
        x_axis(xs, lin_ticks(step, n, dec), L, R, B),
        text((L + R) / 2, B + 40, f"cycles per step, analytic {setup['cost_model']} cost model",
             anchor="middle"),
    ]
    labels = []
    for r in classical:
        x, y = xs(r["cycles"]), ys(r["heldout_error"])
        parts.append(dot(x, y, 1, f"{r['name']}: {fmt.count(r['cycles'])} cycles per step, "
                                  f"held-out error {fmt.sig(r['heldout_error'])}"))
        if r["name"] == best:
            labels.append(text(x - 8, y + 4, r["name"], anchor="end"))
    for r in discovered:
        x, y = xs(r["cycles"]), ys(r["heldout_error"])
        who = f"order {r['order']}, {r['stages']} stages"
        if r.get("is_champion"):
            who = f"champion {champ['hash']}, {who}"
        parts.append(dot(x, y, 2, f"{who}: {fmt.count(r['cycles'])} cycles per step, "
                                  f"held-out error {fmt.sig(r['heldout_error'])}"))
        if r.get("is_champion"):
            labels.append(text(x + 8, y + 4, f"{champ['hash']} (champion)"))
    parts.extend(labels)

    trows = []
    for r in classical:
        trows.append(["classical", code(r["name"]), "", "", fmt.count(r["cycles"]),
                      fmt.sig(r["heldout_error"])])
    for r in discovered:
        name = f"champion {code(champ['hash'])}" if r.get("is_champion") else "cell elite"
        trows.append(["discovered", name, fmt.count(r["order"]), fmt.count(r["stages"]),
                      fmt.count(r["cycles"]), fmt.sig(r["heldout_error"])])

    champ_row = next((r for r in discovered if r.get("is_champion")), None)
    best_row = next((r for r in classical if r["name"] == best), None)
    desc = (f"Scatter plot of held-out RMS error (log scale) against cycles per step for "
            f"{len(classical)} classical methods and {len(discovered)} discovered cell elites.")
    if champ_row and best_row:
        desc += (f" The champion {champ['hash']} has the lowest error, "
                 f"{fmt.sig(champ_row['heldout_error'])} at {champ_row['cycles']} cycles per step; "
                 f"{best}, the best classical method, has {fmt.sig(best_row['heldout_error'])} "
                 f"at {best_row['cycles']}.")

    caption = (
        f"Held-out RMS error against cycles per step for the {word(len(classical))} classical "
        f"methods and the {fmt.count(len(discovered))} discovered cell elites of epoch 1, in Q15 "
        f"with floor rounding at the {fmt.count(setup['budget_cycles'])}-cycle budget, on the "
        f"analytic {code(setup['cost_model'])} cost model with magnitude weighting. Lower is "
        f"better. The champion {code(champ['hash'])} and {code(best)}, the best classical method, "
        f"are labelled {claim_ref('R1', 'R2')}." + source_note(fr.get("source"))
    )
    return {
        "id": "rk-frontier",
        "height": H,
        "title": "Held-out error against cost per step, epoch 1",
        "desc": desc,
        "inner": "".join(parts),
        "caption": caption,
        "table": table(["Series", "Method", "Order", "Stages", "Cycles per step",
                        "Held-out RMS error"], trows),
    }


def counterfactual_chart(rk):
    """B23: the six weighting and cost-basis cells on a log ratio axis."""
    cf = rk["counterfactual"]
    cells = cf["cells"]
    budget = rk["setup"]["budget_cycles"]
    weightings, bases = [], []
    for c in cells:
        if c["weighting"] not in weightings:
            weightings.append(c["weighting"])
        if c["basis"] not in bases:
            bases.append(c["basis"])

    H = 350
    L, T, B = 64, 52, H - 66
    cat_right, line_right = 520, 712
    lo, hi = log_domain([c["ratio"] for c in cells] + [1.0])
    ys = Log(mv(*lo), mv(*hi), B, T)
    band = (cat_right - L) / len(weightings)

    parts = [
        legend([(j + 1, label_of(_BASIS, b)) for j, b in enumerate(bases)], line_right, 16),
        text(8, 38, "ratio: best classical error over champion error (log scale)"),
        y_grid(ys, log_ticks(lo, hi), L, line_right),
    ]
    y1 = ys(1.0)
    parts.append(line(L, y1, line_right, y1, "rk-ref", "var(--text-2)", 1.5))
    parts.append(text(line_right, y1 - 7, "above 1: champion leads", anchor="end"))
    parts.append(text(line_right, y1 + 17, "below 1: a classical method leads", anchor="end",
                      muted=True))
    parts.append(line(L, B, cat_right, B, "rk-axis", "var(--text-2)"))
    for i, w in enumerate(weightings):
        cx = L + band * (i + 0.5)
        parts.append(text(cx, B + 18, label_of(_WEIGHTING, w), anchor="middle"))
        if w == "magnitude":
            parts.append(text(cx, B + 34, "(published)", anchor="middle", muted=True))
    parts.append(text((L + cat_right) / 2, B + 56, "weighting of the four held-out problems",
                      anchor="middle"))

    labels = []
    for c in cells:
        i = weightings.index(c["weighting"])
        j = bases.index(c["basis"])
        cx = L + band * (i + 0.5) + (j - (len(bases) - 1) / 2) * 28
        cy = ys(c["ratio"])
        stays = "stays ahead" if c["champion_still_leads"] else "does not stay ahead"
        title = (f"{label_of(_WEIGHTING, c['weighting'])} weighting, {label_of(_BASIS, c['basis'])}: "
                 f"ratio {fmt.ratio(c['ratio'])}; the champion {stays} on every leave-one-out "
                 f"subset (lowest {fmt.ratio(c['lowest_leave_one_out_ratio'])})")
        parts.append(dot(cx, cy, j + 1, title))
        if c["weighting"] == "magnitude" or c["ratio"] < 1:
            labels.append(text(cx, cy - 9, fmt.ratio(c["ratio"]), anchor="middle"))
    parts.extend(labels)

    trows = [[esc(label_of(_WEIGHTING, c["weighting"])), esc(label_of(_BASIS, c["basis"])),
              fmt.ratio(c["ratio"]), fmt.ratio(c["lowest_leave_one_out_ratio"]),
              "yes" if c["champion_still_leads"] else "no"] for c in cells]

    pub = next((c for c in cells if c["weighting"] == "magnitude" and c["basis"] == "analytic"),
               cells[0])
    desc = (f"Dot plot of {len(cells)} cells, {len(weightings)} weightings by {len(bases)} cost "
            f"bases, on a log ratio axis with a reference line at 1. Above the line the champion "
            f"leads. The published cell is {fmt.ratio(pub['ratio'])}.")
    caption = (
        f"The ratio of the best classical method's held-out error to the champion's, for "
        f"{word(len(weightings))} weightings of the held-out problems and {word(len(bases))} cost "
        f"bases, in Q15 with floor rounding at the {fmt.count(budget)}-cycle budget. Above 1 the "
        f"champion leads. The published {fmt.ratio(pub['ratio'])} is the analytic, "
        f"magnitude-weighted cell. The traced whole-step basis uses the compiled step's cycle "
        f"count only as the budget denominator {claim_ref('R1')}." + source_note(cf.get("source"))
    )
    return {
        "id": "rk-counterfactual",
        "height": H,
        "title": "How the champion's lead changes with weighting and cost basis",
        "desc": desc,
        "inner": "".join(parts),
        "caption": caption,
        "table": table(["Weighting", "Cost basis", "Ratio, best classical over champion",
                        "Lowest leave-one-out ratio",
                        "Champion ahead on every leave-one-out subset"], trows),
    }


def _row_dotplot(problems, plotted, series, x_title, note_fn):
    """Horizontal dot plot, one row per problem, log x. Returns (height, inner)."""
    plotted_names = [p["problem"] for p in plotted]
    rows = plotted + [p for p in problems if p["problem"] not in plotted_names]
    row_h = 30
    L, R, T = 180, 704, 40
    B = T + row_h * len(rows)
    H = B + 52
    values = [fn(p) for p in plotted for (_, _, fn, _) in series]
    lo, hi = log_domain(values)
    xs = Log(mv(*lo), mv(*hi), L, R)

    parts = [
        legend([(n, lab) for (n, lab, _, _) in series], R, 16),
        x_grid(xs, log_ticks(lo, hi), T, B),
        line(L, B, R, B, "rk-axis", "var(--text-2)"),
        text((L + R) / 2, B + 38, x_title, anchor="middle"),
    ]
    for i, p in enumerate(rows):
        y = T + row_h * (i + 0.5)
        name = p["problem"] + (" (stiff)" if p.get("stiff") else "")
        parts.append(text(L - 10, y + 4, name, anchor="end"))
        if p["problem"] in plotted_names:
            px = [xs(fn(p)) for (_, _, fn, _) in series]
            parts.append(line(min(px), y, max(px), y, "rk-connector", "var(--grid)", 2))
            for (n, _, fn, tfn) in series:
                parts.append(dot(xs(fn(p)), y, n, tfn(p)))
        else:
            parts.append(text(L + 6, y + 4, note_fn(p), muted=True))
    return H, "".join(parts)


def _overflowed(problems):
    return [p for p in problems if p.get("champion_overflowed")]


def validation_q15_chart(rk):
    """B24, Q15 half: champion against the best classical method per problem."""
    val = rk["validation"]
    probs = val["problems"]
    champ = rk["champion"]["hash"]
    budget = rk["setup"]["budget_cycles"]
    plotted = [p for p in probs
               if not p.get("champion_overflowed")
               and p.get("champion_q15") is not None
               and p.get("best_classical_q15") is not None]
    series = [
        (1, "best classical method", lambda p: p["best_classical_q15"],
         lambda p: (f"{p['problem']}: best classical method {p['best_classical']}, "
                    f"Q15 error {fmt.sig(p['best_classical_q15'], 4)}")),
        (2, f"champion {champ}", lambda p: p["champion_q15"],
         lambda p: f"{p['problem']}: champion {champ}, Q15 error {fmt.sig(p['champion_q15'], 4)}"),
    ]
    H, inner = _row_dotplot(
        probs, plotted, series,
        f"Q15 RMS error, floor rounding, {fmt.count(budget)}-cycle budget (log scale)",
        lambda p: ("champion overflowed: not plotted" if p.get("champion_overflowed")
                   else "no Q15 result: not plotted"))

    trows = []
    for p in probs:
        if p.get("champion_overflowed"):
            champ_cell = "overflow"
        elif p.get("champion_q15") is None:
            champ_cell = "none"
        else:
            champ_cell = fmt.sig(p["champion_q15"], 4)
        if p.get("best_discovered_q15") is None:
            disc_cell = "overflow" if p.get("champion_overflowed") else "none"
        else:
            disc_cell = fmt.sig(p["best_discovered_q15"], 4)
        bc = fmt.sig(p["best_classical_q15"], 4) if p.get("best_classical_q15") is not None else "none"
        trows.append([code(p["problem"]), "yes" if p.get("stiff") else "no", champ_cell,
                      code(p["best_classical"]), bc, disc_cell, esc(p.get("winner_kind", ""))])

    over = _overflowed(probs)
    over_names = and_list([code(p["problem"]) for p in over])
    desc = (f"Dot plot, one row per out-of-sample problem, of Q15 RMS error on a log axis: the "
            f"champion {champ} against the best classical method for that problem. "
            f"{len(plotted)} problems are plotted.")
    if over:
        desc += " " + ", ".join(p["problem"] for p in over) + " is not plotted: the champion overflowed."
    caption = (
        f"Q15 RMS error with floor rounding at the {fmt.count(budget)}-cycle budget on the "
        f"out-of-sample problems: the champion {code(champ)} against the best classical method "
        f"for each problem {claim_ref('R4')}. Lower is better."
    )
    if over:
        caption += (f" {over_names} is not plotted because the champion hit an overflow there; "
                    f"it is in the table.")
    caption += source_note(val.get("source"))
    return {
        "id": "rk-validation-q15",
        "height": H,
        "title": "Out-of-sample Q15 error, champion against best classical method",
        "desc": desc,
        "inner": inner,
        "caption": caption,
        "table": table(["Problem", "Stiff", "Champion Q15 error", "Best classical method",
                        "Its Q15 error", "Best discovered Q15 error", "Lower error"], trows),
    }


def validation_f64_chart(rk):
    """B24, float64 half: champion against rk4 at the same step counts."""
    val = rk["validation"]
    probs = val["problems"]
    champ = rk["champion"]["hash"]
    plotted = [p for p in probs
               if p.get("champion_float64") is not None and p.get("rk4_float64") is not None]
    series = [
        (1, "rk4 in float64", lambda p: p["rk4_float64"],
         lambda p: f"{p['problem']}: rk4, float64 error {fmt.sig(p['rk4_float64'])}"),
        (2, f"champion {champ} in float64", lambda p: p["champion_float64"],
         lambda p: f"{p['problem']}: champion {champ}, float64 error {fmt.sig(p['champion_float64'])}"),
    ]
    H, inner = _row_dotplot(
        probs, plotted, series,
        "float64 error at the same step counts (log scale)",
        lambda p: ("champion overflowed in Q15: not compared" if p.get("champion_overflowed")
                   else "no float64 result: not plotted"))

    trows = []
    for p in probs:
        if p.get("champion_float64") is not None:
            c_cell = fmt.sig(p["champion_float64"])
        elif p.get("champion_overflowed"):
            c_cell = "overflow in Q15, not compared"
        else:
            c_cell = "none"
        if p.get("rk4_float64") is not None:
            r_cell = fmt.sig(p["rk4_float64"])
        else:
            r_cell = "not compared"
        trows.append([code(p["problem"]), "yes" if p.get("stiff") else "no", c_cell, r_cell])

    over = _overflowed(probs)
    over_names = and_list([code(p["problem"]) for p in over])
    gap = rk.get("float64_gap", {})
    desc = (f"Dot plot, one row per out-of-sample problem, of float64 error on a log axis: the "
            f"champion {champ} against rk4 at the same step counts. {len(plotted)} problems are "
            f"plotted.")
    if gap:
        desc += (f" The champion's error is {fmt.ratio(gap['champion_over_rk4_min'])} to "
                 f"{fmt.ratio(gap['champion_over_rk4_max'])} that of rk4.")
    caption = (
        f"Error in float64 of the champion {code(champ)} and of {code('rk4')}, at the same step "
        f"counts, on the out-of-sample problems where both finish {claim_ref('R5')}. Lower is "
        f"better."
    )
    if over:
        caption += (f" {over_names} is not plotted: the champion hit an overflow there in Q15, "
                    f"so it has no float64 comparison.")
    caption += source_note(gap.get("source") or val.get("source"))
    return {
        "id": "rk-validation-f64",
        "height": H,
        "title": "Out-of-sample float64 error, champion against rk4",
        "desc": desc,
        "inner": inner,
        "caption": caption,
        "table": table(["Problem", "Stiff", "Champion float64 error", "rk4 float64 error"], trows),
    }


def _floor_round_methods(rk, search):
    modes = [m for m in ("floor", "round_to_nearest") if m in search]
    modes += sorted(m for m in search if m not in modes)
    first_mode = search[modes[0]]
    names = [r["name"] for r in rk["frontier"]["classical"] if r["name"] in first_mode]
    names += sorted(n for n in first_mode if n not in names)
    return modes, names


def floor_round_chart(rk):
    """B25: search_rms per method under both rounding modes, two series."""
    fvr = rk["floor_vs_round"]
    search = fvr["search_rms"]
    held = fvr.get("heldout_rms", {})
    budget = rk["setup"]["budget_cycles"]
    modes, names = _floor_round_methods(rk, search)

    H = 330
    L, R, T, B = 64, 704, 52, H - 48
    vmax = max(search[m][n] for m in modes for n in names)
    top, step, n, dec = lin_domain(vmax, 7)
    ys = Linear(0, top, B, T)
    band = (R - L) / len(names)
    bw, gap = 36, 2

    parts = [
        legend([(j + 1, label_of(_MODE, m)) for j, m in enumerate(modes)], R, 16),
        text(8, 38, f"search-set RMS error in Q15, {fmt.count(budget)}-cycle budget"),
        y_grid(ys, lin_ticks(step, n, dec), L, R),
        line(L, B, R, B, "rk-axis", "var(--text-2)"),
    ]
    group_w = len(modes) * bw + (len(modes) - 1) * gap
    for i, name in enumerate(names):
        cx = L + band * (i + 0.5)
        x0 = cx - group_w / 2
        for j, m in enumerate(modes):
            v = search[m][name]
            x = x0 + j * (bw + gap)
            y = ys(v)
            parts.append(bar(x, y, bw, B - y, j + 1,
                             f"{name}, {label_of(_MODE, m)}: search-set RMS error {fmt.sig(v)}"))
        parts.append(text(cx, B + 18, name, anchor="middle"))
    parts.append(text((L + R) / 2, B + 40, "classical method", anchor="middle"))

    headers = ["Method"] + [f"Search set, {esc(label_of(_MODE, m))}" for m in modes]
    held_modes = [m for m in modes if m in held]
    headers += [f"Held-out, {esc(label_of(_MODE, m))} (not plotted)" for m in held_modes]
    trows = []
    for name in names:
        row = [code(name)] + [fmt.sig(search[m][name]) for m in modes]
        row += [fmt.sig(held[m][name]) if name in held[m] else "none" for m in held_modes]
        trows.append(row)

    desc = (f"Grouped bar chart of search-set RMS error for {len(names)} classical methods under "
            f"{' and '.join(label_of(_MODE, m) for m in modes)}.")
    caption = (
        f"Search-set RMS error of {word(len(names))} classical methods in Q15 at the "
        f"{fmt.count(budget)}-cycle budget, under floor rounding and under round-to-nearest. Lower "
        f"is better. The table adds the held-out errors, which are not plotted "
        f"{claim_ref('R8')}." + source_note(fvr.get("source"))
    )
    return {
        "id": "rk-floor-round",
        "height": H,
        "title": "Classical methods under floor rounding and round-to-nearest",
        "desc": desc,
        "inner": "".join(parts),
        "caption": caption,
        "table": table(headers, trows),
    }


def _day_index(d0, iso):
    d = datetime.date.fromisoformat(iso[:10])
    idx = float((d - d0).days)
    if len(iso) >= 16 and iso[10] == "T":
        hh = int(iso[11:13])
        mm = int(iso[14:16])
        idx += (hh * 60 + mm) / 1440.0
    return idx


def archive_chart(rk):
    """B26: cumulative records per archive day, one series per epoch."""
    ep = rk["epochs"]
    series = [(1, "epoch 1", ep["epoch1"]["archive_days"]),
              (2, "epoch 2", ep["epoch2"]["archive_days"])]
    all_days = sorted(r["day"] for (_, _, rows) in series for r in rows)
    d0 = datetime.date.fromisoformat(all_days[0][:10])
    d_end = datetime.date.fromisoformat(all_days[-1][:10])
    span = (d_end - d0).days + 1

    H = 360
    L, R, T, B = 72, 704, 52, H - 52
    xs = Linear(0, span, L, R)
    lo, hi = log_domain([r["cumulative"] for (_, _, rows) in series for r in rows])
    ys = Log(mv(*lo), mv(*hi), B, T)

    parts = [
        legend([(n, lab) for (n, lab, _) in series], R, 16),
        text(8, 38, "cumulative scored records (log scale)"),
    ]
    down = ep["epoch2"].get("down_days") or {}
    if down.get("from") and down.get("to"):
        a = min(max(_day_index(d0, down["from"]), 0.0), float(span))
        b = min(max(_day_index(d0, down["to"]), 0.0), float(span))
        if b > a:
            parts.append(f'<rect class="rk-band" x="{num(xs(a))}" y="{num(T)}" '
                         f'width="{num(xs(b) - xs(a))}" height="{num(B - T)}" '
                         f'fill="var(--grid)" fill-opacity="0.6"/>')
            parts.append(text((xs(a) + xs(b)) / 2, T + 14, "run stopped", anchor="middle",
                              muted=True))
    parts.append(y_grid(ys, log_ticks(lo, hi), L, R))
    ticks = []
    for k in range(0, span, 7):
        d = d0 + datetime.timedelta(days=k)
        ticks.append((k + 0.5, f"{_MONTHS[d.month - 1]} {d.day}"))
    parts.append(x_axis(xs, ticks, L, R, B))
    parts.append(text((L + R) / 2, B + 40, "archive day (UTC)", anchor="middle"))

    for (n, lab, rows) in series:
        pts = []
        for r in rows:
            idx = (datetime.date.fromisoformat(r["day"][:10]) - d0).days
            pts.append((xs(idx + 0.5), ys(r["cumulative"])))
        if len(pts) > 1:
            parts.append(series_line(pts, n))
    for (n, lab, rows) in series:
        for r in rows:
            idx = (datetime.date.fromisoformat(r["day"][:10]) - d0).days
            parts.append(dot(xs(idx + 0.5), ys(r["cumulative"]), n,
                             f"{fmt.day(r['day'])}, {lab}: {fmt.count(r['records'])} records that "
                             f"day, {fmt.count(r['cumulative'])} cumulative"))

    trows = []
    for (n, lab, rows) in series:
        for r in rows:
            trows.append([esc(fmt.day(r["day"])), str(int(r.get("epoch", n))),
                          fmt.count(r["records"]), fmt.count(r["cumulative"])])

    e1 = ep["epoch1"]["archive_days"]
    e2 = ep["epoch2"]["archive_days"]
    desc = (f"Line chart with points, log scale, of cumulative scored records per archive day: "
            f"{len(e1)} days of epoch 1 ending at {fmt.count(e1[-1]['cumulative'])} records and "
            f"{len(e2)} days of epoch 2 ending at {fmt.count(e2[-1]['cumulative'])}.")
    caption = (
        f"Cumulative scored records in the explicit archive at the end of each archive day, on a "
        f"log scale {claim_ref('R12')}. Epoch 1 and epoch 2 are separate series because they "
        f"were scored under different verifier hashes and cost models."
    )
    if down.get("from") and down.get("to"):
        caption += (f" The shaded band is the window from {esc(fmt.day(down['from']))} to "
                    f"{esc(fmt.day(down['to']))} when the run was stopped.")
    caption += source_note(ep.get("source"))
    return {
        "id": "rk-archive-growth",
        "height": H,
        "title": "Archive growth by day, epoch 1 and epoch 2",
        "desc": desc,
        "inner": "".join(parts),
        "caption": caption,
        "table": table(["Day", "Epoch", "Records that day", "Cumulative records"], trows),
    }
