"""novel.html: the 2025 ML project, what it built, and what the 2026 audit found."""
from web import fmt

from . import charts

SLUG = "novel.html"
TITLE = "The 2025 ML project"
DESCRIPTION = (
    "What the 2025 ML project built and measured, and which of its conclusions a "
    "September 2026 audit did not support."
)

VERDICT_LABELS = {
    "supported": "Supported",
    "supported-with-limits": "Supported with limits",
    "not-supported": "Not supported",
    "artifact": "Artifact",
}

# Claims the 2025 project made, each quoted with its original wording and correction.
AUDIT_ORDER = ["N2", "N3", "N4", "N5", "N6", "N7", "N8"]
# Supported findings about the project's checks, stated as the audit found them.
FINDING_ORDER = ["N10", "N11"]

AUDIT_HEADINGS = {
    "N2": "The saved table never left the seed",
    "N3": "The score could not tell RK4 from a random table",
    "N4": "The generator was never trained",
    "N5": "The Gauss-Legendre 3 error measures a stepper bug",
    "N6": "The success rate belongs to the ODE set",
    "N7": "Trial 16 is the top scorer among random draws",
    "N8": "No training set came near 10,000 ODEs",
    "N10": "Nothing enforced the order conditions",
    "N11": "There is no automated test suite",
}

# Stiff families the prose names, in the order it names them.
STIFF_NAMES = [("robertson", "Robertson"), ("oregonator", "Oregonator"), ("van_der_pol", "Van der Pol")]

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


def _span(nums):
    """'1 to 4, 6, 8 and 9': runs of three or more consecutive trials collapse to 'a to b'."""
    nums = sorted(nums)
    groups = []
    for n in nums:
        if groups and n == groups[-1][-1] + 1:
            groups[-1].append(n)
        else:
            groups.append([n])
    parts = []
    for g in groups:
        if len(g) >= 3:
            parts.append(f"{fmt.count(g[0])} to {fmt.count(g[-1])}")
        else:
            parts.extend(fmt.count(n) for n in g)
    return _join(parts)


def _trials(nums):
    nums = sorted(nums)
    word = "trial" if len(nums) == 1 else "trials"
    return f"{word} {_span(nums)}"


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
            notes[r["id"]] = f"the top scorer among random draws ({_claim('N7')})"
        elif by_trial.get(t, {}).get("identical_to_trials"):
            same = _trials(by_trial[t]["identical_to_trials"])
            notes[r["id"]] = f"same A and b as {same} ({_claim('N4')})"
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
                '<td colspan="5">no table saved; not in the final evaluation</td></tr>'
            )
            continue
        d_rk4 = row.get("max_abs_diff_from_rk4")
        d_dp = row.get("max_abs_diff_from_dormand_prince")
        n_odes = row.get("training_odes")
        same = []
        if t in eq_rk4:
            same.append("RK4")
        if t in eq_dp:
            same.append("Dormand-Prince")
        if row.get("identical_to_trials"):
            same.append(_trials(row["identical_to_trials"]))
        rows.append(
            f"<tr><td>{fmt.count(t)}</td><td>{fmt.count(row['stages'])}</td>"
            f"<td>{'n/a' if n_odes is None else fmt.count(n_odes)}</td>"
            f"<td>{'n/a' if d_rk4 is None else fmt.sig(d_rk4)}</td>"
            f"<td>{'n/a' if d_dp is None else fmt.sig(d_dp)}</td>"
            f"<td>{'; '.join(same) if same else 'none'}</td></tr>"
        )
    return (
        '<table class="trials" style="display:block;max-width:100%;overflow-x:auto">'
        "<caption>What each trial saved: the number of ODEs it trained on, the largest "
        "absolute difference in A and b from the textbook table with the same stage count "
        "(n/a where the project has no such table), and the trials that saved the same A "
        "and b</caption>"
        '<thead><tr><th scope="col">Trial</th><th scope="col">Stages</th>'
        '<th scope="col">Training ODEs</th>'
        '<th scope="col">Largest difference from RK4</th>'
        '<th scope="col">Largest difference from Dormand-Prince</th>'
        '<th scope="col">Same A and b as</th></tr></thead>'
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def _flat_score_sentence(trials):
    """The N3 extra: saved files whose table scores 1 against RK4 at a different error."""
    rows = [
        r for r in trials["rows"]
        if r.get("score_ratio_to_rk4") == 1 and r.get("error_ratio_to_rk4") not in (None, 1)
        and r["trial"] != 8
    ]
    worse = [r for r in rows if r["error_ratio_to_rk4"] > 1]
    better = [r for r in rows if r["error_ratio_to_rk4"] < 1]
    eq_dp = set(trials["equal_to_dormand_prince"])
    bits = []
    if worse:
        bits.append(
            f"{_trials(r['trial'] for r in worse).capitalize()} also score 1 against RK4, at "
            f"{_join(fmt.sig(r['error_ratio_to_rk4']) for r in worse)} times RK4's error"
            if len(worse) > 1 else
            f"Trial {fmt.count(worse[0]['trial'])} also scores 1 against RK4, at "
            f"{fmt.sig(worse[0]['error_ratio_to_rk4'])} times RK4's error"
        )
    for r in better:
        what = ", which saved Dormand-Prince," if r["trial"] in eq_dp else ""
        bits.append(
            f"trial {fmt.count(r['trial'])}{what} scores 1 at "
            f"{fmt.sig(r['error_ratio_to_rk4'])} times RK4's error"
        )
    if not bits:
        return ""
    lead = bits[0][0].upper() + bits[0][1:]
    tail = "Tables with far higher error than RK4"
    if better:
        tail += " and a table with lower error" if len(better) == 1 else " and tables with lower error"
    return (
        "<p>Trial 8's file is not the only one. Each trial's saved file compares its table "
        f"with RK4 on one sample. {lead}" + (f", and {', '.join(bits[1:])}" if bits[1:] else "")
        + f". {tail} all scored the same as RK4.</p>"
    )


def _audit_extra(cid, novel, sources):
    bench = novel["benchmark"]
    trials = novel["trials"]
    audit = novel["audit_counts"]
    log = novel["metrics_log"]
    t16 = novel["trial16"]
    ckpt = novel["evolution_checkpoints"]
    by_trial = {row["trial"]: row for row in trials["rows"]}
    eq_rk4 = trials["equal_to_rk4"]
    eq_dp = trials["equal_to_dormand_prince"]

    if cid == "N2":
        d_rk4 = max(by_trial[t]["max_abs_diff_from_rk4"] for t in eq_rk4)
        d_dp = max(by_trial[t]["max_abs_diff_from_dormand_prince"] for t in eq_dp)
        return (
            f"<p>The saved tables confirm it. The largest difference in A and b from RK4 is "
            f"{fmt.sig(d_rk4)} for {_trials(eq_rk4)}, and the largest difference from "
            f"Dormand-Prince is {fmt.sig(d_dp)} for {_trials(eq_dp)}. The checkpoint scores are "
            f"in {charts.source_link(ckpt['source'], sources)}. The search started from the "
            f"textbook tables, so the match was not blind, and neither project ran a blind "
            f"test ({_claim('U2')}).</p>"
        )
    if cid == "N3":
        return (
            _flat_score_sentence(trials)
            + '<p>The <a href="#training-log">training log</a> below shows the same problem '
            "in the raw rows: every logged candidate has the same composite score.</p>"
        )
    if cid == "N4":
        rows = ckpt["rows"]
        loss = {r["epochs_with_surrogate_loss"] for r in rows}
        epochs = {r["epochs"] for r in rows}
        if len(loss) == 1 and len(epochs) == 1:
            trained = (
                f"each records a surrogate loss in {fmt.count(loss.pop())} of its "
                f"{fmt.count(epochs.pop())} epochs"
            )
        else:
            trained = "they record a surrogate loss in " + _join(
                f"{fmt.count(r['epochs_with_surrogate_loss'])} of {fmt.count(r['epochs'])} "
                f"epochs for trial {fmt.count(r['trial'])}" for r in rows
            )
        return (
            f"<p>The checkpoints of {_trials(r['trial'] for r in rows)} show the surrogate "
            f"training: {trained} ({charts.source_link(ckpt['source'], sources)}).</p>"
            "<p>The table below compares what each trial saved with the textbook table of "
            "the same stage count.</p>"
            + _trials_table(novel)
        )
    if cid == "N5":
        off = [r for r in bench["rows"] if r["mean_max_error"] >= charts.OFF_SCALE]
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
            f"one in the project that is not clipped at {fmt.sig(clip)}. Over its "
            f"{fmt.count(len(hist))}-epoch history the best score peaked at "
            f"{fmt.sig(top['best_score'])} in epoch {fmt.count(top['epoch'])}, and the saved "
            f"table is that epoch's random draw. The trial ran for "
            f"{fmt.sig(t16['training_time_s'])} seconds.</p>"
        )
    if cid == "N8":
        return (
            f"<p>The table under <a href=\"#audit-n4\">the generator item</a> above lists the "
            f"size of each trial's training set. In the final code the training generator has "
            f"{fmt.count(audit['training_ode_family_count'])} families, and the reference "
            f"solver handles {fmt.count(audit['reference_solver_family_count'])} of them, so a "
            f"training set from that generator held ODEs the pipeline could not score. The "
            f"final test drew from a separate generator with "
            f"{fmt.count(audit['evaluation_ode_family_count'])} families.</p>"
        )
    if cid == "N10":
        labels = {}
        for row in trials["rows"]:
            if row.get("order_check_label") is not None:
                labels.setdefault(row["order_check_label"], []).append(row["trial"])
        copies = set(eq_rk4) | set(eq_dp)
        top = max(labels)
        top_trials = labels[top]
        others = sorted(t for lab, ts in labels.items() if lab != top for t in ts)
        rest = {lab for lab, ts in labels.items() if lab != top}
        if set(top_trials) != copies or len(rest) != 1:
            return ""
        return (
            f"<p>The saved files show it. {_trials(eq_rk4).capitalize()}, which saved "
            f"RK4, and {_trials(eq_dp)}, which saved Dormand-Prince, are labelled order "
            f"{fmt.count(top)}. Every other saved table, {_trials(others)}, is labelled order "
            f"{fmt.count(rest.pop())}.</p>"
        )
    return ""


def _audit_item(cid, claim, novel, sources):
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
    out.append(
        "<p>The project's own wording:</p>"
        f"<blockquote><p>{fmt.esc(claim['original_wording'])}</p></blockquote>"
    )
    out.append(f"<p>{fmt.esc(claim['correction'])}</p>")
    out.append(_audit_extra(cid, novel, sources))
    out.append("</section>")
    return "".join(out)


def _finding_item(cid, claim, novel, sources):
    """A supported finding: the claim text as the audit states it, no quote marks."""
    verdict = claim["verdict"]
    label = VERDICT_LABELS.get(verdict, verdict)
    anchor = f"audit-{cid.lower()}"
    out = [
        '<section class="audit-item">',
        f'<h3 id="{anchor}">{fmt.esc(AUDIT_HEADINGS.get(cid, cid))}</h3>',
        f"<p>{_claim(cid, 'Claim ' + cid)}: "
        f'<span class="verdict verdict-{fmt.esc(verdict)}">{fmt.esc(label)}</span>. '
        f"{fmt.esc(claim['claim'])}</p>",
    ]
    if claim.get("limits"):
        out.append(f"<p>{fmt.esc(claim['limits'])}</p>")
    out.append(_audit_extra(cid, novel, sources))
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
    t16_row = by_id.get("16")
    ref_fams = set(audit["reference_solver_families"])
    stiff_in = [name for key, name in STIFF_NAMES if key in ref_fams]
    stiff_out = [name for key, name in STIFF_NAMES if key not in ref_fams]
    eval_missing = sorted(set(audit["evaluation_ode_families"]) - ref_fams)

    parts = []
    parts.append(f"<h1>{fmt.esc(TITLE)}</h1>")
    parts.append(
        f'<p class="lead"><code>{fmt.esc(repo_name)}</code> was a 2025 attempt to find new '
        f"explicit Runge-Kutta tables with machine learning: a neural generator, a surrogate "
        f"model and an evolutionary search, scored on generated ODEs. It built an evaluation "
        f"harness that runs end to end for explicit tables and ran a benchmark of "
        f"{fmt.count(bench['methods'])} methods on {fmt.count(bench['odes'])} ODEs. When an "
        f"audit checked its code and committed results in September 2026, its main "
        f"conclusions did not hold up.</p>"
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
        f"{fmt.day(repo['first_commit'])}, the work itself ran from "
        f"{fmt.day(repo['active_from'])} to {fmt.day(repo['active_to'])}, and the last "
        f"commit, on {fmt.day(repo['last_commit'])}, touches only comments and docstrings.</p>"
    )
    parts.append("</section>")

    # What it built
    covered = ""
    if stiff_in or stiff_out:
        covered = (
            f" The reference solver covers {fmt.count(audit['reference_solver_family_count'])} "
            f"of those {fmt.count(audit['training_ode_family_count'])} families"
            + (f", {_join(stiff_in)} among them" if stiff_in else "")
            + (f" but not {' or '.join(stiff_out)}" if stiff_out else "")
            + "."
        )
    parts.append("<section>")
    parts.append(_h2("built", "What it built"))
    parts.append(
        f"<p>The evaluation harness runs end to end for explicit tables ({_claim('N9')}). It "
        f"has a generic Butcher-table stepper for explicit methods, a SciPy reference solver, "
        f"parallel scoring, JSON checkpoints and a training generator with "
        f"{fmt.count(audit['training_ode_family_count'])} ODE families, including stiff ones "
        f"such as {_join(name for _, name in STIFF_NAMES)}.{covered} An SQLite results module "
        f"is in the tree, but nothing in the pipeline calls it.</p>"
    )
    parts.append(
        f"<p>The final test set came from a separate generator with "
        f"{fmt.count(audit['evaluation_ode_family_count'])} families: "
        f"{_join('<code>' + fmt.esc(f) + '</code>' for f in audit['evaluation_ode_families'])}. "
        f"The reference solver has a branch for "
        f"{fmt.count(audit['reference_solver_family_count'])} of them; "
        f"{_join('<code>' + fmt.esc(f) + '</code>' for f in eval_missing)} is the one it "
        f"lacks.</p>"
    )
    parts.append(
        f"<p>The project set up {fmt.count(repo['trial_folders'])} trial configurations, and "
        f"each saved table records the settings its trial ran with. The whole "
        f"<code>src/</code> tree, which holds the generator, the training scripts and the "
        f"analysis code as well as the harness, has {fmt.count(repo['src_python_lines'])} "
        f"lines of Python in {fmt.count(repo['src_python_files'])} files.</p>"
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
        f"Each ODE's reference solution came from Dormand-Prince (SciPy RK45), an adaptive "
        f"solver. Of the {fmt.count(bench['odes'])} ODEs, {fmt.count(bench['scorable_odes'])} "
        f"could be scored, the same {fmt.count(bench['scorable_odes'])} for every method "
        f"({_claim('N6')}).</p>"
    )
    parts.append(
        f"<p>The lowest mean error, {fmt.sig(dp['mean_max_error'])}, belongs to the "
        f"Dormand-Prince table and to {_trials(eq_dp)}, which saved that same table. The "
        f"next, {fmt.sig(rk4['mean_max_error'])}, belongs to RK4 and to {_trials(eq_rk4)}, "
        f"which saved RK4 ({_claim('N1')}). For each scorable ODE the benchmark takes the "
        f"largest absolute error against the reference, then averages those maxima.</p>"
    )
    parts.append(f"<p><strong>Limits.</strong> {fmt.esc(claims['N1']['limits'])}</p>")
    bench_src = charts.source_link(bench["source"], sources)
    gl_off = [r for r in rows if r["mean_max_error"] >= charts.OFF_SCALE]
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
        f"seconds; that spread is the timing noise. {fmt.esc(fastest['label'])} had "
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
        f"<p>In September 2026 an audit checked each claim in the README and in "
        f"<code>results/analysis_report.md</code> against the repository's code and "
        f'committed results. The full list with evidence is on the <a href="claims.html#novel">'
        f"claims audit page</a>. Three main conclusions did not hold: the saved table never "
        f"moved off the seed the evolutionary search started from ({_claim('N2', 'N2')}), the "
        f"generator that proposed tables was never trained ({_claim('N4', 'N4')}), and nothing "
        f"in the project tests whether a table is the best possible ({_claim('N3', 'N3')}). "
        f"Two numbers describe the harness rather than the methods ({_claim('N5', 'N5')}, "
        f"{_claim('N6', 'N6')}), and two more claims needed correcting "
        f"({_claim('N7', 'N7')}, {_claim('N8', 'N8')}). The audit also recorded two facts "
        f"about the project's own checks: nothing enforced the order conditions "
        f"({_claim('N10', 'N10')}), and there is no automated test suite "
        f"({_claim('N11', 'N11')}). Each item from N2 to N8 quotes the claim and the "
        f"project's own wording, then says what the files show.</p>"
    )
    for cid in AUDIT_ORDER:
        parts.append(_audit_item(cid, claims[cid], novel, sources))
    for cid in FINDING_ORDER:
        parts.append(_finding_item(cid, claims[cid], novel, sources))
    parts.append("</section>")

    # The training log
    log_src = charts.source_link(log["source"], sources)
    parts.append("<section>")
    parts.append(_h2("training-log", "The training log"))
    parts.append(
        f"<p><code>metrics_log.csv</code> records one training run: "
        f"{fmt.count(len(per_epoch))} epochs of {fmt.count(per_epoch_candidates)} four-stage "
        f"candidates, {fmt.count(log['rows'])} rows in all. It has no trial column, but only "
        f"trial {fmt.count(15)}'s saved settings ask for {fmt.count(per_epoch_candidates)} "
        f"candidates per epoch, so it is most likely trial {fmt.count(15)}'s log. Every logged "
        f"composite score is {fmt.sig(clip)}, the ceiling the score is clipped to, so the "
        f"score gave the search nothing to select on ({_claim('N2')}).</p>"
    )
    tail = ", and no later epoch goes below it" if best["epoch"] == first_epoch else ""
    parts.append(
        f"<p>The chart plots the lowest and the median <code>max_error</code> among each "
        f"epoch's candidates. The lowest value in the whole log, "
        f"{fmt.sig(best['min_max_error'])}, is at epoch {fmt.count(best['epoch'])}{tail}.</p>"
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
    loss_sentence = ""
    if t16_row is not None:
        loss_sentence = (
            f" Its report kept every benchmark entry, the weakest included, and stated trial "
            f"{fmt.count(16)}'s mean error of {fmt.sig(t16_row['mean_max_error'])} as a loss "
            f"({_claim('N7')})."
        )
    parts.append("<section>")
    parts.append(_h2("what-holds", "What still holds"))
    parts.append(
        f"<p>The harness runs end to end for explicit tables ({_claim('N9')}). A search like "
        f"this needs a stepper that takes any explicit Butcher table, a generator of stiff and "
        f"non-stiff test problems with a reference solver, per-trial configurations and saved "
        f"artifacts. The project had all of them, with the limits the audit lists "
        f"({_claim('N5')}, {_claim('N6')}), and its benchmark ran "
        f"{fmt.count(bench['methods'])} methods over {fmt.count(bench['odes'])} ODEs to "
        f"completion.{loss_sentence}</p>"
    )
    parts.append(
        f"<p>The benchmark ranking holds with its limits ({_claim('N1')}): in float64 on "
        f"these ODEs, the Dormand-Prince table and RK4 had the lowest errors. The rk run also "
        f"found float64 <code>rk4</code> far more accurate than its champion "
        f"({_claim('U1')}). Of the two, the 2025 benchmark is the weaker evidence, because "
        f"its other entries were copies of those two tables, random tables and truncated "
        f"methods. The rk run looked somewhere the 2025 project did not, in Q15 fixed point "
        f'with floor rounding, and <a href="rk.html">its own page</a> covers what it found '
        f"there.</p>"
    )
    parts.append(
        f"<p>The author had already corrected some claims before the audit. Trials "
        f"{fmt.count(6)} and {fmt.count(7)} put the coefficients that earlier trials kept "
        f"producing on a forbidden list, so the author had noticed the repeated table, though "
        f"not its cause. Commit <code>d148c43</code> changed <q>competitive performance</q> "
        f"to <q>significantly worse accuracy</q> once the {fmt.count(bench['odes'])}-ODE "
        f"results came in, though the same commit strengthened <q>near-optimality</q> to "
        f"<q>mathematical optimality</q> ({_claim('N3')}). Commit <code>8c7cdd7</code> "
        f"removed the README's CUDA speedup claim and its <q>outperform</q> claims "
        f"({_claim('N8')}).</p>"
    )
    parts.append(
        '<p>The <a href="architecture.html#arch-novel">architecture page</a> draws the '
        "pipeline and marks where the audit found it broke. Every number on this "
        f"page is read from the repository at commit <code>{fmt.esc(repo_commit)}</code> "
        f'(<a href="{fmt.esc(repo_url)}/tree/{fmt.esc(repo_commit)}">browse it</a>).</p>'
    )
    parts.append("</section>")
    return "\n".join(parts)
