# Full-field exact-trio probabilities and missing data

The [repair audit](2026-11-23-exact-trio-repair-bounds.md) rules out
editing at most one runner in either published prediction as a way to
reach 35 hits on the October block. The new numerical component can
represent one exact set anywhere in a complete declared field. It is
not wired into M0, API27, production, or a training run.

## Complete distribution

For declared runners, enumerate every distinct unordered triple. Let
`l0(S)` be a supplied finite base log weight, `P0` its normalized
distribution, and `F(S)` a fixed vector for that triple. For each
measured channel, record the exact set of its unavailable runner IDs
present in `S`. The tuple of those sets is the group `G(S)`. The
component preserves the base mass of each group and only changes its
conditional distribution:

```text
Q(S) = P0(G(S)) * exp(l0(S) + theta dot F(S))
       / sum_{T in G(S)} exp(l0(T) + theta dot F(T))

d(-log Q(S))/d(theta) = E_Q[F(T) | G(S)] - F(S)
```

Zero coefficients recover the base distribution. A singleton group
has zero gradient and cannot change. The exact-set loss is not a loss
on the three marginal runner probabilities. The prediction is one
joint mode over the entire field; an exact numerical tie uses canonical
numeric runner IDs. Completeness and finite-value checks reject a
shortlist, extra rows, wrong unavailable IDs, or unrepresentable
operands. Normalization and loss retain small positive support in log
space. The caller must independently supply an eligible roster and
define the base weights, features and unavailable sets. Existing
linear ranking scores are not being certified as probabilities.

## Archived input geometry

Use the [literal PDF audit](2026-11-23-pdf-tip-rating-reach.md), which
joins all 534 October and 540 November declarations to their original
cards. October's exact PDF bytes have the independent pre-cutoff
witness documented there; November has local receipts only. No target,
old prediction, baseline score or later revision is read here.

For each channel, form pair products of the two printed values, then
subtract one effect per known endpoint so the residual edges sum to
zero at every known endpoint. Sum the within-triple residual edges.
An unavailable value supplies no edge; it is not a zero pace rating,
an imputed value, or a reason to remove the runner. For the exact screen,
take feature differences relative to one triple in each group. Report
the number of independent feature directions across those differences
with the base held fixed. Also check the increase in rank when the
same differences in arbitrary runner indicators are already present.
The two counts agree for every field in these cards, not in general.

| Design | October 50: rank 0 / 1 / 2 | November 51: rank 0 / 1 / 2 |
| --- | ---: | ---: |
| No partition, diagnostic only | 0 / 1 / 49 | 2 / 3 / 46 |
| Early only, exact early missing IDs | 1 / 49 / 0 | 3 / 48 / 0 |
| Late only, exact late missing IDs | 0 / 50 / 0 | 4 / 47 / 0 |
| Both, exact missing IDs for both | 15 / 6 / 29 | 22 / 9 / 20 |

Keeping both exact missing sets fixed is equivalent to fixing membership
of their union, since the unavailable sets for each channel are known.
Within each such group, only runners known in both channels can be
swapped. Just 2,849 of 7,629 October triples and 2,542 of 7,488 November
triples are in non-singleton groups under the joint constraint. A
non-singleton group can still have identical features, and a nonzero
rank need not change the mode. These are structural counts, not hits,
performance estimates, or proof that the features are learnable.

All 15 zero-rank October fields and 21 of the 22 zero-rank November
fields have at most one runner with both values, so all their groups
are singletons. The remaining November field has three runners with
both values, yet its two residual features have no within-group
variation. Preserve all these fields; coefficients cannot fix absent
comparison support.

## Reproduction

The exclusive local `full-field-exact-trio-20261123/interaction-geometry.json`
pins the source ledger, code, original per-field PDF digests, and scope.
SHA256: `4c77ee6e15574b77bdcb704d44f12188982d50d6dbf53822c849dd3462befc15`.
Read-only replay reproduces the record. A separate integer elimination
check on the original ledger matches every field and policy. The
focused and adjacent local suites pass 181 tests, including finite
difference checks, singleton invariance, tiny masses, and a synthetic
case where the mode moves to a set disjoint from the base mode.

This is a diagnostic for future design, not a reason to select an arm
from these cards. A future candidate still needs approved as-of
training evidence and its own preregistered, complete future comparison.
No source, target, outcome policy, prediction or population was changed.
No network collection, real fit, model promotion, or new accuracy
figure is part of this work. The 70% goal remains unmet.
