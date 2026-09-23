"""README.md and RESUME.md content tests: B34, B35.

Written from .fullsend/SPEC.md alone. The B11 word list and the B9 number
rule are implemented inline from the spec text. Allowed numbers come from
data/rk.json, data/novel.json and data/sources.json; claim ids from
data/claims.json. Both markdown files are read from the repo root.
"""

import json
import math
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
DATA = REPO / "data"
README = REPO / "README.md"
RESUME = REPO / "RESUME.md"

SOURCES = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
CLAIMS_DOC = json.loads((DATA / "claims.json").read_text(encoding="utf-8"))
CLAIM_ID_SET = frozenset(c["id"] for c in CLAIMS_DOC["claims"])
REPOS = SOURCES["repos"]

# Surface: web.shell.SITE_URL
SITE_URL = "https://jgoetzmann.github.io/numeric-integration-methods-exploration/"

# B11, in this order (web.shell.BANNED_WORDS).
BANNED_WORDS = (
    "novel", "first", "beats", "outperforms", "breakthrough", "proves", "proven",
    "state-of-the-art", "best-ever", "revolutionary", "groundbreaking", "cutting-edge",
    "unprecedented", "optimal", "delve", "crucial", "pivotal", "showcase", "testament",
    "seamless", "leverage", "robust",
)
EM_DASH = "\u2014"


def read_md(path):
    assert path.is_file(), f"{path.name} does not exist at the repo root"
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------

def blank_fences(md):
    """Replace fenced code block lines with empty lines."""
    out = []
    fence = None
    for line in md.splitlines():
        s = line.lstrip()
        if fence is None and (s.startswith("```") or s.startswith("~~~")):
            fence = s[:3]
            out.append("")
            continue
        if fence is not None:
            if s.startswith(fence):
                fence = None
            out.append("")
            continue
        out.append(line)
    return "\n".join(out)


def strip_code(md):
    """Markdown with fenced blocks, inline code spans and HTML <code> removed."""
    text = blank_fences(md)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    text = re.sub(r"<code\b[^>]*>.*?</code>", " ", text, flags=re.S | re.I)
    text = re.sub(r"(`+)(.+?)\1", " ", text)
    return text


def visible_markdown(md):
    """Markdown text outside code, quotes and link targets: the markdown
    counterpart of visible text outside <code>, <q>, <blockquote> and
    attribute values."""
    text = strip_code(md)
    text = re.sub(r"<(q|blockquote)\b[^>]*>.*?</\1>", " ", text, flags=re.S | re.I)
    text = re.sub(r"(?m)^[ \t]*>.*$", " ", text)
    text = re.sub(r"\]\([^)]*\)", "]", text)
    text = re.sub(r"<https?://[^>]*>", " ", text)
    text = re.sub(r"(?m)^[ \t]*\[[^\]]+\]:[ \t]*\S+.*$", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\"[^\"\n]*\"", " ", text)
    text = re.sub("\u201c[^\u201d\n]*\u201d", " ", text)
    return text


def link_targets(md):
    """Every URL in the markdown outside code: inline and reference link
    targets, autolinks and bare URLs."""
    urls = re.findall(r"https?://[^\s<>()\[\]`\"']+", strip_code(md))
    return {u.rstrip(".,;:!?") for u in urls}


HEADING_RE = re.compile(r"^ {0,3}(#{1,6})[ \t]+(.*?)[ \t]*#*[ \t]*$")
SETEXT_RE = re.compile(r"^ {0,3}(=+|-+)[ \t]*$")


def md_sections(md):
    """(level, title, body) for every heading outside fenced code. The body runs
    to the next heading of the same or a higher level and keeps fenced code."""
    lines = md.splitlines()
    heads = []
    fence = None
    for i, line in enumerate(lines):
        s = line.lstrip()
        if fence is None and (s.startswith("```") or s.startswith("~~~")):
            fence = s[:3]
            continue
        if fence is not None:
            if s.startswith(fence):
                fence = None
            continue
        m = HEADING_RE.match(line)
        if m:
            heads.append((i, len(m.group(1)), m.group(2).strip()))
            continue
        if (
            line.strip()
            and not re.match(r"^\s*([-*+>|#]|\d+[.)])", line)
            and i + 1 < len(lines)
            and SETEXT_RE.match(lines[i + 1])
        ):
            level = 1 if lines[i + 1].strip().startswith("=") else 2
            heads.append((i, level, line.strip()))
    out = []
    for k, (i, level, title) in enumerate(heads):
        end = len(lines)
        for j, lvl, _ in heads[k + 1:]:
            if lvl <= level:
                end = j
                break
        out.append((level, title, "\n".join(lines[i + 1:end])))
    return out


def top_level_bullets(md):
    """Text of each unindented '-', '*' or '+' list item: its marker line plus
    continuation lines up to a blank line, a nested list, a heading or a quote."""
    bullets = []
    current = None
    for raw in blank_fences(md).splitlines():
        stripped = raw.strip()
        top = re.match(r"^[-*+][ \t]+(\S.*)$", raw)
        if top:
            current = [top.group(1).strip()]
            bullets.append(current)
            continue
        if not stripped:
            current = None
            continue
        if current is None:
            continue
        if re.match(r"^\s*([-*+]|\d+[.)])[ \t]+", raw) or stripped.startswith(("#", ">")):
            current = None
            continue
        current.append(stripped)
    return [" ".join(parts) for parts in bullets]


CLAIM_LIST_TAIL_RE = re.compile(
    r"\(claims?[ \t]+[A-Z][0-9]+(?:(?:[ \t]*,[ \t]*(?:and[ \t]+)?|[ \t]+and[ \t]+)[A-Z][0-9]+)*\)$"
)
CLAIM_LIST_ANY_RE = re.compile(r"\(claims?[ \t]+([^)]*)\)")


# ---------------------------------------------------------------------------
# B9 number rule, inline
# ---------------------------------------------------------------------------

def fmt_count(n):
    return f"{int(n):,}"


def fmt_sig(x, digits=3):
    if x == 0:
        return "0"
    ax = abs(x)
    if 1e-4 <= ax < 1000:
        return f"{x:.{digits}g}"
    if 1000 <= ax < 1e15:
        return fmt_count(round(x))
    return f"{x:.{digits - 1}e}"


def fmt_ratio(x, digits=3):
    return fmt_sig(x, digits) + "x"


def fmt_pct(x, decimals=1):
    return f"{x * 100:.{decimals}f}%"


# Numbers inside JSON string values; a comma belongs to a number only when a digit follows.
STRING_NUMBER_RE = re.compile(r"\d(?:\d|,(?=\d))*(?:\.\d+)?(?:e[+-]\d+)?")


def data_numbers():
    values = []

    def walk(obj):
        if isinstance(obj, bool) or obj is None:
            return
        if isinstance(obj, (int, float)):
            values.append(obj)
        elif isinstance(obj, str):
            for m in STRING_NUMBER_RE.finditer(obj):
                tok = m.group(0).replace(",", "")
                try:
                    values.append(float(tok) if ("." in tok or "e" in tok) else int(tok))
                except ValueError:
                    pass
        elif isinstance(obj, dict):
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)

    for name in ("rk", "novel", "sources"):
        walk(json.loads((DATA / f"{name}.json").read_text(encoding="utf-8")))
    return values


def allowed_number_strings():
    out = set()
    for v in data_numbers():
        if isinstance(v, float) and not math.isfinite(v):
            continue
        out.add(fmt_count(v))
        for d in (2, 3, 4):
            out.add(fmt_sig(v, d))
            out.add(fmt_ratio(v, d))
        for d in (0, 1, 2):
            out.add(fmt_pct(v, d))
        if isinstance(v, int) or float(v).is_integer():
            out.add(str(int(v)))
    return out


ALLOWED_NUMBERS = allowed_number_strings()

TOKEN_RE = re.compile(r"\d(?:\d|,(?=\d))*(?:\.\d+)?(?:e[+-]\d+)?[x%]?")
ISO_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?"
    r"|\b\d{1,2}:\d{2}(?::\d{2})?Z?\b"
)
VERSION_RE = re.compile(r"\d+\.\d+\.\d+")
YEAR_RE = re.compile(r"(?:19|20)\d\d")


def number_violations(text):
    """Number tokens in `text` that are not a formatted value of a data number (B9)."""
    text = ISO_RE.sub(" ", text)
    text = VERSION_RE.sub(" ", text)
    bad = []
    for m in TOKEN_RE.finditer(text):
        tok = m.group(0)
        s, e = m.start(), m.end()
        before = text[s - 1] if s >= 1 else ""
        before2 = text[s - 2] if s >= 2 else ""
        after = text[e] if e < len(text) else ""
        after2 = text[e + 1] if e + 1 < len(text) else ""
        if before.isalpha() or before == "_" or (before == "-" and before2.isalpha()):
            continue
        if after.isalpha() or after == "_" or (after == "-" and after2.isalpha()):
            continue
        if YEAR_RE.fullmatch(tok):
            continue
        if tok not in ALLOWED_NUMBERS:
            bad.append(tok)
    return bad


# ---------------------------------------------------------------------------
# B34: README.md
# ---------------------------------------------------------------------------

def test_b34_readme_contains_site_url():
    """B34: README.md contains the SITE_URL."""
    assert SITE_URL in read_md(README), f"README.md does not contain {SITE_URL}"


@pytest.mark.parametrize("repo", REPOS, ids=[r["name"] for r in REPOS])
def test_b34_readme_links_repo_url(repo):
    """B34: README.md links to every repo url in sources.json."""
    targets = link_targets(read_md(README))
    assert repo["url"] in targets or repo["url"] + "/" in targets, (
        f"README.md has no link to {repo['url']}"
    )


def test_b34_readme_build_section_has_exact_command():
    """B34: README.md has a "Build" section containing the exact command python tools/build.py."""
    sections = md_sections(read_md(README))
    builds = [body for _, title, body in sections if title.strip().rstrip(":").strip().lower() == "build"]
    assert builds, f"README.md has no Build heading; headings: {[t for _, t, _ in sections]}"
    assert any("python tools/build.py" in body for body in builds), (
        "README.md Build section does not contain the command `python tools/build.py`"
    )


def test_b34_readme_has_no_em_dash():
    """B34: README.md has no em dash outside backticks and quotes."""
    text = visible_markdown(read_md(README))
    lines = [line for line in text.splitlines() if EM_DASH in line]
    assert lines == [], f"README.md has em dashes: {lines}"


@pytest.mark.parametrize("word", BANNED_WORDS)
def test_b34_readme_free_of_banned_word(word):
    """B34: README.md does not use this B11 word, whole word and case-insensitive, outside backticks and quotes."""
    text = visible_markdown(read_md(README))
    pattern = re.compile(r"\b" + re.escape(word) + r"\b", re.IGNORECASE)
    lines = [line.strip() for line in text.splitlines() if pattern.search(line)]
    assert lines == [], f"README.md uses {word!r} outside code and quotes: {lines}"


# ---------------------------------------------------------------------------
# B35: RESUME.md
# ---------------------------------------------------------------------------

def test_b35_resume_has_three_to_six_top_level_bullets():
    """B35: RESUME.md has between three and six top-level bullet points."""
    bullets = top_level_bullets(read_md(RESUME))
    assert 3 <= len(bullets) <= 6, f"RESUME.md has {len(bullets)} top-level bullets: {bullets}"


def test_b35_every_bullet_ends_with_claim_ids():
    """B35: each RESUME.md bullet ends with a parenthesized list of claim ids, like "(claims R1, R5)"."""
    bullets = top_level_bullets(read_md(RESUME))
    assert bullets, "RESUME.md has no top-level bullets"
    bad = [b for b in bullets if not CLAIM_LIST_TAIL_RE.search(b.rstrip().rstrip("*_").rstrip())]
    assert bad == [], f"bullets that do not end with a (claims ...) list: {bad}"


def test_b35_cited_claim_ids_exist_in_claims_json():
    """B35: every claim id a RESUME.md bullet cites exists in claims.json."""
    bullets = top_level_bullets(read_md(RESUME))
    cited = []
    for b in bullets:
        for m in CLAIM_LIST_ANY_RE.finditer(b):
            cited.extend(re.findall(r"[A-Z]+[0-9]+", m.group(1)))
    assert cited, "RESUME.md bullets cite no claim ids"
    unknown = sorted(set(cited) - CLAIM_ID_SET)
    assert unknown == [], f"RESUME.md cites claim ids missing from claims.json: {unknown}"


def test_b35_every_number_passes_the_b9_rule():
    """B35: every number in RESUME.md is a formatted value of a number in rk.json, novel.json or sources.json (B9)."""
    text = visible_markdown(read_md(RESUME))
    bad = number_violations(text)
    assert bad == [], f"RESUME.md numbers not traceable to data/*.json: {bad}"
