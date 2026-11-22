# analysis (was rk-overview)

These scripts compute the key findings of the rk run from the run data and the harness. They
were the tools of the old rk-overview site. The project site replaced that site on 2026-11-21.

| File | What it does |
| --- | --- |
| `tools/key_findings.py` | Computes every headline number (the lead, the frontier, the floor-rounding comparison, the premise test) and writes `tools/key_findings.json`. |
| `tools/counterfactual.py` | Computes the lead again under the other cost basis and the other weightings (six cells in all). |
| `tools/demo_data.py` | Writes `tools/demo_data.json`: the methods, the problems and 154 Python results that the Q15 demo on the site checks itself against. |
| `tools/floor_round.json` | The floor against round-to-nearest runs that the key findings read. |
| `DESIGN.md` | The design notes of the harness, as the project wrote them. |

The scripts read `../harness/` and `../run-data/`. Some numbers need the daily archive logs: get
`rk-work-final.tar.gz` from the [final-archive release](https://github.com/jgoetzmann/numeric-integration-methods-exploration/releases/tag/final-archive) and extract it into `../run-data/`.

The old site pages are in the git history of this folder, and in the final-archive release.
