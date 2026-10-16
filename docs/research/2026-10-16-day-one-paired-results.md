# October 16 Paired Results: Provisional

## Full Frozen Population

The unchanged PR95 evaluator successfully compared the October 16 results
against the published M0/API27 commitments. The population is still all
50 races on October 16-18, not today's 16-race subset.

| Model | Verified hits | Verified misses | Pending evidence | Undefined target |
| --- | ---: | ---: | ---: | ---: |
| M0 | 0 | 16 | 34 | 0 |
| API27 fixed v1 | 0 | 16 | 34 | 0 |

The 34 pending races also have unknown target definition. They are not misses
and are not proven cancellations. Full-population exact accuracy, paired
counts and the percentage-point difference remain null. There is no final
winner or full-block tie claim. Both models missed the 16 currently evaluated
races; that observation is not a substitute subset success metric.

This is one day's evidence, with small diagnostic groups and no verified
official finality. No full-block confidence interval is reported. Later
corrections require a new source capture and versioned evaluation; never
overwrite this observation. The 70% goal remains unmet.

## Capture And Validation

The latest schedule was checked at 09:50 UTC, after all October 16 starts.
Four schedule requests and nine entry-API requests found no change since the
08:52 capture. Result collection then used three API214 requests for Jeju
and Busan, preserving 170 rows, followed by the existing official collector's
16 detail pages and 12 list pages. No future result date was requested, no
retry ran, and a nonblocking process lock prevented overlapping collectors.

The original 50 identities and scheduled-roster baseline were retained.
Both result sources reconciled all 16 observed rosters, unique ranks 1-3 and
all relevant lower-rank/time observations. The remaining dates have no result
evidence. The original evaluator verified all 100 prediction packets as
published before cutoff, original inputs/models, whole-population membership,
source clocks and archived GitHub publication evidence.

The runtime is extracted from PR95 merge commit
`2d78a164e10de0a0249ae8a1968c475295cb5fcc`; the imported M0 evaluator, paired
evaluator and result-observation module were byte-compared with that commit.
No contract constant or policy was patched. Unlike the earlier intraday
attempt, this after-day capture passed the original capture-time checks.
The earlier unsuccessful evaluation remains preserved separately.

Busan race 8 retained all 11 registered rows, including gate 9, horse
`1412318`, whose API record says `경주제외` with code 94 and zero time.
Its official HTML row has blank rank/time. Those blanks alone do not
independently establish the exclusion reason. The remaining ten finishers
and unique top three agree across sources. The existing policy therefore
defines a top-three target, without removing this race or horse from the
frozen inputs. Neither prediction selected that horse. Both selected
`50884, 53053, 53895`; the observed set is `50884, 50975, 53895`.

## Condition-History Diagnosis

Only the pre-outcome sealed PR102 candidate matrix and original entry sources
were joined by race ID and horse ID. The matrix was not refitted or edited.
Distance and grade were read from pinned original API pages, not current
post-race cumulative statistics.

- Jeju: 7 observed races; 4 of 21 top-three appearances lacked recent similar
  history. Busan: 9 races; 8 of 27 lacked it.
- Six races had similar history for every observed top-three horse but were
  still missed by both models. Missing history alone is not an explanation.
- Distance groups contain only 1-5 races each; grade groups only 1-4.
  These strata are descriptive, not evidence of a winning segment or a
  threshold to tune. There is no Yeongcheon result evidence yet.
- The models selected different combinations in four races. M0's overlap
  counts with the observed three were 2/1/0 in 8/5/3 races; API27's were
  7/6/3. These are error diagnostics only, not top-k success, a winner
  criterion, or the 70% estimand.

Retain the existing hypothesis: compare the same learner and training cohort
using the base features versus similarity-support/fallback features. Audit
historical availability and the approved training recipe before fitting.
Do not tune similarity thresholds, manual bonuses or shrinkage weights on
these 16 races. Once these outcomes are used for training or model selection,
this block is no longer independent validation for that selected model.
Any claimed improvement requires a separately preregistered future whole
population. No new arm, fit, approval or model promotion occurred here.

## Evidence And Reproduction

Local archive: `.cache/autoresearch/forward-outcomes/20261016T095148.759458Z`.
All raw API/HTML files, receipts, source clocks and hashes are preserved there.

| File | SHA256 |
| --- | --- |
| outcome-plan.json | 7716a92fd21790954b81f83eefb0c85cd49c05283285957b618404882177ccc5 |
| outcomes.json | ea65a25008bcf3f0aa8016010768403f960381a76de86e62948740415645789d |
| paired-evaluation.json | 15381ad4ae0a3cfbc059ea4ccd6e48c38939ce44c6c96acfd0f63655db3a619c |
| condition-diagnostic.json | 4f4603a23bb2f3097c7fbf94e1b4bead5c30f641e3c013c43ae1a35c20e62185 |

The local orchestration sources are
`.cache/autoresearch/collect_day_outcomes_20261016.py` and
`.cache/autoresearch/diagnose_day_outcomes_20261016.py`. Use the latter for
offline review; do not rerun collection just to reproduce existing evidence.
The result plan replays with `versioned_result_observations.replay_plan`;
the scorecard is produced by `api27_evaluation.evaluate` under the PR95
runtime and archived publication witnesses.

An offline replay reproduced the outcome report exactly, checked all 50
unique IDs and both arms' status counts, independently reconstructed each
observed top-three set from API ranks, and verified the sealed matrix hash.
The original runtime's M0 evaluation, API27 forward and versioned-result
test suites passed all 84 tests. Original public M0/API27 and training-input
commitment hashes remain unchanged. Raw caches and credentials are not
included in this documentation change.
