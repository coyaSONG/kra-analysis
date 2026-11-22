# What the printed pre-race summaries add to entry ratings

The literal official card summaries distinguish runners that the
positive entry rating and assigned kilograms leave tied. The source
is a partial view, not a complete order of the field. This is an
input audit of two original cards, not training or a race outcome
comparison.

## Source and cutoff boundary

Keep all 50 races from October 16-18 and all 51 from November 20-22.
The replay joins exact race ID, gate and stable horse ID at every
original declaration. Physical venue and distance match; the older
PDF audit's grade-token conversion handles the 99 compact-vs-long
display strings without combining different grades. Both spellings
remain inspectable. No later declarations or results were read.

The original API26 rosters supply positive rating and the raw
assigned burden, with no new adjustment for a jockey allowance.
Zero/nonpositive and unknown ratings are not bottom-ranked. The
official PDF's DATA TIPS table supplies three separate short lists:
printed early and late averages and printed speed index. Use lower
early/late numbers and higher index as directions of those literal
values. A dash, empty slot or omitted runner is not a slow time,
low index or a proven rank. When one or both runners lack a value
in a given column, the direction in that column is unknown.
No conversion assumes a shared physical timing layout across venues.

The October entry evidence is bound in [PR 95](https://github.com/coyaSONG/kra-analysis/pull/95).
The exact PDF union was independently bound in
[PR 100](https://github.com/coyaSONG/kra-analysis/pull/100) at
2026-10-15 12:20:13 UTC, after the baseline forecasts and before the
2026-10-16 01:20 UTC cutoff. These PDF columns were not inputs to
those forecasts. This proves a bound on the availability of the
exact source bytes, not the first KRA publication time, the
operator's arithmetic or prior availability of this transformation.
For November the observed API and PDF receipts precede the original
2026-11-20 01:15 UTC cutoff locally; neither has the independent
clock evidence required here. No historical status is upgraded.

## Whole-card comparison

Each pair is counted once in a race, including incomparable pairs.
Across columns the counts are unions, not sums.

| Measure | October 16-18 | November 20-22, local only |
| --- | ---: | ---: |
+| Original races / declarations | 50 / 534 | 51 / 540 |
| All within-race pairs | 2,600 | 2,597 |
| Two numbers in at least one common column | 1,121 | 1,151 |
| Strict comparison in at least one column (races) | 1,011 (50) | 1,021 (50) |
| Any known column orders opposite to positive rating (races) | 332 (37) | 388 (37) |
| Distinguished / equal positive rating and assigned kg (races distinguished) | 36 / 95 (24) | 24 / 78 (16) |
| Opposite early/late directions / both strict | 31 / 68 | 24 / 57 |

Only 43.1% and 44.3% of the original pairs have two values in any
one column. A known direction in 50 races is not a complete ranking.
The opposite-direction counts cover overlapping pairs from the same
fields and days, not independent observations. The nature of this
selected print also precludes using the observed fraction to infer
unprinted values. Differences between the two fixed cards are
descriptive, not a change in predictive ability.

## Next research decision

Retain the early and late prints separately: the archive shows that
their known directions need not agree for the same runner pair. A
simple same-rating/same-burden tiebreak has limited reach (24 of 50
October and 16 of 51 November fields). For a later model, carry the
actual literal numbers and separate observation flags for every
declared runner, not imputed display ranks or a filter that removes
unprinted horses. The hypothesis is complementary information,
not a performance claim or a new approved model specification.

Prioritize preserving and witnessing the next complete official card
and fixed M0/API27 pair. Optional PDF acquisition must not consume
their publication window. A later candidate needs its own timely raw
PDF and API roster proof, separately reconciled labels, frozen
training recipe, and an independent future whole-card comparison
on one unordered triple per race. Neither of the two cards above
can independently validate a candidate chosen from this review.

## Reproduction

The local `pdf-tip-rating-reach-20261123/tip-rating-reach.json` ledger
preserves the per-field source pins, collection and witness clocks,
original identities, every pair-state denominator and literal
missingness. SHA256: `f4078c2c5b3b6ef9aec12837c9d6a34e9201189258b14263e2af979d8f8890c9`.
The source replayer reopened the exact archived PDFs. An independent
calculation rehashed 89 preserved API26 page files and
reproduced every field's pair-count totals from API rows and PDF slots.
Read-only replay and 237 focused and adjacent tests passed. No
KRA or API request, fit, prediction, accuracy calculation or change
to either published prediction hash occurred.
