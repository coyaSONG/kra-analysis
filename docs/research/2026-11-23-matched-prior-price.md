# Match a prior finish and price on the same earlier start

This audit preserves all 153 races and 1,549 declarations in the three
locally frozen November cards. A matched pair exists for **803 of 1,549
declarations (51.8%)**. This is pre-race source coverage in archived input
scopes, not independently timed forecasts, model accuracy or a new study.

## Current prices and earlier results are different sources

The [expected-payout listing](https://www.data.go.kr/data/939/linkedData.do)
leads through [MAFRA's link metadata](https://data.mafra.go.kr/opendata/data/indexOpenDataDetail.do?data_id=20220715000000002234)
to the [API160_1 settled-payout catalog](https://www.data.go.kr/data/15058559/openapi.do).
The linked operation explicitly describes final payouts and finishers'
program numbers. Its update frequency does not make it a pre-race quote
archive. Separately, KRA's [2026 operating plan](https://race.kra.co.kr/down/raceplan2026_20260516.pdf)
places normal opening 20-30 minutes before each start (section 15). In the
previous six-card timing calculation, even the earliest normal opening
could not precede the first whole-card cutoff. That calculation does not
observe actual market access or rule out an earlier exception. Do not
request settled prices to fill a missing early quote or move the cutoff.

The old result-price audit is a different source: completed *earlier*
races with the API and official detail table agreeing on price and
identity. The pinned evidence reuses [PR131](https://github.com/coyaSONG/kra-analysis/pull/131)
for the prior bank and [PR108](https://github.com/coyaSONG/kra-analysis/pull/108)
for the already closed October block as history for November only.
The existing local source and publication clocks are retained separately.
Across both price ledgers, 8,405 starts in 831 complete ordinary fields
reconcile to the pinned start index, API snapshot, official receipt and
price rank. No current-race odds, results or settlements were read for
the November target scopes, and no data operation was called.

## Exact same-start rule

Replay each original API26 entry page and its receipt. Check the full
race/program/horse population, venue, distance, literal class, and input
cutoff against the earlier lineage. In the audited historical bank, match
the same horse and physical venue, the same literal class, a distance
difference of at most 200 m, and an earlier day 1-90 days back. The
historical source and witness must precede the original entry receipt,
which itself must precede the block cutoff. Select the most recent day
*without* inspecting price availability. An ambiguous latest day or an
unverified full-field price leaves the pair missing. Do not use an older
price alongside the newer finish.

Finish position is (rank - 1) / (field size - 1). Price position uses
the same scale with the smallest single-win price first and equal prices
sharing their mean rank. These are order descriptors for the exact same
earlier field, not win probabilities. Within each current race, compare
the two orderings only for runners where both descriptors are available.

| Preserved card (KST) | Races | Declarations | Any comparable price | Same latest start | Races with a strict reversal |
| --- | ---: | ---: | ---: | ---: | ---: |
| Nov 6-8 | 51 | 496 | 290 | 277 | 43 |
| Nov 13-15 | 51 | 513 | 286 | 274 | 40 |
| Nov 20-22 | 51 | 540 | 261 | 252 | 40 |
| Total | 153 | 1,549 | 837 | 803 | 123 |

Of the 746 missing pairs, 642 have no comparable start in the bank,
70 have no verified price on any comparable start, and 34 have an older
verified price but none on the latest one. No latest-day ambiguity was
observed. Coverage varies from 55.8% to 46.7% across these three cards;
pooled venue counts are Seoul 343/654, Jeju 235/403, Busan 161/319 and
Yeongcheon 64/173. A missing bank row is neither a known debut nor a
zero-valued feature.

Only two full fields pair every declaration. There are at least two
paired declarations in 142 fields. The order strictly reverses for
702 of the 2,143 comparable within-race pairs, across 123 fields; a
price also breaks 119 finish-position ties. These pairs share races,
horses and historical references. They are not independent trials and
do not establish which ordering will be more accurate, or whether
either adds to the complete existing feature set.

## Research decision and replay

Do not allocate the existing data-call budget to the settled-payout
alias. The verified historical price position is distinct enough from
historical finish position to justify one future candidate comparison,
with a fixed missing-value treatment, if its source can be reproduced
for the newly enrolled whole cards. Keep the same context rule and
test against the same baseline and complete untouched future races.
The lower coverage for Yeongcheon and the named distance/class cells
are diagnostics, not permission to skip any race or relax the rule
after results. This audit trains, scores and promotes nothing.

The isolated local archive `.cache/autoresearch/matched-prior-price-20261123/` retains
`readback.py`, exact input pins, per-declaration links and missing states,
plus distance/class/venue counts. Source pins for the older price
audit and October extension are
`659b51d2371b914311d09e921b65e8746ab69682290a6d8852075fb121f97b93`
and `9b84e90673a1d720aad459b15b9af81a22f7067b727ca49c93c1074a7b646eba`.
The new sealed report SHA256 is
`0e17c4801c55392a50c75e016a8feb290bf3ab4dd4fc56d2dc60ba0b2dcd672e`;
the replay implementation SHA256 is
`39122912caaa49defa927c521831e40de6ddd04beef548862c9ef41c8c86554d`.
All 189 focused and related tests passed. A separate calculation
reconciled the 1,549 declarations, 153 race IDs and 702 strict reversals
without using the audit's summary counters. The existing M0/API27
prediction and reserved input hashes did not change.
