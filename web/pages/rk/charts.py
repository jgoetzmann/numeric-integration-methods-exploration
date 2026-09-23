"""The six rk.html charts, built on the primitives in web.charts.

Each builder returns a chart dict for web.charts.figure.
"""

import datetime

from web import fmt
from web.charts import (Linear, Log, bar, dot, esc, legend, lin_domain, lin_ticks, line,
                        log_domain, log_ticks, mv, num, series_line, table, text, x_axis, x_grid,
                        y_grid)

RK4_ORDER = 4  # textbook order of the classical rk4 tableau (claims.json R5 limits)

_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

_WORDS = {0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
          6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
          11: "eleven", 12: "twelve"}

_WEIGHTING = {
    "magnitude": "magnitude",
    "equal_median_anchor": "median-anchor",
    "equal_reference_norm": "reference-norm",
}
_WEIGHTING_NOTE = {
    "magnitude": "(published)",
    "equal_median_anchor": "(equal weight)",
    "equal_reference_norm": "(weights rc_thermal)",
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


def claim_link(cid, inner):
    """A key phrase (already escaped HTML) linked to its claim on claims.html."""
    return f'<a href="claims.html#{esc(cid)}">{inner}</a>'


def label_of(mapping, key):
    return mapping.get(key, str(key).replace("_", " "))


def source_note(src):
    """A 'Source:' sentence linking the file a block was read from."""
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

    champ_row = next(r for r in discovered if r.get("is_champion"))
    best_row = next(r for r in classical if r["name"] == best)
    desc = (f"Scatter plot of held-out RMS error (log scale) against cycles per step for "
            f"{len(classical)} classical methods and {len(discovered)} discovered cell elites."
            f" The champion {champ['hash']} has the lowest error, "
            f"{fmt.sig(champ_row['heldout_error'])} at {champ_row['cycles']} cycles per step; "
            f"{best}, the best classical method, has {fmt.sig(best_row['heldout_error'])} "
            f"at {best_row['cycles']}.")

    worst_disc = max(r["heldout_error"] for r in discovered)
    best_cls = min(r["heldout_error"] for r in classical)
    if worst_disc < best_cls:
        apart = "Every discovered elite has lower error than every classical method. "
    else:
        apart = ""
    caption = (
        f"Held-out RMS error against cycles per step for the {word(len(classical))} classical "
        f"methods and the {fmt.count(len(discovered))} discovered cell elites of epoch 1, in Q15 "
        f"with floor rounding at the {fmt.count(setup['budget_cycles'])}-cycle budget, on the "
        f"analytic {code(setup['cost_model'])} cost model with magnitude weighting. Lower is "
        f"better. {apart}Elites were picked on these errors, so they carry selection bias."
        + source_note(fr.get("source"))
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
        if w in _WEIGHTING_NOTE:
            parts.append(text(cx, B + 34, _WEIGHTING_NOTE[w], anchor="middle", muted=True))
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
        # Every cell is labelled, so neither weighting scale shows without the other.
        labels.append(text(cx, cy - 9, fmt.ratio(c["ratio"]), anchor="middle"))
    parts.extend(labels)

    trows = [[esc(label_of(_WEIGHTING, c["weighting"])), esc(label_of(_BASIS, c["basis"])),
              fmt.ratio(c["ratio"]), fmt.ratio(c["lowest_leave_one_out_ratio"]),
              "yes" if c["champion_still_leads"] else "no"] for c in cells]

    def cell(w, b):
        return next((c for c in cells if c["weighting"] == w and c["basis"] == b), None)

    pub = cell("magnitude", "analytic") or cells[0]
    desc = (f"Dot plot of {len(cells)} cells, {len(weightings)} weightings by {len(bases)} cost "
            f"bases, on a log ratio axis with a reference line at 1. Above the line the champion "
            f"leads. The published cell is {fmt.ratio(pub['ratio'])}.")
    caption = (
        f"The ratio of the best classical method's held-out error to the champion's, for "
        f"{word(len(weightings))} weightings of the held-out problems and {word(len(bases))} cost "
        f"bases, in Q15 with floor rounding at the {fmt.count(budget)}-cycle budget, epoch 1. "
        f"Above 1 the champion leads."
    )
    pairs = []
    for w in ("magnitude", "equal_reference_norm", "equal_median_anchor"):
        a, t = cell(w, "analytic"), cell(w, "traced_whole_step")
        if a and t:
            name = label_of(_WEIGHTING, w)
            if w == "magnitude":
                name += " weighting, the published one,"
            else:
                name += " weighting"
            pairs.append(f"{name} gives {fmt.ratio(a['ratio'])} analytic and "
                         f"{fmt.ratio(t['ratio'])} traced")
    if pairs:
        joined = "; ".join(pairs)
        caption += " " + joined[0].upper() + joined[1:] + "."
    med_tr = cell("equal_median_anchor", "traced_whole_step")
    if med_tr and med_tr["ratio"] < 1:
        caption += (f" The rk-overview analysis reads the {fmt.ratio(med_tr['ratio'])} cell as "
                    f"that weighting magnifying the champion's pendulum error, not as the "
                    f"champion losing by that factor.")
    caption += (f" The traced whole-step basis uses the compiled step's cycle count only as the "
                f"budget denominator, and neither basis is the full cost of a step on a chip."
                + source_note(cf.get("source")))
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
    plotted = [p for p in probs if not p.get("champion_overflowed")]
    run = list(val.get("classical_methods_run", []))
    n_run = word(len(run)) if run else ""
    best_label = f"best of {n_run} classical methods" if run else "best classical method"
    series = [
        (1, best_label, lambda p: p["best_classical_q15"],
         lambda p: (f"{p['problem']}: best classical method {p['best_classical']}, "
                    f"Q15 error {fmt.sig(p['best_classical_q15'], 4)}")),
        (2, f"champion {champ}", lambda p: p["champion_q15"],
         lambda p: f"{p['problem']}: champion {champ}, Q15 error {fmt.sig(p['champion_q15'], 4)}"),
    ]
    H, inner = _row_dotplot(
        probs, plotted, series,
        f"Q15 error, floor rounding, {fmt.count(budget)}-cycle budget (log scale)",
        lambda p: "champion overflowed: not plotted")

    trows = []
    for p in probs:
        if p.get("champion_overflowed"):
            champ_cell = "overflow"
            disc_cell = "overflow"
        else:
            champ_cell = fmt.sig(p["champion_q15"], 4)
            disc_cell = fmt.sig(p["best_discovered_q15"], 4)
        bc = fmt.sig(p["best_classical_q15"], 4)
        trows.append([code(p["problem"]), "yes" if p.get("stiff") else "no", champ_cell,
                      code(p["best_classical"]), bc, disc_cell, esc(p.get("winner_kind", ""))])

    over = _overflowed(probs)
    over_names = and_list([code(p["problem"]) for p in over])
    desc = (f"Dot plot, one row per out-of-sample problem, of Q15 error on a log axis: the "
            f"champion {champ} against the {best_label} run on that problem. "
            f"{len(plotted)} problems are plotted.")
    desc += " " + ", ".join(p["problem"] for p in over) + " is not plotted: the champion overflowed."
    run_names = f" run ({and_list([code(m) for m in run])})" if run else ""
    caption = (
        f"Q15 error with floor rounding at the {fmt.count(budget)}-cycle budget on the "
        f"out-of-sample problems: the champion {code(champ)} against the {best_label}{run_names} "
        f"on each problem. Lower is better."
    )
    other = [p["problem"] for p in plotted
             if p.get("best_discovered_q15") is not None
             and p["best_discovered_q15"] != p["champion_q15"]]
    n_tried = word(val["discovered_methods_run"])
    if other:
        caption += (f" On {and_list([code(n) for n in other])} the best of the {n_tried} "
                    f"discovered methods tried is not the champion; the data table gives its "
                    f"error beside the others.")
    if over:
        rows_word = "that problem has" if len(over) == 1 else "those problems have"
        caption += f" The champion overflowed on {over_names}, so {rows_word} no points."
    caption += source_note(val.get("source"))
    return {
        "id": "rk-validation-q15",
        "height": H,
        "title": "Out-of-sample Q15 error, champion against best classical method",
        "desc": desc,
        "inner": inner,
        "caption": caption,
        "table": table(["Problem", "Stiff", "Champion Q15 error", "Best classical method",
                        "Its Q15 error", "Best discovered Q15 error",
                        "Lower error, best discovered against best classical"], trows),
    }


def validation_f64_chart(rk):
    """B24, float64 half: champion against rk4, each at its budgeted step count."""
    val = rk["validation"]
    probs = val["problems"]
    champ = rk["champion"]["hash"]
    budget = rk["setup"]["budget_cycles"]
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
        f"float64 error at the {fmt.count(budget)}-cycle budget (log scale)",
        lambda p: "neither finished at its budgeted step size: not plotted")

    def steps(p, key):
        return fmt.count(p[key]) if p.get(key) is not None else ""

    trows = []
    for p in probs:
        if p.get("champion_float64") is not None:
            c_cell = fmt.sig(p["champion_float64"])
        elif p.get("champion_overflowed"):
            c_cell = "overflow in Q15, no float64 result"
        else:
            c_cell = "no float64 result"
        if p.get("rk4_float64") is not None:
            r_cell = fmt.sig(p["rk4_float64"])
        elif p.get("champion_overflowed"):
            r_cell = "overflow in Q15, no float64 result"
        else:
            r_cell = "no float64 result"
        trows.append([code(p["problem"]), "yes" if p.get("stiff") else "no",
                      steps(p, "champion_steps"), c_cell, steps(p, "rk4_steps"), r_cell])

    over = [p for p in probs if p not in plotted]
    over_names = and_list([code(p["problem"]) for p in over])
    gap = rk["float64_gap"]
    desc = (f"Dot plot, one row per out-of-sample problem, of float64 error on a log axis: the "
            f"champion {champ} against rk4, each at the step count the {fmt.count(budget)}-cycle "
            f"budget gives it. {len(plotted)} problems are plotted. The champion's error is "
            f"{fmt.ratio(gap['champion_over_rk4_min'])} to "
            f"{fmt.ratio(gap['champion_over_rk4_max'])} that of rk4.")
    ch = rk["champion"]
    caption = (
        f"Float64 error of the champion {code(champ)} and of {code('rk4')} on the "
        f"out-of-sample problems where both finish, each at the step count the "
        f"{fmt.count(budget)}-cycle budget gives it, so the cheaper champion takes more steps "
        f"than {code('rk4')}. Lower is better. The champion is order "
        f"{fmt.count(ch['order'])} and {code('rk4')} order {fmt.count(RK4_ORDER)}."
    )
    if over:
        rows_word = "it has" if len(over) == 1 else "they have"
        caption += (f" At their budgeted step sizes neither the champion nor {code('rk4')} "
                    f"finished {over_names}, in Q15 or in float64, so {rows_word} no points.")
    caption += source_note(gap["source"])
    return {
        "id": "rk-validation-f64",
        "height": H,
        "title": "Out-of-sample float64 error, champion against rk4",
        "desc": desc,
        "inner": inner,
        "caption": caption,
        "table": table(["Problem", "Stiff", "Champion steps", "Champion float64 error",
                        "rk4 steps", "rk4 float64 error"], trows),
    }


def _floor_round_methods(rk, search):
    modes = ["floor", "round_to_nearest"]
    names = [r["name"] for r in rk["frontier"]["classical"] if r["name"] in search["floor"]]
    return modes, names


def floor_round_chart(rk):
    """B25: search_rms per method under both rounding modes, two series."""
    fvr = rk["floor_vs_round"]
    search = fvr["search_rms"]
    held = fvr["heldout_rms"]
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
    headers += [f"Held-out, {esc(label_of(_MODE, m))} (not plotted)" for m in modes]
    trows = []
    for name in names:
        row = [code(name)] + [fmt.sig(search[m][name]) for m in modes]
        row += [fmt.sig(held[m][name]) for m in modes]
        trows.append(row)

    desc = (f"Grouped bar chart of search-set RMS error for {len(names)} classical methods under "
            f"{' and '.join(label_of(_MODE, m) for m in modes)}.")
    model = fvr.get("cost_model") or rk["setup"]["cost_model"]
    caption = (
        f"Search-set RMS error of {word(len(names))} classical methods in Q15 at the "
        f"{fmt.count(budget)}-cycle budget on the {code(model)} cost model, under floor rounding "
        f"and under round-to-nearest, with no extra cycles charged for round-to-nearest. Lower "
        f"is better. The held-out errors of the same runs are in the data table only."
        + source_note(fvr.get("source"))
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
    down = ep["epoch2"]["down_days"]
    a = min(max(_day_index(d0, down["from"]), 0.0), float(span))
    b = min(max(_day_index(d0, down["to"]), 0.0), float(span))
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
        f"log scale. Epoch 1 and epoch 2 were scored under different verifier hashes and cost "
        f"models, so they are separate series."
    )
    caption += (f" The shaded band marks {esc(fmt.day(down['from']))} to "
                f"{esc(fmt.day(down['to']))}, when the run was stopped.")
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
