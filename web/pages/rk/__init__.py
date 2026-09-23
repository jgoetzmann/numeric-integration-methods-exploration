"""The rk run page (rk.html).

Every number is read from data["rk"] or data["sources"] and rendered through
web.fmt. Every result sentence names its conditions and links its claim id
(data/claims.json is the authority for what the page may say).
"""

import re

from web import fmt
from web.charts import figure, standalone, table
from web.fmt import esc

from . import charts
from .charts import RK4_ORDER, and_list, claim_ref, code, word

SLUG = "rk.html"
TITLE = "The rk run"
DESCRIPTION = ("What the rk run searched for, what it found in Q15 fixed point with floor "
               "rounding, and why rk4 stays far ahead in float64.")

FINDINGS_URL = "https://jgoetzmann.github.io/rk-findings/"


def _section(sid, heading, body):
    return f'<section aria-labelledby="{sid}"><h2 id="{sid}">{esc(heading)}</h2>{body}</section>'


def _site(sources, name):
    for r in sources.get("repos", []):
        if r.get("name") == name and r.get("site"):
            return r["site"]


def _budget(rk):
    return fmt.count(rk["setup"]["budget_cycles"])


def _frac(s):
    s = str(s)
    if s.endswith("/1"):
        return s[:-2]
    return s


def _cell(cells, weighting, basis):
    for c in cells:
        if c["weighting"] == weighting and c["basis"] == basis:
            return c


def _trap_cases(rk):
    """How many of the trace cross-check cases are overflow traps, read from trace.crosscheck."""
    m = re.search(r"(\d[\d,]*) of them are cases where", rk["trace"].get("crosscheck", ""))
    return int(m.group(1).replace(",", "")) if m else None


def _tableau(ch):
    tab = ch["tableau"]
    A, b, c = tab["A"], tab["b"], tab["c"]
    n = len(b)
    rows = []
    for i in range(n):
        cells = [f'<th scope="row"><code>{esc(_frac(c[i]))}</code></th>']
        for j in range(n):
            if j < i:
                cells.append(f"<td><code>{esc(_frac(A[i][j]))}</code></td>")
            else:
                cells.append("<td></td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    weights = "".join(f"<td><code>{esc(_frac(x))}</code></td>" for x in b)
    rows.append(f'<tr><th scope="row"><code>b</code></th>{weights}</tr>')
    return ('<table class="tableau"><caption>Butcher tableau of '
            f"{code(ch['hash'])}: nodes <code>c</code> in the left column, "
            "<code>A</code> below the diagonal, weights <code>b</code> in the last row</caption>"
            "<tbody>" + "".join(rows) + "</tbody></table>")


# ---------------------------------------------------------------- lead


def _lead(rk):
    ch = rk["champion"]
    gap = rk["float64_gap"]
    n_cls = len(rk["frontier"]["classical"])
    model = rk["setup"]["cost_model"]
    return (
        '<section class="lead" aria-label="Summary">'
        "<p>The rk run is an autonomous search for Runge-Kutta coefficients that give the lowest "
        f"error in Q15 fixed point with floor rounding, at a fixed budget of {_budget(rk)} cycles "
        "on a modeled Cortex-M0+. Inside that frame, on the analytic "
        f"{code(model)} cost model with magnitude weighting, it found a "
        f"{word(ch['stages'])}-stage method, {code(ch['hash'])}, whose held-out error is "
        f"{fmt.ratio(ch['lead'])} lower than that of {code(ch['best_classical'])}, the best of the "
        f"{word(n_cls)} classical methods {claim_ref('R1')}.</p>"
        "<p>That figure comes from epoch 1, scored on the cost model that a later audit found had "
        f"{code('rk4')} and {code('rk38')} in the wrong order, and it has not been re-measured "
        "under the corrected epoch-2 model. It also moves with how a step's cost is counted and "
        "how the four held-out problems are weighted, and it holds only under floor rounding. "
        "The sections below give each of those conditions with its numbers.</p>"
        "<p>Outside that frame the result does not carry over. In float64, at the step count the "
        f"budget gives each method, the champion's error was "
        f"{fmt.ratio(gap['champion_over_rk4_min'])} to {fmt.ratio(gap['champion_over_rk4_max'])} "
        f"that of {code('rk4')} {claim_ref('R5')}. Every cycle count on this page comes from a "
        "cost model or an emulator; nothing was measured on a physical chip.</p>"
        "</section>"
    )


# ---------------------------------------------------------------- the question


def _models_phrase(pr):
    models = sorted({mo for m in pr["methods"].values() for mo in m["coefficient_fraction"]})
    named = [f"the slow-multiplier {code(mo)}" if mo.endswith("_slow") else code(mo)
             for mo in models]
    return and_list(named)


def _premise(rk):
    pr = rk["premise"]
    th = pr["thresholds"]
    proceed, kill = th["proceed_fraction"], th["kill_fraction"]
    met_proceed, met_kill, met_neither = [], [], []
    for name in sorted(pr["methods"]):
        m = pr["methods"][name]
        practical = bool(m.get("crossover_practical"))
        for model in sorted(m["coefficient_fraction"]):
            f = m["coefficient_fraction"][model]
            item = (name, model, f)
            if f >= proceed and practical:
                met_proceed.append(item)
            elif f < kill and not practical:
                met_kill.append(item)
            else:
                met_neither.append(item)

    def pairs(items):
        return and_list([f"{code(n)} on {code(mo)} ({fmt.pct(f)})" for n, mo, f in items])

    def of(s):
        a, _, b = str(s).partition("/")
        return f"{esc(a)} of {esc(b)}"

    p = (
        "<p>The project tested that premise before the search began, against thresholds "
        "committed to its own repository before the test ran, not to an outside registry. On "
        f"{code(pr['problem'])} it measured what share of each step's cycles goes to coefficient "
        "arithmetic rather than the derivative, for "
        f"{and_list([code(n) for n in sorted(pr['methods'])])} under both cost models, "
        f"{_models_phrase(pr)}, and whether "
        "Q15 roundoff overtakes truncation error at a practical step size, between "
        f"{fmt.sig(th['practical_h_min'])} and {fmt.sig(th['practical_h_max'])}. The rule was to "
        f"proceed if every share reached {fmt.pct(proceed, 0)} and roundoff took over at a "
        f"practical step size, and to stop if every share was under {fmt.pct(kill, 0)} and it "
        f"never did.</p>"
        f"<p>The verdict was {esc(pr['stored_verdict'])} {claim_ref('R9')}."
    )
    if met_proceed:
        p += f" The proceed bar was met by {pairs(met_proceed)}."
    if met_kill:
        p += f" The stop bar was met by {pairs(met_kill)}."
    for name, model, f in met_neither:
        practical = bool(pr["methods"][name].get("crossover_practical"))
        if f < kill and practical:
            why = (f"its share is under {fmt.pct(kill, 0)}, but roundoff did take over at a "
                   "practical step size")
        elif f < proceed:
            why = f"its share falls between {fmt.pct(kill, 0)} and {fmt.pct(proceed, 0)}"
        else:
            why = "roundoff never took over at a practical step size"
        p += f" Neither bar was met by {code(name)} on {code(model)} ({fmt.pct(f)}): {why}."
    p += (" A later comparison of four classical methods on the seven search and held-out "
          f"problems, made after the search began, found {code('rk4')} best on "
          f"{of(pr['rk4_best_under_floor'])} under floor rounding and "
          f"{of(pr['rk4_best_under_round_to_nearest'])} under round-to-nearest.</p>")
    return p


def _question(rk):
    setup = rk["setup"]
    body = (
        "<p>Q15 stores each value as a signed 16-bit integer that stands for a fraction between "
        "minus one and one. A Cortex-M0+ has no floating-point unit, so it multiplies two Q15 "
        "values as integers and shifts the product right by fifteen bits. The shift is "
        f"arithmetic, and like the ARM {code('ASRS')} instruction it rounds toward minus "
        "infinity, so every product loses part of its last bit, always in the same direction.</p>"
        f"<p>Textbook coefficients such as those of {code('rk4')} were derived for exact "
        "arithmetic. The run asks which coefficients give the lowest error once that downward "
        "rounding is part of every step.</p>"
        f"<p>It scores a method by the error it reaches within a fixed budget of {_budget(rk)} "
        "cycles, not at a fixed step size. A cheaper step buys more, smaller steps, so the cost "
        "of each coefficient is part of the score. That cost only matters in fixed point. In "
        f"floating point, multiplying by {code('1/3')} costs the same as multiplying by "
        f"{code('1/4')}. In Q15 a dyadic coefficient such as {code('13/16')} takes a couple of "
        f"shifts and adds, while {code('1/3')}, which has no short binary form, takes many "
        "more.</p>"
        "<p>The cycle counts come from an analytic model of the Cortex-M0+, "
        f"{code(setup['cost_model'])}, which prices the stage and weight combinations of a step. "
        "Every epoch-1 score was computed under it. The counts are modeled, not measured on a "
        "chip.</p>"
        + _premise(rk)
    )
    return _section("question", "The question", body)


# ---------------------------------------------------------------- scoring


def _scoring(rk):
    eng = rk["engineering"]
    ep1 = rk["epochs"]["epoch1"]
    held = rk["setup"]["heldout_problems"]
    body = (
        "<p>Every candidate tableau goes through a verifier before it is scored. The verifier "
        "checks the order conditions exactly, in rational arithmetic, and rejects a tableau that "
        "is not explicit, breaks the row-sum conditions, would overflow Q15 with a two-times "
        "margin, or falls outside the coefficient and stability limits.</p>"
        "<p>A language model proposes each search cycle's direction as a JSON directive. The "
        "directive can only narrow the search, and an unknown key sends the runner to a fixed "
        "fallback. The scorer, the verifier and every hypothesis verdict are code "
        f"{claim_ref('R13')}.</p>"
        "<p>A tableau that passes is run in Q15 with floor rounding on a set of search problems, "
        f"each at the {_budget(rk)}-cycle budget. The optimizer, CMA-ES, is scored on the search "
        "problems only. The archive sorts methods into cells by order, stage count and cost "
        "band, and keeps in each cell the method with the lowest RMS error on "
        f"{word(len(held))} held-out problems: {and_list([code(h) for h in held])}. No "
        "optimizer reads the held-out problems, but elites are picked on them and the language "
        "model is shown their errors, so they act as a selection set rather than an independent "
        f"test {claim_ref('U2')}.</p>"
        "<p>The scorer is out of the search's reach. The harness is mounted read-only, and a "
        f"sha256 over the pinned files ({fmt.count(ep1['verifier_files'])} in epoch 1, "
        f"{fmt.count(eng['verifier_files'])} since epoch 2) is checked at every start and stored "
        f"in every record. Before any search cycle runs, {fmt.count(eng['golden_gate_cases'])} "
        f"golden and canary cases must pass {claim_ref('R11')}. No GitHub credential enters the "
        "container: it commits, and the host pushes. The one credential inside is the model's "
        "sign-in file, mounted read-only. On "
        f"{esc(fmt.day(eng['tests_collected_on']))} the test suite collected "
        f"{fmt.count(eng['tests_collected'])} tests.</p>"
    )
    return _section("scoring", "How a candidate is scored and verified", body)


# ---------------------------------------------------------------- results


def _loo_table(ch):
    rows = []
    for r in ch["leave_one_out"]:
        name = code(r["dropped"]) if r.get("dropped") else "none (all four problems)"
        rows.append([name, fmt.ratio(r["ratio"])])
    return table(["Held-out problem dropped", "Ratio, best classical error over champion"],
                 rows,
                 caption=("Leave-one-out check: Q15 with floor rounding, analytic cost model, "
                          "magnitude weighting"))


def _per_problem_table(rk):
    ch = rk["champion"]
    best = ch["best_classical"]
    cls = ch["classical_per_problem_heldout"][best]
    rows = []
    for p in rk["setup"]["heldout_problems"]:
        c, m = ch["per_problem_heldout"][p], cls[p]
        rows.append([code(p), fmt.sig(c), fmt.sig(m), "champion" if c < m else code(best)])
    lower = "champion" if ch["heldout_error"] < ch["best_classical_heldout_error"] else code(best)
    rows.append(["RMS over the four (magnitude weighting)", fmt.sig(ch["heldout_error"]),
                 fmt.sig(ch["best_classical_heldout_error"]), lower])
    return table(["Held-out problem", f"Champion {code(ch['hash'])}", code(best), "Lower error"],
                 rows,
                 caption=(f"Held-out error per problem, champion against {code(best)}: Q15 with "
                          f"floor rounding at the {_budget(rk)}-cycle budget, analytic cost "
                          "model, epoch 1"))


def _results(rk):
    ch = rk["champion"]
    fr = rk["frontier"]
    ep1 = rk["epochs"]["epoch1"]
    budget = _budget(rk)
    best = ch["best_classical"]
    model = rk["setup"]["cost_model"]

    # Where the four-problem RMS comes from.
    held = rk["setup"]["heldout_problems"]
    cls_pp = ch["classical_per_problem_heldout"]
    wins = [p for p in held if ch["per_problem_heldout"][p] < cls_pp[best][p]]
    losses = [p for p in held if p not in wins]
    floor_p = "rc_thermal"
    floor_vals = [v[floor_p] for v in cls_pp.values() if floor_p in v]

    loo = [r for r in ch["leave_one_out"] if r.get("dropped")]
    lo_row = min(loo, key=lambda r: r["ratio"])
    hi_row = max(loo, key=lambda r: r["ratio"])

    n_total = fr["cells_total"]
    n_disc = fr["cells_held_by_discovered"]
    n_cls = fr["cells_held_by_classical"]
    best_cls_err = min(r["heldout_error"] for r in fr["classical"])
    n_ahead_all = sum(1 for r in fr["discovered"] if r["heldout_error"] < best_cls_err)
    closest = min(fr["discovered"], key=lambda r: abs(r["heldout_error"]
                                                       - fr["closest_discovered_to_classical"]))

    later = [r for r in fr["discovered"] if r.get("first_cycle", 0) > ch["found_at_cycle"]]
    later_orders = sorted({r["order"] for r in later if r["order"] > ch["order"]})

    body = (
        f"<p>The champion, {code(ch['hash'])}, has {fmt.count(ch['stages'])} stages and order "
        f"{fmt.count(ch['order'])}, and costs {fmt.count(ch['cycles_per_step'])} cycles per step "
        "on the analytic model. Every coefficient is a dyadic fraction.</p>"
        + _tableau(ch)
        + f"<p>Inside Q15 with floor rounding, at the {budget}-cycle budget, on the analytic "
        f"{code(model)} cost model with magnitude weighting, the champion's held-out RMS error is "
        f"{fmt.sig(ch['heldout_error'])} against {fmt.sig(ch['best_classical_heldout_error'])} "
        f"for {code(best)}, the best classical method: a lead of {fmt.ratio(ch['lead'])} "
        f"{claim_ref('R1')}. Elites were picked on held-out error from "
        f"{fmt.count(fr['unique_tableaus'])} archived tableaus, so the four held-out problems act "
        "as a selection set and the lead carries winner's-curse bias. It is also an epoch-1 "
        f"figure: the trace later found this cost model had {code('rk4')} and {code('rk38')} in "
        "the wrong order, and epoch 2, which scores under a corrected model, has not re-measured "
        "it.</p>"
        f"<p>The {fmt.ratio(ch['lead'])} is an RMS over {word(len(held))} problems, and it hides a "
        f"split. The champion has lower error than {code(best)} on "
        f"{and_list([code(p) for p in wins])}"
    )
    if losses:
        body += (f", and higher error on {and_list([code(p) for p in losses])} ("
                 + "; ".join(f"{fmt.sig(ch['per_problem_heldout'][p])} against "
                             f"{fmt.sig(cls_pp[best][p])}" for p in losses)
                 + ")")
    body += "."
    if floor_vals and floor_p in ch["per_problem_heldout"]:
        body += (f" Much of the gap comes from {code(floor_p)}, where every classical method "
                 f"stalls between {fmt.sig(min(floor_vals))} and {fmt.sig(max(floor_vals))}, "
                 "near a quantization floor, and the champion gets under it at "
                 f"{fmt.sig(ch['per_problem_heldout'][floor_p])}.")
    body += "</p>" + _per_problem_table(rk)

    body += (
        f"<p>Dropping any one of the {word(len(loo))} held-out problems leaves the champion "
        f"ahead, by {fmt.ratio(lo_row['ratio'])} to {fmt.ratio(hi_row['ratio'])} on the same "
        f"basis {claim_ref('R3')}. The low end, {fmt.ratio(lo_row['ratio'])}, comes from "
        f"dropping {code(lo_row['dropped'])}. Magnitude weighting lets problems with small errors "
        "count for little, so this check cannot show a loss on one of them"
    )
    if losses:
        body += f", and the champion does lose to {code(best)} on {and_list([code(p) for p in losses])}"
    body += ".</p>" + _loo_table(ch)

    body += (
        f"<p>The champion appeared at search cycle {fmt.count(ch['found_at_cycle'])}, and no "
        f"later cycle in epoch 1's {fmt.count(ch['cycles_run'])} lowered the best held-out error "
        f"{claim_ref('R6')}. The search kept filling and improving other cells after that: "
        f"{fmt.count(len(later))} of the {fmt.count(len(fr['discovered']))} discovered cell elites "
        "appeared later"
    )
    if later_orders:
        body += (", elites of order "
                 + and_list([fmt.count(o) for o in later_orders]) + " among them")
    if ep1.get("last_new_cell_ts"):
        body += (f". The last new cell was filled on {esc(fmt.day(ep1['last_new_cell_ts']))} "
                 "and the last cell improvement came on "
                 f"{esc(fmt.day(ep1['last_improvement_ts']))}.</p>")
    else:
        body += (f", and the last cell improvement came on "
                 f"{esc(fmt.day(ep1['last_improvement_ts']))}.</p>")

    body += (
        f"<p>The champion is not the only discovered method ahead. Epoch 1's archive has "
        f"{fmt.count(n_total)} occupied cells: discovered methods hold {fmt.count(n_disc)} and "
        f"classical methods {fmt.count(n_cls)}. Under the same conditions, and with the same "
        "selection bias, "
    )
    if n_ahead_all == n_disc:
        body += (f"the discovered method in each of those {fmt.count(n_disc)} cells has lower "
                 f"held-out error than all {word(len(fr['classical']))} classical methods, "
                 f"whatever their cost {claim_ref('R2')}.")
    else:
        body += (f"{fmt.count(n_ahead_all)} of those {fmt.count(n_disc)} discovered methods have "
                 f"lower held-out error than all {word(len(fr['classical']))} classical methods "
                 f"{claim_ref('R2')}.")
    body += (f" The closest, a {word(closest['stages'])}-stage elite at "
             f"{fmt.count(closest['cycles'])} cycles per step, has "
             f"{fmt.sig(closest['heldout_error'])} against {code(best)}'s "
             f"{fmt.sig(best_cls_err)}.</p>"
             + figure(charts.frontier_chart(rk)))

    return _section("results", "What the search found", body + _lead_conditions(rk))


def _lead_conditions(rk):
    ch = rk["champion"]
    cf = rk["counterfactual"]
    cells = cf["cells"]
    budget = _budget(rk)
    weightings, bases = [], []
    for c in cells:
        if c["weighting"] not in weightings:
            weightings.append(c["weighting"])
        if c["basis"] not in bases:
            bases.append(c["basis"])
    pub = _cell(cells, "magnitude", "analytic")
    ref_a = _cell(cells, "equal_reference_norm", "analytic")
    ref_t = _cell(cells, "equal_reference_norm", "traced_whole_step")
    med_a = _cell(cells, "equal_median_anchor", "analytic")
    med_t = _cell(cells, "equal_median_anchor", "traced_whole_step")
    mag_t = _cell(cells, "magnitude", "traced_whole_step")
    still = [c for c in cells if c["champion_still_leads"]]

    def loo(c):
        return f"lowest leave-one-out {fmt.ratio(c['lowest_leave_one_out_ratio'])}"

    sub = '<h3 id="lead-conditions">How the lead depends on cost basis and weighting</h3>'
    sub += (
        f"<p>The {fmt.ratio(pub['ratio'])} figure is one cell in a grid of {word(len(cells))}: "
        f"{word(len(weightings))} ways to weight the held-out problems against each other, times "
        f"{word(len(bases))} ways to count what a step costs.</p>"
        "<p>The analytic basis is the one every archived score was computed under. It prices the "
        "stage and weight combinations only. The traced whole-step basis compiles the step and "
        "prices every instruction it executes with the Cortex-M0+ timing table: loop control, "
        "the h times k products and the call into the derivative, but not the derivative's own "
        f"code. It uses that count only to decide how many steps fit in {budget} cycles. Neither "
        "basis is the full cost of a step on a chip. The analytic model prices less than the "
        "traced count, and the traced count prices less than a real application step, so the "
        "two bracket the cost rather than correct each other.</p>"
        "<p>Magnitude weighting, the published one, is an unweighted RMS of the four problems' "
        "errors, so a problem's influence grows with the square of its error. Median-anchor "
        "weighting divides each error by the median error of the eight classical methods on that "
        "problem before the RMS, which weights the four problems equally. Reference-norm "
        "weighting divides by each problem's zero-state error instead. The source publishes it "
        "as a counterexample, because it concentrates weight on rc_thermal rather than "
        "equalizing it.</p>"
    )
    p = []
    if still and all(c["basis"] == "analytic" for c in still) and pub in still and ref_a in still:
        p.append(f"Of the {word(len(cells))} cells, the champion keeps its lead on every "
                 f"leave-one-out subset in {word(len(still))}, both on the analytic basis: "
                 f"{fmt.ratio(pub['ratio'])} under magnitude weighting and "
                 f"{fmt.ratio(ref_a['ratio'])} under reference-norm weighting.")
    else:
        p.append(f"Of the {word(len(cells))} cells, the champion keeps its lead on every "
                 f"leave-one-out subset in {word(len(still))}.")
    p.append(f"On the traced whole-step basis the ratio is {fmt.ratio(mag_t['ratio'])} under "
             f"magnitude weighting, a near tie that dropping one problem turns into a loss "
             f"({loo(mag_t)}), and {fmt.ratio(ref_t['ratio'])} under reference-norm weighting "
             f"({loo(ref_t)}).")
    p.append(f"Under median-anchor weighting it is {fmt.ratio(med_a['ratio'])} on the analytic "
             f"basis ({loo(med_a)}) and {fmt.ratio(med_t['ratio'])} on the traced one, where a "
             f"classical method is far ahead {claim_ref('R1')}.")
    sub += "<p>" + " ".join(p) + "</p>"
    if med_t["ratio"] < 1:
        sub += (
            f"<p>That last cell needs reading. Median-anchor weighting divides by each problem's "
            f"median classical error, which is smallest on {code('pendulum')}, so it magnifies "
            f"any rise in a method's {code('pendulum')} error. The traced basis leaves the "
            f"champion fewer steps, and its {code('pendulum')} error rises. The source reads the "
            f"{fmt.ratio(med_t['ratio'])} cell as the weighting magnifying one problem, not as "
            "the champion losing by that factor.</p>"
        )
    rr = cf.get("archive_reranking") or {}
    if rr:
        order = [w for w in ("magnitude", "equal_reference_norm", "equal_median_anchor") if w in rr]
        ranks = and_list([f"{fmt.count(rr[w]['champion_rank'])} under "
                          f"{charts.label_of(charts._WEIGHTING, w)} weighting" for w in order])
        none_ahead = all(rr[w].get("classical_ahead") == 0 for w in order)
        basis = cf.get("archive_reranking_basis", "")
        n_tab = rk["frontier"].get("unique_tableaus")
        pool = (f"all {fmt.count(n_tab)} archived tableaus" if n_tab
                else "the epoch-1 archive")
        sub += (
            "<p>Which tableau counts as the champion depends on the weighting too. Re-ranking "
            f"{pool} on the {esc(basis)} basis puts {code(ch['hash'])} at rank {ranks}."
        )
        if none_ahead:
            sub += (f" Under all {word(len(order))}, no classical method ranks above it, so a "
                    "discovered method holds the top place each time")
        sub += f" {claim_ref('R2')}.</p>"
    sub += figure(charts.counterfactual_chart(rk))
    return sub


# ---------------------------------------------------------------- validation


def _validation(rk):
    val = rk["validation"]
    probs = val["problems"]
    budget = _budget(rk)
    non_stiff = [p for p in probs if not p.get("stiff")]
    stiff = [p for p in probs if p.get("stiff")]
    champ_wins = sum(1 for p in non_stiff if p["champion_q15"] < p["best_classical_q15"])
    run = list(val.get("classical_methods_run", []))
    n_disc = val["discovered_methods_run"]

    body = (
        f"<p>The run then tried {word(n_disc + len(run))} methods on {word(len(probs))} further "
        f"problems from embedded domains, {word(len(non_stiff))} non-stiff and "
        f"{word(len(stiff))} stiff: {word(n_disc)} discovered methods, the champion among them, "
        f"and {word(len(run))} classical methods, {and_list([code(m) for m in run])}. No "
        "optimizer or model saw these problems, and the champion was fixed before they ran. "
        "People chose the problems after the search began, though, so this is an out-of-sample "
        "check rather than an independent benchmark.</p>"
        f"<p>In Q15 with floor rounding at the {budget}-cycle budget, the best of the "
        f"{word(n_disc)} discovered methods tried had lower Q15 error than the best of the "
        f"{word(len(run))} classical methods run on "
        f"{fmt.count(val['practical_won_by_discovered'])} of {fmt.count(val['practical_total'])} "
        "non-stiff problems, with a median error ratio of "
        f"{fmt.sig(val['practical_median_ratio'])} (discovered over classical) across those "
        f"{word(val['practical_total'])} {claim_ref('R4')}. The fixed champion alone had the "
        f"lower error on {fmt.count(champ_wins)} of the {fmt.count(len(non_stiff))}.</p>"
    )

    won = [p for p in stiff if p.get("winner_kind") == "discovered"]
    stiff_p = (f"<p>The stiff problems went less well under the same conditions. A discovered "
               f"method had the lower error on {fmt.count(val['stiff_won_by_discovered'])} of the "
               f"{fmt.count(val['stiff_total'])}")
    if won:
        stiff_p += f", {and_list([code(p['problem']) for p in won])}"
    stiff_p += "."
    for p in stiff:
        if p.get("champion_overflowed") or p.get("best_discovered_q15") is None:
            continue
        if p.get("winner_kind") == "classical":
            stiff_p += (f" On {code(p['problem'])} {code(p['best_classical'])} had the lower "
                        f"error, {fmt.sig(p['best_classical_q15'], 4)} against "
                        f"{fmt.sig(p['best_discovered_q15'], 4)} for the best discovered method.")
    for p in stiff:
        if p.get("champion_overflowed") or p.get("best_discovered_q15") is None:
            finished = [m for m in run if m not in ("rk4", "rk38")]
            stiff_p += (f" On {code(p['problem'])} every discovered method overflowed, and so did "
                        f"{code('rk4')} and {code('rk38')}; only "
                        f"{and_list([code(m) for m in finished])} finished, "
                        f"{code(p['best_classical'])} with the lowest error.")
    stiff_p += "</p>"
    body += stiff_p + figure(charts.validation_q15_chart(rk))
    return _section("validation", "Out-of-sample check", body)


# ---------------------------------------------------------------- float64


def _float64(rk):
    gap = rk["float64_gap"]
    lib = rk["libraries"]
    val = rk["validation"]
    ch = rk["champion"]
    budget = _budget(rk)
    n_cells = lib["fixed_step_cells_compared"]
    rk4_lower = n_cells - lib["fixed_step_cells_where_q15_error_lower"]
    libs = [s["library_method"] for s in lib.get("solvers", [])
            if s.get("side") == "library" and s.get("library_method")]

    # Step counts each method gets from the budget: the most common pair, and how often.
    pairs = {}
    for p in val["problems"]:
        if p.get("champion_steps") and p.get("rk4_steps"):
            key = (p["champion_steps"], p["rk4_steps"])
            pairs[key] = pairs.get(key, 0) + 1
    steps_clause = ""
    if pairs:
        (c_steps, r_steps), n_pair = max(sorted(pairs.items()), key=lambda kv: kv[1])
        steps_clause = (f" The cheaper champion takes more steps: {fmt.count(c_steps)} against "
                        f"{code('rk4')}'s {fmt.count(r_steps)} on {word(n_pair)} of the "
                        f"{word(len(val['problems']))} problems.")

    best_lib = sorted(set(lib.get("best_library_per_problem", {}).values()))
    if len(best_lib) == 1:
        best_lib_txt = (f"the most accurate library solver, {code(best_lib[0])} on all "
                        f"{fmt.count(len(lib['best_library_per_problem']))} problems,")
    else:
        best_lib_txt = "the most accurate library solver on each problem"

    body = (
        "<p>The search optimized for Q15 floor arithmetic on purpose. The like-for-like test of "
        f"its coefficients in ordinary arithmetic is the champion against {code('rk4')}, both "
        "run in float64 on the out-of-sample problems, each at the step count the "
        f"{budget}-cycle budget gives it." + steps_clause
        + f" Its float64 error was still {fmt.ratio(gap['champion_over_rk4_min'])} to "
        f"{fmt.ratio(gap['champion_over_rk4_max'])} that of {code('rk4')} on the "
        f"{fmt.count(gap['problems'])} problems where both finish {claim_ref('R5')}. The "
        f"champion is order {fmt.count(ch['order'])} and {code('rk4')} order "
        f"{fmt.count(RK4_ORDER)}, and the classical order-{fmt.count(ch['order'])} methods trail "
        f"float64 {code('rk4')} by a similar margin in the same runs.</p>"
        "<p>Two wider comparisons measure the arithmetic rather than the coefficients. Float64 "
        f"{code('rk4')}, run as an arithmetic control, had lower error than every Q15 run, "
        f"classical and discovered alike, in {fmt.count(rk4_lower)} of {fmt.count(n_cells)} "
        "fixed-step cells at identical step counts; the benchmark reads that gap as the cost of "
        "16-bit floor arithmetic, not of the tableaus. At tolerances of one Q15 least "
        f"significant bit, {best_lib_txt} was a median "
        f"{fmt.ratio(lib['median_ratio_q15_over_library_at_matched_tolerance'])} more accurate "
        "than the most accurate Q15 run."
    )
    if libs:
        body += (f" The library set is {and_list([code(x) for x in libs])}, run in compiled "
                 "float64 through SciPy.")
    if "RK45" in libs and "RK45" not in best_lib:
        body += (f" Dormand-Prince (SciPy {code('RK45')}) was among them but was never the most "
                 "accurate, and it was never run against the champion in the same "
                 "arithmetic.")
    body += (
        "</p>"
        f"<p>This is where the Q15 result stops applying {claim_ref('U1')}. Nothing on this page "
        f"says the champion is more accurate than {code('rk4')} or Dormand-Prince outside Q15 "
        "with floor rounding.</p>"
        + figure(charts.validation_f64_chart(rk))
    )
    return _section("float64", "In float64, rk4 is far more accurate", body)


# ---------------------------------------------------------------- rounding


def _rounding(rk):
    fvr = rk["floor_vs_round"]
    ch = rk["champion"]
    search = fvr["search_rms"]
    held = fvr["heldout_rms"]
    budget = _budget(rk)
    modes, names = charts._floor_round_methods(rk, search)
    fl = search["floor"]
    rn = search["round_to_nearest"]
    lowest = min(names, key=lambda n: fl[n])
    highest = max(names, key=lambda n: fl[n])

    p1 = ("<p>Floor rounding changes which classical method does best. On the search "
          f"problems, in Q15 at the {budget}-cycle budget, {code(lowest)} has the lowest RMS error "
          f"under floor rounding ({fmt.sig(fl[lowest])}) of the {word(len(names))} classical "
          f"methods compared ({and_list([code(n) for n in names])}), and {code(highest)} the "
          f"highest ({fmt.sig(fl[highest])})")
    if rn[highest] < rn[lowest]:
        p1 += (f". Under round-to-nearest, {code(highest)} ({fmt.sig(rn[highest])}) is back ahead "
               f"of {code(lowest)} ({fmt.sig(rn[lowest])})")
    p1 += f" {claim_ref('R8')}.</p>"

    hf = held["floor"]
    hr = held["round_to_nearest"]
    bf = min(names, key=lambda n: hf[n])
    br = min(names, key=lambda n: hr[n])
    p2 = "<p>That ordering holds on the search set and on the published basis only. "
    if bf == br:
        p2 += (f"On the held-out problems {code(bf)} has the lowest error of the "
               f"{word(len(names))} methods compared under both rounding modes.</p>")
    else:
        p2 += (f"On the held-out problems {code(bf)} has the lowest error of the "
               f"{word(len(names))} under floor rounding and {code(br)} under "
               "round-to-nearest.</p>")

    p3 = ""
    if hr[br] < ch["heldout_error"]:
        p3 = (
            "<p>That bears on the champion. Under round-to-nearest, at the same budget and cost "
            f"model, {code(br)} alone reaches {fmt.sig(hr[br])} held-out error, below the "
            f"champion's {fmt.sig(ch['heldout_error'])} under floor rounding. The champion's lead "
            f"is a floor-rounding result {claim_ref('R1')}. This page has no round-to-nearest "
            "figure for the champion itself.</p>"
        )
    body = p1 + p2 + p3 + figure(charts.floor_round_chart(rk))
    return _section("rounding", "Rounding reorders the classical methods", body)


# ---------------------------------------------------------------- cost model


def _trace_table(rk):
    tr = rk["trace"]
    model = rk["setup"]["cost_model"]
    rows = []
    for m in tr["methods"]:
        rows.append([code(m["name"]),
                     fmt.count(m["analytic"][model]),
                     fmt.count(m["matched_scope"][model]),
                     fmt.count(m["whole_step"][model])])
    caption = (f"Cycles per step on the {code(model)} model at one state. Compare analytic with "
               "matched scope only, since matched scope counts the same work the analytic model "
               "prices. Whole step adds the derivative call, the h times k product, loop control "
               "and the stack frame; the counterfactual grid uses it only as a budget denominator.")
    return (table(["Method", "Analytic", "Matched scope (traced)", "Whole step (traced)"],
                  rows, caption=caption)
            + "<p>" + charts.source_note(tr["source"]).strip() + "</p>")


def _cost_model(rk):
    lib = rk["libraries"]
    sp = lib["speedup"]
    tr = rk["trace"]
    eng = rk["engineering"]
    model = rk["setup"]["cost_model"]
    by = {m["name"]: m for m in tr["methods"]}

    p1 = (
        "<p>Every Q15 result above rests on a cost model, so the run checked the model against "
        "measurement. Measured in Python on the same solver path, the champion's step ran "
        f"{fmt.ratio(sp['measured_geomean_rk4_over_champion'])} faster than {code('rk4')}'s "
        "(geometric mean over problems), against a model prediction of "
        f"{fmt.ratio(sp['predicted_geomean_rk4_over_champion'])}, and analytic cycles tracked "
        f"measured time with Pearson r = {fmt.sig(lib['cycle_model_pearson_r'], 2)} over "
        f"{fmt.count(lib['cycle_model_points'])} runs {claim_ref('R10')}. That is Python "
        f"wall-clock time. It agrees with the model's ordering of the champion and {code('rk4')}, "
        "not with its absolute cycle counts on a Cortex-M0+. The benchmark did not include "
        f"{code('rk38')}, and the audit below found the model had {code('rk4')} and "
        f"{code('rk38')} in the wrong order.</p>"
    )
    traps = _trap_cases(rk)
    trap_clause = (f", {fmt.count(traps)} of them overflow cases where both stop at the same "
                   "operation") if traps else ""
    a4 = by["rk4"]["analytic"][model]
    a38 = by["rk38"]["analytic"][model]
    m4 = by["rk4"]["matched_scope"][model]
    m38 = by["rk38"]["matched_scope"][model]
    p2 = (
        "<p>A host-side audit then compiled the step with GCC 13.2.1 for the Cortex-M0+ and "
        f"traced it under the {code('unicorn')} emulator. The compiled step agreed with the "
        f"Python evaluator bit for bit in {esc(eng['trace_crosscheck'])} cases{trap_clause} "
        f"{claim_ref('R7')}. It also showed that {code(model)}, the cost model the epoch-1 "
        f"archive was scored under, put {code('rk4')} and {code('rk38')} in the wrong order: it "
        f"prices {code('rk4')} at {fmt.count(a4)} cycles per step and {code('rk38')} at "
        f"{fmt.count(a38)}, while the traced count at matched scope, which covers the same work, "
        f"is {fmt.count(m4)} and {fmt.count(m38)}.</p>"
    )
    p3 = (
        "<p>The rk-overview site's browser demo is a second, independent check on the solver. It "
        "reimplements the Q15 solver in JavaScript and reproduces the Python evaluator in "
        f"{esc(eng['demo_crosscheck'])} fixture cases {claim_ref('R14')}.</p>"
    )
    p4 = (
        "<p>The emulator is instruction-accurate, not cycle-accurate: its cycle counts come from "
        "a timing table applied to the executed instructions, and nothing was measured on a "
        "physical chip. Rather than rescore the old archive, the run froze epoch 1 and started "
        "epoch 2 under a corrected cost model that prices each coefficient by the instructions "
        'GCC emits for it. <a href="epochs.html">Epochs and research</a> covers that decision.</p>'
    )
    body = p1 + p2 + p3 + p4 + _trace_table(rk)
    return _section("cost-model", "Speed and the cost model", body)


# ---------------------------------------------------------------- limits


def _not_shown(rk):
    ch = rk["champion"]
    cells = rk["counterfactual"]["cells"]
    still = [c for c in cells if c["champion_still_leads"]]
    rn = rk["floor_vs_round"]["heldout_rms"]["round_to_nearest"]
    below = sorted(n for n, v in rn.items() if v < ch["heldout_error"])
    if len(below) == 1:
        rtn_who = f"{code(below[0])} alone has"
    elif below:
        rtn_who = f"{and_list([code(n) for n in below])} have"
    else:
        rtn_who = ""
    items = [
        "It measured nothing on hardware. Cycle counts come from an analytic model, checked "
        "against Python timing and an instruction-accurate emulator "
        f"{claim_ref('R7', 'R10')}.",
        "It did not show the champion ahead outside Q15. In float64, "
        f"{code('rk4')} was far more accurate than the champion, and Dormand-Prince was never "
        f"run against the champion in the same arithmetic {claim_ref('R5')}.",
        "Its held-out errors are not independent of the search. Elites are chosen on them and "
        f"the model that proposes directions is shown them, so the {fmt.ratio(ch['lead'])} lead "
        "(Q15 with floor rounding, analytic basis, magnitude weighting) carries winner's-curse "
        f"bias {claim_ref('R1', 'U2')}.",
        "Its validation is an out-of-sample check, not an independent benchmark. No optimizer "
        "or model saw the validation problems, but people chose them after the search began "
        f"{claim_ref('R4')}.",
        "Its lead depends on the cost basis and the weighting. Of the "
        f"{word(len(cells))} cells in the grid above, the champion keeps its lead on every "
        f"leave-one-out subset in {word(len(still))} {claim_ref('R1')}.",
        "It has not re-measured the lead under the corrected epoch-2 cost model. Epoch 2 has no "
        "validation, benchmark or trace results of its own yet, so every result on this page "
        "comes from epoch 1.",
    ]
    if rtn_who:
        items.append(f"Its lead needs floor rounding. Under round-to-nearest {rtn_who} lower "
                     "held-out error than the champion has under floor rounding "
                     f"{claim_ref('R1')}.")
    items += [
        f"Explicit methods did not handle every stiff problem. On {code('robertson_scaled')} "
        f"every discovered method overflowed in Q15, and so did {code('rk4')} and {code('rk38')} "
        f"{claim_ref('R4')}.",
        f"It did not map the search space. The plateau after search cycle "
        f"{fmt.count(ch['found_at_cycle'])} describes one search, not a field of local minima "
        f"{claim_ref('U3')}.",
    ]
    body = "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"
    return _section("not-shown", "What the run did not show", body)


# ---------------------------------------------------------------- archive


def _archive(rk):
    ep = rk["epochs"]
    e1 = ep["epoch1"]
    e2 = ep["epoch2"]
    down = e2["down_days"]
    counts = e1.get("verifier_hash_counts", {})
    pre_pin = sum(v for h, v in counts.items() if h != e1["verifier_hash"])
    starts = e1.get("events", {}).get("runner_started")

    p1 = (
        f"<p>Epoch 1 ran from {esc(fmt.day(e1['started']))} to {esc(fmt.day(e1['stopped']))}: "
        f"{fmt.count(e1['cycles_run'])} search cycles over {fmt.count(e1['archive_day_count'])} "
        f"days of archive and {fmt.count(e1['records'])} scored records, all under verifier hash "
        f"{code(e1['verifier_hash'])}"
    )
    if pre_pin:
        p1 += f" apart from {fmt.count(pre_pin)} written minutes before that pin was set"
    p1 += f" {claim_ref('R12')}. No person chose candidates or scores, and the pinned scorer never changed"
    if starts:
        p1 += (f", though the runner started {fmt.count(starts)} times as people deployed changes "
               "to the unpinned harness code")
    p1 += (". That is what autonomous means here: no person chooses what the search tries or "
           "how it scores, which is not the same as running free of human operation.</p>")

    p2 = (
        f"<p>Epoch 2 started on {esc(fmt.day(e2['started']))} under a new verifier hash, "
        f"{code(e2['verifier_hash'])}. It stopped late that day, and nothing restarted it until "
        f"{esc(fmt.day(down['to']))}. The watchdog now resumes the stops it makes itself; after a "
        "reboot the run is started by hand with one command. "
        f"As of {esc(fmt.day(e2['as_of']))}, epoch 2 had reached search cycle "
        f"{fmt.count(e2['cycle'])} with {fmt.count(e2['records'])} records. Its records are "
        "scored under the corrected cost model, so they are not comparable with epoch 1's, and "
        "the chart keeps the two epochs as separate series. "
        '<a href="epochs.html">Epochs and research</a> has the timeline.</p>'
    )
    body = p1 + p2 + figure(charts.archive_chart(rk))
    return _section("archive-growth", "Archive growth", body)


def _snapshot(data):
    sources = data["sources"]
    overview = _site(sources, "rk-overview")
    body = (
        f"<p>This page is a snapshot of data read on {esc(fmt.day(sources['snapshot_date']))}. "
        f'The rk run keeps going: the <a href="{esc(FINDINGS_URL)}">rk-findings site</a> '
        "rebuilds every cycle and has the current numbers. The "
        f'<a href="{esc(overview)}">rk-overview site</a> explains the run at more length and '
        "reruns the Q15 solver in the browser.</p>"
        "<p>Every claim on this page is listed with its verdict, limits and evidence in the "
        '<a href="claims.html">claims audit</a>, and <a href="architecture.html">Architecture</a> '
        "shows how the run is put together.</p>"
    )
    return _section("snapshot-note", "Snapshot", body)


def build(data):
    rk = data["rk"]
    parts = [
        f"<h1>{esc(TITLE)}</h1>",
        _lead(rk),
        _question(rk),
        _scoring(rk),
        _results(rk),
        _validation(rk),
        _float64(rk),
        _rounding(rk),
        _cost_model(rk),
        _not_shown(rk),
        _archive(rk),
        _snapshot(data),
    ]
    return "\n".join(parts) + "\n"


def assets(data):
    """Standalone copies of two charts, for the README: the Q15 result and its float64 boundary."""
    rk = data["rk"]
    return {
        "rk-frontier.svg": standalone(charts.frontier_chart(rk)),
        "rk-validation-f64.svg": standalone(charts.validation_f64_chart(rk)),
    }
