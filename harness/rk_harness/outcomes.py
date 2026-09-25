"""What recent directives produced, for the directive prompt.

The directive prompt showed the grid but never what the model's own earlier choices had
produced. In epoch 2, up to 2026-09-24, 152 of 186 directives asked for order 4 at stages
[5, 6] without c_fixed, and none of their 5,237 islands yielded an order-4 candidate: the
islands keep A on a dyadic grid and solve b exactly, and at order 4 that system is
overdetermined unless the nodes are pinned. This module tallies, per directive shape, the
islands run, the orders the candidates actually reached and the new elites, from the tail of
events.jsonl, so a dead end is visible to the model that keeps choosing it.

Read-only, and never raises into its caller: the directive path falls back to an empty
section on any failure.
"""
from __future__ import annotations

import json
from collections import Counter

from rk_harness.paths import work_dir

# The tail read per directive call. Island and directive events are a small share of the
# stream (lane candidates dominate it), so this covers several hundred cycles.
TAIL_BYTES = 16 * 1024 * 1024
_WANTED = ('"directive_accepted"', '"directive_fallback"', '"island_start"', '"island_done"',
           '"kind": "accepted"')
# A shape needs this many islands before "never reached its target" is worth saying.
_DEAD_END_ISLANDS = 20


def read_events(max_bytes: int = TAIL_BYTES) -> list[dict]:
    """The directive, island and accepted events in the last max_bytes of events.jsonl."""
    path = work_dir() / "events.jsonl"
    try:
        size = path.stat().st_size
        with open(path, "rb") as fh:
            if size > max_bytes:
                fh.seek(size - max_bytes)
                fh.readline()                     # discard the partial line at the seam
            raw = fh.read().decode("utf-8", errors="replace")
    except OSError:
        return []
    out: list[dict] = []
    for line in raw.splitlines():
        if not any(w in line for w in _WANTED):
            continue
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if isinstance(ev, dict):
            out.append(ev)
    return out


def _shape(ev: dict) -> tuple:
    c = ev.get("constraints") or {}
    stages = tuple(sorted(int(s) for s in (ev.get("stages") or []) if isinstance(s, (int, float))))
    source = "fallback" if ev.get("kind") == "directive_fallback" else str(ev.get("source") or "llm")
    return (int(ev.get("target_order") or 0), stages, bool(c.get("c_fixed")), source)


def tally(events: list[dict]) -> list[dict]:
    """One row per directive shape (target order, stages, c_fixed set, source), most recently
    used first. Islands are attributed through island_start's directive_id, candidates and
    elites through accepted's."""
    shape_of: dict = {}
    rows: dict = {}
    last_use: dict = {}
    pending = None
    for i, ev in enumerate(events):
        kind = ev.get("kind")
        if kind in ("directive_accepted", "directive_fallback"):
            key = _shape(ev)
            shape_of[ev.get("directive_id")] = key
            row = rows.setdefault(key, {"directives": 0, "islands": 0, "reached": Counter(),
                                        "accepted": 0, "new_elites": 0})
            row["directives"] += 1
            last_use[key] = i
        elif kind == "island_start":
            pending = shape_of.get(ev.get("directive_id"))
        elif kind == "island_done":
            if pending is not None:
                row = rows[pending]
                row["islands"] += 1
                for order, n in (ev.get("achieved_orders") or {}).items():
                    try:
                        row["reached"][int(order)] += int(n)
                    except (TypeError, ValueError):
                        continue
                last_use[pending] = i
            pending = None
        elif kind == "accepted":
            key = shape_of.get(ev.get("directive_id"))
            if key is not None:
                rows[key]["accepted"] += 1
                rows[key]["new_elites"] += bool(ev.get("new_elite"))
    out = []
    for key, row in rows.items():
        order, stages, c_fixed, source = key
        out.append({"target_order": order, "stages": list(stages), "c_fixed": c_fixed,
                    "source": source, **row,
                    "dead_end": row["islands"] >= _DEAD_END_ISLANDS and row["reached"][order] == 0})
    out.sort(key=lambda r: -last_use.get((r["target_order"], tuple(r["stages"]), r["c_fixed"],
                                          r["source"]), -1))
    return out


def format_rows(rows: list[dict], limit: int = 12) -> str:
    """The prompt section, or "" when there is nothing to report."""
    if not rows:
        return ""
    lines = ["target_order | stages | c_fixed | source | directives | islands | "
             "candidates by order reached | new elites"]
    for r in rows[:limit]:
        reached = ", ".join(f"order {o}: {n}" for o, n in sorted(r["reached"].items(), reverse=True)) or "none"
        flag = "   <- never reached its target order" if r["dead_end"] else ""
        lines.append(f"{r['target_order']} | {r['stages']} | {'yes' if r['c_fixed'] else 'no'} | "
                     f"{r['source']} | {r['directives']} | {r['islands']} | {reached} | "
                     f"{r['new_elites']}{flag}")
    return "\n".join(lines)


def history_for_prompt() -> str:
    """format_rows over the current event tail; "" on any failure."""
    try:
        return format_rows(tally(read_events()))
    except Exception:  # noqa: BLE001 - the directive call must never fail on its history
        return ""
