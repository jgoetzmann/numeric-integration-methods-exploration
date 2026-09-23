"""novel.html: the 2025 ML project, what it built, and what the 2026 audit found."""
from web import fmt

from . import charts

SLUG = "novel.html"
TITLE = "The 2025 ML project"
DESCRIPTION = (
    "What the 2025 ML project built, what its benchmark measured, and which of its "
    "conclusions a September 2026 audit did not support."
)

VERDICT_LABELS = {
    "supported": "Supported",
    "supported-with-limits": "Supported with limits",
    "not-supported": "Not supported",
    "artifact": "Artifact",
}

AUDIT_ORDER = ["N2", "N3", "N4", "N5", "N6", "N7", "N8"]

AUDIT_HEADINGS = {
    "N2": "Evolution kept the tables it was seeded with",
    "N3": "The score could not tell RK4 from a random table",
    "N4": "No gradient step was taken",
    "N5": "The Gauss-Legendre 3 error measures a stepper bug",
    "N6": "The success rate belongs to the ODE set",
    "N7": "Trial 16 is a random draw",
    "N8": "Training used small sets and no GPU",
}

_WORDS = {
    0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
    7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven", 12: "twelve",
}


def _word(n):
    return _WORDS.get(n, fmt.count(n))


def _join(items):
    items = list(items)
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def _trials(nums):
    nums = sorted(nums)
    word = "trial" if len(nums) == 1 else "trials"
    return f"{word} {_join(fmt.count(t) for t in nums)}"


def _claim(cid, text=None):
    label = text if text is not None else f"claim {cid}"
    return f'<a href="claims.html#{fmt.esc(cid)}">{fmt.esc(label)}</a>'


def _h2(anchor, heading):
    return f'<h2 id="{anchor}">{fmt.esc(heading)}</h2>'


def _bench_notes(novel):
    trials = novel["trials"]
    eq_rk4 = set(trials["equal_to_rk4"])
    eq_dp = set(trials["equal_to_dormand_prince"])
    by_trial = {row["trial"]: row for row in trials["rows"]}
    notes = {}
    for r in novel["benchmark"]["rows"]:
        if r["mean_max_error"] >= charts.OFF_SCALE:
            notes[r["id"]] = f"artifact of a stepper bug, drawn off scale ({_claim('N5')})"
            continue
        if r["label"].startswith("Gauss-Legendre"):
            notes[r["id"]] = f"ran as a truncated explicit method ({_claim('N5')})"
            continue
        if r["baseline"]:
            continue
        t = int(r["id"])
        if t in eq_rk4:
            notes[r["id"]] = f"same table as RK4 ({_claim('N2')})"
        elif t in eq_dp:
            notes[r["id"]] = f"same table as Dormand-Prince ({_claim('N2')})"
        elif t == 16:
            notes[r["id"]] = f"a single random draw ({_claim('N7')})"
        elif by_trial.get(t, {}).get("identical_to_trials"):
            same = _trials(by_trial[t]["identical_to_trials"])
            notes[r["id"]] = f"same table as {same} ({_claim('N4')})"
    return notes


def _trials_table(novel):
    trials = novel["trials"]
    eq_rk4 = set(trials["equal_to_rk4"])
    eq_dp = set(trials["equal_to_dormand_prince"])
    rows = []
    for row in trials["rows"]:
        t = row["trial"]
        if "stages" not in row:
            rows.append(
                f"<tr><td>{fmt.count(t)}</td>"
                '<td colspan="4">no table saved; not in the final evaluation</td></tr>'
            )
            continue
        d_rk4 = row.get("max_abs_diff_from_rk4")
        d_dp = row.get("max_abs_diff_from_dormand_prince")
        same = []
        if t in eq_rk4:
            same.append("RK4")
        if t in eq_dp:
            same.append("Dormand-Prince")
        if row.get("identical_to_trials"):
            same.append(_trials(row["identical_to_trials"]))
        rows.append(
            f"<tr><td>{fmt.count(t)}</td><td>{fmt.count(row['stages'])}</td>"
            f"<td>{'n/a' if d_rk4 is None else fmt.sig(d_rk4)}</td>"
            f"<td>{'n/a' if d_dp is None else fmt.sig(d_dp)}</td>"
            f"<td>{'; '.join(same) if same else 'none'}</td></tr>"
        )
    return (
        '<table class="trials" style="display:block;max-width:100%;overflow-x:auto">'
        "<caption>What each trial saved: the largest absolute coefficient difference "
        "from the textbook table with the same stage count, n/a where the project has "
        "no such table</caption>"
        '<thead><tr><th scope="col">Trial</th><th scope="col">Stages</th>'
        '<th scope="col">Largest difference from RK4</th>'
        '<th scope="col">Largest difference from Dormand-Prince</th>'
        '<th scope="col">Same table as</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _audit_extra(cid, novel):
    bench = novel["benchmark"]
    trials = novel["trials"]
    audit = novel["audit_counts"]
    log = novel["metrics_log"]
    t16 = novel["trial16"]
    by_trial = {row["trial"]: row for row in trials["rows"]}
    eq_rk4 = trials["equal_to_rk4"]
    eq_dp = trials["equal_to_dormand_prince"]

    if cid == "N2":
        d_rk4 = max(by_trial[t]["max_abs_diff_from_rk4"] for t in eq_rk4)
        d_dp = max(by_trial[t]["max_abs_diff_from_dormand_prince"] for t in eq_dp)
        return (
            f"<p>The saved tables bear this out. The largest coefficient difference from RK4 "
            f"is {fmt.sig(d_rk4)} for {_trials(eq_rk4)}, and the largest difference from "
            f"Dormand-Prince is {fmt.sig(d_dp)} for {_trials(eq_dp)}. The comparison with the "
            f"textbook tables was not blind, and neither project ran a blind test "
            f"({_claim('U2')}).</p>"
        )
    if cid == "N3":
        return (
            '<p>The <a href="#training-log">training log</a> below shows the same thing '
            "from the other side: every logged candidate has the same composite score.</p>"
        )
    if cid == "N4":
        return (
            "<p>The table below lists what each trial saved. Every row compares the saved "
            "table with the textbook table of the same stage count.</p>"
            + _trials_table(novel)
        )
    if cid == "N5":
        off = [r for r in bench["rows"] if r["mean_max_error"] >= charts.OFF_SCALE]
        if not off:
            return ""
        return (
            f'<p>The <a href="#novel-benchmark">benchmark chart</a> marks this row off '
            f"scale and does not plot {fmt.sig(off[0]['mean_max_error'])} as a result.</p>"
        )
    if cid == "N6":
        rate = bench["success_rate_distinct_values"][0]
        return (
            f"<p>Every benchmark row records the same success rate, {fmt.pct(rate, 2)}: "
            f"{fmt.count(bench['scorable_odes'])} of {fmt.count(bench['odes'])} ODEs.</p>"
        )
    if cid == "N7":
        hist = t16["history"]
        top = max(hist, key=lambda h: (h["best_score"], -h["epoch"]))
        clip = log["composite_score_distinct_values"][0]
        return (
            f"<p>Trial {fmt.count(16)} used its own training loop, and its score is the only "
            f"one in the project that is not clipped at {fmt.sig(clip)}. The highest best score "
            f"in its {fmt.count(len(hist))}-epoch history, {fmt.sig(top['best_score'])}, is at "
            f"epoch {fmt.count(top['epoch'])}, and the saved table is that epoch's random draw. "
            f"The trial ran for {fmt.sig(t16['training_time_s'])} seconds.</p>"
        )
    if cid == "N8":
        return (
            f"<p>Each training set held {fmt.count(audit['training_set_odes'])} ODEs drawn "
            f"from {fmt.count(audit['training_ode_family_count'])} families. The reference "
            f"solver handles {fmt.count(audit['reference_solver_family_count'])} of those "
            f"families, so ODEs from the others could not be scored during training.</p>"
        )
    return ""


def _audit_item(cid, claim, novel):
    verdict = claim["verdict"]
    label = VERDICT_LABELS.get(verdict, verdict)
    anchor = f"audit-{cid.lower()}"
    out = [
        '<section class="audit-item">',
        f'<h3 id="{anchor}">{fmt.esc(AUDIT_HEADINGS.get(cid, cid))}</h3>',
        f"<p>{_claim(cid, 'Claim ' + cid)}: "
        f'<span class="verdict verdict-{fmt.esc(verdict)}">{fmt.esc(label)}</span>. '
        f"<q>{fmt.esc(claim['claim'])}</q></p>",
    ]
    if claim.get("original_wording"):
        out.append(
            "<p>The project's own wording:</p>"
            f"<blockquote><p>{fmt.esc(claim['original_wording'])}</p></blockquote>"
        )
    if claim.get("correction"):
        out.append(f"<p>{fmt.esc(claim['correction'])}</p>")
    elif claim.get("limits"):
        out.append(f"<p>{fmt.esc(claim['limits'])}</p>")
    out.append(_audit_extra(cid, novel))
    out.append("</section>")
    return "".join(out)


def build(data):
    novel = data["novel"]
    sources = data["sources"]
    claims = {c["id"]: c for c in data["claims"]["claims"]}
    repo = novel["repo"]
    bench = novel["benchmark"]
    audit = novel["audit_counts"]
    log = novel["metrics_log"]
    trials = novel["trials"]
    rows = bench["rows"]
    by_id = {r["id"]: r for r in rows}
    rk4 = by_id["baseline_rk4"]
    dp = by_id["baseline_rk45_dormand_prince"]
    eq_rk4 = trials["equal_to_rk4"]
    eq_dp = trials["equal_to_dormand_prince"]
    repo_name = repo["source"]["repo"]
    repo_url = repo["source"]["url"]
    repo_commit = repo["source"]["commit"]
    for r in sources["repos"]:
        if r["name"] == repo_name:
            repo_url = r["url"]
            repo_commit = r["commit"]
    n_base = sum(1 for r in rows if r["baseline"])
    n_trial = len(rows) - n_base
    per_epoch = log["per_epoch"]
    per_epoch_candidates = log["rows"] // len(per_epoch)
    clip = log["composite_score_distinct_values"][0]
    best = min(per_epoch, key=lambda p: (p["min_max_error"], p["epoch"]))
    first_epoch = min(p["epoch"] for p in per_epoch)
    rk4_rows = [by_id["baseline_rk4"]] + [by_id[str(t)] for t in eq_rk4 if str(t) in by_id]
    rt_lo = min(r["runtime_s"] for r in rk4_rows)
    rt_hi = max(r["runtime_s"] for r in rk4_rows)
    fastest = min(rows, key=lambda r: r["runtime_s"])

    parts = []
    parts.append(f"<h1>{fmt.esc(TITLE)}</h1>")
    parts.append(
        f'<p class="lead"><code>{fmt.esc(repo_name)}</code> was a 2025 attempt to find new '
        f"explicit Runge-Kutta tables with machine learning: a neural generator, a surrogate "
        f"model and an evolutionary search, scored on generated ODEs. It built a working "
        f"evaluation harness and ran a real benchmark of {fmt.count(bench['methods'])} methods "
        f"on {fmt.count(bench['odes'])} ODEs. Its main conclusions did not hold up when its "
        f"code and committed results were audited in September 2026. This page covers both "
        f"parts.</p>"
    )

    # What it set out to do
    parts.append("<section>")
    parts.append(_h2("aims", "What it set out to do"))
    parts.append(
        f"<p>The plan was to generate Butcher tables for explicit Runge-Kutta methods with a "
        f"neural network, refine them with a surrogate model and an evolutionary search, and "
        f"score them on generated ordinary differential equations against {_word(n_base)} "
        f"textbook baselines: RK4, Dormand-Prince and Gauss-Legendre {fmt.count(2)} and "
        f"{fmt.count(3)}. Trials weighted accuracy, efficiency and stability differently, and "
        f"some added a reward for tables unlike RK4.</p>"
    )
    parts.append(
        f"<p>The repository has {fmt.count(repo['commits'])} commits. The earliest is dated "
        f"{fmt.day(repo['first_commit'])}, the working period ran from "
        f"{fmt.day(repo['active_from'])} to {fmt.day(repo['active_to'])}, and the last "
        f"commit, on {fmt.day(repo['last_commit'])}, edits comments and docstrings only.</p>"
    )
    parts.append("</section>")

    # What it built
    parts.append("<section>")
    parts.append(_h2("built", "What it built"))
    parts.append(
        f"<p>The harness is real ({_claim('N9')}). It has a generic Butcher-table stepper "
        f"for explicit methods, an ODE generator with "
        f"{fmt.count(audit['training_ode_family_count'])} families that include stiff "
        f"problems such as Robertson, Oregonator and Van der Pol, a SciPy reference solver, "
        f"parallel scoring, JSON checkpoints and an SQLite results layer. Each of the "
        f"{fmt.count(repo['trial_folders'])} trials has its own configuration, script and "
        f"seed, with its artifacts committed. The source tree holds "
        f"{fmt.count(repo['src_python_lines'])} lines of Python in "
        f"{fmt.count(repo['src_python_files'])} files.</p>"
    )
    parts.append(
        f"<p>The final test set came from a separate generator with "
        f"{fmt.count(audit['evaluation_ode_family_count'])} families: "
        f"{_join('<code>' + fmt.esc(f) + '</code>' for f in audit['evaluation_ode_families'])}. "
        f"Its reference solver has a branch for "
        f"{fmt.count(audit['reference_solver_family_count'])} of them.</p>"
    )
    parts.append("</section>")

    # The benchmark
    parts.append("<section>")
    parts.append(_h2("benchmark", "The benchmark"))
    parts.append(
        f"<p>The final evaluation ran {fmt.count(bench['methods'])} methods, the "
        f"{_word(n_base)} baselines and {_word(n_trial)} trial tables, over "
        f"{fmt.count(bench['odes'])} generated ODEs in float64, with a fixed step "
        f"h = {fmt.sig(audit['evaluation_step'])} on t in [0, {fmt.sig(audit['evaluation_t_end'])}]. "
        f"Each ODE's reference solution came from Dormand-Prince (SciPy RK45). Of the "
        f"{fmt.count(bench['odes'])} ODEs, {fmt.count(bench['scorable_odes'])} could be "
        f"scored, the same {fmt.count(bench['scorable_odes'])} for every method "
        f"({_claim('N6')}).</p>"
    )
    parts.append(
        f"<p>The lowest mean error, {fmt.sig(dp['mean_max_error'])}, belongs to the "
        f"Dormand-Prince table and to {_trials(eq_dp)}, which saved that same table. The "
        f"next, {fmt.sig(rk4['mean_max_error'])}, belongs to RK4 and to {_trials(eq_rk4)}, "
        f"which saved RK4 ({_claim('N1')}). The error is the mean over the scorable ODEs of "
        f"each ODE's largest absolute error against the reference.</p>"
    )
    parts.append(f"<p><strong>Limits.</strong> {fmt.esc(claims['N1']['limits'])}</p>")
    bench_src = charts.source_link(bench["source"], sources)
    gl_off = [r for r in rows if r["mean_max_error"] >= charts.OFF_SCALE]
    off_sentence = ""
    if gl_off:
        off_sentence = (
            f" {fmt.esc(gl_off[0]['label'])} is drawn off scale: its "
            f"{fmt.sig(gl_off[0]['mean_max_error'])} is an artifact of a stepper bug, not a "
            f"measurement of the method ({_claim('N5')})."
        )
    bench_caption = (
        f"Mean of per-ODE max error for each of the {fmt.count(len(rows))} benchmark entries, "
        f"float64, fixed step h = {fmt.sig(audit['evaluation_step'])}, over "
        f"{fmt.count(bench['scorable_odes'])} scorable ODEs of {fmt.count(bench['odes'])}, "
        f"log scale.{off_sentence} Source: {bench_src}."
    )
    parts.append(charts.benchmark_chart(rows, _bench_notes(novel), bench_caption))
    parts.append(
        f"<p>Runtime is wall time for all {fmt.count(bench['odes'])} ODEs with the reference "
        f"solves included, so it measures more than the stepper. RK4 and {_trials(eq_rk4)} "
        f"ran the same table, yet their runtimes span {fmt.sig(rt_lo)} to {fmt.sig(rt_hi)} "
        f"seconds, which gives the size of the timing noise. {fmt.esc(fastest['label'])} had "
        f"the shortest runtime, {fmt.sig(fastest['runtime_s'])} seconds, because it ran as a "
        f"truncated explicit method with {fmt.count(fastest['stages'])} stages "
        f"({_claim('N5')}).</p>"
    )
    runtime_caption = (
        f"Wall time in seconds for all {fmt.count(bench['odes'])} ODEs, reference solves "
        f"included, linear scale. RK4 and {_trials(eq_rk4)} ran the same table, so the "
        f"spread between them is timing noise. Source: {bench_src}."
    )
    parts.append(charts.runtime_chart(rows, bench["odes"], runtime_caption))
    parts.append("</section>")

    # The audit
    parts.append("<section>")
    parts.append(_h2("audit", "What an audit in September 2026 found"))
    parts.append(
        f"<p>In September 2026 the repository's code and committed results were checked "
        f"against each claim in its README and in <code>results/analysis_report.md</code>. "
        f'The full list with evidence is on the <a href="claims.html#novel">claims audit '
        f"page</a>. Three main conclusions did not hold: the evolutionary search kept the "
        f"tables it was seeded with ({_claim('N2', 'N2')}), no gradient descent ran "
        f"({_claim('N4', 'N4')}), and nothing in the project tests whether a table is the "
        f"best possible ({_claim('N3', 'N3')}). Two numbers measure bugs rather than methods "
        f"({_claim('N5', 'N5')}, {_claim('N6', 'N6')}), and two more claims needed "
        f"correcting ({_claim('N7', 'N7')}, {_claim('N8', 'N8')}). Each item below gives the "
        f"claim, the project's own wording, and what the files show.</p>"
    )
    for cid in AUDIT_ORDER:
        if cid in claims:
            parts.append(_audit_item(cid, claims[cid], novel))
    parts.append("</section>")

    # The training log
    log_src = charts.source_link(log["source"], sources)
    parts.append("<section>")
    parts.append(_h2("training-log", "The training log"))
    parts.append(
        f"<p><code>metrics_log.csv</code> records one training run: "
        f"{fmt.count(len(per_epoch))} epochs of {fmt.count(per_epoch_candidates)} four-stage "
        f"candidates, {fmt.count(log['rows'])} rows in all. It has no trial column, so the "
        f"run it belongs to is not recorded. Every logged composite score is "
        f"{fmt.sig(clip)}, the ceiling the score is clipped to, so the score gave the search "
        f"nothing to select on ({_claim('N2')}).</p>"
    )
    tail = ""
    if best["epoch"] == first_epoch:
        tail = (
            " That candidate is RK4, which the search placed in its starting population, "
            "and no later epoch goes below it."
        )
    parts.append(
        f"<p>The chart plots the lowest and the median <code>max_error</code> among each "
        f"epoch's candidates. The lowest value in the whole log, "
        f"{fmt.sig(best['min_max_error'])}, is at epoch {fmt.count(best['epoch'])}.{tail}</p>"
    )
    log_caption = (
        f"Lowest and median <code>max_error</code> among the "
        f"{fmt.count(per_epoch_candidates)} candidates in each epoch of the one run in "
        f"<code>metrics_log.csv</code>, log scale. Every row has a composite score of "
        f"{fmt.sig(clip)}, the clip ceiling. Source: {log_src}."
    )
    parts.append(charts.metrics_log_chart(per_epoch, log_caption))
    parts.append("</section>")

    # What still holds
    parts.append("<section>")
    parts.append(_h2("what-holds", "What still holds"))
    parts.append(
        f"<p>The harness holds up as built ({_claim('N9')}). A stepper that takes any "
        f"explicit Butcher table, a generator of stiff and non-stiff test problems with a "
        f"reference solver, per-trial configurations and saved artifacts are what a search "
        f"like this needs, and the project had them working. The benchmark itself ran "
        f"{fmt.count(bench['methods'])} methods over {fmt.count(bench['odes'])} ODEs to "
        f"completion.</p>"
    )
    parts.append(
        f"<p>The benchmark ranking holds with its limits ({_claim('N1')}): in float64 on "
        f"these ODEs, the Dormand-Prince table and RK4 had the lowest errors. That matches "
        f"what the rk run found in float64 ({_claim('U1')}). The rk run looked somewhere the "
        f"2025 project did not, in Q15 fixed point with floor rounding, and "
        f'<a href="rk.html">its own page</a> '
        f"covers what it found there.</p>"
    )
    parts.append(
        f"<p>The author corrected some claims before this audit. Trials {fmt.count(6)} and "
        f"{fmt.count(7)} put the coefficients that earlier trials kept producing on a "
        f"forbidden list, so the repeated table had been noticed even though its cause had "
        f"not been found. Commit <code>d148c43</code> changed <q>competitive performance</q> "
        f"to <q>significantly worse accuracy</q> once the {fmt.count(bench['odes'])}-ODE "
        f"results came in, and commit <code>8c7cdd7</code> removed the README's CUDA speedup "
        f"claim and its <q>outperform</q> claims ({_claim('N8')}).</p>"
    )
    parts.append(
        '<p>The pipeline, and the points where the audit found it broke, are drawn on the '
        '<a href="architecture.html#arch-novel">architecture page</a>. Every number on this '
        f"page is read from the repository at commit <code>{fmt.esc(repo_commit)}</code> "
        f'(<a href="{fmt.esc(repo_url)}/tree/{fmt.esc(repo_commit)}">browse it</a>).</p>'
    )
    parts.append("</section>")
    return "\n".join(parts)
