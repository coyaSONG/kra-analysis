# October 16-18 Full-Block Paired Results

## Complete Frozen Population

The unchanged PR95 evaluator has now verified all 50 original races. Each arm
made exactly one unordered three-horse prediction per race before the block
cutoff. The original predictions, models, inputs and population are unchanged.

| Model | Verified hits | Verified misses | Pending | Undefined target | Exact accuracy |
| --- | ---: | ---: | ---: | ---: | ---: |
| M0 | 0 | 50 | 0 | 0 | 0% |
| API27 fixed v1 | 0 | 50 | 0 | 0 | 0% |

The API27-minus-M0 difference is **0 percentage points**. Paired counts are
both hit **0**, M0 only **0**, API27 only **0**, neither **50**. The models tie
on this block; neither performed better on the required exact-combination
metric. This does not establish equal predictive ability in general.
No model is promoted and the 70% research goal remains unmet.

There are 50 races in one three-day block, not 50 independent weeks. A nominal
two-sided 95% exact binomial interval for each arm is approximately 0-7.11%,
assuming independent, identically distributed Bernoulli outcomes. Within-week
dependence and future distribution shift are not covered by that interval.
The evaluator's [0, 0] evidence-identification bounds indicate no missing
binary outcomes; they are not a confidence interval.

This is a complete evaluation of the currently selected official observation,
not a claim that future official corrections are impossible. A correction
must create a new source/evaluation version and an explicit comparison.

## Capture And Identity

Archive: `.cache/autoresearch/forward-outcomes/20261018T094903.670114Z`.
The fresh 09:49 UTC schedule capture confirmed 17 October 18 races and all
scheduled starts had elapsed. Four schedule requests, three API214 result
requests and one API26 identity-support request were made, without retries.
All four API requests returned HTTP 200. Official evidence used 17 new detail
pages plus the existing collector's 12 regional list pages. Previous 33
detail receipts and previous result bytes were reused, not recollected.

Yeongcheon's API214 payload had 66 rows but omitted venue identity. Its
original `identity_unresolved` / `missing_result_venue` capture remains intact.
The unchanged PR95 entry-roster binding verified all 66 identities across six
races. An offline check against the earlier archived entry also passed, but
moving that entry manifest into the replay bundle violated its path contract.
No path validation or original manifest was patched. Instead, the collector's
existing entry-support mechanism captured one new entry snapshot under the
correct archive root, within the original four-request budget. Receipt 0002
adds that evidence while receipt 0001 and the collection error remain intact.
This post-race entry is identity support only, never a pre-race feature input.

All 50 unique race IDs and complete rosters reconcile under the original
outcome policy, including lower-rank/time observations and unique top-three
targets. The new Seoul race 6 API note is one withdrawal (`출전취소`); it does
not remove the race or the registered horse from the frozen population.
Previously documented exclusions/running-stop notes are preserved. A blank
HTML rank/time alone is not independent proof of an API exception reason.

Every old October 16-17 ledger row equals its previous observation exactly.
The day-two 0/33/17/0 report is retained; this version adds 17 verified misses
per arm, with no revisions to the prior 33. Both public prediction hashes and
the original training-input commitment remain unchanged. The evaluator
verified 100 pre-cutoff published packets and original publication witnesses.

## Failure Diagnosis

Only the pre-outcome PR102 matrix and original pinned entry pages supply
diagnostic features, distance and grade. All 534 race/horse feature keys are
unique and all 150 observed top-three appearances join successfully. This
does not by itself certify historical source availability for future fitting.

| Venue | Races | Top-three appearances without recent similar history | Races with history for all three |
| --- | ---: | ---: | ---: |
| Seoul | 21 | 26 / 63 | 7 |
| Jeju | 14 | 12 / 42 | 5 |
| Busan | 9 | 8 / 27 | 3 |
| Yeongcheon | 6 | 14 / 18 | 0 |

Overall, 60 of 150 top-three appearances lack recent similar history. Both
models also missed all 15 races where all three had such history. Therefore
missing history alone cannot explain the failures. Yeongcheon has a clear
support gap, but its six races do not identify a causal venue effect.

Distance groups have 2-15 races; grade groups have 1-11. Five of 15 1200m races
and three of ten 1400m races have history for all three, yet still fail. Five
of 11 domestic class-6 races have that support, compared with two of nine
domestic class-5 races. These overlapping, small strata are diagnostic only;
none replaces the full-population score or supports a tuned threshold.

The models chose the same combination in 35 races and different combinations
in 15. M0 shared exactly two horses with the target in 23 races, one in 22,
and none in five; API27's corresponding counts are 21, 23 and six. All remain
exact-combination failures. Partial overlap is not an alternative success
metric or evidence to promote M0.

Retain the same-learner, same-cohort base-versus-condition-support hypothesis,
including fallback/support counts. Also inspect full-set ranking errors in
the 15 supported races. Before fitting, audit feature availability at each
original cutoff, source hashes, missingness and join coverage. Historical
event dates alone are insufficient. Do not fill old features with today's
post-race snapshots or repeatedly tune these 50 races. No fit or training
approval occurred here. Any candidate learned or selected from this block
must be validated on a separately preregistered future complete population;
this block cannot serve as its independent validation again.

## Verification And Next Work

The M0, paired evaluator and versioned-observation source files were
byte-compared with PR95 commit `2d78a164e10de0a0249ae8a1968c475295cb5fcc`.
The original suites passed **84 tests in 7.34 seconds**. An offline companion
replayed the outcome plan, independently reconstructed unordered target sets,
checked all prediction comparisons and verified the sealed matrix hash.

Local orchestration: `.cache/autoresearch/collect_day_outcomes_20261018.py`,
`resume_day_outcomes_20261018.py` and `diagnose_day_outcomes_20261018.py`.
The collection entry point refuses a second October 18 run. Do not rerun
collection to replay evidence; output files are append-only. Raw caches and
credentials are excluded from this documentation change.

| File | SHA256 |
| --- | --- |
| outcome-plan.json | bb122ca93d14c56e7fe6bba969fe1df0c5add72c09b135ced8f8e949cd2834e0 |
| outcomes.json | 0cf7be483e1089ba55db78f70c51c9a6dbcaf8738847460f469ee11901ac0cbb |
| paired-evaluation.json | efb7418f8a969844679393b1178c9ff169d2624e036c99374e8bf6dd7aa6ab3f |
| condition-diagnostic.json | 74a4959370c68070afdd1cefc8c9fd34f71f5b539839402f522fef2e3e918390 |
| identity-binding.json | 1c3cf01fd088da1ada6afa50278e8daf3fb71be0a9e04373a05f2506d87fbedb |
| import-lineage.json | c88d57ad8f41ae088b6480c8ceb019819510115c4314329ad3c5fa1b66a31795 |

Stop routine result and entry recollection for this completed block. Collect
a new result version only upon a correction/conflict signal. Continue the
historical-availability audit and condition research before selecting a new
candidate or registering a future evaluation. Do not reset this population,
silently advance dates, automatically promote an arm, or mark the 70% goal
complete merely because this block's evaluation is complete.
