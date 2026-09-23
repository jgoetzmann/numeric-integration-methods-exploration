"""Claims audit page: every claim, its verdict, its limits and where to check it."""

import re

from web import fmt

SLUG = "claims.html"
TITLE = "Claims audit"
DESCRIPTION = (
    "Every claim this site makes about the rk run and the 2025 ML project, "
    "with its verdict, its limits and links to the files that show it."
)

VERDICT_LABELS = {
    "supported": "Supported",
    "supported-with-limits": "Supported with limits",
    "not-supported": "Not supported",
    "artifact": "Artifact",
}

# Verdicts whose claim text the site does not stand behind: shown inside <q>.
QUOTED_VERDICTS = ("not-supported", "artifact")

GROUPS = (
    (
        "rk",
        "The rk run",
        "The rk run's Q15 results hold inside Q15 fixed point with floor rounding "
        "at the run's fixed cycle budget, under the conditions each claim lists. "
        'In float64 the established methods win, as <a href="#R5">R5</a> records.',
    ),
    (
        "novel",
        "The 2025 ML project",
        "Where <code>Novel-Numerical-Integration-Methods</code> made a claim itself, "
        "in its README or its analysis report, this page quotes the original wording "
        "and gives the correction after it. The audit also credits what the project "
        "built and measured.",
    ),
    (
        "both",
        "Across both projects",
        "These claims cover both projects. Each rests on claims in the two groups "
        "above and links to them.",
    ),
)

_CLAIM_REF = re.compile(r"\b[RNU]\d{1,2}\b")


def _is_single_file(path):
    return ";" not in path and "*" not in path and not path.endswith("/")


def _evidence_item(ev, repos):
    repo = repos[ev["repo"]]
    path = ev["path"]
    at = ev.get("at", "")
    if _is_single_file(path):
        href = f"{repo['url']}/blob/{repo['commit']}/{path}"
        note = ""
    else:
        href = f"{repo['url']}/tree/{repo['commit']}"
        note = ' <span class="evidence-note">(the link opens the repository at this commit)</span>'
    text = f"<code>{fmt.esc(path)}</code>"
    if at:
        text += f" at <code>{fmt.esc(at)}</code>"
    return (
        f'<li><code>{fmt.esc(ev["repo"])}</code>: '
        f'<a href="{fmt.esc(href)}">{text}</a>{note}</li>'
    )


def _related(claim):
    seen = []
    for field in ("claim", "limits", "correction"):
        for ref in _CLAIM_REF.findall(claim.get(field, "") or ""):
            if ref != claim["id"] and ref not in seen:
                seen.append(ref)
    return seen


def _article(claim, repos):
    cid = claim["id"]
    verdict = claim["verdict"]
    parts = [f'<article id="{fmt.esc(cid)}" class="claim claim-{fmt.esc(verdict)}">']
    parts.append(f'<h3 class="claim-head"><a class="claim-id" href="#{fmt.esc(cid)}">{fmt.esc(cid)}</a></h3>')

    meta = (
        f'<span class="verdict verdict-{fmt.esc(verdict)}">'
        f"{fmt.esc(VERDICT_LABELS[verdict])}</span>"
    )
    if claim.get("headline"):
        meta += ' <span class="headline-tag">Headline claim on the <a href="index.html">story page</a></span>'
    parts.append(f'<p class="claim-meta">{meta}</p>')

    if verdict in QUOTED_VERDICTS:
        parts.append(f'<p class="claim-text"><strong>Claim:</strong> <q>{fmt.esc(claim["claim"])}</q></p>')
    else:
        parts.append(f'<p class="claim-text"><strong>Claim:</strong> {fmt.esc(claim["claim"])}</p>')

    if claim.get("original_wording"):
        parts.append('<p class="original-label"><strong>Original wording:</strong></p>')
        parts.append(f'<blockquote class="original-wording"><p>{fmt.esc(claim["original_wording"])}</p></blockquote>')

    if claim.get("limits"):
        parts.append(f'<p class="claim-limits"><strong>Limits:</strong> {fmt.esc(claim["limits"])}</p>')

    if claim.get("correction"):
        parts.append(f'<p class="claim-correction"><strong>Correction:</strong> {fmt.esc(claim["correction"])}</p>')

    related = _related(claim)
    if related:
        links = ", ".join(f'<a href="#{fmt.esc(r)}">{fmt.esc(r)}</a>' for r in related)
        parts.append(f'<p class="claim-related">Related claims: {links}</p>')

    items = "\n".join(_evidence_item(ev, repos) for ev in claim["evidence"])
    parts.append(
        '<div class="evidence">\n'
        '<p class="evidence-label"><strong>Evidence</strong></p>\n'
        f'<ul class="evidence-list">\n{items}\n</ul>\n'
        "</div>"
    )
    parts.append("</article>")
    return "\n".join(parts)


def _group_summary(group_claims, verdict_order):
    pieces = []
    for verdict in verdict_order:
        ids = [c["id"] for c in group_claims if c["verdict"] == verdict]
        if not ids:
            continue
        links = ", ".join(f'<a href="#{fmt.esc(i)}">{fmt.esc(i)}</a>' for i in ids)
        pieces.append(f"{fmt.esc(VERDICT_LABELS[verdict])}: {links}.")
    return '<p class="group-summary">' + " ".join(pieces) + "</p>"


def build(data: dict) -> str:
    claims_doc = data["claims"]
    sources = data["sources"]
    repos = {r["name"]: r for r in sources["repos"]}
    claims = claims_doc["claims"]
    verdict_order = [v for v in claims_doc["verdicts"] if v in VERDICT_LABELS]
    snapshot = fmt.esc(fmt.day(sources["snapshot_date"]))

    out = ["<h1>Claims audit</h1>"]
    out.append(
        '<section class="intro">\n'
        "<p>This page lists every claim this site makes about either project. Each "
        "one carries a verdict, the conditions it holds under, and links to the files "
        "that show it, pinned to the commits named in the footer. Other pages link "
        "here by claim id.</p>\n"
        "<p>The audit checked every claim against the source repositories as of the "
        f"snapshot on {snapshot}. It checked the claims about the 2025 ML project in "
        "September 2026 against that project's code and data. Where the 2025 project "
        "published a claim the files do not support, this page keeps its original "
        "wording in a block quote beside the correction.</p>\n"
        "<p>A verdict is always written out in words. Claims marked not supported are "
        "claims this site does not make; they stay listed so each correction sits next "
        "to the claim it replaces.</p>\n"
        "</section>"
    )

    legend = []
    for verdict in verdict_order:
        legend.append(
            f'<dt><span class="verdict verdict-{fmt.esc(verdict)}">'
            f"{fmt.esc(VERDICT_LABELS[verdict])}</span></dt>\n"
            f"<dd>{fmt.esc(claims_doc['verdicts'][verdict])}</dd>"
        )
    out.append(
        '<section class="verdicts">\n'
        '<h2 id="verdicts">Verdicts</h2>\n'
        '<dl class="verdict-legend">\n' + "\n".join(legend) + "\n</dl>\n"
        "</section>"
    )

    for group_id, heading, intro in GROUPS:
        group_claims = [c for c in claims if c["project"] == group_id]
        section = [f'<section class="claim-group">', f'<h2 id="{group_id}">{fmt.esc(heading)}</h2>']
        section.append(f"<p>{intro}</p>")
        section.append(_group_summary(group_claims, verdict_order))
        for claim in group_claims:
            section.append(_article(claim, repos))
        section.append("</section>")
        out.append("\n".join(section))

    return "\n".join(out) + "\n"
