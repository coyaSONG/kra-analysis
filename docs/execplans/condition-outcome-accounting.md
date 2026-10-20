# Prepare A24/B34 whole-population outcome accounting

This living ExecPlan follows `.agent/PLANS.md`. It implements the accounting
part of the unactivated proposal in
`docs/research/2026-10-20-condition-preregistration-draft.md`. A24 and B34 are
stored models with exhausted training allowances. No training or study
registration is permitted by this plan.

## Purpose / Big Picture


The prospective comparison must retain failed predictions and unresolved
results without turning missing results into misses. A separate, pure
calculation module will make the proposed arithmetic executable on synthetic
evidence. It must not change the historical M0/API27 evaluation contract.
This is the first independently testable milestone toward a read-only
prospective evaluator, not that evaluator's activation.

## Progress


- [x] (2026-10-20) Read the preregistration proposal and existing result/scoring code.
- [x] (2026-10-20) Implement normalized-evidence accounting and 65 synthetic tests,
  including 80 nonempty paired count tables within one test.
- [x] (2026-10-20) Focused and historical regression tests: 184 passed in 6.41s.
- [x] (2026-10-20) Ruff lint/format and diff whitespace checks pass; repeat test
  run passes 184 tests in 6.62s. Stored A24/B34 and M0/API27 commitment hashes
  match their published pins.
- [x] (2026-10-20 14:14Z) PR118 normally merged as
  `51ef5733fa1b0a60eaecad54afeedb2602c86c69`; required Python checks passed.
  The nonrequired security scan retained the same 17 dependency advisory rows
  as the preceding baseline, not an all-green CI result.
- [x] (2026-10-20 14:39Z) Follow-up Pro consultation completed; code inspection
  and four synthetic cases separate current runtime/local failures from
  archived publication. Added explicit observer finality assertions.
  Recorded the proposed evidence and population contract in
  `docs/research/2026-10-20-condition-evidence-boundaries.md`.
- [ ] Publish and normally merge the evidence-boundary tests and draft clarification.
- [ ] Later milestone: implement raw-evidence replay and append-only umbrella
  completeness ledger, then separately review before prospective registration.

## Surprises & Discoveries


`local_m0_evaluation.classify` counts a missing prediction with a known target
as a miss, but treats unverified publication as pending. It is not the proposed
A24/B34 classifier and must remain unchanged. The result observer's
`void_reported_no_top3` is a report of void text, not proof of settlement
finality. A future adapter must retain that distinction.

`verify_local()` depends on current runtime/approval and local failure
markers, while archived publication replay can still establish original
public bytes after that gate fails. Four synthetic counterexamples reproduce
this distinction. One local attempt also does not establish absence across
arbitrary publication PRs or clones; the accepted submission slots need
prior binding and complete source-backed closure.

## Decision Log


- Decision: implement a pure internal reducer with no CLI, filesystem,
  network, training, publication or registration entry point.
  Rationale: arithmetic can be tested before schedules and evidence bindings
  exist, but normalized states alone cannot certify authenticity.
  Date/Author: 2026-10-20 / Codex.
- Decision: absent prediction evidence defaults to pending, not proven failure.
  Rationale: inaccessible artifacts do not prove a missed prediction.
  Date/Author: 2026-10-20 / Codex.
- Decision: preserve the current operating gate and build historical replay
  separately; reported void alone is not the new adapter's undefined target.
  Rationale: local loss/runtime drift does not prove original invalidity, and
  blank HTML plus API void text does not prove a whole-race no-target decision.
  Record original evidence and add separate admission policy rather than
  rewriting old M0/API27 observations.
  Date/Author: 2026-10-20 / Codex after completed Pro review.

## Outcomes & Retrospective


The first milestone passes 65 new tests and 119 existing regressions. Unknown
prediction evidence stays pending, proven prediction failures require a unique
target before becoming misses, and partial-arm failures retain the other arm.
The overall 70% objective remains unmet. These synthetic tests cannot
demonstrate pre-race availability or population completeness.

PR118 is merged. Follow-up validation passes 188 tests and documents stronger
evidence requirements without changing runtime code or registering any race.
Historical replay, submission closure and umbrella completeness remain
unimplemented activation blockers; the consultation is not execution approval.

## Context and Orientation


`packages/scripts/autoresearch/versioned_result_observations.py` replays
official/API observations. `local_m0_evaluation.py` owns the older contract.
`condition_forward.py` performs frozen inference/publication but does not
evaluate prospective outcomes. The new `condition_outcome_accounting.py`
accepts already-normalized evidence; it does not read any of those artifacts.
An evidence adapter is future code that checks original hashes, source
identity, clocks, public existence and linked correction versions before
calling this module. An umbrella ledger is the complete multiweek enrollment
record, including late additions and weeks where inference could not run.

## Plan of Work


Milestone one adds immutable normalized prediction/outcome values, left-joins
both arms to an explicit race universe, classifies every row and reports
counts, paired cells and conditional full-universe rates. Unknown states,
duplicate IDs, extra evidence IDs and malformed triples fail closed.
Unverified population suppresses rates and row-level hit/miss verification.
Pending results dominate prediction failures; undefined targets remain
undefined. Each arm is counted separately. No model is selected or promoted.

Milestone two, a later separately reviewed change, must replay actual
publication evidence and versioned results, bind them to original population
and model pins, record missing weeks and late-added races without modifying
execution protocols, and emit append-only reports with correction ancestry.
It must not trust caller-supplied state labels as proof. Approval remains
empty and actual dates remain unset until schedule evidence and all gates
are available. Neither milestone authorizes real inference or fitting.

Before that implementation, retain the counterexamples in
`test_condition_forward.py` and the observer assertions in
`test_versioned_result_observations.py`. Follow the evidence contract's original
snapshot, closed publication slots, explicit no-target decisions and physical
race identity requirements. The four publication tests intentionally do not
call an outcome evaluator or claim a hit. Complete historical validation needs
its own tests for current-checkout independence and evidence loss never
creating a proven failure.

## Concrete Steps


Work in the isolated research checkout. Add the module and tests under
`packages/scripts/autoresearch/`. Run:

    env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts .venv/bin/python -B -m pytest -q -p no:cacheprovider packages/scripts/autoresearch/tests/test_condition_outcome_accounting.py packages/scripts/autoresearch/tests/test_condition_forward.py packages/scripts/autoresearch/tests/test_local_m0_evaluation.py packages/scripts/autoresearch/tests/test_versioned_result_observations.py

Run Ruff lint/format checks and `git diff --check`. The local environment has
no Black executable; current repository CI uses Ruff formatting. Publish a small conventional
commit, inspect required branch checks and merge normally without bypass.

## Validation and Acceptance


Synthetic tests must cover every prediction/outcome state combination,
unordered triples, partial-arm failure, empty and incomplete populations,
left-joined missing evidence, unknown/extra IDs, conservation of per-arm and
paired totals, correction replay without mutation, and no subset accuracy.
Reports must label their scope as normalized-input arithmetic, not verified
prospective evidence. Existing inference and M0/API27 tests must still pass.
No real schedules, API collection, predictions, fits or registry changes are
part of acceptance.

## Idempotence and Recovery


The reducer performs no I/O and mutates no inputs. Calling it again with the
same values yields the same report. A different outcome version yields a
separate return value, never rewriting the original. No shared attempt ledger
or frozen model is touched. If tests fail, fix only the new module/tests;
never reset user changes or retry training.

## Artifacts and Notes


The preregistration proposal remains a draft. Do not claim that this milestone
satisfies its raw-evidence, completeness-ledger or separate-review gates.

## Interfaces and Dependencies


Use Python standard-library frozen dataclasses and counters, plus the existing
canonical race identity validator. Define `PredictionEvidence`,
`OutcomeEvidence`, and `summarize(race_ids, predictions, outcomes,
*, full_population_verified)`. Predictions contain exactly A24/B34 mappings;
missing race keys are unknown evidence. Triples contain three distinct
numeric horse-ID strings with the source's zero-padding preserved. A caller must check roster membership,
source integrity and timeliness before constructing a timely-valid state.

Revision note: initial plan separates testable accounting from evidence replay
so development cannot accidentally register or score an unverified study.
Validation update: the first local run passed 184 tests; use the actual CI
Ruff formatter rather than the unavailable Black executable.
Evidence-boundary update (2026-10-20): recorded PR118 merge and completed Pro
review, added four passing publication counterexamples and observer assertions,
and made the remaining historical/closure/population gates explicit. This
prevents a later adapter from treating an operating-gate failure as an outcome.
