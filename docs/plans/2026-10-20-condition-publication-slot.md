# Bind prospective predictions to one reviewed publication slot

This ExecPlan follows `.agent/PLANS.md`. Keep Progress, Surprises & Discoveries,
Decision Log and Outcomes & Retrospective current.

## Purpose / Big Picture

Before a future A24/B34 attempt, bind the one accepted prediction publication
PR and document path into the separately reviewed protocol. An operator must
not choose a different publication PR after seeing its timing or contents.
This implements a necessary boundary from the existing evidence contract;
it does not prove that a missing publication was absent, close all submission
evidence, authorize a study, or change the 70% full-population objective.

## Progress

- [x] Read live admission, publication witness and historical archive replay.
- [x] Demonstrate that the current witness reaches replay for an unbound PR.
- [x] Add versioned prospective slot admission and reject mismatches before I/O.
- [x] Preserve historical v1 interpretation and verify v2 slot attribution.
- [x] Run focused and integration regressions (432 passed), Ruff and whitespace checks.
- [x] Verify both model, fit receipt, M0/API27 commitment and empty-registry hashes.
- [ ] Publish PR and inspect required checks; normal merge requires all checks passing.

## Surprises & Discoveries

The research checkout's local `main` was old; the new clean branch was
fast-forwarded to observed `origin/main` at 2f3f029. No original checkout or
pending PR branch was changed. The live witness currently takes any positive
PR supplied by the caller and verifies its bytes, without a prebound slot.
The empty actual execution registry permits a new live protocol version
without migrating any real study. Historical v1 archives still need replay.
The first combined run passed 180 tests but rejected 22 snapshot tests whose
shared fixture declared prediction PR 901 while archiving prediction PR 902
and approval PR 901. Fixed only that synthetic fixture to declare its actual
archive slot; the production identity check remains strict.

## Decision Log

On 2026-10-20 choose protocol v2 for new live admissions; retain v1 historical
interpretation. Add an exact repository/PR/document slot and a matching
review-record PR. Use the existing repository and deterministic paired-document
path, not a configurable external destination. Reject duplicate PR slots across
reviewed studies. Do not infer physical-race uniqueness from this uniqueness.

## Context and Orientation

`condition_forward_contract.py` admits reviewed protocols; `condition_forward.py`
computes, stages and witnesses predictions. `condition_forward_publication.py`
already checks GitHub repository, merge and document bytes. The historical
reader `condition_historical_publication.py` replays archived public evidence
independently of current runtime. Tests use temporary fictional studies; the
real `data/contracts/condition_forward_reviews_v1.json` must remain empty.

## Plan of Work

First add a regression that refuses another PR before numerical replay or
network capture. Then require protocol v2 with `publication_slot` containing
exactly repository, pull_number and document. A positive integer excludes bool.
The registry record binds `prediction_publication_pr` to the protocol and must
not reuse it or the protocol publication PR. Witness checks it before replay
and before capture; staged output identifies the accepted slot.

Historical v1 stays readable and reports that no slot was prebound. For v2,
read the original slot, check original approval binding and the selected
prediction archive's PR/path. No current runtime, live fetch or inference may
be used for historical attribution. Missing files remain pending; a chosen
wrong slot is a structural conflict, never a scored prediction failure.

## Concrete Steps

Work in the existing isolated research checkout on `codex/condition-publication-slot`.
Use apply_patch for edits. Run with the existing `.venv`, without installations:

    PYTHONPATH=packages/scripts PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider packages/scripts/autoresearch/tests/test_condition_forward.py packages/scripts/autoresearch/tests/test_condition_historical_publication.py packages/scripts/autoresearch/tests/test_condition_snapshot_replay.py

Run Ruff with `--no-cache`, whitespace checks, then compare original model,
receipt, M0/API27 commitment and empty-registry hashes. Only synthetic tests
may run inference; never execute actual stored models on real future inputs.

## Validation and Acceptance

Correct v2 slots complete the synthetic run/stage/witness chain. Missing,
malformed, wrong-repository/path, duplicate and mismatching slots fail before
reservation or witness capture. Wrong-PR witness requests must not call
numerical replay. Historical v1 remains unchanged; v2 reports original-slot
attribution only when matching archived evidence exists. Later missing copies,
runtime drift or lack of closure must not be turned into proven absence.
Fit traps and read-only historical tests must continue passing.

## Idempotence and Recovery

All actual models, protocols, reservations and registry bytes stay unchanged.
No migration or real publication-slot PR is created. Keep old evidence intact;
v2 is a new future contract, not retroactive v1 amendment. Failed CI is not
bypassed. PR132/133 security remediation is still pending and can block merge.

## Interfaces and Dependencies

Reuse existing Python, canonical JSON, publication witnesses and pinned model
interfaces. No package changes. The shared slot checker is pure, validates
identities only and has no Git, network or scoring side effects.

## Outcomes & Retrospective

Implemented prospective v2 slot admission and historical v1/v2 attribution.
Nine related test modules passed 432 tests in 41.73 seconds. Ruff lint and
format checks passed for all seven changed Python files; whitespace checks
passed. Frozen hashes matched their existing pins and no actual registry entry,
prediction, fit or schedule request was created. The earlier interrupted test
session's final output could not be recovered, so the final expanded suite was
run once against the completed code and its successful exit was observed.
Even after this boundary works, full submission
closure, umbrella admission and target admission remain necessary before
prospective evaluation. No dates, population, sample size or fit are approved.

## Artifacts and Notes

Initial plan recorded before code edits on 2026-10-20. The intended change
removes post-hoc publication-slot choice, not the need for independent evidence.
