"""The Story page (index.html): both projects on one page, with the headline claims.

Every number is read from data/*.json and rendered through web.fmt. Each result links a
key phrase to its claim in claims.html the first time it appears.
"""

import re

from web import fmt

SLUG = "index.html"
TITLE = "Story"
DESCRIPTION = (
    "Two searches for better Runge-Kutta coefficients: what each one found, "
    "and where established methods still lead."
)

FINDINGS_URL = "https://jgoetzmann.github.io/rk-findings/"

# Headline claims stated and linked in full by the lead (U1) or the scoring table (R11),
# so they get no card of their own.
NO_CARD = {"U1", "R11"}

VERDICT_LABELS = {
    "supported": "Supported",
    "supported-with-limits": "Supported with limits",
    "not-supported": "Not supported",
    "artifact": "Artifact",
}

_WORDS = {
    1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
    7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve",
}


def _word(n):
    """Small structural counts as words (writing rule 3)."""
    return _WORDS.get(int(n), fmt.count(n))


def _link(href, text):
    return f'<a href="{fmt.esc(href)}">{text}</a>'


def _cl(cid, text):
    """A key phrase linked to its claim."""
    return _link(f"claims.html#{cid}", text)


def _code(s):
    return "<code>" + fmt.esc(s) + "</code>"


def _cell(rk, basis, weighting):
    for c in rk["counterfactual"]["cells"]:
        if c["basis"] == basis and c["weighting"] == weighting:
            return c


def _trap_cases(rk):
    """How many of the trace cross-check cases are overflow traps, read from trace.crosscheck."""
    m = re.search(r"(\d[\d,]*) of them are cases where", rk["trace"].get("crosscheck", ""))
    return int(m.group(1).replace(",", "")) if m else None


def _lead(rk):
    champ = rk["champion"]
    budget = fmt.count(rk["setup"]["budget_cycles"])
    n_classical = _word(len(rk["frontier"]["classical"]))
    return (
        '<p class="lead">Both projects asked whether a search can find Runge-Kutta '
        "coefficients that do better than the textbook ones. In float64, "
        f"{_cl('U1', 'established methods were more accurate in both')}, though the 2025 half "
        "of that is weak evidence. Inside Q15 fixed point with floor rounding, at a "
        f"{budget}-cycle budget on the analytic cost model with magnitude weighting, the rk "
        "run found a "
        f"{_word(champ['stages'])}-stage method with "
        f"{_cl('R1', fmt.ratio(champ['lead']) + ' lower held-out error')} than the best of "
        f"{n_classical} classical methods. That figure comes from the epoch-1 cost model, "
        "which a later trace found "
        f"{_cl('R7', 'had <code>rk4</code> and <code>rk38</code> in the wrong order')}; epoch 2 "
        "has not re-measured it, and it moves with the cost basis and the weighting.</p>"
    )


def _dated(sources):
    return (
        f'<p class="note">Figures date from {fmt.day(sources["snapshot_date"])}; the rk run has '
        f"kept going, and {_link(FINDINGS_URL, 'its findings site')} has current numbers.</p>"
    )


def _terms(rk):
    budget = fmt.count(rk["setup"]["budget_cycles"])
    n_heldout = _word(len(rk["setup"]["heldout_problems"]))
    items = [
        ("Q15",
         "A sixteen-bit fixed-point fraction between minus one and one, for chips without a "
         "floating-point unit."),
        ("Floor rounding",
         "Each Q15 multiply rounds toward minus infinity, so every product errs the same way."),
        ("Cycle budget",
         f"{budget} modeled clock cycles per method per problem, so a cheaper step buys more "
         "steps."),
        ("Analytic and traced cost",
         "The analytic model prices coefficient arithmetic only; the traced count prices the "
         "compiled step, minus the derivative routine's body."),
        ("Held-out problems",
         f"{n_heldout.capitalize()} problems that elites are picked on and the optimizer never "
         "reads: a selection set, not a test set."),
        ("Cell and elite",
         "The archive sorts methods into cells by order, stage count and cost band; a cell's "
         "elite is its method with the lowest held-out error."),
        ("Weighting",
         f"How the {n_heldout} held-out errors become one number. Magnitude weighting, which "
         "the archive uses, is their RMS, so small errors count for little; median-anchor "
         f"weighting counts the {n_heldout} equally."),
        ("Epoch",
         "A stretch of the rk run under one set of pinned scoring files."),
    ]
    body = "\n".join(f"<dt>{fmt.esc(t)}</dt>\n<dd>{d}</dd>" for t, d in items)
    return '<h2 id="terms">Terms</h2>\n<dl class="terms">\n' + body + "\n</dl>"


def _projects(rk, novel, sources):
    e1 = rk["epochs"]["epoch1"]
    e2 = rk["epochs"]["epoch2"]
    down = e2["down_days"]
    repo = novel["repo"]
    return (
        '<h2 id="projects">The two projects</h2>\n'
        '<div class="cards projects">\n'
        '<article class="card project-card">\n'
        f'<h3>{_link("rk.html", "The rk run")}</h3>\n'
        f'<p class="card-dates">{fmt.day(e1["started"])} onward</p>\n'
        "<p>An autonomous search, run in a container, for coefficients that do well in Q15 "
        "on a modeled Cortex-M0+. A language model "
        f"{_cl('R13', 'steers it through a JSON directive that can only narrow the search')}, "
        f"and code does the scoring. {_link('epochs.html', 'Epoch 1')} ran until "
        f"{fmt.day(e1['stopped'])}: {fmt.count(e1['cycles_run'])} search cycles and "
        f"{fmt.count(e1['records'])} scored records. No person chose candidates or scores, "
        f"though {_cl('R12', 'the runner started ' + fmt.count(e1['events']['runner_started']) + ' times')}, "
        "including restarts to deploy changes to unpinned code. Epoch 2 started on "
        f"{fmt.day(e2['started'])} under a corrected cost model, stopped late that day, and "
        f"stayed down until {fmt.day(down['to'])}.</p>\n"
        "</article>\n"
        '<article class="card project-card">\n'
        f'<h3>{_link("novel.html", "The 2025 ML project")}</h3>\n'
        f'<p class="card-dates">Active {fmt.day(repo["active_from"])} to '
        f'{fmt.day(repo["active_to"])}</p>\n'
        "<p><code>Novel-Numerical-Integration-Methods</code> tried to generate new explicit "
        "Runge-Kutta tables with a neural generator, a surrogate model and evolutionary "
        f"search, in float64. {_cl('N9', 'Its evaluation harness runs end to end')} for "
        "explicit tables. Its main conclusions from 2025 did not hold.</p>\n"
        "</article>\n"
        "</div>\n"
        "<p>The same author built both, and audited the 2025 project in September 2026, after "
        "the rk run began. The code and data for both are in "
        f"{_link('repos.html', _word(len(sources['repos'])) + ' repositories')}.</p>"
    )


def _card_texts(data):
    """Heading and body HTML for each headline claim: the result and its conditions."""
    rk = data["rk"]
    novel = data["novel"]
    champ = rk["champion"]
    budget = fmt.count(rk["setup"]["budget_cycles"])
    per_problem = champ["per_problem_heldout"]
    best = champ["best_classical"]
    best_pp = champ["classical_per_problem_heldout"][best]
    worse_on = sorted(p for p in per_problem if per_problem[p] > best_pp[p])
    equal = _cell(rk, "analytic", "equal_median_anchor")
    traced = _cell(rk, "traced_whole_step", "magnitude")
    rtn_all = rk["floor_vs_round"]["heldout_rms"]["round_to_nearest"]
    rtn_best = min(sorted(rtn_all), key=lambda m: rtn_all[m])
    frontier = rk["frontier"]
    classical_best = min(c["heldout_error"] for c in frontier["classical"])
    ahead_of_all = sum(1 for d in frontier["discovered"] if d["heldout_error"] < classical_best)
    val = rk["validation"]
    nonstiff = [p for p in val["problems"] if not p["stiff"]]
    champ_alone = sum(
        1 for p in nonstiff
        if p["champion_q15"] is not None and p["champion_q15"] < p["best_classical_q15"]
    )
    over = next(p for p in val["problems"] if p["champion_overflowed"])
    gap = rk["float64_gap"]
    eng = rk["engineering"]
    traps = _trap_cases(rk)
    trap_clause = f", {fmt.count(traps)} of them overflow cases," if traps else ""
    bench = novel["benchmark"]
    rows = {r["id"]: r for r in bench["rows"]}
    dp_err = rows["baseline_rk45_dormand_prince"]["mean_max_error"]
    rk4_err = rows["baseline_rk4"]["mean_max_error"]
    clip = fmt.sig(novel["metrics_log"]["composite_score_distinct_values"][0])
    by_id = {c["id"]: c for c in data["claims"]["claims"]}

    def rejected(cid):
        return f"<p><q>{fmt.esc(by_id[cid]['claim'])}</q></p>\n"

    floor_problem = min(
        (x for x in champ["leave_one_out"] if x["dropped"]), key=lambda x: x["ratio"]
    )["dropped"]
    worse_clause = ""
    if worse_on:
        names = ", ".join(_code(p) for p in worse_on)
        worse_clause = (
            f" It has higher error than {_code(best)} on {names}, and much of the gap comes "
            f"from {_code(floor_problem)}, where every classical method stalls near a "
            "quantization floor."
        )

    return {
        "R1": (
            "The Q15 lead",
            f"<p>The champion, {_code(champ['hash'])}, was picked on held-out error from "
            f"{fmt.count(frontier['unique_tableaus'])} archived tableaus, so its lead over "
            f"{_code(best)}, the best classical method, carries selection bias."
            f"{worse_clause}</p>\n"
            "<p>On the traced whole-step basis the lead falls to "
            f"{fmt.ratio(traced['ratio'])}, which dropping one held-out problem overturns. With "
            f"the {_word(len(per_problem))} problems weighted equally it is "
            f"{fmt.ratio(equal['ratio'])} on the analytic basis, and dropping one can reverse "
            f"that too (lowest {fmt.ratio(equal['lowest_leave_one_out_ratio'])}). Under "
            "round-to-nearest, at the same budget and cost model and with no extra cycles "
            f"charged for the rounding, {_code(rtn_best)}, one of the {_word(len(rtn_all))} "
            "classical methods run under both rounding modes, reaches "
            f"{fmt.sig(rtn_all[rtn_best])} held-out error, below the champion's "
            f"{fmt.sig(champ['heldout_error'])} under floor rounding.</p>",
        ),
        "R2": (
            "Discovered elites lead in every cell they hold",
            f"<p>In Q15 with floor rounding at the {budget}-cycle budget, on the analytic cost "
            "model with magnitude weighting and with the same selection bias, all "
            f"{fmt.count(ahead_of_all)} discovered methods that hold one of the "
            f"{fmt.count(frontier['cells_total'])} occupied archive cells have lower held-out "
            "error than every classical method, whatever its cost. The closest is "
            f"{fmt.sig(frontier['closest_discovered_to_classical'])} against "
            f"{_code(best)}'s {fmt.sig(classical_best)}.</p>",
        ),
        "R4": (
            "Out-of-sample problems",
            f"<p>On {_word(len(val['problems']))} problems chosen after the search began, the "
            f"best of {_word(val['discovered_methods_run'])} discovered methods had lower Q15 "
            f"error than the best of {_word(len(val['classical_methods_run']))} classical ones "
            f"on {fmt.count(val['practical_won_by_discovered'])} of "
            f"{fmt.count(val['practical_total'])} non-stiff problems, the champion by itself on "
            f"{fmt.count(champ_alone)}. On the stiff {_code(over['problem'])}, every "
            "discovered method overflowed, as did <code>rk4</code> and <code>rk38</code>.</p>",
        ),
        "R5": (
            "In float64, rk4 is far more accurate",
            f"<p>At the step count the {budget}-cycle budget gives each method, the champion's "
            f"float64 error was {fmt.ratio(gap['champion_over_rk4_min'])} to "
            f"{fmt.ratio(gap['champion_over_rk4_max'])} that of <code>rk4</code> on the "
            f"{_word(gap['problems'])} validation problems where both finish, second order "
            "against fourth. Dormand-Prince never ran against the champion in the same "
            "arithmetic.</p>",
        ),
        "R7": (
            "A trace caught the cost model's error",
            "<p>The compiled step matched the Python evaluator in "
            f"{fmt.esc(eng['trace_crosscheck'])} cases{trap_clause} on an emulator that is "
            "instruction-accurate but not cycle-accurate. Once the trace found <code>rk4</code> and "
            "<code>rk38</code> in the wrong order, the run froze epoch 1 instead of rescoring "
            "it.</p>",
        ),
        "N1": (
            "The 2025 benchmark ran",
            f"<p>In float64, over {fmt.count(bench['methods'])} entries and "
            f"{fmt.count(bench['odes'])} ODEs ({fmt.count(bench['scorable_odes'])} scorable), "
            f"Dormand-Prince had the lowest mean error ({fmt.sig(dp_err)}) and RK4 the next "
            f"({fmt.sig(rk4_err)}). The other entries were copies of those two, random tables "
            "or truncated methods, and the reference solver was itself Dormand-Prince.</p>",
        ),
        "N2": (
            "The saved tables never left the seeds",
            rejected("N2")
            + "<p>The genetic operators ran, but RK4 and Dormand-Prince were seeded in and "
            f"every score tied at the clip of {clip}, so the saved table never changed.</p>",
        ),
        "N4": (
            "The generator was never trained",
            rejected("N4")
            + "<p>The generator's optimizer was never stepped. Gradient descent trained only a "
            "surrogate model, and nothing in training reads its predictions.</p>",
        ),
    }


def _card(claim, heading, body):
    cid = claim["id"]
    verdict = claim["verdict"]
    return (
        '<article class="card claim-card">\n'
        f"<h3>{_cl(cid, fmt.esc(heading))}</h3>\n"
        f"{body}\n"
        f'<p class="card-foot"><span class="verdict verdict-{fmt.esc(verdict)}">'
        f"{fmt.esc(VERDICT_LABELS.get(verdict, verdict))}</span></p>\n"
        "</article>"
    )


def _results(data):
    headline = [
        c for c in data["claims"]["claims"]
        if c.get("headline") is True and c["id"] not in NO_CARD
    ]
    texts = _card_texts(data)
    cards = []
    for claim in headline:
        heading, body = texts[claim["id"]]
        cards.append(_card(claim, heading, body))
    return (
        '<h2 id="results">Results</h2>\n'
        '<div class="cards claims">\n' + "\n".join(cards) + "\n</div>"
    )


def _scoring(rk, novel):
    log = novel["metrics_log"]
    epochs = len(log["per_epoch"])
    clip = fmt.sig(log["composite_score_distinct_values"][0])
    seed = novel["audit_counts"]["random_generator_seed"]
    bench = novel["benchmark"]
    eng = rk["engineering"]
    e1 = rk["epochs"]["epoch1"]
    n_heldout = _word(len(rk["setup"]["heldout_problems"])).capitalize()
    n_oos = _word(len(rk["validation"]["problems"]))
    rows = [
        (
            "What a candidate is scored on",
            f"A composite clipped at {clip}. "
            f"{_cl('N2', 'All ' + fmt.count(log['rows']) + ' rows')} of the one training log "
            f"({fmt.count(epochs)} epochs of {fmt.count(log['rows'] // epochs)} candidates) "
            f"score {clip}.",
            "Search-set error for the optimizer and held-out error for choosing elites, both "
            "in Q15 at the cycle budget.",
        ),
        (
            "Order conditions",
            f"None enforced. {_cl('N10', 'Its order-4 test labels RK4 as order 3')}.",
            "Exact rational order conditions, checked before a candidate is scored.",
        ),
        (
            "Where the search starts",
            "RK4 and Dormand-Prince in the starting populations, and "
            f"{_cl('N4', 'a random generator reseeded to ' + fmt.count(seed))} for empty slots.",
            "An exhaustive lattice of dyadic coefficients, then CMA-ES over the stage matrix.",
        ),
        (
            "Guarding the scorer",
            f"{_cl('N11', 'No automated test suite')}.",
            f"A {_link('architecture.html', 'read-only harness')}, "
            f"{_cl('R11', 'a sha256 over the pinned files')} "
            f"({fmt.count(e1['verifier_files'])} in epoch 1, {fmt.count(eng['verifier_files'])} "
            "since epoch 2) checked at every start and stored in every record, and "
            f"{fmt.count(eng['golden_gate_cases'])} gate cases that must pass before any search "
            "cycle.",
        ),
        (
            "Problems outside the search",
            f"A {_cl('N1', 'final benchmark on ' + fmt.count(bench['odes']) + ' generated ODEs')}.",
            f"{n_heldout} held-out problems, then "
            f"{_cl('R4', n_oos + ' out-of-sample ones')}.",
        ),
        (
            "What gets published",
            "Every benchmark entry, the weakest included.",
            f"Negative results too: {_cl('R9', 'a mixed premise test')} and "
            f"{_cl('R5', 'the float64 gap')}.",
        ),
    ]
    body = "".join(
        f'<tr><th scope="row">{fmt.esc(aspect)}</th><td>{old}</td><td>{new}</td></tr>\n'
        for aspect, old, new in rows
    )
    return (
        '<h2 id="scoring">How each project scored candidates</h2>\n'
        '<table class="compare">\n'
        '<thead><tr><th scope="col">Aspect</th><th scope="col">The 2025 ML project</th>'
        '<th scope="col">The rk run</th></tr></thead>\n'
        "<tbody>\n" + body + "</tbody>\n</table>\n"
        "<p>Neither project isolated any of these differences, so none of them can be tied to "
        "a particular result.</p>"
    )


def _untested(rk):
    found_at = rk["champion"]["found_at_cycle"]
    return (
        '<h2 id="untested">What neither project tested</h2>\n'
        f"<p>{_cl('U2', 'Neither project kept its comparisons hidden from the search')}. The language model "
        "that steers the rk run sees held-out errors, and elites are picked on them, so the "
        "nearest independent check "
        f"is the {_cl('R4', 'out-of-sample suite')}. The 2025 search started from the tables it "
        "was said to rediscover.</p>\n"
        f"<p>{_cl('U3', 'Neither search measured whether large local minima exist')}. The "
        "2025 project's results stayed flat because of its clipped score, untrained generator "
        "and reseeded random fallback. The rk run's best held-out error "
        f"{_cl('R6', 'stopped improving after search cycle ' + fmt.count(found_at))} while "
        "other cells kept improving, which describes one search, not the space it "
        "searched.</p>"
    )


def build(data):
    rk = data["rk"]
    novel = data["novel"]
    sources = data["sources"]
    parts = [
        "<h1>Two searches for better Runge-Kutta coefficients</h1>",
        _lead(rk),
        _dated(sources),
        _terms(rk),
        _projects(rk, novel, sources),
        _results(data),
        _scoring(rk, novel),
        _untested(rk),
    ]
    return "\n".join(parts) + "\n"
