"""The three novel.html charts, built on the primitives in web.charts.

Chart-specific here: the off-scale marker for rows at or above OFF_SCALE (the
Gauss-Legendre 3 artifact) and the baseline / trial series split.
"""
from web import fmt
from web.charts import (W, Linear, Log, bar, dot, figure, legend, lin_domain, lin_ticks, line,
                        log_domain, log_ticks, mv, num, table, text, x_axis, x_grid, y_grid)

OFF_SCALE = 1e6


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
    on = [r["mean_max_error"] for r in rows if r["mean_max_error"] < OFF_SCALE]
    off = [r for r in rows if r["mean_max_error"] >= OFF_SCALE]
    lo, hi = log_domain(on)
    xs = Log(mv(*lo), mv(*hi), x0, x1)

    parts = [
        legend([(1, "Baselines"), (2, "Trial entries")], off_x, 16),
        x_grid(xs, log_ticks(lo, hi), top, bottom),
        line(break_x, top, break_x, bottom, "rk-grid", "var(--grid)"),
        text((break_x + W) / 2, bottom + 16, "off scale", anchor="middle", muted=True),
        text((x0 + x1) / 2, bottom + 40, "Mean of per-ODE max error, float64 (log scale)",
             anchor="middle"),
    ]
    for i, r in enumerate(rows):
        y = top + pitch * i + pitch / 2
        slot = 1 if r["baseline"] else 2
        v = r["mean_max_error"]
        parts.append(line(x0, y, x1, y, "rk-grid", "var(--grid)"))
        parts.append(text(label_x, y + 4, r["label"], anchor="end"))
        if v >= OFF_SCALE:
            tip = f'{r["label"]}: {fmt.sig(v)}, an artifact of a stepper bug, drawn off scale'
            parts.append(
                f'<path class="mark series-{slot} offscale" '
                f'd="M{num(off_x - 10)},{num(y - 5)} L{num(off_x)},{num(y)} '
                f'L{num(off_x - 10)},{num(y + 5)} Z" fill="var(--series-{slot})">'
                f"<title>{fmt.esc(tip)}</title></path>"
            )
            parts.append(text(break_x - 8, y + 4, f"{fmt.sig(v)}: artifact, off scale", anchor="end"))
        else:
            parts.append(dot(xs(v), y, slot, f'{r["label"]}: {fmt.sig(v)}'))

    off_desc = "; ".join(
        f'{r["label"]} is marked off scale at {fmt.sig(r["mean_max_error"])} because that number is an artifact'
        for r in off
    )
    desc = (
        f"Dot plot on a log scale with one mark for each of {len(rows)} benchmark entries, "
        f"baselines and trial entries as two series. The lowest mean error is {fmt.sig(min(on))}. "
        f"{off_desc}."
    )
    table_rows = [
        [
            fmt.esc(r["label"]),
            "baseline" if r["baseline"] else "trial",
            fmt.count(r["stages"]),
            fmt.sig(r["mean_max_error"]),
            fmt.sig(r["runtime_s"]),
            fmt.pct(r["success_rate"], 1),
            notes.get(r["id"], ""),
        ]
        for r in rows
    ]
    return figure({
        "id": "novel-benchmark",
        "height": int(bottom + 56),
        "title": "Mean of per-ODE max error for each benchmark entry",
        "desc": desc,
        "inner": "".join(parts),
        "caption": caption_html,
        "table": table(["Entry", "Kind", "Stages", "Mean of per-ODE max error", "Runtime (s)",
                        "Success rate", "Note"], table_rows),
    })


def runtime_chart(rows, odes, caption_html):
    label_x, x0, x1 = 176.0, 184.0, 680.0
    top, pitch = 40.0, 24.0
    bottom = top + pitch * len(rows)
    vmax, step, n, dec = lin_domain(max(r["runtime_s"] for r in rows), 5)
    xs = Linear(0, vmax, x0, x1)

    parts = [
        legend([(1, "Baselines"), (2, "Trial entries")], x1, 16),
        x_grid(xs, lin_ticks(step, n, dec), top, bottom),
        text((x0 + x1) / 2, bottom + 40, f"Wall time for all {fmt.count(odes)} ODEs, seconds",
             anchor="middle"),
    ]
    for i, r in enumerate(rows):
        y = top + pitch * i
        slot = 1 if r["baseline"] else 2
        v = r["runtime_s"]
        parts.append(text(label_x, y + pitch / 2 + 4, r["label"], anchor="end"))
        parts.append(bar(x0, y + 1, xs(v) - x0, pitch - 2, slot, f'{r["label"]}: {fmt.sig(v)} s'))
    fastest = min(rows, key=lambda r: r["runtime_s"])
    slowest = max(rows, key=lambda r: r["runtime_s"])
    desc = (
        f"Horizontal bar chart of runtime in seconds for {len(rows)} benchmark entries, "
        f"baselines and trial entries as two series. Shortest: {fastest['label']} at "
        f"{fmt.sig(fastest['runtime_s'])} s. Longest: {slowest['label']} at "
        f"{fmt.sig(slowest['runtime_s'])} s."
    )
    return figure({
        "id": "novel-runtime",
        "height": int(bottom + 56),
        "title": "Benchmark runtime for each entry",
        "desc": desc,
        "inner": "".join(parts),
        "caption": caption_html,
        "table": table(["Entry", "Stages", "Runtime (s)"],
                       [[fmt.esc(r["label"]), fmt.count(r["stages"]), fmt.sig(r["runtime_s"])]
                        for r in rows]),
    })


def metrics_log_chart(per_epoch, caption_html):
    x0, x1, top, bottom = 72.0, 700.0, 52.0, 320.0
    mins = [p["min_max_error"] for p in per_epoch]
    meds = [p["median_max_error"] for p in per_epoch]
    e0 = min(p["epoch"] for p in per_epoch)
    e1 = max(p["epoch"] for p in per_epoch)
    # A decade of room under the lowest point for the reference line's label.
    lo, hi = log_domain(mins + meds + [min(mins) / 10])
    ys = Log(mv(*lo), mv(*hi), bottom, top)
    xs = Linear(e0, e1, x0, x1)
    ticks = [e0] + [e for e in range(10, e1 + 1, 10) if e > e0]
    best = min(per_epoch, key=lambda p: (p["min_max_error"], p["epoch"]))
    yb = ys(best["min_max_error"])

    parts = [
        legend([(1, "Lowest max_error in the epoch"), (2, "Median max_error in the epoch")], x1, 16),
        text(8, 38, "max_error (log scale)"),
        y_grid(ys, log_ticks(lo, hi), x0, x1),
        x_axis(xs, [(e, str(e)) for e in ticks], x0, x1, bottom),
        text((x0 + x1) / 2, bottom + 40, "Epoch", anchor="middle"),
        line(x0, yb, x1, yb, "rk-ref", "var(--text-2)", 1.5),
        text(x1, yb + 16, f"lowest in the log: {fmt.sig(best['min_max_error'])}, epoch {best['epoch']}",
             anchor="end"),
    ]
    parts += [dot(xs(p["epoch"]), ys(p["median_max_error"]), 2,
                  f"Epoch {p['epoch']}: median max_error {fmt.sig(p['median_max_error'])}")
              for p in per_epoch]
    parts += [dot(xs(p["epoch"]), ys(p["min_max_error"]), 1,
                  f"Epoch {p['epoch']}: lowest max_error {fmt.sig(p['min_max_error'])}")
              for p in per_epoch]
    desc = (
        f"Scatter plot on a log scale of the lowest and the median max_error in each of "
        f"{len(per_epoch)} epochs, two series. The lowest value in the log, "
        f"{fmt.sig(best['min_max_error'])}, is at epoch {best['epoch']}."
    )
    return figure({
        "id": "novel-metrics-log",
        "height": int(bottom + 56),
        "title": "Lowest and median max_error per epoch in the training log",
        "desc": desc,
        "inner": "".join(parts),
        "caption": caption_html,
        "table": table(["Epoch", "Lowest max_error", "Median max_error"],
                       [[fmt.count(p["epoch"]), fmt.sig(p["min_max_error"]),
                         fmt.sig(p["median_max_error"])] for p in per_epoch]),
    })
