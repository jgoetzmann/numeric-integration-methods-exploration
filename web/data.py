"""Load the four frozen data documents the site is built from."""

import json
import pathlib

NAMES = ("rk", "novel", "claims", "sources")


def load(root: pathlib.Path) -> dict:
    """Return {"rk", "novel", "claims", "sources"}, each the parsed root/data/<name>.json.

    Raises FileNotFoundError naming every missing file before reading any of them.
    """
    root = pathlib.Path(root)
    paths = {name: root / "data" / f"{name}.json" for name in NAMES}
    missing = [name for name in NAMES if not paths[name].is_file()]
    if missing:
        listed = ", ".join(f"{name}.json" for name in missing)
        where = ", ".join(str(paths[name]) for name in missing)
        raise FileNotFoundError(f"missing data file: {listed} (looked for {where})")
    out = {}
    for name in NAMES:
        with paths[name].open(encoding="utf-8") as fh:
            out[name] = json.load(fh)
    return out
