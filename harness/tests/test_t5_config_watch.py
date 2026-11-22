"""Operational layer: config.json / configure.py, runner auto-stop limits, the watch view."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HARNESS = Path(__file__).resolve().parent.parent
WORKSPACE = HARNESS.parent
CONFIGURE = WORKSPACE / "configure.py"


@pytest.mark.skipif(not CONFIGURE.exists(), reason="workspace configure.py not present")
def test_C11_configure_set_show_reset_roundtrip(tmp_path, monkeypatch):
    # run configure.py against a copy of the workspace so the live config is untouched
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "configure.py").write_text(CONFIGURE.read_text(encoding="utf-8"), encoding="utf-8")
    run = lambda *a: subprocess.run([sys.executable, str(ws / "configure.py"), *a], capture_output=True, text=True, cwd=ws)
    p = run("set", "run.auto_stop_minutes=120", "container.cpus=6", "watchdog.battery_guard=false")
    assert p.returncode == 0, p.stderr
    data = json.loads((ws / "config.json").read_text(encoding="utf-8"))
    assert data["run"]["auto_stop_minutes"] == 120 and data["container"]["cpus"] == 6 and data["watchdog"]["battery_guard"] is False
    assert "next start" in p.stdout
    p = run("show")
    assert "run.auto_stop_minutes" in p.stdout and "120" in p.stdout
    p = run("set", "run.llm=banana")
    assert p.returncode != 0
    p = run("set", "container.cpus=0")
    assert p.returncode != 0
    p = run("set", "nope.key=1")
    assert p.returncode != 0
    p = run("set", "watchdog.cpu_pause_low_percent=90")
    assert p.returncode != 0 and "below" in p.stderr + p.stdout
    p = run("reset", "run.auto_stop_minutes")
    assert p.returncode == 0
    assert json.loads((ws / "config.json").read_text(encoding="utf-8"))["run"]["auto_stop_minutes"] == 0
    p = run("explain")
    assert p.returncode == 0 and "run.auto_stop_minutes" in p.stdout


@pytest.mark.slow
def test_C12_runner_stops_on_cycle_and_time_limits(tmp_path, monkeypatch):
    work = tmp_path / "work"
    monkeypatch.setenv("RK_WORK_DIR", str(work))
    monkeypatch.setenv("RK_SITE", "off")
    monkeypatch.setenv("RK_LLM", "off")
    monkeypatch.setenv("RK_CLOCK", "2026-09-21T10:00:00Z")
    monkeypatch.setenv("RK_MAX_MINUTES", "0")
    monkeypatch.setenv("RK_MAX_CYCLES", "0")
    from rk_harness import runner
    # time limit: 0 minutes elapsed >= limit? no — use a tiny limit and a cycle-free path: RK_MAX_CYCLES=0 with
    # RK_MAX_MINUTES=1 would run a full cycle first; instead assert the cycle limit path.
    monkeypatch.setenv("RK_MAX_CYCLES", "1")
    monkeypatch.setenv("RK_PHASE", "0")
    rc = runner.main([])
    assert rc == 0
    ev = (work / "events.jsonl").read_text(encoding="utf-8")
    assert "runner_started" in ev and "stopped_by_cycle_limit" in ev and ev.count('"cycle_done"') == 1
    # time limit with an already-elapsed budget: RK_MAX_MINUTES=1 but t_start is now; emulate by patching monotonic
    monkeypatch.setenv("RK_MAX_CYCLES", "0")
    monkeypatch.setenv("RK_MAX_MINUTES", "1")
    ticks = iter([0.0, 10_000.0, 20_000.0, 30_000.0])
    monkeypatch.setattr(runner.time, "monotonic", lambda: next(ticks))
    rc = runner.main([])
    assert rc == 0
    ev = (work / "events.jsonl").read_text(encoding="utf-8")
    assert "stopped_by_time_limit" in ev


def test_C13_enum_per_cycle_env(monkeypatch):
    from rk_harness import runner
    monkeypatch.delenv("RK_ENUM_PER_CYCLE", raising=False)
    assert runner._enum_per_cycle() == 500
    monkeypatch.setenv("RK_ENUM_PER_CYCLE", "7")
    assert runner._enum_per_cycle() == 7
    monkeypatch.setenv("RK_ENUM_PER_CYCLE", "junk")
    assert runner._enum_per_cycle() == 500


def test_C14_watch_renders_and_is_clean(tmp_path, monkeypatch):
    work = tmp_path / "work"
    work.mkdir()
    (work / "events.jsonl").write_text(
        '{"ts": "2026-09-21T10:00:00Z", "kind": "action", "action": "SEARCH_CELL", "payload": {"order": 2, "cell": [2, 0]}, "cycle_id": 1, "phase": 0}\n'
        '{"ts": "2026-09-21T10:00:01Z", "kind": "directive_fallback", "directive_id": "D-F00001", "target_order": 2, "stages": [2], "rationale": "fallback: emptiest cell", "source": "fallback"}\n'
        '{"ts": "2026-09-21T10:00:02Z", "kind": "codex_usage", "tokens": {"input_tokens": 10, "output_tokens": 2}, "used_percent": 3.5, "window_minutes": 10080, "resets_at": 1788671031, "plan_type": "plus"}\n'
        '{"ts": "2026-09-21T10:00:03Z", "kind": "cycle_done", "cycle_id": 1, "phase": 0, "improved": true, "stall_counter": 0, "accepted": 3, "rejected": 1, "spend_usd": 0.0, "cap_usd": 50.0}\n',
        encoding="utf-8")
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"run": {"auto_stop_minutes": 90}, "watcher": {"refresh_seconds": 5, "events_tail": 10}}), encoding="utf-8")
    monkeypatch.setenv("RK_WORK_DIR", str(work))
    monkeypatch.setenv("RK_CONFIG", str(cfg))
    from rk_harness import watch
    monkeypatch.setattr(watch, "docker_info", lambda name="rk": {"status": "running", "started": "2026-09-21T09:00:00Z",
                                                                 "image": "rk-harness:latest", "cpus": 4.0, "memory_gb": 6.0,
                                                                 "pids_limit": 512, "cpu_shares": 256, "env": {"RK_LLM": "codex"}})
    monkeypatch.setattr(watch, "watchdog_running", lambda: True)
    monkeypatch.setattr(watch, "last_push_time", lambda repo: "n/a")
    text = watch.render_once()
    for needle in ("rk run", "settings", "auto_stop_minutes", "what it is working on", "SEARCH_CELL", "fallback: emptiest cell",
                   "codex usage", "3.5%", "progress", "health", "results", "last 10 events"):
        assert needle in text, needle
    src = (HARNESS / "rk_harness" / "watch.py").read_text(encoding="utf-8").lower()
    assert "openai" not in src
    # read-only: nothing written into the work dir by rendering. HEARTBEAT is excluded
    # because T4's heartbeat test leaves a daemon thread running for the rest of the
    # pytest process, and it writes into whatever RK_WORK_DIR points at by then; that
    # made this assertion fail depending on where the 10 s timer landed, which is
    # nothing to do with what render_once() writes.
    assert sorted(p.name for p in work.iterdir() if p.name != "HEARTBEAT") == ["events.jsonl"]


def test_C15_project_falls_back_to_highest_solvable_order():
    from rk_harness import search
    from rk_harness.orderconditions import achieved_order_symbolic
    from rk_harness.tableau import classical, content_hash
    rk4 = classical()["rk4"]
    a_free = [float(rk4.A[i][j]) for i in range(4) for j in range(i)]
    t = search.project_or_lower(a_free, [float(b) for b in rk4.b], 4, 4, search.default_constraints())
    assert t is not None and content_hash(t) == content_hash(rk4)          # exact order 4 still wins when solvable
    # a dyadic A with no exact order-4 b: project() stays None (B46), project_or_lower falls back to order 3 (or 2)
    a_free = [0.25, 0.125, 0.375, 0.5, -0.25, 0.75]
    assert search.project(a_free, [0.25] * 4, 4, 4, search.default_constraints()) is None
    t = search.project_or_lower(a_free, [0.25] * 4, 4, 4, search.default_constraints())
    assert t is not None
    assert 2 <= achieved_order_symbolic(t, max_order=4) < 4


def test_C16_llm_throttle_and_usage_cap(tmp_path, monkeypatch):
    from rk_harness import runner
    from rk_harness.types import ArchiveState, RunState
    work = tmp_path / "work"
    monkeypatch.setenv("RK_WORK_DIR", str(work))
    monkeypatch.setenv("RK_LLM", "codex")
    monkeypatch.setenv("RK_LLM_EVERY_CYCLES", "3")
    monkeypatch.setenv("RK_CODEX_USAGE_CAP", "80")
    arch = ArchiveState(0, 0, {1: {}, 2: {}, 3: {}, 4: {}}, (), ())
    st = RunState(0, 2, "2026-09-21T10:00:00Z", "2026-09-21T10:00:00Z", 0.0, 0, None)
    calls = []
    good = json.dumps({"directive_id": "D-T1", "hypothesis_id": None, "target_order": 3, "stages": [4],
                       "constraints": {}, "islands": 1, "budget_minutes": 5, "rationale": "test"})

    def fake_call(system, user):
        calls.append(1)
        return good, 0.0
    monkeypatch.setattr(runner, "call_llm", fake_call)
    monkeypatch.setattr(runner, "_codex_rate_limits", lambda: {"used_percent": 10.0})
    assert runner.llm_due(3, "SEARCH_CELL", 3) and not runner.llm_due(4, "SEARCH_CELL", 3) and runner.llm_due(4, "HYPOTHESIZE", 3)
    d, _ = runner._llm_directive(st, arch, 2, 1, "SEARCH_CELL")      # cycle 1: not due, nothing to reuse -> fallback
    assert calls == [] and d["directive_id"].startswith("D-F")
    d, _ = runner._llm_directive(st, arch, 2, 3, "SEARCH_CELL")      # cycle 3: due -> call
    assert calls == [1] and d["directive_id"] == "D-T1"
    d, _ = runner._llm_directive(st, arch, 2, 4, "SEARCH_CELL")      # cycle 4: reuse the last directive
    assert calls == [1] and d["directive_id"] == "D-T1"
    assert "directive_reused" in (work / "events.jsonl").read_text(encoding="utf-8")
    d, _ = runner._llm_directive(st, arch, 2, 5, "WIDEN")            # escalation -> call again
    assert calls == [1, 1]
    monkeypatch.setattr(runner, "_codex_rate_limits", lambda: {"used_percent": 85.0})
    d, _ = runner._llm_directive(st, arch, 2, 6, "SEARCH_CELL")      # usage cap -> skipped, fallback
    assert calls == [1, 1] and d["directive_id"].startswith("D-F")
    assert "plan usage cap" in (work / "events.jsonl").read_text(encoding="utf-8")


def test_C17_hypothesize_action_appends_a_validated_hypothesis(tmp_path, monkeypatch):
    from rk_harness import ledger, runner
    from rk_harness.types import ArchiveState, RunState
    work = tmp_path / "work"
    monkeypatch.setenv("RK_WORK_DIR", str(work))
    monkeypatch.setenv("RK_LLM", "codex")
    arch = ArchiveState(0, 0, {1: {}, 2: {}, 3: {}, 4: {}}, (), ())
    st = RunState(9, 2, "2026-09-21T10:00:00Z", "2026-09-21T10:00:00Z", 0.0, 21, None)
    good = json.dumps({"statement": "slow p3s4 beats p4s4", "mechanism": "csd weight",
                       "control": "reverses under fast", "predicate": "slow.p3s4.heldout < slow.p4s4.heldout",
                       "min_samples": 200})
    monkeypatch.setattr(runner, "call_llm", lambda s, u: (good, 0.0))
    monkeypatch.setattr(runner, "_codex_rate_limits", lambda: {"used_percent": 10.0})
    assert runner._maybe_propose_hypothesis(st, arch, "SEARCH_CELL", 10) == 0.0      # only on HYPOTHESIZE
    assert ledger.load_hypotheses() == []
    runner._maybe_propose_hypothesis(st, arch, "HYPOTHESIZE", 10)
    hyps = ledger.load_hypotheses()
    assert len(hyps) == 1 and hyps[0]["id"] == "H-001" and hyps[0]["cycle_proposed"] == 10
    assert hyps[0]["verdict"] is None and hyps[0]["min_samples"] == 200
    # ids increment (a second, different predicate: the same one again is dropped, see C51)
    other = json.dumps({**json.loads(good), "predicate": "slow.p3s5.heldout < slow.p4s4.heldout"})
    monkeypatch.setattr(runner, "call_llm", lambda s, u: (other, 0.0))
    runner._maybe_propose_hypothesis(st, arch, "HYPOTHESIZE", 11)
    assert [h["id"] for h in ledger.load_hypotheses()] == ["H-001", "H-002"]
    # malformed predicate: rejected, nothing appended, cycle unaffected
    bad = json.dumps({"statement": "x", "mechanism": "y", "control": "z",
                      "predicate": "__import__('os')", "min_samples": 50})
    monkeypatch.setattr(runner, "call_llm", lambda s, u: (bad, 0.0))
    runner._maybe_propose_hypothesis(st, arch, "HYPOTHESIZE", 12)
    assert len(ledger.load_hypotheses()) == 2
    ev = (work / "events.jsonl").read_text(encoding="utf-8")
    assert "hypothesis_proposed" in ev and "hypothesis_rejected" in ev
    # K8/I5: the hypothesis prompt carries no tier strings and never asks for a verdict
    from rk_harness import prompts
    text = prompts.HYPOTHESIS_SYSTEM_PROMPT + prompts.build_hypothesis_prompt(arch, st, [], [])
    for banned in ("heldout_verified", "search_only", "no_incumbent", "no_improvement",
                   "unreplicated"):
        assert banned not in text
    assert "verdicts are assigned" in prompts.HYPOTHESIS_SYSTEM_PROMPT


def test_C18_literature_store_soften_and_prompt_wiring(tmp_path, monkeypatch):
    monkeypatch.setenv("RK_WORK_DIR", str(tmp_path / "work"))
    from rk_harness import literature, prompts
    from rk_harness.types import ArchiveState, RunState
    softened = literature.soften("a novel first method that beats X, proves Y, a breakthrough")
    for banned in ("novel", "first", "beats", "proves", "breakthrough"):
        assert banned not in softened.lower()
    literature.append_digest({"ts": "2026-09-21T10:00:00Z", "cycle": 5, "topic": "novel Q15 RK",
                              "summary": "Stochastic rounding beats floor rounding in drift.\n\nSecond para.",
                              "key_points": ["floor bias is systematic"],
                              "sources": [{"title": "first paper", "url": "https://arxiv.org/abs/1911.00318"}]})
    d = literature.load_digests()[0]
    assert "novel" not in d["topic"] and "beats" not in d["summary"]
    text = literature.digest_for_prompt()
    assert "floor bias is systematic" in text
    assert literature.next_topic(0) != literature.next_topic(1)
    arch = ArchiveState(0, 0, {1: {}, 2: {}, 3: {}, 4: {}}, (), ())
    st = RunState(1, 2, "", "", 0.0, 0, None)
    assert "floor bias is systematic" in prompts.build_user_prompt(arch, st, [], [], literature=text)
    assert "floor bias is systematic" in prompts.build_hypothesis_prompt(arch, st, [], [], literature=text)
    for banned in ("heldout_verified", "search_only", "no_incumbent", "no_improvement",
                   "unreplicated"):
        assert banned not in prompts.LITERATURE_SYSTEM_PROMPT + prompts.INTERPRET_SYSTEM_PROMPT


def test_C19_runner_literature_and_interpretation_gating(tmp_path, monkeypatch):
    from rk_harness import ledger, literature, runner
    from rk_harness.types import ArchiveState, RunState
    work = tmp_path / "work"
    monkeypatch.setenv("RK_WORK_DIR", str(work))
    monkeypatch.setenv("RK_LLM", "codex")
    monkeypatch.setenv("RK_LIT_EVERY", "2")
    monkeypatch.setenv("RK_INTERPRET_EVERY", "3")
    arch = ArchiveState(0, 0, {1: {}, 2: {}, 3: {}, 4: {}}, (), ())
    st = RunState(1, 2, "2026-09-21T10:00:00Z", "2026-09-21T10:00:00Z", 0.0, 0, None)
    dig = json.dumps({"topic": "csd multipliers", "summary": "CSD halves the shift count on slow multipliers.",
                      "key_points": ["naf is minimal"], "sources": [{"title": "t", "url": "https://x"}]})
    seen = []

    def fake_codex(system, user, extra_args=None, timeout=600, effort=""):
        seen.append(list(extra_args or []))
        return (dig if extra_args else "Para one interpreting the grids at length, easily long enough to pass the two-hundred-character floor for a published interpretation entry, with mechanism talk.\n\nPara two about the novel first results."), 0.0
    monkeypatch.setattr(runner, "_call_codex", fake_codex)
    monkeypatch.setattr(runner, "_codex_rate_limits", lambda: {"used_percent": 10.0})
    assert runner._maybe_literature_review(st, arch, 3) == 0.0        # not due
    assert literature.load_digests() == []
    runner._maybe_literature_review(st, arch, 4)                      # due -> digest written via web search args
    assert ["-c", 'web_search="live"'] in seen
    assert literature.load_digests()[0]["topic"] == "csd multipliers"
    assert runner._maybe_interpret(st, arch, 4) == 0.0                # not due
    runner._maybe_interpret(st, arch, 6)                              # due -> interpretation written, softened
    entries = literature.load_interpretations()
    assert len(entries) == 1 and "novel" not in entries[0]["text"]
    ev = (work / "events.jsonl").read_text(encoding="utf-8")
    assert "literature_digest" in ev and "interpretation_published" in ev
    monkeypatch.setattr(runner, "_codex_rate_limits", lambda: {"used_percent": 95.0})
    assert runner._maybe_literature_review(st, arch, 6) == 0.0        # capped


def test_C20_sitegen_publishes_literature_and_interpretation(tmp_path, monkeypatch):
    """Both logs are sections of the research log (hypotheses.html) since D41."""
    work = tmp_path / "work"
    monkeypatch.setenv("RK_WORK_DIR", str(work))
    from rk_harness import archive, literature, sitegen
    literature.append_digest({"ts": "2026-09-21T10:00:00Z", "cycle": 5, "topic": "novel Q15 RK",
                              "summary": "Floor rounding drift beats naive expectations.",
                              "key_points": ["k1"], "sources": [{"title": "first paper", "url": "https://arxiv.org/abs/1911.00318"}]})
    literature.append_interpretation({"ts": "2026-09-21T10:01:00Z", "cycle": 6,
                                      "text": "The archive proves a novel pattern.\n\nSecond paragraph."})
    out = tmp_path / "docs"
    sitegen.build(archive.replay(), out)                              # would raise on any banned word
    assert not (out / "literature.html").exists() and not (out / "interpretation.html").exists()
    page = (out / "hypotheses.html").read_text(encoding="utf-8")
    interp = page.split('<h2 id="interpretation">', 1)[1].split('<h2 id="literature">', 1)[0]
    lit = page.split('<h2 id="literature">', 1)[1]
    assert sitegen.BANNER in page
    assert "arxiv.org" in lit and "Model-written" in page
    assert "Second paragraph." in interp
    sitegen.check_banned(page)


def test_C21_a_snapshot_whose_window_has_reset_does_not_cap(tmp_path, monkeypatch):
    """Only a codex call writes a rate-limit snapshot, so a reading that closes the gate is
    the last reading that will ever be taken. Without an expiry the gate latches shut: that
    is what kept the run on fallback directives for over a thousand cycles."""
    import time as _time
    from rk_harness import runner
    from rk_harness.types import ArchiveState, RunState
    work = tmp_path / "work"
    monkeypatch.setenv("RK_WORK_DIR", str(work))
    monkeypatch.setenv("RK_LLM", "codex")
    monkeypatch.setenv("RK_LLM_EVERY_CYCLES", "1")
    monkeypatch.setenv("RK_CODEX_USAGE_CAP", "80")
    arch = ArchiveState(0, 0, {1: {}, 2: {}, 3: {}, 4: {}}, (), ())
    st = RunState(0, 2, "2026-09-21T10:00:00Z", "2026-09-21T10:00:00Z", 0.0, 0, None)
    good = json.dumps({"directive_id": "D-T9", "hypothesis_id": None, "target_order": 3,
                       "stages": [4], "constraints": {}, "islands": 1, "budget_minutes": 5,
                       "rationale": "test"})
    calls = []

    def fake_call(system, user):
        calls.append(1)
        return good, 0.0
    monkeypatch.setattr(runner, "call_llm", fake_call)

    now = _time.time()
    # over cap, window still open: the cap binds, which is the behaviour worth keeping
    monkeypatch.setattr(runner, "_codex_rate_limits", lambda: {
        "used_percent": 80.0, "window_minutes": 10080, "resets_at": now + 3600})
    d, _ = runner._llm_directive(st, arch, 2, 1, "SEARCH_CELL")
    assert calls == [] and d["directive_id"].startswith("D-F")
    assert runner._codex_cap_state()[:2] == (True, "plan usage cap")

    # same reading, window already reset: it describes a window that no longer exists
    monkeypatch.setattr(runner, "_codex_rate_limits", lambda: {
        "used_percent": 80.0, "window_minutes": 10080, "resets_at": now - 1})
    assert runner._codex_cap_state()[:2] == (False, "window reset passed")
    d, _ = runner._llm_directive(st, arch, 2, 2, "SEARCH_CELL")
    assert calls == [1] and d["directive_id"] == "D-T9"

    # no resets_at, but the reading is older than its own window: same conclusion
    monkeypatch.setattr(runner, "_codex_rate_limits", lambda: {
        "used_percent": 80.0, "window_minutes": 60, "snapshot_age_s": 7200.0})
    assert runner._codex_cap_state()[:2] == (False, "snapshot older than its window")

    # no snapshot at all is not a cap hit either
    monkeypatch.setattr(runner, "_codex_rate_limits", dict)
    assert runner._codex_cap_state()[:2] == (False, "no snapshot")


def test_C22_every_codex_gate_names_itself_when_it_suppresses(tmp_path, monkeypatch):
    """Three of the four gates used to suppress silently, which is why a thousand-cycle
    outage left almost no trace in events.jsonl."""
    import time as _time
    from rk_harness import runner
    from rk_harness.types import ArchiveState, RunState
    work = tmp_path / "work"
    monkeypatch.setenv("RK_WORK_DIR", str(work))
    monkeypatch.setenv("RK_LLM", "codex")
    monkeypatch.setenv("RK_LLM_EVERY_CYCLES", "1")
    monkeypatch.setenv("RK_LIT_EVERY", "1")
    monkeypatch.setenv("RK_INTERPRET_EVERY", "1")
    monkeypatch.setenv("RK_CODEX_USAGE_CAP", "80")
    arch = ArchiveState(0, 0, {1: {}, 2: {}, 3: {}, 4: {}}, (), ())
    st = RunState(0, 2, "2026-09-21T10:00:00Z", "2026-09-21T10:00:00Z", 0.0, 0, None)
    monkeypatch.setattr(runner, "_codex_rate_limits", lambda: {
        "used_percent": 95.0, "window_minutes": 10080, "resets_at": _time.time() + 3600})
    monkeypatch.setattr(runner, "call_llm", lambda s, u: (_ for _ in ()).throw(
        AssertionError("a capped gate must not call out")))
    monkeypatch.setattr(runner, "_call_codex", lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("a capped gate must not call out")))

    runner._llm_directive(st, arch, 2, 1, "SEARCH_CELL")
    assert runner._maybe_propose_hypothesis(st, arch, "HYPOTHESIZE", 1) == 0.0
    assert runner._maybe_literature_review(st, arch, 1) == 0.0
    assert runner._maybe_interpret(st, arch, 1) == 0.0

    lines = [json.loads(x) for x in
             (work / "events.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    gates = {e.get("gate") for e in lines if e.get("kind") == "llm_skipped"}
    assert gates == {"directive", "hypothesis", "literature", "interpret"}, gates
    for e in lines:
        if e.get("kind") == "llm_skipped":
            assert e["reason"] == "plan usage cap"
            assert e["used_percent"] == 95.0 and e["cap_percent"] == 80.0


def _watch_events_file(work: Path) -> None:
    """One of each kind the scoped rows count: a cycle, an accepted, a rejected, an LLM
    call and an abandoned cycle."""
    lines = [
        {"ts": "2026-09-21T10:00:00Z", "kind": "cycle_done", "cycle_id": 1, "phase": 2,
         "improved": False, "stall_counter": 1, "accepted": 1, "rejected": 1,
         "spend_usd": 0.0, "cap_usd": 50.0},
        {"ts": "2026-09-21T10:00:01Z", "kind": "accepted", "tableau_hash": "a" * 8, "cycle_id": 1},
        {"ts": "2026-09-21T10:00:02Z", "kind": "rejected", "code": "ORDER_NOT_MET", "tableau_hash": "b" * 8},
        {"ts": "2026-09-21T10:00:03Z", "kind": "llm_call", "cycle_id": 1, "cost_usd": 0.0},
        {"ts": "2026-09-21T10:00:04Z", "kind": "cycle_abandoned", "cycle_id": 1, "error": "boom"},
    ]
    (work / "events.jsonl").write_text(
        "".join(json.dumps(d) + chr(10) for d in lines), encoding="utf-8")


def _watch_module(tmp_path, monkeypatch, work: Path):
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"watcher": {"refresh_seconds": 5, "events_tail": 10}}), encoding="utf-8")
    monkeypatch.setenv("RK_WORK_DIR", str(work))
    monkeypatch.setenv("RK_CONFIG", str(cfg))
    from rk_harness import watch
    monkeypatch.setattr(watch, "docker_info", lambda name="rk": {"status": "absent"})
    monkeypatch.setattr(watch, "watchdog_running", lambda: None)
    monkeypatch.setattr(watch, "last_push_time", lambda repo: "n/a")
    return watch


def _line_with(text: str, needle: str) -> str:
    for line in text.splitlines():
        if needle in line:
            return line
    raise AssertionError(f"no line containing {needle!r}")


def test_C23_tail_derived_counts_name_their_window(tmp_path, monkeypatch):
    """events.jsonl has no rotation and the view reads its tail, so a count taken from it
    is a run total only when the tail is the whole file. Every such row says which."""
    work = tmp_path / "work"
    work.mkdir()
    _watch_events_file(work)
    watch = _watch_module(tmp_path, monkeypatch, work)

    events, truncated = watch.load_events()
    assert len(events) == 5 and truncated is False
    assert watch._scope(truncated, events) == "this run"

    text = watch.render_once(width=200)
    assert "(this archive)" not in text
    assert "this run" in _line_with(text, "cycles done")
    assert "total" not in _line_with(text, "directive calls")
    assert "this run" in _line_with(text, "directive calls")
    assert "this run" in _line_with(text, "abandoned cycles")

    # a tail smaller than the file: every one of those counts now names its window
    monkeypatch.setattr(watch, "EVENTS_TAIL_BYTES", 200)
    events, truncated = watch.load_events()
    assert truncated is True and len(events) < 5
    text = watch.render_once(width=200)
    assert "this run" not in text
    assert "since " in _line_with(text, "cycles done")


def test_C24_progress_panel_shows_the_heldout_gap_and_surrogate_state(tmp_path, monkeypatch):
    """The two rows that dashboard.py was the only live display of. DESIGN calls the
    held-out gap a first-class metric, so it belongs on the view that actually runs."""
    work = tmp_path / "work"
    work.mkdir()
    _watch_events_file(work)
    watch = _watch_module(tmp_path, monkeypatch, work)
    text = watch.render_once(width=200)
    assert "heldout gap" in text
    assert "mean heldout - search over elites" in text
    assert "need 5000, have 0" in _line_with(text, "surrogate")


# ---------------------------------------------------------------- the host scripts themselves
#
# This tier already reads workspace files, so these live here rather than in a new test file
# (a new tests/test_tN_*.py would fail the overview build until _SUITE_DESC describes it).

START_PS1 = WORKSPACE / "start.ps1"
WATCHDOG_PS1 = HARNESS / "scripts" / "watchdog.ps1"


def _schema() -> dict:
    """The workspace configure.py SCHEMA, loaded by path. Importing it has no side effects:
    everything below the dict is a function, and main() is behind __main__."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("_rk_configure", CONFIGURE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.SCHEMA


def _watchdog_function(name: str) -> str:
    """One PowerShell function body: from its 'function <name>' line to the next line that is
    a closing brace in the first column."""
    text = WATCHDOG_PS1.read_text(encoding="ascii")
    lines = text.splitlines()
    start = next(i for i, ln in enumerate(lines) if ln.startswith("function " + name))
    end = next(i for i in range(start + 1, len(lines)) if lines[i] == "}")
    return "\n".join(lines[start:end + 1])


@pytest.mark.skipif(not (CONFIGURE.exists() and START_PS1.exists()),
                    reason="workspace configure.py / start.ps1 not present")
def test_C25_start_ps1_passes_every_watchdog_config_key():
    """A key added to configure.py that start.ps1 never passes is a setting that appears in
    `configure.py show`, accepts a value, writes it to config.json, and changes nothing."""
    import re
    text = START_PS1.read_text(encoding="ascii")
    # keys the watchdog deliberately does not take from config.json; each needs a reason
    allowed_missing: dict[str, str] = {}
    missing = []
    for key in _schema():
        sec, name = key.split(".", 1)
        if sec != "watchdog" or name in allowed_missing:
            continue
        if not re.search(r"""Cfg\s+['"]watchdog['"]\s+['"]{}['"]""".format(re.escape(name)), text):
            missing.append(key)
    assert not missing, "configured but never passed to the watchdog: {}".format(missing)


def test_C26_every_powershell_script_is_pure_ascii():
    """PowerShell 5.1 will not parse a smart quote or an em dash, and the parse error it
    gives points somewhere unhelpful. A parse error in watchdog.ps1 is a disabled kill
    switch, so this is checked on every script rather than on that one."""
    scripts = sorted((HARNESS / "scripts").glob("*.ps1"))
    if WORKSPACE.exists():
        scripts += sorted(WORKSPACE.glob("*.ps1"))
    assert scripts, "no PowerShell scripts found to check"
    for p in scripts:
        try:
            p.read_bytes().decode("ascii")
        except UnicodeDecodeError as exc:
            raise AssertionError("{} is not ASCII at byte {}".format(p, exc.start))


def test_C27_docker_stats_is_only_called_through_the_bounded_helper():
    """docker stats has no timeout of its own and samples every container on the daemon, and
    this call sits on the path that decides whether the run is paused. Exactly one place may
    make it, and that place must be able to give up."""
    text = WATCHDOG_PS1.read_text(encoding="ascii")
    block = _watchdog_function("Get-DockerCpuRows")
    assert text.count("--no-stream") == 1
    assert "--no-stream" in block
    assert "WaitForExit(" in block
    assert "Kill()" in block
    # the old unbounded form, and any other direct invocation, is gone
    assert "= docker stats" not in text
    # everywhere else the phrase may only appear in a comment or in a line the script prints
    inside = set(block.splitlines())
    for ln in text.splitlines():
        if ln in inside:
            continue
        code = ln.split("#", 1)[0]
        if "docker stats" not in code:
            continue
        assert "Say " in code, ln


def test_C42_every_watchdog_stop_is_recorded_and_only_a_recorded_stop_is_resumed():
    """The watchdog starts the container again only after a stop it made itself, and it
    knows which stops those were from the record Stop-Run writes. A docker stop or kill
    written anywhere else would be a stop with no record, so the run would stay down after
    it exactly as it did for five days after 2026-09-17. And a docker start anywhere but
    Resume-Run would be a restart that no limit counts."""
    import re
    text = WATCHDOG_PS1.read_text(encoding="ascii")
    stop_run = _watchdog_function("Stop-Run")
    resume_run = _watchdog_function("Resume-Run")
    blocker = _watchdog_function("Resume-Blocker")
    for ln in text.splitlines():
        code = ln.split("#", 1)[0]
        if re.search(r"\bdocker\s+(stop|kill)\b", code):
            assert "Say " in code, "a docker stop or kill outside Stop-Run: " + ln.strip()
        if re.search(r"\bdocker\s+start\b", code) and ln not in resume_run.splitlines():
            assert "Say " in code, "a docker start outside Resume-Run: " + ln.strip()
    assert "docker $verb $Container" in stop_run and "Write-WatchdogState" in stop_run
    assert "docker start $Container" in resume_run and "Recent-Resumes" in resume_run
    # the four stop sites, each under its own reason
    for reason in ("heartbeat", "spend", "disk", "system"):
        assert re.search(r'Stop-Run\s+"{}"'.format(reason), text), reason
        assert '"{}"'.format(reason) in blocker, reason
    # what keeps a stop down, whatever its reason
    for guard in ("$NoAutoResume", '"STOP"', "$freezePending", "$ResumeMax", "$ResumeCooldownSeconds"):
        assert guard in blocker, guard


@pytest.mark.skipif(not CONFIGURE.exists(), reason="workspace configure.py not present")
def test_C43_the_resume_defaults_match_the_config_defaults():
    """Same reason as C28: the watchdog is started by hand as often as by start.ps1, and a
    restart limit that differs with who launched it is not a limit anyone can state."""
    import re
    schema = _schema()
    text = WATCHDOG_PS1.read_text(encoding="ascii")
    for key, param in (("watchdog.resume_max", "ResumeMax"),
                       ("watchdog.resume_window_hours", "ResumeWindowHours"),
                       ("watchdog.resume_margin_gb", "ResumeMarginGB")):
        m = re.search(r"\[(?:int|double)\]\$" + param + r"\s*=\s*([0-9.]+)", text)
        assert m, param
        assert float(m.group(1)) == float(schema[key][0]), key
    assert schema["watchdog.auto_resume"][0] is True
    assert "[switch]$NoAutoResume" in text


@pytest.mark.skipif(not (WORKSPACE / "autostart.ps1").exists(),
                    reason="workspace autostart.ps1 not present")
def test_C44_a_reboot_starts_the_run_but_never_undoes_a_stop():
    """autostart.ps1 runs start.ps1 at sign-in (D47), because otherwise a reboot left the run
    with no watchdog until someone noticed. A stop made on purpose has to outlast that:
    stop.ps1 leaves run-stopped.txt, start.ps1 is the only thing that removes it, and the
    logon script checks it, and rk-work/STOP, before it starts anything."""
    auto = (WORKSPACE / "autostart.ps1").read_text(encoding="ascii")
    stop = (WORKSPACE / "stop.ps1").read_text(encoding="ascii")
    start = START_PS1.read_text(encoding="ascii")
    first_start = auto.index('"start.ps1")')
    for guard in ('"run-stopped.txt"', '"rk-work\\STOP"'):
        assert guard in auto, guard
        assert auto.index(guard) < first_start, guard + " is checked after start.ps1 runs"
    assert 'Set-Content -Path (Join-Path $root "run-stopped.txt")' in stop
    assert 'Remove-Item (Join-Path $root "run-stopped.txt")' in start
    assert 'Remove-Item (Join-Path $root "run-stopped.txt")' not in stop
    # task defaults would refuse to start on battery; the watchdog owns that rule
    assert "-AllowStartIfOnBatteries" in auto and "-DontStopIfGoingOnBatteries" in auto


@pytest.mark.skipif(not CONFIGURE.exists(), reason="workspace configure.py not present")
def test_C28_the_peer_default_matches_the_config_default():
    """The script's own default and the configured one cannot drift: the watchdog is started
    by hand as often as by start.ps1, and a different default in each place is a guard that
    behaves differently depending on who launched it."""
    import re
    schema = _schema()
    key = "watchdog.peer_containers"
    if key not in schema:
        pytest.skip("watchdog.peer_containers is not in SCHEMA yet")
    text = WATCHDOG_PS1.read_text(encoding="ascii")
    m = re.search(r"""\[string\]\$PeerContainers\s*=\s*["']([^"']*)["']""", text)
    assert m, "watchdog.ps1 has no $PeerContainers parameter"
    assert m.group(1) == schema[key][0]


# ---------------------------------------------------------------- the lane panel
#
# The watcher's side-track row was written when a cycle could only be an explicit search and
# the two other classes shared one optional slot. Under a lane rotation a cycle can be any of
# the three, and a panel that cannot say which reports a stall for a cycle that did exactly
# what it was told. These pin the panel before the rotation is armed.

def _health_text(watch, work, dk, width=100) -> str:
    """The health panel alone, rendered wide enough that nothing wraps mid-sentence."""
    from rich.console import Console
    events, _ = watch.load_events()
    console = Console(width=width, record=True, force_terminal=False)
    console.print(watch.health_panel(events, watch._now(), "this run", dk, 7))
    return " ".join(console.export_text().replace("|", " ").split())


def test_C29_the_health_panel_reads_a_cycle_as_a_lane_not_as_a_search(tmp_path, monkeypatch):
    work = tmp_path / "work"
    work.mkdir()
    _watch_events_file(work)
    watch = _watch_module(tmp_path, monkeypatch, work)

    # Docker answered and the container sets no lane schedule: the run as it stands. The
    # panel must say so plainly, and must not suggest a rotation is under way.
    today = _health_text(watch, work, {"status": "running", "env": {"RK_LLM": "codex"}})
    assert "every cycle explicit (schedule 'E'; container sets none)" in today
    assert "unknown; no rotation is scheduled, so none is recorded" in today
    assert "33%" not in today

    # Docker silent: nothing is claimed about the container, here as in stats.txt.
    silent = _health_text(watch, work, {"status": "unknown"})
    assert "unknown; no shares.json names one and Docker did not say" in silent

    # Armed, with a document that records what actually happened.
    from rk_harness import lanes
    rows = [lanes.cycle_row(100 + i, lanes.lane_for(100 + i, "EAI"),
                            "2026-09-09T06:{:02d}:00Z".format(i), 176.0, 100.0,
                            schedule="EAI")
            for i in range(30)]
    doc = lanes.build_shares(rows, schedule="EAI", window_cycles=200)
    lanes.validate_shares(doc)
    lanes.write_shares(doc, work / "schedule" / "shares.json")
    armed = _health_text(watch, work, {"status": "running",
                                       "env": {"RK_LANE_SCHEDULE": "EAI"}})
    assert "schedule 'EAI', named in shares.json" in armed
    assert "asks for explicit 33%, adaptive 33%, implicit 33%" in armed
    assert "explicit 33%, adaptive 33%, implicit 33% over 30 cycles" in armed


def test_C30_the_watcher_and_stats_txt_render_the_same_lane_lines(tmp_path, monkeypatch):
    """stats.txt exists because a file the container writes cannot report that the container
    is dead, and the machine panel already shares its probes so the two cannot disagree. The
    lane lines are the same arrangement: one reader, two displays."""
    work = tmp_path / "work"
    work.mkdir()
    _watch_events_file(work)
    watch = _watch_module(tmp_path, monkeypatch, work)
    from rk_harness import status

    for env in (None, {}, {"RK_LANE_SCHEDULE": "EAI"}):
        dk = {"status": "running", "env": env} if env is not None else {"status": "unknown"}
        want = status.lane_rows(status.read_lanes(work, docker_env=env, current_cycle=7))
        assert watch.lane_panel_rows(dk, 7) == want, env


def test_C31_the_side_track_plan_is_reported_per_lane(tmp_path, monkeypatch):
    """The two side tracks share one slot, one budget and, until now, one number. '103 of 103'
    cannot say which lane the catalogue was for, which is the arrangement the rotation
    replaces, so the row is broken out before the rotation arrives."""
    work = tmp_path / "work"
    work.mkdir()
    _watch_events_file(work)
    watch = _watch_module(tmp_path, monkeypatch, work)
    from rk_harness import sidetrack
    monkeypatch.setattr(sidetrack, "status", lambda *a, **k: {
        "code_hash": "305c692a1b5c085a", "ledger_lines": 143, "planned_total": 103,
        "done_total": 103, "set_aside_total": 0, "remaining_total": 0,
        "estimated_seconds_remaining": None,
        "jobs": [{"job": "sweep", "track": "adaptive", "planned": 61, "done": 61, "set_aside": 0},
                 {"job": "gain", "track": "implicit", "planned": 42, "done": 42, "set_aside": 0}]})
    text = _health_text(watch, work, {"status": "running", "env": {}}, width=140)
    assert "adaptive 61/61, implicit 42/42 points measured" in text
    assert "plan exhausted" in text


def test_C32_a_lane_archive_that_does_not_exist_yet_shows_nothing(tmp_path, monkeypatch):
    """The two parallel lane archives arrive with the rotation. Until then the panel must be
    silent about them rather than printing an empty one, and must never fail on the read."""
    work = tmp_path / "work"
    work.mkdir()
    _watch_events_file(work)
    watch = _watch_module(tmp_path, monkeypatch, work)
    assert watch._lanesearch_rows() == []

    from rk_harness import lanesearch
    (work / "adaptive_archive").mkdir(parents=True, exist_ok=True)
    watch._cache.pop(("lanesearch", "adaptive"), None)
    watch._cache.pop(("lanesearch", "implicit"), None)
    rows = watch._lanesearch_rows()
    if lanesearch.lane_dir("adaptive").exists():
        assert rows and rows[0][0] == "adaptive archive"
        assert "candidates measured under code" in rows[0][1]
    watch._cache.pop(("lanesearch", "adaptive"), None)
    watch._cache.pop(("lanesearch", "implicit"), None)


# ---------------------------------------------------------------- 2026-09-24: watcher and effort

def test_C45_the_header_says_whether_a_stopped_run_was_stopped_on_purpose(tmp_path, monkeypatch):
    """docker reports the same "exited" whether stop.ps1 stopped the run or it died, so the
    header reads the stop records to tell the two apart, and flags a stale heartbeat."""
    import datetime
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.setenv("RK_WORK_DIR", str(work))
    from rk_harness import watch
    now = datetime.datetime(2026, 9, 25, 3, 0, tzinfo=datetime.timezone.utc)
    fresh, old = now - datetime.timedelta(seconds=20), now - datetime.timedelta(minutes=10)
    assert "RUNNING" in watch.run_verdict({"status": "running"}, fresh, now, 120)
    assert "STALLED" in watch.run_verdict({"status": "running"}, old, now, 120)
    assert "STARTING" in watch.run_verdict({"status": "running"}, None, now, 120)
    assert "PAUSED" in watch.run_verdict({"status": "paused"}, fresh, now, 120)
    assert "UNKNOWN" in watch.run_verdict({}, None, now, 120)
    assert "DOWN" in watch.run_verdict({"status": "exited"}, old, now, 120)
    (tmp_path / "run-stopped.txt").write_text(
        "stop.ps1 stopped the run at 2026-09-25T02:57:55Z. start.ps1 deletes this file; "
        "autostart.ps1 will not start the run while it exists.", encoding="ascii")
    v = watch.run_verdict({"status": "exited"}, old, now, 120)
    assert "STOPPED ON PURPOSE" in v and "2026-09-24 21:57" in v
    (work / "STOP").write_text("stop", encoding="ascii")
    assert "STOPPING" in watch.run_verdict({"status": "exited"}, old, now, 120)


def test_C46_one_failing_panel_costs_only_that_panel(tmp_path, monkeypatch):
    """A panel that raises used to replace the whole live view with one "refresh failed" box
    and to crash --once; now it renders its own error and every other panel still shows."""
    work = tmp_path / "work"
    work.mkdir()
    _watch_events_file(work)
    watch = _watch_module(tmp_path, monkeypatch, work)

    def boom(*a, **k):
        raise RuntimeError("half-written state file")
    monkeypatch.setattr(watch, "llm_panel", boom)
    text = watch.render_once(width=200)
    assert "could not build this panel" in text and "half-written state file" in text
    for needle in ("rk run", "progress", "health", "results", "what it is working on"):
        assert needle in text, needle
    # and a failure outside any panel still renders, as one panel, rather than raising
    monkeypatch.setattr(watch, "load_events", boom)
    assert "refresh failed" in watch.render_once(width=200)


def test_C47_a_config_file_with_a_bad_section_does_not_break_the_view(tmp_path, monkeypatch):
    work = tmp_path / "work"
    work.mkdir()
    _watch_events_file(work)
    watch = _watch_module(tmp_path, monkeypatch, work)
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"watcher": "oops", "run": {"llm": "codex"}}), encoding="utf-8")
    assert watch.load_config() == {"run": {"llm": "codex"}}
    cfg.write_text("[1, 2]", encoding="utf-8")
    assert watch.load_config() == {}
    assert "rk run" in watch.render_once(width=200)


def test_C48_under_wsl_the_watchdog_is_found_through_windows_powershell(monkeypatch):
    """watch-integration-harness runs this view under WSL's Python, where the watchdog (a
    Windows process) used to read "n/a". Interop reaches powershell.exe by full path only."""
    from rk_harness import watch
    seen = {}

    class P:
        returncode, stdout, stderr = 0, "1\r\n", ""

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        return P()
    monkeypatch.setattr(watch.platform, "system", lambda: "Linux")
    monkeypatch.setattr(watch.platform, "release", lambda: "6.18.33.1-microsoft-standard-WSL2")
    monkeypatch.setattr(watch.Path, "exists", lambda self: str(self) == watch._WSL_POWERSHELL or False)
    monkeypatch.setattr(watch.subprocess, "run", fake_run)
    watch._cache.pop("watchdog", None)
    assert watch.watchdog_running() is True
    assert seen["cmd"][0] == watch._WSL_POWERSHELL
    watch._cache.pop("watchdog", None)
    monkeypatch.setattr(watch.platform, "release", lambda: "6.8.0-generic")
    assert watch.watchdog_running() is None
    watch._cache.pop("watchdog", None)


@pytest.mark.skipif(not CONFIGURE.exists(), reason="workspace configure.py not present")
def test_C49_reasoning_effort_reaches_codex_only_where_it_should(tmp_path, monkeypatch):
    """run.llm_reasoning_effort flows config -> start.ps1 -> run.ps1 -> RK_LLM_EFFORT ->
    `codex exec -c model_reasoning_effort=...`. An unknown value is dropped, not passed on,
    and each usage event records the model and effort it ran at."""
    import re
    from rk_harness import runner
    monkeypatch.setenv("RK_WORK_DIR", str(tmp_path / "work"))
    calls = []

    class P:
        returncode, stderr = 0, ""
        stdout = '{"type": "turn.completed", "usage": {"input_tokens": 5, "output_tokens": 1}}\n'

    def fake_run(cmd, **kw):
        calls.append(cmd)
        out = cmd[cmd.index("--output-last-message") + 1]
        Path(out).write_text("{}", encoding="utf-8")
        return P()
    monkeypatch.setattr(runner.subprocess, "run", fake_run)
    monkeypatch.setattr(runner, "_codex_rate_limits", lambda: {})
    monkeypatch.setenv("RK_LLM", "codex")
    monkeypatch.setenv("RK_LLM_MODEL", "gpt-6-sol")
    monkeypatch.setenv("RK_LLM_EFFORT", "HIGH")
    assert runner._llm_effort() == "high"
    runner.call_llm("sys", "user")
    assert calls[-1][calls[-1].index("-m") + 1] == "gpt-6-sol"
    assert 'model_reasoning_effort="high"' in calls[-1]
    assert 'web_search="disabled"' in calls[-1]          # codex 0.156 searches unless told not to
    runner._call_codex("sys", "user", extra_args=["-c", 'web_search="live"'])   # the literature call
    assert not any("model_reasoning_effort" in a for a in calls[-1])
    assert 'web_search="live"' in calls[-1] and 'web_search="disabled"' not in calls[-1]
    monkeypatch.setenv("RK_LLM_EFFORT", "banana")
    assert runner._llm_effort() == ""
    runner.call_llm("sys", "user")
    assert not any("model_reasoning_effort" in a for a in calls[-1])
    ev = [json.loads(x) for x in (tmp_path / "work" / "events.jsonl").read_text(encoding="utf-8").splitlines()]
    usage = [e for e in ev if e["kind"] == "codex_usage"]
    assert usage[0]["model"] == "gpt-6-sol" and usage[0]["effort"] == "high"
    assert usage[1]["effort"] == "default"
    # the plumbing between the config and the container
    schema = _schema()
    assert schema["run.llm_reasoning_effort"][0] == ""
    assert set(schema["run.llm_reasoning_effort"][2]) == {"", *runner._LLM_EFFORTS}
    start = START_PS1.read_text(encoding="ascii")
    assert re.search(r'LlmEffort\s*=\s*\[string\]\(Cfg "run" "llm_reasoning_effort" ""\)', start)
    run_ps1 = (HARNESS / "scripts" / "run.ps1").read_text(encoding="ascii")
    assert "[string]$LlmEffort" in run_ps1 and '"RK_LLM_EFFORT=$LlmEffort"' in run_ps1


def test_C50_the_directive_prompt_shows_what_earlier_directives_produced(tmp_path, monkeypatch):
    """Epoch 2 asked for order 4 at stages [5, 6] in 152 of 186 directives and none of those
    islands reached order 4, because the prompt never showed the model its own results. The
    tally attributes islands and elites to directive shapes and flags a dead end."""
    from rk_harness import outcomes, prompts
    from rk_harness.types import ArchiveState, RunState
    ev = []
    def d(did, order, stages, c_fixed=None, kind="directive_accepted"):
        e = {"kind": kind, "directive_id": did, "target_order": order, "stages": stages,
             "constraints": {"c_fixed": c_fixed} if c_fixed else {}, "source": "llm"}
        ev.append(e)
    def island(did, reached):
        ev.append({"kind": "island_start", "directive_id": did})
        ev.append({"kind": "island_done", "achieved_orders": reached})
    d("D-1", 4, [6, 5])
    for _ in range(25):
        island("D-1", {"3": 6})
    ev.append({"kind": "accepted", "directive_id": "D-1", "new_elite": True})
    d("D-2", 3, [4])
    for _ in range(3):
        island("D-2", {"3": 5, "2": 1})
    ev.append({"kind": "accepted", "directive_id": "D-2", "new_elite": True})
    ev.append({"kind": "accepted", "directive_id": "D-2", "new_elite": False})
    d("D-3", 4, [6], c_fixed={"1": "1/2"})
    island("D-3", {"4": 1, "3": 2})
    rows = outcomes.tally(ev)
    by = {(r["target_order"], tuple(r["stages"]), r["c_fixed"]): r for r in rows}
    r4 = by[(4, (5, 6), False)]
    assert r4["islands"] == 25 and r4["reached"][3] == 150 and r4["reached"][4] == 0
    assert r4["new_elites"] == 1 and r4["dead_end"] is True
    assert r4["islands_since_last_elite"] == 0             # its one elite came after all 25 islands
    r3 = by[(3, (4,), False)]
    assert r3["islands"] == 3 and r3["accepted"] == 2 and r3["new_elites"] == 1 and not r3["dead_end"]
    assert by[(4, (6,), True)]["reached"][4] == 1
    assert by[(4, (6,), True)]["islands_since_last_elite"] is None      # no elite yet
    assert rows[0]["c_fixed"] is True                       # most recently used shape first
    text = outcomes.format_rows(rows)
    assert "never reached its target order" in text.splitlines()[[i for i, l in enumerate(text.splitlines()) if l.startswith("4 | [5, 6]")][0]]
    arch = ArchiveState(0, 0, {1: {}, 2: {}, 3: {}, 4: {}}, (), ())
    st = RunState(1, 2, "2026-09-21T10:00:00Z", "2026-09-21T10:00:00Z", 0.0, 0, None)
    prompt = prompts.build_user_prompt(arch, st, [], [], history=text)
    assert "What recent directives produced" in prompt and '"c_fixed": {"1": "1/2"' in prompt
    assert prompt.index("What recent directives produced") < prompt.index("## Directive format")
    assert "What recent directives produced" not in prompts.build_user_prompt(arch, st, [], [])
    # and the reader never raises: no file means no section
    monkeypatch.setenv("RK_WORK_DIR", str(tmp_path / "nowhere"))
    assert outcomes.history_for_prompt() == ""


def test_C51_resolved_hypotheses_are_listed_and_a_repeated_predicate_is_dropped(tmp_path, monkeypatch):
    """22 proposals held 10 distinct predicates, one proposed 7 times, because the prompt
    listed only open and refuted hypotheses."""
    from rk_harness import ledger, prompts, runner
    from rk_harness.types import ArchiveState, RunState
    arch = ArchiveState(0, 0, {1: {}, 2: {}, 3: {}, 4: {}}, (), ())
    st = RunState(1, 2, "2026-09-21T10:00:00Z", "2026-09-21T10:00:00Z", 0.0, 0, None)
    done = {"id": "H-004", "statement": "s", "predicate": "fast.p3s6.heldout < fast.p3s5.heldout",
            "verdict": "inconclusive"}
    text = prompts.build_hypothesis_prompt(arch, st, [], [], resolved=[done])
    assert "H-004" in text and "(1)" in text
    hyps = [done]
    assert runner._same_predicate("FAST.p3s6.heldout <   fast.p3s5.heldout", hyps) == "H-004"
    assert runner._same_predicate("fast.p3s6.heldout > fast.p3s5.heldout", hyps) is None
    # end to end: the model proposes the same predicate again and the ledger does not grow
    work = tmp_path / "work"
    monkeypatch.setenv("RK_WORK_DIR", str(work))
    monkeypatch.setenv("RK_LLM", "codex")
    monkeypatch.setattr(runner, "_codex_capped", lambda gate: False)
    monkeypatch.setattr(ledger, "load_hypotheses", lambda: hyps)
    appended = []
    monkeypatch.setattr(ledger, "append_hypothesis", lambda h: appended.append(h))
    reply = json.dumps({"statement": "again", "mechanism": "m", "control": "c",
                        "predicate": "fast.p3s6.heldout  <  fast.p3s5.heldout", "min_samples": 50})
    monkeypatch.setattr(runner, "call_llm", lambda system, user: (reply, 0.0))
    runner._maybe_propose_hypothesis(st, arch, "HYPOTHESIZE", 7)
    assert appended == []
    assert "hypothesis_duplicate" in (work / "events.jsonl").read_text(encoding="utf-8")


def test_C52_the_view_shows_new_elites_and_what_recent_directive_shapes_reached(tmp_path, monkeypatch):
    work = tmp_path / "work"
    work.mkdir()
    lines = [
        {"ts": "2026-09-21T09:00:00Z", "kind": "directive_accepted", "directive_id": "D-9", "target_order": 4,
         "stages": [5, 6], "constraints": {}, "source": "llm"},
    ]
    for i in range(21):
        lines.append({"ts": "2026-09-21T09:%02d:00Z" % (i + 1), "kind": "island_start", "directive_id": "D-9"})
        lines.append({"ts": "2026-09-21T09:%02d:30Z" % (i + 1), "kind": "island_done", "achieved_orders": {"3": 4}})
    lines.append({"ts": "2026-09-21T09:50:00Z", "kind": "accepted", "directive_id": "D-9", "new_elite": True})
    (work / "events.jsonl").write_text("".join(json.dumps(d) + chr(10) for d in lines), encoding="utf-8")
    watch = _watch_module(tmp_path, monkeypatch, work)
    watch._cache.pop("outcomes", None)
    monkeypatch.setattr(watch, "_now", lambda: __import__("datetime").datetime(
        2026, 9, 21, 12, 0, tzinfo=__import__("datetime").timezone.utc))
    text = watch.render_once(width=220, height=120)
    assert "1 in the last 24 h" in _line_with(text, "new elites")
    assert "order 4 stages [5, 6]: 21 islands" in _line_with(text, "recent shape")
    # the whole row, from the panel alone, so the layout's column width cannot wrap it
    from rich.console import Console
    con = Console(width=400, record=True, force_terminal=False)
    con.print(watch.working_panel(watch.load_events()[0], []))
    row = _line_with(con.export_text(), "recent shape")
    watch._cache.pop("outcomes", None)
    assert "1 new elites (0 islands since the latest)" in row and "never reached its target" in row
