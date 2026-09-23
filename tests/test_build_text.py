"""Number and wording tests: B9, B10 and B11 of .fullsend/SPEC.md, plus the web.fmt worked examples.

The B9 rule is implemented here from the spec's text. The allowed set is built
from data/rk.json, data/novel.json and data/sources.json with this file's own
copies of the fmt formulas, so a wrong web.fmt cannot make a page pass. A
separate test checks web.fmt against those same formulas.

Reading of the B9 token regex: the spec's \\d[\\d,]* also swallows a comma used
as punctuation ("cycle 33, and"). Commas count only between digits here;
.fullsend/notes/spec-gaps-build.md explains why.
"""
from __future__ import annotations

import html as html_lib
import importlib
import json
import math
import os
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

SLUGS = [
    "index.html",
    "rk.html",
    "novel.html",
    "architecture.html",
    "epochs.html",
    "claims.html",
    "repos.html",
]
BANNED = (
    "novel",
    "first",
    "beats",
    "outperforms",
    "breakthrough",
    "proves",
    "proven",
    "state-of-the-art",
    "best-ever",
    "revolutionary",
    "groundbreaking",
    "cutting-edge",
    "unprecedented",
    "optimal",
    "delve",
    "crucial",
    "pivotal",
    "showcase",
    "testament",
    "seamless",
    "leverage",
    "robust",
)
EM_DASH = "\u2014"
EXCLUDED = frozenset({"code", "q", "blockquote", "svg", "script", "style"})
BREAKING = frozenset(
    {
        "address", "article", "aside", "body", "br", "caption", "dd", "details", "div", "dl",
        "dt", "figcaption", "figure", "footer", "form", "h1", "h2", "h3", "h4", "h5", "h6",
        "head", "header", "hr", "html", "li", "main", "nav", "ol", "p", "pre", "section",
        "summary", "table", "tbody", "td", "tfoot", "th", "thead", "title", "tr", "ul",
    }
)


# --------------------------------------------------------------------------- spec formulas (inline copies)


def _count(n) -> str:
    return f"{int(n):,}"


def _sig(x, digits=3) -> str:
    if x == 0:
        return "0"
    magnitude = abs(x)
    if 1e-4 <= magnitude < 1000:
        return f"{x:.{digits}g}"
    if 1000 <= magnitude < 1e15:
        return _count(round(x))
    return f"{x:.{digits - 1}e}"


def _ratio(x, digits=3) -> str:
    return _sig(x, digits) + "x"


def _pct(x, decimals=1) -> str:
    return f"{x * 100:.{decimals}f}%"


# --------------------------------------------------------------------------- numbers in the data

NUMBER_IN_STRING = re.compile(r"\d(?:,?\d)*(?:\.\d+)?(?:[eE][+-]\d+)?")


def _collect(obj, out: list) -> None:
    if obj is None or isinstance(obj, bool):
        return
    if isinstance(obj, int):
        out.append(obj)
    elif isinstance(obj, float):
        if math.isfinite(obj):
            out.append(obj)
    elif isinstance(obj, str):
        for match in NUMBER_IN_STRING.finditer(obj):
            text = match.group().replace(",", "")
            if "." in text or "e" in text.lower():
                value = float(text)
                if math.isfinite(value):
                    out.append(value)
            else:
                out.append(int(text))
    elif isinstance(obj, list):
        for item in obj:
            _collect(item, out)
    elif isinstance(obj, dict):
        for item in obj.values():
            _collect(item, out)


def _data_values() -> list:
    values: list = []
    for name in ("rk.json", "novel.json", "sources.json"):
        _collect(json.loads((REPO / "data" / name).read_text(encoding="utf-8")), values)
    unique = {}
    for value in values:
        unique.setdefault((type(value).__name__, value), value)
    return list(unique.values())


VALUES = _data_values()


def _allowed_with(count, sig, ratio, pct) -> set[str]:
    allowed = set()
    for value in VALUES:
        allowed.add(count(value))
        for digits in (2, 3, 4):
            allowed.add(sig(value, digits))
            allowed.add(ratio(value, digits))
        for decimals in (0, 1, 2):
            allowed.add(pct(value, decimals))
        if float(value).is_integer():
            allowed.add(str(int(value)))
    return allowed


ALLOWED = _allowed_with(_count, _sig, _ratio, _pct)


# --------------------------------------------------------------------------- B9 token rule

TOKEN = re.compile(r"\d(?:,?\d)*(?:\.\d+)?(?:e[+-]\d+)?[x%]?")
ISO_DATE = re.compile(
    r"(?<![\d.,])\d{4}-\d{2}(?:-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?)?(?!\d)"
)
ISO_TIME = re.compile(r"(?<![\d.:])\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?Z?(?![\d:])")
VERSION = re.compile(r"(?<![\d.])\d+(?:\.\d+){2,}(?!\d)")


def _letterish(ch: str) -> bool:
    return ch != "" and (ch.isalpha() or ch == "_")


def _number_tokens(text: str) -> list[tuple[str, int]]:
    """(token, start) for every number token the B9 rule checks, skips removed."""
    masks = [m.span() for rx in (ISO_DATE, ISO_TIME, VERSION) for m in rx.finditer(text)]
    tokens = []
    for match in TOKEN.finditer(text):
        start, end = match.span()
        token = match.group()
        if any(start < mask_end and mask_start < end for mask_start, mask_end in masks):
            continue
        before = text[start - 1] if start >= 1 else ""
        before2 = text[start - 2] if start >= 2 else ""
        after = text[end] if end < len(text) else ""
        after2 = text[end + 1] if end + 1 < len(text) else ""
        if _letterish(before) or (before == "-" and before2.isalpha()):
            continue
        if _letterish(after) or (after == "-" and after2.isalpha()):
            continue
        if re.fullmatch(r"\d{4}", token) and 1900 <= int(token) <= 2099:
            continue
        tokens.append((token, start))
    return tokens


def _bad_tokens(text: str, allowed: set[str]) -> list[str]:
    bad = []
    for token, start in _number_tokens(text):
        if token not in allowed:
            context = " ".join(text[max(0, start - 40) : start + len(token) + 40].split())
            bad.append(f"{token!r} in ...{context}...")
    return bad


# --------------------------------------------------------------------------- visible text


class _VisibleText(HTMLParser):
    """Text outside code, q, blockquote, svg, script and style; block boundaries become spaces."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in EXCLUDED:
            self.depth += 1
            self.parts.append(" ")
        elif tag in BREAKING:
            self.parts.append(" ")

    def handle_startendtag(self, tag, attrs):
        if tag in EXCLUDED or tag in BREAKING:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in EXCLUDED:
            self.depth = max(0, self.depth - 1)
            self.parts.append(" ")
        elif tag in BREAKING:
            self.parts.append(" ")

    def handle_data(self, data):
        if self.depth == 0:
            self.parts.append(data)


def _visible_text(html: str) -> str:
    parser = _VisibleText()
    parser.feed(html)
    parser.close()
    return "".join(parser.parts)


def _banned_hits(text: str) -> list[str]:
    hits = []
    if EM_DASH in text:
        index = text.index(EM_DASH)
        hits.append(f"em dash in ...{' '.join(text[max(0, index - 40) : index + 40].split())}...")
    for word in BANNED:
        match = re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", text, flags=re.IGNORECASE)
        if match:
            start = match.start()
            hits.append(f"{word!r} in ...{' '.join(text[max(0, start - 40) : start + 40].split())}...")
    return hits


# --------------------------------------------------------------------------- build fixture


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("build_text")
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    proc = subprocess.run(
        [sys.executable, "tools/build.py", "--out", str(out)],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
    return {"out": out, "proc": proc}


def _page(built, slug: str) -> str:
    proc = built["proc"]
    if proc.returncode != 0:
        pytest.fail(f"tools/build.py exited {proc.returncode}\nstderr:\n{proc.stderr[-4000:]}")
    path = built["out"] / slug
    if not path.is_file():
        pytest.fail(f"{slug} was not written to the output directory")
    return path.read_text(encoding="utf-8")


def _fmt():
    return importlib.import_module("web.fmt")


# --------------------------------------------------------------------------- B9: pages


@pytest.mark.parametrize("slug", SLUGS)
def test_b9_every_number_in_visible_text_is_a_formatted_data_value(site, slug):
    """B9: every number token in the page's visible text is count/sig/ratio/pct/str(int) of a number in rk, novel or sources."""
    bad = _bad_tokens(_visible_text(_page(site, slug)), ALLOWED)
    assert bad == [], f"{slug}: {len(bad)} number tokens not traceable to data:\n" + "\n".join(bad[:25])


# --------------------------------------------------------------------------- B9: web.fmt

FMT_WORKED_EXAMPLES = [
    ("count", (141364,), "141,364"),
    ("sig", (0,), "0"),
    ("sig", (0.0286180,), "0.0286"),
    ("sig", (2.9507,), "2.95"),
    ("sig", (1.5,), "1.5"),
    ("sig", (519.17,), "519"),
    ("sig", (1991.66,), "1,992"),
    ("sig", (5577.05,), "5,577"),
    ("sig", (8.3059e211,), "8.31e+211"),
    ("sig", (1.1478e-10,), "1.15e-10"),
    ("ratio", (2.9507,), "2.95x"),
    ("pct", (0.8113,), "81.1%"),
    ("day", ("2026-09-17T17:54Z",), "2026-09-17"),
]


@pytest.mark.parametrize(
    "name, args, expected",
    FMT_WORKED_EXAMPLES,
    ids=[f"{name}{args!r}" for name, args, _ in FMT_WORKED_EXAMPLES],
)
def test_b9_fmt_reproduces_the_spec_worked_examples(name, args, expected):
    """B9: web.fmt gives the Surface's worked examples exactly (day feeds the ISO dates B9 skips)."""
    assert getattr(_fmt(), name)(*args) == expected


FMT_BOUNDARIES = [
    ("sig", (1e-4,), "0.0001"),
    ("sig", (9.99e-5,), "9.99e-05"),
    ("sig", (999.4,), "999"),
    ("sig", (1000,), "1,000"),
    ("sig", (1e15,), "1.00e+15"),
    ("sig", (-2.9507,), "-2.95"),
    ("sig", (2.9507, 4), "2.951"),
    ("count", (5577.9,), "5,577"),
]


@pytest.mark.parametrize(
    "name, args, expected",
    FMT_BOUNDARIES,
    ids=[f"{name}{args!r}" for name, args, _ in FMT_BOUNDARIES],
)
def test_b9_fmt_follows_the_range_boundaries_of_the_spec_formulas(name, args, expected):
    """B9: sig switches format at 1e-4, 1000 and 1e15 on |x|; count truncates with int(n) while sig rounds."""
    assert getattr(_fmt(), name)(*args) == expected


def test_b9_web_fmt_matches_the_spec_formulas_on_every_data_number():
    """B9: count, sig, ratio and pct, at every digits setting B9 allows and at their defaults, match the spec formulas on every data number."""
    fmt = _fmt()
    mismatches = []
    for value in VALUES:
        checks = [
            ("count", fmt.count(value), _count(value)),
            ("sig", fmt.sig(value), _sig(value)),
            ("ratio", fmt.ratio(value), _ratio(value)),
            ("pct", fmt.pct(value), _pct(value)),
        ]
        for digits in (2, 3, 4):
            checks.append((f"sig d={digits}", fmt.sig(value, digits), _sig(value, digits)))
            checks.append((f"ratio d={digits}", fmt.ratio(value, digits), _ratio(value, digits)))
        for decimals in (0, 1, 2):
            checks.append((f"pct d={decimals}", fmt.pct(value, decimals), _pct(value, decimals)))
        for label, got, want in checks:
            if got != want:
                mismatches.append(f"{label}({value!r}): got {got!r}, spec formula gives {want!r}")
    assert not mismatches, f"{len(mismatches)} mismatches:\n" + "\n".join(mismatches[:25])


def test_b4_fmt_esc_escapes_markup_and_quotes():
    """B4: fmt.esc is html.escape(str(s), quote=True), so data strings cannot open tags, scripts or attributes."""
    fmt = _fmt()
    raw = "<script>alert(\"x\")</script> & 'y' <a onclick=\"z\">"
    assert fmt.esc(raw) == html_lib.escape(raw, quote=True)
    assert "<" not in fmt.esc(raw) and '"' not in fmt.esc(raw)
    assert fmt.esc(42) == "42"


# --------------------------------------------------------------------------- B10


def _claim_fields():
    claims = json.loads((REPO / "data" / "claims.json").read_text(encoding="utf-8"))["claims"]
    for claim in claims:
        for field in ("claim", "limits", "correction"):
            text = claim.get(field)
            if isinstance(text, str) and text:
                yield claim["id"], field, text


def test_b10_claim_limits_and_correction_numbers_are_formatted_data_values():
    """B10: the B9 rule holds for the claim, limits and correction text of every claims.json entry (spec formulas)."""
    bad = [
        f"{claim_id}.{field}: {item}"
        for claim_id, field, text in _claim_fields()
        for item in _bad_tokens(text, ALLOWED)
    ]
    assert bad == [], "\n".join(bad)


def test_b10_claim_numbers_are_reproduced_by_web_fmt():
    """B10: every number token in claim, limits and correction text is produced by web.fmt from a data number."""
    fmt = _fmt()
    allowed = _allowed_with(fmt.count, fmt.sig, fmt.ratio, fmt.pct)
    bad = [
        f"{claim_id}.{field}: {item}"
        for claim_id, field, text in _claim_fields()
        for item in _bad_tokens(text, allowed)
    ]
    assert bad == [], "\n".join(bad)


# --------------------------------------------------------------------------- B11


def test_b11_banned_words_constant_is_the_spec_list_in_order():
    """B11: web.shell.BANNED_WORDS is exactly B11's list, as a tuple, in B11's order."""
    words = importlib.import_module("web.shell").BANNED_WORDS
    assert isinstance(words, tuple)
    assert words == BANNED


@pytest.mark.parametrize("slug", SLUGS)
def test_b11_no_em_dash_or_banned_word_in_visible_text(site, slug):
    """B11: the page's visible text outside code, q, blockquote and svg has no em dash and no banned whole word."""
    hits = _banned_hits(_visible_text(_page(site, slug)))
    assert hits == [], f"{slug}:\n" + "\n".join(hits)
