"""The page shell (head, header, nav, footer) and the banned-text check."""

import re
from html.parser import HTMLParser

from web.fmt import day, esc

SITE_NAME = "Numeric integration methods"
SITE_URL = "https://jgoetzmann.github.io/numeric-integration-methods-exploration/"
PAGES: list[tuple[str, str]] = [
    ("index.html", "Story"), ("rk.html", "The rk run"), ("novel.html", "The 2025 ML project"),
    ("architecture.html", "Architecture"), ("epochs.html", "Epochs and research"),
    ("claims.html", "Claims audit"), ("repos.html", "Repositories")]

BANNED_WORDS: tuple[str, ...] = (
    "novel", "first", "beats", "outperforms", "breakthrough", "proves", "proven",
    "state-of-the-art", "best-ever", "revolutionary", "groundbreaking", "cutting-edge",
    "unprecedented", "optimal", "delve", "crucial", "pivotal", "showcase", "testament",
    "seamless", "leverage", "robust",
)

EM_DASH = "\u2014"

_BANNED_RES = tuple(
    (word, re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)) for word in BANNED_WORDS
)

# Text inside these elements is exempt from the check (quotes, code, drawings, and
# non-rendered content). Attribute values are never text, so they are exempt too.
_EXEMPT_TAGS = frozenset({"code", "q", "blockquote", "svg", "script", "style"})


class _VisibleText(HTMLParser):
    """Collects text nodes that are not inside an exempt element."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.chunks: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in _EXEMPT_TAGS:
            self.depth += 1

    def handle_startendtag(self, tag, attrs):
        # A self-closing element opens and closes at once: no change in depth.
        return

    def handle_endtag(self, tag):
        if tag in _EXEMPT_TAGS and self.depth > 0:
            self.depth -= 1

    def handle_data(self, data):
        if self.depth == 0:
            self.chunks.append(data)


def check_text(html: str) -> list[str]:
    """Banned words and the em dash found in the visible text of `html`.

    Text inside <code>, <q>, <blockquote>, <svg>, <script> and <style>, and attribute
    values, are ignored. Words match case-insensitively as whole words. The result lists
    each hit once, in BANNED_WORDS order, with the em dash last. Empty when clean.
    """
    parser = _VisibleText()
    parser.feed(html)
    parser.close()
    text = "\n".join(parser.chunks)
    found = [word for word, pattern in _BANNED_RES if pattern.search(text)]
    if EM_DASH in text:
        found.append(EM_DASH)
    return found


def _nav(slug: str) -> str:
    items = []
    for href, label in PAGES:
        current = ' aria-current="page"' if href == slug else ""
        items.append(f'<li><a href="{esc(href)}"{current}>{esc(label)}</a></li>')
    return '<nav class="site-nav" aria-label="Pages">\n<ul>\n' + "\n".join(items) + "\n</ul>\n</nav>"


def _footer(data: dict) -> str:
    sources = data["sources"]
    snapshot = day(sources["snapshot_date"])
    items = []
    findings_site = None
    for repo in sources["repos"]:
        name = repo["name"]
        commit = repo["commit"]
        url = f'{repo["url"]}/tree/{commit}'
        items.append(f'<li><code><a href="{esc(url)}">{esc(name)}@{esc(commit)}</a></code></li>')
        if name == "rk-findings" and repo.get("site"):
            findings_site = repo["site"]
    lines = [
        '<footer class="site-footer">',
        f'<p>Snapshot taken <time datetime="{esc(snapshot)}">{esc(snapshot)}</time>. '
        "Every number on this site comes from <code>data/*.json</code>, read from these "
        "repositories at the commits shown:</p>",
        '<ul class="sources">',
        *items,
        "</ul>",
    ]
    if findings_site:
        lines.append(
            "<p>The findings site regenerates every cycle, so its numbers can be newer than "
            f'these: <a href="{esc(findings_site)}">rk-findings site</a>.</p>'
        )
    lines.append(
        "<p>Built by <code>tools/build.py</code> as static HTML with no JavaScript.</p>"
    )
    lines.append("</footer>")
    return "\n".join(lines)


def page(slug: str, title: str, description: str, body: str, data: dict) -> str:
    """A complete HTML5 document for one page; `body` goes inside <main>."""
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{esc(title)} | {esc(SITE_NAME)}</title>\n"
        f'<meta name="description" content="{esc(description)}">\n'
        '<meta name="color-scheme" content="light dark">\n'
        '<link rel="stylesheet" href="style.css">\n'
        "</head>\n"
        "<body>\n"
        '<a class="skip-link" href="#content">Skip to content</a>\n'
        '<header class="site-header">\n'
        f'<a class="site-name" href="index.html">{esc(SITE_NAME)}</a>\n'
        f"{_nav(slug)}\n"
        "</header>\n"
        f'<main id="content">\n{body}\n</main>\n'
        f"{_footer(data)}\n"
        "</body>\n"
        "</html>\n"
    )
