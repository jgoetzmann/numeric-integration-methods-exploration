"""Checks for the site. Run with: python -m pytest site"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "site"))
import build  # noqa: E402
import ste_check  # noqa: E402


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("site")
    build.build(out)
    return out


@pytest.fixture(scope="module")
def page(built):
    return (built / "index.html").read_text(encoding="utf-8")


def test_docs_is_the_build(built):
    """docs/ in the repository is exactly what build.py makes now."""
    for f in sorted(built.iterdir()):
        committed = ROOT / "docs" / f.name
        assert committed.exists(), f"docs/{f.name} is missing: run python site/build.py"
        assert committed.read_bytes() == f.read_bytes(), f"docs/{f.name} is stale: run python site/build.py"


def test_build_is_deterministic(built, tmp_path):
    build.build(tmp_path)
    for f in built.iterdir():
        assert (tmp_path / f.name).read_bytes() == f.read_bytes()


def test_no_slot_left(page):
    assert not re.search(r"\{\{\w+\}\}", page)


def test_every_claim_is_on_the_page(page):
    claims = json.loads((ROOT / "data" / "claims.json").read_text(encoding="utf-8"))["claims"]
    for c in claims:
        assert f'id="{c["id"]}"' in page


def test_internal_links_resolve(page):
    ids = set(re.findall(r'id="([^"]+)"', page))
    for target in set(re.findall(r'href="#([^"]+)"', page)):
        assert target in ids, f"#{target} has no target"


def test_evidence_files_exist(page):
    for path in set(re.findall(r'github\.com/jgoetzmann/numeric-integration-methods-exploration/(?:blob|tree)/main/([^"#]+)', page)):
        assert (ROOT / path).exists(), path


def test_headline_numbers_come_from_the_data(page):
    rk = json.loads((ROOT / "data" / "rk.json").read_text(encoding="utf-8"))
    assert f'{rk["champion"]["lead"]:.3g}x' in page
    assert f'{rk["run_end"]["records_both_epochs"]:,}' in page
    assert rk["champion"]["hash"] in page


def test_limits_stay_next_to_the_lead(page):
    """The 2.95x must not appear without its limits: the section that states it has them."""
    for phrase in ("epoch-1 result", "selection bias", "floor-rounding result", "1.01x"):
        assert phrase in page, phrase


def test_old_pages_redirect(built):
    for name in build.REDIRECTS:
        assert "location.replace" in (built / name).read_text(encoding="utf-8")


def test_text_follows_ste_rules(page):
    r = ste_check.check_html(page)
    assert r["score"] >= ste_check.TARGET, r["failures"][:10]
    assert not r["long_paragraphs"], r["long_paragraphs"]


@pytest.mark.skipif(shutil.which("node") is None, reason="needs node")
def test_browser_engine_matches_python_cases():
    js = (ROOT / "site" / "src" / "q15.js").as_posix()
    demo = (ROOT / "analysis" / "tools" / "demo_data.json").as_posix()
    script = (
        "global.document={getElementById:()=>({textContent:JSON.stringify({demo:require(%r)})})};"
        "global.window={};require(%r);window.Q15.check(s=>{if(s.done){console.log(s.pass+'/'+s.total)}});"
    ) % (demo, js)
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True, timeout=120).stdout.strip()
    assert out == "154/154", out
