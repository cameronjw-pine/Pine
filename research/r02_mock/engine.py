"""R02 event contract (plan §2) on M1 data, minute by minute.

Levels and bands are exact Fractions (prices parsed exactly from the decimal
strings); ATR and pi/R ratios are floats, as in Pine.
"""
import csv
import glob
import math
import os
from collections import deque
from datetime import datetime, timezone
from fractions import Fraction

from nodes import NODES

MIN = 60
M15 = 900
DAY = 86400
FRESH_BARS = 20
W = 12
ATR_LEN = 14
MINTICK = Fraction(1, 100)          # BINANCE:BTCUSDC
TICK_GATE = Fraction(1, 41000)
HYG_WIN, HYG_MIN, HYG_K = 1440, 720, 10.0


def ts_to_sec(raw):
    v = int(raw)
    if v > 10 ** 14:      # microseconds (2025+ spot files)
        return v // 1_000_000
    if v > 10 ** 11:      # milliseconds
        return v // 1000
    return v


def utc(t):
    return datetime.fromtimestamp(t, tz=timezone.utc)


def load_m1(data_dir):
    rows = {}
    for path in sorted(glob.glob(os.path.join(data_dir, "*.csv"))):
        with open(path, newline="") as fh:
            for r in csv.reader(fh):
                if not r or not r[0].strip().isdigit():
                    continue
                t = ts_to_sec(r[0])
                rows[t] = (Fraction(r[1]), Fraction(r[2]), Fraction(r[3]), Fraction(r[4]))
    ts = sorted(rows)
    return [(t,) + rows[t] for t in ts]


def aggregate_m15(m1):
    bars = {}
    for t, o, h, l, c in m1:
        k = t // M15
        if k not in bars:
            bars[k] = [o, h, l, c, 1]
        else:
            b = bars[k]
            b[1] = max(b[1], h)
            b[2] = min(b[2], l)
            b[3] = c
            b[4] += 1
    return bars  # key: M15 index (t//900) -> [o,h,l,c,count]


def compute_atr(bars, k0, k1):
    """ATR value at the close of each M15 bar k (None until seeded)."""
    atr = {}
    prev_c = None
    seed = []
    cur = None
    for k in range(k0, k1 + 1):
        b = bars.get(k)
        if b is None or b[4] < 15:              # source gap -> reset
            atr[k] = None
            prev_c, seed, cur = None, [], None
            continue
        o, h, l, c, _ = b
        if prev_c is None:
            tr = float(h - l)
        else:
            tr = float(max(h - l, abs(h - prev_c), abs(l - prev_c)))
        prev_c = c
        if cur is None:
            seed.append(tr)
            if len(seed) == ATR_LEN:
                cur = sum(seed) / ATR_LEN
        else:
            cur = (cur * (ATR_LEN - 1) + tr) / ATR_LEN
        atr[k] = cur
    return atr


def hygiene_flags(m1):
    """Return {later-minute time: (r, flagged)} for every residual (§2.1)."""
    out = {}
    win = deque()
    s = s2 = 0.0
    prev = None
    for t, o, h, l, c in m1:
        mid = math.log(float((h + l) / 2))
        if prev is not None and t - prev[0] == MIN:
            r = mid - prev[1]
            flagged = False
            n = len(win)
            if n >= HYG_MIN:
                var = (s2 - s * s / n) / (n - 1)
                sd = math.sqrt(max(var, 0.0))
                flagged = abs(r) > HYG_K * sd
            if not flagged:
                win.append(r)
                s += r
                s2 += r * r
                if len(win) > HYG_WIN:
                    x = win.popleft()
                    s -= x
                    s2 -= x * x
            out[t] = (r, flagged)
        prev = (t, mid)
    return out


class Lattice:
    """One evaluation day's published lattice."""

    def __init__(self, day0, L, H, n_prior, eligible, reason):
        self.day0 = day0                # 00:00 UTC of the evaluation day (sec)
        self.L, self.H = L, H
        self.n_prior = n_prior
        self.eligible = eligible
        self.reason = reason            # None or incomplete/range/tick/hygiene
        self.pub_time = None            # set at publication
        self.end_time = day0 + DAY      # 24:00 UTC
        self.bands = []                 # (node, lo, hi, level)
        for nd in NODES:
            lo, hi = nd.band(L, H)
            self.bands.append((nd, lo, hi, nd.level(L, H)))

    @property
    def date(self):
        return utc(self.day0).strftime("%Y-%m-%d")

    @property
    def anchor_date(self):
        return utc(self.day0 - DAY).strftime("%Y-%m-%d")


class Event:
    def __init__(self, node, level, lo, hi, side, atr, t_min, bar, entry_px, lat):
        self.node = node
        self.level = float(level)
        self.level_exact = level
        self.band = (lo, hi)
        self.side = side                # 'below' or 'above'
        self.atr = atr
        self.t_min = t_min              # M1 open time containing the entry
        self.bar = bar                  # containing M15 index t
        self.entry_px = entry_px
        self.lat = lat
        self.pen = 0.0                  # max penetration (price units)
        self.rev = 0.0                  # max reversal (price units)
        self.status = "PENDING"
        self.t_resolved = None          # time (sec) from which status is final
        self.hist = []                  # (minute_end_time, pen, rev)

    @property
    def horizon_end_bar(self):
        return self.bar + W - 1

    @property
    def horizon_end_time(self):
        return (self.horizon_end_bar + 1) * M15

    def feed(self, px):
        px = float(px)
        d = px - self.level
        if self.side == "below":
            self.pen = max(self.pen, d)
            self.rev = max(self.rev, -d)
        else:
            self.pen = max(self.pen, -d)
            self.rev = max(self.rev, d)
        return self.pen >= 1.0 * self.atr

    def pi_r(self, at=None):
        if at is None:
            pen, rev = self.pen, self.rev
        else:
            pen = rev = 0.0
            for te, p, r in self.hist:
                if te <= at:
                    pen, rev = p, r
        return pen / self.atr, rev / self.atr

    def status_at(self, t):
        if self.t_resolved is not None and t >= self.t_resolved:
            return self.status
        return "PENDING"

    def tooltip(self, at=None):
        st = self.status if at is None else self.status_at(at)
        pi, r = self.pi_r(None if st != "PENDING" else at)
        side = "from below" if self.side == "below" else "from above"
        return f"{self.node.label} · {side} · ATR {self.atr:.2f} · {st} (π {pi:.2f}, R {r:.2f})"


def day_of(t):
    return t - t % DAY


class Engine:
    def __init__(self, m1, hygiene_on=True, require_complete=True, force_ineligible=None):
        self.m1 = m1
        self.force_ineligible = force_ineligible or {}
        self.hygiene_on = hygiene_on
        self.require_complete = require_complete
        self.bars = aggregate_m15(m1)
        self.k0 = min(self.bars)
        self.k1 = max(self.bars)
        self.atr = compute_atr(self.bars, self.k0, self.k1)
        self.hyg = hygiene_flags(m1)
        self.by_day = {}
        for row in m1:
            self.by_day.setdefault(day_of(row[0]), []).append(row)
        self.lattices = {}              # day0 -> Lattice
        self.events = []
        self.physical_entries = 0
        self.first_tracked_bar = None   # recovery: first fully tracked M15 bar
        self.close_at = {}              # minute end time -> close

    # ---- §2.1 eligibility -------------------------------------------------
    def make_lattice(self, day0):
        prior = self.by_day.get(day0 - DAY)
        if not prior:
            return None
        L = min(r[3] for r in prior)
        H = max(r[2] for r in prior)
        n = len(prior)
        reason = None
        if self.require_complete and n != 1440:
            reason = "incomplete"
        elif not H > L:
            reason = "range"
        elif MINTICK / (H - L) > TICK_GATE:
            reason = "tick"
        elif self.hygiene_on:
            lo_t, hi_t = day0 - DAY, day0
            for t, (r, fl) in self.hyg.items():
                if fl and lo_t <= t <= hi_t:   # later minute in prior day, or 00:00
                    reason = "hygiene"
                    break
        if reason is None and day0 in self.force_ineligible:   # style preview only
            reason = self.force_ineligible[day0]
        return Lattice(day0, L, H, n, reason is None, reason)

    def known(self, k):
        """Freshness knowledge for an entry in M15 bar k (§2.5, §2.7)."""
        if self.first_tracked_bar is None:
            return False
        lo = k - FRESH_BARS
        if lo < self.first_tracked_bar:
            return False
        for j in range(lo, k):
            b = self.bars.get(j)
            if b is None or b[4] < 15:
                return False
        return True

    # ---- main loop --------------------------------------------------------
    def run(self):
        last_entry = {}                 # band identity f -> last physical entry M15 index
        inside = {}                     # f -> bool for the active lattice
        active = None
        pending = []
        prev_c = None
        prev_t = None
        checked_bar = None
        for t, o, h, l, c in self.m1:
            k = t // M15
            d0 = day_of(t)
            # gap / censoring checks at bar change
            if checked_bar is None:
                checked_bar = k
            while checked_bar < k:
                b = self.bars.get(checked_bar)
                if b is None or b[4] < 15:
                    for ev in pending:
                        if ev.bar <= checked_bar <= ev.horizon_end_bar:
                            ev.status = "CENSORED"
                            ev.t_resolved = (checked_bar + 1) * M15
                    pending = [e for e in pending if e.status == "PENDING"]
                checked_bar += 1
            # horizon ends (close of bar t+11 already passed)
            for ev in pending:
                if k > ev.horizon_end_bar:
                    self._finalize(ev)
            pending = [e for e in pending if e.status == "PENDING"]

            # lattice expiry at 24:00 and publication at first open >= 00:01
            if active is not None and t >= active.end_time:
                active = None
            published_now = False
            if active is None and t >= d0 + MIN and d0 not in self.lattices:
                lat = self.make_lattice(d0)
                if lat is not None:
                    lat.pub_time = t
                    self.lattices[d0] = lat
                    active = lat
                    published_now = True
                    if self.first_tracked_bar is None:
                        # tracking starts mid-bar; first fully tracked bar is the next one
                        self.first_tracked_bar = k + 1 if t % M15 else k
                    for nd, lo, hi, lev in lat.bands:
                        inside[nd.f] = lo <= o <= hi

            pts = [o, l, h, c] if c >= o else [o, h, l, c]
            new_events = []
            if active is not None:
                for nd, lo, hi, lev in active.bands:
                    f = nd.f
                    entries = []        # (leg index, entry price, side)
                    st = inside[f]
                    if not published_now:
                        ino = lo <= o <= hi
                        if not st and ino and prev_c is not None:
                            entries.append((-1, o, "below" if prev_c < lo else "above"))
                        st = ino
                    for i in range(3):
                        p0, p1 = pts[i], pts[i + 1]
                        if not st and p0 != p1:
                            a, b = (p0, p1) if p0 < p1 else (p1, p0)
                            if a <= hi and b >= lo:
                                if p0 < lo:
                                    entries.append((i, lo, "below"))
                                else:
                                    entries.append((i, hi, "above"))
                        st = lo <= p1 <= hi
                    inside[f] = st
                    for leg, epx, side in entries:
                        self.physical_entries += 1
                        fresh = (last_entry.get(f) is None or last_entry[f] < k - FRESH_BARS) and self.known(k)
                        last_entry[f] = k
                        if not fresh or not active.eligible:
                            continue
                        if t % M15 == 0:            # ATR knowledge pause
                            continue
                        atr = self.atr.get(k - 1)
                        if atr is None:
                            continue
                        ev = Event(nd, lev, lo, hi, side, atr, t, k, epx, active)
                        post = [epx] + pts[leg + 1:]
                        new_events.append((ev, post))
            # advance pending events over this minute's path
            t_end = t + MIN
            for ev in pending:
                for px in pts:
                    if ev.feed(px):
                        ev.status, ev.t_resolved = "BREAK", t_end
                        break
                ev.hist.append((t_end, ev.pen, ev.rev))
            for ev, post in new_events:
                for px in post:
                    if ev.feed(px):
                        ev.status, ev.t_resolved = "BREAK", t_end
                        break
                ev.hist.append((t_end, ev.pen, ev.rev))
                self.events.append(ev)
                if ev.status == "PENDING":
                    pending.append(ev)
            pending = [e for e in pending if e.status == "PENDING"]
            # horizon closes with this minute?
            for ev in pending:
                if t_end >= ev.horizon_end_time:
                    self._finalize(ev)
            pending = [e for e in pending if e.status == "PENDING"]
            self.close_at[t_end] = c
            prev_c, prev_t = c, t
        self.data_end = prev_t + MIN
        return self

    def _finalize(self, ev):
        pi, r = ev.pen / ev.atr, ev.rev / ev.atr
        if pi <= 0.25 and r >= 1.0:
            ev.status = "REJECT"
        else:
            ev.status = "INDETERMINATE"
        ev.t_resolved = ev.horizon_end_time

    # ---- snapshots --------------------------------------------------------
    def lattice_at(self, t):
        for lat in self.lattices.values():
            if lat.pub_time is not None and lat.pub_time <= t < lat.end_time:
                return lat
        return None

    def panel_at(self, t):
        """Panel rows as of time t (state after all minutes ending <= t)."""
        lat = self.lattice_at(t - 1) or self.lattice_at(t)
        price = self.close_at.get(t)
        k_last = t // M15 - 1
        atr = self.atr.get(k_last)
        rows = [("R02 {2,3} lattice", "")]
        if lat is None:
            return rows
        rows.append(("Anchor", f"{lat.anchor_date}  L {fmt(lat.L)} H {fmt(lat.H)}"))
        rows.append(("Status", "ELIGIBLE" if lat.eligible else f"INELIGIBLE: {lat.reason}"))
        rows.append(("ATR15", f"{atr:,.2f}" if atr is not None else "n/a"))
        above = [b for b in lat.bands if b[3] > price]
        below = [b for b in lat.bands if b[3] < price]
        if above:
            nd, _, _, lev = min(above, key=lambda b: b[3])
            rows.append(("Above", f"{nd.label} @ {fmt(lev)} ({(float(lev) - float(price)) / atr:+.2f} ATR)"))
        else:
            rows.append(("Above", "none"))
        if below:
            nd, _, _, lev = max(below, key=lambda b: b[3])
            rows.append(("Below", f"{nd.label} @ {fmt(lev)} ({(float(lev) - float(price)) / atr:+.2f} ATR)"))
        else:
            rows.append(("Below", "none"))
        npend = sum(1 for e in self.events if e.t_min < t and e.status_at(t) == "PENDING")
        rows.append(("Pending", str(npend)))
        return rows


def fmt(x):
    return f"{float(x):,.2f}"
