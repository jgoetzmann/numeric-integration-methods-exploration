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

PROJECT_LABELS = {
    "rk": "The rk run",
    "novel": "The 2025 ML project",
    "both": "Both projects",
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


def _claims(a, b):
    return "claims " + _ref(a) + " and " + _ref(b)


def _code(s):
    return "<code>" + fmt.esc(s) + "</code>"


def _cell(rk, basis, weighting):
    for c in rk["counterfactual"]["cells"]:
        if c["basis"] == basis and c["weighting"] == weighting:
            return c


def _lead(rk):
    champ = rk["champion"]
    budget = fmt.count(rk["setup"]["budget_cycles"])
    traced = _cell(rk, "traced_whole_step", "magnitude")
    return (
        '<p class="lead">Both projects asked whether a search can find Runge-Kutta '
        "coefficients that do better than the textbook ones. The answer depends on "
        f"the arithmetic ({_claim('U1')}).</p>\n"
        "<p>In float64, established methods such as <code>rk4</code> and Dormand-Prince "
        "came out on top in both projects. Inside Q15 fixed point with floor rounding, at a "
        f"{budget}-cycle budget and on the analytic cost model, the rk run found a "
        f"{_word(champ['stages'])}-stage dyadic method with {fmt.ratio(champ['lead'])} lower "
        f"held-out error than the best classical method ({_claim('R1')}). On the traced "
        f"whole-step cost basis that lead shrinks to {fmt.ratio(traced['ratio'])}.</p>\n"
        "<p>The 2025 ML project worked in float64. An audit in September 2026 found that "
        "its evolutionary search started from RK4 and Dormand-Prince themselves, that its "
        f"generator was never trained ({_claims('N2', 'N4')}), and that its score could not "
        f"tell RK4 from a random table ({_claim('N3')}). Its benchmark did run, and its "
        f"evaluation harness works ({_claims('N1', 'N9')}).</p>"
    )


def _projects(rk, novel):
    e1 = rk["epochs"]["epoch1"]
    e2 = rk["epochs"]["epoch2"]
    champ = rk["champion"]
    repo = novel["repo"]
    return (
        '<h2 id="projects">The two projects</h2>\n'
        '<div class="cards projects">\n'
        '<article class="card project-card">\n'
        "<h3>The rk run</h3>\n"
        f'<p class="card-dates">{fmt.day(e1["started"])} onward</p>\n'
        "<p>It searches unattended, inside a container, for Runge-Kutta coefficients that do "
        "best in Q15 fixed point with floor rounding on a modeled Cortex-M0+. Epoch 1 ran "
        f"from {fmt.day(e1['started'])} to {fmt.day(e1['stopped'])} and wrote "
        f"{fmt.count(e1['records'])} scored records over {fmt.count(e1['cycles_run'])} "
        f"cycles ({_claim('R12')}). The champion appeared at cycle "
        f"{fmt.count(champ['found_at_cycle'])} and nothing later in epoch 1 improved on it "
        f"({_claim('R6')}). Epoch 2 started on {fmt.day(e2['started'])} under a corrected "
        "cost model.</p>\n"
        '<p><a href="rk.html">Read about the rk run</a></p>\n'
        "</article>\n"
        '<article class="card project-card">\n'
        "<h3>The 2025 ML project</h3>\n"
        f'<p class="card-dates">Active {fmt.day(repo["active_from"])} to '
        f'{fmt.day(repo["active_to"])}</p>\n'
        "<p><code>Novel-Numerical-Integration-Methods</code> set out to generate new explicit "
        "Runge-Kutta tables with a neural generator, a surrogate model and evolutionary "
        "search, scored on generated ODEs. It built a working evaluation harness of "
        f"{fmt.count(repo['src_python_lines'])} lines of Python across "
        f"{fmt.count(repo['src_python_files'])} files and set up "
        f"{fmt.count(repo['trial_folders'])} trial configurations ({_claim('N9')}).</p>\n"
        '<p><a href="novel.html">Read about the 2025 ML project</a></p>\n'
        "</article>\n"
        "</div>"
    )


def _card_texts(data):
    """Heading and body HTML for each headline claim, in plain words with conditions."""
    rk = data["rk"]
    novel = data["novel"]
    champ = rk["champion"]
    budget = fmt.count(rk["setup"]["budget_cycles"])
    traced_mag = _cell(rk, "traced_whole_step", "magnitude")
    traced_med = _cell(rk, "traced_whole_step", "equal_median_anchor")
    frontier = rk["frontier"]
    val = rk["validation"]
    nonstiff = [p for p in val["problems"] if not p["stiff"]]
    champ_alone = sum(
        1 for p in nonstiff
        if p["champion_q15"] is not None and p["champion_q15"] < p["best_classical_q15"]
    )
    over = next(p for p in val["problems"] if p["champion_overflowed"])
    lib = rk["libraries"]
    compared = lib["fixed_step_cells_compared"]
    rk4_lower = compared - lib["fixed_step_cells_where_q15_error_lower"]
    gap = rk["float64_gap"]
    eng = rk["engineering"]
    bench = novel["benchmark"]
    rows = {r["id"]: r for r in bench["rows"]}
    dp_err = rows["baseline_rk45_dormand_prince"]["mean_max_error"]
    rk4_err = rows["baseline_rk4"]["mean_max_error"]
    log = novel["metrics_log"]
    clip = log["composite_score_distinct_values"][0]
    seed = novel["audit_counts"]["random_generator_seed"]
    by_id = {c["id"]: c for c in data["claims"]["claims"]}

    def rejected(cid):
        return f"<p>The claim: <q>{fmt.esc(by_id[cid]['claim'])}</q></p>\n"

    return {
        "R1": (
            "A lead inside Q15 with floor rounding",
            f"<p>Inside Q15 fixed point with floor rounding, at a {budget}-cycle budget, the "
            f"champion {_code(champ['hash'])} has {fmt.ratio(champ['lead'])} lower held-out "
            f"error than {_code(champ['best_classical'])}, the best of "
            f"{_word(len(frontier['classical']))} classical methods, on the analytic cost "
            "model with magnitude weighting.</p>\n"
            "<p>On the traced whole-step cost basis the lead falls to "
            f"{fmt.ratio(traced_mag['ratio'])}. With median-anchor weighting on that basis the "
            f"ratio is {fmt.ratio(traced_med['ratio'])} and <code>midpoint</code> leads. Elites were "
            "picked on held-out error, so these figures carry selection bias.</p>",
        ),
        "R2": (
            "Ahead in every filled cell",
            f"<p>Inside Q15 with floor rounding at the {budget}-cycle budget, on the analytic "
            "cost model, the discovered method has lower held-out error than every classical "
            "method that costs the same or less in "
            f"{fmt.count(frontier['cells_where_discovered_leads_every_cheaper_or_equal_classical'])} "
            f"of the {fmt.count(frontier['cells_held_by_discovered'])} grid cells the search "
            "filled.</p>",
        ),
        "R4": (
            "Out-of-sample problems",
            f"<p>People chose these {_word(len(val['problems']))} problems after the search "
            "began, and no optimizer or model saw them. In Q15 with floor rounding, the best "
            "discovered method had lower error than the best classical method on "
            f"{fmt.count(val['practical_won_by_discovered'])} of the "
            f"{fmt.count(val['practical_total'])} non-stiff problems. The champion alone had "
            f"the lower error on {fmt.count(champ_alone)}. On the stiff "
            f"{_code(over['problem'])} problem every discovered method overflowed while "
            f"{_code(over['best_classical'])} finished.</p>",
        ),
        "R5": (
            "In float64, established methods lead",
            "<p>At the same step counts, float64 <code>rk4</code> had lower error than the Q15 "
            f"methods in {fmt.count(rk4_lower)} of {fmt.count(compared)} cells, and in float64 "
            f"the champion was {fmt.ratio(gap['champion_over_rk4_min'])} to "
            f"{fmt.ratio(gap['champion_over_rk4_max'])} less accurate than <code>rk4</code>. "
            "At tolerances matched to one Q15 step, adaptive library solvers such as "
            "Dormand-Prince (SciPy RK45) were a median "
            f"{fmt.ratio(lib['median_ratio_q15_over_library_at_matched_tolerance'])} more "
            "accurate than the best Q15 result.</p>",
        ),
        "R7": (
            "The run caught its own cost-model error",
            "<p>Compiling the step and tracing it under an emulator matched the Python "
            f"evaluator bit for bit in {fmt.esc(eng['trace_crosscheck'])} cases and showed "
            "that the epoch-1 cost model put <code>rk4</code> and <code>rk38</code> in the "
            "wrong order. The run froze epoch 1 and started epoch 2 under a corrected cost "
            "model instead of rescoring the old archive. The emulator is "
            "instruction-accurate, not cycle-accurate, and nothing was measured on a "
            "physical chip.</p>",
        ),
        "R11": (
            "A scorer the search cannot edit",
            "<p>The harness is mounted read-only, a sha256 over "
            f"{fmt.count(eng['verifier_files'])} files is checked at every start and stored "
            f"in every record, and {fmt.count(eng['golden_gate_cases'])} golden and canary "
            "cases must pass before any cycle runs. The suite collected "
            f"{fmt.count(eng['tests_collected'])} tests on "
            f"{fmt.day(eng['tests_collected_on'])}.</p>",
        ),
        "N1": (
            "The 2025 benchmark ran",
            f"<p>In float64, across {fmt.count(bench['methods'])} methods and "
            f"{fmt.count(bench['odes'])} generated ODEs ({fmt.count(bench['scorable_odes'])} "
            f"scorable), Dormand-Prince had the lowest mean error ({fmt.sig(dp_err)}) and "
            f"RK4 the next lowest ({fmt.sig(rk4_err)}). The error is a mean of per-ODE "
            "maxima that a few outlier ODEs dominate, and the other entries were copies of "
            "those two, random tables or truncated methods.</p>",
        ),
        "N2": (
            "The evolved tables were the seeds",
            rejected("N2")
            + "<p>The audit found both tables placed in the starting population. Every one "
            f"of the {fmt.count(log['rows'])} logged scores sits at the clip ceiling of "
            f"{fmt.sig(clip)}, so no candidate could replace the seed.</p>",
        ),
        "N4": (
            "No gradient step was taken",
            rejected("N4")
            + "<p>The audit found that the generator's optimizer was created and never "
            "stepped. A random generator that resets its seed to "
            f"{fmt.count(seed)} filled every empty slot, which is why trials 8 and 9 saved "
            "the same table.</p>",
        ),
        "U1": (
            "The arithmetic decides which methods lead",
            "<p>In float64, established methods such as <code>rk4</code> and Dormand-Prince "
            f"came out on top in both projects ({_claims('R5', 'N1')}). Inside Q15 with "
            "floor rounding at a fixed cycle budget, the searched method leads the classical "
            f"fixed-step methods ({_claim('R1')}), which is the one place the rk run set out "
            "to look.</p>",
        ),
    }


def _card(claim, heading, body):
    cid = fmt.esc(claim["id"])
    verdict = claim["verdict"]
    project = PROJECT_LABELS.get(claim["project"], claim["project"])
    return (
        '<article class="card claim-card">\n'
        f'<p class="card-tag">{fmt.esc(project)}</p>\n'
        f"<h3>{fmt.esc(heading)}</h3>\n"
        f"{body}\n"
        f'<p class="card-foot"><span class="verdict verdict-{fmt.esc(verdict)}">'
        f"{fmt.esc(VERDICT_LABELS.get(verdict, verdict))}</span> "
        f'<a href="claims.html#{cid}">Claim {cid} in the audit</a></p>\n'
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
        f"<p>The claims audit marks {_word(len(headline))} claims as headlines. Each card "
        "states one with its conditions and links to its verdict, limits and evidence.</p>\n"
        '<div class="cards claims">\n' + "\n".join(cards) + "\n</div>"
    )


def _scoring(rk, novel):
    budget = fmt.count(rk["setup"]["budget_cycles"])
    eng = rk["engineering"]
    log = novel["metrics_log"]
    clip = fmt.sig(log["composite_score_distinct_values"][0])
    bench = novel["benchmark"]
    audit = novel["audit_counts"]
    rows = [
        (
            "What a candidate is scored on",
            "A composite of accuracy, efficiency and stability terms, clipped at "
            f"{clip}. All {fmt.count(log['rows'])} logged scores sit at that ceiling.",
            f"Held-out RMS error in Q15 with floor rounding at a {budget}-cycle budget.",
        ),
        (
            "Order conditions",
            "No working order check. The only hard constraint was that the weights sum "
            "to one.",
            "Exact rational order conditions, checked by the verifier before a candidate "
            "is scored.",
        ),
        (
            "Where the search starts",
            "Evolution started from RK4 and Dormand-Prince. Empty generator slots were "
            "filled by one seeded random table.",
            "Early phases enumerate a small lattice in full; later phases run CMA-ES over "
            "dyadic coefficients.",
        ),
        (
            "Guarding the scorer",
            "No test suite.",
            f"A sha256 over {fmt.count(eng['verifier_files'])} files that is checked at every "
            f"start and stored in every record, plus {fmt.count(eng['golden_gate_cases'])} "
            "golden and canary cases before any cycle.",
        ),
        (
            "Problems outside the search",
            f"A final benchmark on {fmt.count(bench['odes'])} generated ODEs. Training sets "
            f"held {fmt.count(audit['training_set_odes'])} ODEs each.",
            f"{_word(len(rk['setup']['heldout_problems'])).capitalize()} held-out problems "
            "the optimizer does not read, though elites are picked on them, then "
            f"{_word(len(rk['validation']['problems']))} out-of-sample problems chosen after "
            "the search began.",
        ),
        (
            "What gets published",
            f"A {fmt.count(bench['methods'])}-row benchmark table that keeps every entry, "
            "the weakest included.",
            f"Negative results next to the positive ones: a mixed premise test "
            f"({_claim('R9')}), the stiff overflow, the float64 gap and every cell of the "
            "counterfactual grid.",
        ),
    ]
    body = "".join(
        f'<tr><th scope="row">{fmt.esc(aspect)}</th><td>{old}</td><td>{new}</td></tr>\n'
        for aspect, old, new in rows
    )
    return (
        '<h2 id="scoring">How each project scored candidates</h2>\n'
        "<p>The table sets out what each project did, one aspect per row.</p>\n"
        '<table class="compare">\n'
        '<thead><tr><th scope="col">Aspect</th><th scope="col">The 2025 ML project</th>'
        '<th scope="col">The rk run</th></tr></thead>\n'
        "<tbody>\n" + body + "</tbody>\n</table>\n"
        "<p>These are differences in method, stated as facts about each project. Neither "
        "project ran an experiment that isolates one of them, so this site does not say "
        "which difference produced which result.</p>"
    )


def _next(sources):
    return (
        '<h2 id="next">Where to go next</h2>\n'
        '<ul class="next">\n'
        '<li><a href="architecture.html">Architecture</a>: how each system is built, and '
        "where the audit found the 2025 pipeline broke.</li>\n"
        '<li><a href="epochs.html">Epochs and research</a>: the timeline of the rk run, why '
        "epoch 1 froze, and how the run tests its own premise.</li>\n"
        '<li><a href="claims.html">Claims audit</a>: every claim on this site with its '
        "verdict, limits and evidence.</li>\n"
        f'<li><a href="repos.html">Repositories</a>: the {_word(len(sources["repos"]))} '
        "repositories, their commits and how to rebuild this site.</li>\n"
        "</ul>"
    )


def _snapshot(sources):
    return (
        '<h2 id="snapshot">About this snapshot</h2>\n'
        f"<p>Every number on this site was read from the {_word(len(sources['repos']))} "
        "repositories listed in the footer, as of "
        f"{fmt.day(sources['snapshot_date'])}. The rk run was still running on that date, "
        "so its numbers here will age. For current numbers, see the findings site the run "
        f'rebuilds every cycle: <a href="{FINDINGS_URL}">jgoetzmann.github.io/rk-findings</a>.'
        "</p>"
    )


def build(data):
    rk = data["rk"]
    novel = data["novel"]
    sources = data["sources"]
    parts = [
        "<h1>Two searches for better Runge-Kutta coefficients</h1>",
        _lead(rk),
        _projects(rk, novel),
        _highlights(data),
        _scoring(rk, novel),
        _next(sources),
        _snapshot(sources),
    ]
    return "\n".join(parts) + "\n"
