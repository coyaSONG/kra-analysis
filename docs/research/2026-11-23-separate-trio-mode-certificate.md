# Certifying a unique mode of the separate-margin trio projection

The [previous projection audit](2026-11-23-separate-trio-projection.md)
shows that a log-margin residual of 5.11e-12 can coexist with a reversal of
the two leading trios. A small residual alone cannot establish the most
probable trio. The offline certifier in
[`separate_trio_mode.py`](../../packages/scripts/autoresearch/separate_trio_mode.py)
returns a unique mathematical maximum only when it can prove it, or gives an
explicit reason for non-certification. It does not change the distribution,
choose a fallback, or alter either fixed forecast model.

## Certificate

Treat each input binary64 log weight and tilt as the exact real number it
represents. Represent every supported trio as a distinct edge between its
channel-specific exact missing-ID sets. If the tilt equals a sum of row and
column potentials on **every** edge, its expected value is constant for all
feasible distributions. The unique maximum is then the largest original
baseline log weight; ties produce no trio. The published weak-connection
counterexample is resolved by this exact test, even though its old approximate
ordering is reversed.

Otherwise use the existing projection only to propose a feasible point and
arbitrary dual potentials. Solve the edge changes on a spanning forest in
exact rational arithmetic and independently verify zero change at each
vertex. Adding these changes to the exact baseline softmax preserves both
margins and total mass. Demand strictly positive lower bounds for the
resulting feasible vector f. Let q* be the exact optimum and q_y be the
normalized tilted vector after adding the proposed potentials. Because
f and q* have the same margins, KL(f || q_y) equals the primal objective
gap plus KL(q* || q_y); the primal objective gap is KL(f || q*) by the
first-order conditions of the positive optimum. The gap is therefore at
most any verified upper bound U on KL(f || q_y). See
[Csiszar's I-divergence geometry](https://projecteuclid.org/euclid.aop/1176996454).

A lower bound g on the leading probability gap at f proves the same
unique maximum at q* if g > 0 and g squared is strictly greater than 2U:
[Pinsker's inequality](https://people.lids.mit.edu/yp/homepage/data/itbook-export.pdf)
bounds each coordinate error by the total variation, at most sqrt(U / 2).
Use directed 80-digit arithmetic and enclose each correctly rounded exp
or ln by its representable neighbors, as supported by
[Python's Decimal specification](https://docs.python.org/3.13/library/decimal.html).
A failed enclosure or gap check never returns the approximate mode.

## Same synthetic inputs

The tests include an independent 100-digit solution of a nonadditive
two-by-two table whose optimum changes, with tie, parallel-edge,
disconnected-graph, bad-proposal and ambient-rounding regressions. Replay
the prior fixed inputs on all 19 anonymous shapes with no parameter
change or retry at a different precision.

| Synthetic input | Unique modes proved | October / November shape equivalents | No certificate |
| --- | ---: | ---: | --- |
| Modest tilt | 18 / 19 | 50 / 50 | 1 exact tie |
| Modest tilt with an extremely small mass | 18 / 19 | 50 / 50 | 1 exact tie |
| Concentrated tilt | 0 / 19 | 0 / 0 | 1 exact tie, 16 feasible positivity checks failed, 2 projections did not converge |

The previous 17 accepted concentrated projections established residual
checks, not usable modes. The 16 positivity failures here concern the
constructed witness; they do not imply the true optimizer has zero mass or
that all those optima are tied. The next useful numerical test is a
strictly feasible witness by construction for sharply concentrated cells,
rather than relaxed convergence or rank tolerances.

Local receipt: `separate-trio-mode-certificate-20261123/mode-shape-replay.json`,
SHA256 `35561349d708c83b0f13c2915bf4c7b71c33a62de38382974a7806e316540b89`.
It pins the implementation, experiment and prior synthetic receipt.
The replay uses no real feature values or labels and makes no source calls.
Multiplicities are archived shape equivalents, not independent trials,
forecastable races or accuracy.

This is a proof conditional on supplied inputs, not an eligibility audit,
training result or prospective prediction. Before use, separately establish
an eligible baseline and a preregistered procedure that covers the whole
future card even when a proof attempt fails. Do not replace or exclude a race
because its maximum was not certified. The 70% prospective target is not met.
