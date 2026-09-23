"""Inline SVG charts for novel.html.

Colors come only from CSS custom properties (var(--series-N), var(--grid),
var(--text-2)) or currentColor. Every data mark carries a <title> child.
Coordinates are rounded to one decimal so output is byte-stable.
"""
import math

from web import fmt

WIDTH = 720
OFF_SCALE = 1e6


def num(x):
    return f"{x:.1f}"


def log_tick(k):
    if -2 <= k <= 2:
        return fmt.sig(10.0 ** k)
    return f"1e{k}"


def text(x, y, s, anchor="start", extra=""):
    return (
        f'<text x="{num(x)}" y="{num(y)}" text-anchor="{anchor}" font-size="12" '
        f'fill="currentColor"{extra}>{fmt.esc(s)}</text>'
    )


def muted(x, y, s, anchor="start"):
    return (
        f'<text x="{num(x)}" y="{num(y)}" text-anchor="{anchor}" font-size="12" '
        f'fill="var(--text-2)">{fmt.esc(s)}</text>'
    )


def gridline(x1, y1, x2, y2):
    return (
        f'<line x1="{num(x1)}" y1="{num(y1)}" x2="{num(x2)}" y2="{num(y2)}" '
        f'stroke="var(--grid)" stroke-width="1"/>'
    )


def refline(x1, y1, x2, y2, slot):
    return (
        f'<line class="ref" x1="{num(x1)}" y1="{num(y1)}" x2="{num(x2)}" y2="{num(y2)}" '
        f'stroke="var(--series-{slot})" stroke-width="1"/>'
    )


def legend(items, x, y):
    out = ['<g class="legend">']
    cx = x
    for slot, label in items:
        out.append(
            f'<circle class="swatch" cx="{num(cx + 4)}" cy="{num(y - 4)}" r="4" '
            f'fill="var(--series-{slot})"><title>Legend: {fmt.esc(label)}</title></circle>'
        )
        out.append(text(cx + 14, y, label))
        cx += 14 + 7 * len(label) + 28
    out.append("</g>")
    return "".join(out)


def dot(cx, cy, slot, tip):
    return (
        f'<circle class="mark series-{slot}" cx="{num(cx)}" cy="{num(cy)}" r="4" '
        f'fill="var(--series-{slot})"><title>{fmt.esc(tip)}</title></circle>'
    )


def bar(x, y, w, h, slot, tip):
    return (
        f'<rect class="mark series-{slot}" x="{num(x)}" y="{num(y)}" width="{num(w)}" '
        f'height="{num(h)}" fill="var(--series-{slot})"><title>{fmt.esc(tip)}</title></rect>'
    )


def table(headers, rows):
    head = "".join(f'<th scope="col">{fmt.esc(h)}</th>' for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows
    )
    return (
        '<table style="display:block;max-width:100%;overflow-x:auto">'
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
    )


def figure(chart_id, height, title, desc, svg_body, caption_html, table_html):
    return (
        f'<figure id="{chart_id}" class="chart">'
        f'<svg viewBox="0 0 {WIDTH} {int(height)}" role="img" '
        f'aria-labelledby="{chart_id}-title {chart_id}-desc">'
        f'<title id="{chart_id}-title">{fmt.esc(title)}</title>'
        f'<desc id="{chart_id}-desc">{fmt.esc(desc)}</desc>'
        f"{svg_body}</svg>"
        f"<figcaption>{caption_html}</figcaption>"
        '<details class="data"><summary>Data table</summary>'
        f"{table_html}</details>"
        "</figure>"
    )


def source_link(source, sources):
    url = source["url"]
    commit = source["commit"]
    for repo in sources["repos"]:
        if repo["name"] == source["repo"]:
            url = repo["url"]
            commit = repo["commit"]
    path = source["path"]
    single = path != "" and ";" not in path and "*" not in path and not path.endswith("/")
    href = f"{url}/blob/{commit}/{path}" if single else f"{url}/tree/{commit}"
    return (
        f'<a href="{fmt.esc(href)}"><code>{fmt.esc(path)}</code></a> '
        f"at <code>{fmt.esc(commit)}</code>"
    )


def benchmark_chart(rows, notes, caption_html):
    label_x, x0, x1 = 176.0, 184.0, 612.0
    break_x, off_x = 640.0, 704.0
    top, pitch = 40.0, 26.0
    bottom = top + pitch * len(rows)
    height = bottom + 56
    on = [r["mean_max_error"] for r in rows if r["mean_max_error"] < OFF_SCALE]
    off = [r for r in rows if r["mean_max_error"] >= OFF_SCALE]
    lo = math.floor(math.log10(min(on)))
    hi = math.ceil(math.log10(max(on)))

    def xpos(v):
        return x0 + (math.log10(v) - lo) / (hi - lo) * (x1 - x0)

    parts = [legend([(1, "Baselines"), (2, "Trial entries")], x0, 20)]
    for k in range(lo, hi + 1):
        x = xpos(10.0 ** k)
        parts.append(gridline(x, top, x, bottom))
        parts.append(muted(x, bottom + 16, log_tick(k), "middle"))
    parts.append(gridline(break_x, top, break_x, bottom))
    parts.append(muted((break_x + WIDTH) / 2, bottom + 16, "off scale", "middle"))
    for i, r in enumerate(rows):
        y = top + pitch * i + pitch / 2
        parts.append(gridline(x0, y, x1, y))
    for i, r in enumerate(rows):
        y = top + pitch * i + pitch / 2
        slot = 1 if r["baseline"] else 2
        v = r["mean_max_error"]
        parts.append(text(label_x, y + 4, r["label"], "end"))
        if v >= OFF_SCALE:
            tip = f'{r["label"]}: {fmt.sig(v)}, an artifact of a stepper bug, drawn off scale'
            parts.append(
                f'<path class="mark series-{slot} offscale" '
                f'd="M{num(off_x - 10)},{num(y - 5)} L{num(off_x)},{num(y)} '
                f'L{num(off_x - 10)},{num(y + 5)} Z" fill="var(--series-{slot})">'
                f"<title>{fmt.esc(tip)}</title></path>"
            )
            parts.append(text(break_x - 8, y + 4, f"{fmt.sig(v)}: artifact, off scale", "end"))
        else:
            parts.append(dot(xpos(v), y, slot, f'{r["label"]}: {fmt.sig(v)}'))
    parts.append(
        text((x0 + x1) / 2, bottom + 40, "Mean of per-ODE max error, float64 (log scale)", "middle")
    )

    lowest = min(on)
    off_desc = "; ".join(
        f'{r["label"]} is marked off scale at {fmt.sig(r["mean_max_error"])} because that number is an artifact'
        for r in off
    )
    desc = (
        f"Dot plot on a log scale with one mark for each of {len(rows)} benchmark entries, "
        f"baselines and trial entries as two series. The lowest mean error is {fmt.sig(lowest)}. "
        f"{off_desc}."
    )
    table_rows = []
    for r in rows:
        table_rows.append([
            fmt.esc(r["label"]),
            "baseline" if r["baseline"] else "trial",
            fmt.count(r["stages"]),
            fmt.sig(r["mean_max_error"]),
            fmt.sig(r["runtime_s"]),
            fmt.pct(r["success_rate"], 1),
            notes.get(r["id"], ""),
        ])
    tbl = table(
        ["Entry", "Kind", "Stages", "Mean of per-ODE max error", "Runtime (s)", "Success rate", "Note"],
        table_rows,
    )
    return figure(
        "novel-benchmark",
        height,
        "Mean of per-ODE max error for each benchmark entry",
        desc,
        "".join(parts),
        caption_html,
        tbl,
    )


def runtime_chart(rows, odes, caption_html):
    label_x, x0, x1 = 176.0, 184.0, 680.0
    top, pitch = 40.0, 24.0
    bottom = top + pitch * len(rows)
    height = bottom + 56
    step = 100.0
    vmax = math.ceil(max(r["runtime_s"] for r in rows) / step) * step

    def xpos(v):
        return x0 + v / vmax * (x1 - x0)

    parts = [legend([(1, "Baselines"), (2, "Trial entries")], x0, 20)]
    for k in range(int(vmax / step) + 1):
        t = k * step
        x = xpos(t)
        parts.append(gridline(x, top, x, bottom))
        parts.append(muted(x, bottom + 16, fmt.count(t), "middle"))
    for i, r in enumerate(rows):
        y = top + pitch * i
        slot = 1 if r["baseline"] else 2
        v = r["runtime_s"]
        parts.append(text(label_x, y + pitch / 2 + 4, r["label"], "end"))
        parts.append(bar(x0, y + 1, xpos(v) - x0, pitch - 2, slot, f'{r["label"]}: {fmt.sig(v)} s'))
    parts.append(
        text((x0 + x1) / 2, bottom + 40, f"Wall time for all {fmt.count(odes)} ODEs, seconds", "middle")
    )
    fastest = min(rows, key=lambda r: r["runtime_s"])
    slowest = max(rows, key=lambda r: r["runtime_s"])
    desc = (
        f"Horizontal bar chart of runtime in seconds for {len(rows)} benchmark entries, "
        f"baselines and trial entries as two series. Shortest: {fastest['label']} at "
        f"{fmt.sig(fastest['runtime_s'])} s. Longest: {slowest['label']} at "
        f"{fmt.sig(slowest['runtime_s'])} s."
    )
    tbl = table(
        ["Entry", "Stages", "Runtime (s)"],
        [[fmt.esc(r["label"]), fmt.count(r["stages"]), fmt.sig(r["runtime_s"])] for r in rows],
    )
    return figure(
        "novel-runtime",
        height,
        "Benchmark runtime for each entry",
        desc,
        "".join(parts),
        caption_html,
        tbl,
    )


def metrics_log_chart(per_epoch, caption_html):
    x0, x1, top, bottom = 72.0, 700.0, 40.0, 320.0
    height = bottom + 56
    mins = [p["min_max_error"] for p in per_epoch]
    meds = [p["median_max_error"] for p in per_epoch]
    epochs = [p["epoch"] for p in per_epoch]
    lo = math.floor(math.log10(min(mins))) - 1
    hi = math.ceil(math.log10(max(meds)))
    e0, e1 = min(epochs), max(epochs)

    def xpos(e):
        return x0 + (e - e0) / (e1 - e0) * (x1 - x0)

    def ypos(v):
        return bottom - (math.log10(v) - lo) / (hi - lo) * (bottom - top)

    parts = [legend([(1, "Lowest max_error in the epoch"), (2, "Median max_error in the epoch")], x0, 20)]
    for k in range(lo, hi + 1):
        y = ypos(10.0 ** k)
        parts.append(gridline(x0, y, x1, y))
        parts.append(muted(x0 - 8, y + 4, log_tick(k), "end"))
    ticks = [e0] + [e for e in range(10, e1 + 1, 10) if e > e0]
    for e in ticks:
        parts.append(muted(xpos(e), bottom + 16, str(e), "middle"))
    parts.append(text((x0 + x1) / 2, bottom + 40, "Epoch", "middle"))
    parts.append(
        f'<text x="{num(-(top + bottom) / 2)}" y="16" transform="rotate(-90)" '
        f'text-anchor="middle" font-size="12" fill="currentColor">max_error (log scale)</text>'
    )
    best = min(per_epoch, key=lambda p: (p["min_max_error"], p["epoch"]))
    yb = ypos(best["min_max_error"])
    parts.append(refline(x0, yb, x1, yb, 1))
    parts.append(
        text(x1, yb + 16, f"lowest in the log: {fmt.sig(best['min_max_error'])}, epoch {best['epoch']}", "end")
    )
    for p in per_epoch:
        parts.append(
            dot(xpos(p["epoch"]), ypos(p["median_max_error"]), 2,
                f"Epoch {p['epoch']}: median max_error {fmt.sig(p['median_max_error'])}")
        )
    for p in per_epoch:
        parts.append(
            dot(xpos(p["epoch"]), ypos(p["min_max_error"]), 1,
                f"Epoch {p['epoch']}: lowest max_error {fmt.sig(p['min_max_error'])}")
        )
    desc = (
        f"Scatter plot on a log scale of the lowest and the median max_error in each of "
        f"{len(per_epoch)} epochs, two series. The lowest value in the log, "
        f"{fmt.sig(best['min_max_error'])}, is at epoch {best['epoch']}."
    )
    tbl = table(
        ["Epoch", "Lowest max_error", "Median max_error"],
        [
            [fmt.count(p["epoch"]), fmt.sig(p["min_max_error"]), fmt.sig(p["median_max_error"])]
            for p in per_epoch
        ],
    )
    return figure(
        "novel-metrics-log",
        height,
        "Lowest and median max_error per epoch in the training log",
        desc,
        "".join(parts),
        caption_html,
        tbl,
    )
