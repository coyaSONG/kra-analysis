# October 17 Paired Results: Provisional

## Full Frozen Population

The unchanged PR95 evaluator now has result evidence for 33 of the original
50 races on October 16-18. This adds October 17's 17 races without replacing
the day-one observation, inputs, predictions, models or population.

| Model | Verified hits | Verified misses | Pending evidence | Undefined target |
| --- | ---: | ---: | ---: | ---: |
| M0 | 0 | 33 | 17 | 0 |
| API27 fixed v1 | 0 | 33 | 17 | 0 |

The 17 pending races are October 18 races; their target definition is also
unknown, not established as undefined. They are not failures or cancellations.
Full-population exact accuracy, percentage-point difference and full paired
counts remain null. Both models missed all 33 observed races, but no final
winner or full-block tie is established. A subset accuracy does not replace
the required whole-population metric.

This is still a small, incomplete block. Diagnostic strata are smaller still,
and official finality has not been established. No full-block confidence
interval or promotion is justified. The 70% goal remains unmet.

## Capture And Integrity

The 09:14 UTC schedule capture and entry-API check found no further changes.
All October 17 starts had elapsed and the existing 18:10 KST collection gate
had passed. Result collection used three API214 calls for Seoul and Jeju,
then 17 new official detail pages and 12 official list pages. There were no
retries, future-date result requests or overlapping collectors.

The new derived replay bundle reuses October 16 raw API results and all 16
official detail receipts byte-for-byte. New API receipt wrappers bind those
unchanged results to the combined replay plan; import-lineage.json preserves
their original receipt hashes and source clocks. This is not a new
preregistration or a backdated capture. The old archive remains unchanged,
and every October 16 replayed ledger row equals its previous version exactly.

Both sources reconcile all 33 observed rosters and unique top-three targets,
including relevant lower-rank/time observations under the original policy.
The frozen scheduled-roster baseline remains unchanged even where a later
schedule reported fewer starters. Seoul race 3 has an API running-stop note;
Seoul race 4 has an API exclusion note. These do not remove races or registered
horses from the frozen population. The policy still defines unique top-three
targets. A blank HTML rank/time alone is not independent proof of an API
exception reason. The previously documented Busan race 8 exclusion is retained.

The runtime is extracted from PR95 merge commit
`2d78a164e10de0a0249ae8a1968c475295cb5fcc`. The imported M0 evaluator, paired
evaluator and outcome-policy module were byte-compared with that commit.
All 50 unique race IDs, 100 pre-cutoff published prediction packets, input
and model commitments, source clocks and archived publication witnesses
passed the original evaluator. No policy or hash constant was patched.

## Condition-History Diagnosis

The offline diagnosis joins only the pre-outcome sealed PR102 matrix and
original pinned entry pages by race and horse identity. Distance and grade
come from those original pages, not updated post-race cumulative statistics.
The matrix SHA256 remains
`7277897731011c64706f427cd7733444a5450767d312dabe8293a67c35a788a1`.

| Venue | Observed races | Top-three appearances lacking recent similar history | Races with similar history for all three |
| --- | ---: | ---: | ---: |
| Seoul | 10 | 12 of 30 | 4 |
| Jeju | 14 | 12 of 42 | 5 |
| Busan | 9 | 8 of 27 | 3 |

There are 32 fallback appearances among 99 observed top-three appearances.
However, both models also missed the 12 races where all three had similar
history. Missing history alone cannot explain the failures. October 17 adds
20 fallback appearances among 51 and six all-supported races. No Yeongcheon
result evidence exists yet.

Distance strata contain 1-9 races and grade strata 1-8. For example, the
single 1700m race has three fallback appearances, whereas four of nine 1200m
races have similar history for every top-three horse. These are descriptive
support diagnostics, not evidence of a superior segment or thresholds to tune.
Venue, distance and grade effects cannot be separated from these small,
overlapping groups.

Retain the prior hypothesis: compare the same learner and cohort using base
features versus similarity-support/fallback features, including missingness
and support counts. Historical event dates do not prove feature availability;
audit source availability, missingness and joins before approving a fixed
training set. Do not add manual bonuses or repeatedly tune this block.
There was no fit, new training approval, new arm or promotion in this update.
Any model trained or selected using these outcomes must be evaluated on a
separately preregistered future full population, not this block again.

## Evidence And Reproduction

Local archive: `.cache/autoresearch/forward-outcomes/20261017T091609.128006Z`.
Raw sources, collection clocks, receipts, hashes and missing statuses are
preserved. The previous day-one report remains a separate observation.

| File | SHA256 |
| --- | --- |
| outcome-plan.json | 8174a4dcd1934018d5eb56c67f775f2135b06d35203d2cc2d427248068da7531 |
| outcomes.json | 8ff1574685d4d9366315e847568e3db3a59c10623b70b6681511157d85fbbe59 |
| paired-evaluation.json | f672009d61fe01b75cab0517d51dba25d99e104f34a075dc2320e1afde974c53 |
| condition-diagnostic.json | b693e8a911cab42bcaf34dcb2656761c8ea7e9db76d121cf541d02cf440d1db6 |
| import-lineage.json | 78ac7ed1c35ec7694d221ff90b7177f1acaabecb948e75b25b1eff585ca3742c |

Local orchestration is in `.cache/autoresearch/collect_day_outcomes_20261017.py`
and `.cache/autoresearch/diagnose_day_outcomes_20261017.py`. Reproduce offline
with the latter and the pinned PR95 runtime; do not recollect to replay.
It reproduces outcomes, reconstructs top-three sets from API ranks, checks
the matrix and original runtime, and validates the complete universe.
The original M0 evaluation, API27 forward and versioned-result suites passed
84 tests. The original public M0/API27 and training-input hashes are unchanged.
Raw caches and secrets are not part of this documentation change.

Next result collection is gated at October 18 18:10 KST, after the latest
currently observed 17:55 start; recheck the schedule before collecting.
Do not repeat completed-day collection absent a correction signal. Continue
bounded entry monitoring only for October 18. Corrections require new source
versions and a new evaluation with an explicit difference from this report.
