# Historical form: more history did not improve the fixed 90-day rule

## Result And Decision

Executed five non-fitting predictors on all **671 archived races and 6,816
runner appearances**, producing **3,355 single-three-horse selections**. Adding
June HTML history changed 395 combinations but gained 15 matches and lost 15:
the original and expanded 90-day rank rules each matched 28 observed outcomes.
The 180-day rule matched 29, a net difference of one, not evidence for promotion.

This is a **late-captured retrospective diagnostic on result-derived rosters**,
not a pre-race backtest, newly trained model, untouched holdout, or 70% claim.
It does not compare these rules with frozen M0 on a common eligible population
and cannot establish which deployed model is best. No fitting, parameter search
or promotion occurred. Do not keep tuning the same outcomes until something wins.

## Fixed Design

Input pins and five recipes were committed as `d856fbd` before first execution.
Protocol: `data/contracts/history_form_exploration_v1.json`, SHA256
`c4a1173a7883f11e60a9234160c8c231cb0a2e730479607f84dac766f77225a9`.
Targets are the entire original July 12-October 11 seed. Prior sources are that
seed, July 5-11 dual-supported history and June 1-July 4 HTML-only history. Each
source is revalidated from raw bytes, not trusted coverage totals.

| Arm | Fixed rule |
| --- | --- |
| gate | History-free reference: lowest gates, then numeric horse ID |
| dual90 | Prior normalized rank, API/HTML-supported observations, 90 days |
| expanded90 | Same rank formula/window, adding HTML-only observations |
| expanded180 | Same formula using available observations within 180 days |
| top3_90 | Smoothed prior top-three frequency with expanded90 observations |

For prior observed roster size n and rank r, rank contribution is `(n-r)/(n-1)`.
The full prior roster, including unresolved lower rows, determines n; it is not
actual starters, speed, empirical percentile or opponent strength. Contributions
require `n >= 2` and `1 <= r <= n`. No invalid rank/size rows occurred in this run.
Source-conflict races cannot supply numeric history. Duplicate history identities
and overlapping source race inventories fail instead of being double-counted.

With m priors, rank score is `(sum(contributions)+1)/(m+2)`. Top-three score is
`(sum(rank <= 3)+0.6)/(m+2)`. Its fixed prior mean 0.3 is not a measured base rate
or calibrated probability. Pro later suggested 0.5; we retained the already
committed 0.3 rather than change a recipe after results. Unknown lower statuses
are not invented failures. Neither score is a calibrated prediction probability.

History dates must lie in `[target date-window, target date)`, excluding the
entire target day across venues. Earlier target outcomes may enter later target
histories under this fixed rule, but their captured versions' historical
availability remains unproven. Exact fractions determine score ordering, followed
by gate then numeric horse ID. Each arm supplies one unordered combination;
arms are never pooled. No-history scores are 0.5 and 0.3 respectively. Missing
history never removes a runner or forces a whole-race fallback. A no-history
runner can outrank one with a poor observed result; this rule was not retuned.

## Complete Outcome Ledger

The existing versioned `observe_race` logic checks identity, complete observed
API/HTML roster agreement, unique ranks 1/2/3 and rank/time conflicts. Its count
argument here is archived roster size, **not independently verified scheduled
runners**. This wrapper does not claim a national schedule population.

There are 613 unique observed top-three outcomes, 55 missing official event
observations, two unresolved top-three mappings, and one reported void. Every
arm retains 57 pending and one undefined slot. All selections were generated;
execution failures are zero. The 616 confirmed event identities are not 616
scoreable outcomes. No resolved-only accuracy is emitted: success rate is null.

| Arm | Archived races | Matches | Mismatches | Pending | Undefined |
| --- | ---: | ---: | ---: | ---: | ---: |
| gate | 671 | 10 | 603 | 57 | 1 |
| dual90 | 671 | 28 | 585 | 57 | 1 |
| expanded90 | 671 | 28 | 585 | 57 | 1 |
| expanded180 | 671 | 29 | 584 | 57 | 1 |
| top3_90 | 671 | 28 | 585 | 57 | 1 |

| Candidate versus dual90 | Both match | Only dual90 | Only candidate | Neither match | Not comparable | Changed combinations |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| expanded90 | 13 | 15 | 15 | 570 | 58 | 395 |
| expanded180 | 13 | 15 | 16 | 569 | 58 | 474 |
| top3_90 | 8 | 20 | 20 | 565 | 58 | 533 |

The five outcome-status columns sum to all 671 races; combination changes include
unresolved slots. Top-three frequency matched 14 September outcomes versus
dual90's 8, but only 2 October outcomes versus 6. This is descriptive variation,
not permission to switch rules after seeing each month. Repeated horses and
shared dates are not independent validation samples. Gate order is a simple
history-free reference, not a random chance baseline or a significance test.

## Mechanism Diagnostics

| Diagnostic | dual90 | expanded90 | expanded180 | top3_90 |
| --- | ---: | ---: | ---: | ---: |
| Runner appearances with no eligible prior | 2,381 | 1,098 | 1,037 | 1,098 |
| Runner appearances with at least three priors | 630 | 1,519 | 2,012 | 1,519 |
| Selected appearances without history | 481 | 150 | 149 | 272 |
| Races tied at third/fourth score boundary | 258 | 140 | 120 | 312 |

Extra data reduced sparsity and ties without increasing expanded90 matches.
Lack of any score change is therefore not the explanation for zero net gain.
This does not prove that history is uninformative or no model can improve.
These particular unconditional summaries did not show a useful net gain here.

All October 3 onward dual90/expanded90 score rows and selections are equal:
June 1-July 4 is outside their 90-day windows. Through August 30, expanded90 and
expanded180 outputs are equal because available history starts June 1. Both
invariants passed on actual data. The 180-day arm uses available observations
inside a calendar window, not a complete 180-day history. Additional observations
and weaker shrinkage change together; this experiment does not separate them.

## Reproduction And Validation

From `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf`:

```sh
PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.history_form_research \
  --plan data/contracts/history_form_exploration_v1.json \
  --plan-sha256 c4a1173a7883f11e60a9234160c8c231cb0a2e730479607f84dac766f77225a9 \
  --output-dir .cache/autoresearch/history-form-research-20261013/new-replay
```

The first two runs produced identical prediction/report bytes. After completed
Pro advice, manifests and tie/fallback diagnostics were added without changing
formulas. Direct comparison verified every score, prior ID/tier and selection
identical to the first run. Original artifacts remain intact. Their outcomes
had already been inspected before this diagnostic-only addition.

Final artifacts below `.cache/autoresearch/history-form-research-20261013/run-3`:

| Artifact | SHA256 |
| --- | --- |
| targets.json | `814d42e0d74b607986235f332fa8466203755e550fb691fd55d74714633ebb03` |
| history.json | `06703c30ac143a520b8249c3840964fb5bcd52d176b85a03a2940bfe1292e04f` |
| predictions.json | `123c3d5ae22f635fb3163990f4ecd96110f8805125c37d5b9963d70a957af40a` |
| report.json | `a59b05e8c7668544c6ff703a79f3cb64a63314a3079f756ded7a6936f56f6b4d` |

The identity manifest and 8,994-row history view are saved before prediction;
predictions are saved before outcome comparison. Source and implementation
hashes bind the artifacts. Raw data, derived rows and credentials stay local.
An independent calculation from history, not scorer-selected prior IDs, matched
all 34,080 scores and 3,355 selections. **261 related tests passed**, including
30 new tests; Ruff passed. Cases cover dates, label isolation, full prior roster
normalization, fallback, duplicate/source overlap, ambiguous/void outcomes,
execution failures, raw tampering, repeat equality and exclusive saving.

## Pro Advice And Next Hypothesis

The authorized [Pro consultation](https://chatgpt.com/c/6aca2dc4-d2e8-83e8-acab-e85f281c27b7)
completed without interrupted generation. It reviewed public PR91 and our design,
not the new local implementation or outputs. It supported the narrow non-fitting
experiment and emphasized source boundaries, no post-result tuning, manifests,
date-span invariants and fallback/tie diagnostics. These safeguards were adopted;
Pro did not independently validate local results or grant training approval.

The next hypothesis is **comparability of previous race conditions**, initially
distance and class context, not another window search. Establish field semantics
and time availability, review a separate feature recipe, and capture new targets
before cutoff before any eligible fit. These results do not prove which extra
feature will help. Frozen M0/API27 and fit-admission reviews remain unchanged.
API recovery is not needed for local source-semantics and feature investigations.
