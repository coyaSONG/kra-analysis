# Separate missing-ID distributions for the exact trio

The [joint preservation audit](2026-11-23-full-field-trio-distribution.md)
fixed the base probability of every exact pair of unavailable-runner sets.
An alternative would fix each channel's complete distribution of those sets
separately. This is a different constraint, not a change to the existing
calculator or the M0/API27 evaluation. We compare their structural freedom
for the same two printed early and late columns and every original race.

## What the alternative preserves

For a trio S, define its keys as S intersect the unavailable-runner set
of the early channel and S intersect that of the late channel. Keep
both exact keys, including their runner identities; a count alone is
not a key. If a reference distribution were given, preservation of
the two margins would equalize the total probability of every early key
and every late key to its respective reference total. It would not fix
the probability of every **pair** of keys. Probability could move
between joint groups while maintaining each channel's marginal totals.

Build a bipartite graph of the two sets of keys, with one trio per edge.
Two trios on the same pair of vertices can exchange mass under either
policy. On the graph of unique vertex pairs, every fundamental cycle
adds one independent possible direction: add and subtract alternately
along the cycle, holding the sum at every vertex fixed. Starting from
a strictly positive distribution, a sufficiently small move in such a
direction preserves nonnegativity. This is an algebraic test; no real
base probability or proposal to normalize each channel once in sequence
is assumed. The fixed models' single predictions are not probabilities.

## Original input comparison

Replay the [same literal PDF data](2026-11-23-pdf-tip-rating-reach.md):
October 16-18, 50 races and 534 declarations, and November 20-22,
51 races and 540 declarations. October raw bytes have the separately
documented pre-cutoff witness. November has local receipts only;
this comparison supplies no missing independent clock. Do not remove
a missing or withdrawn declaration from the original scope.

Use the same centered pair products of printed times for both
policies. Compute their rank on admissible directions after accounting
for arbitrary per-field runner effects. Also verify the fixed-base rank
without those effects; both ranks agree on these two cards, not by
definition. Independently get the same result by eliminating the
entire integer indicator design, without constructing cycles.

| Card | Joint rank 0 / 1 / 2 | Separate rank 0 / 1 / 2 | Fields moving from 0 | Fields with at least one cycle |
| --- | ---: | ---: | ---: | ---: |
| October 16-18 | 15 / 6 / 29 | 3 / 1 / 46 | 12 | 47 / 50 |
| November 20-22 | 22 / 9 / 20 | 5 / 3 / 43 | 17 | 46 / 51 |

The direct checks cover all 7,629 October and 7,488 November trios.
Allowing cycles restores some nonadditive comparison in 29 of the
37 former rank-zero fields. Another 13 fields move from rank one to
two. These are changes in possible contrasts, not in prediction,
calibration, a sample-size count of independent trials, or accuracy.
The scopes share racing conditions and runners; no sampling interval
or generalization result is asserted.

Six of the eight remaining zero-rank fields have no runner with
both values. They have cycles, but each channel's pair products are
then fixed by the other channel's missing-ID set: there is nothing in
those two columns for a cycle to change. The other two have no cycle
and had zero rank already. A weaker partition does not produce
unobserved measurements or guarantee a different global mode.

## Next decision and reproducibility

Consider separate margins only as a **different** future candidate.
Before a real comparison, independently review whether changes to joint
missing-pattern frequencies are acceptable, define an eligible positive
reference distribution and a prebound fitting rule, and verify both
margins on the complete held-out field. Do not select between policies
using the same outcomes used to train. Define the separately registered
future comparison with the same whole-population unordered exact-trio
metric, and retain every original race even when neither term varies.
No choice to relax a constraint on a particular upcoming field is made.

`separate-mask-geometry-20261123/separate-margin-geometry.json` locally retains
the original source pins, cutoff states, method and every field's rank.
SHA256: `88db91afb65161a8b7dc3c4beab788e25c49503e0dc314f8bb4cb409b527cf47`.
The exact graph and integer-matrix checks agree on every field, and
read-only replay reproduces the same file. No KRA/API call, real model
run, outcome access, fit, prediction or change to any prior publication
occurred. The 70% goal is not attained.
