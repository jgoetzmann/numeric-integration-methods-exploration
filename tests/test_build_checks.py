"""Failure-path tests: B37 (banned words and em dashes stop the build) and B38 (missing data stops the build).

check_text is exercised on crafted HTML. main() is exercised in-process: for
B37 a page package's build() is monkeypatched to emit a banned word or an em
dash; for B38 web/, tools/ and a partial data/ are copied into a temporary
project so the real data files are never touched.

check_text's return shape (case of each entry, duplicates, order) is not
pinned by the spec, so results are compared as lowercased sets.
"""
from __future__ import annotations

import importlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
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
DATA_FILES = ["rk.json", "novel.json", "claims.json", "sources.json"]
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


# --------------------------------------------------------------------------- helpers


def _doc(body: str, head: str = "") -> str:
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        f"<title>Probe | Numeric integration methods</title>{head}</head>"
        f"<body><main>{body}</main></body></html>"
    )


def _check(html: str) -> list:
    return importlib.import_module("web.shell").check_text(html)


def _found(html: str) -> set[str]:
    result = _check(html)
    assert isinstance(result, list), f"check_text returned {type(result).__name__}, not list"
    return {str(item).lower() for item in result}


def _load_build_script(path: Path, monkeypatch):
    """Import a tools/build.py file as a fresh module; sys.path and sys.modules are restored afterwards."""
    monkeypatch.setattr(sys, "path", list(sys.path))
    name = f"build_script_under_test_{abs(hash(str(path)))}"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


def _data_root(tmp_path: Path, missing: tuple[str, ...]) -> Path:
    root = tmp_path / "root"
    (root / "data").mkdir(parents=True)
    for name in DATA_FILES:
        if name not in missing:
            shutil.copyfile(REPO / "data" / name, root / "data" / name)
    return root


def _copy_project(tmp_path: Path, missing: tuple[str, ...] = (), data_dir: bool = True) -> Path:
    root = tmp_path / "project"
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    shutil.copytree(REPO / "web", root / "web", ignore=ignore)
    shutil.copytree(REPO / "tools", root / "tools", ignore=ignore)
    if data_dir:
        (root / "data").mkdir()
        for name in DATA_FILES:
            if name not in missing:
                shutil.copyfile(REPO / "data" / name, root / "data" / name)
    return root


def _run_cli(root: Path, out: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    return subprocess.run(
        [sys.executable, "tools/build.py", "--out", str(out)],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )


def _main_in(root: Path, tmp_path: Path, monkeypatch, capsys) -> tuple[int, str]:
    importlib.import_module("web.data")
    monkeypatch.chdir(root)
    build = _load_build_script(root / "tools" / "build.py", monkeypatch)
    out = tmp_path / "out"
    out.mkdir()
    code = build.main(["--out", str(out)])
    return code, capsys.readouterr().err


# --------------------------------------------------------------------------- B37: check_text finds problems


@pytest.mark.parametrize("word", BANNED)
def test_b37_check_text_flags_each_banned_word(word):
    """B37: check_text reports each B11 banned word found in visible text."""
    assert _found(_doc(f"<p>This is a {word} result.</p>")) == {word}


@pytest.mark.parametrize(
    "markup, word",
    [("<p>A NOVEL result.</p>", "novel"), ("<p>First, the setup.</p>", "first")],
    ids=["upper-case", "title-case"],
)
def test_b37_check_text_matches_case_insensitively(markup, word):
    """B37: banned words are matched case-insensitively."""
    assert _found(_doc(markup)) == {word}


@pytest.mark.parametrize(
    "markup",
    [
        f"<p>The run {EM_DASH} as planned {EM_DASH} stopped.</p>",
        f"<p>held-out{EM_DASH}error</p>",
        "<p>The run &mdash; stopped.</p>",
        "<p>The run &#8212; stopped.</p>",
    ],
    ids=["spaced", "unspaced", "named-entity", "numeric-entity"],
)
def test_b37_check_text_flags_the_em_dash(markup):
    """B37: check_text reports an em dash in visible text, spaced or not, literal or as a character reference."""
    assert _found(_doc(markup)) == {EM_DASH}


@pytest.mark.parametrize(
    "markup",
    [
        "<table><tr><td>robust</td></tr></table>",
        "<table><tr><th>robust</th></tr></table>",
        "<ul><li>robust</li></ul>",
        "<h1>robust</h1>",
        '<h2 id="x">robust</h2>',
        "<h3>robust</h3>",
        "<figure><figcaption>robust</figcaption></figure>",
        '<details class="data"><summary>robust</summary></details>',
        "<table><caption>robust</caption></table>",
        "<dl><dt>robust</dt><dd>plain</dd></dl>",
        "<dl><dt>plain</dt><dd>robust</dd></dl>",
        '<p><a href="rk.html">robust</a></p>',
        "<p><em>robust</em></p>",
        "<p><span>robust</span></p>",
        "<footer>robust</footer>",
        '<nav><a href="index.html">robust</a></nav>',
        "<header>robust</header>",
        "<article><p>robust</p></article>",
        "<p>line one<br>robust</p>",
    ],
    ids=[
        "td", "th", "li", "h1", "h2", "h3", "figcaption", "summary", "caption", "dt", "dd",
        "a", "em", "span", "footer", "nav", "header", "article", "after-br",
    ],
)
def test_b37_check_text_reads_every_visible_container(markup):
    """B37: a banned word is found wherever visible text sits, not only in paragraphs."""
    assert _found(_doc(markup)) == {"robust"}


def test_b37_check_text_flags_link_text_but_not_its_attributes():
    """B37: a banned word in link text is found even when the same word also sits in attribute values."""
    assert _found(_doc('<p><a href="novel.html" title="novel">novel</a></p>')) == {"novel"}


@pytest.mark.parametrize(
    "markup",
    [
        "<p><code>x</code> robust</p>",
        "<p><q>x</q> robust</p>",
        "<blockquote><p>x</p></blockquote><p>robust</p>",
        '<svg viewBox="0 0 10 10" role="img"><title>x</title><text>x</text></svg><p>robust</p>',
        "<script>var a = 1;</script><p>robust</p>",
        "<style>p { color: black; }</style><p>robust</p>",
    ],
    ids=["code", "q", "blockquote", "svg", "script", "style"],
)
def test_b37_check_text_resumes_after_an_excluded_element_closes(markup):
    """B37: text after </code>, </q>, </blockquote>, </svg>, </script> or </style> is visible again and checked."""
    assert _found(_doc(markup)) == {"robust"}


@pytest.mark.parametrize(
    "markup",
    ["<p>novel,</p>", "<p>It is novel.</p>", "<p>(novel)</p>", "<p>novel; then</p>", "<p>novel: yes</p>"],
    ids=["comma", "period", "parentheses", "semicolon", "colon"],
)
def test_b37_check_text_treats_punctuation_as_a_word_boundary(markup):
    """B37: a banned word next to punctuation is still a whole word."""
    assert _found(_doc(markup)) == {"novel"}


def test_b37_check_text_flags_bare_text_without_tags():
    """B37: check_text treats markup-free input as visible text."""
    assert _found("A novel idea") == {"novel"}


def test_b37_check_text_reports_every_problem_in_one_page():
    """B37: several banned words and an em dash in one page are all reported."""
    found = _found(_doc(f"<p>A novel, robust method {EM_DASH} first of its kind.</p>"))
    assert found == {"novel", "robust", "first", EM_DASH}


def test_b37_check_text_reports_only_the_visible_word_in_a_mixed_page():
    """B37: with banned words in visible text, <code> and <q>, only the visible one is reported."""
    assert _found(_doc("<p>robust</p><p><code>novel</code> and <q>first</q></p>")) == {"robust"}


# --------------------------------------------------------------------------- B37: check_text stays quiet


def test_b37_check_text_returns_empty_list_for_clean_html():
    """B37: check_text returns an empty list when the page is clean."""
    html = _doc(
        "<h1>Two searches for better Runge-Kutta coefficients</h1>"
        "<p>The search found a three-stage method with 2.95x lower held-out error.</p>"
    )
    assert _check(html) == []


@pytest.mark.parametrize(
    "markup",
    [
        f"<p><code>novel {EM_DASH} first</code></p>",
        f"<p><q>novel {EM_DASH} first</q></p>",
        f"<blockquote><p>A novel {EM_DASH} first result.</p></blockquote>",
        f'<svg viewBox="0 0 10 10" role="img"><title>novel</title><desc>first {EM_DASH} robust</desc>'
        "<text>optimal</text></svg>",
        f"<script>// novel {EM_DASH} first</script>",
        f"<style>/* novel {EM_DASH} first */ p {{ color: black; }}</style>",
    ],
    ids=["code", "q", "blockquote", "svg", "script", "style"],
)
def test_b37_check_text_ignores_excluded_elements(markup):
    """B37: banned words and em dashes inside code, q, blockquote, svg, script and style are not reported."""
    assert _check(_doc(markup)) == []


def test_b37_check_text_ignores_attribute_values():
    """B37: banned words and em dashes in attribute values are not reported."""
    html = _doc(
        f'<p><a href="novel.html" title="first {EM_DASH} robust">Story</a>'
        '<img src="assets/x.svg" alt="optimal"></p>',
        head=f'<meta name="description" content="A novel {EM_DASH} first look">',
    )
    assert _check(html) == []


def test_b37_check_text_matches_whole_words_only():
    """B37: words that merely contain a banned word are not reported."""
    html = _doc(
        "<p>novelty, firstly, robustness, leveraged, Optimality, provenance, showcased, "
        "delved, pivotally, crucially, seamlessly</p>"
    )
    assert _check(html) == []


def test_b37_check_text_allows_hyphens_en_dashes_and_minus_signs():
    """B37: only the em dash character is flagged, not hyphens, en dashes or minus signs."""
    assert _check(_doc("<p>held-out error, 2025\u20132026, a - b, a \u2212 b</p>")) == []


# --------------------------------------------------------------------------- B37: main()


@pytest.mark.parametrize("slug", SLUGS)
def test_b37_main_returns_1_and_names_page_and_word(slug, monkeypatch, capsys, tmp_path):
    """B37: when a page's HTML has a banned word in visible text, main() returns 1 and prints the slug and word to stderr."""
    importlib.import_module("web.data")
    page = importlib.import_module("web.pages." + slug[: -len(".html")])
    original = page.build
    monkeypatch.setattr(page, "build", lambda data: original(data) + "<p>A groundbreaking result.</p>")
    build = _load_build_script(REPO / "tools" / "build.py", monkeypatch)
    out = tmp_path / "out"
    out.mkdir()
    code = build.main(["--out", str(out)])
    err = capsys.readouterr().err
    assert code == 1
    assert slug in err, f"stderr does not name {slug}: {err!r}"
    assert "groundbreaking" in err.lower(), f"stderr does not name the word: {err!r}"


@pytest.mark.parametrize("slug", SLUGS)
def test_b37_main_returns_1_and_names_page_for_an_em_dash(slug, monkeypatch, capsys, tmp_path):
    """B37: when a page's HTML has an em dash in visible text, main() returns 1 and prints the slug to stderr."""
    importlib.import_module("web.data")
    page = importlib.import_module("web.pages." + slug[: -len(".html")])
    original = page.build
    monkeypatch.setattr(page, "build", lambda data: original(data) + f"<p>Before {EM_DASH} after.</p>")
    build = _load_build_script(REPO / "tools" / "build.py", monkeypatch)
    out = tmp_path / "out"
    out.mkdir()
    code = build.main(["--out", str(out)])
    err = capsys.readouterr().err
    assert code == 1
    assert slug in err, f"stderr does not name {slug}: {err!r}"


# --------------------------------------------------------------------------- B38: web.data.load


def test_b38_load_returns_the_four_parsed_data_files():
    """B38: with every data file present, load returns rk, novel, claims and sources, each the parsed JSON."""
    loaded = importlib.import_module("web.data").load(REPO)
    assert isinstance(loaded, dict)
    assert set(loaded) == {"rk", "novel", "claims", "sources"}
    for key in ("rk", "novel", "claims", "sources"):
        assert loaded[key] == json.loads((REPO / "data" / f"{key}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("missing", DATA_FILES)
def test_b38_load_raises_file_not_found_naming_the_missing_file(missing, tmp_path):
    """B38: with one data file absent, web.data.load raises FileNotFoundError whose message names that file."""
    data = importlib.import_module("web.data")
    root = _data_root(tmp_path, (missing,))
    with pytest.raises(FileNotFoundError) as info:
        data.load(root)
    assert missing in str(info.value)


def test_b38_load_without_a_data_directory_raises_file_not_found(tmp_path):
    """B38: with no data directory at all, load raises FileNotFoundError naming a data file."""
    data = importlib.import_module("web.data")
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(FileNotFoundError) as info:
        data.load(empty)
    assert any(name in str(info.value) for name in DATA_FILES), str(info.value)


def test_b38_load_with_two_files_missing_names_a_missing_one(tmp_path):
    """B38: with rk.json and claims.json both absent, the FileNotFoundError names one of them."""
    data = importlib.import_module("web.data")
    root = _data_root(tmp_path, ("rk.json", "claims.json"))
    with pytest.raises(FileNotFoundError) as info:
        data.load(root)
    message = str(info.value)
    assert "rk.json" in message or "claims.json" in message, message


# --------------------------------------------------------------------------- B38: main() and the CLI


@pytest.mark.parametrize("missing", DATA_FILES)
def test_b38_main_returns_1_naming_the_missing_file(missing, tmp_path, monkeypatch, capsys):
    """B38: with one data file missing, main() returns 1 and names the file on stderr."""
    root = _copy_project(tmp_path, (missing,))
    code, err = _main_in(root, tmp_path, monkeypatch, capsys)
    assert code == 1
    assert missing in err, f"stderr does not name {missing}: {err!r}"


def test_b38_main_returns_1_without_a_data_directory(tmp_path, monkeypatch, capsys):
    """B38: with no data directory, main() returns 1 and names a data file on stderr."""
    root = _copy_project(tmp_path, data_dir=False)
    code, err = _main_in(root, tmp_path, monkeypatch, capsys)
    assert code == 1
    assert any(name in err for name in DATA_FILES), err


@pytest.mark.parametrize("missing", DATA_FILES)
def test_b38_cli_exits_1_naming_the_missing_file(missing, tmp_path):
    """B38: python tools/build.py exits 1 with a message naming the missing file, not a traceback."""
    root = _copy_project(tmp_path, (missing,))
    out = tmp_path / "out"
    out.mkdir()
    proc = _run_cli(root, out)
    assert proc.returncode == 1, f"exit {proc.returncode}; stderr:\n{proc.stderr[-3000:]}"
    assert missing in proc.stderr
    assert "Traceback" not in proc.stderr, proc.stderr[-3000:]


def test_b38_cli_exits_1_without_a_data_directory(tmp_path):
    """B38: python tools/build.py exits 1 with a message, not a traceback, when data/ is absent."""
    root = _copy_project(tmp_path, data_dir=False)
    out = tmp_path / "out"
    out.mkdir()
    proc = _run_cli(root, out)
    assert proc.returncode == 1, f"exit {proc.returncode}; stderr:\n{proc.stderr[-3000:]}"
    assert any(name in proc.stderr for name in DATA_FILES), proc.stderr
    assert "Traceback" not in proc.stderr, proc.stderr[-3000:]


def test_b38_cli_exits_1_with_two_files_missing(tmp_path):
    """B38: python tools/build.py exits 1 naming a missing file when rk.json and claims.json are both absent."""
    root = _copy_project(tmp_path, ("rk.json", "claims.json"))
    out = tmp_path / "out"
    out.mkdir()
    proc = _run_cli(root, out)
    assert proc.returncode == 1, f"exit {proc.returncode}; stderr:\n{proc.stderr[-3000:]}"
    assert "rk.json" in proc.stderr or "claims.json" in proc.stderr, proc.stderr
    assert "Traceback" not in proc.stderr, proc.stderr[-3000:]
