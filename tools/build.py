"""Build the static site from data/*.json into an output directory (default: docs/).

Usage, from the repo root:  python tools/build.py [--out DIR]
"""

import argparse
import importlib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if not sys.path or sys.path[0] != str(ROOT):
    sys.path.insert(0, str(ROOT))

import web.data  # noqa: E402
import web.shell  # noqa: E402


def _err(message: str) -> None:
    try:
        print(message, file=sys.stderr)
    except UnicodeEncodeError:
        print(message.encode("ascii", "backslashreplace").decode("ascii"), file=sys.stderr)


def _describe(word: str) -> str:
    if word == web.shell.EM_DASH:
        return f"'{word}' (em dash, U+2014)"
    return f"'{word}'"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="build.py", description="Build the static site.")
    parser.add_argument("--out", default=None, help="output directory (default: docs)")
    args = parser.parse_args(argv)
    out = pathlib.Path(args.out) if args.out is not None else ROOT / "docs"

    try:
        data = web.data.load(ROOT)
    except FileNotFoundError as exc:
        _err(f"build.py: {exc}")
        return 1

    rendered: list[tuple[str, str]] = []
    assets: dict[str, str] = {}
    problems: list[str] = []
    for slug, _label in web.shell.PAGES:
        module = importlib.import_module("web.pages." + slug.rsplit(".", 1)[0])
        page_slug = module.SLUG
        html = web.shell.page(page_slug, module.TITLE, module.DESCRIPTION, module.build(data), data)
        for word in web.shell.check_text(html):
            problems.append(f"build.py: {page_slug}: banned text in visible text: {_describe(word)}")
        rendered.append((page_slug, html))
        make_assets = getattr(module, "assets", None)
        if make_assets is not None:
            for name, text in sorted(make_assets(data).items()):
                assets[name] = text

    if problems:
        for line in problems:
            _err(line)
        return 1

    out.mkdir(parents=True, exist_ok=True)
    for page_slug, html in rendered:
        (out / page_slug).write_bytes(html.encode("utf-8"))
    (out / "style.css").write_bytes((ROOT / "web" / "style.css").read_bytes())
    (out / ".nojekyll").write_bytes(b"")
    for name in sorted(assets):
        target = out / "assets" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(assets[name].encode("utf-8"))

    print(f"build.py: wrote {len(rendered)} pages and {len(assets)} assets to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
