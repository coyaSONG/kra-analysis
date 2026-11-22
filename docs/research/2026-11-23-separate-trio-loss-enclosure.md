# Exact-trio loss with two fixed missing-ID margins

The [complete-field projection](2026-11-23-separate-trio-projection.md)
holds each of two missing-ID distributions fixed. Its scaling changes
with the tilt. The within-group gradient of the joint partition is
therefore not the gradient for these separate margins.
`autoresearch.separate_trio_loss.certify_separate_trio_loss` bounds the
negative log probability of one specified trio and its derivative along
one supplied tilt direction. It does not choose a target, fit an
estimator, issue a prediction, or certify a data source. Input floats
define exact stored binary numbers; each map must cover the full field.

## Derivative and verification

Write A for the node-edge incidence with one row per channel key.
Two channels use distinct node identities. A trio is an individual
edge, including when its endpoints equal another trio's endpoints.
Keep the base weights and both margin vectors fixed. With q the
positive optimum, W = diag(q), and f the tilt direction, the log
derivative r satisfies

    r = f - A^T lambda,    A W r = 0.

This is the weighted regression residual of f on additive node
potentials. Negate its target coordinate for the loss derivative.
The approach follows [implicit differentiation of entropic transport](https://openaccess.thecvf.com/content/CVPR2022/papers/Eisenberger_A_Unified_Framework_for_Implicit_Sinkhorn_Differentiation_CVPR_2022_paper.pdf);
here the support may be disconnected or have parallel individual trios.
A true individual-edge bridge cannot carry a feasible change:
summing oriented incidence over either side of its cut proves that its
mass is fixed. Cut these bridges for the local error bounds. The full
base normalization still includes every original trio.

For any positive W, let P_W be the residual operator above and
Q_W = I - P_W the additive part. In a connected component of n nodes,
orient each edge from one channel to the other. Across a cut between
two consecutive sorted potential values, the weighted mean of the
potential drops equals the weighted mean of the signed input on those
edges. A gap larger than the maximum absolute input is impossible.
Thus the infinity norms of Q_W and P_W are at most n-1 and n.

Use the existing float projection as a proposal only. Combine the
exact base softmax with an exact rational circulation to obtain a
feasible qF. Use directed arithmetic to establish positivity and
bound the log stationarity residual s after subtracting an additive
potential. The log difference between qF and q is P_V s, where V uses
the positive logarithmic means of the two masses on each edge.
Indeed, multiplying the log difference by V yields qF - q, which
has zero margin change. Therefore each target log coordinate is
within n times the residual bound. A tilt exactly additive within
the target component leaves its base probabilities unchanged.

For the derivative, numerically propose tree-edge residuals in a
maximum-weight forest; a chord's weight divided by any tree weight
on its path is at most one. Verify separately: require exact rational
mass movement z with Az = 0, and enclose z/qF and its stationarity
residual. This gives an error bound at qF by the same cut argument.
If the log-weight error is a, the residual operator changes by at most
n(n-1) a times the direction norm, by differentiating the additive
normal equations along a log-weight segment. A second bound uses the
verified size of the actual residual at qF and the relative change
factor exp(a)-1, bounded by a/(1-a) for 0 <= a < 1. Use the tighter
valid bound. No tiny mass is rounded to a declared zero or deleted.
An unavailable enclosure returns a reason and no loss or derivative;
a wide enclosure is not a precise training gradient.

## Why fitting would not be convex

Take five fictional runners and missing sets {4} and {5}. Equal weights
put masses 1/10, 3/10, 3/10, 3/10 in the four cells (00, 01, 10, 11).
Tilt only cell 00 by theta. Fixed margins give cell masses x,
2/5-x, 2/5-x and x+1/5. The log cross-ratio increases by theta.
At zero tilt its first two derivatives with respect to x are 20 and
-800/9. Hence x' = 1/20 and x'' = 1/90. The loss of any specific
trio in cell 11 has curvature **-1/108** there, since its cell
conditional is unchanged. A unique probability solution at each
tilt does not make coefficient fitting convex or justify a global
convergence claim.

## Synthetic evidence

The independent tests use a high-precision scalar cross-ratio solution,
exact enumeration of spanning trees on another graph, disconnected
and parallel cases, probability below binary64 range, and intentionally
bad forward and linear proposals. A false proposal cannot produce a
false narrow enclosure.

Replay the same 19 anonymous shapes and the same fictitious input
weights as the prior projection. Fix test widths of 1e-6 for loss and
1e-5 for one tilt derivative; these are numerical diagnostics, not a
training or future-study rule.

| Synthetic case | Initial proof within width | Refined proof within width | Refined wider / unavailable |
| --- | ---: | ---: | ---: |
| Modest tilt | 17 / 19 | 19 / 19 | 0 / 0 |
| Modest tilt with rare runner mass | 17 / 19 | 19 / 19 | 0 / 0 |
| Concentrated tilt | 1 / 19 | 6 / 19 | 12 / 1 |

The remaining unavailable case hit the existing projection sweep
limit; no iteration budget or width was changed. The other
previously unavailable target is fixed by the exact local structure.
The local folder `separate-trio-loss-bounds-20261123/` retains both
versions: v1 SHA256
`11c5ed1b6ae429af673c07559d6b1d26ab2a9a93ea9836d86cef82566480c67e`,
v2 SHA256
`e54d5bf475cda6eea23f63f89080769a5c55deef235178e18b349290fe644542`.
No observed features, predictions, or targets entered these tests.

A later study still needs an eligible positive base and training rows,
a reviewed optimization and numerical-failure policy, and a separate
preregistered future full-card comparison. Do not drop a race or change
the fixed metric because its gradient or mode could not be verified.
The original commitments and 70 percent objective are unchanged.
