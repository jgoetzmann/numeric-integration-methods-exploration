"""Epochs and research page (epochs.html): B29, B36, and B9, B11, B12, B19, B20 for its output."""
import re
from datetime import datetime

from web import fmt
from web.pages.epochs import timeline

SLUG = "epochs.html"
TITLE = "Epochs and research"
DESCRIPTION = (
    "When the rk run's two epochs ran, why epoch 1 froze, what stopped epoch 2 for five days, "
    "and how the run checks its own claims."
)

FINDINGS_URL = "https://jgoetzmann.github.io/rk-findings/"

_WORDS = (
    "zero", "one", "two", "three", "four", "five", "six",
    "seven", "eight", "nine", "ten", "eleven", "twelve",
)

_METHODS = ("euler", "midpoint", "heun2", "ralston2", "heun3", "kutta3", "rk4", "rk38")
_METHOD_RE = re.compile(r"\b(" + "|".join(_METHODS) + r")\b")

_WEIGHTING_LABELS = {
    "magnitude": "magnitude",
    "equal_median_anchor": "equal, median anchor",
    "equal_reference_norm": "equal, reference norm",
}
_BASIS_LABELS = {
    "analytic": "analytic",
    "traced_whole_step": "traced whole step",
}


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


def _epoch1(data):
    rk = data["rk"]
    e1 = rk["epochs"]["epoch1"]
    ch = rk["champion"]
    setup = rk["setup"]
    n_classical = len(rk["frontier"]["classical"])
    n_heldout = len(setup["heldout_problems"])
    p1 = (
        f"<p>Epoch 1 ran unattended from {fmt.day(e1['started'])} to {fmt.day(e1['stopped'])} "
        f"({_claim('R12')}). It completed {fmt.count(e1['cycles_run'])} cycles over "
        f"{fmt.count(e1['archive_day_count'])} days of archive and wrote "
        f"{fmt.count(e1['records'])} scored records, all under verifier hash "
        f"{_code(e1['verifier_hash'])}. When it stopped, the search was in phase "
        f"{fmt.count(e1['phase_at_stop'])} and {fmt.count(e1['occupied_cells'])} cells of the "
        "archive grid held an elite.</p>"
    )
    p2 = (
        f"<p>Its main result came early: the champion, {_code(ch['hash'])}, appeared at cycle "
        f"{fmt.count(ch['found_at_cycle'])}, and nothing in the remaining "
        f"{fmt.count(ch['cycles_since_last_improvement'])} cycles improved on it ({_claim('R6')}). "
        "Most of epoch 1's later work went into checking that result.</p>"
    )
    p3 = (
        f"<p>Inside Q15 fixed point with floor rounding, at the {fmt.count(setup['budget_cycles'])}"
        f"-cycle budget, the champion has {fmt.ratio(ch['lead'])} lower held-out error than "
        f"{_code(ch['best_classical'])}, the best of the {_word(n_classical)} classical methods "
        f"({_claim('R1')}). That figure uses the analytic cost model and magnitude weighting over "
        f"{_word(n_heldout)} held-out problems. It narrows under other cost bases and "
        'weightings (see the <a href="#grid">counterfactual grid</a> below). The full results '
        'are on the <a href="rk.html">rk run page</a>.</p>'
    )
    table = _archive_table(e1["archive_days"], "Epoch 1 records per archive day")
    return (
        "<section>\n"
        '<h2 id="epoch-1">Epoch 1</h2>\n'
        f"{p1}\n{p2}\n{p3}\n{table}\n"
        "</section>"
    )


def _froze(data):
    rk = data["rk"]
    ep = rk["epochs"]
    e1 = ep["epoch1"]
    e2 = ep["epoch2"]
    model = rk["setup"]["cost_model"]
    rk4 = _trace_row(rk, "rk4")
    rk38 = _trace_row(rk, "rk38")
    p1 = f"<p>{_prose(ep['why_epoch1_froze'])}</p>"
    p2 = (
        f"<p>Under the epoch-1 rule with the fast multiplier "
        f"({_code(model)}), <code>rk4</code> cost {fmt.count(rk4['analytic'][model])} cycles per "
        f"step and <code>rk38</code> {fmt.count(rk38['analytic'][model])}. The compiled step, "
        "counted over the same scope the model prices, took "
        f"{fmt.count(rk38['matched_scope'][model])} cycles for <code>rk38</code> and "
        f"{fmt.count(rk4['matched_scope'][model])} for <code>rk4</code> ({_claim('R7')}). The "
        "traced step matched the Python evaluator bit for bit in "
        f"{fmt.esc(rk['engineering']['trace_crosscheck'])} cases. The emulator is "
        "instruction-accurate, not cycle-accurate: its cycle counts come from a timing table "
        "applied to the executed instructions, and nothing was measured on a physical chip.</p>"
    )
    p3 = (
        "<p>With the pinned files changed, the verifier hash moved from "
        f"{_code(e1['verifier_hash'])} over {fmt.count(e1['verifier_files'])} files to "
        f"{_code(e2['verifier_hash'])} over {fmt.count(e2['verifier_files'])}. The run did not "
        "rescore the epoch-1 archive under the new model. It froze epoch 1 on "
        f"{fmt.day(e1['frozen_at'])}, kept its archive and documents in <code>rk-work</code> "
        "under <code>epochs/1/</code>, and started epoch 2 with a new archive. Results on this "
        "site come from epoch 1 unless they say otherwise.</p>"
    )
    return (
        "<section>\n"
        '<h2 id="why-epoch-1-froze">Why epoch 1 froze</h2>\n'
        f"{p1}\n{p2}\n{p3}\n"
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
        f"<p>Epoch 2 started on {fmt.day(e2['started'])} under verifier hash "
        f"{_code(e2['verifier_hash'])}. As of {fmt.day(e2['as_of'])} it had reached cycle "
        f"{fmt.count(e2['cycle'])} and written {fmt.count(e2['records'])} records to its own "
        f"archive. Its cycles rotate among {_word(len(lanes))} lanes: the explicit lane scores "
        "candidates in Q15 into the archive, while the adaptive and implicit lanes measure how "
        "many cycles a float64 solve needs to reach a tolerance, and their results stay out of "
        f"the archive. Cycles per lane so far: {lane_text}.</p>"
    )
    p2 = (
        f"<p>From {fmt.day(down['from'])} to {fmt.day(down['to'])} the run was down for about "
        f"{_word(round(down_days))} days: {_prose(down['why'])}. Epoch 2's archive therefore has "
        f"records from only {_word(len(days))} days so far: {day_text}.</p>"
    )
    p3 = (
        "<p>Two changes followed. The watchdog now restarts the run after its own stops, once "
        "the condition behind the stop clears (decision D46). A logon task restarts the run "
        "after a reboot (decision D47).</p>"
    )
    return (
        "<section>\n"
        '<h2 id="epoch-2">Epoch 2, as of the snapshot</h2>\n'
        f"{p1}\n{p2}\n{p3}\n"
        "</section>"
    )


def _premise(data):
    rk = data["rk"]
    pr = rk["premise"]
    budget = fmt.count(rk["setup"]["budget_cycles"])
    floor_won, floor_of = (int(v) for v in pr["rk4_best_under_floor"].split("/"))
    near_won, near_of = (int(v) for v in pr["rk4_best_under_round_to_nearest"].split("/"))
    return (
        '<h3 id="premise">A premise test set before the search</h3>\n'
        "<p>Before the search started, the run pre-registered thresholds that would count "
        "against its premise: that in Q15 with floor rounding, at practical step sizes, rounding "
        "error outweighs truncation error, so the textbook coefficients are not the ones that do "
        f"best. The stored verdict is {_code(pr['stored_verdict'])} ({_claim('R9')}): the "
        "thresholds were met for some methods and missed narrowly for one. The run published "
        "that verdict as it came out.</p>\n"
        f"<p>In Q15 at the {budget}-cycle budget, <code>rk4</code> had the lowest error on "
        f"{fmt.count(floor_won)} of {fmt.count(floor_of)} problems under floor rounding, and on "
        f"{fmt.count(near_won)} of {fmt.count(near_of)} under round to nearest.</p>"
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


def _grid(data):
    cf = data["rk"]["counterfactual"]
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
        "<th>Lowest ratio, one problem dropped</th><th>Champion still leads</th></tr></thead>\n"
        f"<tbody>\n{rows}\n</tbody>\n</table>\n</div>"
    )

    both = ""
    if len(lead_bases) == 1 and len(leading) >= 2:
        label = fmt.esc(_BASIS_LABELS.get(lead_bases[0], lead_bases[0]))
        both = f", {'both' if len(leading) == 2 else 'all'} on the {label} basis"
    mag_traced = by_key[("magnitude", "traced_whole_step")]
    med_traced = by_key[("equal_median_anchor", "traced_whole_step")]
    tail = (
        " On the traced whole-step basis the ratio is "
        f"{fmt.ratio(mag_traced['ratio'])} under magnitude weighting, and under median-anchor "
        f"weighting a classical method leads, at {fmt.ratio(med_traced['ratio'])}."
    )
    n_other = len(cells) - len(leading)
    return (
        '<h3 id="grid">The counterfactual grid</h3>\n'
        f"<p>The run recomputed the headline lead under {_word(len(weightings))} weightings of "
        f"the held-out problems and {_word(len(bases))} cost bases, {_word(len(cells))} cells in "
        f"all, and publishes every cell. {_cap(_prose(cf['note']))}</p>\n"
        f"{table}\n"
        f"<p>The stored check says the champion still leads in {_word(len(leading))} of the "
        f"{_word(len(cells))} cells{both}. In the other {_word(n_other)}, either the ratio is "
        "below 1 or it falls below 1 when one held-out problem is dropped."
        f"{tail}</p>"
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
