# R02 {2,3} Odds Lattice — Pine Script Indicator Plan

Authority file. Decisions here are fixed; agents build exactly this. Running
progress lives in `docs/R02_STATUS.md`.

## 0 · Premise (decided with the user, 2026-11-07)

Hypothetical world: R02's three primary slots (G, N, A) all came back
SUPPORTED at the material margin. Therefore the complete 41-node {2,3}
odds lattice on the prior UTC day's range is treated as a validated reaction
map **under R02's exact event contract**. Consequences:

- No {2,5} control, no decoys, no LAT23 proxy, no scoreboard, no ledger, no
  testing of the hypothesis. Only the O23-H4 family is drawn.
- Fidelity to the event contract still matters: "proven" was proven for that
  anchor / touch / freshness / outcome definition, so the indicator reproduces
  it rather than inventing a looser one.
- The indicator is a level map plus fresh-touch setups with their rejection
  geometry. It never prints buy/sell.

Sources: ULF R02 Design Protocol v0.1, Development Report v0.2, Validation
Report v0.3 (user uploads, not in repo).

## 1 · Geometry (exact)

- Nodes: all integer (a,b) with |a|+|b| ≤ 4; odds o = 2^a·3^b; f = o/(1+o).
  41 distinct nodes, f ∈ [1/82, 81/82]. Height h = |a|+|b| (0..4).
- Reduced odds label: num = 2^max(a,0)·3^max(b,0), den = 2^max(−a,0)·3^max(−b,0)
  (automatically coprime). Label text `num:den` (e.g. `3:2`, `1:1`, `2:9`).
  f = num/(num+den).
- Anchor A1: L, H = low/high of the preceding complete UTC day, computed from
  its 1440 M1 bars. Level price = L + f·(H−L). Band = inclusive
  [L+(f−ε)(H−L), L+(f+ε)(H−L)], ε = 1/4100. Unrounded, unclipped.
- Sanity: min adjacent gap 3/700 ≈ 0.00429 of range, max 1/14 ≈ 0.0714.

## 2 · Event contract (reproduce exactly)

Chart: 15-minute. Source path: M1 bars via `request.security_lower_tf`.

1. **Day eligibility** (all must hold, else the day is INELIGIBLE — levels
   drawn dimmed, no events):
   - Prior UTC day has all 1440 M1 bars (input to disable for non-24/7 symbols).
   - H > L.
   - Tick gate: `syminfo.mintick / (H−L) ≤ 1/41000`.
   - Hygiene gate (Pine approximation of thesis E13, input toggle, default on):
     residual r_t = ln(mid_t) − ln(mid_{t−1}) for consecutive minutes,
     mid = (high+low)/2. Keep a rolling window of the latest ≤1440 non-flagged
     residuals. Flag r_t if the window holds ≥720 values and
     |r_t| > 10 × sample SD(window). Flagged residuals never enter the window.
     Process chronologically, never revisit. The day is ineligible if any
     residual whose later minute lies in that day, or the residual from
     23:59 into the following 00:00 minute, is flagged.
     A non-consecutive minute (gap) breaks the residual chain (no residual).
2. **Publication**: first M1 open at or after 00:01 UTC of the evaluation
   day. No entries before it. At publication each band's inside/outside
   state is initialised from that first observed price with no touch emitted.
   Freshness history persists across days by band identity (the fraction).
   Pending events keep their original level, range and ATR across midnight.
3. **M1 path**: O→L→H→C when C ≥ O, else O→H→L→C. Continuous legs; a leg
   that crosses a band intersects it. Between minutes there is no
   interpolation: if the previous close is outside and this open is inside,
   that is an entry at the open. Jumping over a whole band across a gap is not
   an entry.
4. **Entry**: transition outside→inside of the inclusive band. Entry
   position = first point of the path inside the band. Approach side = side of
   the pre-entry price (below if < band low, above if > band high).
5. **Freshness**: an entry qualifies only if that band had no physical entry
   in the containing M15 bar or the prior 20 M15 bars, and tracking has been
   known for at least those 20 completed bars. At most one qualifying event
   per band per M15 bar. Every physical entry, including suppressed ones,
   updates the band's last-entry clock.
6. **ATR**: Wilder/RMA ATR14 on M15, seeded with the mean of the first 14
   true ranges. At entry use the last completed M15 bar's ATR, frozen for the
   event. Entries during the first M1 of each M15 bar are not eligible
   (ATR knowledge pause); physical tracking continues.
7. **Gaps/recovery**: an M15 bar with fewer than 15 M1 bars is a source gap.
   Freshness becomes unknown for all bands → require 20 fully observed M15
   bars of renewed tracking. ATR resets: first complete recovered bar uses
   TR = H−L, reseed from 14 consecutive complete bars. Pending events whose
   horizon contains a gap become CENSORED. Script start counts as a recovery.
8. **Outcome**: horizon from the exact entry position to the close of M15 bar
   t+11 (W=12, containing bar is t). From below: π = max(P−level,0)/ATR,
   R = max(level−P,0)/ATR over the post-entry path; from above, mirrored.
   Level = node centre price.
   - BREAK when π ≥ 1.0 (final as soon as it happens).
   - REJECT when, at horizon end, π ≤ 0.25 AND R ≥ 1.0.
   - INDETERMINATE otherwise at horizon end.

## 3 · Visual spec (exact)

Colours chosen to read on both TradingView dark and light themes.

| Element | Spec |
|---|---|
| Lattice line, h=0 (1:1) | `#E8A317`, width 2, solid, transp 0 |
| h=1 | `#E8A317`, width 1, solid, transp 0 |
| h=2 | `#E8A317`, width 1, solid, transp 40 |
| h=3 | `#E8A317`, width 1, dotted, transp 65 on dark backgrounds, 45 on light |
| h=4 | `#E8A317`, width 1, dotted, transp 80 on dark backgrounds, 60 on light. Light = luminance of `chart.bg_color` (0.299r+0.587g+0.114b) > 128 |
| Line extent | from publication time to 24:00 UTC of the evaluation day (projects into the future for the current day); `xloc.bar_time` |
| PDH / PDL | `#808080`, width 1, dashed, same extent, labels `PDH` / `PDL` on the latest anchor day only |
| Ineligible day | every lattice line `#9E9E9E` transp 70 dotted; panel shows reason |
| Node labels | latest anchor day only (older drawn days are unlabelled), at the line's right end, `label.style_label_left`, no background, text colour = line colour (transp capped at 0 for h≤2), `size.tiny`, text `num:den`. Default shown for h ≤ 2 (13 labels) |
| Touch marker | `label` at entry bar, y = level, `size.tiny`. From below → `style_triangledown`; from above → `style_triangleup` (points in the rejection direction) |
| Marker colour | Must never equal candle colours. PENDING `#E8A317` transp 0; REJECT `#2962FF` transp 0; BREAK `#E040FB` transp 50; INDETERMINATE `#787B86` transp 50; CENSORED `#787B86` transp 80 |
| Marker tooltip | `3:2 · from below · ATR 412.50 · REJECT (π 0.12, R 1.43)` (state and π/R so far while pending) |
| Pending geometry (only while PENDING, deleted on resolution; drawn for **one** event only: the pending event whose level is nearest the last close, ties → newest; input mode Nearest/All/Off, default Nearest) | tolerance box from level to level ± 0.25·ATR on the penetration side, entry bar → entry bar+11, fill `#E8A317` transp 85, no border; reject-target line at level ∓ 1·ATR, dashed `#2962FF` width 1; break line at level ± 1·ATR, dotted `#E040FB` width 1; both span the horizon |
| Panel | `table` `position.bottom_left`, 2 columns, `size.tiny`, `text_color=chart.fg_color`, `bgcolor=color.new(chart.bg_color, 20)`, no border, left-aligned text. Rows: `R02 {2,3} lattice` · Anchor `YYYY-MM-DD  L … H …` · Status `ELIGIBLE` or `INELIGIBLE: hygiene/incomplete/tick/range` · `ATR15 …` · `Above 4:3 @ 98,432.10 (+0.31 ATR)` · `Below …` · `Pending n` · a one-line note `Outside R02 population` when the symbol is not BINANCE:BTCUSDC, or `Events need 15m chart` on any other timeframe |

Inputs (group names in brackets): [Display] label max height 0–4 (2);
lattice days drawn 1–5 (2); pending geometry Nearest/All/Off (Nearest); show resolved markers
(on); show panel (on). [Contract] hygiene gate (on); require complete prior
day (on). [Alerts] fresh-touch alerts (on).

Timeframe behaviour: lattice draws on any intraday timeframe ≤ 15m; the
touch engine runs only on the 15m chart.

Revision r1 (2026-11-08, after mock round 1): marker palette moved off the candle colours, faded BREAK/INDET, panel restyled and moved bottom-left, labels on latest day only, ineligible transp 85→70.
Revision r2 (2026-11-08, after mock round 2): pending geometry for the nearest pending event only, theme-aware h3/h4 transparency, PDH/PDL labels on latest day only.

## 4 · Engineering rules for the Pine file

- Pine v6, single self-contained file `indicators/R02OddsLattice.pine`,
  `overlay=true`, sensible `max_lines_count/max_boxes_count/max_labels_count`
  (500). No `request.security` with `lookahead_on` on unconfirmed data.
- Realtime: process only completed M1 intrabars. Because `var` state rolls
  back on each realtime tick, reprocess the completed intrabars of the current
  M15 bar from the bar-open state on each tick, so touches show within about a
  minute of happening. Confirm how drawing objects behave under rollback and
  make sure duplicates never accumulate.
- Alerts: `alert()` on each new qualifying fresh touch, deduplicated by event
  key (band, M1 time) with `varip`, so a touch never fires twice. Message:
  `R02 fresh touch 3:2 @ 98,432.10 from below · reject target 98,020.00 · break 98,844.20 · horizon ends 14:45 UTC`.
- Drawing caps: delete the oldest lattice day when more than the input count is
  drawn; keep at most 300 markers (FIFO).
- Header comment states the hypothetical premise in one sentence.

## 5 · Mock renderer (visual review substitute)

There is no TradingView or Pine compiler in the build environment, so a Python
mirror under `research/r02_mock/` renders the same geometry and visual spec on
real Binance BTCUSDC M1/M15 data (synthetic fallback if the network blocks
it). It exists only so the design can be judged by eye; it is not a test of
R02.

## 6 · Agents

| Agent | Owns | Never touches |
|---|---|---|
| A · Pine | `indicators/R02OddsLattice.pine` | everything else |
| B · Mock | `research/r02_mock/**` | everything else |

Hard rules for every agent: touch only owned files; never rename or delete
other files; never commit or push; never invent content beyond this plan (if
something is ambiguous, pick the most literal reading, note it, and list it in
the report); write your own exact-edit plan to your scratch file before
building.

### Fixed report format (every agent, every report)

```
## Report — <agent> — <round n>
Built: <one paragraph>
Files: <paths written>
Scratch plan: <path>
Ambiguities resolved: <bullets: spec item → choice made>
Deviations from plan: <bullets or "none">
Screenshots: <absolute paths>
Checks: <JSON block>
Not verified: <bullets>
```
