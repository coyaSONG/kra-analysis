# Historical time repeatability: association, not forward accuracy

## Decision and scope

The checked final-600m relative-speed quantity has some historical recurrence,
but its association with the next observed same-venue, same-distance finishing
rank is weak. This supports keeping it as an unproven research hypothesis,
not adding it to A24/B34, retraining, selecting a model or claiming improved
exact-three accuracy. The 70% goal remains unmet.

This is a descriptive historical diagnostic of the admitted May 1-October 11,
2026 corpus, not a prospective registration or independent model evaluation.
The rules and implementation were committed at
`f8aa2b562f5e075e0ed4c04255c108d997ec2ed6` before this computation. They
were not fixed before the historical races or the earlier corpus investigations.
The [future protocol draft](2026-10-20-condition-preregistration-draft.md)
remains a draft: actual dates, race IDs, rosters and N are UNSET; the execution
registry remains empty. No fits, model inference, outcome collection, API calls
or changes to frozen M0/API27/A24/B34 artifacts occurred in this analysis.

## Evidence and fixed method

The [source time audit](2026-10-20-longitudinal-time-operands.md) explains original
official sources, provenance and the one cumulative-clock conflict. Its pinned
report is `experiments/2026-10-20-longitudinal-time/report.json`, SHA256
`2ff4ef525c33a6f83e5aa2ecc9f14c9d5942f103386b34d2e4007f4fda1e6f7a`.

The [complete result](experiments/2026-10-20-time-repeatability/report.json)
has SHA256 `c3ff4a7e71463bf753d7773192327f6746055a9a948c778e81cf9a09203b16eb`.
The run began at `2026-10-20T19:17:06.927296Z`, using Python 3.13.13;
implementation SHA256 is
`9898ecaeab601fc919cf2930c9f86343214e2ec173ee125c40730365fac14764`.
Exact rational values, every selected prior, reference membership, missingness
and all subgroup/month diagnostics are retained in that JSON.

For checked total time T, distance D and final-600m time L, use `600*T/(D*L)`
minus the median of that ratio over all admitted members of the same race,
including the focal record. Require at least three members and a valid ratio
for every admitted member. This is not necessarily the full original field.
The current-race median is deliberately contemporaneous descriptive data,
**never a future pre-race feature**. Rank fraction is `(rank-1)/(field_size-1)`;
lower is better. Faster relative closing speed has a larger ratio, but this
ratio also depends on whole-race speed and is not an absolute ability measure.

Select the most recent structural prior for the same horse, physical venue and
exact distance, 1-180 days earlier. Choose before checking measurements; never
replace an unavailable nearest prior with an older usable one. Same-day/future
records are ineligible; tied latest dates would be ambiguous. No filtering on
grade, confidence, observed outcome or source tier is added.

## Population and unavailable observations

All **11,523 admitted horse-start rows**, **1,156 races**, and **3,275 horses**
remain in the ledger. These are not all raw starters or a complete national
history. Source tiers remain 9,184 dual-supported and 2,339 HTML-only rows.

| Pair state | Rows |
| --- | ---: |
| No structural prior | 6,350 |
| Both measurements unavailable | 1,993 |
| Current measurement unavailable | 8 |
| Prior measurement unavailable | 6 |
| Complete pair | 3,166 |
| Total | 11,523 |

Ambiguous latest dates: zero. The complete pairs represent **1,584 horses**
and **612 current races**; they are dependent horse-start pairs, not 3,166
independent races or successful predictions. No-prior records also retain their
own measurement status; a no-prior label does not imply a usable measurement.

Current reference quantities are usable for 7,684 rows and unavailable for
3,839. The latter comprise 3,399 Jeju rows with unverified endpoints, 184 rows
with unrecognized layouts, 245 unsupported-venue rows, and all 11 members of
`20260703_3_6`. One original conflicting clock in that last race withholds its
whole reference, including ten otherwise readable rows; the race is not removed.
The invalid reference also withholds six later pairs using it as nearest prior.
No clock is repaired or imputed. This leaves 3,166 complete pairs rather than
the preceding inventory's 3,179 records having any usable prior: these are
different matching/reference definitions, not a revision of that inventory.

## Associations on the same complete pairs

All three fixed Spearman statistics use average ranks for ties on the identical
3,166-pair set. Undefined associations are null, never zero.

| Association | Spearman rho | Descriptive 95% horse-cluster interval |
| --- | ---: | --- |
| Prior relative closing speed vs current relative closing speed | 0.3012 | [0.2641, 0.3369] |
| Prior rank fraction vs current rank fraction | 0.2870 | [0.2512, 0.3223] |
| Prior relative closing speed vs current rank fraction | -0.0741 | [-0.1121, -0.0359] |

The last negative sign means higher prior relative closing speed is weakly
associated with a better subsequent rank. The first correlation is recurrence
of a measurement, not predictive accuracy. Comparing these three numbers does
not show added information beyond rank/history, causality, or an improvement
in exact-three selection. There is no fitted or selected predictive model here.

Intervals use 1,000 whole-horse cluster draws, seed 20261020, inclusive linear
percentiles; all 1,000 draws are defined for each statistic. Every pair of a
sampled horse is retained together. Shared race, weather, calendar and cross-horse
dependence remain unresolved. The nominal intervals are descriptive and must
not be treated as calibrated future-performance confidence intervals or a
multiple-testing-controlled significance claim.

## Sensitivity and non-generalization

All 30 venue/distance groups are in the JSON, including zero-pair groups.
Only 13 have complete pairs. For prior speed vs current rank, those correlations
range from -0.2544 (Seoul 2,000m, only 26 pairs) to +0.0620 (Seoul 1,000m,
66 pairs). Seoul 1,200m is near zero (-0.0031, 493 pairs). These exceptions
prevent a uniform-distance claim; small-group extrema are not feature-selection
criteria. Jeju and unsupported-venue absence is unknown applicability, not zero
predictive value. Grade-specific effects are not estimated by this fixed study.

| Current month omitted | Complete pairs | Pace recurrence | Rank recurrence | Prior pace / current rank |
| --- | ---: | ---: | ---: | ---: |
| May | 3,043 | 0.2930 | 0.2776 | -0.0741 |
| June | 2,623 | 0.2991 | 0.2844 | -0.0894 |
| July | 2,455 | 0.2997 | 0.2765 | -0.0714 |
| August | 2,321 | 0.3032 | 0.2998 | -0.0861 |
| September | 2,638 | 0.3171 | 0.2964 | -0.0619 |
| October through the 11th | 2,750 | 0.2968 | 0.2891 | -0.0639 |

These delete current-month observations only; earlier histories of retained
observations are not deleted or reselected. They are overlapping sensitivity
summaries, not six independent temporal validation folds. May is left-censored
by corpus start and October is a partial month. Source snapshots and semantic
guide evidence were collected after these historical races; availability before
each historical target is **not verified**. No October 16-18 outcome is loaded.

## Verification and next hypothesis

Share with caveats as a historical measurement diagnostic only. Synthetic tests
cover unavailable latest priors, date boundaries, ambiguous dates, exact ratios,
ties, all-member references, whole-horse resampling and immutable source pins.
An independent local checker at
`.cache/autoresearch/time-repeatability/independent_check.py` used a SQLite
temporal self-join and NumPy 2.5.1 ranks/correlations/linear quantiles, without
importing the implementation (checker SHA256
`e31788490a546c29e9eea2144edc55c6818f6daffbd1dbd24926b0ee12a29d88`).
It reproduced every row/reference and prior,
all 30 group and six month summaries, and the 1,000-draw intervals to 1e-12.
This verifies calculations on the same source, not original source truth or PIT.
The seven historical audit suites pass together: 256 tests, including 31 for
this module; Ruff lint and formatting checks pass. No dependency was added.

The remaining research question is whether an independently fixed,
pre-race-available history-only version adds conditional value beyond prior
rank and distance/grade context. Current results do not answer that question.
Do not tune more definitions on these pairs, promote a favorable distance, or
alter A24/B34. Any later development study needs a separately fixed method and
availability audit; any actual improvement claim needs a new, separately
approved future protocol and complete-population evaluation. The pending
future schedule and existing preregistration draft remain unchanged.
