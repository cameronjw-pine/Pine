#!/usr/bin/env python3
"""Analysis skeleton for the Harmonic Time Circle research ledger.

Implements the first two tests of the validation program (docs/VALIDATION.md)
over JSON-lines records captured from the indicator's alert() webhook:

  1. comma-residual clustering — do |chi| residuals concentrate at the
     registered low-order fractions {0, 1/12, 1/6, 1/4, 1/2} more than a
     circular-shuffle null?
  2. node-vs-decoy concentration — are events closer to registered nodes
     than to matched random pseudo-node sets of identical size?

Usage:
    python analyze_ledger.py ledger.jsonl [--n-null 2000] [--seed 7]

Records must conform to research/ledger_schema.json. This is deliberately a
skeleton: outcome-conditional tests (MFE/MAE, reversal vs continuation) plug
in once the collector appends outcome fields.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from dataclasses import dataclass

PHI = (1 + 5 ** 0.5) / 2
COMMA_H = 24 * math.log2(3 ** 12 / 2 ** 19)          # 0.4692002 h
FRACTIONS = [0.0, 1 / 12, 1 / 6, 1 / 4, 1 / 2]
FRACTION_TOL = 1 / 48

# registered node families (NY hours) — keep in sync with the indicator
CLOCK = [float(h) for h in range(0, 24, 2)]
PYTH = [24 * math.log2(r) % 24 for r in
        (9 / 8, 81 / 64, 4 / 3, 1024 / 729, 2 ** 0.5, 729 / 512,
         3 / 2, 128 / 81, 16 / 9, 243 / 128)]
GOLD = [24 * (2 - PHI), 24 * (PHI - 1)]
ALL_NODES = sorted(CLOCK + PYTH + GOLD)


def circ_dist(a: float, b: float) -> float:
    d = abs(a - b) % 24
    return min(d, 24 - d)


def nearest_node_dist(t: float, nodes: list[float]) -> float:
    return min(circ_dist(t, n) for n in nodes)


def chi_is_clustered(chi: float) -> bool:
    return any(abs(abs(chi) - f) <= FRACTION_TOL for f in FRACTIONS)


@dataclass
class Event:
    tod_hours: float
    chi: float | None


def load(path: str) -> list[Event]:
    events: list[Event] = []
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            hh, mm, ss = (int(x) for x in rec["ny_tod"].split(":"))
            events.append(Event(hh + mm / 60 + ss / 3600, rec.get("chi")))
    return events


def test_chi_clustering(events: list[Event], n_null: int, rng: random.Random) -> None:
    chis = [e.chi for e in events if e.chi is not None]
    if not chis:
        print("chi clustering: no chi values in ledger, skipped")
        return
    observed = sum(chi_is_clustered(c) for c in chis) / len(chis)
    # null: circularly rotate event times, recompute chi vs nearest harmonic node
    harmonic = sorted(PYTH + GOLD)
    exceed = 0
    for _ in range(n_null):
        shift = rng.uniform(0, 24)
        rate = 0
        for e in events:
            t = (e.tod_hours + shift) % 24
            node = min(harmonic, key=lambda n: circ_dist(t, n))
            raw = t - node
            chi = (raw - 24 * round(raw / 24)) / COMMA_H
            rate += chi_is_clustered(chi)
        if rate / len(events) >= observed:
            exceed += 1
    p = (exceed + 1) / (n_null + 1)
    print(f"chi clustering: observed rate {observed:.3f} over {len(chis)} events, "
          f"circular-rotation p = {p:.4f}")


def test_node_concentration(events: list[Event], n_null: int, rng: random.Random) -> None:
    if not events:
        print("node concentration: empty ledger, skipped")
        return
    observed = sum(nearest_node_dist(e.tod_hours, ALL_NODES) for e in events) / len(events)
    exceed = 0
    k = len(ALL_NODES)
    for _ in range(n_null):
        decoys = sorted(rng.uniform(0, 24) for _ in range(k))
        mean_d = sum(nearest_node_dist(e.tod_hours, decoys) for e in events) / len(events)
        if mean_d <= observed:
            exceed += 1
    p = (exceed + 1) / (n_null + 1)
    print(f"node concentration: mean distance {observed * 60:.2f} min to registered nodes, "
          f"matched-decoy p = {p:.4f}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("ledger", help="JSON-lines file of htc-ledger-1 records")
    ap.add_argument("--n-null", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    events = load(args.ledger)
    print(f"loaded {len(events)} ledger events")
    test_chi_clustering(events, args.n_null, rng)
    test_node_concentration(events, args.n_null, rng)
    print("note: hypothesis-generating only — confirmation requires untouched "
          "out-of-sample data (docs/VALIDATION.md).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
