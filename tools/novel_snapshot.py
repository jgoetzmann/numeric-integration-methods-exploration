"""The Novel-Numerical-Integration-Methods half of tools/snapshot.py.

Everything here is read or computed from that repository's own committed files. Where a
figure comes from an audit of its code rather than from its data (for example "the
evolutionary population starts from RK4"), the claim lives in data/claims.json with a file
and line reference, not here.
"""
from __future__ import annotations

import csv
import glob
import json
import statistics
import subprocess
from fractions import Fraction as F
from pathlib import Path

# The textbook tables the audit compares against, written out rather than imported: the
# project's own module imports torch, and this script should not need it.
RK4_A = [[0, 0, 0, 0], [F(1, 2), 0, 0, 0], [0, F(1, 2), 0, 0], [0, 0, 1, 0]]
RK4_B = [F(1, 6), F(1, 3), F(1, 3), F(1, 6)]
DP_A = [
    [0, 0, 0, 0, 0, 0, 0],
    [F(1, 5), 0, 0, 0, 0, 0, 0],
    [F(3, 40), F(9, 40), 0, 0, 0, 0, 0],
    [F(44, 45), F(-56, 15), F(32, 9), 0, 0, 0, 0],
    [F(19372, 6561), F(-25360, 2187), F(64448, 6561), F(-212, 729), 0, 0, 0],
    [F(9017, 3168), F(-355, 33), F(46732, 5247), F(49, 176), F(-5103, 18656), 0, 0],
    [F(35, 384), 0, F(500, 1113), F(125, 192), F(-2187, 6784), F(11, 84), 0],
]
DP_B = [F(35, 384), 0, F(500, 1113), F(125, 192), F(-2187, 6784), F(11, 84), 0]

LABELS = {
    "baseline_rk4": "RK4",
    "baseline_rk45_dormand_prince": "Dormand-Prince (RK45)",
    "baseline_gauss_legendre_2": "Gauss-Legendre 2",
    "baseline_gauss_legendre_3": "Gauss-Legendre 3",
}


def _max_diff(A, b, A0, b0) -> float | None:
    if len(b) != len(b0):
        return None
    d = max(abs(float(x) - float(y)) for x, y in zip(b, b0))
    for r, r0 in zip(A, A0):
        d = max(d, max(abs(float(x) - float(y)) for x, y in zip(r, r0)))
    return d


def _git(repo: Path, *args) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                          text=True).stdout.strip()


def novel(repo: Path, _src, _load) -> dict:
    name = "Novel-Numerical-Integration-Methods"
    out: dict = {"_about": (
        "The 2025 ML project: a pipeline meant to generate new explicit Runge-Kutta tables with "
        "a neural generator, a surrogate model and evolutionary search, scored on generated "
        "ODEs. Numbers are read from its committed files; the claims audit is data/claims.json.")}

    commits = _git(repo, "log", "--reverse", "--format=%ad", "--date=short").splitlines()
    py = [p for p in glob.glob(str(repo / "src" / "**" / "*.py"), recursive=True)]
    lines = sum(sum(1 for _ in open(p, encoding="utf-8", errors="replace")) for p in py)
    out["repo"] = {"commits": len(commits), "first_commit": commits[0], "last_commit": commits[-1],
                   "active_from": "2025-09-13", "active_to": "2025-09-21",
                   "src_python_files": len(py), "src_python_lines": lines,
                   "trial_folders": len(glob.glob(str(repo / "trials" / "trial_*"))),
                   "source": _src(name, repo, "git log; src/**/*.py; trials/", "")}

    rows = list(csv.DictReader(open(repo / "results" / "real_trial_results.csv", encoding="utf-8")))
    bench = []
    for r in rows:
        tid = r["Trial_Number"]
        label = LABELS.get(tid) or ("Trial " + tid.replace("trial_", "").lstrip("0"))
        bench.append({"id": tid, "label": label, "baseline": tid.startswith("baseline"),
                      "stages": int(r["Stages"]),
                      "runtime_s": float(r["Runtime_Seconds"]),
                      "mean_max_error": float(r["Max_Error"]),
                      "success_rate": float(r["Success_Rate"]),
                      "n_successful": int(r["N_Successful"]), "n_total": int(r["N_Total"])})
    out["benchmark"] = {
        "rows": bench,
        "methods": len(bench),
        "odes": bench[0]["n_total"],
        "scorable_odes": bench[0]["n_successful"],
        "success_rate_distinct_values": sorted({b["success_rate"] for b in bench}),
        "error_metric": "mean over the scorable ODEs of each ODE's maximum absolute error against "
                        "a SciPy RK45 reference, fixed step h = 0.01 on t in [0, 1]",
        "runtime_metric": "wall time for all 10,000 ODEs, reference solve included",
        "source": _src(name, repo, "results/real_trial_results.csv", "Max_Error; Runtime_Seconds; "
                       "Success_Rate; N_Successful; N_Total"),
    }

    trials = []
    tables = {}
    for d in sorted(glob.glob(str(repo / "trials" / "trial_*"))):
        p = Path(d) / "best_butcher_table.json"
        num = int(Path(d).name.split("_")[1])
        if not p.exists():
            trials.append({"trial": num, "folder": Path(d).name, "saved_table": None})
            continue
        doc = _load(p)
        bt = doc["butcher_table"]
        A, b = bt["A"], bt["b"]
        tables[num] = (A, b)
        same_rk4 = _max_diff(A, b, RK4_A, RK4_B)
        same_dp = _max_diff(A, b, DP_A, DP_B)
        trials.append({"trial": num, "folder": Path(d).name, "stages": len(b),
                       "max_abs_diff_from_rk4": same_rk4, "max_abs_diff_from_dormand_prince": same_dp,
                       "training_odes": (doc.get("config") or {}).get("N_ODES"),
                       "order_check_label": bt.get("consistency_order"),
                       "score_ratio_to_rk4": ((doc.get("comparisons") or {}).get("rk4") or {}).get("score_ratio"),
                       "error_ratio_to_rk4": ((doc.get("comparisons") or {}).get("rk4") or {}).get("accuracy_ratio")})
    # which trials saved one and the same table
    for t in trials:
        if t.get("saved_table", True) is None:
            continue
        A, b = tables[t["trial"]]
        t["identical_to_trials"] = sorted(
            n for n, (A2, b2) in tables.items()
            if n != t["trial"] and len(b2) == len(b) and _max_diff(A, b, A2, b2) == 0.0)
    out["trials"] = {
        "rows": trials,
        "equal_to_rk4": [t["trial"] for t in trials if t.get("max_abs_diff_from_rk4") == 0.0],
        "equal_to_dormand_prince": [t["trial"] for t in trials
                                    if t.get("max_abs_diff_from_dormand_prince") == 0.0],
        "source": _src(name, repo, "trials/*/best_butcher_table.json", "butcher_table.A; butcher_table.b"),
    }

    log = list(csv.DictReader(open(repo / "metrics_log.csv", encoding="utf-8")))
    by_epoch: dict[int, list[float]] = {}
    for r in log:
        by_epoch.setdefault(int(r["epoch"]), []).append(float(r["max_error"]))
    out["metrics_log"] = {
        "rows": len(log),
        "composite_score_distinct_values": sorted({float(r["composite_score"]) for r in log}),
        "per_epoch": [{"epoch": e, "min_max_error": min(v), "median_max_error": statistics.median(v)}
                      for e, v in sorted(by_epoch.items())],
        "note": "one 100-epoch run of 100 four-stage candidates per epoch; the file has no trial "
                "column. Every logged composite score is the clip ceiling, 1.0.",
        "source": _src(name, repo, "metrics_log.csv", "epoch; max_error; composite_score"),
    }

    import re
    gen = (repo / "src" / "core" / "ode_dataset.py").read_text(encoding="utf-8")
    ev = (repo / "results" / "real_trial_evaluation.py").read_text(encoding="utf-8")
    run = (repo / "src" / "core" / "integrator_runner.py").read_text(encoding="utf-8").splitlines()
    ref_block = "\n".join(run[239:254])            # ReferenceSolver's family dispatch
    eval_types = re.search(r"ode_types = \[([^\]]*)\]", ev).group(1)
    out["audit_counts"] = {
        "training_ode_families": sorted(set(re.findall(r'equation_type="([a-z_]+)"', gen))),
        "evaluation_ode_families": re.findall(r"'([a-z_]+)'", eval_types),
        "reference_solver_families": re.findall(r'equation_type == "([a-z_]+)"', ref_block),
        "evaluation_step": 0.01, "evaluation_t_end": 1.0, "evaluation_odes": 10000,
        "training_set_odes": 1000,
        "source": _src(name, repo, "src/core/ode_dataset.py; results/real_trial_evaluation.py:50-130; "
                       "src/core/integrator_runner.py:240-254", ""),
    }
    bt_src = (repo / "src" / "core" / "butcher_tables.py").read_text(encoding="utf-8")
    out["audit_counts"]["random_generator_seed"] = int(
        re.search(r"def __init__\(self, seed: int = (\d+)\)", bt_src).group(1))
    c = out["audit_counts"]
    c["training_ode_family_count"] = len(c["training_ode_families"])
    c["evaluation_ode_family_count"] = len(c["evaluation_ode_families"])
    c["reference_solver_family_count"] = len(c["reference_solver_families"])

    evo = []
    for num, folder in ((12, "trial_012_4stage_evolution"), (13, "trial_013_7stage_evolution"),
                        (14, "trial_014_4stage_novelty"), (15, "trial_015_4stage_unconstrained")):
        h = _load(repo / "trials" / folder / "checkpoints" / "checkpoint_epoch_100.json")["training_history"]
        evo.append({"trial": num, "epochs": len(h),
                    "best_score_distinct": sorted({x["best_score"] for x in h}),
                    "mean_score_distinct": sorted({x["mean_score"] for x in h}),
                    "epochs_with_surrogate_loss": sum(1 for x in h if x.get("surrogate_loss"))})
    out["evolution_checkpoints"] = {
        "rows": evo,
        "note": "the surrogate model is trained by gradient descent (src/models/model.py:394-405); "
                "nothing in the training loop reads its predictions",
        "source": _src(name, repo, "trials/trial_01{2,3,4,5}_*/checkpoints/checkpoint_epoch_100.json",
                       "training_history[].best_score; mean_score; surrogate_loss"),
    }

    t16 = _load(repo / "trials" / "trial_016_4stage_novelty_v2" / "best_butcher_table.json")
    out["trial16"] = {
        "history": [{"epoch": h["epoch"], "best_score": h["best_score"], "mean_score": h["mean_score"]}
                    for h in t16["training_history"]],
        "training_time_s": t16.get("training_time"),
        "source": _src(name, repo, "trials/trial_016_4stage_novelty_v2/best_butcher_table.json",
                       "training_history; training_time"),
    }
    return out
