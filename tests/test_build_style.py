"""Stylesheet tests: B8 of .fullsend/SPEC.md, with the palette values from its chart rules.

Reads web/style.css, the file tools/build.py copies verbatim to the output
(B1 checks the copy). The CSS is split into rules with a small brace parser
written here, since the stack allows the standard library only.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
STYLE = REPO / "web" / "style.css"

# Chart rules: token -> (light value, dark value).
PALETTE = {
    "--series-1": ("#2a78d6", "#3987e5"),
    "--series-2": ("#eb6834", "#d95926"),
    "--series-3": ("#1baf7a", "#199e70"),
    "--series-4": ("#eda100", "#c98500"),
    "--surface": ("#fcfcfb", "#1a1a19"),
    "--text-1": ("#0b0b0b", "#ffffff"),
    "--text-2": ("#52514e", "#c3c2b7"),
    "--grid": ("#e4e3df", "#383835"),
}
COLOR_VALUE = re.compile(r"^(#[0-9a-f]{3,8}|(rgb|rgba|hsl|hsla)\()", re.IGNORECASE)
FIXED_LENGTH = re.compile(r"^(\d+(?:\.\d+)?)(px|rem|em)$", re.IGNORECASE)
FIGURE_SELECTOR_MARKS = ("figure", "svg", "chart", ".data")


# --------------------------------------------------------------------------- helpers


def _declarations(body: str) -> dict[str, str]:
    declarations = {}
    for part in body.split(";"):
        if ":" not in part:
            continue
        name, value = part.split(":", 1)
        name = name.strip()
        if not name or "{" in name or "}" in name:
            continue
        declarations[name if name.startswith("--") else name.lower()] = value.strip()
    return declarations


def _parse(css: str) -> list[tuple]:
    """Nodes: ("rule", selector, declarations) or ("at", prelude, child nodes)."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)
    length = len(css)

    def block(i: int) -> tuple[list[tuple], int]:
        nodes: list[tuple] = []
        buffer: list[str] = []
        while i < length:
            ch = css[i]
            if ch == "{":
                prelude = "".join(buffer).strip()
                buffer = []
                if prelude.startswith("@"):
                    children, i = block(i + 1)
                    nodes.append(("at", prelude, children))
                    continue
                depth = 1
                j = i + 1
                while j < length and depth:
                    if css[j] == "{":
                        depth += 1
                    elif css[j] == "}":
                        depth -= 1
                    j += 1
                nodes.append(("rule", prelude, _declarations(css[i + 1 : j - 1])))
                i = j
                continue
            if ch == "}":
                return nodes, i + 1
            if ch == ";" and "".join(buffer).strip().startswith("@"):
                buffer = []
                i += 1
                continue
            buffer.append(ch)
            i += 1
        return nodes, i

    return block(0)[0]


def _nodes() -> list[tuple]:
    return _parse(STYLE.read_text(encoding="utf-8"))


def _selectors(prelude: str) -> list[str]:
    return [s.strip() for s in prelude.split(",")]


def _is_root(prelude: str) -> bool:
    return any(s.startswith(":root") for s in _selectors(prelude))


def _is_dark_media(prelude: str) -> bool:
    compact = re.sub(r"\s+", "", prelude.lower())
    return compact.startswith("@media") and "prefers-color-scheme:dark" in compact


def _root_tokens(nodes) -> dict[str, str]:
    tokens = {}
    for kind, prelude, body in nodes:
        if kind == "rule" and _is_root(prelude):
            tokens.update({k: v for k, v in body.items() if k.startswith("--")})
    return tokens


def _dark_tokens(nodes) -> tuple[bool, dict[str, str]]:
    found = False
    tokens = {}
    for kind, prelude, body in nodes:
        if kind == "at" and _is_dark_media(prelude):
            found = True
            for inner_kind, inner_prelude, inner_body in body:
                if inner_kind == "rule" and _is_root(inner_prelude):
                    tokens.update({k: v for k, v in inner_body.items() if k.startswith("--")})
    return found, tokens


def _normal_color(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.replace("!important", "").strip().lower()
    if re.fullmatch(r"#[0-9a-f]{3}", value):
        value = "#" + "".join(ch * 2 for ch in value[1:])
    return value


def _all_rules(nodes):
    for kind, prelude, body in nodes:
        if kind == "rule":
            yield prelude, body
        else:
            for inner_kind, inner_prelude, inner_body in body:
                if inner_kind == "rule":
                    yield inner_prelude, inner_body


def _narrow_screen_rules(nodes):
    """Top-level rules plus rules in @media blocks that still apply at 360px (no min-width query)."""
    for kind, prelude, body in nodes:
        if kind == "rule":
            yield prelude, body
        elif prelude.lower().startswith("@media") and "min-width" not in prelude.lower():
            for inner_kind, inner_prelude, inner_body in body:
                if inner_kind == "rule":
                    yield inner_prelude, inner_body


# --------------------------------------------------------------------------- B8


def test_b8_root_sets_the_palette_tokens():
    """B8: :root sets the color tokens, --series-1 through --series-4 among them, plus the surface, text and grid tokens."""
    tokens = _root_tokens(_nodes())
    missing = [name for name in PALETTE if name not in tokens]
    assert missing == [], f":root does not set {missing}"


def test_b8_dark_media_block_redefines_the_palette_tokens():
    """B8: @media (prefers-color-scheme: dark) redefines the palette tokens on :root."""
    found, tokens = _dark_tokens(_nodes())
    assert found, "no @media (prefers-color-scheme: dark) block"
    missing = [name for name in PALETTE if name not in tokens]
    assert missing == [], f"dark block does not redefine {missing}"


def test_b8_every_color_token_on_root_is_redefined_for_dark():
    """B8: every :root custom property holding a literal color is redefined inside the dark block."""
    nodes = _nodes()
    root = _root_tokens(nodes)
    _, dark = _dark_tokens(nodes)
    colors = sorted(name for name, value in root.items() if COLOR_VALUE.match(value.strip()))
    assert colors, ":root holds no literal color tokens"
    assert [name for name in colors if name not in dark] == []


def test_b8_light_palette_values_match_the_chart_rules():
    """B8: the :root palette tokens carry the chart rules' light values."""
    tokens = _root_tokens(_nodes())
    wrong = {
        name: tokens.get(name)
        for name, (light, _) in PALETTE.items()
        if _normal_color(tokens.get(name)) != light
    }
    assert wrong == {}


def test_b8_dark_palette_values_match_the_chart_rules():
    """B8: the dark-block palette tokens carry the chart rules' dark values."""
    _, tokens = _dark_tokens(_nodes())
    wrong = {
        name: tokens.get(name)
        for name, (_, dark) in PALETTE.items()
        if _normal_color(tokens.get(name)) != dark
    }
    assert wrong == {}


def test_b8_body_background_and_color_come_from_tokens():
    """B8: a body rule sets an explicit background and color, both through var(--...)."""
    body: dict[str, str] = {}
    for kind, prelude, declarations in _nodes():
        if kind == "rule" and "body" in _selectors(prelude):
            body.update(declarations)
    background = body.get("background-color") or body.get("background") or ""
    assert "var(--" in background, f"body background is {background!r}"
    assert "var(--" in body.get("color", ""), f"body color is {body.get('color')!r}"


def test_b8_no_fixed_width_over_360px_outside_figures():
    """B8: outside figures, no width or min-width is a fixed length over 360px (rem and em at 16px)."""
    offenders = []
    for prelude, declarations in _narrow_screen_rules(_nodes()):
        if any(mark in prelude.lower() for mark in FIGURE_SELECTOR_MARKS):
            continue
        for prop in ("width", "min-width"):
            value = declarations.get(prop, "").replace("!important", "").strip()
            match = FIXED_LENGTH.match(value)
            if not match:
                continue
            number, unit = float(match.group(1)), match.group(2).lower()
            pixels = number if unit == "px" else number * 16
            if pixels > 360:
                offenders.append(f"{prelude} {{ {prop}: {value} }}")
    assert offenders == []


def test_b8_figures_scale_with_max_width_100_percent():
    """B8: figures (or the svg inside them) scale with max-width: 100%."""
    scaling = [
        prelude
        for prelude, declarations in _all_rules(_nodes())
        if any(mark in prelude.lower() for mark in ("figure", "svg", "chart"))
        and re.sub(r"\s+", "", declarations.get("max-width", "")) == "100%"
    ]
    assert scaling, "no figure, svg or .chart rule sets max-width: 100%"
