"""architecture.html: how the rk run and the 2025 ML project are built.

Two diagrams (B30): figure#arch-rk for the rk run's host, container and
outputs, and figure#arch-novel for the 2025 pipeline with the audit's breaks
labelled in text. Under each, a list of the components, one sentence each.
"""

from web import fmt

from . import diagrams

SLUG = "architecture.html"
TITLE = "Architecture"
DESCRIPTION = (
    "How the rk run's container, host and sites fit together, and how the 2025 ML "
    "pipeline was wired, with the places an audit found it broke."
)

NOVEL_REPO = "Novel-Numerical-Integration-Methods"


def _cite(*ids):
    """(R11) or (N2, N3), each id linked to its entry on the claims page."""
    parts = []
    for cid in ids:
        parts.append(f'<a href="claims.html#{fmt.esc(cid)}">{fmt.esc(cid)}</a>')
    return "(" + ", ".join(parts) + ")"


def _repo(sources, name):
    for r in sources["repos"]:
        if r["name"] == name:
            return r


def _site_link(sources, name, text):
    repo = _repo(sources, name)
    return f'<a href="{fmt.esc(repo["site"])}">{fmt.esc(text)}</a>'


def _code(s):
    return f"<code>{fmt.esc(s)}</code>"


def _item(name, sentence):
    return f"<li><strong>{fmt.esc(name)}.</strong> {sentence}</li>"


def _rk_section(data):
    rk = data["rk"]
    sources = data["sources"]
    num = diagrams.rk_numbers(rk)
    snapshot = fmt.day(sources["snapshot_date"])
    heldout = diagrams.and_list(_code(p) for p in num["heldout"])
    c = _cite

    items = [
        _item("Watchdog",
              "A PowerShell script on the host kills the container on a stale heartbeat, stops "
              "it on model spend or low disk, pauses it on battery power or foreground CPU load, "
              "and pushes the run's repositories to GitHub; since epoch 2 lost five days to a "
              f"stop that nothing restarted {c('R12')}, it resumes the stops it made itself (D46)."),
        _item("Stats file",
              f"{_code('stats.txt')} is written on the host rather than in the container, so it "
              "can report a dead container, and it never carries a value forward or claims "
              "anything about the container unless Docker answered."),
        _item("Logon task",
              "A scheduled task runs the start script at logon, so the run comes back after a "
              "reboot unless a stop file says otherwise (D47)."),
        _item("Container",
              "The harness is mounted read-only and no credential enters the container, so the "
              f"search cannot reach its own scorer {c('R11')}; the host does the pushing."),
        _item("Verifier",
              f"A sha256 over {num['files']} pinned files is checked at every start and stored in "
              "every record, so changing a pinned file opens a new epoch instead of editing the "
              f"old one: epoch 1 ran under {_code(num['e1_hash'])} over {num['e1_files']} files, "
              f"and epoch 2 runs under {_code(num['e2_hash'])} over {num['e2_files']} after "
              f"tracing the compiled step showed the old cost model had {_code('rk4')} and "
              f"{_code('rk38')} in the wrong order {c('R7')}."),
        _item("Golden gate",
              f"Before any cycle runs, {num['gate']} golden and canary cases must pass, and the "
              f"full suite collected {num['tests']} tests on {num['tests_on']} {c('R11')}."),
        _item("Runner",
              "Each cycle replays unfinished work, runs the five steps in the diagram, then "
              "updates the hypothesis ledger, rebuilds the findings site and commits, so a crash "
              "mid-cycle is replayed rather than lost."),
        _item("Directive",
              "A language model writes a JSON directive that can only narrow the search, and an "
              "unknown key sends the runner to a fixed fallback; the model sees held-out errors, "
              f"and elites are picked on them {c('U2')}."),
        _item("Search",
              "Early phases enumerate a lattice of dyadic coefficients exhaustively, and later "
              "phases run CMA-ES over the stage matrix with the weights solved exactly."),
        _item("Verify",
              "The pinned verifier checks the order conditions in exact rational arithmetic, "
              "along with explicitness, row sums, coefficient range, Q15 overflow and stability."),
        _item("Score",
              f"Each surviving candidate runs in Q15 with floor rounding at a {num['budget']}-cycle "
              f"budget on the search problems and then on the held-out problems {heldout}, with "
              f"cycle costs from a model of the Cortex-M0+ rather than a chip {c('R7')}."),
        _item("Archive",
              "Scored candidates are appended to per-day JSON-lines files in "
              f"{_code('rk-work')}, and a MAP-Elites grid per order keeps the lowest held-out "
              "error in each cell of stage count and cycle band; epoch 1 wrote "
              f"{num['e1_records']} records {c('R12')}."),
        _item("Lanes and side tracks",
              "A schedule rotates this explicit lane with adaptive and implicit lanes that "
              "measure float64 cycles-to-tolerance, are not order-verified and are never ranked "
              "against archive errors, while side tracks answer a fixed catalogue of design "
              "questions off the archive."),
        _item("Hypothesis ledger",
              "Hypotheses are predicates in a closed grammar read by a hand-written parser, and "
              "code, not the model, assigns their verdicts."),
        _item("Literature digests",
              "The model writes web digests that feed later prompts, and the site publishes them "
              "labelled as model-written."),
        _item("Findings site",
              "The container rebuilds "
              f"{_site_link(sources, 'rk-findings', 'the findings site')} every cycle, "
              "deterministic and free of JavaScript, and one banned word blocks the whole build."),
        _item("Overview site",
              f"{_site_link(sources, 'rk-overview', 'The overview site')} is built by hand from a "
              "snapshot of the run's data, so it goes stale until someone rebuilds it."),
    ]

    return (
        '<section aria-labelledby="rk-system">'
        '<h2 id="rk-system">The rk run\'s system</h2>'
        "<p>Everything that decides a score sits inside the container behind a pinned hash, and "
        "everything that keeps the run alive or publishes it sits on the host. The runner box "
        "draws the explicit lane, the one whose candidates are scored into the archive.</p>"
        f'<figure id="{diagrams.RK_ID}">'
        f"{diagrams.arch_rk(data)}"
        f"<figcaption>The rk run as of the {snapshot} snapshot. Arrows show which part starts, "
        "controls or feeds which; the three boxes under the runner work beside the explicit "
        "lane.</figcaption>"
        "</figure>"
        '<h3 id="rk-components">Components</h3>'
        '<ul class="components">' + "".join(items) + "</ul>"
        "</section>"
    )


def _novel_section(data):
    sources = data["sources"]
    num = diagrams.novel_numbers(data["novel"])
    commit = _repo(sources, NOVEL_REPO)["commit"]
    missing = diagrams.and_list(_code(f) for f in num["missing_families"])
    c = _cite
    rk4 = _code("RK4")

    items = [
        _item("Generator",
              "An MLP maps noise to table entries, but its optimizer is created and never "
              "stepped and its raw outputs never pass validation, so every candidate slot falls "
              f"back to a random generator that reseeds to {num['seed']}, and trials "
              f"{num['nn_saved_span']} saved the same seeded table for each stage count "
              f"{c('N4')}."),
        _item("Evolution",
              f"Trials {num['evo_span']} ran a genetic search whose population starts with {rk4} "
              "or Dormand-Prince and perturbed copies of it, and trials "
              f"{num['rk4_trials']} saved {rk4} exactly while trial {num['dp_trials']} saved "
              f"Dormand-Prince exactly {c('N2')}."),
        _item("Random sampling",
              f"Trial {num['t16']} drew every candidate at random with no mutation or crossover, "
              "and its fitness read an accuracy field that does not exist, so accuracy carried "
              f"no weight {c('N7')}."),
        _item("Stepper",
              "A fixed-step stepper builds each stage from earlier stages only, so it ignores the "
              "diagonal and upper triangle of an implicit table, and both Gauss-Legendre baselines "
              f"ran as truncated explicit methods of order one {c('N5')}."),
        _item("Reference solver",
              "Dormand-Prince (SciPy RK45) supplies each reference solution but handles only "
              f"{num['ref_families']} of the {num['eval_families']} ODE families in the final "
              f"test, so {missing} problems fail for every method, and together with polynomial "
              f"ODEs that blow up this gives every method the same {num['success']} success rate "
              f"{c('N6')}."),
        _item("Composite score",
              "Weighted accuracy, efficiency and stability terms are summed and the total is "
              f"clipped at {num['clip']}, and all {num['logged']} logged scores sit at that "
              f"ceiling, so the score cannot tell {rk4} from a random table {c('N2', 'N3')}."),
        _item("Best-table tracker",
              "The saved table changes only on a strictly higher score, so once scores tie at the "
              "ceiling the earliest valid candidate stays best, which in the evolution trials is "
              f"the seeded baseline {c('N2')}."),
    ]

    return (
        '<section aria-labelledby="novel-pipeline">'
        '<h2 id="novel-pipeline">The 2025 ML project\'s pipeline</h2>'
        f"<p>{_code(NOVEL_REPO)} proposed Butcher tables in three ways and scored all of them "
        "with one stepper and one composite score. An audit in September 2026 read its code "
        f"and data at commit {_code(commit)}; each box with a heavy outline carries a line "
        "starting with \"Audit:\" that names the break and the claim that records it.</p>"
        f'<figure id="{diagrams.NOVEL_ID}">'
        f"{diagrams.arch_novel(data)}"
        f"<figcaption>The pipeline in {_code(NOVEL_REPO)}. A heavy outline and a line starting "
        "with \"Audit:\" mark each place the audit found a break; the ids in parentheses are "
        'entries on the <a href="claims.html">claims audit</a>.</figcaption>'
        "</figure>"
        '<h3 id="novel-components">Components</h3>'
        '<ul class="components">' + "".join(items) + "</ul>"
        '<h3 id="novel-holds">What still holds</h3>'
        "<p>The parts work as code: the stepper runs any explicit table, the ODE generator "
        f"covers {num['train_families']} families including stiff ones, and the final benchmark "
        f"ran {num['methods']} methods on {num['odes']} ODEs, {num['scorable']} of them scorable "
        f"{c('N9', 'N1')}. The audit's findings concern how the parts were connected and scored, "
        "not whether the code runs.</p>"
        "</section>"
    )


def _more_section(data):
    snapshot = fmt.day(data["sources"]["snapshot_date"])
    return (
        '<section aria-labelledby="read-more">'
        '<h2 id="read-more">Where the numbers are</h2>'
        "<p>The diagrams describe the code as of the snapshot on "
        f"{snapshot}. Results for the rk run are on "
        '<a href="rk.html">The rk run</a>, its epochs and research practice on '
        '<a href="epochs.html">Epochs and research</a>, the 2025 results on '
        '<a href="novel.html">The 2025 ML project</a>, every verdict on '
        '<a href="claims.html">Claims audit</a>, and the source code and commits on '
        '<a href="repos.html">Repositories</a>.</p>'
        "</section>"
    )


def build(data):
    return (
        "<h1>How the two projects are built</h1>"
        '<p class="lead">The rk run is a long-lived system: a container that searches and '
        "scores, a host that keeps it running and publishes its data, and two websites that "
        "read the results. The 2025 ML project is a training pipeline that generated Butcher "
        "tables, integrated generated ODEs with them and scored them against a reference "
        "solver. The second diagram marks where an audit in September 2026 found that pipeline "
        "broke.</p>"
        + _rk_section(data)
        + _novel_section(data)
        + _more_section(data)
    )
