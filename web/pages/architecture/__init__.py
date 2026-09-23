"""architecture.html: how the rk run and the 2025 ML project are built.

Two diagrams (B30): figure#arch-rk for the rk run's host, container and
outputs, and figure#arch-novel for the 2025 pipeline with the parts that broke
labelled in text. Under each, a list of the components.
"""

from web import fmt

from . import diagrams

SLUG = "architecture.html"
TITLE = "Architecture"
DESCRIPTION = (
    "How the rk run's container, host and sites fit together, and how the 2025 ML "
    "pipeline was wired and where it broke."
)

NOVEL_REPO = "Novel-Numerical-Integration-Methods"


def _repo(sources, name):
    for r in sources["repos"]:
        if r["name"] == name:
            return r


def _site_link(sources, name, text):
    repo = _repo(sources, name)
    return f'<a href="{fmt.esc(repo["site"])}">{fmt.esc(text)}</a>'


def _code(s):
    return f"<code>{fmt.esc(s)}</code>"


def _ln(cid, inner_html):
    """A phrase linked to its entry on the claims page."""
    return f'<a href="claims.html#{fmt.esc(cid)}">{inner_html}</a>'


def _item(name, sentence):
    return f"<li><strong>{fmt.esc(name)}.</strong> {sentence}</li>"


def _rk_section(data):
    rk = data["rk"]
    sources = data["sources"]
    num = diagrams.rk_numbers(rk)
    snapshot = fmt.day(sources["snapshot_date"])
    heldout = diagrams.and_list(_code(p) for p in num["heldout"])

    items = [
        _item("Watchdog",
              "A PowerShell script on the host kills the container on a stale heartbeat, stops "
              "it on language-model API spend or low disk, pauses it on battery power or "
              "foreground CPU load, and pushes the run's repositories to GitHub. Epoch 2 lost "
              f"five days to {_ln('R12', 'a stop that nothing restarted')}, so since decision "
              "D46 the watchdog resumes the stops it made itself."),
        _item("Stats file",
              f"The host writes {_code('stats.txt')}, not the container, so the file can still "
              "report a dead container. It never carries a value forward, and it claims nothing "
              "about the container unless Docker answered."),
        _item("Start command",
              f"Nothing starts the run at sign-in. After a reboot "
              f"{_ln('R12', 'a person starts it by hand')} with one command, "
              f"{_code('start-integration-harness')}, which brings up the container and the "
              "watchdog."),
        _item("Container",
              "The harness is mounted read-only, so "
              f"{_ln('R11', 'the search cannot change its own scorer')}. No GitHub credential "
              "enters the container: it commits, and the host "
              "pushes. The one credential inside is the model's sign-in file, mounted "
              "read-only, and the model runs in a read-only sandbox."),
        _item("Verifier",
              f"A sha256 over {num['files']} pinned files is checked at every start and stored in "
              "every record, so changing a pinned file opens a new epoch instead of editing the "
              f"old one. Epoch 1's records carry {_code(num['e1_hash'])}, over "
              f"{num['e1_files']} files, apart from {num['e1_prepin']} written minutes before "
              f"that pin was set. Epoch 2 runs under {_code(num['e2_hash'])} over "
              f"{num['e2_files']}; it started after {_ln('R7', 'a trace of the compiled step')} "
              f"showed that the old cost model had {_code('rk4')} and {_code('rk38')} in the "
              "wrong order."),
        _item("Golden gate",
              f"Before any cycle runs, {num['gate']} golden and canary cases must pass. The full "
              f"suite collected {_ln('R11', num['tests'] + ' tests')} on {num['tests_on']}."),
        _item("Runner",
              "Each cycle starts by rebuilding its state from the archive files, so a crash "
              "costs at most the cycle in progress. It then runs the directive, search, verify, "
              "score and append steps, updates the hypothesis ledger, rebuilds the findings site "
              "and commits."),
        _item("Directive",
              "A language model writes each cycle's direction as a JSON directive that "
              f"{_ln('R13', 'can only narrow the search')}, and an unknown key sends the runner "
              f"to a fixed fallback. {_ln('U2', 'The model sees held-out errors')}, and elites "
              "are picked on them."),
        _item("Search",
              "Early phases enumerate a lattice of dyadic coefficients exhaustively, and later "
              "phases run CMA-ES over the stage matrix with the weights solved exactly."),
        _item("Verify",
              "The pinned verifier checks the order conditions in exact rational arithmetic, "
              "along with explicitness, row sums, coefficient range, Q15 overflow and stability."),
        _item("Score",
              f"Each surviving candidate runs in Q15 with floor rounding at a {num['budget']}-cycle "
              f"budget, on the search problems and then on the held-out problems {heldout}. "
              f"Cycle costs come from {_ln('R7', 'a model of the Cortex-M0+')}, not from a "
              "chip."),
        _item("Archive",
              "Scored candidates are appended to per-day JSON-lines files in "
              f"{_code('rk-work')}. For each order, a MAP-Elites grid keeps the lowest held-out "
              "error in each cell of stage count and cost band. Epoch 1 wrote "
              f"{_ln('R12', num['e1_records'] + ' records')}."),
        _item("Lanes and side tracks",
              "A schedule rotates the explicit lane with adaptive and implicit lanes. Those "
              "lanes measure float64 cycles-to-tolerance, are not order-verified, and are never "
              "ranked against archive errors. Side tracks answer a fixed catalogue of design "
              "questions off the archive."),
        _item("Hypothesis ledger",
              "Each hypothesis is a predicate in a closed grammar, read by a hand-written "
              "parser. Code assigns the verdicts, not the model."),
        _item("Literature digests",
              "The model writes web digests that feed later prompts, and the findings site "
              "publishes them labelled as model-written."),
        _item("Findings site",
              "The container rebuilds "
              f"{_site_link(sources, 'rk-findings', 'the findings site')} every cycle. The build "
              "is deterministic and uses no JavaScript, and a single banned word blocks it."),
        _item("Overview site",
              f"{_site_link(sources, 'rk-overview', 'The overview site')} is built by hand from a "
              "snapshot of the run's data, so it goes stale until someone rebuilds it."),
    ]

    return (
        '<section aria-labelledby="rk-system">'
        '<h2 id="rk-system">The rk run\'s system</h2>'
        "<p>Everything that decides a score sits inside the container behind a pinned hash, and "
        "everything that keeps the run alive or publishes it sits on the host. The runner's "
        "cycle is the explicit lane, the only one whose candidates are scored into the "
        "archive.</p>"
        f'<figure id="{diagrams.RK_ID}">'
        f"{diagrams.arch_rk(data)}"
        f"<figcaption>The rk run on {snapshot}. Arrows show which part starts, controls or "
        "feeds which; the three boxes under the runner work beside the explicit "
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
    rk4 = _code("RK4")

    items = [
        _item("Generator",
              f"An MLP maps noise to table entries, but "
              f"{_ln('N4', 'its optimizer is created and never stepped')}, and its raw outputs "
              "never pass validation. Every candidate slot therefore falls back to a random "
              f"generator that reseeds to {num['seed']}, so {num['same_ab']}."),
        _item("Surrogate",
              "An MLP is trained by gradient descent on the scored candidates, at start-up and "
              f"periodically after, and the checkpoints of trials {num['ckpt_span']} record its "
              f"loss in {num['ckpt_loss']} of their {num['ckpt_epochs']} epochs. "
              f"{_ln('N4', 'Nothing in the training loop reads its predictions')}."),
        _item("Evolution",
              f"Trials {num['evo_span']} ran a genetic search whose population starts with {rk4} "
              "or Dormand-Prince plus perturbed copies of it. Selection, crossover and mutation "
              "ran and the population moved off the seed, but every score tied at the clip, so "
              f"{_ln('N2', 'the saved table stayed the seed')}: trials {num['rk4_trials']} saved "
              f"{rk4} exactly, and trial {num['dp_trials']} saved Dormand-Prince exactly."),
        _item("Random sampling",
              f"Trial {num['t16']} drew every candidate at random, with no mutation or "
              "crossover, and saved the top scorer. "
              f"{_ln('N7', 'Its fitness read an accuracy field that does not exist')}, so "
              "accuracy carried no weight."),
        _item("Stepper",
              "A fixed-step stepper reads the diagonal only while that stage is still zero and "
              "never reads the upper triangle, so an implicit table runs as its strictly lower "
              "part. Every candidate was explicit, so the gap hit only the two Gauss-Legendre "
              f"baselines, which {_ln('N5', 'ran as truncated explicit methods of order one')}."),
        _item("Reference solver",
              "Dormand-Prince (SciPy RK45) supplies each reference solution but handles only "
              f"{num['ref_families']} of the {num['eval_families']} ODE families in the final "
              f"test and {num['ref_families']} of the {num['train_families']} in training, so "
              f"{missing} problems fail for every method in the final test. Those failures, "
              "plus polynomial ODEs that blow up, give every method "
              f"{_ln('N6', 'the same ' + num['success'] + ' success rate')}."),
        _item("Composite score",
              "Weighted accuracy, efficiency and stability terms are summed, and the total is "
              f"{_ln('N2', 'clipped at ' + num['clip'])}. All {num['logged']} rows of the one "
              f"training log score {num['clip']}, and the checkpoints of trials "
              f"{num['ckpt_span']} record a best and a mean score of {num['clip']} in all "
              f"{num['ckpt_epochs']} of their epochs, so "
              f"{_ln('N3', 'the score cannot tell ' + rk4 + ' from a random table')}."),
        _item("Best-table tracker",
              "The saved table changes only on a strictly higher score, so once scores tie at the "
              "ceiling the earliest valid candidate stays best. In the evolution trials that "
              "candidate is the seeded baseline."),
    ]

    return (
        '<section aria-labelledby="novel-pipeline">'
        '<h2 id="novel-pipeline">The 2025 ML project\'s pipeline</h2>'
        f"<p>{_code(NOVEL_REPO)} proposed Butcher tables in three ways and scored all of them "
        "with one stepper and one composite score. A surrogate model trained beside them, but "
        "nothing read its predictions.</p>"
        f'<figure id="{diagrams.NOVEL_ID}">'
        f"{diagrams.arch_novel(data)}"
        f"<figcaption>The pipeline in {_code(NOVEL_REPO)} at commit {_code(commit)}. A heavy "
        f"outline and a line starting with \"{diagrams.FLAW}\" mark each part that broke, with "
        'its <a href="claims.html#novel">claim id</a> in parentheses.</figcaption>'
        "</figure>"
        '<h3 id="novel-components">Components</h3>'
        '<ul class="components">' + "".join(items) + "</ul>"
        '<h3 id="novel-holds">What still holds</h3>'
        f"<p>The harness {_ln('N9', 'runs end to end for explicit tables')}: the stepper runs "
        f"any explicit table, the training generator covers {num['train_families']} ODE "
        "families including stiff ones, and "
        f"{_ln('N1', 'the final benchmark ran ' + num['methods'] + ' methods')} on "
        f"{num['odes']} ODEs, {num['scorable']} of them scorable. Trials {num['copy_span']} "
        f"reproduce the {rk4} and Dormand-Prince errors exactly, {num['rk4_error']} and "
        f"{num['dp_error']}, so the evaluation gives the same number for the same table.</p>"
        "<p>Most of what broke was in the training code and the score: a generator optimizer "
        "that was never stepped, a fitness that read a missing field and a score clipped at "
        f"{num['clip']}. Two defects sit inside single parts: the stepper runs only the explicit "
        f"part of a table, and the reference solver covers {num['ref_families']} of the "
        f"{num['eval_families']} test families.</p>"
        "</section>"
    )


def build(data):
    people = _ln("R12", "people start it, stop it and deploy changes to its unpinned code")
    return (
        "<h1>How the two projects are built</h1>"
        '<p class="lead">The rk run is an autonomous search: no person chooses what it tries '
        f"or how it scores, though {people}. It is built as a container that searches and "
        "scores, a host that keeps it running and publishes its data, and two websites that "
        "read the results. The 2025 ML project was a training pipeline that generated Butcher "
        "tables, integrated generated ODEs with them and scored them against a reference "
        f"solver. {_ln('N4', 'Its generator was never trained')}, and because "
        f"{_ln('N2', 'its score was clipped')}, its evolutionary search saved the textbook "
        "tables it was seeded with.</p>"
        + _rk_section(data)
        + _novel_section(data)
    )
