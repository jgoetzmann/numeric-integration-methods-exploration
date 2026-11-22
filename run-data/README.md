# rk-work

Run data for the rk search, an unattended hunt for Runge-Kutta integrators that hold up in Q15
fixed point on a Cortex-M0+ cycle model. The run container wrote this repository at the end of
every cycle. People do not edit it.

**The run is over, and this is its final data.** The owner ended the run on 2026-11-10, after
cycle 17,364, and no more compute goes to it. `EPOCH_STATUS.json` freezes epoch 2, the last
commit (`run ended after cycle 17364`) is the final state, and nothing will be appended again.
Every number on both sites can be rebuilt from this repository and rk-harness; the overview's
closing section, [The run is over](https://jgoetzmann.github.io/rk-overview/#final), sums up the
final findings.

- Overview of the project: https://jgoetzmann.github.io/rk-overview/
- Findings built from this data (final snapshot): https://jgoetzmann.github.io/rk-findings/
- The code that wrote it: [rk-harness](https://github.com/jgoetzmann/rk-harness)

## What is in here

| Path | What it holds |
| --- | --- |
| `archive/YYYY-MM-DD.jsonl` | The scored archive for the explicit class. One record per accepted tableau, appended and never rewritten. Each record carries the verifier hash that scored it. |
| `adaptive_archive/`, `implicit_archive/` | The two lane archives. `ledger/YYYY-MM-DD.jsonl` is one line per candidate the lane search measured, by UTC day (`ledger.jsonl` holds the lines written before the 2026-09-23 split); `elites.json` is the capped, ranked list the findings site publishes. Nothing in them is scored against the pinned checker. |
| `sidetrack/` | The side-track measurement ledger (`ledger.jsonl`) and one JSON artifact per measured point, grouped by job. Each artifact states its own arithmetic. |
| `validation/results.json` | The practical validation suite: Q15 and float64 error for each method on each application problem. |
| `benchmark/results.json` | Library comparisons, matched-accuracy tables for the three classes, and measured time per step. |
| `falsification.json` | The early falsification experiment: where roundoff overtakes truncation error. |
| `hypotheses.jsonl` | The hypothesis ledger. Verdicts come from code. |
| `literature/`, `interpretation/` | Model-written literature digests and cycle interpretations. Verify their citations before relying on them. |
| `schedule/` | The lane rotation's own records, one row per cycle. |
| `prototypes/` | Output of the early adaptive and SDIRK prototypes. |
| `LAST_DIRECTIVE.json`, `saturation_state.json` | The most recent search directive and the epoch saturation state. |
| `epochs/1/` | The frozen epoch-1 run state, moved byte-identical at the D45 boundary with a sha256 manifest. Root paths always mean the current epoch. |
| `EPOCH.json` | The current epoch number, its verifier hash, and the frozen-epoch block with the archive site and tag. |

Some files exist only on the machine running the container and are gitignored: the event stream
(`events.jsonl`), run state, the heartbeat, the archive checkpoint, and the per-day lane record
files (`*_archive/20*.jsonl`). The per-day lane files run to a few hundred megabytes a day, and
single files already pass GitHub's 100 MB limit. Every record in them can be regenerated from
code and parameters.

What the container commits, and when: every cycle, whatever it changed among the paths above,
except today's archive file and today's lane ledger files, which go in once their UTC day has
closed. `EPOCH.json` and `epochs/` are written by hand at an epoch boundary. No file the runner
stages by name is staged at 95 MiB or more,
because GitHub refuses a push carrying a file of 100 MiB or more and every later push would fail
on it. The runner logs `commit_skipped_oversize` instead and the file stays on disk. See
`rk-harness/docs/DECISIONS.md` D46 and D47.

## What the public sites read

The findings pages read `archive/`, `validation/results.json`, `benchmark/results.json`,
`falsification.json`, `hypotheses.jsonl`, the side-track ledger and the artifacts it names, and
the two `elites.json` files. The research log also shows the newest entries from `literature/`
and `interpretation/` as model-written text, and the epoch panel on the findings index reads the
run's state files. The overview site reads the validation, benchmark and falsification documents
and its own `key_findings.json`, computed from this archive. Neither site quotes the per-day lane
records, `validation/axes.json` or `schedule/`. The reasoning is in `rk-harness/docs/DECISIONS.md`
(D24, D39, D40).
