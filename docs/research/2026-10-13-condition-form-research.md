# Similar-condition form: a small retrospective gain, not a promoted model

## Result and Decision

Five fixed non-fitting rules produced all **3,355 selections across the same
671 archived races and 6,816 runner appearances**. Exact unordered-three matches
were 28 for expanded90, 28 for same venue, 31 for similar distance, 31 for exact
class, and 32 for their intersection. Joint conditions gained eight matches and
lost four against expanded90. This small descriptive difference does not justify
promotion or tuning more thresholds against these already examined outcomes.

This is a late-captured retrospective diagnostic with result-derived rosters and
target conditions, not a pre-race backtest, untouched holdout, calibrated
probability, deployed-model comparison, or evidence for the 70% goal. All arms
retain 57 pending and one undefined outcome. No fitting or promotion occurred.

## Authenticated API Check and Recovery

On 2026-10-13 KST, the logged-in [portal application list](https://www.data.go.kr/iim/api/selectAcountList.do)
showed 14 approved active APIs and one expired application. The expired item was
the unrelated TAGO bus-arrival service, not a KRA API. Authenticated details:

| API | Status/account | Daily traffic limit | Expiry |
| --- | --- | ---: | --- |
| API214_1 / RaceDetailResult_1 | Approved, development | 10,000 | 2027-05-24 |
| API26_2 / entrySheet_2 | Approved, development | 3,000 | 2028-06-15 |

These are daily allowances, **not verified remaining-call balances**. No key
rotation, quota change, new application or paid service was requested. Credentials,
account IDs and personal details are excluded. At 13:02 UTC, bounded probes for
June 7 Seoul returned HTTP 200/code `00`, 100 first-page rows and totalCount 109
for both APIs. This proves response recovery, not that browser login caused it.
Probe receipts under `.cache/autoresearch/history-api-diagnostics`:

| Receipt | SHA256 |
| --- | --- |
| 20261013-approval-api214.json | `3878c01c009b1e9e698862b7ef958d6fa22183781f871241040f9699d24e69d1` |
| 20261013-approval-api26.json | `4d76448d1bb5b991bc5375cf2769cd3b83dc075f3e7015668d4145a11f754361` |

Resumed the existing June1-July4 four-venue 512-call plan with `--retry-failed`.
Old failures and `seed-attempt-1.json` remain intact. All 136 date/venue units
were attempted: 28 returned rows, 108 were empty responses, which are **not proof
of no scheduled racing**. Total request reservations: 147 including three old
failures; the successful increment used 144. The two probes are separate. This
is not an account-wide usage audit.

Recovered **237 races / 2,375 rows**: June 204/2,046, July 33/329. Raw pinned replay
passed; the race-ID set equals the official HTML catalog. `reconcile_group`
supports 2,339 numeric rank/time rows. `observe_race` yields 236 unique top-three
observations and one unresolved mapping, `20260628_1_4` (`no_unique_1_2_3`). Do
not invent its top three or reinterpret the other 36 rows as failures. Captures
remain late and unapproved for fitting. These newly corroborated rows are **not
injected** into the fixed experiment below; its HTML-only June tier is unchanged.

Recovery root: `.cache/autoresearch/observed-history-extension-20260601-0704`.

| Artifact | SHA256 |
| --- | --- |
| plan.json | `679676e6661413ddfe66756b8f15dfe6d69fb35efbaa59d9879dcb099d57ef05` |
| seed-recovered-20261013.json | `c114b14920cc1b10ca807e9dde9256f4d373928cb11ab55ff55667bc3b6ad6f8` |
| recovered-catalog-audit-20261013.json | `5b1c46932abac5a2057be8e0d003ac55c3f96cedca08bd9bfd3ea0a52637e5fd` |

The audit replays this seed with `frozen_history_view.replay_frozen` and the
catalog pins in `history_form_exploration_v1.json`, groups API rows by race,
then applies `reconcile_group` and `observe_race` to catalog rows. Count is the
archived roster size, not verified scheduled runners. Raw data stay local.

## Fixed Design

Protocol/ExecPlan were committed as `c08cb77` before execution. Protocol
`data/contracts/condition_form_exploration_v1.json` SHA256 is
`a1ae3612217706362c437c7bb9417835f5c2506d56b9d84c305bfc6755b0460f`.
It pins the unchanged source protocol and its original target/earlier/June data.

| Arm | Eligible prior observations |
| --- | --- |
| expanded90 | Original expanded90, no condition restriction |
| venue90 | Same physical venue, observed dated-header conditions |
| distance90 | Same venue and absolute distance difference <= 200m |
| class90 | Same venue and exact class label |
| joint90 | Same venue, distance difference <= 200m, exact class label |

All use strict prior dates `[D-90,D)`. For full observed prior roster N and finish
rank r, score is `(1 + sum((N-r)/(N-1)))/(2+n)`, with exact fractions and
gate/numeric horse-ID ties. Missing target conditions or zero eligible priors
trigger **per-runner expanded90 fallback**, not deletion or whole-race fallback.
No history keeps the fixed 0.5 prior. These are mixed fallback policies, not pure
conditional scores; sample size and shrinkage change alongside filtering.

The additive parser locates a unique dated header, checks physical venue/date/
race number and reads adjacent class/distance cells. Normal header/rating spans
are allowed; spans in those two value cells are rejected. Finish rank, rating
and `Grade2` in a race title never substitute for class. National/mixed/Jeju and
OPEN labels remain distinct; 1110/1610m are not rounded. No ordinal class mapping.
Conditions are HTML-only evidence even where outcomes have two-source support.
Receipt/raw pins, encoding, capture time and table coordinates are retained.

Across 978 source groups, 903 conditions are observed and 75 unknown. Target
coverage is 616/671 groups and 6,273/6,816 rows. The other 55 groups/543 rows
remain with baseline fallback; template pages do not prove event occurrence or
absence. Malformed/ambiguous context is unknown; raw pin failures abort.

## Full-Population Counts

| Arm | Races | Match | Mismatch | Pending | Undefined | Execution failure |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| expanded90 | 671 | 28 | 585 | 57 | 1 | 0 |
| venue90 | 671 | 28 | 585 | 57 | 1 | 0 |
| distance90 | 671 | 31 | 582 | 57 | 1 | 0 |
| class90 | 671 | 31 | 582 | 57 | 1 | 0 |
| joint90 | 671 | 32 | 581 | 57 | 1 | 0 |

| Versus expanded90 | Both match | Baseline only | Candidate only | Neither | Not comparable | Changed combinations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| venue90 | 28 | 0 | 0 | 585 | 58 | 3 |
| distance90 | 26 | 2 | 5 | 580 | 58 | 55 |
| class90 | 25 | 3 | 6 | 579 | 58 | 114 |
| joint90 | 24 | 4 | 8 | 577 | 58 | 133 |

Joint monthly matches are July 1, August 14, September 11, October 6; baseline
is 1/13/8/6. There is no October net gain. Repeated horses and shared dates are
not independent observations. No monthly winner, OR-combination, resolved-subset
accuracy or significance claim is made.

| Diagnostic | expanded90 | venue90 | distance90 | class90 | joint90 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Runner rows using baseline fallback | 0 | 1,885 | 2,208 | 2,849 | 3,128 |
| Selected runner rows using fallback | 0 | 389 | 462 | 884 | 937 |
| Runner rows without history after fallback | 1,098 | 1,098 | 1,098 | 1,098 | 1,098 |
| Eligible priors 3+ | 1,519 | 1,195 | 1,027 | 810 | 726 |
| Third/fourth score ties | 140 | 143 | 140 | 143 | 142 |

Joint90 falls back for almost half the runner appearances. Its small gain does
not establish an isolated condition effect or reliable future lift. The useful
next validation is prospectively captured target conditions and frozen single
selections, not more threshold searches on these labels.

Completed Pro advice motivated diagnostics only, after the first results were
seen. All 34,080 scores and 3,355 combinations stayed identical in `run-2`.
Existing eligible history has **zero rows without observed conditions**. The 55
unknown target-condition IDs exactly equal the 55 `source_missing` outcome IDs;
do not blame those groups for losing condition history or diluting scoreable
matches. The 75 unknown source headers were already outside numeric history.

| Additional diagnostic | venue90 | distance90 | class90 | joint90 |
| --- | ---: | ---: | ---: | ---: |
| Runner scores actually changed | 41 | 416 | 609 | 746 |
| Prior contributions condition-eligible | 9,729 | 8,756 | 7,234 | 6,585 |
| Prior contributions with mismatched conditions | 543 | 1,516 | 3,038 | 3,687 |
| Prior contributions blocked by missing target context | 1,357 | 1,357 | 1,357 | 1,357 |
| Races with all runners on fallback | 79 | 81 | 98 | 101 |
| Races with mixed score paths | 427 | 491 | 533 | 540 |
| Races with every runner using condition scores | 165 | 99 | 40 | 30 |

Each prior partition sums to 11,629 baseline contributions. Fallback can re-add
mismatched priors, so actual used histories/scores need not be nested as filters
get stricter. Whole-header recognition was fixed in this protocol for every
condition arm. Pro suggested per-field missingness for future partial headers;
all observed headers here have both fields, so no observed partial-field case
requires a post-result policy change. Raw cell text stored by `Tables` already
has decoded HTML entities and collapsed whitespace; original bytes remain pinned.

## Reproduction and Validation

From the isolated checkout root:

```sh
PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.condition_form_research \
  --plan data/contracts/condition_form_exploration_v1.json \
  --plan-sha256 a1ae3612217706362c437c7bb9417835f5c2506d56b9d84c305bfc6755b0460f \
  --output-dir .cache/autoresearch/condition-form-research-20261013/new-replay
```

Require a new output directory. Save inputs/conditions before scoring and all
predictions before outcome comparison. Scorer receives identity-only target
rosters, history and conditions, never target labels. Source/implementation pins
are retained; frozen M0/API27 and fit gates remain unchanged.

Artifacts under `.cache/autoresearch/condition-form-research-20261013/run-1`:

| Artifact | SHA256 |
| --- | --- |
| targets.json | `814d42e0d74b607986235f332fa8466203755e550fb691fd55d74714633ebb03` |
| history.json | `f718152b1465bea5990145ed30afb2402eaaba9ce2640a89163841e6211e5125` |
| conditions.json | `818f0be674ef148b9c83e46192a52686be1e5ba2805b5daf8c601134aaaa6123` |
| predictions.json | `38b6a8686ae17b0101b63a1bf6b028baac1982fa8dc3610d6e95eebffdf72387` |
| report.json | `16d59bccc8c93eb712232d6da78ae607725249970f3ef972fbcaa86c37d51da1` |
| independent-check.json | `de43deb67a06c26908b650d81e3275b589353af922f358e392b1c701ea7ae6cd` |

Independent arithmetic from full history, not scorer-selected prior lists,
reproduced all **34,080 scores and 3,355 selections**. Every expanded90 score,
prior ID/tier and selection matches PR92; target manifest hash is identical.
**246 related tests passed**, including 48 new tests covering identity/encoding/
pins, malformed conditions, distance/date boundaries, fallback, label isolation,
duplicates, outcome states and exclusive saves. CI includes the new test step.

## Pro Consultation and Publication

A follow-up design critique completed in the authorized
[Pro conversation](https://chatgpt.com/c/6aca2dc4-d2e8-83e8-acab-e85f281c27b7).
The UI reported 8m19s processing and a completed response. Generation was not
interrupted or subjected to a short response timeout. Pro read public PR92/main
and our design summary, not the new local code, raw files or experiment outputs.
It found no fatal design flaw and supported a bounded non-fitting policy
comparison. It emphasized unchanged baseline/source eligibility, direct per-horse
fallback, non-monotonic shrinkage, exact-label limits, and honest retrospective
interpretation. We added the diagnostics and synthetic counterexamples above,
not new arms, tuning or promotion. No account data or credentials were submitted.

Final diagnostic artifacts in `run-2` (inputs remain identical to `run-1`):

| Artifact | SHA256 |
| --- | --- |
| predictions.json | `cdbe7402585c1fb3d02362e1a6b12f0e7eaf12a8d9809667ca52a8a479675c20` |
| report.json | `8b958c2fda394ef109175611b2ac78a9e219b6269ac810e4c79601facea1f948` |
| diagnostic-invariance.json | `d94e5248e3c14dee5ce68c926c7d370fcd9a389ec18b3cb4ce4408abb8af06cb` |

Publication and CI closure will be recorded on the PR. Normal merge only; no
required-check bypass. Research code gains do not imply a production-model gain.
