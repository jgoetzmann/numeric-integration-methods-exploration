"""Number, date and HTML formatting. Every number on a page goes through one of these."""

import html


def count(n) -> str:
    """int(n) with comma thousands separators: 141364 -> "141,364"."""
    return f"{int(n):,}"


def sig(x, digits=3) -> str:
    """Significant-figure formatting with the ranges fixed by the spec."""
    if x == 0:
        return "0"
    a = abs(x)
    if 1e-4 <= a < 1000:
        return f"{x:.{digits}g}"
    if 1000 <= a < 1e15:
        return count(round(x))
    return f"{x:.{digits - 1}e}"


def ratio(x, digits=3) -> str:
    """sig(x, digits) followed by "x": 2.9507 -> "2.95x"."""
    return sig(x, digits) + "x"


def pct(x, decimals=1) -> str:
    """A fraction as a percentage: 0.8113 -> "81.1%"."""
    return f"{x * 100:.{decimals}f}%"


def day(s: str) -> str:
    """The YYYY-MM-DD part of an ISO timestamp: "2026-09-17T17:54Z" -> "2026-09-17"."""
    return str(s)[:10]


def esc(s) -> str:
    """HTML-escape any value for text or a double-quoted attribute."""
    return html.escape(str(s), quote=True)
