"""The timeline figure on epochs.html (B29, B19, B20).

A Gantt-style chart: one row per event, dates on x. The date axis runs from the
month of the 2025 project's earliest commit to two days past the snapshot date.
It is broken between the 2025 project and the rk run; both parts share one
days-per-pixel scale, so bar lengths compare across the break.
"""
from datetime import date, timedelta

from web import fmt

FIG_ID = "timeline"
WIDTH = 720
LABEL_X = 4
X0 = 200
X1 = 704
GAP = 26
TOP = 44
ROW_H = 38
BAR_H = 14
RADIUS = 4

RK_FILL = "var(--series-1)"
ML_FILL = "var(--series-2)"
STOP_FILL = "var(--series-3)"
SNAP_FILL = "currentColor"


def _date(s):
    return date.fromisoformat(fmt.day(s))


def _next_month(d):
    if d.month == 12:
        return date(d.year + 1, 1, 1)
    return date(d.year, d.month + 1, 1)


def _n(v):
    return f"{v:.1f}"


def _dates_text(ev):
    if ev["end"] is None:
        return fmt.day(ev["start"])
    return f"{fmt.day(ev['start'])} to {fmt.day(ev['end'])}"


def events(data):
    """The timeline rows, top to bottom. `end` is None for a one-day event."""
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
            "fill": ML_FILL,
            "kind": "ml2025",
            "source": (ml_repo, "git log"),
        },
        {
            "name": "Epoch 1 runs",
            "what": "Epoch 1 runs unattended",
            "extra": f"{fmt.count(e1['cycles_run'])} cycles, {fmt.count(e1['records'])} records",
            "start": e1["started"],
            "end": e1["stopped"],
            "fill": RK_FILL,
            "kind": "epoch1",
            "source": (rk_repo, "epochs/1/RUNSTATE.json"),
        },
        {
            "name": "Epoch 1 frozen",
            "what": "Epoch 1 frozen",
            "extra": "archive kept, not rescored",
            "start": e1["frozen_at"],
            "end": None,
            "fill": RK_FILL,
            "kind": "freeze",
            "source": (rk_repo, "EPOCH.json"),
        },
        {
            "name": "Epoch 2 starts",
            "what": "Epoch 2 starts",
            "extra": f"verifier hash {e2['verifier_hash']}",
            "start": e2["started"],
            "end": None,
            "fill": RK_FILL,
            "kind": "epoch2",
            "source": (rk_repo, ""),
        },
        {
            "name": "Epoch 2 stopped",
            "what": "The run stopped",
            "extra": "nothing restarted it",
            "start": down["from"],
            "end": down["to"],
            "fill": STOP_FILL,
            "kind": "stopped",
            "source": (rk_repo, ""),
        },
        {
            "name": "Snapshot",
            "what": "Snapshot date of this site's data",
            "extra": "",
            "start": snap,
            "end": None,
            "fill": SNAP_FILL,
            "kind": "snapshot",
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


def _svg(data, evs):
    x, a_end, b_start, ticks = _axis(data)
    axis_y = TOP + ROW_H * len(evs)
    height = axis_y + 28
    snap_ev = evs[-1]
    windows = [e for e in evs if e["end"] is not None]
    points = [e for e in evs if e["end"] is None]
    title = "Timeline of the 2025 ML project and the rk run's epochs"
    desc = (
        "Date axis from "
        + fmt.day(data["novel"]["repo"].get("first_commit") or data["novel"]["repo"]["active_from"])[:7]
        + " to "
        + fmt.day(data["sources"]["snapshot_date"])
        + ", broken between the two projects, one scale on both sides. Bars: "
        + "; ".join(f"{e['what']}, {_dates_text(e)}" for e in windows)
        + ". Points: "
        + "; ".join(f"{e['what']}, {_dates_text(e)}" for e in points)
        + "."
    )
    out = [
        f'<svg viewBox="0 0 {WIDTH} {height}" role="img" '
        f'aria-labelledby="{FIG_ID}-title {FIG_ID}-desc">',
        f'<title id="{FIG_ID}-title">{fmt.esc(title)}</title>',
        f'<desc id="{FIG_ID}-desc">{fmt.esc(desc)}</desc>',
    ]

    # Legend.
    legend = [
        ("bar", RK_FILL, "The rk run"),
        ("bar", ML_FILL, "The 2025 ML project"),
        ("bar", STOP_FILL, "Run stopped"),
        ("dot", SNAP_FILL, "Snapshot date"),
    ]
    lx = float(LABEL_X)
    for shape, fill, label in legend:
        if shape == "bar":
            out.append(
                f'<rect class="legend-key" x="{_n(lx)}" y="12" width="12" height="12" fill="{fill}"/>'
            )
        else:
            out.append(
                f'<circle class="legend-key" cx="{_n(lx + 6)}" cy="18" r="{RADIUS}" fill="{fill}"/>'
            )
        out.append(
            f'<text x="{_n(lx + 18)}" y="22" font-size="12" fill="currentColor">{fmt.esc(label)}</text>'
        )
        lx += 18 + len(label) * 6.8 + 22

    # Row separators and vertical grid lines at the ticks.
    for i in range(len(evs)):
        y = TOP + i * ROW_H
        out.append(
            f'<path class="grid" d="M{LABEL_X} {y}H{X1}" stroke="var(--grid)" stroke-width="1" fill="none"/>'
        )
    for d, _label in ticks:
        tx = x(d)
        out.append(
            f'<path class="grid" d="M{_n(tx)} {TOP}V{axis_y}" stroke="var(--grid)" stroke-width="1" fill="none"/>'
        )

    # Snapshot reference line, behind the marks.
    sx = x(_date(snap_ev["start"]))
    out.append(
        f'<path class="ref" d="M{_n(sx)} {TOP}V{axis_y}" stroke="var(--text-2)" stroke-width="1" fill="none"/>'
    )

    # Axis in two parts with a break marker between them.
    out.append(
        f'<path class="axis" d="M{X0} {axis_y}H{_n(a_end)}M{_n(b_start)} {axis_y}H{X1}" '
        f'stroke="var(--text-2)" stroke-width="1" fill="none"/>'
    )
    mid = (a_end + b_start) / 2
    out.append(
        f'<path class="axis-break" d="M{_n(mid - 7)} {axis_y + 6}L{_n(mid - 1)} {axis_y - 6}'
        f'M{_n(mid + 1)} {axis_y + 6}L{_n(mid + 7)} {axis_y - 6}" '
        f'stroke="var(--text-2)" stroke-width="1" fill="none"/>'
    )
    for d, label in ticks:
        out.append(
            f'<text x="{_n(x(d))}" y="{axis_y + 18}" font-size="12" text-anchor="middle" '
            f'fill="var(--text-2)">{fmt.esc(label)}</text>'
        )

    # Rows: a two-line label on the left, one mark per row.
    for i, ev in enumerate(evs):
        yc = TOP + i * ROW_H + 19
        dates = _dates_text(ev)
        out.append(
            f'<text x="{LABEL_X}" y="{yc - 2}" font-size="13" fill="currentColor">{fmt.esc(ev["name"])}</text>'
        )
        out.append(
            f'<text x="{LABEL_X}" y="{yc + 13}" font-size="12" fill="var(--text-2)">{fmt.esc(dates)}</text>'
        )
        tip = f"{ev['what']}: {dates}"
        if ev["extra"]:
            tip += f", {ev['extra']}"
        if ev["end"] is None:
            cx = x(_date(ev["start"]))
            out.append(
                f'<circle class="mark event {ev["kind"]}" cx="{_n(cx)}" cy="{yc + 1}" r="{RADIUS}" '
                f'fill="{ev["fill"]}"><title>{fmt.esc(tip)}</title></circle>'
            )
        else:
            xa = x(_date(ev["start"]))
            xb = x(_date(ev["end"]))
            w = max(xb - xa, 2.0)
            out.append(
                f'<rect class="mark window {ev["kind"]}" x="{_n(xa)}" y="{yc + 1 - BAR_H // 2}" '
                f'width="{_n(w)}" height="{BAR_H}" fill="{ev["fill"]}"><title>{fmt.esc(tip)}</title></rect>'
            )

    out.append("</svg>")
    return "\n".join(out)


def _table(evs):
    rows = []
    for ev in evs:
        start = fmt.day(ev["start"])
        end = fmt.day(ev["end"]) if ev["end"] is not None else start
        repo, path = ev["source"]
        src = f"<code>{fmt.esc(repo)}</code>"
        if path:
            src += f" <code>{fmt.esc(path)}</code>"
        rows.append(
            f"<tr><td>{fmt.esc(ev['what'])}</td><td>{start}</td><td>{end}</td><td>{src}</td></tr>"
        )
    return (
        '<details class="data"><summary>Data table</summary>\n<table>\n'
        "<thead><tr><th>Event</th><th>Start</th><th>End</th><th>Source</th></tr></thead>\n"
        "<tbody>\n" + "\n".join(rows) + "\n</tbody>\n</table>\n</details>"
    )


def figure(data):
    """The complete <figure id="timeline" class="chart"> element."""
    evs = events(data)
    snap = fmt.day(data["sources"]["snapshot_date"])
    caption = (
        "When the 2025 ML project did its main work, and the rk run's two epochs up to the "
        f"snapshot on {snap}. The date axis is broken between October 2025 and late August "
        "2026; both parts share one scale, so bar lengths compare."
    )
    return (
        f'<figure id="{FIG_ID}" class="chart">\n'
        + _svg(data, evs)
        + f"\n<figcaption>{fmt.esc(caption)}</figcaption>\n"
        + _table(evs)
        + "\n</figure>"
    )
