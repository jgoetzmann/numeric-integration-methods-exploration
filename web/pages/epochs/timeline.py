"""The timeline figure on epochs.html (B29, B19, B20).

A Gantt-style chart: one row per event, dates on x. The date axis runs from the
month of the 2025 project's earliest commit to two days past the snapshot date.
It is broken between the 2025 project and the rk run; both parts share one
days-per-pixel scale, so bar lengths compare across the break.
"""
from datetime import date, timedelta

from web import fmt
from web.charts import bar, dot, figure as chart_figure, legend, num, table, text

LABEL_X = 4
X0 = 200
X1 = 704
GAP = 26
TOP = 44
ROW_H = 38
BAR_H = 14


def _date(s):
    return date.fromisoformat(fmt.day(s))


def _next_month(d):
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def _dates_text(ev):
    if ev["end"] is None:
        return fmt.day(ev["start"])
    return f"{fmt.day(ev['start'])} to {fmt.day(ev['end'])}"


def events(data):
    """The timeline rows, top to bottom. `end` is None for a one-day event; `n` is the
    series slot, None for the snapshot, which is drawn in currentColor."""
    ml = data["novel"]["repo"]
    ep = data["rk"]["epochs"]
    e1 = ep["epoch1"]
    e2 = ep["epoch2"]
    down = e2["down_days"]
    snap = data["sources"]["snapshot_date"]
    ml_repo = ml["source"]["repo"]
    rk_repo = ep["source"]["repo"]
    return [
        {
            "name": "2025 ML project",
            "what": "The 2025 ML project's active window",
            "extra": "when its main work was committed",
            "start": ml["active_from"],
            "end": ml["active_to"],
            "n": 2,
            "source": (ml_repo, "git log"),
        },
        {
            "name": "Epoch 1 runs",
            "what": "Epoch 1 runs",
            "extra": (
                f"{fmt.count(e1['cycles_run'])} search cycles, {fmt.count(e1['records'])} records, "
                f"runner started {fmt.count(e1['events']['runner_started'])} times for deploys"
            ),
            "start": e1["started"],
            "end": e1["stopped"],
            "n": 1,
            "source": (rk_repo, "epochs/1/RUNSTATE.json"),
        },
        {
            "name": "Epoch 1 frozen",
            "what": "Epoch 1 frozen",
            "extra": "archive kept, not rescored",
            "start": e1["frozen_at"],
            "end": None,
            "n": 1,
            "source": (rk_repo, "EPOCH.json"),
        },
        {
            "name": "Epoch 2 starts",
            "what": "Epoch 2 starts",
            "extra": f"verifier hash {e2['verifier_hash']}",
            "start": e2["started"],
            "end": None,
            "n": 1,
            "source": (rk_repo, ""),
        },
        {
            "name": "Epoch 2 stopped",
            "what": "The run stopped",
            "extra": down["why"],
            "start": down["from"],
            "end": down["to"],
            "n": 3,
            "source": (rk_repo, ""),
        },
        {
            "name": "Snapshot",
            "what": "Snapshot date of this site's data",
            "extra": "",
            "start": snap,
            "end": None,
            "n": None,
            "source": ("data/sources.json", ""),
        },
    ]


def _axis(data):
    """Return (x, a_end, b_start, ticks) for the broken date axis."""
    ml = data["novel"]["repo"]
    e1 = data["rk"]["epochs"]["epoch1"]
    snap = data["sources"]["snapshot_date"]
    earliest = _date(ml.get("first_commit") or ml["active_from"])
    a0 = date(earliest.year, earliest.month, 1)
    a1 = _next_month(_date(ml["active_to"]))
    b0 = _date(e1["started"]) - timedelta(days=4)
    b1 = _date(snap) + timedelta(days=2)
    a_days = (a1 - a0).days
    b_days = (b1 - b0).days
    per_day = (X1 - X0 - GAP) / (a_days + b_days)
    a_end = X0 + a_days * per_day
    b_start = a_end + GAP

    def x(d):
        if d <= a1:
            return X0 + (max(d, a0) - a0).days * per_day
        return b_start + (min(max(d, b0), b1) - b0).days * per_day

    ticks = []
    d = a0
    while d < a1:
        ticks.append((d, f"{d.year}-{d.month:02d}"))
        d = _next_month(d)
    d = b0
    while d <= b1:
        if d.day in (1, 15):
            ticks.append((d, d.isoformat()))
        d += timedelta(days=1)
    return x, a_end, b_start, ticks


def _inner(data, evs, axis_y):
    x, a_end, b_start, ticks = _axis(data)
    out = [legend([(1, "The rk run"), (2, "The 2025 ML project"), (3, "Run stopped")], X1, 22)]

    # Row separators and vertical grid lines at the ticks.
    for i in range(len(evs)):
        y = TOP + i * ROW_H
        out.append(
            f'<path class="grid" d="M{LABEL_X} {y}H{X1}" stroke="var(--grid)" stroke-width="1" fill="none"/>'
        )
    for d, _label in ticks:
        tx = x(d)
        out.append(
            f'<path class="grid" d="M{num(tx)} {TOP}V{axis_y}" stroke="var(--grid)" stroke-width="1" fill="none"/>'
        )

    # Snapshot reference line, behind the marks.
    sx = x(_date(evs[-1]["start"]))
    out.append(
        f'<path class="ref" d="M{num(sx)} {TOP}V{axis_y}" stroke="var(--text-2)" stroke-width="1" fill="none"/>'
    )

    # Axis in two parts with a break marker between them.
    out.append(
        f'<path class="axis" d="M{X0} {axis_y}H{num(a_end)}M{num(b_start)} {axis_y}H{X1}" '
        f'stroke="var(--text-2)" stroke-width="1" fill="none"/>'
    )
    mid = (a_end + b_start) / 2
    out.append(
        f'<path class="axis-break" d="M{num(mid - 7)} {axis_y + 6}L{num(mid - 1)} {axis_y - 6}'
        f'M{num(mid + 1)} {axis_y + 6}L{num(mid + 7)} {axis_y - 6}" '
        f'stroke="var(--text-2)" stroke-width="1" fill="none"/>'
    )
    for d, label in ticks:
        out.append(
            f'<text x="{num(x(d))}" y="{axis_y + 18}" font-size="12" text-anchor="middle" '
            f'fill="var(--text-2)">{fmt.esc(label)}</text>'
        )

    # Rows: a two-line label on the left, one mark per row.
    for i, ev in enumerate(evs):
        yc = TOP + i * ROW_H + 19
        dates = _dates_text(ev)
        out.append(text(LABEL_X, yc - 2, ev["name"], size=13))
        out.append(text(LABEL_X, yc + 13, dates, muted=True))
        tip = f"{ev['what']}: {dates}" + (f", {ev['extra']}" if ev["extra"] else "")
        xa = x(_date(ev["start"]))
        if ev["n"] is None:
            out.append(
                f'<circle class="mark event snapshot" cx="{num(xa)}" cy="{yc + 1}" r="4" '
                f'fill="currentColor"><title>{fmt.esc(tip)}</title></circle>'
            )
        elif ev["end"] is None:
            out.append(dot(xa, yc + 1, ev["n"], tip))
        else:
            out.append(bar(xa, yc + 1 - BAR_H // 2, max(x(_date(ev["end"])) - xa, 2.0), BAR_H, ev["n"], tip))
    return "".join(out)


def _source(ev):
    repo, path = ev["source"]
    return f"<code>{fmt.esc(repo)}</code>" + (f" <code>{fmt.esc(path)}</code>" if path else "")


def figure(data):
    """The complete <figure id="timeline" class="chart"> element."""
    evs = events(data)
    axis_y = TOP + ROW_H * len(evs)
    ml = data["novel"]["repo"]
    snap = fmt.day(data["sources"]["snapshot_date"])
    windows = [e for e in evs if e["end"] is not None]
    points = [e for e in evs if e["end"] is None]
    desc = (
        f"Date axis from {fmt.day(ml.get('first_commit') or ml['active_from'])[:7]} to {snap}, "
        "broken between the two projects, one scale on both sides. Bars: "
        + "; ".join(f"{e['what']}, {_dates_text(e)}" for e in windows)
        + ". Points: "
        + "; ".join(f"{e['what']}, {_dates_text(e)}" for e in points)
        + "."
    )
    caption = (
        "When the 2025 ML project did its main work, and the rk run's two epochs up to the "
        f"snapshot on {snap}. The date axis is broken between October 2025 and late August "
        "2026. Both parts share one scale, so bar lengths can be compared across the break."
    )
    rows = [[fmt.esc(ev["what"]), fmt.day(ev["start"]), fmt.day(ev["end"] or ev["start"]), _source(ev)]
            for ev in evs]
    return chart_figure({
        "id": "timeline",
        "height": axis_y + 28,
        "title": "Timeline of the 2025 ML project and the rk run's epochs",
        "desc": desc,
        "inner": _inner(data, evs, axis_y),
        "caption": fmt.esc(caption),
        "table": table(["Event", "Start", "End", "Source"], rows),
    })
