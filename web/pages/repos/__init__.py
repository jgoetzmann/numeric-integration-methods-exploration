"""Repositories page: where the code and data behind both projects live.

One card per repository in sources.json (name, role, snapshot commit, links), how the
repositories fit together, the private-workspace sentence (stated, never linked), and
how to rebuild this site from fresh clones. Every data string goes through fmt.esc.
"""
from web import fmt

SLUG = "repos.html"
TITLE = "Repositories"
DESCRIPTION = ("Where the code and data behind both projects live, the commit this "
               "snapshot read from each, and how to rebuild this site.")

THIS_REPO_URL = "https://github.com/jgoetzmann/numeric-integration-methods-exploration"
FINDINGS_SITE = "https://jgoetzmann.github.io/rk-findings/"


def _bare(url: str) -> str:
    """A URL without its scheme or trailing slash, used as link text."""
    return url.split("://", 1)[-1].rstrip("/")


def _link(href: str, text_html: str) -> str:
    return f'<a href="{fmt.esc(href)}">{text_html}</a>'


def _cited_by(claims: list, name: str) -> list:
    """Claim ids, in claims.json order, whose evidence cites repository `name`."""
    ids = []
    for claim in claims:
        for ev in claim.get("evidence", []):
            if ev.get("repo") == name and claim["id"] not in ids:
                ids.append(claim["id"])
    return ids


def _card(repo: dict, cited: list) -> str:
    name, url, commit = repo["name"], repo["url"], repo["commit"]
    rows = [
        "<dt>Commit</dt><dd>"
        + _link(f"{url}/tree/{commit}", f"<code>{fmt.esc(commit)}</code>") + "</dd>",
        "<dt>Repository</dt><dd>"
        + _link(url, f"<code>{fmt.esc(_bare(url))}</code>") + "</dd>",
    ]
    if repo.get("site"):
        rows.append("<dt>Live site</dt><dd>"
                    + _link(repo["site"], f"<code>{fmt.esc(_bare(repo['site']))}</code>")
                    + "</dd>")
    if cited:
        rows.append("<dt>Claims that cite it</dt><dd>"
                    + ", ".join(_link(f"claims.html#{cid}", fmt.esc(cid)) for cid in cited)
                    + "</dd>")
    return "\n".join([
        f'<article class="card repo" id="repo-{fmt.esc(name)}">',
        f"<h3><code>{fmt.esc(name)}</code></h3>",
        f'<p class="role">{fmt.esc(repo["role"])}</p>',
        "<dl>",
        *rows,
        "</dl>",
        "</article>",
    ])


def build(data: dict) -> str:
    sources = data["sources"]
    repos = sources["repos"]
    claims = data["claims"]["claims"]
    snap = fmt.esc(fmt.day(sources["snapshot_date"]))

    def ref(name: str) -> str:
        return _link(f"#repo-{name}", f"<code>{fmt.esc(name)}</code>")

    harness = ref("rk-harness")
    work = ref("rk-work")
    findings = ref("rk-findings")
    overview = ref("rk-overview")
    ml = ref("Novel-Numerical-Integration-Methods")

    out = [
        "<h1>The repositories behind both projects</h1>",
        '<p class="lead">The rk run lives in four repositories on GitHub and the 2025 ML '
        "project in one. Each card gives the repository's role and the commit at its head "
        f"when this site's snapshot was taken on {snap}. Every block of figures in that "
        "snapshot also records the repository, commit, file and key it was read from, and the "
        '<a href="claims.html">claims audit</a> links each claim to the files that back it.</p>',

        "<section>",
        '<h2 id="repositories">The repositories</h2>',
        '<div class="cards">',
        *(_card(r, _cited_by(claims, r["name"])) for r in repos),
        "</div>",
        "</section>",

        "<section>",
        '<h2 id="fit">How they fit together</h2>',
        f"<p>{harness} is the code: the runner, the search, the pinned verifier, the site "
        "generator and the tests. A host watchdog starts a container that mounts the harness "
        "read-only, so the search cannot change the code that scores it "
        '(<a href="claims.html#R11">claim R11</a>).</p>',
        f"<p>Each cycle the container appends scored records to {work} and regenerates "
        f"{findings}, the findings site, and commits both. The host watchdog does the pushing, "
        f"so no credential enters the container. {work} also keeps epoch 1 frozen under "
        "<code>epochs/1/</code>, with the validation, benchmark and trace documents this site "
        'quotes (<a href="claims.html#R7">why epoch 1 froze: claim R7</a>).</p>',
        f"<p>{overview} is built by hand from {work}. Its tools recompute the analysis into "
        "<code>tools/key_findings.json</code> and generate the explainer pages, including a "
        "browser demo that reruns the Q15 solver. It is a snapshot that goes stale between "
        "refreshes, while the findings site rebuilds every cycle.</p>",
        f"<p>{ml} stands alone. It shares no code or data with the rk run; the two projects "
        "share the question they asked, and this site.</p>",
        "<p>The four rk repositories sit side by side in one private workspace, where the run "
        "is started and stopped.</p>",
        f'<p class="private-workspace">{fmt.esc(sources["private_workspace"])}.</p>',
        "<p>Every file the claims audit cites is in one of the public repositories above. The "
        '<a href="architecture.html">architecture page</a> draws both systems.</p>',
        "</section>",

        "<section>",
        '<h2 id="rebuild">How to rebuild this site</h2>',
        "<p>The source of this site is "
        + _link(THIS_REPO_URL, "<code>numeric-integration-methods-exploration</code>")
        + ". The build never reads the source repositories. It reads the snapshot in "
        "<code>data/*.json</code> and writes static pages with the Python standard library "
        "only, and the same data gives byte-identical pages.</p>",
        "<p>To refresh the numbers and rebuild:</p>",
        '<pre style="overflow-x: auto"><code>python tools/snapshot.py \\\n'
        "  --rk-workspace RK_WORKSPACE \\\n"
        "  --novel ML_2025_CLONE\n"
        "python tools/build.py</code></pre>",
        "<p><code>RK_WORKSPACE</code> is a directory holding clones of "
        f"{harness}, {work}, {findings} and {overview} side by side, and "
        f"<code>ML_2025_CLONE</code> is a clone of {ml}. The snapshot rewrites "
        "<code>data/rk.json</code>, <code>data/novel.json</code> and "
        "<code>data/sources.json</code>, recording the repository, commit, file and key behind "
        "each block of figures.</p>",
        "<p><code>data/claims.json</code>, the audit, is written by hand and the snapshot leaves "
        "it alone, so its claims need checking against the new numbers before a rebuild is "
        "published. <code>python tools/build.py --out DIR</code> writes somewhere other than "
        "<code>docs/</code>, and <code>python -m pytest tests</code> runs the checks.</p>",
        f"<p>The numbers on this site are the snapshot of {snap}. The rk run keeps going, and "
        f'<a href="{FINDINGS_SITE}">its findings site</a> has current numbers.</p>',
        "</section>",
    ]
    return "\n".join(out) + "\n"
