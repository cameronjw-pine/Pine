# Mathematical Specification

Formal definitions behind the Harmonic Time Circle engine. Everything in this
file is **exact mathematics** (level 1 in the paper's evidential hierarchy) —
identities that follow from definitions. Empirical claims live in
[VALIDATION.md](VALIDATION.md).

## 1. The temporal octave

New York local clock time `t` (hours, DST-resolved via `America/New_York`) is
mapped onto a daily circle:

```
p = t/24 mod 1          normalized phase
θ = 360·p               degrees   (1 h = 15°)
c = 1200·p              cents     (1 h = 50 c)
```

One daily cycle is one musical octave: `24 h = 360° = 1200 cents`.
Even hours form a 12-step subgroup equivalent to 12-tone equal temperament
(2 h = 100 c).

## 2. Node families

### 2.1 Clock lattice (equal temperament)

Even hours 00:00, 02:00, …, 22:00. Notable equal-tempered positions:
10:00 = 500 c (fourth), 12:00 = 600 c (tritone), 14:00 = 700 c (fifth).

### 2.2 Pure Pythagorean lattice

A frequency ratio `r` maps to `T(r) = 24·log2(r) mod 24`:

| Interval | Ratio | NY time | Cents |
|---|---|---|---|
| Unison | 1/1 | 00:00:00 | 0.000 |
| Major tone | 9/8 | 04:04:42 | 203.910 |
| Pyth M3 | 81/64 | 08:09:23 | 407.820 |
| Perfect fourth | 4/3 | 09:57:39 | 498.045 |
| Pyth d5 | 1024/729 | 11:45:55 | 588.270 |
| Symmetric tritone | √2 | 12:00:00 | 600.000 |
| Pyth A4 | 729/512 | 12:14:05 | 611.730 |
| Perfect fifth | 3/2 | 14:02:21 | 701.955 |
| Pyth m6 | 128/81 | 15:50:37 | 792.180 |
| Pyth m7 | 16/9 | 19:55:18 | 996.090 |
| Pyth M7 | 243/128 | 22:11:44 | 1109.775 |

### 2.3 Golden / Fibonacci pair

```
φ = (1+√5)/2,   φ⁻² + φ⁻¹ = 1
24·φ⁻² = 09:10:01.86      24·φ⁻¹ = 14:49:58.14
```

Fibonacci convergents `F(n)/F(n+2)` oscillate toward `φ⁻²`
(3/8 → 09:00, 5/13 → 09:13:51, …, limit 09:10:02).

## 3. Noon as common inversion axis

Exact coincidences at 12:00:00 (all identities, no fitting):

- half day: `p = 1/2`, `θ = 180°`
- symmetric tritone: `log2(√2) = 1/2`
- golden pair midpoint: `(φ⁻² + φ⁻¹)/2 = 1/2`
- fourth/fifth midpoint: `log2(4/3) + log2(3/2) = 1`
- the Pythagorean d5/A4 pair straddles noon symmetrically; the envelope
  11:45:55 → 12:14:05 is **exactly one Pythagorean comma** wide.

Temporal reflection: `t* = 24 − t` exchanges conjugate nodes
(φ⁻² ↔ φ⁻¹, 4/3 ↔ 3/2).

## 4. The temporal Pythagorean comma

```
C_P = 3¹²/2¹⁹
C_time = 24·log2(C_P) = 0.4692002 h = 28 m 09.12 s
```

Residual coordinate for any observed boundary vs harmonic node:

```
χ = (t_ICT − t_harmonic) / C_time
```

Exact residual identities:

| Comparison | Residual | χ |
|---|---|---|
| 10:00 vs 4/3 | +2m20.76s | +1/12 |
| 14:00 vs 3/2 | −2m20.76s | −1/12 |
| 20:00 vs 16/9 | +4m41.52s | +1/6 |
| Pyth d5 → Pyth A4 | 28m09.12s | 1 |
| Noon → either tritone edge | 14m04.56s | 1/2 |

Registered fraction classes for the engine: `{0, ±1/12, ±1/6, ±1/4, ±1/2}`,
classification tolerance 1/48.

## 5. Interval circles and the evening arbelos

Any interval `[a, b]` is a circle on the temporal baseline with
`center = (a+b)/2`, `radius = (b−a)/2`. Splitting at `c` produces two child
circles externally tangent at `c`, each internally tangent to the parent.

The 14:00–24:00 parent (10 h) splits exactly into CBDR 14:00–20:00 (r = 3 h)
and Asian 20:00–24:00 (r = 2 h): center distance 5 h = 3 + 2, a genuine
arbelos packing tangent at 20:00.

## 6. Golden-axis Descartes/Pappus chain

For the symmetric chain inside the golden interval (R = 12·φ⁻³ h):

```
κ_n·R = n² + 2                 (parameter-free curvature law)
r_n   = R/(n²+2),  y_n = 2n·r_n
D_n   = 24/[φ³(n²+2)] hours
```

| n | κR | D_n | nearby ICT scale | error |
|---|---|---|---|---|
| 1 | 3 | 113.31 min | 120 min | −6.69 |
| 2 | 6 | 56.66 min | 60 min | −3.34 |
| 3 | 11 | 30.90 min | 30 min | +0.90 |
| 4 | 18 | 18.89 min | 20 min | −1.11 |
| 5 | 27 | 12.59 min | 10 min | +2.59 |
| 6 | 38 | 8.95 min | 10 min | −1.05 |

The proximity of D₁…D₄ to 120/60/30/20 is a **hypothesis**, not an identity
(note the exact 3:1 ratio D₂:D₄).

## 7. Salience model implemented by the indicator

Per family `f ∈ {clock, pyth, gold}` with bandwidth σ_f (minutes) and
weight w_f:

```
d_f  = circular distance to nearest node of family f (hours)
K_f  = exp(−½ (60·d_f/σ_f)²)
S_T  = Σ w_f·K_f / Σ w_f              ∈ [0, 1]
```

Confluence order = #{f : K_f > 0.5}. Nesting depth N = number of registered
ICT windows containing `t`. The trade-quality frame from the paper is
`Q = w_L·L + w_S·S + w_D·D + w_T·T + w_N·N`; the indicator supplies only the
T and N terms — L, S, D remain the trader's or a downstream model's job.

## 8. Reference node table (Appendix A of the paper)

| Node | Definition | NY time | Angle | Cents |
|---|---|---|---|---|
| NY midnight | clock | 00:00:00 | 0.000° | 0.000 |
| Pyth M2 | 9/8 | 04:04:42 | 61.173° | 203.910 |
| Pyth M3 | 81/64 | 08:09:23 | 122.346° | 407.820 |
| Golden angle | φ⁻² | 09:10:02 | 137.508° | 458.359 |
| Perfect fourth | 4/3 | 09:57:39 | 149.414° | 498.045 |
| Pyth d5 | 1024/729 | 11:45:55 | 176.481° | 588.270 |
| Tritone | √2 | 12:00:00 | 180.000° | 600.000 |
| Pyth A4 | 729/512 | 12:14:05 | 183.519° | 611.730 |
| Perfect fifth | 3/2 | 14:02:21 | 210.587° | 701.955 |
| Golden complement | φ⁻¹ | 14:49:58 | 222.492° | 741.641 |
| Pyth m6 | 128/81 | 15:50:37 | 237.654° | 792.180 |
| Pyth m7 | 16/9 | 19:55:18 | 298.827° | 996.090 |
| Pyth M7 | 243/128 | 22:11:44 | 332.933° | 1109.775 |
