"""Epochs and research page (epochs.html): B29, B36, and B9, B11, B12, B19, B20 for its output."""
import re
from datetime import datetime

from web import fmt
from web.pages.epochs import timeline

SLUG = "epochs.html"
TITLE = "Epochs and research"
DESCRIPTION = (
    "When the rk run's two epochs ran, what happened between them, what stopped epoch 2 for "
    "five days, and how the run checks its own claims."
)

FINDINGS_URL = "https://jgoetzmann.github.io/rk-findings/"

_WORDS = (
    "zero", "one", "two", "three", "four", "five", "six",
    "seven", "eight", "nine", "ten", "eleven", "twelve",
)

_METHODS = ("euler", "midpoint", "heun2", "ralston2", "heun3", "kutta3", "rk4", "rk38")
_METHOD_RE = re.compile(r"\b(" + "|".join(_METHODS) + r")\b")

# Table labels for the counterfactual grid. The data keys call both non-magnitude
# weightings "equal", but only the median-anchor one gives the problems equal weight.
_WEIGHTING_LABELS = {
    "magnitude": "magnitude",
    "equal_median_anchor": "median anchor (equal weight)",
    "equal_reference_norm": "reference norm",
}
# The same weightings named inside a sentence.
_WEIGHTING_NAMES = {
    "magnitude": "magnitude",
    "equal_median_anchor": "median-anchor",
    "equal_reference_norm": "reference-norm",
}
_BASIS_LABELS = {
    "analytic": "analytic",
    "traced_whole_step": "traced whole step",
}
# Terms in the definition list above the grid table.
_TERMS = {
    "magnitude": "Magnitude weighting",
    "equal_median_anchor": "Median-anchor weighting (equal weight)",
    "equal_reference_norm": "Reference-norm weighting",
    "analytic": "Analytic basis",
    "traced_whole_step": "Traced whole-step basis",
}
# Order in which the grid prose and the re-ranking sentence name the weightings.
_WEIGHTING_ORDER = ("magnitude", "equal_reference_norm", "equal_median_anchor")


def _word(n):
    n = int(n)
    if 0 <= n < len(_WORDS):
        return _WORDS[n]
    return fmt.count(n)


def _cap(s):
    return s[:1].upper() + s[1:]


def _claim(cid):
    return f'<a href="claims.html#{cid}">claim {cid}</a>'


def _code(s):
    return f"<code>{fmt.esc(s)}</code>"


def _prose(s):
    """Escape a sentence taken from data and put method identifiers in <code>."""
    return _METHOD_RE.sub(r"<code>\1</code>", fmt.esc(s))


def _stamp(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _utc(s):
    """The HH:MM part of an ISO timestamp from the data, which stores UTC."""
    return fmt.esc(str(s)[11:16]) + " UTC"


def _join(items):
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _trace_row(rk, name):
    for m in rk["trace"]["methods"]:
        if m["name"] == name:
            return m


def _lead():
    return (
        "<p>The rk run is split into epochs. Every scored record stores the hash of the pinned "
        f"files that do the scoring ({_claim('R11')}). When one of those files has to change, "
        "the run starts a new epoch and leaves the old archive as it was. There have been two "
        "epochs so far.</p>"
    )


def _dates(data):
    ml = data["novel"]["repo"]
    e1 = data["rk"]["epochs"]["epoch1"]
    return (
        "<section>\n"
        '<h2 id="dates">Timeline</h2>\n'
        f"<p>The 2025 ML project, <code>Novel-Numerical-Integration-Methods</code>, committed its "
        f"main work between {fmt.day(ml['active_from'])} and {fmt.day(ml['active_to'])}. The rk "
        f"run started almost a year later, on {fmt.day(e1['started'])}.</p>\n"
        + timeline.figure(data)
        + "\n</section>"
    )


def _archive_table(days, caption):
    rows = "\n".join(
        f"<tr><td>{fmt.day(d['day'])}</td><td>{fmt.count(d['records'])}</td>"
        f"<td>{fmt.count(d['cumulative'])}</td></tr>"
        for d in days
    )
    return (
        f'<details class="archive-days"><summary>{fmt.esc(caption)}</summary>\n'
        '<div class="table-wrap" style="overflow-x:auto">\n<table>\n'
        "<thead><tr><th>Day</th><th>Records</th><th>Cumulative</th></tr></thead>\n"
        f"<tbody>\n{rows}\n</tbody>\n</table>\n</div>\n</details>"
    )


def _hash_sentence(e1):
    """Which verifier hash epoch 1's records carry, naming the records written before the pin."""
    main = e1["verifier_hash"]
    others = sorted(
        (h, n) for h, n in e1.get("verifier_hash_counts", {}).items() if h != main and n
    )
    if not others:
        return f"All of them carry verifier hash {_code(main)}."
    if len(others) == 1:
        h, n = others[0]
        return (
            f"All but {fmt.count(n)} of them carry verifier hash {_code(main)}. Those "
            f"{fmt.count(n)} were written minutes before that pin was set and carry {_code(h)}."
        )
    n = sum(v for _, v in others)
    return (
        f"All but {fmt.count(n)} of them carry verifier hash {_code(main)}; the rest were "
        "written before that pin was set."
    )


def _epoch1(data):
    rk = data["rk"]
    e1 = rk["epochs"]["epoch1"]
    ch = rk["champion"]
    fr = rk["frontier"]
    setup = rk["setup"]
    n_classical = len(fr["classical"])
    n_heldout = len(setup["heldout_problems"])
    p1 = (
        f"<p>Epoch 1 ran from {fmt.day(e1['started'])} to {fmt.day(e1['stopped'])} "
        f"({_claim('R12')}). It completed {fmt.count(e1['cycles_run'])} search cycles over "
        f"{fmt.count(e1['archive_day_count'])} days of archive and wrote "
        f"{fmt.count(e1['records'])} scored records. {_hash_sentence(e1)} When it stopped, "
        f"the search was in phase {fmt.count(e1['phase_at_stop'])} and "
        f"{fmt.count(e1['occupied_cells'])} cells of the archive grid held an elite.</p>"
    )
    p_auto = (
        "<p>The run is autonomous in a narrow sense: no person chose what the search tried or "
        "how it scored, and the pinned scorer never changed. It was not free of human "
        f"operation. The runner started {fmt.count(e1['events']['runner_started'])} times "
        "during epoch 1 as people deployed changes to the harness code outside the pinned "
        "files.</p>"
    )
    found = ch["found_at_cycle"]
    later_orders = sorted(
        {d["order"] for d in fr["discovered"] if d["first_cycle"] > found and d["order"] > ch["order"]}
    )
    orders = ""
    if later_orders:
        orders = ", including elites of " + _join(f"order {fmt.count(o)}" for o in later_orders)
    p2 = (
        f"<p>Its main result came early. The champion, {_code(ch['hash'])}, appeared at cycle "
        f"{fmt.count(found)}, and no later cycle in epoch 1 lowered the best held-out error "
        f"({_claim('R6')}). The search kept filling and improving other cells: "
        f"{fmt.count(fr['discovered_first_seen_after_champion'])} of the "
        f"{fmt.count(fr['cells_held_by_discovered'])} discovered cell elites appeared after "
        f"cycle {fmt.count(found)}{orders}. The last new cell was filled on "
        f"{fmt.day(e1['last_new_cell_ts'])}, and the last improvement to any cell came on "
        f"{fmt.day(e1['last_improvement_ts'])}.</p>"
    )
    p3 = (
        f"<p>Inside Q15 fixed point with floor rounding, at the {fmt.count(setup['budget_cycles'])}"
        f"-cycle budget, the champion has {fmt.ratio(ch['lead'])} lower held-out error than "
        f"{_code(ch['best_classical'])}, the best of the {_word(n_classical)} classical methods "
        f"({_claim('R1')}). That figure uses the analytic cost model and magnitude weighting over "
        f"{_word(n_heldout)} held-out problems. It moves in both directions under other cost "
        'bases and weightings, as the <a href="#grid">counterfactual grid</a> below shows. It '
        "is also an epoch-1 figure, on the cost model the trace later found had <code>rk4</code> "
        "and <code>rk38</code> in the wrong order, and epoch 2 has not re-measured it. The full "
        'results are on the <a href="rk.html">rk run page</a>.</p>'
    )
    table = _archive_table(e1["archive_days"], "Epoch 1 records per archive day")
    return (
        "<section>\n"
        '<h2 id="epoch-1">Epoch 1</h2>\n'
        f"{p1}\n{p_auto}\n{p2}\n{p3}\n{table}\n"
        "</section>"
    )


def _overflow_cases(crosscheck):
    """The number of overflow cases the trace's crosscheck sentence states, or None."""
    m = re.search(r"\b(\d+) of them are cases where the Q15 primitives raise", crosscheck or "")
    return int(m.group(1)) if m else None


def _froze(data):
    rk = data["rk"]
    ep = rk["epochs"]
    e1 = ep["epoch1"]
    e2 = ep["epoch2"]
    model = rk["setup"]["cost_model"]
    rk4 = _trace_row(rk, "rk4")
    rk38 = _trace_row(rk, "rk38")
    overflow = _overflow_cases(rk["trace"].get("crosscheck"))
    overflow_text = ""
    if overflow is not None:
        overflow_text = (
            f", {fmt.count(overflow)} of them overflow cases where both stop at the same operation"
        )
    p1 = f"<p>{_prose(ep['why_epoch1_froze'])}</p>"
    p2 = (
        f"<p>A host-side audit did the compiling and tracing ({_claim('R7')}). Under the "
        f"epoch-1 rule with the fast multiplier ({_code(model)}), <code>rk4</code> cost "
        f"{fmt.count(rk4['analytic'][model])} cycles per step and <code>rk38</code> "
        f"{fmt.count(rk38['analytic'][model])}. The compiled step, counted over the same scope "
        f"the model prices, took {fmt.count(rk38['matched_scope'][model])} cycles for "
        f"<code>rk38</code> and {fmt.count(rk4['matched_scope'][model])} for <code>rk4</code>. "
        "The traced step matched the Python evaluator bit for bit in "
        f"{fmt.esc(rk['engineering']['trace_crosscheck'])} cases{overflow_text}. The emulator "
        "is instruction-accurate, not cycle-accurate: its cycle counts come from a timing table "
        "applied to the executed instructions, and nothing was measured on a physical chip.</p>"
    )
    p3 = (
        "<p>With the pinned files changed, the verifier hash moved from "
        f"{_code(e1['verifier_hash'])} over {fmt.count(e1['verifier_files'])} files to "
        f"{_code(e2['verifier_hash'])} over {fmt.count(e2['verifier_files'])}. The run did not "
        "rescore the epoch-1 archive under the new model. Results on this site come from "
        "epoch 1 unless they say otherwise.</p>"
    )
    p4 = (
        f"<p>Epoch 1's last cycle ran on {fmt.day(e1['stopped'])}, and epoch 2 started on "
        f"{fmt.day(e2['started'])}. The week between went to the boundary work: the trace, "
        "the change to the cost model and the pinned files, and the move of epoch 1's archive "
        "and documents under <code>epochs/1/</code> in <code>rk-work</code>, where they stay as "
        f"they were. Epoch 1 was frozen on {fmt.day(e1['frozen_at'])}, and epoch 2 began a new "
        "archive.</p>"
    )
    return (
        "<section>\n"
        '<h2 id="why-epoch-1-froze">Why epoch 1 froze</h2>\n'
        f"{p1}\n{p2}\n{p3}\n{p4}\n"
        "</section>"
    )


def _epoch2(data):
    e2 = data["rk"]["epochs"]["epoch2"]
    lanes = e2["lane_cycles"]
    down = e2["down_days"]
    days = e2["archive_days"]
    down_days = (_stamp(down["to"]) - _stamp(down["from"])).total_seconds() / 86400
    lane_text = (
        f"explicit {fmt.count(lanes['explicit'])}, adaptive "
        f"{fmt.count(lanes['adaptive'])}, implicit {fmt.count(lanes['implicit'])}"
    )
    day_text = " and ".join(
        f"{fmt.count(d['records'])} on {fmt.day(d['day'])}" for d in days
    )
    p1 = (
        f"<p>Epoch 2 started at {_utc(e2['started'])} on {fmt.day(e2['started'])} under "
        f"verifier hash {_code(e2['verifier_hash'])}. As of {fmt.day(e2['as_of'])} it had "
        f"reached cycle {fmt.count(e2['cycle'])} and written {fmt.count(e2['records'])} records "
        "to its own archive. That count comes from the running work tree, so it includes the "
        "day's archive file before the run commits it at the day's close. Its cycles rotate "
        f"among {_word(len(lanes))} lanes: the explicit lane scores candidates in Q15 into the "
        "archive, while the adaptive and implicit lanes measure how many cycles a float64 solve "
        "needs to reach a tolerance, and their results stay out of the archive. Cycles per lane "
        f"so far: {lane_text}.</p>"
    )
    p2 = (
        f"<p>From {_utc(down['from'])} on {fmt.day(down['from'])} to {_utc(down['to'])} on "
        f"{fmt.day(down['to'])} the run was down for about {_word(round(down_days))} days: "
        f"{_prose(down['why'])}. Epoch 2's archive therefore has records from only "
        f"{_word(len(days))} days so far: {day_text}.</p>"
    )
    p3 = (
        "<p>Two decisions followed that stop. The watchdog now resumes the stops it makes "
        "itself, once the condition behind the stop clears (decision D46). Decision D47 added a "
        "logon task that started the run after a reboot, and that task has since been removed. "
        "After a reboot the run is started by hand, with one command: "
        "<code>start-integration-harness</code>.</p>"
    )
    return (
        "<section>\n"
        '<h2 id="epoch-2">Epoch 2, as of the snapshot</h2>\n'
        f"{p1}\n{p2}\n{p3}\n"
        "</section>"
    )


def _premise_outcomes(pr):
    """(proceed, kill, neither) lists of (method, model) pairs, from the stored thresholds."""
    th = pr["thresholds"]
    proceed, kill, neither = [], [], []
    for method in sorted(pr["methods"], key=lambda m: (m != "rk4", m)):
        row = pr["methods"][method]
        for model in sorted(row["coefficient_fraction"]):
            frac = row["coefficient_fraction"][model]
            practical = row["crossover_practical"]
            if frac >= th["proceed_fraction"] and practical:
                proceed.append((method, model))
            elif frac < th["kill_fraction"] and not practical:
                kill.append((method, model))
            else:
                neither.append((method, model))
    return proceed, kill, neither


def _pairs_text(pairs, n_models):
    """'<code>rk4</code> on both cost models and <code>heun2</code> on <code>m0plus_fast</code>'."""
    by_method = {}
    for method, model in pairs:
        by_method.setdefault(method, []).append(model)
    parts = []
    for method, models in by_method.items():
        if n_models == 2 and len(models) == 2:
            parts.append(f"{_code(method)} on both cost models")
        else:
            parts.append(f"{_code(method)} on " + _join(_code(m) for m in models))
    return _join(parts)


def _premise(data):
    rk = data["rk"]
    pr = rk["premise"]
    th = pr["thresholds"]
    budget = fmt.count(rk["setup"]["budget_cycles"])
    methods = sorted(pr["methods"], key=lambda m: (m != "rk4", m))
    models = sorted({mo for m in pr["methods"].values() for mo in m["coefficient_fraction"]})
    proceed, kill, neither = _premise_outcomes(pr)

    p1 = (
        "<p>Before the search started, the run tested its own premise. The test ran "
        f"{_join(_code(m) for m in methods)} in Q15 on one problem, {_code(pr['problem'])}, "
        f"under both cost models, {_join(_code(m) for m in models)}. It measured the share of "
        "each step's cycles spent on coefficient arithmetic, and the step size at which "
        "rounding error overtakes truncation error. The thresholds were committed to the "
        "project's own repository before the test ran, not to an outside registry "
        f"({_claim('R9')}). The run would proceed if coefficient arithmetic took at least "
        f"{fmt.pct(th['proceed_fraction'], 0)} of a step's cycles and rounding error overtook "
        f"truncation error at a practical step size, between {fmt.sig(th['practical_h_min'])} "
        f"and {fmt.sig(th['practical_h_max'])}. It would stop if coefficient arithmetic took "
        f"under {fmt.pct(th['kill_fraction'], 0)} and no practical step size was "
        "rounding-dominated.</p>"
    )

    met = []
    if proceed:
        met.append(f"{_pairs_text(proceed, len(models))} met the proceed criterion")
    if kill:
        met.append(f"{_pairs_text(kill, len(models))} met the kill criterion")
    verdict = f"The stored verdict is {_code(pr['stored_verdict'])}"
    outcome = [verdict + (": " + ", and ".join(met) if met else "") + "."]
    for method, model in neither:
        row = pr["methods"][method]
        frac = row["coefficient_fraction"][model]
        if frac < th["kill_fraction"] and row["crossover_practical"]:
            outcome.append(
                f"On {_code(model)}, {_code(method)} spent {fmt.pct(frac, 1)} of its cycles on "
                f"coefficient arithmetic, below both the {fmt.pct(th['proceed_fraction'], 0)} "
                f"and the {fmt.pct(th['kill_fraction'], 0)} lines, but it still had a "
                "rounding-dominated regime at a practical step size, so it met neither "
                "criterion."
            )
        else:
            outcome.append(
                f"On {_code(model)}, {_code(method)} spent {fmt.pct(frac, 1)} of its cycles on "
                "coefficient arithmetic and met neither criterion."
            )
    p2 = "<p>" + " ".join(outcome) + "</p>"

    floor_won, floor_of = (int(v) for v in pr["rk4_best_under_floor"].split("/"))
    near_won, near_of = (int(v) for v in pr["rk4_best_under_round_to_nearest"].split("/"))
    m = re.search(r"\(([^)]*)\)", pr.get("rk4_best_note", ""))
    compared = ""
    n_compared = ""
    if m:
        names = [n.strip() for n in m.group(1).split(",") if n.strip()]
        compared = " (" + _join(_code(n) for n in names) + ")"
        n_compared = _word(len(names)) + " "
    p3 = (
        "<p>A later comparison is separate from the premise test, and it was made after the "
        f"search began. It compared {n_compared}classical methods{compared} on the "
        f"{_word(floor_of)} search and held-out problems at the {budget}-cycle budget on "
        f"{_code(rk['setup']['cost_model'])}. Among them, <code>rk4</code> had the lowest "
        f"error on {fmt.count(floor_won)} of {fmt.count(floor_of)} under floor rounding, and on "
        f"{fmt.count(near_won)} of {fmt.count(near_of)} under round-to-nearest.</p>"
    )
    return (
        '<h3 id="premise">A premise test with thresholds set in advance</h3>\n'
        f"{p1}\n{p2}\n{p3}"
    )


def _ledger():
    return (
        '<h3 id="ledger">A hypothesis ledger scored by code</h3>\n'
        "<p>The run keeps a ledger of hypotheses about its own search. Each hypothesis is a "
        "predicate in a small closed grammar that a hand-written parser reads, and code "
        "evaluates the predicate to assign its verdict. No model decides whether a hypothesis "
        "held. This "
        "site quotes no counts from the ledger, because it is not among the documents the run "
        "treats as sources for published numbers.</p>"
    )


def _literature():
    return (
        '<h3 id="literature">Literature digests, labelled as model-written</h3>\n'
        "<p>The run searches the web for related work and writes digests that feed later "
        "prompts. A language model writes them, and the run publishes them labelled as "
        "model-written, so a reader can keep them apart from results the code computed.</p>"
    )


def _definitions(data):
    """One-line definitions of the three weightings and the two cost bases in the grid."""
    rk = data["rk"]
    cf = rk["counterfactual"]
    n_heldout = _word(len(rk["setup"]["heldout_problems"]))
    n_classical = _word(len(rk["frontier"]["classical"]))
    defs = {
        "magnitude": (
            f"The published weighting: an RMS of the {n_heldout} problems' raw errors, so a "
            "problem's influence grows with the square of its error."
        ),
        "equal_median_anchor": (
            "Each problem's error is divided by the median error of the "
            f"{n_classical} classical methods on that problem before the RMS, which gives the "
            f"{n_heldout} problems equal weight."
        ),
        "equal_reference_norm": (
            "Each problem's error is divided by that problem's zero-state error before the "
            "RMS. The run publishes it as a counterexample: it puts most of the weight on "
            "<code>rc_thermal</code> instead of equalizing it."
        ),
        "analytic": (
            "The cost model every archived score was computed under. It prices only the stage "
            "and weight combinations of a step."
        ),
        "traced_whole_step": (
            "Cycles for every instruction the compiled step executes, priced from the "
            "Cortex-M0+ timing table, leaving out the derivative routine's own body. The grid "
            "uses it only to decide how many steps fit in the budget."
        ),
    }
    used = {c["weighting"] for c in cf["cells"]} | {c["basis"] for c in cf["cells"]}
    keys = ("magnitude", "equal_median_anchor", "equal_reference_norm", "analytic", "traced_whole_step")
    rows = [
        f"<dt>{fmt.esc(_TERMS[k])}</dt>\n<dd>{defs[k]}</dd>" for k in keys if k in used
    ]
    return (
        '<dl class="grid-terms">\n' + "\n".join(rows) + "\n</dl>\n"
        "<p>Neither basis is the full cost of a step on a chip: the analytic model prices less "
        "than the traced count, and the traced count prices less than a real application "
        "step.</p>"
    )


def _reranking(data):
    rk = data["rk"]
    cf = rk["counterfactual"]
    rr = cf.get("archive_reranking")
    if not rr:
        return ""
    basis = _BASIS_LABELS.get(cf.get("archive_reranking_basis", ""), "")
    on_basis = f" on the {fmt.esc(basis)} basis" if basis else ""
    keys = [k for k in _WEIGHTING_ORDER if k in rr]
    ranks = _join(
        f"rank {fmt.count(rr[k]['champion_rank'])} under {_WEIGHTING_NAMES[k]} weighting"
        for k in keys
    )
    text = (
        "<p>Which archived method ranks highest also depends on the weighting. Re-ranking "
        f"all {fmt.count(rk['frontier']['unique_tableaus'])} archived tableaus{on_basis} puts "
        f"the champion at {ranks}."
    )
    if all(rr[k]["classical_ahead"] == 0 for k in keys):
        text += (
            f" Under all {_word(len(keys))}, no classical method ranks above it, so a "
            "discovered method holds the top place each time."
        )
    return text + "</p>"


def _grid(data):
    rk = data["rk"]
    cf = rk["counterfactual"]
    cells = cf["cells"]
    weightings = []
    bases = []
    for c in cells:
        if c["weighting"] not in weightings:
            weightings.append(c["weighting"])
        if c["basis"] not in bases:
            bases.append(c["basis"])
    leading = [c for c in cells if c["champion_still_leads"]]
    lead_bases = sorted({c["basis"] for c in leading})
    by_key = {(c["weighting"], c["basis"]): c for c in cells}

    rows = "\n".join(
        "<tr>"
        f"<td>{fmt.esc(_WEIGHTING_LABELS.get(c['weighting'], c['weighting']))}</td>"
        f"<td>{fmt.esc(_BASIS_LABELS.get(c['basis'], c['basis']))}</td>"
        f"<td>{fmt.ratio(c['ratio'])}</td>"
        f"<td>{fmt.ratio(c['lowest_leave_one_out_ratio'])}</td>"
        f"<td>{'yes' if c['champion_still_leads'] else 'no'}</td>"
        "</tr>"
        for c in cells
    )
    table = (
        '<div class="table-wrap" style="overflow-x:auto">\n<table class="grid-table">\n'
        "<thead><tr><th>Weighting</th><th>Cost basis</th><th>Ratio</th>"
        "<th>Lowest ratio, one problem dropped</th><th>Ahead with any one problem dropped</th>"
        "</tr></thead>\n"
        f"<tbody>\n{rows}\n</tbody>\n</table>\n</div>"
    )

    held = ""
    if leading:
        where = _join(
            f"{fmt.ratio(c['ratio'])} under {_WEIGHTING_NAMES[c['weighting']]} weighting"
            for c in sorted(leading, key=lambda c: _WEIGHTING_ORDER.index(c["weighting"]))
        )
        basis = ""
        if len(lead_bases) == 1:
            label = fmt.esc(_BASIS_LABELS.get(lead_bases[0], lead_bases[0]))
            if len(leading) == 1:
                basis = f", on the {label} basis"
            else:
                basis = f", {'both' if len(leading) == 2 else 'all'} on the {label} basis"
        held = (
            f"The champion stays ahead with any one problem dropped in {_word(len(leading))} of "
            f"the {_word(len(cells))} cells{basis}: {where}. "
        )
    rest = (
        f"In the other {_word(len(cells) - len(leading))}, either the ratio is below 1 or it "
        "falls below 1 when one held-out problem is dropped."
    )

    mag_t = by_key[("magnitude", "traced_whole_step")]
    ref_t = by_key[("equal_reference_norm", "traced_whole_step")]
    med_a = by_key[("equal_median_anchor", "analytic")]
    med_t = by_key[("equal_median_anchor", "traced_whole_step")]
    detail = (
        "<p>On the traced whole-step basis the ratio is "
        f"{fmt.ratio(mag_t['ratio'])} under magnitude weighting, and dropping one problem takes "
        f"it to {fmt.ratio(mag_t['lowest_leave_one_out_ratio'])}. Under reference-norm "
        f"weighting on that basis it is {fmt.ratio(ref_t['ratio'])} (lowest "
        f"{fmt.ratio(ref_t['lowest_leave_one_out_ratio'])}). Under median-anchor weighting it "
        f"is {fmt.ratio(med_a['ratio'])} on the analytic basis (lowest "
        f"{fmt.ratio(med_a['lowest_leave_one_out_ratio'])}) and {fmt.ratio(med_t['ratio'])} on "
        "the traced one, where a classical method is far ahead. The source reads that last "
        "cell as the weighting magnifying one problem, not as the champion losing by that "
        "factor. Of the held-out problems, <code>pendulum</code> has the smallest median "
        "classical error, so dividing by it amplifies the champion's error there, and that "
        "error rises when the traced basis leaves the champion fewer steps.</p>"
    )
    return (
        '<h3 id="grid">The counterfactual grid</h3>\n'
        f"<p>The run recomputed the headline lead ({_claim('R1')}) under "
        f"{_word(len(weightings))} weightings of the held-out problems and {_word(len(bases))} "
        f"cost bases, {_word(len(cells))} cells in all, and publishes every cell. Each ratio is "
        "the best classical method's held-out error over the champion's, so above 1 the "
        "champion leads.</p>\n"
        f"{_definitions(data)}\n"
        f"{table}\n"
        f"<p>{held}{rest}</p>\n"
        f"{detail}\n"
        f"{_reranking(data)}"
    )


def _practice(data):
    return (
        "<section>\n"
        '<h2 id="research-practice">Research practice</h2>\n'
        "<p>The run publishes its checks and its negative results next to its headline. The "
        "four practices below matter for reading its claims.</p>\n"
        f"{_premise(data)}\n{_ledger()}\n{_literature()}\n{_grid(data)}\n"
        "</section>"
    )


def _snapshot(data):
    snap = fmt.day(data["sources"]["snapshot_date"])
    return (
        "<section>\n"
        '<h2 id="about-this-snapshot">About this snapshot</h2>\n'
        f"<p>This page was built from data read on {snap}. The run was still going on that "
        "date, so the epoch 2 counts above will go out of date. For current numbers, see the "
        f'findings site the run rebuilds every cycle: <a href="{FINDINGS_URL}">'
        "jgoetzmann.github.io/rk-findings</a>.</p>\n"
        "</section>"
    )


def build(data):
    parts = [
        "<h1>Epochs and research</h1>",
        _lead(),
        _dates(data),
        _epoch1(data),
        _froze(data),
        _epoch2(data),
        _practice(data),
        _snapshot(data),
    ]
    return "\n".join(parts) + "\n"
