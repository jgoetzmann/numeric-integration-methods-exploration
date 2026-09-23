"""The rk run page (rk.html).

Every number is read from data["rk"] or data["sources"] and rendered through
web.fmt. Every result sentence names its conditions and links its claim id.
"""

from web import fmt
from web.charts import figure, standalone, table
from web.fmt import esc

from . import charts
from .charts import and_list, claim_ref, code, word

SLUG = "rk.html"
TITLE = "The rk run"
DESCRIPTION = ("What the rk run searched for, what it found in Q15 fixed point with floor "
               "rounding, and where established methods still win.")

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


def _lead(rk):
    ch = rk["champion"]
    n_cls = len(rk["frontier"]["classical"])
    return (
        '<section class="lead" aria-label="Summary">'
        "<p>The rk run is an unattended search for Runge-Kutta coefficients that give the lowest "
        f"error in Q15 fixed point with floor rounding, at a fixed budget of {_budget(rk)} cycles "
        "on a modeled Cortex-M0+. Inside that frame, on the analytic cost model with magnitude "
        f"weighting, it found a {word(ch['stages'])}-stage method, {code(ch['hash'])}, whose "
        f"held-out error is {fmt.ratio(ch['lead'])} lower than that of "
        f"{code(ch['best_classical'])}, the best of the {word(n_cls)} classical methods "
        f"{claim_ref('R1')}.</p>"
        "<p>Outside that frame the result does not carry over. In float64, "
        f"{code('rk4')} and the adaptive library solvers, Dormand-Prince (SciPy {code('RK45')}) "
        "among them, are far more accurate than anything the search found "
        f"{claim_ref('R5')}. Every cycle count on this page comes from a cost model or an "
        "emulator; nothing was measured on a physical chip.</p>"
        "</section>"
    )


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
        f"{code('1/4')}. In Q15 a dyadic coefficient such as {code('13/16')} can be applied "
        f"with a few shifts and adds, while {code('1/3')} needs a multiply.</p>"
        "<p>The cycle counts come from an analytic model of the Cortex-M0+, "
        f"{code(setup['cost_model'])}, which prices the stage and weight combinations of a step. "
        "They are modeled, not measured on a chip.</p>"
    )
    return _section("question", "The question", body)


def _scoring(rk):
    eng = rk["engineering"]
    ep1 = rk["epochs"]["epoch1"]
    held = rk["setup"]["heldout_problems"]
    body = (
        "<p>Every candidate tableau goes through a verifier before it is scored. The verifier "
        "checks the order conditions exactly, in rational arithmetic, and rejects a tableau that "
        "is not explicit, breaks the row-sum conditions, would overflow Q15 with a two-times "
        "margin, or falls outside the coefficient and stability limits.</p>"
        "<p>A tableau that passes is run in Q15 with floor rounding on a set of search problems, "
        f"each at the {_budget(rk)}-cycle budget. The archive sorts methods into cells by order, "
        "stage count and cost band, and keeps in each cell the method with the lowest RMS error "
        f"on {word(len(held))} held-out problems: {and_list([code(h) for h in held])}. No "
        "optimizer reads the held-out problems. The model that proposes search directions does "
        "see one held-out error per cell, though, and elites are picked on those errors, so the "
        f"held-out numbers are not independent of the search {claim_ref('U2')}.</p>"
        "<p>The scorer is out of the search's reach. The harness is mounted read-only, a sha256 "
        f"over {fmt.count(eng['verifier_files'])} files ({fmt.count(ep1['verifier_files'])} in "
        "epoch 1) is checked at every start and stored in every record, and "
        f"{fmt.count(eng['golden_gate_cases'])} golden and canary cases must pass before any "
        f"cycle runs {claim_ref('R11')}. The test suite collected "
        f"{fmt.count(eng['tests_collected'])} tests on {esc(fmt.day(eng['tests_collected_on']))}."
        "</p>"
    )
    return _section("scoring", "How a candidate is scored and verified", body)


def _cell(cells, weighting, basis):
    for c in cells:
        if c["weighting"] == weighting and c["basis"] == basis:
            return c


def _loo_table(ch):
    rows = []
    for r in ch["leave_one_out"]:
        name = code(r["dropped"]) if r.get("dropped") else "none (all four problems)"
        rows.append([name, fmt.ratio(r["ratio"])])
    return table(["Held-out problem dropped", "Ratio, best classical error over champion"],
                        rows,
                        caption=("Leave-one-out check: Q15 with floor rounding, analytic cost "
                                 "model, magnitude weighting"))


def _results(rk):
    ch = rk["champion"]
    fr = rk["frontier"]
    cf = rk["counterfactual"]
    cells = cf["cells"]
    budget = _budget(rk)

    loo = [r for r in ch["leave_one_out"] if r.get("dropped")]
    lo_row = min(loo, key=lambda r: r["ratio"])
    hi_row = max(loo, key=lambda r: r["ratio"])

    n_total = fr["cells_total"]
    n_disc = fr["cells_held_by_discovered"]
    n_cls = fr["cells_held_by_classical"]
    n_lead = fr["cells_where_discovered_leads_every_cheaper_or_equal_classical"]
    if n_lead == n_disc:
        in_cells = f"in all {fmt.count(n_disc)} discovered cells"
    else:
        in_cells = f"in {fmt.count(n_lead)} of the {fmt.count(n_disc)} discovered cells"

    body = (
        f"<p>The champion, {code(ch['hash'])}, has {fmt.count(ch['stages'])} stages and order "
        f"{fmt.count(ch['order'])}, and costs {fmt.count(ch['cycles_per_step'])} cycles per step "
        "on the analytic model. Every coefficient is a dyadic fraction.</p>"
        + _tableau(ch)
        + f"<p>Inside Q15 with floor rounding, at the {budget}-cycle budget, on the analytic "
        "cost model with magnitude weighting, the champion's held-out RMS error is "
        f"{fmt.sig(ch['heldout_error'])} against {fmt.sig(ch['best_classical_heldout_error'])} "
        f"for {code(ch['best_classical'])}, the best classical method: a lead of "
        f"{fmt.ratio(ch['lead'])} {claim_ref('R1')}. Elites are picked from the archive by "
        "held-out error, so that lead carries winner's-curse bias.</p>"
        f"<p>It appeared at cycle {fmt.count(ch['found_at_cycle'])}. Nothing in the remaining "
        f"{fmt.count(ch['cycles_since_last_improvement'])} of epoch 1's "
        f"{fmt.count(ch['cycles_run'])} cycles improved on it {claim_ref('R6')}. From then on, "
        "the run's value lay mostly in checking this result rather than in improving it.</p>"
        "<p>The champion is not the only discovered method ahead of the classical ones. Epoch 1 "
        f"filled {fmt.count(n_total)} cells in the archive, {fmt.count(n_disc)} with a discovered "
        f"method and {fmt.count(n_cls)} with a classical one. Under the same conditions, "
        f"{in_cells} the discovered method has lower held-out error than every classical method "
        f"that costs the same or less {claim_ref('R2')}.</p>"
        f"<p>Dropping any one of the {word(len(loo))} held-out problems leaves the champion "
        f"ahead, by {fmt.ratio(lo_row['ratio'])} to {fmt.ratio(hi_row['ratio'])} on the same "
        f"basis {claim_ref('R3')}. The low end comes from dropping {code(lo_row['dropped'])}, "
        "which carries most of the champion's lead.</p>"
        + _loo_table(ch)
        + figure(charts.frontier_chart(rk))
    )

    # How the lead depends on cost basis and weighting.
    weightings, bases = [], []
    for c in cells:
        if c["weighting"] not in weightings:
            weightings.append(c["weighting"])
        if c["basis"] not in bases:
            bases.append(c["basis"])
    pub = _cell(cells, "magnitude", "analytic")
    mag_tr = _cell(cells, "magnitude", "traced_whole_step")
    med_tr = _cell(cells, "equal_median_anchor", "traced_whole_step")
    still = [c for c in cells if c["champion_still_leads"]]

    sub = '<h3 id="lead-conditions">How the lead depends on cost basis and weighting</h3>'
    sub += (
        f"<p>The {fmt.ratio(pub['ratio'])} figure is one cell in a grid of "
        f"{word(len(cells))}: {word(len(weightings))} ways to weight the held-out problems "
        f"against each other, times {word(len(bases))} ways to count what a step costs. The "
        "analytic basis prices only the stage and weight combinations. The traced whole-step "
        "basis compiles the step, counts the cycles of the whole step under an emulator, "
        "including the derivative call and loop control, and uses that count only to decide "
        f"how many steps fit in {budget} cycles.</p>"
    )
    para = []
    para.append("On the traced whole-step basis with magnitude weighting, still in Q15 with "
                f"floor rounding, the lead shrinks to {fmt.ratio(mag_tr['ratio'])}.")
    if med_tr["ratio"] < 1:
        para.append(f"With median-anchor weighting on that basis, {code('midpoint')} leads "
                    f"at a ratio of {fmt.ratio(med_tr['ratio'])} {claim_ref('R1')}.")
    else:
        para.append(f"With median-anchor weighting on that basis the ratio is "
                    f"{fmt.ratio(med_tr['ratio'])} {claim_ref('R1')}.")
    tail = ""
    if still and all(c["basis"] == "analytic" for c in still):
        if len(still) == 1:
            tail = ", on the analytic basis"
        elif len(still) == 2:
            tail = ", both on the analytic basis"
        else:
            tail = ", all on the analytic basis"
    para.append(f"The champion stays ahead on every leave-one-out subset in "
                f"{word(len(still))} of the {word(len(cells))} cells{tail}.")
    sub += "<p>" + " ".join(para) + "</p>"
    sub += figure(charts.counterfactual_chart(rk))

    return _section("results", "What the search found", body + sub)


def _validation(rk):
    val = rk["validation"]
    probs = val["problems"]
    budget = _budget(rk)
    non_stiff = [p for p in probs if not p.get("stiff")]
    stiff = [p for p in probs if p.get("stiff")]
    champ_wins = sum(1 for p in non_stiff if p["champion_q15"] < p["best_classical_q15"])

    stiff_parts = []
    for p in stiff:
        if p.get("champion_overflowed") or p.get("best_discovered_q15") is None:
            stiff_parts.append(f"on {code(p['problem'])} every discovered method overflowed while "
                               f"{code(p['best_classical'])} finished")
        elif p.get("winner_kind") == "classical":
            stiff_parts.append(
                f"on {code(p['problem'])} {code(p['best_classical'])} had the lower error, "
                f"{fmt.sig(p['best_classical_q15'], 4)} against "
                f"{fmt.sig(p['best_discovered_q15'], 4)} for the best discovered method")
    stiff_sentence = (f"<p>Under the same Q15 floor rounding and budget, the stiff problems went "
                      f"less well. A discovered method had the "
                      f"lower error on {fmt.count(val['stiff_won_by_discovered'])} of the "
                      f"{fmt.count(val['stiff_total'])}")
    if stiff_parts:
        stiff_sentence += "; " + "; ".join(stiff_parts)
    stiff_sentence += ".</p>"

    body = (
        f"<p>The run then scored the champion on {word(len(probs))} further problems from "
        f"embedded domains, {word(len(non_stiff))} non-stiff and {word(len(stiff))} stiff. No "
        "optimizer or model saw these problems, and the champion was fixed before they ran. "
        "People chose the problems after the search began, though, so this is an out-of-sample "
        "check rather than an independent benchmark.</p>"
        f"<p>In Q15 with floor rounding at the {budget}-cycle budget, the best discovered method "
        "had lower error than the best classical method on "
        f"{fmt.count(val['practical_won_by_discovered'])} of {fmt.count(val['practical_total'])} "
        "non-stiff problems, with a median error ratio of "
        f"{fmt.sig(val['practical_median_ratio'])} (discovered over classical) across those "
        f"{word(val['practical_total'])} {claim_ref('R4')}. The fixed champion alone had the "
        f"lower error on {fmt.count(champ_wins)} of the {fmt.count(len(non_stiff))}.</p>"
        + stiff_sentence
        + figure(charts.validation_q15_chart(rk))
    )
    return _section("validation", "Out-of-sample check", body)


def _float64(rk):
    gap = rk["float64_gap"]
    lib = rk["libraries"]
    n_cells = lib["fixed_step_cells_compared"]
    rk4_lower = n_cells - lib["fixed_step_cells_where_q15_error_lower"]
    libs = [s["library_method"] for s in lib.get("solvers", [])
            if s.get("side") == "library" and s.get("library_method")]
    body = (
        "<p>The search optimized for Q15 floor arithmetic on purpose, and its methods fall far "
        f"behind once the arithmetic is float64 {claim_ref('R5')}. At the same step counts in "
        f"float64, {code('rk4')} had the lower error in {fmt.count(rk4_lower)} of "
        f"{fmt.count(n_cells)} fixed-step cells. On the {fmt.count(gap['problems'])} validation "
        "problems where both methods finish, the champion in float64 was "
        f"{fmt.ratio(gap['champion_over_rk4_min'])} to {fmt.ratio(gap['champion_over_rk4_max'])} "
        f"less accurate than {code('rk4')} in float64.</p>"
        "<p>At tolerances matched to one Q15 step, the adaptive library solvers, Dormand-Prince "
        f"(SciPy {code('RK45')}) among them, were a median "
        f"{fmt.ratio(lib['median_ratio_q15_over_library_at_matched_tolerance'])} more accurate "
        "than the best Q15 result."
    )
    body += (f" The library set is {and_list([code(x) for x in libs])}, run in compiled "
             "float64 through SciPy.")
    body += (
        "</p>"
        "<p>This is where the Q15 result stops applying. Nothing on this page says "
        f"the champion is more accurate than {code('rk4')} or Dormand-Prince outside Q15 with "
        "floor rounding.</p>"
        + figure(charts.validation_f64_chart(rk))
    )
    return _section("float64", "Where established methods win", body)


def _rounding(rk):
    fvr = rk["floor_vs_round"]
    search = fvr["search_rms"]
    held = fvr["heldout_rms"]
    budget = _budget(rk)
    modes, names = charts._floor_round_methods(rk, search)
    fl = search["floor"]
    rn = search["round_to_nearest"]
    lowest = min(names, key=lambda n: fl[n])
    highest = max(names, key=lambda n: fl[n])

    p1 = ("<p>Floor rounding changes which classical method does best. On the search problems, "
          f"in Q15 at the {budget}-cycle budget, {code(lowest)} has the lowest RMS error under "
          f"floor rounding ({fmt.sig(fl[lowest])}) and {code(highest)} the highest "
          f"({fmt.sig(fl[highest])})")
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
               f"{word(len(names))} under both rounding modes.</p>")
    else:
        p2 += (f"On the held-out problems {code(bf)} has the lowest error under floor "
               f"rounding and {code(br)} under round-to-nearest.</p>")

    pr = rk["premise"]

    def of(s):
        a, _, b = str(s).partition("/")
        return f"{esc(a)} of {esc(b)}"

    p3 = (
        "<p>The run tested its premise before the search began. At the budget, "
        f"{code('rk4')} was the best method on {of(pr['rk4_best_under_floor'])} premise problems "
        f"under floor rounding, against {of(pr['rk4_best_under_round_to_nearest'])} under "
        f"round-to-nearest. The stored verdict is {esc(pr['stored_verdict'])}: the thresholds "
        "set in advance were met for some methods and missed narrowly for one "
        f"{claim_ref('R9')}.</p>"
    )
    body = p1 + p2 + p3 + figure(charts.floor_round_chart(rk))
    return _section("rounding", "Rounding reorders the classical methods", body)


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
        "wall-clock time: it supports the model's ordering of methods, not its absolute cycle "
        "counts on a Cortex-M0+.</p>"
    )
    p2 = (
        "<p>The run also compiled the step with GCC 13.2.1 for the Cortex-M0+ and traced it under "
        f"the {code('unicorn')} emulator. The compiled step reproduced the Python evaluator bit "
        f"for bit in {esc(eng['trace_crosscheck'])} cases, and it showed that the epoch-1 cost "
        f"model put {code('rk4')} and {code('rk38')} in the wrong order {claim_ref('R7')}"
    )
    a4 = by["rk4"]["analytic"][model]
    a38 = by["rk38"]["analytic"][model]
    m4 = by["rk4"]["matched_scope"][model]
    m38 = by["rk38"]["matched_scope"][model]
    p2 += (f": the analytic model prices {code('rk4')} at {fmt.count(a4)} cycles per step and "
           f"{code('rk38')} at {fmt.count(a38)}, while the traced count at matched scope, "
           f"which covers the same work, is {fmt.count(m4)} and {fmt.count(m38)}")
    p2 += ".</p>"
    p3 = (
        "<p>The emulator is instruction-accurate, not cycle-accurate: its cycle counts come from "
        "a timing table applied to the executed instructions, and nothing was measured on a "
        "physical chip. Rather than rescore the old archive, the run froze epoch 1 and started "
        "epoch 2 under a corrected cost model that prices each coefficient by the instructions "
        'GCC emits for it. <a href="epochs.html">Epochs and research</a> covers that decision.</p>'
    )
    body = p1 + p2 + p3 + _trace_table(rk)
    return _section("cost-model", "Speed and the cost model", body)


def _not_shown(rk):
    ch = rk["champion"]
    cells = rk["counterfactual"]["cells"]
    mag_tr = _cell(cells, "magnitude", "traced_whole_step")
    items = [
        "It measured nothing on hardware. Cycle counts come from an analytic model, checked "
        "against Python timing and an instruction-accurate emulator "
        f"{claim_ref('R7', 'R10')}.",
        f"It found no method more accurate than {code('rk4')} or Dormand-Prince in float64. The "
        f"champion's lead exists only inside Q15 with floor rounding {claim_ref('R5')}.",
        "Its held-out errors are not independent of the search. Elites are chosen on them and "
        f"the model that proposes directions sees them, so the {fmt.ratio(ch['lead'])} lead (Q15 "
        "with floor rounding, analytic basis, magnitude weighting) carries winner's-curse bias "
        f"{claim_ref('R1', 'U2')}.",
        "Its validation is an out-of-sample check, not an independent benchmark. No optimizer "
        "or model saw the validation problems, but people chose them after the search began "
        f"{claim_ref('R4')}.",
    ]
    items.append("Its lead depends on the cost basis. On the traced "
                 "whole-step basis with magnitude weighting, in Q15 with floor rounding, it "
                 f"is {fmt.ratio(mag_tr['ratio'])} {claim_ref('R1')}.")
    items.append("Its methods do not handle every stiff problem. Every discovered method "
                 f"overflowed on {code('robertson_scaled')} {claim_ref('R4')}.")
    items.append(f"It did not map the search space. The plateau after cycle "
                 f"{fmt.count(ch['found_at_cycle'])} describes one search, not a field of local "
                 f"minima {claim_ref('U3')}.")
    items.append("Epoch 2 has no validation, benchmark or trace results of its own yet, so every "
                 "result on this page comes from epoch 1.")
    body = "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"
    return _section("not-shown", "What the run did not show", body)


def _archive(rk):
    ep = rk["epochs"]
    e1 = ep["epoch1"]
    e2 = ep["epoch2"]
    down = e2["down_days"]
    p1 = (
        f"<p>Epoch 1 ran unattended from {esc(fmt.day(e1['started']))} to "
        f"{esc(fmt.day(e1['stopped']))}: {fmt.count(e1['cycles_run'])} cycles over "
        f"{fmt.count(e1['archive_day_count'])} days of archive, ending with "
        f"{fmt.count(e1['records'])} scored records {claim_ref('R12')}. Epoch 2 has run since "
        f"{esc(fmt.day(e2['started']))} under a new verifier hash, {code(e2['verifier_hash'])}, "
        f"which replaced epoch 1's {code(e1['verifier_hash'])}.</p>"
    )
    p2 = "<p>"
    p2 += (f"Epoch 2 lost five days to a stop that nothing restarted, from "
           f"{esc(fmt.day(down['from']))} to {esc(fmt.day(down['to']))}. The watchdog now "
           "resumes its own stops, and a logon task restarts the run after a reboot. ")
    p2 += (
        f"As of {esc(fmt.day(e2['as_of']))}, epoch 2 had reached cycle {fmt.count(e2['cycle'])} "
        f"with {fmt.count(e2['records'])} records. Its records are scored under the corrected "
        "cost model, so they are not comparable with epoch 1's, and the chart keeps the two "
        'epochs as separate series. <a href="epochs.html">Epochs and research</a> has the '
        "timeline.</p>"
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
