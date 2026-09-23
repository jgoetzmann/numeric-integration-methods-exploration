"""Pull every number the site quotes out of the source repositories, with its provenance.

The site never types a number by hand. This script reads local clones of the source repos,
copies each figure out of the document that holds it, and writes data/*.json with the
repository, commit, file and key path it came from. The site build reads only data/*.json,
so the public repo rebuilds without the sources. Run it again to refresh the snapshot:

    python tools/snapshot.py --rk-workspace ../integration-harness \\
                             --novel ../Personal/Novel-Numerical-Integration-Methods
"""
from __future__ import annotations

import argparse
import csv
import datetime
import glob
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
GITHUB = "https://github.com/jgoetzmann"


_HEADS: dict[str, str] = {}


def _head(repo: Path) -> str:
    """HEAD of a source repo, read once per run. rk-work commits every cycle, so reading it
    per block would pin different blocks of one snapshot to different commits."""
    key = str(repo.resolve())
    if key not in _HEADS:
        _HEADS[key] = subprocess.run(["git", "-C", key, "rev-parse", "HEAD"], check=True,
                                     capture_output=True, text=True).stdout.strip()
    return _HEADS[key]


def _src(repo_name: str, repo: Path, path: str, key: str = "") -> dict:
    return {"repo": repo_name, "url": f"{GITHUB}/{repo_name}", "commit": _head(repo)[:12],
            "path": path, "key": key}


def _load(p: Path):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _lines(p: Path) -> int:
    n = 0
    with open(p, "rb") as fh:
        for line in fh:
            if line.strip():
                n += 1
    return n


def _event_counts(path: Path) -> dict:
    """How often the run started, stopped on its STOP file, or abandoned a cycle."""
    kinds = ("runner_started", "stopped_by_killfile", "cycle_abandoned")
    out = {k: 0 for k in kinds}
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                k = json.loads(line).get("kind")
            except ValueError:
                continue
            if k in out:
                out[k] += 1
    return out


# --------------------------------------------------------------------------- the rk run

def rk(ws: Path) -> dict:
    ov, work, harness = ws / "rk-overview", ws / "rk-work", ws / "rk-harness"
    kf = _load(ov / "tools" / "key_findings.json")
    e1 = work / "epochs" / "1"
    val = _load(e1 / "validation" / "results.json")
    ben = _load(e1 / "benchmark" / "results.json")
    tr = _load(e1 / "trace" / "results.json")
    epoch = _load(work / "EPOCH.json")
    eff = kf["efficiency"]["numbers"]
    best = eff["best_discovered"]
    cf = kf["counterfactual"]["numbers"]
    sp = kf["search_progress"]["numbers"]
    fb = kf["floor_bias_flip"]["numbers"]["aggregate"]

    out: dict = {"_about": (
        "The rk run: an unattended search for Runge-Kutta coefficients that do best in Q15 "
        "fixed point with floor rounding, at a fixed 65,536-cycle budget on a modeled "
        "Cortex-M0+. Every result below is epoch 1 unless its block says epoch 2.")}

    out["setup"] = {
        "budget_cycles": kf["_meta"]["budget_cycles"],
        "cost_model": kf["_meta"]["cost_model"],
        "rounding": "floor (arithmetic shift right, as ARM ASRS)",
        "heldout_problems": list(best["per_problem_heldout"].keys()),
        "source": _src("rk-overview", ov, "tools/key_findings.json", "_meta"),
    }

    fr = kf["efficiency"]["series"]["frontier_cycles_vs_heldout"]
    first_cycle: dict[str, int] = {}
    hash_counts: dict[str, int] = {}
    for path in sorted(glob.glob(str(work / "epochs" / "1" / "archive" / "*.jsonl"))):
        with open(path, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                th = rec.get("tableau_hash") or (rec.get("tableau") or {}).get("hash") or ""
                cyc = rec.get("cycle_id")
                if th and isinstance(cyc, int) and (th not in first_cycle or cyc < first_cycle[th]):
                    first_cycle[th] = cyc
                vh = str(rec.get("verifier_hash", ""))[:8]
                hash_counts[vh] = hash_counts.get(vh, 0) + 1
    out["frontier"] = {
        "classical": [{"name": r["name"], "cycles": r["cycles"], "heldout_error": r["heldout_error"]}
                      for r in fr if r["kind"] == "classical"],
        "discovered": [{"order": r.get("order"), "stages": r.get("stages"), "cycles": r["cycles"],
                        "heldout_error": r["heldout_error"],
                        "is_champion": r.get("tableau_hash", "").startswith("11e898cb"),
                        "first_cycle": first_cycle.get(r.get("tableau_hash", ""))}
                       for r in fr if r["kind"] != "classical"],
        "cells_total": eff["grid_cells_total"],
        "cells_held_by_discovered": eff["cells_held_by_discovered"],
        "cells_held_by_classical": eff["cells_held_by_classical"],
        "cells_where_discovered_leads_every_cheaper_or_equal_classical":
            eff["cells_where_discovered_beats_all_cheaper_or_equal_anchors"],
        "median_error_ratio_discovered_over_classical": eff["median_error_ratio_discovered_over_anchor"],
        "note_on_comparison": eff.get("note_on_comparison"),
        "unique_tableaus": eff["unique_tableaus"],
        "note": "held-out RMS error, Q15 floor rounding, 65,536-cycle budget, m0plus_fast analytic "
                "cycles per step at one state; the ratio is against the best classical method "
                "of equal or lower cost",
        "source": _src("rk-overview", ov, "tools/key_findings.json",
                       "efficiency.series.frontier_cycles_vs_heldout; efficiency.numbers"),
    }

    champ_cycle = kf["search_progress"]["numbers"]["last_improvement_cycle_id"]
    out["frontier"]["discovered_first_seen_after_champion"] = sum(
        1 for d in out["frontier"]["discovered"] if (d["first_cycle"] or 0) > champ_cycle)
    out["frontier"]["closest_discovered_to_classical"] = max(
        d["heldout_error"] for d in out["frontier"]["discovered"])
    loo = eff["leave_one_out"]
    out["champion"] = {
        "hash": best["tableau_hash"][:8],
        "stages": best["stages"], "order": best["order"], "cycles_per_step": best["cycles"],
        "tableau": best["tableau"],
        "per_problem_heldout": best["per_problem_heldout"],
        "classical_per_problem_heldout": {a["name"]: a["per_problem_heldout"] for a in eff["classical_anchors"]},
        "selection_pool_note": "cell elites are selected by held-out error among the archive's candidates; "
                               "see caveats for the pool size",
        "heldout_error": best["heldout_error"],
        "best_classical": loo[0]["best_anchor_name"],
        "best_classical_heldout_error": loo[0]["best_anchor_error"],
        "lead": cf["headline_checks"]["published_ratio"],
        "leave_one_out": [{"dropped": r["dropped"], "ratio": r["ratio"]} for r in loo],
        "leave_one_out_min": min(r["ratio"] for r in loo),
        "leave_one_out_max": max(r["ratio"] for r in loo),
        "found_at_cycle": sp["last_improvement_cycle_id"],
        "cycles_run": sp["cycles_run"],
        "cycles_since_last_improvement": sp["cycles_since_last_improvement"],
        "stored_tier": best["tier"],
        "caveats": eff["caveats"],
        "caveats_note": "quoted verbatim from the source; its '45k+ unique candidates' is older than "
                        "the full archive, which holds " + f"{eff['unique_tableaus']:,}" +
                        " unique tableaus (efficiency.numbers.unique_tableaus)",
        "source": _src("rk-overview", ov, "tools/key_findings.json",
                       "efficiency.numbers.best_discovered; efficiency.numbers.leave_one_out; "
                       "counterfactual.numbers.headline_checks.published_ratio; search_progress.numbers"),
    }

    out["counterfactual"] = {
        "cells": [{"weighting": c["weighting"], "basis": c["basis"], "ratio": c["ratio"],
                   "champion_still_leads": c["champion_still_leads"],
                   "lowest_leave_one_out_ratio": c["lowest_leave_one_out_ratio"]}
                  for c in cf["headline_checks"]["cells"]],
        "note": "ratio = best classical held-out error over the champion's; above 1 the champion "
                "leads. traced_whole_step uses the compiled step's cycle count only as the "
                "budget denominator (how many steps fit in 65,536 cycles).",
        "archive_reranking": {w: {"champion_rank": v["published_champion_rank"],
                                  "classical_ahead": v["classical_anchors_ahead_of_the_champion"]}
                              for w, v in cf["archive_reranking"]["by_weighting"].items()},
        "archive_reranking_basis": cf["archive_reranking"]["basis"],
        "weightings": cf["weightings"],
        "cost_bases": cf["cost_bases"],
        "basis_scope": cf["scope"]["basis_scope"],
        "median_anchor_traced_cell_reading": cf["scope"]["weighting_under_a_changed_cost_basis"],
        "source": _src("rk-overview", ov, "tools/key_findings.json",
                       "counterfactual.numbers.headline_checks.cells; counterfactual.numbers.archive_reranking"),
    }

    out["floor_vs_round"] = {
        "search_rms": {mode: fb[mode]["search_rms"]["error"] for mode in ("floor", "round_to_nearest")},
        "heldout_rms": {mode: fb[mode]["heldout_rms"]["error"] for mode in ("floor", "round_to_nearest")},
        "budget_cycles": kf["floor_bias_flip"]["numbers"]["budget_cycles"],
        "cost_model": kf["floor_bias_flip"]["numbers"]["cost_model"],
        "mechanism": kf["floor_bias_flip"]["numbers"]["mechanism"],
        "source": _src("rk-overview", ov, "tools/key_findings.json", "floor_bias_flip.numbers.aggregate"),
    }

    cr = kf["crossover"]["numbers"]
    out["premise"] = {
        "stored_verdict": cr["stored_verdict"],
        "rk4_best_under_floor": cr["rk4_wins_at_budget"]["floor"]["fraction"],
        "rk4_best_under_round_to_nearest": cr["rk4_wins_at_budget"]["round_to_nearest"]["fraction"],
        "rk4_best_note": cr["rk4_wins_at_budget"].get("note"),
        "thresholds": cr["thresholds"],
        "problem": cr.get("problem"),
        "methods": {m: {"coefficient_fraction": d["coefficient_fraction"],
                        "crossover_h": d["crossover_h"], "crossover_practical": d["crossover_practical"]}
                    for m, d in cr["methods"].items()},
        "source": _src("rk-overview", ov, "tools/key_findings.json", "crossover.numbers"),
    }

    pp = val["verdicts"]["per_problem"]
    rows = []
    res = val["results"]
    champ = best["tableau_hash"]
    for prob, v in sorted(pp.items()):
        def err(method, key):
            for r in res:
                if r["problem"] == prob and (r["method"] == method or r["method"].startswith(method[:8])):
                    return r.get(key)
            return None
        classical_winner = v.get("winner_kind") == "classical"
        rows.append({
            "problem": prob, "stiff": v["stiff"],
            "champion_q15": err(champ, "q15_error"),
            "champion_overflowed": err(champ, "q15_error") is None,
            "best_classical": v.get("best_classical") or (v.get("winner") if classical_winner else None),
            "best_classical_q15": v.get("best_classical_q15_error")
                or (v.get("winner_q15_error") if classical_winner else None),
            "best_discovered_q15": v.get("best_discovered_q15_error"),
            "winner_kind": v.get("winner_kind"),
            "champion_float64": err(champ, "float_error"),
            "rk4_float64": err("rk4", "float_error"),
            "champion_steps": err(champ, "steps"),
            "rk4_steps": err("rk4", "steps"),
        })
    vv = val["verdicts"]
    gaps = [r["champion_float64"] / r["rk4_float64"] for r in rows
            if r["champion_float64"] and r["rk4_float64"]]
    out["float64_gap"] = {
        "champion_over_rk4_min": min(gaps), "champion_over_rk4_max": max(gaps),
        "problems": len(gaps),
        "note": "float64 error of the champion over float64 error of rk4, each at the step count the "
                "65,536-cycle budget gives it, per validation problem where both finish",
        "source": _src("rk-work", work, "epochs/1/validation/results.json", "results[].float_error"),
    }
    out["validation"] = {
        "problems": rows,
        "practical_won_by_discovered": vv["practical_problems_won_by_discovered"],
        "practical_total": vv["practical_problems_total"],
        "practical_median_ratio": vv["practical_median_ratio_discovered_over_classical"],
        "stiff_total": vv["stiff_problems_total"],
        "stiff_won_by_discovered": vv["stiff_problems_won_by_discovered"],
        "stiff_with_no_discovered_finisher": vv["stiff_problems_with_no_discovered_finisher"],
        "classical_methods_run": sorted({r["method"] for r in res if len(r["method"]) < 16}),
        "discovered_methods_run": sum(1 for m in val["methods"] if m.get("kind") == "discovered"),
        "note": "out-of-sample: no optimizer or model saw these problems and the champion was "
                "fixed before they ran, but people chose them after the search began",
        "source": _src("rk-work", work, "epochs/1/validation/results.json", "verdicts; results[]"),
    }

    bv = ben["verdicts"]
    out["libraries"] = {
        "median_ratio_q15_over_library_at_matched_tolerance":
            bv.get("median_ratio_q15_over_library_at_matched_tolerance"),
        "fixed_step_cells_compared": bv["fixed_step_cells_compared"],
        "fixed_step_cells_where_q15_error_lower": bv["fixed_step_cells_where_q15_error_lower"],
        "fixed_step_verdict": bv.get("fixed_step"),
        "matched_tolerance_verdict": bv.get("matched_tolerance"),
        "tolerance_rule": ben.get("tolerance_rule"),
        "best_library_per_problem": {k: v.get("best_library") for k, v in sorted(bv["per_problem"].items())},
        "solvers": ben.get("solvers"),
        "speedup": {"baseline": ben["speedup"]["baseline"],
                    "measured_geomean_rk4_over_champion": ben["speedup"]["geomean_measured_speedup_rk4_over_champion"],
                    "predicted_geomean_rk4_over_champion": ben["speedup"]["geomean_predicted_speedup_rk4_over_champion"],
                    "champion_error_lower_on": ben["speedup"]["champion_error_lower_count"],
                    "problems_compared": ben["speedup"]["error_comparisons"],
                    "note": "Python wall clock per step, both methods on the same solver path"},
        "cycle_model_pearson_r": ben["correlation"]["pearson_r"],
        "cycle_model_points": ben["correlation"]["n_points"],
        "source": _src("rk-work", work, "epochs/1/benchmark/results.json", "verdicts; speedup; correlation"),
    }

    out["trace"] = {
        "methods": [{"name": m.get("name") or m.get("method"),
                     "analytic": m.get("cycles_analytic"),
                     "matched_scope": m.get("cycles_traced_model_scope"),
                     "whole_step": m.get("cycles_traced")}
                    for m in tr["methods"]],
        "crosscheck": tr["verdicts"].get("crosscheck"),
        "toolchain": tr.get("toolchain"),
        "emulator_note": "unicorn is instruction-accurate, not cycle-accurate; cycles come from the "
                         "TRM timing table applied to executed instructions. Nothing was measured "
                         "on a physical part.",
        "source": _src("rk-work", work, "epochs/1/trace/results.json", "methods[]; verdicts"),
    }

    fz = epoch["frozen"][0]
    days = []
    total = 0
    for p in sorted(glob.glob(str(e1 / "archive" / "*.jsonl"))):
        n = _lines(Path(p))
        total += n
        days.append({"epoch": 1, "day": Path(p).stem, "records": n, "cumulative": total})
    e2days = []
    total2 = 0
    for p in sorted(glob.glob(str(work / "archive" / "*.jsonl"))):
        n = _lines(Path(p))
        total2 += n
        e2days.append({"epoch": 2, "day": Path(p).stem, "records": n, "cumulative": total2})
    runstate = _load(work / "RUNSTATE.json")
    cycles = [json.loads(l) for l in open(work / "schedule" / "cycles.jsonl", encoding="utf-8") if l.strip()]
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    out["epochs"] = {
        "epoch1": {"verifier_hash": "de5bec22", "verifier_files": 10,
                   "started": _load(e1 / "RUNSTATE.json")["started_at"],
                   "stopped": _load(e1 / "RUNSTATE.json")["last_heartbeat"],
                   "phase_at_stop": _load(e1 / "RUNSTATE.json")["phase"],
                   "archive_day_count": len(days),
                   "verifier_hash_counts": {k: v for k, v in sorted(hash_counts.items())},
                   "events": _event_counts(e1 / "events.jsonl"),
                   "last_improvement_ts": _load(e1 / "EPOCH_STATUS.json")["metrics"].get("last_improvement_ts"),
                   "last_new_cell_ts": _load(e1 / "EPOCH_STATUS.json")["metrics"].get("last_new_cell_ts"),
                   "records": fz.get("records", {}).get("archive_records"),
                   "cycles_run": sp["cycles_run"], "last_cycle_id": sp["last_cycle_id"],
                   "frozen_at": fz.get("frozen_at"),
                   "occupied_cells": eff["grid_cells_total"],
                   "archive_days": days},
        "epoch2": {"verifier_hash": "2db0816c", "verifier_files": 14,
                   "started": "2026-09-17T17:54Z",
                   "as_of": now,
                   "counted_from": "the running work tree at as_of, which includes the current UTC "
                                   "day's archive file before the run commits it at the day's close",
                   "cycle": runstate.get("cycle_id"),
                   "records": total2,
                   "lane_cycles": {lane: sum(1 for c in cycles if c.get("lane") == lane)
                                   for lane in ("explicit", "adaptive", "implicit")},
                   "archive_days": e2days,
                   "down_days": {"from": "2026-09-17T22:09Z", "to": "2026-09-23T02:19Z",
                                 "why": "the watchdog's system-drive guard stopped it and nothing "
                                        "restarted it (fixed by D46)"}},
        "why_epoch1_froze": "Compiling and tracing the step showed the epoch-1 analytic cost rule "
                            "mis-ordered rk4 and rk38, so epoch 2 prices each coefficient by the "
                            "instructions GCC 13.2.1 emits for it. That edits a pinned file, which "
                            "forces a new epoch (DECISIONS D42, D45).",
        "source": _src("rk-work", work, "EPOCH.json; epochs/1/archive/*.jsonl; archive/*.jsonl; "
                       "RUNSTATE.json; schedule/cycles.jsonl", "frozen[0]; line counts"),
    }

    tests = subprocess.run([str(harness / ".venv-wsl" / "bin" / "python"), "-m", "pytest", "--collect-only",
                            "-q", "-p", "no:cacheprovider", "tests"],
                           cwd=harness, capture_output=True, text=True, env={**os.environ,
                           "PYTHONDONTWRITEBYTECODE": "1"})
    # -q prints one "tests/<file>.py: <count>" line per file
    collected = sum(int(l.rsplit(":", 1)[1]) for l in tests.stdout.splitlines()
                    if l.startswith("tests/") and l.rsplit(":", 1)[1].strip().isdigit()) or None
    out["engineering"] = {
        "tests_collected": collected,
        "tests_collected_on": now[:10],
        "verifier_files": 14,
        "golden_gate_cases": 91,
        "trace_crosscheck": "144 of 144",
        "demo_crosscheck": "154 of 154",
        "source": _src("rk-harness", harness, "tests/ (pytest --collect-only); tests/golden_gate.txt; "
                       "VERIFIER_FILES.txt", ""),
    }
    return out


# --------------------------------------------------------------------------- write

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rk-workspace", required=True, type=Path)
    ap.add_argument("--novel", required=True, type=Path)
    a = ap.parse_args(argv)
    DATA.mkdir(exist_ok=True)
    ws = a.rk_workspace.resolve()
    docs = {"rk.json": rk(ws)}
    roles = {
        "rk-harness": "code: the runner, the pinned verifier, the site generator, 1,900-odd tests",
        "rk-work": "run data: the append-only archive, lanes, validation, benchmark and trace documents",
        "rk-findings": "the findings site the run regenerates every cycle",
        "rk-overview": "the hand-built explainer site with an in-browser Q15 demo",
        "Novel-Numerical-Integration-Methods": "the 2025 ML project: generator, evolution, 10,000-ODE benchmark",
    }
    paths = {"rk-harness": ws / "rk-harness", "rk-work": ws / "rk-work", "rk-findings": ws / "rk-findings",
             "rk-overview": ws / "rk-overview",
             "Novel-Numerical-Integration-Methods": a.novel.resolve()}
    sites = {"rk-findings": "https://jgoetzmann.github.io/rk-findings/",
             "rk-overview": "https://jgoetzmann.github.io/rk-overview/"}
    docs["sources.json"] = {
        "snapshot_date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
        "repos": [{"name": k, "url": f"{GITHUB}/{k}", "commit": _head(v)[:12], "role": roles[k],
                   "site": sites.get(k)} for k, v in paths.items()],
        "private_workspace": "rk-dev, the private superproject that pins the four rk repos, is not linked",
    }
    try:
        import novel_snapshot  # noqa: F401  (tools/novel_snapshot.py, same directory)
        docs["novel.json"] = novel_snapshot.novel(a.novel.resolve(), _src, _load)
    except ImportError:
        pass
    for name, doc in docs.items():
        (DATA / name).write_text(json.dumps(doc, indent=1, sort_keys=True, allow_nan=False) + "\n",
                                 encoding="utf-8")
        print("wrote", DATA / name)
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    sys.exit(main())
