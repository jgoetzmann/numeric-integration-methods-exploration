# Numeric integration methods

Two projects by the same author searched for Runge-Kutta coefficients that do better than the textbook ones. The 2025 ML project, `Novel-Numerical-Integration-Methods`, tried to generate new explicit Butcher tables with a neural generator, a surrogate model and evolutionary search, scored in float64 on generated ODEs. The rk run (2026) is an autonomous, containerized search for coefficients that do well in Q15 fixed point with floor rounding on a modeled Cortex-M0+. A language model steers it through a JSON directive that can only narrow the search, and code does all the scoring.

In float64, established methods were more accurate in both projects ([claim U1](https://jgoetzmann.github.io/numeric-integration-methods-exploration/claims.html#U1)). In the rk run, float64 rk4 was 1,992x to 420,975x more accurate than the searched champion at the same cycle budget. In the 2025 benchmark, Dormand-Prince and RK4 had the lowest mean error, though against copies of themselves, random tables and truncated methods. Inside Q15 with floor rounding, at a 65,536-cycle budget on the analytic cost model, the rk run found a three-stage dyadic method with 2.95x lower held-out error than the best of eight classical methods. That lead also depends on the cost basis and on how the held-out problems are weighted, so the arithmetic alone does not decide it. It comes from epoch 1, whose cost model a later trace found had rk4 and rk38 in the wrong order, and epoch 2 has not re-measured it. An audit of the 2025 project credits its harness and benchmark, and finds that its claimed rediscovery of RK4 and Dormand-Prince does not hold: its search started from those two tables.

This repository builds a static site that tells both stories and carries the claims audit: every claim, its verdict, its limits and where to check it.

**Site:** [jgoetzmann.github.io/numeric-integration-methods-exploration](https://jgoetzmann.github.io/numeric-integration-methods-exploration/)

## Key findings

![Held-out error against cycles per step for the eight classical methods and the 16 discovered cell elites, in Q15 with floor rounding at a 65,536-cycle budget on the analytic cost model](docs/assets/rk-frontier.svg)

![Float64 error of the champion and of rk4 on the out-of-sample problems, each at the step count the 65,536-cycle budget gives it](docs/assets/rk-validation-f64.svg)

Each finding links to its claim in the audit, which gives the full limits and the evidence.

- Inside Q15 fixed point with floor rounding, at a 65,536-cycle budget, on the analytic `m0plus_fast` cost model with magnitude weighting, the searched three-stage method `11e898cb` has 2.95x lower held-out error than midpoint, the best of eight classical methods. This is an epoch-1 result on the cost model the trace later found had rk4 and rk38 in the wrong order, and epoch 2 has not re-measured it. Elites were picked on held-out error among 141,364 archived tableaus, so the four held-out problems act as a selection set and the lead carries winner's-curse bias. The 2.95x is an RMS over four problems: the champion has lower error than midpoint on three of them and higher on pendulum, and much of the gap comes from rc_thermal, where every classical method stalls near a quantization floor. Of six cost-basis and weighting cells, the champion keeps its lead on every leave-one-out subset in two, both analytic: 2.95x under magnitude weighting and 3.36x under reference-norm weighting. On the traced whole-step basis the ratio is 1.01x under magnitude weighting (lowest leave-one-out 0.614x) and 1.84x under reference-norm weighting (lowest 0.604x). Under median-anchor weighting, which weights the four problems equally, it is 1.1x on the analytic basis (lowest 0.814x) and 0.0494x on the traced one, a cell the source reads as that weighting magnifying pendulum, not as the champion losing by that factor. The lead is a floor-rounding result: under round-to-nearest, at the same budget and cost model, rk38 alone reaches 0.0263 held-out error, below the champion's 0.0286 under floor rounding. ([claim R1](https://jgoetzmann.github.io/numeric-integration-methods-exploration/claims.html#R1))
- Under the same conditions and with the same selection bias, each of the 16 discovered methods that hold one of the archive's 18 occupied cells has lower held-out error than all eight classical methods, whatever their cost. The closest, a four-stage elite at 30 cycles per step, has 0.0836 against midpoint's 0.0844. Classical methods hold the other 2 cells. Re-ranking all 141,364 archived tableaus on the analytic basis, no classical method ranks above the champion under any of the three weightings, though the champion's own rank moves with the weighting: 1 under magnitude weighting, 15 under reference-norm weighting and 9,974 under median-anchor weighting. ([claim R2](https://jgoetzmann.github.io/numeric-integration-methods-exploration/claims.html#R2))
- On eight out-of-sample problems, the best of the three discovered methods tried had lower Q15 error than the best of the five classical methods run (euler, heun2, midpoint, rk4, rk38) on 4 of 5 non-stiff problems. The fixed champion alone had the lower error on 3 of the 5. No optimizer or model saw these problems and the champion was fixed before they ran, but people chose them after the search began. On the stiff `robertson_scaled` problem every discovered method overflowed, and so did rk4 and rk38; euler, heun2 and midpoint finished, midpoint with the lowest error. ([claim R4](https://jgoetzmann.github.io/numeric-integration-methods-exploration/claims.html#R4))
- In float64, rk4 is far more accurate than the champion. At the step count the 65,536-cycle budget gives each method, the champion's float64 error was 1,992x to 420,975x rk4's on the 7 validation problems where both finish. That is the like-for-like comparison, and it sets an order-2 method against an order-4 one; classical order-2 methods trail float64 rk4 by a similar margin in the same runs. Two wider comparisons measure the arithmetic rather than the coefficients. Float64 rk4 had lower error than every Q15 run, classical and discovered alike, in 56 of 56 fixed-step cells at identical step counts. At tolerances of one Q15 least significant bit, the most accurate library solver, Radau on all 7 problems, was a median 519x more accurate than the most accurate Q15 run. Dormand-Prince (SciPy RK45) was among the library solvers but was never the most accurate one, and it never ran against the champion in the same arithmetic. The search optimized for Q15 floor arithmetic on purpose. ([claim R5](https://jgoetzmann.github.io/numeric-integration-methods-exploration/claims.html#R5))
- A host-side audit compiled the step with GCC 13.2.1 and traced it under an emulator. The compiled step agreed with the Python evaluator bit for bit in 144 of 144 cases, 25 of them overflow cases where both stop at the same operation, and it showed that the `m0plus_fast` cost model the archive was scored under put rk4 and rk38 in the wrong order. The run froze epoch 1 and started epoch 2 under a corrected cost model instead of rescoring the old archive. The emulator is instruction-accurate, not cycle-accurate, and nothing was measured on a physical chip. ([claim R7](https://jgoetzmann.github.io/numeric-integration-methods-exploration/claims.html#R7))
- The scorer is out of the search's reach. The harness is mounted read-only, and a sha256 over the pinned files (10 in epoch 1, 14 since epoch 2) is checked at every start and stored in every record. 91 golden and canary cases must pass before any cycle runs, and the suite collected 1,908 tests on 2026-09-23. No GitHub credential enters the container: it commits and the host pushes. The one credential inside is the language model's sign-in file, mounted read-only. ([claim R11](https://jgoetzmann.github.io/numeric-integration-methods-exploration/claims.html#R11))
- Epoch 1 ran from 2026-08-29 to 2026-09-10: 3,931 search cycles over 13 days of archive and 141,364 scored records, all under the epoch-1 hash apart from 21 written minutes before that pin was set. Autonomous here means that no person chose candidates or scores and the pinned scorer never changed. It does not mean free of human operation: the runner started 24 times as people deployed changes to the unpinned harness code. Epoch 2 started on 2026-09-17 under the new verifier hash, stopped late that day, and nothing restarted it until 2026-09-23. The watchdog now resumes the stops it makes itself, and after a reboot the run is started by hand with one command. ([claim R12](https://jgoetzmann.github.io/numeric-integration-methods-exploration/claims.html#R12))
- The 2025 ML project built an evaluation harness that runs end to end for explicit tables: a generic Butcher-table stepper, a generator covering 11 ODE families including stiff ones, a SciPy reference solver, parallel scoring and 16 trial configurations. Its source tree holds 10,279 lines of Python across 47 files. Two of its parts produced artifacts: the stepper runs only the explicit part of a table, and the reference solver covers 5 of the 6 test families and 5 of the 11 training families. The claims drawn from it in 2025 are what did not hold. ([claim N9](https://jgoetzmann.github.io/numeric-integration-methods-exploration/claims.html#N9))
- Across 12 methods and 10,000 generated ODEs (8,113 scorable), Dormand-Prince had the lowest mean error (0.0791) and RK4 the next lowest (0.14). The error is the mean of each ODE's maximum error, which a few outlier ODEs dominate. The trial entries were copies of RK4 and Dormand-Prince or random tables, the Gauss-Legendre entries ran truncated through a stepper that ignores the implicit part of a table, and the reference solutions came from SciPy RK45, an adaptive Dormand-Prince solver, so the Dormand-Prince entry is measured against a reference built on its own tableau. ([claim N1](https://jgoetzmann.github.io/numeric-integration-methods-exploration/claims.html#N1))
- The claimed rediscovery of RK4 and Dormand-Prince does not hold. RK4 was placed in the starting population of the four-stage runs and Dormand-Prince in that of the seven-stage run. The genetic operators ran and the population moved off the seed, but the composite score is clipped at 1: all 10,000 rows of the one training log score 1, and the best-table tracker replaces the saved table only on a strictly higher score, so the seed stayed. ([claim N2](https://jgoetzmann.github.io/numeric-integration-methods-exploration/claims.html#N2))
- The claim that gradient descent collapsed into local minima does not hold either. The generator that proposes tables was never trained: its optimizer was created and never stepped, and a random generator that resets its seed to 42 filled every empty slot. The only gradient descent in the project trained a surrogate model, and nothing in the training loop reads its predictions. ([claim N4](https://jgoetzmann.github.io/numeric-integration-methods-exploration/claims.html#N4))

## Repositories

| Repository | Role | Link | Live site | Commit at snapshot |
| --- | --- | --- | --- | --- |
| `rk-harness` | code: the runner, the pinned verifier, the site generator, 1,900-odd tests | [GitHub](https://github.com/jgoetzmann/rk-harness) | none | `d1e41d5976a4` |
| `rk-work` | run data: the append-only archive, lanes, validation, benchmark and trace documents | [GitHub](https://github.com/jgoetzmann/rk-work) | none | `2bed0ad028c3` |
| `rk-findings` | the findings site the run regenerates every cycle | [GitHub](https://github.com/jgoetzmann/rk-findings) | [jgoetzmann.github.io/rk-findings](https://jgoetzmann.github.io/rk-findings/) | `4aa8ff43b09c` |
| `rk-overview` | the hand-built explainer site with an in-browser Q15 demo | [GitHub](https://github.com/jgoetzmann/rk-overview) | [jgoetzmann.github.io/rk-overview](https://jgoetzmann.github.io/rk-overview/) | `1a8e0a739ce4` |
| `Novel-Numerical-Integration-Methods` | the 2025 ML project: generator, evolution, 10,000-ODE benchmark | <a href="https://github.com/jgoetzmann/Novel-Numerical-Integration-Methods">GitHub</a> | none | `d89c2c809ee0` |

## How the pieces fit

- `rk-harness` is the code: the runner, the search, the pinned verifier, the site generator and the tests. A host watchdog starts a container that mounts the harness read-only, so the search cannot change the code that scores it.
- Each cycle the container appends scored records to `rk-work`, regenerates `rk-findings` and commits both. No GitHub credential enters the container: it commits, and the host watchdog pushes. The one credential inside is the language model's sign-in file, mounted read-only. `rk-work` also keeps epoch 1 frozen under `epochs/1/`.
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
