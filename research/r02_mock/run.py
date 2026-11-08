"""Render the R02 lattice mock screenshots.

usage: python3 -I run.py DATA_DIR OUT_DIR [--source binance.vision|api|synthetic]
DATA_DIR holds Binance spot 1m kline CSVs (one per UTC day).
"""
import argparse
import collections
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine import DAY, M15, Engine, load_m1, utc        # noqa: E402
from nodes import sanity                                  # noqa: E402
from render import Chart                                  # noqa: E402


def ts(s):
    from datetime import datetime, timezone
    return int(datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--source", default="binance.vision")
    ap.add_argument("--day", default="2025-06-05")
    ap.add_argument("--preview-ineligible", default="",
                    help="DATE:REASON, extra render with that day forced ineligible (style preview)")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)

    eng = Engine(load_m1(a.data_dir)).run()
    lats = sorted(eng.lattices.values(), key=lambda l: l.day0)
    window = [l for l in lats if "2025-06-01" <= l.date <= "2025-06-08"]
    eligible = [l for l in window if l.eligible]
    inelig = {l.date: l.reason for l in window if not l.eligible}
    outcomes = collections.Counter(e.status for e in eng.events if e.lat in window)

    day0 = ts(a.day + " 00:00")
    notes = []

    # 1 full day
    full = Chart(eng, day0 - 6 * 3600, day0 + DAY, asof=day0 + DAY, panel_at=day0 + 16 * 3600,
                 title_note=f"{a.day} UTC · markers as of 24:00 · panel as of 16:00")
    full.render(os.path.join(a.out_dir, "mock_day_full.png"))

    light = Chart(eng, day0 - 6 * 3600, day0 + DAY, asof=day0 + DAY, panel_at=day0 + 16 * 3600, theme="light",
                  title_note=f"{a.day} UTC · LIGHT THEME · markers as of 24:00 · panel as of 16:00")
    light.render(os.path.join(a.out_dir, "mock_day_full_light.png"))

    # extra: light theme at a moment with pending events (candles only up to that moment)
    pt = day0 + 13 * 3600 + 15 * 60
    Chart(eng, pt - 5 * 3600, pt, asof=pt, right_bars=14, theme="light",
          title_note=f"{a.day} 13:15 UTC · LIGHT THEME · live snapshot with pending markers and geometry").render(
        os.path.join(a.out_dir, "extra_light_pending_1315.png"))

    def first(status):
        d = day0
        while d <= ts("2025-06-08 00:00"):
            evs = [e for e in eng.events if e.lat.day0 == d and e.status == status]
            if evs:
                return evs[0], d
            d += DAY
        return None, None

    zooms = {}
    for status, fname in (("REJECT", "mock_zoom_reject.png"), ("BREAK", "mock_zoom_break.png")):
        ev, d = first(status)
        if ev is None:
            notes.append(f"no {status} in window")
            continue
        if d != day0:
            notes.append(f"first {status} not on {a.day}; used {utc(d):%Y-%m-%d}")
        t0 = ev.bar * M15
        z = Chart(eng, t0 - 4 * 3600, t0 + 4 * 3600 + M15, asof=t0 + 4 * 3600 + M15, right_bars=2,
                  tooltips=True, focus=ev,
                  title_note=f"zoom · first {status} {utc(ev.t_min):%Y-%m-%d %H:%M} UTC · "
                             f"pending geometry of the focus event overlaid as it was while pending")
        z.render(os.path.join(a.out_dir, fname))
        zooms[status] = (ev, z)

    if inelig:
        idate = sorted(inelig)[0]
        inote = f"{idate}: {inelig[idate]}"
    else:
        idate = "2025-06-06"
        inote = "no ineligible day in window"
    i0 = ts(idate + " 00:00")
    ic = Chart(eng, i0 - 6 * 3600, i0 + DAY, asof=i0 + DAY,
               title_note=f"{idate} UTC · {inote}")
    ic.render(os.path.join(a.out_dir, "mock_ineligible.png"))

    if a.preview_ineligible:
        # extra, clearly labelled: forces one day ineligible only to preview the §3 dimmed style
        pdate, preason = a.preview_ineligible.split(":")
        peng = Engine(load_m1(a.data_dir), force_ineligible={ts(pdate + " 00:00"): preason}).run()
        p0 = ts(pdate + " 00:00")
        Chart(peng, p0 - 6 * 3600, p0 + DAY, asof=p0 + DAY,
              title_note=f"{pdate} UTC · STYLE PREVIEW ONLY: day forced ineligible ({preason}); "
                         f"the real day is eligible").render(
            os.path.join(a.out_dir, "extra_ineligible_style_preview.png"))

    day_events = [e for e in eng.events if e.lat.day0 == day0]
    checks = {
        "data_source": a.source,
        **{k: v for k, v in sanity().items() if k in ("node_count", "f_min", "f_max")},
        "eval_days_processed": len(window),
        "eligible_days": len(eligible),
        "ineligible_days": inelig,
        "fresh_touches_per_eligible_day_mean": round(
            sum(1 for e in eng.events if e.lat in eligible) / max(len(eligible), 1), 3),
        "outcomes": {k: outcomes.get(k, 0) for k in ("REJECT", "BREAK", "INDETERMINATE", "CENSORED")},
        "pending_at_data_end": outcomes.get("PENDING", 0),
        "labels_drawn_day_0605": len(full.visible_labels),
        "max_label_overlap_px": round(full.overlap, 2),
        "max_label_overlap_pair_day_0605": full.worst_pair,
        "min_label_centre_spacing_px_day_0605": round(full.min_label_spacing, 2),
        "label_text_height_px": round(full.label_height, 2),
        "labels_under_panel_day_0605": full.panel_hits,
        "image_px": [2400, 1350],
        "labels_drawn_day_0605_light": len(light.visible_labels),
        "labels_under_panel_day_0605_light": light.panel_hits,
        "candles_under_panel_day_0605": full.candles_under_panel,
        "events_day_0605": len(day_events),
        "outcomes_day_0605": dict(collections.Counter(e.status for e in day_events)),
        "physical_entries_total": eng.physical_entries,
        "panel_0605_1600": full.panel_rows,
        "zoom_focus": {k: {"t": f"{utc(v[0].t_min):%Y-%m-%d %H:%M}", "tooltip": v[0].tooltip()}
                       for k, v in zooms.items()},
        "ineligible_render": inote,
        "notes": notes,
        "per_day": {l.date: {"anchor": l.anchor_date, "L": float(l.L), "H": float(l.H),
                             "eligible": l.eligible, "reason": l.reason,
                             "events": sum(1 for e in eng.events if e.lat is l),
                             "outcomes": dict(collections.Counter(e.status for e in eng.events if e.lat is l))}
                    for l in window},
    }
    with open(os.path.join(a.out_dir, "checks.json"), "w") as fh:
        json.dump(checks, fh, indent=1, default=str)
    print(json.dumps(checks, indent=1, default=str))


if __name__ == "__main__":
    main()
