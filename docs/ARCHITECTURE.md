# Indicator Architecture

The framework implements the three-layer design from §11 of the research
paper. The guiding principle: **hide the mathematics, expose only
prospective, actionable temporal information — and never a directional
signal.**

```
┌──────────────────────────────────────────────────────────────────┐
│ 1 · HIDDEN ENGINE                                                │
│   NY phase mapping (DST-safe) → node registry → circular         │
│   distances → family kernels → S_T, χ, confluence, nesting       │
├──────────────────────────────────────────────────────────────────┤
│ 2 · VISIBLE LAYER                                                │
│   future-time rail · projected node lines · diagnostic panel ·   │
│   narrow high-salience background bands · node-hit markers       │
├──────────────────────────────────────────────────────────────────┤
│ 3 · RESEARCH LEDGER                                              │
│   alert() JSON records → webhook → research/ analysis tooling    │
└──────────────────────────────────────────────────────────────────┘
```

## Module map

| Component | File | Role |
|---|---|---|
| Main indicator | `indicators/HarmonicTimeCircle.pine` | Full three-layer implementation, self-contained |
| Math library | `libraries/HarmonicTime.pine` | Pure exported primitives for reuse in other scripts/strategies |
| Ledger schema | `research/ledger_schema.json` | Contract for webhook-captured event records |
| Ledger analysis | `research/analyze_ledger.py` | Skeleton implementing the paper's validation tests |

The main indicator intentionally does **not** import the library (published
library imports require a TradingView publication step); it inlines the same
formulas. Once `HarmonicTime` is published under your account, downstream
strategies should import it rather than copying math.

## Hidden engine

1. **Phase mapping** — all time math uses the IANA zone `America/New_York`
   via `hour/minute/second(time, tz)`, so daylight-saving transitions are
   handled by the runtime, never by offsets (paper §13 requirement).
2. **Node registry** — built once at `barstate.isfirst` as an
   `array<Node>`: clock lattice (even hours), Pythagorean lattice
   (`T(r) = 24·log2(r)`), golden pair (`24φ⁻²`, `24φ⁻¹`). The tritone is
   pinned to exactly `12.0` rather than computed, preserving the identity.
3. **Windows registry** — registered ICT windows are parsed from
   `HHMM-HHMM` config strings into an `array<Window>`, tagged by kind
   (MACRO / SB / RANGE / KZ). Kill zones ship disabled by default because
   they are era-dependent (paper §13, "timing-source ambiguity"); the fixed
   macro/range set ships enabled. Windows contribute **nesting depth N**,
   never salience — keeping the empirical layer separate from node math.
4. **Per-bar state** — signed circular offsets, per-family nearest
   distances, Gaussian kernels `K_f`, weight-normalized salience
   `S_T ∈ [0,1]`, comma residual `χ` (vs nearest *harmonic* node only),
   χ-class against the registered fractions, confluence order, and forward
   ETA to the next node.

## Visible layer

- **Future-time rail** (top-center table): the next 2–6 nodes with family
  badge, exact NY time, and countdown — the paper's
  "`P4 09:57 → TT 12:00 → P5 14:02 → golden 14:50 → 20:00`" rail.
- **Projected node lines**: vertical lines + tiny labels at upcoming node
  timestamps within a configurable look-ahead horizon.
- **Diagnostic panel** (top-right): state (QUIET / SALIENT / QUALIFIED),
  nearest node + signed offset, S_T, χ + class, active windows, confluence,
  displacement reading.
- **Background bands**: drawn only when `S_T ≥ threshold` *and* (optionally)
  inside an active registered window — "narrow bands only around active
  high-salience windows", never a forest of paint.
- **Descartes panel** (optional): the `D_n = 24/[φ³(n²+2)]` duration
  hierarchy as inspection horizons (113/57/31/19/13/9 min).

## Repaint policy

- Node times are deterministic constants of the NY day; projections drawn on
  the last bar are pure look-ahead of a fixed schedule — nothing about
  history is ever redrawn.
- Historical node-hit markers derive only from bar-open time-of-day
  crossings (`nyH[1] → nyH`), which are immutable.
- No `request.security`, no `lookahead`, no dependence on unconfirmed values
  for the ledger: ledger records emit at `barstate.isconfirmed` only.
- On non-intraday timeframes the engine idles and says so, rather than
  rendering meaningless intraday geometry.

## Price-evidence gate

The paper's non-negotiable rule is enforced structurally: the strongest
state the indicator can emit is **QUALIFIED**, defined as
`S_T ≥ threshold` ∧ (window active, if required) ∧ displacement
(`|body| ≥ k·ATR`). That is a *salience + evidence coincidence*, not an
entry. Liquidity and market-structure terms (L, S in the paper's Q-score)
are deliberately out of scope — attach them downstream.

## Performance budget

- Node loop: ~24 nodes × 1 pass per bar, O(1) memory.
- Drawings: rebuilt only on the last bar; bounded by `max_lines_count` /
  `max_labels_count`.
- Tables: three fixed-size tables, cleared and repopulated on the last bar.

## Extension points

- **Era-versioned window sets**: swap the config strings per ICT era; keep
  each registered set under version control before testing (paper §12
  preregistration discipline).
- **Confluence with boundary nodes**: window *boundaries* (e.g. 20:00) could
  be added as a fourth node family once their standalone value is shown
  against the 16/9 node (the "20:00 residual test").
- **Strategy wrapper**: import `HarmonicTime` into a strategy that supplies
  the L/S/D terms and consumes S_T/χ/N as regime inputs.
