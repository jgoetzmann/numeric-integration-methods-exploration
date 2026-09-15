"""Counterfactual scoring: one harness, three switches.

Every counterfactual this project runs sits downstream of the same three calls in the
pinned scoring path:

    n    = simulate.steps_for_budget(t, model, p.n_states, budget)   (cost enters here)
    e, q = simulate.problem_error(t, p, n)                           (the solve)
    agg  = evaluator._rms(values)                                    (the aggregate)

`score()` takes one override per call site, with the pinned behaviour as all three
defaults. Rounding overrides the solve, which is the counterfactual already shipped in
demo_data.py. Cost overrides the step count (audit G3). Weighting overrides the aggregate
(audit G1). Nothing here edits a pinned file: costmodel, evaluator, problems and simulate
are imported and used as they are, no archived score is read as authoritative or rewritten,
and VERIFIER_HASH is untouched. See DECISIONS.md D43.

Cost basis, and the label every traced number carries
-----------------------------------------------------
The analytic basis is `costmodel.cycle_count`, which is what the archive was scored under.
The traced basis is `state_scaling.n{1..4}.cycles_per_step` from rk-work/trace/results.json:
TRM-priced cycles for every instruction executed inside rk_step in one step, EXCLUDING the
derivative routine's own body, under an emulator that is instruction accurate and not cycle
accurate. It is used here as a budget denominator, because a real part pays those cycles out
of the same 65,536, and never as a numerator against the analytic count: that second use
would report a scope difference as a model error and stays forbidden (CLAUDE.md, D42, D43).
Neither basis is the full per-step cost on a part, so the pair is a bracket rather than a
correction.

Weighting scales
----------------
Held-out and search error are an RMS of the per-problem errors, so a problem's influence
grows with the square of its error and the problems do not carry equal weight. Two scales
divide it out, and they disagree, so both are published:

  median_anchor    the median error of the eight classical anchors on that problem, at the
                   analytic basis. This is the equal-weighting answer the project names.
  reference_norm   the error a method reports when its state collapses to zero, which is
                   error_metric(name, zeros). For the five distance problems that is
                   ||reference(t_end)|| / peak; pendulum and quaternion measure relative
                   drift, whose natural scale is 1, and the zero-state definition gives 1
                   for them without a special case. Dividing by it CONCENTRATES weight on
                   rc_thermal rather than equalizing it, because rc_thermal's norm is the
                   smallest of the four held-out problems.

Both scales are constants of the analytic basis, computed once, so a weighting comparison
and a cost comparison never move together.

Determinism: sorted iteration, no wall clock, no randomness, no network. Given the same
archive, trace document and pins, this module writes the same bytes.
"""
from __future__ import annotations

import json
import math
import os
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # rk-overview/tools
WS = HERE.parent.parent                          # workspace root
os.environ.setdefault("RK_WORK_DIR", str(WS / "rk-work"))
os.environ.setdefault("RK_FINDINGS_DIR", str(WS / "rk-findings"))
if str(WS / "rk-harness") not in sys.path:
    sys.path.insert(0, str(WS / "rk-harness"))

from rk_harness import trace_hash, verifier_hash                  # noqa: E402
from rk_harness.costmodel import COST_MODELS, cycle_count         # noqa: E402
from rk_harness.evaluator import _rms                             # noqa: E402
from rk_harness.problems import PROBLEMS, error_metric, to_physical  # noqa: E402
from rk_harness.simulate import problem_error, solve_q15, steps_for_budget  # noqa: E402
from rk_harness.tableau import classical, content_hash, from_json  # noqa: E402

BUDGET = 65536
MODEL = "m0plus_fast"
SEARCH_PROBLEMS = ("dahlquist", "damped_osc", "vanderpol_mild")
HELDOUT_PROBLEMS = ("pendulum", "dc_motor", "rc_thermal", "quaternion")
ALL_PROBLEMS = SEARCH_PROBLEMS + HELDOUT_PROBLEMS

# The four methods finding 2 publishes, the ones tools/floor_round.json covers. euler's rank
# question is asked inside this field, so it is answered inside it as well as over the nine.
PUBLISHED_FOUR = ("euler", "heun2", "rk4", "rk38")

COST_BASES = ("analytic", "traced_whole_step")
WEIGHTINGS = ("magnitude", "equal_median_anchor", "equal_reference_norm")

_INF = float("inf")


class CounterfactualError(RuntimeError):
    """A price that does not exist, or a document that does not match the pins."""


# ------------------------------------------------------------------- the harness

def analytic_steps(model_name: str = MODEL, budget: int = BUDGET):
    """steps_fn: the pinned step count, budget // costmodel.cycle_count."""
    model = COST_MODELS[model_name]

    def steps(t, p) -> int:
        return steps_for_budget(t, model, p.n_states, budget)
    return steps


def traced_steps(prices: dict[str, dict[int, int]], budget: int = BUDGET):
    """steps_fn: budget // the traced whole-step count for this tableau at this state count.

    Raises rather than modelling when a price is missing. Pricing an untraced method or an
    untraced state count by extrapolation is the one thing acceptance 7 forbids, and the
    measured n1 to n4 counts are markedly non-linear in state dimension, so an affine fit
    from two of them underprices four states by 1.46x to 2.43x.
    """
    def steps(t, p) -> int:
        by_state = prices.get(content_hash(t))
        if by_state is None:
            raise CounterfactualError("no trace row for this tableau")
        cyc = by_state.get(p.n_states)
        if cyc is None:
            raise CounterfactualError(f"no traced price at n_states={p.n_states}")
        if cyc <= 0:
            raise CounterfactualError(f"traced price at n_states={p.n_states} is not positive")
        return budget // cyc
    return steps


def equal_weight(scale: dict[str, float]):
    """weight_fn: divide each per-problem error by that problem's scale before the RMS."""
    def weight(p, e: float) -> float:
        s = scale[p.name]
        if not (s > 0):
            raise CounterfactualError(f"scale for {p.name} is not positive")
        return e / s
    return weight


def score(t, problems, *, steps_fn=None, solve_fn=None, weight_fn=None) -> dict:
    """Score one tableau over one problem tuple, with three overridable call sites.

    Defaults are the pinned path: steps from costmodel.cycle_count, the solve from
    simulate.problem_error, and an unweighted RMS. Failure semantics follow
    evaluator._run_set and evaluator.set_error exactly, so a counterfactual row means the
    same thing a scored row means: a problem that raises is inf, and one overflow anywhere
    makes the whole set inf. A missing price is not an overflow and propagates.
    """
    steps_fn = steps_fn or analytic_steps()
    solve_fn = solve_fn or problem_error
    weight_fn = weight_fn or (lambda p, e: e)

    raw: dict[str, float] = {}
    steps: dict[str, int] = {}
    overflowed = False
    for p in problems:
        try:
            n = int(steps_fn(t, p))
            steps[p.name] = n
            if n <= 0:
                raw[p.name] = _INF
                continue
            e, _q = solve_fn(t, p, n)
            e = float(e)
            if not math.isfinite(e):
                e = _INF
            raw[p.name] = e
        except CounterfactualError:
            raise
        except Exception:  # noqa: BLE001 - evaluator._run_set catches everything here too
            raw[p.name] = _INF
            overflowed = True
    if overflowed:
        raw = {p.name: _INF for p in problems}
    weighted = {p.name: weight_fn(p, raw[p.name]) for p in problems}
    agg = _INF if overflowed else _rms([weighted[p.name] for p in problems])
    return {"aggregate": agg, "per_problem": raw, "weighted": weighted,
            "steps": steps, "overflowed": overflowed}


def memo(fn):
    """Memoize a solve on (tableau content hash, problem name, steps).

    problem_error is a pure function of those three, so the cache changes nothing about the
    numbers; it exists because the same (method, basis) cell is scored once per weighting.
    """
    cache: dict[tuple, tuple] = {}

    def wrapped(t, p, n):
        key = (content_hash(t), p.name, int(n))
        if key not in cache:
            cache[key] = fn(t, p, n)
        return cache[key]
    wrapped.cache = cache
    return wrapped


# ------------------------------------------------------------------ trace document

def load_trace(path: Path | None = None) -> dict:
    path = path or (Path(os.environ["RK_WORK_DIR"]) / "trace" / "results.json")
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CounterfactualError(f"cannot read the trace document at {path}: {exc}")


def check_pins(doc: dict) -> dict:
    """Fail closed unless the document was produced by the pinned scorer and the pinned tracer.

    A counterfactual re-prices steps for an archive that was scored by one particular
    evaluator. If the trace document was generated against a different VERIFIER_HASH, its
    cycle counts and the archive's errors are not about the same thing, and the honest move
    is to refuse rather than to publish a ratio between them. The same holds for TRACE_HASH:
    a document whose producer has moved is not the document the pin describes.
    """
    gen = doc.get("generated_from") or {}
    checks = {
        "document_verifier_hash": str(gen.get("verifier_hash") or ""),
        "pinned_verifier_hash": verifier_hash.pinned_verifier_hash() or "",
        "computed_verifier_hash": verifier_hash.compute_verifier_hash(),
        "document_trace_hash": str(gen.get("trace_hash") or ""),
        "pinned_trace_hash": trace_hash.pinned_trace_hash() or "",
        "computed_trace_hash": trace_hash.compute_trace_hash(),
    }
    if checks["document_verifier_hash"] != checks["pinned_verifier_hash"]:
        raise CounterfactualError(
            "the trace document was generated under verifier hash "
            f"{checks['document_verifier_hash'][:12]} and the pin on disk is "
            f"{checks['pinned_verifier_hash'][:12]}: refusing to price archive scores "
            "against a different evaluator")
    if checks["pinned_verifier_hash"] != checks["computed_verifier_hash"]:
        raise CounterfactualError(
            "VERIFIER_HASH does not match the files it pins: refusing to run")
    if checks["document_trace_hash"] != checks["pinned_trace_hash"]:
        raise CounterfactualError(
            f"the trace document carries trace hash {checks['document_trace_hash'][:12]} "
            f"and the pin on disk is {checks['pinned_trace_hash'][:12]}: regenerate the "
            "document or restore the pin")
    if checks["pinned_trace_hash"] != checks["computed_trace_hash"]:
        raise CounterfactualError(
            "TRACE_HASH does not match the files it pins: refusing to run")
    return checks


def traced_prices(doc: dict, model_name: str = MODEL) -> tuple[dict[str, dict[int, int]], dict[str, str]]:
    """(tableau content hash -> {n_states: whole-step cycles}, hash -> the trace row's name).

    Joined by tableau content hash rather than by name, so a renamed or re-derived method
    cannot pick up another method's price.
    """
    prices: dict[str, dict[int, int]] = {}
    names: dict[str, str] = {}
    for row in doc.get("methods") or []:
        h = str(row.get("tableau_hash") or "")
        if not h:
            continue
        names[h] = str(row.get("name") or "")
        by_state: dict[int, int] = {}
        for key, block in sorted((row.get("state_scaling") or {}).items()):
            if not key.startswith("n"):
                continue
            cyc = ((block.get("cycles_per_step") or {}).get(model_name))
            if cyc is None:
                continue
            by_state[int(key[1:])] = int(cyc)
        prices[h] = by_state
    return prices, names


# ------------------------------------------------------------------------ scales

def scales(per_method: dict[str, dict[str, float]], anchor_names: tuple[str, ...]) -> dict[str, dict[str, float]]:
    """The two per-problem scales, both computed at the analytic basis.

    median_anchor is the median over the classical anchor field, which is what "equal
    weighting" has to mean when the errors have no common physical unit. reference_norm is
    the zero-state error, the value a method reports when its state collapses; it is
    published beside the median because the two disagree about the headline, and a reader
    who is shown only one cannot see that the scale choice decides the result.
    """
    median = {}
    norm = {}
    for name in ALL_PROBLEMS:
        vals = [per_method[m][name] for m in anchor_names
                if math.isfinite(per_method[m].get(name, _INF))]
        median[name] = statistics.median(vals) if vals else _INF
        p = PROBLEMS[name]
        norm[name] = error_metric(name, tuple(0.0 for _ in range(p.n_states)))
    return {"median_anchor": median, "reference_norm": norm}


def weight_fn_for(weighting: str, scale_set: dict[str, dict[str, float]]):
    if weighting == "magnitude":
        return None
    if weighting == "equal_median_anchor":
        return equal_weight(scale_set["median_anchor"])
    if weighting == "equal_reference_norm":
        return equal_weight(scale_set["reference_norm"])
    raise CounterfactualError(f"unknown weighting {weighting!r}")


# ----------------------------------------------------------------------- helpers

def _num(v):
    if v is None:
        return None
    f = float(v)
    return f if math.isfinite(f) else None


def _ranks(scores: dict[str, float]) -> dict[str, int]:
    """1 = lowest error. Ties broken by name, the convention key_findings already uses."""
    order = sorted(scores, key=lambda k: (scores[k], k))
    return {name: i + 1 for i, name in enumerate(order)}


def _shares(values: list[float]) -> list[float]:
    """Each value's share of the sum of squares. This is the weight an RMS actually gives."""
    sq = [v * v for v in values]
    total = sum(sq)
    if not (total > 0) or not math.isfinite(total):
        return [0.0 for _ in values]
    return [s / total for s in sq]


def _leave_one_out(champ_w: dict[str, float], anchors_w: dict[str, dict[str, float]]) -> list[dict]:
    """The champion against the best classical anchor, one held-out problem dropped.

    The anchor is re-chosen by minimum on every reduced set, over all eight anchors, which
    is what key_findings._leave_one_out does. Every anchor is traced, so the cost basis
    changes the numbers without changing which set the minimum is taken over.
    """
    rows = []
    for drop in (None,) + HELDOUT_PROBLEMS:
        kept = [p for p in HELDOUT_PROBLEMS if p != drop]
        champ = _rms([champ_w[p] for p in kept])
        ranked = sorted((_rms([anchors_w[a][p] for p in kept]), a) for a in sorted(anchors_w))
        err, name = ranked[0]
        rows.append({
            "dropped": drop,
            "problems_kept": kept,
            "champion_error": _num(champ),
            "best_anchor_name": name,
            "best_anchor_error": _num(err),
            "runner_up_anchor_name": ranked[1][1] if len(ranked) > 1 else None,
            "ratio": _num(err / champ) if champ else None,
        })
    return rows


# ------------------------------------------------------------------- the driver

def build(records, eff: dict, *, budget: int = BUDGET, model_name: str = MODEL,
          trace_path: Path | None = None) -> dict:
    """The whole counterfactual: two cost bases, three weightings, and the archive re-ranking."""
    doc = load_trace(trace_path)
    pins = check_pins(doc)
    prices, trace_names = traced_prices(doc, model_name)

    champ_tableau = from_json(eff["numbers"]["best_discovered"]["tableau"])
    champ_hash = content_hash(champ_tableau)
    if champ_hash != eff["numbers"]["best_discovered"]["tableau_hash"]:
        raise CounterfactualError("the champion tableau does not hash to its published hash")
    champ_name = trace_names.get(champ_hash) or champ_hash[:8]

    anchors = dict(sorted(classical().items()))
    anchor_names = tuple(sorted(anchors))
    methods: dict[str, object] = dict(anchors)
    methods[champ_name] = champ_tableau
    kinds = {n: "classical" for n in anchors}
    kinds[champ_name] = "discovered"

    untraced = sorted(n for n, t in methods.items() if content_hash(t) not in prices)
    if untraced:
        raise CounterfactualError(
            "these methods have no trace row and cannot be priced: " + ", ".join(untraced))

    problems_by_set = {"search": tuple(PROBLEMS[p] for p in SEARCH_PROBLEMS),
                       "heldout": tuple(PROBLEMS[p] for p in HELDOUT_PROBLEMS)}
    solve = memo(problem_error)
    steps_fns = {"analytic": analytic_steps(model_name, budget),
                 "traced_whole_step": traced_steps(prices, budget)}

    # raw[basis][method] -> {"per_problem", "steps"} over all seven problems, scored once.
    raw: dict[str, dict[str, dict]] = {}
    for basis in COST_BASES:
        raw[basis] = {}
        for name in sorted(methods):
            r = score(methods[name], tuple(PROBLEMS[p] for p in ALL_PROBLEMS),
                      steps_fn=steps_fns[basis], solve_fn=solve)
            raw[basis][name] = {"per_problem": r["per_problem"], "steps": r["steps"],
                                "overflowed": r["overflowed"]}

    scale_set = scales({m: raw["analytic"][m]["per_problem"] for m in methods}, anchor_names)

    # ------------------------------------------------ aggregates, every basis and weighting
    agg: dict[str, dict[str, dict]] = {}
    per_method_rows: list[dict] = []
    rows_by_key: dict[tuple, dict] = {}
    loo_rows: list[dict] = []
    share_sets = 0
    worst_share_deviation = 0.0

    for weighting in WEIGHTINGS:
        wf = weight_fn_for(weighting, scale_set)
        agg[weighting] = {}
        for basis in COST_BASES:
            cell = {"search": {}, "heldout": {}}
            weighted_by_method: dict[str, dict[str, float]] = {}
            for set_name, probs in sorted(problems_by_set.items()):
                errors, ranks_in = {}, {}
                for name in sorted(methods):
                    r = score(methods[name], probs, steps_fn=steps_fns[basis],
                              solve_fn=solve, weight_fn=wf)
                    errors[name] = r["aggregate"]
                    weighted_by_method.setdefault(name, {}).update(r["weighted"])
                    vals = [r["weighted"][p.name] for p in probs]
                    sh = _shares(vals)
                    if all(math.isfinite(v) for v in vals):
                        share_sets += 1
                        worst_share_deviation = max(worst_share_deviation, abs(sum(sh) - 1.0))
                    # One row per (basis, set, method, problem), carrying the share each
                    # weighting gives it. The error and the step count do not depend on the
                    # weighting, so repeating them three times would invite a reader to
                    # compare two rows that hold the same measurement.
                    for p, s in zip(probs, sh):
                        key = (basis, set_name, name, p.name)
                        row = rows_by_key.get(key)
                        if row is None:
                            row = {
                                "method": name, "kind": kinds[name], "basis": basis,
                                "set": set_name, "problem": p.name, "n_states": p.n_states,
                                "cycles_per_step": (
                                    cycle_count(methods[name], COST_MODELS[model_name], p.n_states)
                                    if basis == "analytic"
                                    else prices[content_hash(methods[name])][p.n_states]),
                                "steps": raw[basis][name]["steps"].get(p.name),
                                "error": _num(raw[basis][name]["per_problem"].get(p.name)),
                            }
                            rows_by_key[key] = row
                            per_method_rows.append(row)
                        row["share_" + weighting] = _num(s)
                ranks_in = _ranks(errors)
                four = {m: errors[m] for m in PUBLISHED_FOUR}
                cell[set_name] = {
                    "error": {m: _num(v) for m, v in sorted(errors.items())},
                    "rank": dict(sorted(ranks_in.items())),
                    "rank_within_published_four": dict(sorted(_ranks(four).items())),
                    "leader": min(sorted(errors), key=lambda m: (errors[m], m)),
                    "leader_within_published_four": min(sorted(four), key=lambda m: (four[m], m)),
                }
            champ_w = weighted_by_method[champ_name]
            anchors_w = {a: weighted_by_method[a] for a in anchor_names}
            rows = _leave_one_out(champ_w, anchors_w)
            for r in rows:
                loo_rows.append(dict(r, basis=basis, weighting=weighting))
            full = rows[0]
            ratios = [r["ratio"] for r in rows if r["ratio"] is not None]
            floor_row = min((r for r in rows if r["ratio"] is not None),
                            key=lambda r: (r["ratio"], r["dropped"] or ""))
            cell["heldout"].update({
                "champion_name": champ_name,
                "champion_error": full["champion_error"],
                "best_anchor_name": full["best_anchor_name"],
                "best_anchor_error": full["best_anchor_error"],
                "runner_up_anchor_name": full["runner_up_anchor_name"],
                "ratio": full["ratio"],
                "leave_one_out": rows,
                "lowest_leave_one_out_ratio": _num(min(ratios)) if ratios else None,
                "lowest_leave_one_out_dropped": floor_row["dropped"],
                "reduced_sets_where_an_anchor_leads":
                    sum(1 for r in rows[1:] if r["ratio"] is not None and r["ratio"] < 1.0),
                "champion_leads_on_every_reduced_set":
                    bool(ratios) and min(ratios) > 1.0,
            })
            agg[weighting][basis] = cell

    # --------------------------------------------------------------------- invariants
    published_loo = eff["numbers"].get("leave_one_out") or []
    mine = agg["magnitude"]["analytic"]["heldout"]["leave_one_out"]
    loo_diff, loo_names_agree = 0.0, len(published_loo) == len(mine)
    for a, b in zip(published_loo, mine):
        if a.get("dropped") != b.get("dropped") or a.get("best_anchor_name") != b.get("best_anchor_name"):
            loo_names_agree = False
        for key in ("champion_error", "best_anchor_error", "ratio"):
            if a.get(key) is not None and b.get(key) is not None:
                loo_diff = max(loo_diff, abs(a[key] - b[key]))

    pub = {a["name"]: a for a in eff["numbers"]["classical_anchors"]}
    pub[champ_name] = {"heldout_error": eff["numbers"]["best_discovered"]["heldout_error"],
                       "search_error": eff["numbers"]["best_discovered"]["search_error"]}
    rms_diff = 0.0
    for name in sorted(methods):
        per = raw["analytic"][name]["per_problem"]
        rms_diff = max(rms_diff,
                       abs(_rms([per[p] for p in HELDOUT_PROBLEMS]) - pub[name]["heldout_error"]),
                       abs(_rms([per[p] for p in SEARCH_PROBLEMS]) - pub[name]["search_error"]))

    steps_ok = True
    for basis in COST_BASES:
        for name in sorted(methods):
            for p_name in ALL_PROBLEMS:
                p = PROBLEMS[p_name]
                n = raw[basis][name]["steps"][p_name]
                cost = (cycle_count(methods[name], COST_MODELS[model_name], p.n_states)
                        if basis == "analytic" else prices[content_hash(methods[name])][p.n_states])
                if n != budget // cost:
                    steps_ok = False

    # The scales are analytic-basis constants, so a cell that changes both the cost basis
    # and the weighting measures traced-basis errors against an analytic-basis scale. One
    # of those cells reads oddly enough to need saying out loud, and the sentence is
    # generated so it cannot drift away from the numbers it describes.
    amp = min(HELDOUT_PROBLEMS, key=lambda p: (scale_set["median_anchor"][p], p))
    cross_basis_note = (
        f"{amp} has the smallest median anchor error of the four held-out problems at "
        f"{scale_set['median_anchor'][amp]:.3g}, so dividing by it amplifies any method "
        f"whose {amp} error rises when steps are taken away. The champion's {amp} error "
        f"goes from {raw['analytic'][champ_name]['per_problem'][amp]:.3g} at "
        f"{raw['analytic'][champ_name]['steps'][amp]:,} steps on the analytic basis to "
        f"{raw['traced_whole_step'][champ_name]['per_problem'][amp]:.3g} at "
        f"{raw['traced_whole_step'][champ_name]['steps'][amp]:,} steps on the traced one, "
        f"which is most of why the median anchor ratio falls below one there. Read that "
        f"cell as the metric magnifying one problem, not as the champion losing by that "
        f"factor.")

    fr_diff = _floor_round_crosscheck(raw["analytic"])
    rerank = archive_reranking(records, eff, scale_set, champ_hash, champ_name, anchors, model_name)

    excluded = _excluded(eff, prices)

    numbers = {
        "budget_cycles": budget,
        "cost_model": model_name,
        "cost_bases": {
            "analytic": ("costmodel.cycle_count, the basis every archived score was "
                         "computed under: the stage and b combinations only, scaled "
                         "linearly in state dimension"),
            "traced_whole_step": ("state_scaling.cycles_per_step from "
                                  "rk-work/trace/results.json: TRM-priced cycles for every "
                                  "instruction executed inside rk_step in one step, "
                                  "excluding the derivative routine's own body, measured at "
                                  "each of the four state counts the problem set uses"),
        },
        "weightings": {
            "magnitude": ("the pinned aggregate, an unweighted RMS of the per-problem "
                          "errors, so a problem's influence grows with the square of its "
                          "error"),
            "equal_median_anchor": ("each error divided by the median error of the eight "
                                    "classical anchors on that problem before the RMS. This "
                                    "is the equal-weighting answer"),
            "equal_reference_norm": ("each error divided by the zero-state error of that "
                                     "problem before the RMS. Published as the counterexample: "
                                     "it concentrates weight on rc_thermal rather than "
                                     "equalizing it"),
        },
        "scales": {k: {p: _num(v) for p, v in sorted(s.items())} for k, s in sorted(scale_set.items())},
        "scale_note": (
            "Both scales are constants of the analytic basis, so a weighting comparison and "
            "a cost comparison never move together. reference_norm is error_metric(name, "
            "zeros), which equals the reference norm over peak for the five distance "
            "problems and is 1 for pendulum and quaternion, whose metrics are already "
            "relative drifts."),
        "scope": {
            "basis_scope": ("whole rk_step, derivative body excluded. Neither basis is the "
                            "full per-step cost on a part: the analytic model prices less "
                            "than the traced count, the traced count prices less than a real "
                            "application step, and the pair is a bracket rather than a "
                            "correction"),
            "arithmetic": ("the emulator that produced the traced counts is instruction "
                           "accurate and not cycle accurate; every cycle number comes from "
                           "applying the Cortex-M0+ TRM table to that instruction stream "
                           "offline, and none was measured on a physical part"),
            "budget_basis_not_model_error": (
                "the traced count is used here only as a budget denominator, because a real "
                "part pays those cycles out of the same 65,536. Quoting it against the "
                "analytic count as a ratio would report a scope difference as a model error, "
                "which CLAUDE.md and D42 forbid and D43 keeps forbidden"),
            "selection_bias": (
                "the champion was selected under magnitude weighting out of every candidate "
                "the archive holds, so an equal-weighted ratio for that same champion "
                "describes the metric and not the search. archive_reranking is the part that "
                "answers what the search would have kept"),
            "weighting_under_a_changed_cost_basis": cross_basis_note,
        },
        "provenance": {
            "trace_document": "rk-work/trace/results.json",
            "trace_hash": pins["document_trace_hash"],
            "verifier_hash": pins["document_verifier_hash"],
            "methods_priced": sorted(trace_names.values()),
            "state_counts_priced": sorted({n for by in prices.values() for n in by}),
        },
        "methods": [
            {"name": n, "kind": kinds[n], "tableau_hash": content_hash(methods[n]),
             "trace_row": trace_names.get(content_hash(methods[n])),
             "stages": len(methods[n].b),
             "cycles_analytic": {f"n{s}": cycle_count(methods[n], COST_MODELS[model_name], s)
                                 for s in sorted({p.n_states for p in PROBLEMS.values()})},
             "cycles_traced_whole_step": {f"n{k}": v for k, v in
                                          sorted(prices[content_hash(methods[n])].items())}}
            for n in sorted(methods)],
        "excluded": excluded,
        "search_set": {w: {b: agg[w][b]["search"] for b in COST_BASES} for w in WEIGHTINGS},
        "heldout": {w: {b: agg[w][b]["heldout"] for b in COST_BASES} for w in WEIGHTINGS},
        "headline_checks": _headline_checks(agg, eff),
        "archive_reranking": rerank,
        "invariants": {
            "published_leave_one_out_reproduced": bool(loo_names_agree and loo_diff <= 1e-12),
            "published_leave_one_out_max_abs_diff": _num(loo_diff),
            "rms_reconstruction_max_abs_diff": _num(rms_diff),
            "floor_round_crosscheck_max_rel_diff": _num(fr_diff),
            "share_sets_checked": share_sets,
            "share_sum_max_deviation_from_one": _num(worst_share_deviation),
            "every_step_count_is_the_budget_division": steps_ok,
            "archive_rms_reconstruction_max_abs_diff": rerank["reconstruction_max_abs_diff"],
            "note": ("Each invariant is recomputed here from the per-problem values rather "
                     "than read back, so a generator that drifts fails the build instead of "
                     "publishing."),
        },
    }
    return {"verdict": _verdict(numbers["headline_checks"], rerank, champ_name),
            "numbers": numbers,
            "series": {"per_method": per_method_rows,
                       "leave_one_out": loo_rows,
                       "archive_top": rerank["top"],
                       "dahlquist_final_state": _dahlquist_final_state(methods, kinds, raw),
                       "chart_hint": ("grouped bars per method, one group per cost basis, "
                                      "log y; a second chart per weighting for the five "
                                      "leave-one-out ratios with a line at 1.0")}}


def _floor_round_crosscheck(raw_analytic: dict[str, dict]) -> float:
    """Recompute tools/floor_round.json's floor side from this module's own solves.

    floor_round.json is where finding 2's published search errors come from, so a
    counterfactual that cannot reproduce it is not scoring the same thing the page shows.
    """
    path = HERE / "floor_round.json"
    try:
        fr = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return _INF
    worst = 0.0
    for name, row in sorted((fr.get("floor") or {}).items()):
        if name not in raw_analytic:
            continue
        for p, want in sorted(row.items()):
            got = raw_analytic[name]["per_problem"].get(p)
            if got is None or not math.isfinite(got):
                return _INF
            worst = max(worst, abs(got - want) / max(abs(want), 1e-300))
    return worst


def _excluded(eff: dict, prices: dict[str, dict[int, int]]) -> dict:
    """Name the gap rather than filling it with a model."""
    rows = []
    for row in eff["series"]["frontier_cycles_vs_heldout"]:
        if row.get("kind") != "discovered" or row.get("tableau_hash") in prices:
            continue
        rows.append({"tableau_hash": str(row.get("tableau_hash"))[:12],
                     "cycles": row.get("cycles"),
                     "heldout_error": row.get("heldout_error")})
    rows.sort(key=lambda r: (r["cycles"] if r["cycles"] is not None else 0, r["tableau_hash"]))
    return {
        "methods_without_a_trace_row": rows,
        "state_counts_without_a_traced_price": [],
        "note": ("Every method in the cost counterfactual has a trace row and every state "
                 f"count the problem set uses is priced, so nothing is extrapolated. The "
                 f"{len(rows)} discovered cell elites above hold a cell but were never "
                 "compiled and traced, so they are named here and left out of the cost "
                 "counterfactual rather than priced by a fit. They are not excluded from "
                 "the archive re-ranking, which changes only the aggregate and re-prices "
                 "nothing."),
    }


def _headline_checks(agg: dict, eff: dict) -> dict:
    """The plain statements the acceptances ask for, generated rather than typed."""
    published = agg["magnitude"]["analytic"]["heldout"]
    out = {
        "published_ratio": published["ratio"],
        "published_lowest_leave_one_out_ratio": published["lowest_leave_one_out_ratio"],
        "published_search_leader": agg["magnitude"]["analytic"]["search"]["leader_within_published_four"],
        "cells": [],
    }
    for weighting in WEIGHTINGS:
        for basis in COST_BASES:
            h = agg[weighting][basis]["heldout"]
            s = agg[weighting][basis]["search"]
            out["cells"].append({
                "weighting": weighting,
                "basis": basis,
                "ratio": h["ratio"],
                "ratio_moves_by": (_num(h["ratio"] / published["ratio"])
                                   if h["ratio"] and published["ratio"] else None),
                "champion_still_leads": h["champion_leads_on_every_reduced_set"],
                "lowest_leave_one_out_ratio": h["lowest_leave_one_out_ratio"],
                "lowest_leave_one_out_dropped": h["lowest_leave_one_out_dropped"],
                "reduced_sets_where_an_anchor_leads": h["reduced_sets_where_an_anchor_leads"],
                "search_leader_of_nine": s["leader"],
                "search_leader_of_published_four": s["leader_within_published_four"],
                "euler_rank_of_nine": s["rank"]["euler"],
                "euler_rank_of_published_four": s["rank_within_published_four"]["euler"],
                "euler_keeps_rank_1_in_the_published_four":
                    s["rank_within_published_four"]["euler"] == 1,
            })
    return out


def archive_reranking(records, eff: dict, scale_set: dict, champ_hash: str, champ_name: str,
                      anchors: dict, model_name: str) -> dict:
    """Re-aggregate every archived record's stored per-problem errors under equal weighting.

    No simulation: every record already carries its four held-out errors, so this is the same
    numbers added up a different way. It answers the question the ratio alone cannot, which is
    which tableau the archive would have kept if the aggregate had weighted the problems
    equally. It is an analytic-basis result, because that is the basis the stored errors were
    computed under; re-pricing steps would require re-running the archive.
    """
    classical_hashes = {content_hash(t): n for n, t in anchors.items()}
    best: dict[str, dict] = {}
    n_scanned = 0
    n_skipped = 0
    recon = 0.0
    inconsistent = 0
    for r in records:
        vals = [r.score.per_problem.get(p) for p in HELDOUT_PROBLEMS]
        if any(v is None or not math.isfinite(v) for v in vals):
            n_skipped += 1
            continue
        n_scanned += 1
        if math.isfinite(r.score.heldout_error):
            recon = max(recon, abs(_rms(vals) - r.score.heldout_error))
        row = {"tableau_hash": r.tableau_hash,
               "kind": "classical" if r.tableau_hash in classical_hashes else "discovered",
               "name": classical_hashes.get(r.tableau_hash),
               "stages": len(r.tableau.b),
               "cycles": r.score.cycles.get(model_name),
               "tier": r.tier,
               "measured_order": _num(r.score.measured_order),
               "magnitude": _rms(vals)}
        for key, scale in sorted(scale_set.items()):
            row["equal_" + key] = _rms([v / scale[p] for v, p in zip(vals, HELDOUT_PROBLEMS)])
        seen = best.get(r.tableau_hash)
        if seen is None:
            best[r.tableau_hash] = row
        else:
            if abs(seen["magnitude"] - row["magnitude"]) > 1e-12:
                inconsistent += 1
            if row["magnitude"] < seen["magnitude"]:
                best[r.tableau_hash] = row

    rows = sorted(best.values(), key=lambda d: d["tableau_hash"])
    out = {
        "records_scanned": n_scanned,
        "records_skipped_for_a_non_finite_error": n_skipped,
        "unique_tableaus_ranked": len(rows),
        "reconstruction_max_abs_diff": _num(recon),
        "tableaus_whose_records_disagree": inconsistent,
        "champion_tableau_hash": champ_hash[:12],
        "basis": "analytic",
        "note": ("A re-aggregation of stored per-problem errors over every archived record, "
                 "reduced to one row per unique tableau. No step count and no solve changes, "
                 "so this is the same data under a different aggregate."),
        "by_weighting": {},
        "top": [],
    }
    for key, field in (("magnitude", "magnitude"),
                       ("equal_median_anchor", "equal_median_anchor"),
                       ("equal_reference_norm", "equal_reference_norm")):
        ranked = sorted(rows, key=lambda d: (d[field], d["tableau_hash"]))
        rank_of = {d["tableau_hash"]: i + 1 for i, d in enumerate(ranked)}
        winner = ranked[0]
        out["by_weighting"][key] = {
            "winner_tableau_hash": winner["tableau_hash"][:12],
            "winner_kind": winner["kind"],
            "winner_name": winner["name"],
            "winner_cycles": winner["cycles"],
            "winner_error": _num(winner[field]),
            "winner_is_the_published_champion": winner["tableau_hash"] == champ_hash,
            "published_champion_rank": rank_of.get(champ_hash),
            "tableaus_ahead_of_the_published_champion": rank_of.get(champ_hash, 1) - 1,
            "classical_anchors_ahead_of_the_champion": sum(
                1 for d in ranked[:rank_of.get(champ_hash, 1) - 1] if d["kind"] == "classical"),
        }
        for i, d in enumerate(ranked[:10]):
            out["top"].append({
                "weighting": key, "rank": i + 1,
                "tableau_hash": d["tableau_hash"][:12], "kind": d["kind"], "name": d["name"],
                "stages": d["stages"], "cycles": d["cycles"], "tier": d["tier"],
                "measured_order": d["measured_order"],
                "error": _num(d[field]),
                "is_the_published_champion": d["tableau_hash"] == champ_hash,
            })
    return out


def _dahlquist_final_state(methods: dict, kinds: dict, raw: dict) -> list[dict]:
    """Each scored method's final Q15 state on dahlquist, on the analytic basis.

    The overview's index says every method in this field ends within a few Q15 steps of
    zero on dahlquist, and that number has to come from a document rather than from a solve
    run while a page is being written. The rows follow rc_thermal_collapse's per_method
    shape. Each one is checked against the counterfactual's own analytic solve before it is
    written: the step count must be the one that solve used, and the error the pinned metric
    gives for this final state must be the error that solve reported, bit for bit.
    """
    p = PROBLEMS["dahlquist"]
    rows = []
    for name in sorted(methods):
        n = raw["analytic"][name]["steps"]["dahlquist"]
        final, _max_abs = solve_q15(methods[name], p, n)
        err = error_metric("dahlquist", to_physical(final, p.scale))
        want = raw["analytic"][name]["per_problem"]["dahlquist"]
        if err != want:
            raise CounterfactualError(
                f"{name}'s final dahlquist state gives error {err!r} and the analytic solve "
                f"reported {want!r}: the two are not the same run")
        rows.append({"method": name, "kind": kinds[name], "basis": "analytic", "steps": n,
                     "final_state_q15": [int(q) for q in final],
                     "final_state_lsbs_from_origin": max(abs(int(q)) for q in final),
                     "error": _num(err)})
    return rows


_WORDS = {"magnitude": "magnitude weighting",
          "equal_median_anchor": "median-anchor equal weighting",
          "equal_reference_norm": "the reference-norm scale"}
_BASIS_WORDS = {"analytic": "the analytic basis",
                "traced_whole_step": "the traced whole-step basis"}


def _verdict(checks: dict, rerank: dict, champ_name: str) -> str:
    """The finding's one-paragraph statement, written from headline_checks.

    Every clause is chosen by the numbers it describes, so it stays true in every cell it
    names. An earlier version said the weighting decided the headline and the cost basis
    did not, while the same document had the traced basis taking the published weighting's
    lead from 2.95x to 1.01x with an anchor ahead on three of the four reduced sets.
    """
    cells = checks["cells"]
    pub = next(c for c in cells
               if (c["weighting"], c["basis"]) == ("magnitude", "analytic"))
    others = [c for c in cells if c is not pub]

    def name(c):
        return f"{_WORDS[c['weighting']]} on {_BASIS_WORDS[c['basis']]}"

    keep = [c for c in others if c["ratio"] > 1.0 and c["reduced_sets_where_an_anchor_leads"] == 0]
    partial = [c for c in others if c["ratio"] > 1.0 and c["reduced_sets_where_an_anchor_leads"] > 0]
    behind = [c for c in others if c["ratio"] <= 1.0]
    lead = (f"Under {name(pub)} the champion's held-out error is {pub['ratio']:.4f}x lower than "
            f"the best classical anchor's, and it stays lower on "
            + ("every reduced set" if pub["reduced_sets_where_an_anchor_leads"] == 0
               else f"{4 - pub['reduced_sets_where_an_anchor_leads']} of the four reduced sets")
            + f". Of the {len(others)} other cells of the grid,")
    bits = []
    if keep:
        bits.append(f" {len(keep)} {'keeps' if len(keep) == 1 else 'keep'} a lead on the full "
                    "set and on every reduced set ("
                    + "; ".join(f"{name(c)}, {c['ratio']:.4f}x" for c in keep) + ")")
    if partial:
        bits.append(f" {len(partial)} {'keeps' if len(partial) == 1 else 'keep'} a lead on the "
                    "full set while an anchor leads on at least one reduced set ("
                    + "; ".join(f"{name(c)}, {c['ratio']:.4f}x with an anchor ahead on "
                                f"{c['reduced_sets_where_an_anchor_leads']} of 4"
                                for c in partial) + ")")
    if behind:
        bits.append(f" in {len(behind)} the anchor leads on the full set ("
                    + "; ".join(f"{name(c)}, {c['ratio']:.4f}x" for c in behind) + ")")
    # A switch "moves the result" when changing it alone, with the other left at the
    # published setting, loses either published claim.
    weight_alone = [c for c in partial + behind if c["basis"] == "analytic"]
    basis_alone = [c for c in partial + behind if c["weighting"] == "magnitude"]
    closing = {(True, True): " Changing the weighting alone or the cost basis alone each "
                             "loses a published claim in at least one cell.",
               (True, False): " Changing the weighting alone loses a published claim; "
                              "changing the cost basis alone does not.",
               (False, True): " Changing the cost basis alone loses a published claim; "
                              "changing the weighting alone does not.",
               (False, False): ""}[(bool(weight_alone), bool(basis_alone))]
    lead += ",".join(bits) + "." + closing
    s_pub = pub["search_leader_of_published_four"]
    keeps_rank = [c for c in cells if c["search_leader_of_published_four"] == s_pub]
    search = (f" On the search set, {s_pub} has the lowest error of the four published methods "
              + ("only under " + name(pub) if keeps_rank == [pub]
                 else "under " + "; ".join(name(c) for c in keeps_rank))
              + ".")
    who = rerank["by_weighting"]
    rank = "; ".join(f"under {_WORDS[w]} it is rank {who[w]['published_champion_rank']:,}"
                     for w in ("magnitude", "equal_median_anchor", "equal_reference_norm"))
    rer = (f" Re-aggregating all {rerank['records_scanned']:,} archived records on the analytic "
           f"basis ranks {rerank['unique_tableaus_ranked']:,} unique tableaus: {rank}. The "
           f"champion was selected under magnitude weighting, so the other two columns describe "
           f"the metric rather than the search that produced {champ_name}.")
    return lead + search + rer
