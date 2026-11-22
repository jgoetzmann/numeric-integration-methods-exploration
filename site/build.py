"""Build the site in docs/ from data/*.json and the files in site/src/.

The site never types a number by hand: every figure in the page text comes from data/*.json
(the final snapshot of the run) through the {{name}} slots below. The same inputs always give
the same bytes. Standard library only.

    python site/build.py            # writes docs/
    python site/build.py --out DIR  # writes somewhere else
"""
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "site" / "src"
DATA = ROOT / "data"
REPO = "https://github.com/jgoetzmann/numeric-integration-methods-exploration"
BLOB = REPO + "/blob/main/"
TREE = REPO + "/tree/main/"
RELEASE = REPO + "/releases/tag/final-archive"

# Old page names of the site, kept as redirects so that old links still work.
REDIRECTS = {"rk.html": "#result", "claims.html": "#claims", "novel.html": "#ml-2025",
             "epochs.html": "#timeline", "architecture.html": "#how", "repos.html": "#repo"}


def load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def x(v: float, digits: int = 3) -> str:
    """A ratio as the page writes it: 2.95x, 1.01x, 0.614x."""
    s = f"{v:.{digits}g}"
    return s + "x"


def n(v) -> str:
    return f"{int(v):,}"


def e(s: str) -> str:
    return html.escape(s, quote=True)


def values(rk: dict, novel: dict, claims: dict) -> dict:
    ch, fr, cf = rk["champion"], rk["frontier"], rk["counterfactual"]
    cells = {(c["basis"], c["weighting"]): c for c in cf["cells"]}
    e1, e2, end = rk["epochs"]["epoch1"], rk["epochs"]["epoch2"], rk["run_end"]
    eng, val, lib = rk["engineering"], rk["validation"], rk["libraries"]
    fvr = rk["floor_vs_round"]["heldout_rms"]
    trace_ok, trace_all = (int(t) for t in eng["trace_crosscheck"].split(" of "))
    demo_ok, demo_all = (int(t) for t in eng["demo_crosscheck"].split(" of "))
    verdicts = {}
    for c in claims["claims"]:
        verdicts[c["verdict"]] = verdicts.get(c["verdict"], 0) + 1
    return {
        "champ_hash": ch["hash"],
        "champ_stages": str(ch["stages"]),
        "champ_order": str(ch["order"]),
        "champ_error": f"{ch['heldout_error']:.3g}",
        "champ_cycle": str(ch["found_at_cycle"]),
        "lead": x(ch["lead"]),
        "lead_plain": f"{ch['lead']:.3g}",
        "best_classical": ch["best_classical"],
        "best_classical_error": f"{ch['best_classical_heldout_error']:.3g}",
        "loo_min": x(ch["leave_one_out_min"]),
        "loo_max": x(ch["leave_one_out_max"]),
        "traced_mag": x(cells[("traced_whole_step", "magnitude")]["ratio"]),
        "traced_mag_loo": x(cells[("traced_whole_step", "magnitude")]["lowest_leave_one_out_ratio"]),
        "rk38_round": f"{fvr['round_to_nearest']['rk38']:.3g}",
        "champ_error_3": f"{ch['heldout_error']:.3g}",
        "cells_total": str(fr["cells_total"]),
        "cells_disc": str(fr["cells_held_by_discovered"]),
        "cells_class": str(fr["cells_held_by_classical"]),
        "tableaus": n(fr["unique_tableaus"]),
        "f64_min": n(round(rk["float64_gap"]["champion_over_rk4_min"])),
        "f64_max": n(round(rk["float64_gap"]["champion_over_rk4_max"])),
        "f64_problems": str(rk["float64_gap"]["problems"]),
        "lib_median": n(round(lib["median_ratio_q15_over_library_at_matched_tolerance"])),
        "fixed_cells": str(lib["fixed_step_cells_compared"]),
        "val_won": str(val["practical_won_by_discovered"]),
        "val_total": str(val["practical_total"]),
        "trace_ok": str(trace_ok), "trace_all": str(trace_all),
        "demo_ok": str(demo_ok), "demo_all": str(demo_all),
        "tests": n(eng["tests_collected"]),
        "tests_on": eng["tests_collected_on"],
        "golden": str(eng["golden_gate_cases"]),
        "pinned": str(eng["verifier_files"]),
        "budget": n(rk["setup"]["budget_cycles"]),
        "e1_start": e1["started"][:10], "e1_stop": e1["stopped"][:10],
        "e1_cycles": n(e1["cycles_run"]), "e1_records": n(e1["records"]),
        "e1_days": str(e1["archive_day_count"]),
        "e1_frozen": e1["frozen_at"][:10],
        "e2_start": e2["started"][:10],
        "end_date": end["ended"][:10], "end_cycle": n(end["final_cycle"]),
        "e2_records": n(end["epoch2_records"]),
        "all_records": n(end["records_both_epochs"]),
        "n_claims": str(len(claims["claims"])),
        "n_true": str(verdicts.get("supported", 0)),
        "n_limits": str(verdicts.get("supported-with-limits", 0)),
        "n_false": str(verdicts.get("not-supported", 0)),
        "n_bug": str(verdicts.get("artifact", 0)),
        "novel_odes": n(novel["benchmark"]["odes"]),
        "novel_methods": str(novel["benchmark"]["methods"]),
        "repo": REPO, "release": RELEASE, "tree": TREE, "blob": BLOB,
    }


def evidence_link(f: dict) -> str:
    if f["kind"] == "release":
        return (f'<a href="{RELEASE}">{e(f["path"])}</a> '
                f'<span class="muted">(in rk-work-final.tar.gz, final-archive release)</span>')
    label = f.get("label", f["path"])
    url = (TREE if f["kind"] == "tree" else BLOB) + f["path"].rstrip("/")
    return f'<a href="{e(url)}"><code>{e(label)}</code></a>'


def line_anchor(f: dict, at: str) -> dict:
    """For one source file cited with line numbers, point the link at the first range."""
    m = re.match(r"^(\d+)(?:-(\d+))?", at)
    if f["kind"] == "repo" and m and not f["path"].endswith(".json"):
        g = dict(f)
        a, b = m.group(1), m.group(2)
        g["anchor"] = f"#L{a}" + (f"-L{b}" if b else "")
        return g
    return f


def render_claims(claims: dict) -> str:
    v = claims["verdicts"]
    out = []
    for c in claims["claims"]:
        proj = {"rk": "The rk run", "novel": "2025 project", "both": "Both projects"}[c["project"]]
        body = [f'<p class="claim-text">{e(c["claim"])}</p>']
        if c.get("original_wording"):
            body.append(f'<p class="orig"><span class="k">Original words:</span> <q data-ste-skip>{e(c["original_wording"])}</q></p>')
        for key, head in (("correction", "What is true"), ("limits", "Limits")):
            if c.get(key):
                body.append(f'<p class="k">{head}</p>')
                body.extend(f"<p>{e(p)}</p>" for p in c[key])
        ev = []
        for item in c["evidence"]:
            links = []
            for f in item["files"]:
                f = line_anchor(f, item["at"])
                link = evidence_link(f)
                if f.get("anchor"):
                    link = link.replace('">', f'{f["anchor"]}">', 1)
                links.append(link)
            at = f' <span class="muted">at</span> <code>{e(item["at"])}</code>' if item["at"] else ""
            ev.append(f'<li data-ste-skip>{" · ".join(links)}{at}</li>')
        body.append('<p class="k">Evidence</p><ul class="ev">' + "".join(ev) + "</ul>")
        star = ' <span class="star" title="headline claim">★</span>' if c["headline"] else ""
        out.append(
            f'<details class="claim" id="{c["id"]}" data-project="{c["project"]}" data-verdict="{c["verdict"]}">'
            f'<summary><span class="cid">{c["id"]}</span><span class="ct">{e(c["title"])}{star}</span>'
            f'<span class="badge v-{c["verdict"]}">{e(v[c["verdict"]]["label"])}</span>'
            f'<span class="proj">{proj}</span></summary>'
            f'<div class="cbody">{"".join(body)}</div></details>')
    return "\n".join(out)


def render_verdict_key(claims: dict) -> str:
    return "".join(f'<li><span class="badge v-{k}">{e(d["label"])}</span> {e(d["meaning"])}</li>'
                   for k, d in claims["verdicts"].items())


def page_data(rk: dict, demo: dict) -> dict:
    """The numbers that the charts and the demo draw, and nothing more."""
    fr, cf = rk["frontier"], rk["counterfactual"]
    return {
        "frontier": {"classical": fr["classical"],
                     "discovered": [{k: d[k] for k in ("cycles", "heldout_error", "is_champion", "order", "stages", "first_cycle")}
                                    for d in fr["discovered"]]},
        "cells": cf["cells"],
        "champion": {"hash": rk["champion"]["hash"], "per_problem": rk["champion"]["per_problem_heldout"],
                     "midpoint": rk["champion"]["classical_per_problem_heldout"]["midpoint"]},
        "demo": demo,
    }


def build(out: Path) -> None:
    rk, novel, claims = load("rk.json"), load("novel.json"), load("claims.json")
    demo = json.loads((ROOT / "analysis" / "tools" / "demo_data.json").read_text(encoding="utf-8"))
    v = values(rk, novel, claims)
    v["claims"] = render_claims(claims)
    v["verdict_key"] = render_verdict_key(claims)
    v["claims_about"] = e(claims["about"])
    v["data_json"] = json.dumps(page_data(rk, demo), separators=(",", ":"), sort_keys=True).replace("</", "<\\/")
    tpl = (SRC / "index.html").read_text(encoding="utf-8")

    def sub(m):
        k = m.group(1)
        if k not in v:
            raise KeyError(f"index.html uses {{{{{k}}}}}, which build.py does not define")
        return v[k]

    page = re.sub(r"\{\{(\w+)\}\}", sub, tpl)
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.html"):
        old.unlink()
    for name in ("style.css", "app.js", "q15.js"):
        shutil.copyfile(SRC / name, out / name)
    (out / "index.html").write_text(page, encoding="utf-8", newline="\n")
    (out / ".nojekyll").write_text("", encoding="utf-8")
    for name, anchor in REDIRECTS.items():
        (out / name).write_text(
            '<!doctype html><meta charset="utf-8"><title>Moved</title>'
            f'<meta http-equiv="refresh" content="0; url=./{anchor}">'
            f'<script>location.replace("./"+(location.hash||"{anchor}"))</script>'
            f'<p>This page moved to <a href="./{anchor}">the main page</a>.</p>\n',
            encoding="utf-8", newline="\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "docs")
    a = ap.parse_args(argv)
    build(a.out)
    print(f"built {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
