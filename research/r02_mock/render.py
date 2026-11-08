"""TradingView dark-theme mimic that draws the plan §3 visual spec.

Scale: 2400 px wide, 1 CSS px = 2 device px (deviceScaleFactor 2), dpi 200.
"""
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt                      # noqa: E402
from matplotlib.patches import Rectangle             # noqa: E402
from matplotlib.transforms import offset_copy        # noqa: E402

from engine import M15, DAY, utc, fmt                # noqa: E402

# ---- device scale ---------------------------------------------------------
W_PX, H_PX, DPI, CSS = 2400, 1350, 200, 2
PT = CSS * 72.0 / DPI            # points per CSS px
plt.rcParams["lines.scale_dashes"] = False
plt.rcParams["font.family"] = "DejaVu Sans"

# ---- TradingView chrome (dark theme) --------------------------------------
THEMES = {   # TradingView chrome; fg = chart.fg_color, bg = chart.bg_color
    "dark": dict(bg="#131722", grid="#1e222d", axis="#B2B5BE", sep="#2A2E39", fg="#D1D4DC",
                 tip_bg="#2A2E39", tip_ec="#434651"),
    "light": dict(bg="#FFFFFF", grid="#F0F3FA", axis="#131722", sep="#E0E3EB", fg="#131722",
                  tip_bg="#FFFFFF", tip_ec="#B2B5BE"),
}
UP, DOWN = "#26a69a", "#ef5350"
SCALE_W, TIME_H = 70, 28         # CSS px
CAP_H = 22                       # CSS px, mock caption strip above the chart (not part of the chart)
AXIS_FS = 11                     # CSS px
TINY_FS = 9                      # CSS px, size.tiny (mock assumption)
TRI_PX = 8                       # CSS px, size.tiny triangle (mock assumption)

# ---- §3 spec ----------------------------------------------------------------
GOLD = "#E8A317"
LAT_STYLE = {                    # h -> (colour, width, style, transp)
    0: (GOLD, 2, "solid", 0),
    1: (GOLD, 1, "solid", 0),
    2: (GOLD, 1, "solid", 40),
    3: (GOLD, 1, "dotted", 65),
    4: (GOLD, 1, "dotted", 80),
}
LIGHT_TRANSP = {3: 45, 4: 60}    # r2: h3/h4 on light backgrounds (luminance of chart.bg_color > 128)


def is_light(hex_bg):
    r, g, b = (int(hex_bg[i:i + 2], 16) for i in (1, 3, 5))
    return 0.299 * r + 0.587 * g + 0.114 * b > 128
PDHL = ("#808080", 1, "dashed", 0)
INELIG = ("#9E9E9E", "dotted", 70)                      # r1
MARKER = {
    "PENDING": ("#E8A317", 0),                          # r1
    "REJECT": ("#2962FF", 0),
    "BREAK": ("#E040FB", 50),
    "INDETERMINATE": ("#787B86", 50),
    "CENSORED": ("#787B86", 80),
}
BOX_FILL = (GOLD, 85)
REJ_LINE = ("#2962FF", 1, "dashed")                      # r1
BRK_LINE = ("#E040FB", 1, "dotted")
LABEL_MAX_H = 2
PANEL_BG_TRANSP = 20             # r1: bgcolor=color.new(chart.bg_color, 20), text_color=chart.fg_color


def alpha(transp):
    return 1.0 - transp / 100.0


def dashes(style, width):
    w = width * PT
    if style == "solid":
        return dict(linestyle="solid")
    if style == "dotted":
        return dict(linestyle=(0, (1 * PT * width, 2 * PT * width)), dash_capstyle="butt")
    if style == "dashed":
        return dict(linestyle=(0, (4 * PT * width, 4 * PT * width)), dash_capstyle="butt")
    raise ValueError(style)


class Chart:
    def __init__(self, eng, t_from, t_to, asof, right_bars=6, panel_at=None,
                 tooltips=False, focus=None, title_note="", theme="dark", geom_mode="Nearest"):
        self.th = THEMES[theme]
        self.light = is_light(self.th["bg"])
        self.geom_mode = geom_mode          # r2 input: Nearest / All / Off
        self.eng = eng
        self.t_from, self.t_to, self.asof = t_from, t_to, asof
        self.k_from = t_from // M15
        self.right_bars = right_bars
        self.panel_at = panel_at if panel_at is not None else asof
        self.tooltips = tooltips
        self.focus = focus
        self.title_note = title_note
        self.labels = []          # (artist, kind)

    def x(self, t):
        return (t - self.k_from * M15) / M15

    # -------------------------------------------------------------------
    def render(self, path):
        eng = self.eng
        fig = plt.figure(figsize=(W_PX / DPI, H_PX / DPI), dpi=DPI, facecolor=self.th["bg"])
        self.fig = fig
        sw, th, ch = SCALE_W * CSS / W_PX, TIME_H * CSS / H_PX, CAP_H * CSS / H_PX
        ax = fig.add_axes([0, th, 1 - sw, 1 - th - ch], facecolor=self.th["bg"])
        self.ax = ax
        for s in ax.spines.values():
            s.set_visible(False)
        ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)

        ks = [k for k in sorted(eng.bars) if self.t_from <= k * M15 < self.t_to]
        bars = [(k, eng.bars[k]) for k in ks]
        n = len(ks)
        lo = min(float(b[2]) for _, b in bars)
        hi = max(float(b[1]) for _, b in bars)
        pad_top, pad_bot = 0.10, 0.08            # TV default scale margins
        rng = hi - lo
        y0, y1 = lo - pad_bot * rng / (1 - pad_top - pad_bot), hi + pad_top * rng / (1 - pad_top - pad_bot)
        x0, x1 = -1.0, n - 1 + self.right_bars
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)

        self._grid_and_axes(ax, y0, y1, x0, x1)
        self._candles(ax, bars)
        self._bars = bars
        self._lattices(ax)
        self._events(ax)
        self._header(fig)
        if self.panel_at is not None:
            self._panel(fig, ax)
        fig.savefig(path, dpi=DPI, facecolor=self.th["bg"])
        self.overlap = self._label_overlap(fig)
        plt.close(fig)
        return self

    # -------------------------------------------------------------------
    def _grid_and_axes(self, ax, y0, y1, x0, x1):
        fig = self.fig
        # price ticks: nice step giving ~ 10-14 levels
        raw = (y1 - y0) / 12
        mag = 10 ** math.floor(math.log10(raw))
        step = min((m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw))
        p = math.ceil(y0 / step) * step
        sep_x = 1 - SCALE_W * CSS / W_PX
        while p < y1:
            ax.axhline(p, color=self.th["grid"], lw=1 * PT, zorder=0)
            yf = self._fig_y(p)
            fig.text(sep_x + 8 * CSS / W_PX, yf, f"{p:.2f}", color=self.th["axis"],
                     fontsize=AXIS_FS * PT, va="center", ha="left")
            p += step
        # time ticks
        span_h = (x1 - x0) * M15 / 3600
        hstep = next(s for s in (1, 2, 3, 4, 6, 12, 24) if span_h / s <= 12)
        t = (self.t_from // 3600) * 3600
        th = TIME_H * CSS / H_PX
        while self.x(t) < x1:
            if self.x(t) >= x0 and (t // 3600) % hstep == 0:
                ax.axvline(self.x(t), color=self.th["grid"], lw=1 * PT, zorder=0)
                d = utc(t)
                txt = d.strftime("%-d %b") if d.hour == 0 and d.minute == 0 else d.strftime("%H:%M")
                xf = self._fig_x(self.x(t))
                if 24 * CSS / W_PX < xf < sep_x - 24 * CSS / W_PX:
                    fig.text(xf, th / 2, txt, color=self.th["axis"], fontsize=AXIS_FS * PT,
                             va="center", ha="center",
                             weight="bold" if d.hour == 0 else "normal")
            t += 3600
        # scale separators
        fig.add_artist(plt.Line2D([sep_x, sep_x], [0, 1], color=self.th["sep"], lw=1 * PT))
        fig.add_artist(plt.Line2D([0, 1], [th, th], color=self.th["sep"], lw=1 * PT))
        ch = 1 - CAP_H * CSS / H_PX
        fig.add_artist(plt.Line2D([0, 1], [ch, ch], color=self.th["sep"], lw=1 * PT))
        fig.text(1 - SCALE_W * CSS / W_PX / 2, th / 2, "UTC", color=self.th["axis"],
                 fontsize=AXIS_FS * PT, va="center", ha="center")

    def _fig_y(self, p):
        ax = self.ax
        y0, y1 = ax.get_ylim()
        b = ax.get_position()
        return b.y0 + (p - y0) / (y1 - y0) * b.height

    def _fig_x(self, xv):
        ax = self.ax
        x0, x1 = ax.get_xlim()
        b = ax.get_position()
        return b.x0 + (xv - x0) / (x1 - x0) * b.width

    def _candles(self, ax, bars):
        bw = 0.7
        for i, (k, (o, h, l, c, _)) in enumerate(bars):
            o, h, l, c = float(o), float(h), float(l), float(c)
            col = UP if c >= o else DOWN
            ax.plot([i, i], [l, h], color=col, lw=1 * PT, zorder=2, solid_capstyle="butt")
            ax.add_patch(Rectangle((i - bw / 2, min(o, c)), bw, max(abs(c - o), 1e-9),
                                   facecolor=col, edgecolor=col, lw=0.5 * PT, zorder=2))

    # -------------------------------------------------------------------
    def drawn_lattices(self):
        lats = [l for l in self.eng.lattices.values() if l.pub_time is not None and l.pub_time <= self.asof]
        lats.sort(key=lambda l: l.day0)
        return lats[-2:]                       # [Display] lattice days drawn = 2

    def _lattices(self, ax):
        drawn = self.drawn_lattices()
        for lat in drawn:
            latest = lat is drawn[-1]          # r1: node labels on the latest anchor day only
            xa, xb = self.x(lat.pub_time), self.x(lat.end_time)
            for nd, lo, hi, lev in lat.bands:
                col, w, sty, tr = LAT_STYLE[nd.h]
                if self.light and nd.h in LIGHT_TRANSP:
                    tr = LIGHT_TRANSP[nd.h]
                if not lat.eligible:
                    col, sty, tr = INELIG
                y = float(lev)
                ax.plot([xa, xb], [y, y], color=col, alpha=alpha(tr), lw=w * PT, zorder=4,
                        **dashes(sty, 1))
                if latest and nd.h <= LABEL_MAX_H:
                    ltr = 0                          # transp capped at 0 for h<=2
                    self._end_label(ax, xb, y, nd.label, col, alpha(ltr), "node")
            for name, val in (("PDH", lat.H), ("PDL", lat.L)):
                col, w, sty, tr = PDHL
                y = float(val)
                ax.plot([xa, xb], [y, y], color=col, alpha=alpha(tr), lw=w * PT, zorder=4,
                        **dashes(sty, 1))
                if latest:                         # r2: PDH/PDL labels on the latest day only
                    self._end_label(ax, xb, y, name, col, 1.0, "pdhl")

    def _end_label(self, ax, xb, y, text, col, a, kind):
        trans = offset_copy(ax.transData, fig=self.fig, x=3 * PT, y=0, units="points")
        art = ax.text(xb, y, text, color=col, alpha=a, fontsize=TINY_FS * PT, va="center",
                      ha="left", transform=trans, zorder=6, clip_on=True)
        self.labels.append((art, kind))

    # -------------------------------------------------------------------
    def _events(self, ax):
        eng = self.eng
        # r2: geometry for one pending event only (nearest level to the last close, ties -> newest)
        pend = [e for e in eng.events if e.t_min < self.asof and e.status_at(self.asof) == "PENDING"]
        geom = set()
        if self.geom_mode == "All":
            geom = set(map(id, pend))
        elif self.geom_mode == "Nearest" and pend:
            last = float(eng.close_at[max(t for t in eng.close_at if t <= self.asof)])
            best = min(enumerate(pend), key=lambda ie: (abs(ie[1].level - last), -ie[0]))[1]
            geom = {id(best)}
        self.pending_at_asof = len(pend)
        self.geoms_drawn = 0
        for ev in eng.events:
            if not (self.t_from <= ev.t_min < self.t_to) or ev.t_min >= self.asof:
                continue
            st = ev.status_at(self.asof)
            show_geom = id(ev) in geom or ev is self.focus
            self.geoms_drawn += show_geom
            xe = self.x(ev.bar * M15)
            if show_geom:
                xh = self.x((ev.bar + W_BARS - 1) * M15)
                sgn = 1 if ev.side == "below" else -1
                lev, atr = ev.level, ev.atr
                col, tr = BOX_FILL
                ax.add_patch(Rectangle((xe, min(lev, lev + sgn * 0.25 * atr)), xh - xe, 0.25 * atr,
                                       facecolor=col, alpha=alpha(tr), edgecolor="none", lw=0, zorder=3))
                c, w, s = REJ_LINE
                ax.plot([xe, xh], [lev - sgn * atr] * 2, color=c, lw=w * PT, zorder=4, **dashes(s, 1))
                c, w, s = BRK_LINE
                ax.plot([xe, xh], [lev + sgn * atr] * 2, color=c, lw=w * PT, zorder=4, **dashes(s, 1))
            col, tr = MARKER[st]
            mk = "v" if ev.side == "below" else "^"
            ax.plot([xe], [ev.level], marker=mk, color=col, alpha=alpha(tr), markersize=TRI_PX * PT,
                    markeredgewidth=0, linestyle="none", zorder=7)
            if self.tooltips and ev is self.focus:
                self._tooltip(ax, xe, ev.level, ev.tooltip(self.asof), ev.side)

    def _tooltip(self, ax, x, y, text, side):
        # place the box on the rejection side, away from the tolerance box / break line
        dy = -26 if side == "below" else 26
        ax.annotate(text, (x, y), xytext=(14 * PT, dy * PT), textcoords="offset points",
                    color=self.th["fg"], fontsize=TINY_FS * PT, va="center", ha="left", zorder=9,
                    bbox=dict(boxstyle="round,pad=0.35", fc=self.th["tip_bg"], ec=self.th["tip_ec"], lw=0.5 * PT),
                    arrowprops=dict(arrowstyle="-", color=self.th["tip_ec"], lw=0.5 * PT))

    # -------------------------------------------------------------------
    def _header(self, fig):
        cap = 1 - CAP_H * CSS / H_PX
        if self.title_note:          # mock caption, outside the chart area
            fig.text(8 * CSS / W_PX, 1 - CAP_H * CSS / H_PX / 2, "MOCK (not TradingView) · " + self.title_note,
                     color="#787B86", fontsize=10 * PT, va="center", ha="left")
        fig.text(8 * CSS / W_PX, cap - 8 * CSS / H_PX, "BTCUSDC · 15 · BINANCE", color=self.th["fg"],
                 fontsize=13 * PT, va="top", ha="left")

    def _panel(self, fig, ax):
        rows = self.eng.panel_at(self.panel_at)
        self.panel_rows = rows
        r = fig.canvas.get_renderer()
        pad_x, pad_y = 4 * CSS, 2 * CSS              # device px
        fs = TINY_FS * PT
        probe = [[fig.text(0, 0, c, fontsize=fs) for c in row] for row in rows]
        widths = [0, 0]
        hmax = 0
        for row in probe:
            for j, t in enumerate(row):
                bb = t.get_window_extent(r)
                widths[j] = max(widths[j], bb.width)
                hmax = max(hmax, bb.height)
                t.remove()
        cw = [w + 2 * pad_x for w in widths]
        rh = hmax + 2 * pad_y
        axb = ax.get_window_extent(r)
        left = axb.x0 + 4 * CSS                       # position.bottom_left
        bottom = axb.y0 + 4 * CSS
        right = left + sum(cw)
        top = bottom + len(rows) * rh
        fig.add_artist(Rectangle((left / W_PX, bottom / H_PX), (right - left) / W_PX, (top - bottom) / H_PX,
                                 transform=fig.transFigure, facecolor=self.th["bg"],
                                 alpha=alpha(PANEL_BG_TRANSP), edgecolor="none", lw=0, zorder=10))
        for i, row in enumerate(rows):
            yc = top - (i + 0.5) * rh
            xc = left
            for j in range(2):
                txt = row[j] if j < len(row) else ""
                fig.text((xc + pad_x) / W_PX, yc / H_PX, txt, color=self.th["fg"],
                         fontsize=fs, va="center", ha="left", zorder=11)   # left-aligned
                xc += cw[j]
        self.panel_box = (left, bottom, right, top)

    # -------------------------------------------------------------------
    def _label_overlap(self, fig):
        r = fig.canvas.get_renderer()
        axb = self.ax.get_window_extent(r)
        boxes = []
        for art, kind in self.labels:
            bb = art.get_window_extent(r)
            if bb.x1 < axb.x0 or bb.x0 > axb.x1 or bb.y1 < axb.y0 or bb.y0 > axb.y1:
                continue
            boxes.append((bb, art.get_text(), kind))
        self.visible_labels = boxes
        worst = 0.0
        worst_pair = None
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                a, b = boxes[i][0], boxes[j][0]
                ow = min(a.x1, b.x1) - max(a.x0, b.x0)
                oh = min(a.y1, b.y1) - max(a.y0, b.y0)
                if ow > 0 and oh > 0 and oh > worst:
                    worst, worst_pair = oh, (boxes[i][1], boxes[j][1])
        self.worst_pair = worst_pair
        # labels partly covered by the panel table (top-right)
        self.panel_hits = []
        if getattr(self, "panel_box", None):
            l, b, rr, t = self.panel_box
            for bb, txt, kind in boxes:
                if bb.x1 > l and bb.x0 < rr and bb.y1 > b and bb.y0 < t:
                    self.panel_hits.append(txt)
        # candles (wick extent) partly covered by the panel table
        self.candles_under_panel = 0
        if getattr(self, "panel_box", None):
            l, b, rr, t = self.panel_box
            for i, (k, (o, h, lo, c, _)) in enumerate(self._bars):
                (xa, ya), (xb, yb) = self.ax.transData.transform([(i - 0.35, float(lo)), (i + 0.35, float(h))])
                if xb > l and xa < rr and yb > b and ya < t:
                    self.candles_under_panel += 1
        # vertical spacing (device px) between adjacent visible labels sharing an x anchor
        gaps = []
        bykey = {}
        for bb, txt, kind in boxes:
            bykey.setdefault(round(bb.x0), []).append((bb.y0 + bb.y1) / 2)
        for ys in bykey.values():
            ys.sort()
            gaps += [b2 - b1 for b1, b2 in zip(ys, ys[1:])]
        self.min_label_spacing = min(gaps) if gaps else None
        self.label_height = max((bb.height for bb, _, _ in boxes), default=0)
        return worst


W_BARS = 12
