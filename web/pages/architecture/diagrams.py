"""Inline SVG diagrams for architecture.html: arch-rk and arch-novel.

Both diagrams use a 360-unit-wide viewBox laid out top to bottom, so that on a
360px phone the 12 and 13 unit text renders close to its nominal size. Every
fill and stroke is a CSS custom property, currentColor or none, so the diagrams
follow the light and dark tokens in style.css. Every number drawn comes from
the data dict through web.fmt.
"""

from web import fmt

WIDTH = 360
LINE = 16
STEP_H = 30
MAX_WIDTH_PX = 440

RK_ID = "arch-rk"
NOVEL_ID = "arch-novel"

# Starts the line that marks a part of the 2025 pipeline that broke.
FLAW = "Flaw:"


# ---------------------------------------------------------------- helpers

def and_list(items):
    items = list(items)
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def trial_span(nums):
    """'12 to 15', or '1 to 4, 6, 8 and 9': runs of three or more collapse to 'a to b'."""
    groups = []
    for n in sorted(nums):
        if groups and n == groups[-1][-1] + 1:
            groups[-1].append(n)
        else:
            groups.append([n])
    parts = []
    for g in groups:
        if len(g) >= 3:
            parts.append(f"{fmt.count(g[0])} to {fmt.count(g[-1])}")
        else:
            parts.extend(fmt.count(v) for v in g)
    return and_list(parts)


_STAGE_WORDS = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven"}


def rk_numbers(rk):
    eng = rk["engineering"]
    e1 = rk["epochs"]["epoch1"]
    e2 = rk["epochs"]["epoch2"]
    return {
        "budget": fmt.count(rk["setup"]["budget_cycles"]),
        "files": fmt.count(eng["verifier_files"]),
        "gate": fmt.count(eng["golden_gate_cases"]),
        "tests": fmt.count(eng["tests_collected"]),
        "tests_on": fmt.day(eng["tests_collected_on"]),
        "e1_hash": e1["verifier_hash"],
        "e1_files": fmt.count(e1["verifier_files"]),
        "e1_records": fmt.count(e1["records"]),
        "e1_prepin": fmt.count(sum(n for h, n in e1["verifier_hash_counts"].items()
                                   if h != e1["verifier_hash"])),
        "e2_hash": e2["verifier_hash"],
        "e2_files": fmt.count(e2["verifier_files"]),
        "heldout": list(rk["setup"]["heldout_problems"]),
    }


def novel_numbers(novel):
    rows = novel["trials"]["rows"]
    rk4 = sorted(novel["trials"]["equal_to_rk4"])
    dp = sorted(novel["trials"]["equal_to_dormand_prince"])
    evo = sorted(rk4 + dp)
    for r in rows:
        if str(r.get("folder", "")).endswith("novelty_v2"):
            t16 = r["trial"]
    nn = sorted(r["trial"] for r in rows if r["trial"] not in evo and r["trial"] != t16)
    nn_saved = sorted(
        r["trial"] for r in rows if r["trial"] in nn and r.get("stages") is not None
    )
    ac = novel["audit_counts"]
    missing = sorted(set(ac["evaluation_ode_families"]) - set(ac["reference_solver_families"]))
    bench = novel["benchmark"]

    # Generator trials that saved the same A and b, grouped, in trial order.
    by_trial = {r["trial"]: r for r in rows}
    groups = []
    seen = set()
    for t in nn_saved:
        if t in seen:
            continue
        g = sorted({t} | set(by_trial[t].get("identical_to_trials") or []))
        seen.update(g)
        if len(g) > 1:
            groups.append(g)
    same = []
    for i, g in enumerate(groups):
        stages = _STAGE_WORDS.get(by_trial[g[0]]["stages"], fmt.count(by_trial[g[0]]["stages"]))
        verb = "saved " if i == 0 else ""
        same.append(f"trials {trial_span(g)} {verb}the same {stages}-stage A and b")
    same_ab = and_list(same) if same else "the saved tables repeat"

    ckpt = novel["evolution_checkpoints"]["rows"]
    loss = sorted({r["epochs_with_surrogate_loss"] for r in ckpt})
    ep = sorted({r["epochs"] for r in ckpt})
    bench_by = {r["id"]: r for r in bench["rows"]}
    return {
        "rk4_trials": and_list(fmt.count(t) for t in rk4),
        "dp_trials": and_list(fmt.count(t) for t in dp),
        "evo_span": trial_span(evo),
        "copy_span": trial_span(rk4 + dp),
        "t16": fmt.count(t16),
        "nn_span": trial_span(nn),
        "nn_saved_span": trial_span(nn_saved),
        "same_ab": same_ab,
        "ckpt_span": trial_span(r["trial"] for r in ckpt),
        "ckpt_loss": (fmt.count(loss[0]) if len(loss) == 1
                      else f"{fmt.count(loss[0])} to {fmt.count(loss[-1])}"),
        "ckpt_epochs": fmt.count(ep[-1]),
        "rk4_error": fmt.sig(bench_by["baseline_rk4"]["mean_max_error"]),
        "dp_error": fmt.sig(bench_by["baseline_rk45_dormand_prince"]["mean_max_error"]),
        "seed": fmt.count(ac["random_generator_seed"]),
        "ref_families": fmt.count(ac["reference_solver_family_count"]),
        "eval_families": fmt.count(ac["evaluation_ode_family_count"]),
        "missing_families": missing,
        "train_families": fmt.count(ac["training_ode_family_count"]),
        "clip": fmt.sig(novel["metrics_log"]["composite_score_distinct_values"][0]),
        "logged": fmt.count(novel["metrics_log"]["rows"]),
        "success": fmt.pct(bench["success_rate_distinct_values"][0]),
        "methods": fmt.count(bench["methods"]),
        "odes": fmt.count(bench["odes"]),
        "scorable": fmt.count(bench["scorable_odes"]),
    }


def _n(v):
    return f"{v:g}"


def _text(x, y, s, size=12, weight=None, fill="currentColor", anchor=None, rotate=False):
    attrs = [f'x="{_n(x)}"', f'y="{_n(y)}"', f'font-size="{size}"', f'fill="{fill}"']
    if weight:
        attrs.append(f'font-weight="{weight}"')
    if anchor:
        attrs.append(f'text-anchor="{anchor}"')
    if rotate:
        attrs.append(f'transform="rotate(-90 {_n(x)} {_n(y)})"')
    return f"<text {' '.join(attrs)}>{fmt.esc(s)}</text>"


def _rect(x, y, w, h, cls, fill, stroke, stroke_width, rx=4, extra=""):
    return (
        f'<rect class="{cls}" x="{_n(x)}" y="{_n(y)}" width="{_n(w)}" height="{_n(h)}" '
        f'rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{stroke_width}"{extra}/>'
    )


def _box(x, y, w, title, details=(), audit=None):
    """A labelled box: bold title line(s), detail lines, optional flaw line.

    A box with a flaw line gets a heavy outline in --series-2; the flaw line
    itself starts with FLAW so the mark never rests on color alone.
    Returns (svg, height).
    """
    titles = [title] if isinstance(title, str) else list(title)
    lines = [(t, 13, "600", "currentColor") for t in titles]
    lines += [(d, 12, None, "var(--text-2)") for d in details]
    if audit:
        lines.append((audit, 12, "700", "currentColor"))
    h = 14 + LINE * len(lines)
    if audit:
        out = [_rect(x, y, w, h, "node node-audit", "var(--surface)", "var(--series-2)", "2.5")]
    else:
        out = [_rect(x, y, w, h, "node", "var(--surface)", "var(--text-2)", "1")]
    base = y + 19
    for s, size, weight, fill in lines:
        out.append(_text(x + 10, base, s, size=size, weight=weight, fill=fill))
        base += LINE
    return "".join(out), h


def _step(x, y, w, name, detail):
    return (
        _rect(x, y, w, STEP_H, "node", "var(--surface)", "var(--text-2)", "1")
        + f'<text x="{_n(x + 10)}" y="{_n(y + 19)}" font-size="12" fill="var(--text-2)">'
        + f'<tspan font-weight="600" fill="currentColor">{fmt.esc(name)}:</tspan> '
        + f"{fmt.esc(detail)}</text>"
    )


def _group(x, y, w, h, label):
    return _rect(
        x, y, w, h, "group", "var(--grid)", "var(--text-2)", "1", rx=8,
        extra=' fill-opacity="0.35"',
    ) + _text(x + 10, y + 18, label, size=13, weight="700")


def _frame(x, y, w, h, label):
    return _rect(x, y, w, h, "frame", "none", "var(--text-2)", "1", rx=6) + _text(
        x + 10, y + 18, label, size=13, weight="700"
    )


def _edge(points, marker=None):
    d = "M" + " L".join(f"{_n(px)} {_n(py)}" for px, py in points)
    tail = f' marker-end="url(#{marker})"' if marker else ""
    return (
        f'<path class="edge" d="{d}" fill="none" stroke="var(--text-2)" '
        f'stroke-width="1.5"{tail}/>'
    )


def _defs(marker):
    return (
        f'<defs><marker id="{marker}" viewBox="0 0 10 10" refX="10" refY="5" '
        f'markerWidth="6" markerHeight="6" orient="auto">'
        f'<path d="M0 0 L10 5 L0 10 z" fill="var(--text-2)"/></marker></defs>'
    )


def _svg(fig_id, height, title, desc, marker, layers):
    return (
        f'<svg viewBox="0 0 {WIDTH} {_n(height)}" role="img" '
        f'aria-labelledby="{fig_id}-title {fig_id}-desc" '
        f'style="display:block;width:100%;max-width:{MAX_WIDTH_PX}px;height:auto;margin:0 auto">'
        f'<title id="{fig_id}-title">{fmt.esc(title)}</title>'
        f'<desc id="{fig_id}-desc">{fmt.esc(desc)}</desc>'
        f"{_defs(marker)}{''.join(layers)}</svg>"
    )


# ---------------------------------------------------------------- arch-rk

def arch_rk(data):
    """The rk run: host machine, container and outputs, top to bottom."""
    num = rk_numbers(data["rk"])
    marker = f"{RK_ID}-arrow"
    back, edges, nodes, labels = [], [], [], []

    gx, gw = 6, 328              # group boxes span 6..334
    ix, iw = 16, 308             # inner boxes span 16..324
    hw = (iw - 12) // 2          # two boxes per row
    x2 = ix + hw + 12
    tw = (iw - 20) // 3          # three boxes per row
    cx = ix + iw // 2
    push_x = 342                 # channel right of the groups for the push line

    # host machine
    host_y = 6
    row_y = host_y + 28
    s, h_stats = _box(ix, row_y, hw, "stats file",
                      ["written on the host,", "so a dead container", "still gets reported"])
    nodes.append(s)
    s, h_start = _box(x2, row_y, hw, "start command",
                      ["run by hand after", "a reboot; starts the", "run and the watchdog"])
    nodes.append(s)
    row_h = max(h_stats, h_start)
    wd_y = row_y + row_h + 16
    s, h_wd = _box(ix, wd_y, iw, "watchdog",
                   ["pause guard: battery or foreground load",
                    "pushes to GitHub; resumes its own stops"])
    nodes.append(s)
    start_cx = x2 + hw // 2
    edges.append(_edge([(start_cx, row_y + row_h), (start_cx, wd_y)], marker))
    host_h = wd_y + h_wd + 10 - host_y
    back.append(_group(gx, host_y, gw, host_h, "host machine"))

    # container
    c_y = host_y + host_h + 26
    wd_x = ix + 56
    edges.append(_edge([(wd_x, wd_y + h_wd), (wd_x, c_y)], marker))
    labels.append(_text(wd_x + 8, wd_y + h_wd + 18, "kill, stop, pause, resume",
                        fill="var(--text-2)"))

    y = c_y + 28
    s, h = _box(ix, y, iw, "harness", ["mounted read-only; no GitHub credentials inside"])
    nodes.append(s)
    prev_end = y + h
    chain = [
        ("verifier", [f"sha256 pinned over {num['files']} files, checked",
                      "at every start, stored in every record"]),
        ("golden gate", [f"{num['gate']} golden and canary cases must pass",
                         "before any cycle runs"]),
    ]
    for title, details in chain:
        y = prev_end + 16
        edges.append(_edge([(cx, prev_end), (cx, y)], marker))
        s, h = _box(ix, y, iw, title, details)
        nodes.append(s)
        prev_end = y + h

    r_y = prev_end + 16
    edges.append(_edge([(cx, prev_end), (cx, r_y)], marker))
    steps = [
        ("directive", "model or fixed fallback"),
        ("search", "enumerate, or CMA-ES"),
        ("verify", "exact rational order conditions"),
        ("score", f"Q15 floor, {num['budget']}-cycle budget"),
        ("append", "each result to the archive"),
    ]
    loop_x = ix + 20
    sx = ix + 34
    sw = iw - 34 - 10
    step_gap = 14
    sy = r_y + 28
    step_ys = []
    for i, (name, detail) in enumerate(steps):
        step_ys.append(sy)
        nodes.append(_step(sx, sy, sw, name, detail))
        if i < len(steps) - 1:
            mid = sx + sw // 2
            edges.append(_edge([(mid, sy + STEP_H), (mid, sy + STEP_H + step_gap)], marker))
        sy += STEP_H + step_gap
    r_end = step_ys[-1] + STEP_H + 10
    back.append(_frame(ix, r_y, iw, r_end - r_y, "runner: one cycle"))
    y_top = step_ys[0] + STEP_H // 2
    y_bot = step_ys[-1] + STEP_H // 2
    edges.append(_edge([(sx, y_bot), (loop_x, y_bot), (loop_x, y_top), (sx, y_top)], marker))
    labels.append(_text(loop_x - 7, (y_top + y_bot) / 2, "next cycle",
                        fill="var(--text-2)", anchor="middle", rotate=True))

    side_y = r_end + 14
    side = [
        (["lanes and", "side tracks"], ["kept off", "the archive"]),
        (["hypothesis", "ledger"], ["verdicts set", "by code"]),
        (["literature", "digests"], ["written by", "the model"]),
    ]
    side_h = 0
    for i, (t, d) in enumerate(side):
        bx = ix + i * (tw + 10)
        s, h = _box(bx, side_y, tw, t, d)
        nodes.append(s)
        edges.append(_edge([(bx + tw // 2, r_end), (bx + tw // 2, side_y)]))
        side_h = max(side_h, h)
    c_end = side_y + side_h + 10
    back.append(_group(gx, c_y, gw, c_end - c_y, "container (Docker)"))

    # outputs
    o_y = c_end + 24
    arch_y = o_y + 28
    gap_x = ix + 2 * tw + 10 + 5          # the gap between the second and third side box
    edges.append(_edge([(gap_x, c_end), (gap_x, arch_y)], marker))
    labels.append(_text(gap_x + 8, c_end + 16, "every cycle", fill="var(--text-2)"))
    s, h_arch = _box(ix, arch_y, iw, "rk-work archive",
                     ["append-only JSON lines, one file per day"])
    nodes.append(s)
    site_y = arch_y + h_arch + 16
    s, h_f = _box(ix, site_y, hw, "findings site", ["rebuilt every cycle,", "no JavaScript"])
    nodes.append(s)
    s, h_o = _box(x2, site_y, hw, "overview site", ["built by hand from", "the run's data"])
    nodes.append(s)
    edges.append(_edge([(ix + hw // 2, arch_y + h_arch), (ix + hw // 2, site_y)], marker))
    edges.append(_edge([(x2 + hw // 2, arch_y + h_arch), (x2 + hw // 2, site_y)], marker))
    o_end = site_y + max(h_f, h_o) + 10
    back.append(_group(gx, o_y, gw, o_end - o_y, "outputs (GitHub repos)"))

    # the watchdog's push, down the right-hand channel into the archive
    wd_mid = wd_y + h_wd // 2
    push_end = arch_y + h_arch // 2
    edges.append(_edge([(ix + iw, wd_mid), (push_x, wd_mid), (push_x, push_end),
                        (ix + iw, push_end)], marker))
    labels.append(_text(push_x + 14, (wd_mid + push_end) / 2, "push to GitHub",
                        fill="var(--text-2)", anchor="middle", rotate=True))

    height = o_end + 6
    title = "Architecture of the rk run"
    desc = (
        "Three groups, stacked top to bottom. The host machine holds a stats file written on "
        "the host, a start command that a person runs by hand after a reboot, and a watchdog "
        "with a pause guard. The watchdog can kill, stop, pause and resume the container, and it "
        "pushes the outputs to GitHub. In the container, the harness is mounted read-only with "
        "no GitHub credentials inside, the "
        f"verifier's sha256 over {num['files']} pinned files is checked at start, and "
        f"{num['gate']} golden and canary cases must pass. The runner then repeats one cycle: a "
        "directive from a model or a fixed fallback, a search by enumeration or CMA-ES, "
        "verification with exact rational order conditions, scoring in Q15 with floor rounding "
        f"at a {num['budget']}-cycle budget, and an append to the archive. Beside the runner sit "
        "the lanes and side tracks, the hypothesis ledger and the literature digests. The "
        "outputs are the rk-work archive, the findings site rebuilt from it every cycle, and the "
        "overview site built from it by hand."
    )
    return _svg(RK_ID, height, title, desc, marker, back + edges + nodes + labels)


# ---------------------------------------------------------------- arch-novel

def arch_novel(data):
    """The 2025 ML project's pipeline, with the parts that broke labelled in text."""
    num = novel_numbers(data["novel"])
    marker = f"{NOVEL_ID}-arrow"
    edges, nodes, labels = [], [], []

    bx, bw = 34, 288             # boxes span 34..322
    loop_x = 20                  # selection loop channel on the left
    bus_x = 340                  # candidate bus on the right
    hw = (bw - 12) // 2
    x2 = bx + hw + 12

    sources = [
        (f"generator (trials {num['nn_span']})",
         ["an MLP whose optimizer is never stepped",
          f"fallback: a random table reseeded to {num['seed']}"],
         f"{FLAW} never trained (N4)"),
        (f"evolution (trials {num['evo_span']})",
         ["population seeded with RK4 or",
          "Dormand-Prince and perturbed copies"],
         f"{FLAW} saved table stays the seed (N2)"),
        (f"random sampling (trial {num['t16']})",
         ["random tables, no mutation or crossover"],
         f"{FLAW} fitness read a missing field (N7)"),
    ]
    y = 8
    mids = []
    for title, details, audit in sources:
        s, h = _box(bx, y, bw, title, details, audit)
        nodes.append(s)
        mids.append(y + h // 2)
        y += h + 12
    src_end = y - 12
    evo_mid = mids[1]

    bus_y = src_end + 20
    row_y = bus_y + 18
    step_cx = bx + hw // 2
    ref_cx = x2 + hw // 2
    edges.append(_edge([(bx + bw, mids[0]), (bus_x, mids[0]), (bus_x, bus_y),
                        (step_cx, bus_y), (step_cx, row_y)], marker))
    for m in mids[1:]:
        edges.append(_edge([(bx + bw, m), (bus_x, m)]))
    labels.append(_text((step_cx + bus_x) / 2, bus_y - 5, "candidate tables",
                        fill="var(--text-2)", anchor="middle"))

    s, h_s = _box(bx, row_y, hw, "stepper",
                  ["fixed step; uses", "only the explicit", "part of a table"],
                  f"{FLAW} a bug (N5)")
    nodes.append(s)
    s, h_r = _box(x2, row_y, hw, "reference solver",
                  ["Dormand-Prince", "(SciPy RK45),",
                   f"{num['ref_families']} of {num['eval_families']} test families"],
                  f"{FLAW} artifact (N6)")
    nodes.append(s)
    row_end = row_y + max(h_s, h_r)

    c_y = row_end + 32
    edges.append(_edge([(step_cx, row_end), (step_cx, c_y)], marker))
    edges.append(_edge([(ref_cx, row_end), (ref_cx, c_y)], marker))
    mid_x = bx + bw // 2
    labels.append(_text(mid_x, row_end + 20, "error vs reference",
                        fill="var(--text-2)", anchor="middle"))

    s, h_c = _box(bx, c_y, bw, "composite score",
                  ["weighted accuracy, efficiency, stability",
                   f"clipped at {num['clip']}: all {num['logged']} logged scores are {num['clip']}"],
                  f"{FLAW} nothing left to select on (N2, N3)")
    nodes.append(s)
    c_mid = c_y + h_c // 2
    t_y = c_y + h_c + 18
    edges.append(_edge([(mid_x, c_y + h_c), (mid_x, t_y)], marker))
    s, h_t = _box(bx, t_y, bw, "best-table tracker",
                  ["replaces the saved table only on a", "strictly higher score"],
                  f"{FLAW} ties keep the seeded table (N2)")
    nodes.append(s)

    # the surrogate trains on the scores through the right-hand channel; nothing reads it
    u_y = t_y + h_t + 18
    s, h_u = _box(bx, u_y, bw, "surrogate",
                  ["an MLP trained by gradient descent", "on the scored candidates"],
                  f"{FLAW} nothing reads its output (N4)")
    nodes.append(s)
    c_right = c_y + h_c // 2
    u_mid = u_y + h_u // 2
    edges.append(_edge([(bx + bw, c_right), (bus_x, c_right), (bus_x, u_mid), (bx + bw, u_mid)],
                       marker))
    labels.append(_text(bus_x + 13, (c_right + u_mid) / 2, "trains on scores",
                        fill="var(--text-2)", anchor="middle", rotate=True))

    edges.append(_edge([(bx, c_mid), (loop_x, c_mid), (loop_x, evo_mid), (bx, evo_mid)], marker))
    labels.append(_text(loop_x - 6, (c_mid + evo_mid) / 2, "selection",
                        fill="var(--text-2)", anchor="middle", rotate=True))

    height = u_y + h_u + 10
    title = "Pipeline of the 2025 ML project and where it broke"
    desc = (
        f"Three sources propose Butcher tables: a generator (trials {num['nn_span']}) that is "
        f"never trained and falls back to a random table reseeded to {num['seed']}; evolution "
        f"(trials {num['evo_span']}) whose population is seeded with RK4 or Dormand-Prince; and "
        f"random sampling in trial {num['t16']}. The candidate tables and the baselines go to a "
        "fixed-step stepper that uses only the explicit part of a table, and its results are "
        f"compared with a reference solver, Dormand-Prince (SciPy RK45), which handles "
        f"{num['ref_families']} of the {num['eval_families']} test families. The error feeds a "
        f"composite score clipped at {num['clip']}, which feeds a best-table tracker and, "
        "through selection, the evolution loop. The scores also train a surrogate model by "
        f"gradient descent, and nothing reads its output. Labels starting with \"{FLAW}\" "
        f"mark breaks at the generator, the evolution seed, trial {num['t16']}'s fitness, the "
        "stepper, the reference solver's coverage, the clipped score, the tracker and the "
        "surrogate."
    )
    return _svg(NOVEL_ID, height, title, desc, marker, edges + nodes + labels)
