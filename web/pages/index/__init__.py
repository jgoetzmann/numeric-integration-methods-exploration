"""The Story page (index.html): both projects on one page, with the headline claims.

Every number is read from data/*.json and rendered through web.fmt. Every result
statement links to its claim in claims.html the first time it appears.
"""

from web import fmt

SLUG = "index.html"
TITLE = "Story"
DESCRIPTION = (
    "Two searches for better Runge-Kutta coefficients: what each one found, "
    "and where established methods still lead."
)

FINDINGS_URL = "https://jgoetzmann.github.io/rk-findings/"

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


def _ref(cid):
    c = fmt.esc(cid)
    return f'<a href="claims.html#{c}">{c}</a>'


def _claim(cid):
    return "claim " + _ref(cid)


def _claims(*ids):
    refs = [_ref(c) for c in ids]
    if len(refs) == 1:
        return "claim " + refs[0]
    return "claims " + ", ".join(refs[:-1]) + " and " + refs[-1]


def _code(s):
    return "<code>" + fmt.esc(s) + "</code>"


def _cell(rk, basis, weighting):
    for c in rk["counterfactual"]["cells"]:
        if c["basis"] == basis and c["weighting"] == weighting:
            return c


def _lead(rk):
    champ = rk["champion"]
    budget = fmt.count(rk["setup"]["budget_cycles"])
    n_classical = _word(len(rk["frontier"]["classical"]))
    return (
        '<p class="lead">Both projects asked whether a search can find Runge-Kutta '
        "coefficients that do better than the textbook ones. In float64, established "
        f"methods were more accurate in both ({_claim('U1')}). Inside Q15 fixed point with "
        f"floor rounding, at a {budget}-cycle budget on the analytic cost model, the rk run "
        f"found a {_word(champ['stages'])}-stage method with {fmt.ratio(champ['lead'])} lower "
        f"held-out error than the best of {n_classical} classical methods "
        f"({_claim('R1')}).</p>\n"
        "<p>The cost model and the weighting of the held-out problems move that lead too, so "
        "this site does not credit the arithmetic alone.</p>"
    )


def _terms(rk):
    budget = fmt.count(rk["setup"]["budget_cycles"])
    dyadic = rk["champion"]["tableau"]["A"][1][0]
    n_heldout = _word(len(rk["setup"]["heldout_problems"])).capitalize()
    items = [
        ("Q15",
         "A sixteen-bit integer standing for a fraction between minus one and one. A "
         "Cortex-M0+ has no floating-point unit."),
        ("Floor rounding",
         "Each Q15 multiply shifts right by fifteen bits, rounding toward minus infinity, so "
         "every product errs the same way."),
        ("Dyadic coefficient",
         f"A fraction such as {_code(dyadic)} with a power-of-two denominator, applied by "
         "shifts and adds."),
        ("Cycle budget",
         f"Every method gets {budget} modeled clock cycles per problem, so a cheaper step "
         "buys more steps."),
        ("Search cycle",
         "One round of the rk run, from directive to archive."),
        ("Analytic and traced cost",
         "The analytic model prices coefficient arithmetic only. The traced count prices the "
         "compiled step, except the derivative routine's body."),
        ("Held-out problems",
         f"{n_heldout} problems that elites are picked on but the optimizer never reads: a "
         "selection set, not a test set."),
        ("Epoch",
         "A stretch of the rk run under one set of pinned scoring files."),
        ("The language model",
         "It proposes each search cycle's direction. Code scores the candidates."),
    ]
    body = "\n".join(f"<dt>{fmt.esc(t)}</dt>\n<dd>{d}</dd>" for t, d in items)
    return '<h2 id="terms">Terms</h2>\n<dl class="terms">\n' + body + "\n</dl>"


def _projects(rk, novel):
    e1 = rk["epochs"]["epoch1"]
    e2 = rk["epochs"]["epoch2"]
    down = e2["down_days"]
    repo = novel["repo"]
    return (
        '<h2 id="projects">The two projects</h2>\n'
        '<div class="cards projects">\n'
        '<article class="card project-card">\n'
        "<h3>The rk run</h3>\n"
        f'<p class="card-dates">{fmt.day(e1["started"])} onward</p>\n'
        "<p>An autonomous search, run in a container, for coefficients that do well in Q15 "
        "on a modeled Cortex-M0+. A language model steers it through a JSON directive that "
        f"can only narrow the search ({_claim('R13')}). Epoch 1 ran until "
        f"{fmt.day(e1['stopped'])}: {fmt.count(e1['cycles_run'])} search cycles and "
        f"{fmt.count(e1['records'])} scored records. No person chose candidates or scores, "
        f"though the runner started {fmt.count(e1['events']['runner_started'])} times as "
        f"people deployed changes to unpinned code ({_claim('R12')}). It was frozen on "
        f"{fmt.day(e1['frozen_at'])}. Epoch 2 started on "
        f"{fmt.day(e2['started'])} under a corrected cost model, stopped late that day, and "
        f"nothing restarted it until {fmt.day(down['to'])}.</p>\n"
        '<p><a href="rk.html">Read about the rk run</a></p>\n'
        "</article>\n"
        '<article class="card project-card">\n'
        "<h3>The 2025 ML project</h3>\n"
        f'<p class="card-dates">Active {fmt.day(repo["active_from"])} to '
        f'{fmt.day(repo["active_to"])}</p>\n'
        "<p><code>Novel-Numerical-Integration-Methods</code> tried to generate new explicit "
        "Runge-Kutta tables with a neural generator, a surrogate model and evolutionary "
        "search, in float64. Its evaluation harness runs end to end for explicit tables "
        f"({_claim('N9')}).</p>\n"
        '<p><a href="novel.html">Read about the 2025 ML project</a></p>\n'
        "</article>\n"
        "</div>\n"
        "<p>The same author built both and audited the 2025 project in September 2026, after "
        "the rk run began, so the table below compares two designs rather than one correcting "
        "the other.</p>"
    )


def _scoring(rk, novel):
    log = novel["metrics_log"]
    epochs = len(log["per_epoch"])
    clip = fmt.sig(log["composite_score_distinct_values"][0])
    seed = novel["audit_counts"]["random_generator_seed"]
    bench = novel["benchmark"]
    eng = rk["engineering"]
    n_heldout = _word(len(rk["setup"]["heldout_problems"])).capitalize()
    n_oos = _word(len(rk["validation"]["problems"]))
    rows = [
        (
            "What a candidate is scored on",
            f"A composite clipped at {clip}. All {fmt.count(log['rows'])} rows of the one "
            f"training log ({fmt.count(epochs)} epochs of "
            f"{fmt.count(log['rows'] // epochs)} candidates) score {clip} "
            f"({_claim('N2')}).",
            "Search-set error for the optimizer and held-out error for choosing elites, both "
            "in Q15 at the cycle budget.",
        ),
        (
            "Order conditions",
            f"None enforced. Its order-4 test labels RK4 as order 3 ({_claim('N10')}).",
            "Exact rational order conditions, checked before a candidate is scored.",
        ),
        (
            "Where the search starts",
            "RK4 and Dormand-Prince in the starting populations, and a random generator "
            f"reseeded to {fmt.count(seed)} for empty slots ({_claim('N4')}).",
            "An exhaustive lattice of dyadic coefficients, then CMA-ES over the stage matrix.",
        ),
        (
            "Guarding the scorer",
            f"No automated test suite ({_claim('N11')}).",
            f"A read-only harness, a pinned sha256 and {fmt.count(eng['golden_gate_cases'])} "
            f"golden and canary cases before any cycle ({_claim('R11')}).",
        ),
        (
            "Problems outside the search",
            f"A final benchmark on {fmt.count(bench['odes'])} generated ODEs "
            f"({_claim('N1')}).",
            f"{n_heldout} held-out problems, then {n_oos} out-of-sample ones "
            f"({_claim('R4')}).",
        ),
        (
            "What gets published",
            "Every benchmark entry, the weakest included.",
            f"Negative results too: a mixed premise test ({_claim('R9')}) and the float64 gap "
            f"({_claim('R5')}).",
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
        "<p>Neither project isolated any of these differences, so this site does not say "
        "which one produced which result.</p>"
    )


def _bottom_line(rk, novel):
    champ = rk["champion"]
    traced = _cell(rk, "traced_whole_step", "magnitude")
    bench = novel["benchmark"]
    return (
        '<h2 id="bottom-line">Bottom line</h2>\n'
        "<p>Inside Q15 with floor rounding at a fixed cycle budget, the rk run found methods "
        "that lead the classical ones on the cost model it was scored on, the best by "
        f"{fmt.ratio(champ['lead'])}. That lead is {fmt.ratio(traced['ratio'])} on the "
        "traced whole-step basis and shifts with the weighting of the held-out problems. It "
        "comes from the epoch-1 cost model, which a later trace found had <code>rk4</code> "
        f"and <code>rk38</code> in the wrong order ({_claim('R7')}); epoch 2 has not "
        "re-measured it. In float64, <code>rk4</code> is far more accurate. The 2025 search "
        "never moved its saved tables off their seeds, but its harness ran a "
        f"{fmt.count(bench['methods'])}-entry benchmark over {fmt.count(bench['odes'])} "
        "ODEs.</p>"
    )


def _card_texts(data):
    """Heading and body HTML for each headline claim: the claim and its key conditions."""
    rk = data["rk"]
    novel = data["novel"]
    champ = rk["champion"]
    budget = fmt.count(rk["setup"]["budget_cycles"])
    cells = rk["counterfactual"]["cells"]
    kept = sum(1 for c in cells if c["champion_still_leads"])
    traced_mag = _cell(rk, "traced_whole_step", "magnitude")
    rtn = rk["floor_vs_round"]["heldout_rms"]["round_to_nearest"]
    rtn_best = min(sorted(rtn), key=lambda m: rtn[m])
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
    e1 = rk["epochs"]["epoch1"]
    e2 = rk["epochs"]["epoch2"]
    eng = rk["engineering"]
    bench = novel["benchmark"]
    rows = {r["id"]: r for r in bench["rows"]}
    dp_err = rows["baseline_rk45_dormand_prince"]["mean_max_error"]
    rk4_err = rows["baseline_rk4"]["mean_max_error"]
    clip = fmt.sig(novel["metrics_log"]["composite_score_distinct_values"][0])
    by_id = {c["id"]: c for c in data["claims"]["claims"]}

    def rejected(cid):
        return f"<p><q>{fmt.esc(by_id[cid]['claim'])}</q></p>\n"

    return {
        "R1": (
            "The Q15 lead",
            f"<p>In Q15 with floor rounding at the {budget}-cycle budget, on the analytic cost "
            f"model with magnitude weighting, {_code(champ['hash'])} has "
            f"{fmt.ratio(champ['lead'])} lower held-out error than "
            f"{_code(champ['best_classical'])}. The lead survives dropping any one problem in "
            f"{_word(kept)} of {_word(len(cells))} cost-basis and weighting cells. Rounding to "
            f"nearest, {_code(rtn_best)} alone reaches {fmt.sig(rtn[rtn_best])}, below the "
            f"champion's {fmt.sig(champ['heldout_error'])} under floor rounding.</p>",
        ),
        "R2": (
            "Every discovered cell elite ahead",
            f"<p>Under the same conditions and selection bias, all {fmt.count(ahead_of_all)} "
            "discovered methods "
            f"that hold one of the {fmt.count(frontier['cells_total'])} occupied archive cells "
            "have lower held-out error than every classical method, whatever its cost.</p>",
        ),
        "R4": (
            "Out-of-sample problems",
            f"<p>On {_word(len(val['problems']))} problems chosen after the search began, the "
            f"best of {_word(val['discovered_methods_run'])} discovered methods had lower Q15 "
            f"error than the best of {_word(len(val['classical_methods_run']))} classical ones "
            f"on {fmt.count(val['practical_won_by_discovered'])} of "
            f"{fmt.count(val['practical_total'])} non-stiff problems, the champion alone on "
            f"{fmt.count(champ_alone)}. On the stiff {_code(over['problem'])}, every "
            "discovered method overflowed, as did <code>rk4</code> and <code>rk38</code>.</p>",
        ),
        "R5": (
            "In float64, rk4 is far more accurate",
            "<p>At the step count the budget gives each method, the champion's float64 error "
            f"was {fmt.ratio(gap['champion_over_rk4_min'])} to "
            f"{fmt.ratio(gap['champion_over_rk4_max'])} that of <code>rk4</code> on the "
            f"{fmt.count(gap['problems'])} validation problems where both finish: a "
            "second-order method against a fourth-order one.</p>",
        ),
        "R7": (
            "An audit caught the cost model's error",
            "<p>A host-side trace of the compiled step, on an instruction-accurate emulator, "
            f"matched the Python evaluator in {fmt.esc(eng['trace_crosscheck'])} cases and "
            "found <code>rk4</code> and <code>rk38</code> in the wrong order in the epoch-1 "
            "cost model.</p>",
        ),
        "R11": (
            "A scorer the search cannot edit",
            "<p>The harness is mounted read-only, and a sha256 over the pinned files "
            f"({fmt.count(e1['verifier_files'])} in epoch 1, {fmt.count(e2['verifier_files'])} "
            "since epoch 2) is checked at every start and stored in every record.</p>",
        ),
        "N1": (
            "The 2025 benchmark ran",
            f"<p>In float64, over {fmt.count(bench['methods'])} entries and "
            f"{fmt.count(bench['odes'])} ODEs, Dormand-Prince had the lowest mean error "
            f"({fmt.sig(dp_err)}) and RK4 the next ({fmt.sig(rk4_err)}). The other entries "
            "were copies of those two, random tables or truncated methods, and the reference "
            "solver was itself Dormand-Prince.</p>",
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
            "surrogate "
            "model that nothing in training reads.</p>",
        ),
        "U1": (
            "In float64, established methods led in both projects",
            "<p>In the rk run this is float64 <code>rk4</code> against the champion. The 2025 "
            "half is weak evidence: there they led against copies of themselves, random tables "
            "and truncated methods.</p>",
        ),
    }


def _card(claim, heading, body):
    cid = fmt.esc(claim["id"])
    verdict = claim["verdict"]
    return (
        '<article class="card claim-card">\n'
        f"<h3>{fmt.esc(heading)}</h3>\n"
        f"{body}\n"
        f'<p class="card-foot"><span class="verdict verdict-{fmt.esc(verdict)}">'
        f"{fmt.esc(VERDICT_LABELS.get(verdict, verdict))}</span> "
        f'<a href="claims.html#{cid}">Claim {cid}</a></p>\n'
        "</article>"
    )


def _highlights(data):
    headline = [c for c in data["claims"]["claims"] if c.get("headline") is True]
    texts = _card_texts(data)
    cards = []
    for claim in headline:
        heading, body = texts[claim["id"]]
        cards.append(_card(claim, heading, body))
    return (
        '<h2 id="highlights">Headline claims</h2>\n'
        '<div class="cards claims">\n' + "\n".join(cards) + "\n</div>"
    )


def _not_claimed(data):
    by_id = {c["id"]: c for c in data["claims"]["claims"]}
    found_at = data["rk"]["champion"]["found_at_cycle"]
    return (
        '<h2 id="not-claimed">Two claims this site does not make</h2>\n'
        f"<p><q>{fmt.esc(by_id['U2']['claim'])}</q> The model that directs the rk run sees "
        "held-out errors, so the nearest thing to an independent check is the out-of-sample "
        f"suite ({_claims('U2', 'R4')}).</p>\n"
        f"<p><q>{fmt.esc(by_id['U3']['claim'])}</q> Neither project measured that. The rk "
        f"run's best held-out error stopped improving after cycle {fmt.count(found_at)}, "
        "which describes one search "
        f"({_claims('U3', 'R6')}).</p>"
    )


def _next(sources):
    return (
        '<h2 id="next">Where to go next</h2>\n'
        '<ul class="next">\n'
        '<li><a href="rk.html">The rk run</a>: the results and their limits.</li>\n'
        '<li><a href="novel.html">The 2025 ML project</a>: what it built and what the audit '
        "found.</li>\n"
        '<li><a href="architecture.html">Architecture</a>: how each system is built.</li>\n'
        '<li><a href="epochs.html">Epochs and research</a>: the timeline.</li>\n'
        '<li><a href="claims.html">Claims audit</a>: every claim, verdict and limit.</li>\n'
        f'<li><a href="repos.html">Repositories</a>: the {_word(len(sources["repos"]))} '
        "repositories and how to rebuild this site.</li>\n"
        "</ul>"
    )


def _snapshot(sources):
    return (
        '<h2 id="snapshot">About this snapshot</h2>\n'
        f"<p>Every number here was read from the {_word(len(sources['repos']))} repositories "
        f"in the footer as of {fmt.day(sources['snapshot_date'])}. The rk run kept going "
        "after that date. The findings site it rebuilds every cycle has current numbers: "
        f'<a href="{FINDINGS_URL}">jgoetzmann.github.io/rk-findings</a>.</p>'
    )


def build(data):
    rk = data["rk"]
    novel = data["novel"]
    sources = data["sources"]
    parts = [
        "<h1>Two searches for better Runge-Kutta coefficients</h1>",
        _lead(rk),
        _terms(rk),
        _projects(rk, novel),
        _scoring(rk, novel),
        _bottom_line(rk, novel),
        _highlights(data),
        _not_claimed(data),
        _next(sources),
        _snapshot(sources),
    ]
    return "\n".join(parts) + "\n"
