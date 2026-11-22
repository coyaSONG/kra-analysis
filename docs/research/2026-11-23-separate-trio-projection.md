# Numerical projection with two separate missing-ID margins

The [separate-margin design audit](2026-11-23-separate-missing-id-margins.md)
found additional structural contrasts, not an improvement in predictions.
For a possible later study, the offline numerical component can now
compute the corresponding complete-field distribution from hypothetical
weights. It does not derive weights from the frozen single sets, choose
between margin policies, or authorize a source or model.

## Definition and numerical checks

Give the calculator one finite base log weight and one finite log tilt
for **every** unordered trio of the declared runners. The normalized
base is positive on that complete support. A trio has two keys: its
exact subset of unavailable runners in each of the two channels.
The target is the unique minimizer of KL(q || tilted base), subject to
preserving every key's marginal mass from the base **in each channel
separately**. The base is itself feasible. Strict convexity gives
uniqueness. Joint key-pair masses need not be preserved.

The KL chain rule fixes the conditional distribution inside each
key-pair cell to the tilted conditional. Scale the remaining cell
masses in log space, alternating the two margins. This is iterative
information projection under ideal arithmetic; see [Csiszar, 1975,
Section 3](https://projecteuclid.org/euclid.aop/1176996454).
On the bipartite cell graph, a bridge's mass cannot vary: the
difference from the base has zero net flow across its cut. Fix each
bridge at its base mass and sum the flexible baseline margins directly
from their cells. Subtracting bridge masses from totals can erase
small flexible masses. A bridge can still change its conditional
distribution when several trios share it.

Recompute both margins, normalization and all fixed cell masses from
the returned complete trio vector. Independently reconstruct node
adjustments and check the additive form of each trio's log ratio to
its tilted weight. The log residual limit is 1e-10. These are
acceptance checks, not a bound on forward error, optimizer
suboptimality or the margin between the most probable trios. Keep
probabilities as logs even when ordinary exponentiation would lose
them. If the checks fail or 4,096 sweeps do not suffice, return no
distribution. The module exposes neither a mode nor a fallback.

A weakly connected four-cell example demonstrates the distinction.
Use runners 1 through 5 with missing sets {4} and {5}; index the cells
by those two membership indicators. Set the base log weight of
(1,4,5) to 0 and of (1,2,3) to -1e-12. The other trios in cell (1,1)
have log weight -80; distribute log mass -90 uniformly in each
off-diagonal cell. Add 64 times the column indicator minus 64 times
the row indicator to each trio. This is only a row plus column tilt,
so the true projection is the base. The floating-point computation
passes with a 5.11e-12 margin log residual but reverses the order of
the two nearly tied leading combinations. Do not use the result to
select a trio without a separate way to certify that ordering.

## Offline checks on original field shapes

A balanced four-cell example has an exact solution; an asymmetric
example agrees with an independent 70-digit cross-ratio calculation.
Other tests check row and column tilt invariance, direct enumeration
of bridges on all 511 nonempty subgraphs of a 3-by-3 cell graph,
positive mass below ordinary floating-point range, and explicit
failure rather than returning the last iterate.

Group the archived 50 October and 51 November fields into 19
anonymous shapes by roster size and the three observed counts (early,
late, and both). These counts reconstruct the two missing sets up to
runner relabeling. Assign only deterministic fictitious log weights
and tilts. For each returned vector, independently verify both full
margins and total mass in 60-digit arithmetic.

| Synthetic input | Verified shapes | October / November field equivalents | Most sweeps on a verified shape |
| --- | ---: | ---: | ---: |
| Modest tilt | 19 / 19 | 50 / 51 | 38 |
| Modest tilt, -900 log weight for trios with one fictitious runner | 19 / 19 | 50 / 51 | 40 |
| Concentrated tilt between -180 and +180 | 17 / 19 | 46 / 47 | 3,457 |

Both rejected shapes hit the sweep limit. They represent four fields
on each card. No rejection was retried with a different budget. The
largest independent log residual on accepted shapes was 4.88e-11.
These field equivalents are not independent trials, actual accepted
race forecasts, or accuracy. This experiment makes no new clock
claim: October's independent witness and November's local-only
receipts remain distinct.

The local exclusive numerical record is
separate-trio-projection-20261123/shape-stress.json with SHA256
9e2d24c7a31c9ac17cd5da6751dccb6c70e38020599a64abfe70ee53442aa230.
It binds the source shape inventory, the calculation and the
synthetic test. No real feature value, label, source call, fit,
prediction or model change is involved.

Before fitting, establish an eligible positive base, review the
change in protection for joint missing patterns, and specify how to
differentiate the constrained fit and deal with numerical rejects.
The conditional gradient from the original joint model cannot be
reused: the two margin adjustments themselves depend on the tilt.
A real comparison needs a separately registered future whole-card
evaluation, with no exclusion of inconvenient fields. The 70% goal
is not attained.
