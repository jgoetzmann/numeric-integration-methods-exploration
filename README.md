# Numeric integration methods

Two projects searched for Runge-Kutta coefficients that do better than the textbook ones. The 2025 ML project, `Novel-Numerical-Integration-Methods`, tried to generate new explicit Butcher tables with a neural generator and evolutionary search, scored on generated ODEs. The rk run (2026) is an unattended search for coefficients that do best in Q15 fixed point with floor rounding on a modeled Cortex-M0+.

In float64, established methods such as rk4 and Dormand-Prince came out on top in both projects ([claim U1](https://jgoetzmann.github.io/numeric-integration-methods-exploration/claims.html#U1)). Inside Q15 with floor rounding, at a 65,536-cycle budget and on the analytic cost model, the rk run found a three-stage dyadic method with 2.95x lower held-out error than the best of eight classical methods. On a traced whole-step cost basis that lead shrinks to 1.01x. An audit of the 2025 project credits its harness and benchmark but finds that its claimed rediscovery of RK4 and Dormand-Prince does not hold: the evolutionary search started from those two tables.

This repository builds a static site that tells both stories and carries the claims audit: every claim, its verdict, its limits and where to check it.

**Site:** [jgoetzmann.github.io/numeric-integration-methods-exploration](https://jgoetzmann.github.io/numeric-integration-methods-exploration/)

## Key findings

- **The Q15 result.** Inside Q15 fixed point with floor rounding, at a 65,536-cycle budget, the searched three-stage method `11e898cb` has 2.95x lower held-out error than midpoint, the best of eight classical methods (analytic cost model, magnitude weighting, four held-out problems). On the traced whole-step cost basis the lead shrinks to 1.01x, and under median-anchor weighting on that basis midpoint leads. Elites were picked on held-out error, so the lead carries winner's-curse bias. Under the same conditions, in all 16 cells the search filled, the discovered method has lower held-out error than every classical method that costs the same or less. ([claim R1](https://jgoetzmann.github.io/numeric-integration-methods-exploration/claims.html#R1), [claim R2](https://jgoetzmann.github.io/numeric-integration-methods-exploration/claims.html#R2))
- **Out of sample.** On eight problems no optimizer or model saw, chosen by people after the search began, the best discovered method had lower Q15 error than the best classical method on 4 of 5 non-stiff problems. On the stiff `robertson_scaled` problem every discovered method overflowed while midpoint finished. ([claim R4](https://jgoetzmann.github.io/numeric-integration-methods-exploration/claims.html#R4))
- **Where established methods win.** In float64, at the same step counts, rk4 had the lower error in 56 of 56 cells and the champion was 1,992x to 420,975x less accurate than rk4. The adaptive library solvers, Dormand-Prince (SciPy RK45) among them, were a median 519x more accurate at tolerances matched to one Q15 step. The search optimized for Q15 floor arithmetic on purpose, and this is the boundary of that result. ([claim R5](https://jgoetzmann.github.io/numeric-integration-methods-exploration/claims.html#R5))
- **The run caught its own cost-model error.** Compiling the step with GCC 13.2.1 and tracing it under an instruction-accurate (not cycle-accurate) emulator reproduced the Python evaluator bit for bit in 144 of 144 cases and showed that the epoch 1 cost model put rk4 and rk38 in the wrong order. The run froze epoch 1 and started epoch 2 under the corrected cost model instead of rescoring the old archive. Nothing was measured on a physical chip. ([claim R7](https://jgoetzmann.github.io/numeric-integration-methods-exploration/claims.html#R7))
- **The scorer is out of the search's reach, and the run is unattended.** The harness is mounted read-only, a sha256 over 14 files is checked at every start and stored in every record, and 91 golden and canary cases must pass before any cycle runs. The suite collected 1,908 tests on the snapshot date. Epoch 1 ran from 2026-08-29 to 2026-09-10: 3,931 cycles over 13 days of archive and 141,364 scored records. Epoch 2 lost five days to a stop nothing restarted; the watchdog now resumes its own stops. ([claim R11](https://jgoetzmann.github.io/numeric-integration-methods-exploration/claims.html#R11), [claim R12](https://jgoetzmann.github.io/numeric-integration-methods-exploration/claims.html#R12))
- **The 2025 harness and benchmark.** The 2025 ML project built a working evaluation harness: a generic Butcher-table stepper for explicit methods, a generator covering 11 ODE families including stiff ones, a SciPy reference solver, parallel scoring and 16 trial configurations, in 10,279 lines of Python across 47 files. Across 12 methods and 10,000 generated ODEs (8,113 scorable), Dormand-Prince had the lowest mean error (0.0791) and RK4 the next lowest (0.14). That error is a mean of per-ODE maxima that a few outlier ODEs dominate, and the trained entries were copies of RK4 and Dormand-Prince or random tables. ([claim N9](https://jgoetzmann.github.io/numeric-integration-methods-exploration/claims.html#N9), [claim N1](https://jgoetzmann.github.io/numeric-integration-methods-exploration/claims.html#N1))
- **What the audit of the 2025 project found.** Both RK4 and Dormand-Prince were placed in the starting population of the evolutionary search. The composite score is clipped at 1 and every one of the 10,000 logged scores sits at that ceiling, so no candidate could replace the seed, and the claimed rediscovery does not hold. The generator's optimizer was created and never stepped, so no gradient descent ran and nothing collapsed into local minima. ([claim N2](https://jgoetzmann.github.io/numeric-integration-methods-exploration/claims.html#N2), [claim N4](https://jgoetzmann.github.io/numeric-integration-methods-exploration/claims.html#N4))

## Repositories

| Repository | Role | Link | Live site | Commit at snapshot |
| --- | --- | --- | --- | --- |
| `rk-harness` | code: the runner, the pinned verifier, the site generator, 1,900-odd tests | [GitHub](https://github.com/jgoetzmann/rk-harness) | none | `424f25c3f36b` |
| `rk-work` | run data: the append-only archive, lanes, validation, benchmark and trace documents | [GitHub](https://github.com/jgoetzmann/rk-work) | none | `25da57d0cd19` |
| `rk-findings` | the findings site the run regenerates every cycle | [GitHub](https://github.com/jgoetzmann/rk-findings) | [jgoetzmann.github.io/rk-findings](https://jgoetzmann.github.io/rk-findings/) | `24a3a8f815c3` |
| `rk-overview` | the hand-built explainer site with an in-browser Q15 demo | [GitHub](https://github.com/jgoetzmann/rk-overview) | [jgoetzmann.github.io/rk-overview](https://jgoetzmann.github.io/rk-overview/) | `1a8e0a739ce4` |
| `Novel-Numerical-Integration-Methods` | the 2025 ML project: generator, evolution, 10,000-ODE benchmark | <a href="https://github.com/jgoetzmann/Novel-Numerical-Integration-Methods">GitHub</a> | none | `d89c2c809ee0` |

## How the pieces fit

- `rk-harness` is the code: the runner, the search, the pinned verifier, the site generator and the tests. A host watchdog starts a container that mounts the harness read-only, so the search cannot change the code that scores it.
- Each cycle the container appends scored records to `rk-work`, regenerates `rk-findings` and commits both. The host watchdog does the pushing, so no credential enters the container. `rk-work` also keeps epoch 1 frozen under `epochs/1/`.
- `rk-overview` is built by hand from `rk-work`. Its tools recompute the analysis into `tools/key_findings.json` and generate the explainer pages. It is a snapshot that goes stale between refreshes, while the findings site rebuilds every cycle.
- rk-dev, the private superproject that pins the four rk repos, is not linked.
- `Novel-Numerical-Integration-Methods` stands alone. It shares no code or data with the rk run.
- This repository never reads any of them at build time. `tools/snapshot.py` copies the figures out of local clones into `data/*.json`, recording the repository, commit, file and key behind each block. `data/claims.json` is the audit, written by hand against those files. `tools/build.py` turns `data/` into the static site in `docs/`.

## Build

Build the site from the committed snapshot. It uses the Python standard library only, and the same data gives byte-identical pages:

`python tools/build.py`

That writes `docs/`; `python tools/build.py --out DIR` writes somewhere else. The checks run with `python -m pytest tests` (needs `pytest`).

To refresh the snapshot from the source repositories, then rebuild:

`python tools/snapshot.py --rk-workspace RK_WORKSPACE --novel ML_2025_CLONE`

`python tools/build.py`

`RK_WORKSPACE` is a directory holding clones of `rk-harness`, `rk-work`, `rk-findings` and `rk-overview` side by side, and `ML_2025_CLONE` is a clone of `Novel-Numerical-Integration-Methods`. The snapshot rewrites `data/rk.json`, `data/novel.json` and `data/sources.json` and leaves `data/claims.json` alone, so check the claims against the new numbers before publishing a rebuild.

## Layout

- `data/`: the snapshot (`rk.json`, `novel.json`, `sources.json`) and the claims audit (`claims.json`).
- `web/`: the page code, one package per page under `web/pages/`, the shared page shell, number formatting and the stylesheet.
- `tools/`: `build.py` builds the site; `snapshot.py` refreshes `data/`.
- `docs/`: the built site.
- `tests/`: the checks.

## Numbers are a dated snapshot

Every number here and on the site comes from a snapshot taken on 2026-09-23, at the commits in the table above. The rk run keeps going after that date. The live findings site, [jgoetzmann.github.io/rk-findings](https://jgoetzmann.github.io/rk-findings/), has current numbers.
