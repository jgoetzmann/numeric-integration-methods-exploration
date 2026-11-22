"""A mechanical check of the site text against the main ASD-STE100 writing rules.

ASD-STE100 (Simplified Technical English) has a controlled dictionary and a set of writing
rules. This script does not hold the dictionary. It checks the rules that a machine can check
without it, on every sentence of the built pages:

  length      at most 20 words in a procedure step (an <li> in an <ol>), at most 25 in
              other text
  paragraph   at most 6 sentences in a paragraph
  passive     no "be" verb before a past participle (a simple pattern, so it is approximate)
  ing         no -ing word, other than technical names on the ALLOWED_ING list
  words       no word from a short list of words that STE does not approve, each with the
              STE word to use in its place
  contraction no contractions ("don't", "it's")

Technical names (method names, file paths, numbers, code) are taken out before the check.
The target for this site is that at least 80% of sentences pass every rule.

    python site/ste_check.py docs/index.html        # prints the score and the failures
"""
from __future__ import annotations

import html
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

MAX_DESCRIPTIVE = 25
MAX_PROCEDURE = 20
MAX_PARAGRAPH = 6
TARGET = 0.80

# -ing words that are technical names here, or that are not verb forms.
ALLOWED_ING = {
    "rounding", "weighting", "weightings", "training", "scoring", "string", "nothing", "something",
    "anything", "everything", "thing", "things", "during", "bring", "king", "ring", "spring",
    "swing", "wing", "ceiling", "building", "warning", "warnings", "setting", "settings",
    "timing", "learning", "computing", "engineering", "testing", "sing", "ping", "floating",
}

# Words that STE does not approve, with the word to use. A short list, not the dictionary.
NOT_APPROVED = {
    "utilize": "use", "utilise": "use", "approximately": "about", "obtain": "get",
    "obtained": "got", "demonstrate": "show", "demonstrates": "shows", "regarding": "about",
    "however": "but", "therefore": "(two sentences)", "thus": "(two sentences)",
    "hence": "(two sentences)", "via": "through", "whilst": "while", "numerous": "many",
    "commence": "start", "terminate": "stop", "facilitate": "help", "additional": "more",
    "prior": "before", "subsequent": "after", "subsequently": "after", "sufficient": "enough",
    "require": "need", "requires": "needs", "required": "necessary", "assist": "help",
    "perform": "do", "performs": "does", "performed": "did", "possess": "have",
    "indicate": "show", "indicates": "shows", "attempt": "try", "ensure": "make sure",
    "etc": "(name the items)", "e.g": "for example", "i.e": "that is", "very": "(delete)",
    "really": "(delete)", "basically": "(delete)", "simply": "(delete)",
}

BE = r"(?:is|are|was|were|be|been|being|am)"
# Past participles that are adjectives here, not passives.
ADJECTIVE_PARTICIPLES = {
    "pinned", "fixed", "frozen", "based", "done", "complete", "open", "closed", "known",
    "used", "needed", "stated", "set", "found", "out", "built", "same", "true", "free",
    "untrained", "seeded", "scored", "occupied", "held", "ended", "over", "mixed",
}
PASSIVE = re.compile(rf"\b{BE}\s+(?:\w+ly\s+)?(\w+(?:ed|en)|built|made|kept|set|found|shown|run|held|put|said|seen|told|given|known|done|sent)\b",
                     re.IGNORECASE)
CONTRACTION = re.compile(r"\b\w+(?:n't|'re|'ve|'ll|'d|'m)\b|\b(?:it|that|there|what)'s\b", re.IGNORECASE)


class _Text(HTMLParser):
    """Collect paragraphs: the text of each <p>, <li>, <h2>, <h3>, <dd>, <td> and <summary>."""

    BLOCKS = {"p", "li", "dd", "td", "summary", "figcaption", "h1", "h2", "h3"}
    SKIP = {"script", "style", "code", "pre", "kbd", "svg", "button", "select", "option"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[tuple[str, bool]] = []   # (text, is_procedure_step)
        self.stack: list[str] = []
        self.buf: list[str] = []
        self.skip = 0
        self.lists: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        if tag in ("ol", "ul"):
            self.lists.append(tag)
        if tag in self.BLOCKS:
            self._flush()
            self.stack.append(tag)
        a = dict(attrs)
        if "data-ste-skip" in a:
            self.skip += 1
            self.stack.append("@skip:" + tag)

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1] == "@skip:" + tag:
            self.stack.pop()
            self.skip -= 1
        if tag in self.SKIP:
            self.skip -= 1
        if tag in self.BLOCKS:
            self._flush()
            if self.stack and self.stack[-1] == tag:
                self.stack.pop()
        if tag in ("ol", "ul") and self.lists:
            self.lists.pop()

    def handle_data(self, data):
        if self.skip == 0 and self.stack:
            self.buf.append(data)
        elif self.skip > 0 and self.stack:
            self.buf.append(" X ")          # a technical name or code: counts as one word

    def _flush(self):
        t = " ".join("".join(self.buf).split())
        if t:
            proc = bool(self.stack) and self.stack[-1] == "li" and bool(self.lists) and self.lists[-1] == "ol"
            heading = bool(self.stack) and self.stack[-1] in ("h1", "h2", "h3", "summary", "td")
            self.out.append((t, proc if not heading else None))
        self.buf = []


def sentences(text: str) -> list[str]:
    t = re.sub(r"\b(\d+)\.(\d+)", r"\1_\2", text)            # 2.95 is one token
    t = re.sub(r"\b(vs|e\.g|i\.e|Fig|No)\.", r"\1", t)
    parts = re.split(r"(?<=[.!?])\s+", t)
    return [p.strip() for p in parts if len(p.split()) > 0]


def words(sentence: str) -> list[str]:
    s = re.sub(r"\([^)]*\)", " ", sentence)                  # a parenthesis is a note, not a clause
    return [w for w in re.split(r"[\s/]+", s) if re.search(r"[A-Za-z0-9]", w)]


def check_sentence(s: str, procedure: bool) -> list[str]:
    fails = []
    n = len(words(s))
    cap = MAX_PROCEDURE if procedure else MAX_DESCRIPTIVE
    if n > cap:
        fails.append(f"length {n}>{cap}")
    for m in PASSIVE.finditer(s):
        if m.group(1).lower() not in ADJECTIVE_PARTICIPLES:
            fails.append(f"passive '{m.group(0)}'")
            break
    for w in re.findall(r"[A-Za-z][A-Za-z-]*ing\b", s):
        base = w.lower().split("-")[-1]
        if base not in ALLOWED_ING and not w[0].isupper():
            fails.append(f"-ing '{w}'")
            break
    for w in re.findall(r"[A-Za-z][A-Za-z.]*", s):
        k = w.lower().rstrip(".")
        if k in NOT_APPROVED:
            fails.append(f"word '{w}' -> {NOT_APPROVED[k]}")
            break
    if CONTRACTION.search(s):
        fails.append("contraction")
    return fails


def check_html(doc: str) -> dict:
    p = _Text()
    p.feed(doc)
    p._flush()
    total = passed = 0
    failures = []
    long_paragraphs = []
    for text, proc in p.out:
        if proc is None:              # headings and table cells: not sentences
            continue
        ss = sentences(html.unescape(text))
        if len(ss) > MAX_PARAGRAPH:
            long_paragraphs.append((len(ss), text[:80]))
        for s in ss:
            if len(words(s)) < 3:     # labels and fragments
                continue
            total += 1
            f = check_sentence(s, bool(proc))
            if f:
                failures.append((s, f))
            else:
                passed += 1
    return {"sentences": total, "passed": passed, "score": passed / total if total else 1.0,
            "failures": failures, "long_paragraphs": long_paragraphs}


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    files = [Path(a) for a in argv] or [Path(__file__).resolve().parent.parent / "docs" / "index.html"]
    ok = True
    for f in files:
        r = check_html(f.read_text(encoding="utf-8"))
        print(f"{f}: {r['passed']}/{r['sentences']} sentences pass ({r['score']:.0%}); "
              f"{len(r['long_paragraphs'])} paragraphs over {MAX_PARAGRAPH} sentences")
        for s, why in r["failures"]:
            print(f"  - {', '.join(why)}: {s[:140]}")
        for n, t in r["long_paragraphs"]:
            print(f"  - paragraph of {n} sentences: {t}")
        ok = ok and r["score"] >= TARGET and not r["long_paragraphs"]
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
