# Empirical Validation Program

The geometry identifies candidate WHEN zones; whether they matter is an
empirical question. This document operationalizes §12 of the paper for this
framework. **If the harmonic/golden nodes do not outperform simple clock
benchmarks and matched decoys, the framework is a descriptive visualization,
not an edge.**

## Evidential discipline

Three statement levels, never conflated:

1. **Exact mathematics** — identities (see [MATH_SPEC.md](MATH_SPEC.md)).
2. **Observed timing correspondence** — an ICT boundary lies near a node.
3. **Market hypothesis** — proximity changes event probability/character.

Progression: geometry → registered timing comparison → null model →
out-of-sample market test. Register all node families and windows **before**
testing; report point-to-boundary errors and decoy coverage.

## Primary tests

| Test | Question |
|---|---|
| Golden-boundary | Are events concentrated near 09:10:02 / 14:49:58 vs matched nearby decoys? |
| Noon tritone/comma | Does the 28m09s noon comma envelope show excess reversal / continuation / displacement? |
| Clock-vs-pure | Does 09:57:39 outperform 10:00, and 14:02:21 outperform 14:00, with realistic execution windows? |
| 20:00 residual | Does the 16/9 node or the 20:00 clock boundary better explain the CBDR→Asian transition? |
| Duration-family | Do realized effective windows fit 120/60/30/20, 113.31/56.66/30.90/18.89, or neither? |
| Comma-residual | Do χ residuals cluster at low-order fractions more than shuffled events? |

## Null models

- Circular time rotation within session/day.
- Matched random pseudo-nodes (same count, same window widths).
- Ordinary hour/half-hour boundaries as the simpler benchmark.
- Alternative irrational decoys (e.g. √3, e-based phases) to control for
  post-hoc attraction to unusual constants.
- Block bootstrap by trading session to preserve intraday dependence.

## Outcome variables

Liquidity sweep frequency, displacement probability, MSS occurrence, FVG
creation/reaction, reversal probability, continuation probability, realized
range expansion, post-node MFE/MAE. Directional claims must be conditioned
on price state, never phase alone.

## Data pipeline

1. Enable **research ledger** in the indicator inputs.
2. Create a TradingView alert on the script with *"Any alert() function
   call"*, webhook pointed at your collector.
3. Each qualified confirmed bar emits one JSON record conforming to
   [`research/ledger_schema.json`](../research/ledger_schema.json).
4. Analyze accumulated records with
   [`research/analyze_ledger.py`](../research/analyze_ledger.py)
   (χ-clustering test skeleton + node-vs-decoy concentration test).

Outcome fields (MFE/MAE, subsequent structure) are appended by the collector
or in post-processing — Pine cannot know the future without repainting.

## Promotion criteria

Visual prominence must track measured out-of-sample effect size:

- A node family earns default-on + high weight only after surviving decoy
  and null comparisons out-of-sample.
- If only some nodes survive, **retain only those nodes** and discard the
  rest from the default registry.
- Era-dependent windows (kill zones) stay default-off until verified against
  primary ICT source material and versioned by era.

## Known risks (paper §13)

Multiple-comparisons risk, timing-source ambiguity, window flexibility,
DST/session handling, mechanism-vs-description confusion, directionality
leakage, and data snooping. The current node set is hypothesis-generating;
confirmation requires untouched out-of-sample data.
