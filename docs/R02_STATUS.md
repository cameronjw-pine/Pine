# R02 Indicator — Running List

Authority alongside `docs/R02_PLAN.md`. Newest first within each section.

## Open
- Build `indicators/R02OddsLattice.pine` (Agent A).
- Pine build (Agent A): told about spec r1 mid-build.
- User compiles the Pine in TradingView (no compiler in build env).

## Agreed
- 2026-11-08 · Spec r2 after mock round 2: fast moves stacked 6 pending geometries → draw geometry for the nearest pending event only (All/Off selectable); h3/h4 more opaque on light theme; PDH/PDL labels on the latest day only. Kept pending amber and INDET faint.
- 2026-11-08 · Spec r1 after mock round 1: marker colours moved off the candle colours (REJECT blue, BREAK faded magenta, pending amber), panel bottom-left and readable on both themes, labels on the latest day only, ineligible transp 70. Kept the h≤2 label default despite ≤3.5px overlap on narrow ranges.
- 2026-11-07 · Premise: hypothetical world where R02 G/N/A all came back
  material; draw only the 41-node {2,3} family; no control, decoys,
  scoreboard, ledger or testing.
- 2026-11-07 · Reproduce the R02 event contract exactly (A1 anchor, M1 path,
  freshness 20, ATR14 frozen, W=12, REJECT/BREAK thresholds, E13 gate).
- 2026-11-07 · Ineligible days are dimmed, not hidden.
- 2026-11-07 · No buy/sell output; fresh-touch markers + pending rejection
  geometry + alerts.
- 2026-11-07 · M15 chart with M1 intrabars; realtime reprocesses completed
  minutes so touches show within about a minute.

## Done
- 2026-11-08 · Mock renderer `research/r02_mock/` accepted after 3 review rounds (8 iterations): visual spec r2 confirmed on dark and light, real Binance BTCUSDC 2025-06-01..08 (29.9 fresh touches/day, 7.9% REJECT). Known gaps: gap/censor/ATR-reset and real hygiene-ineligible paths not exercised by this data.
