# Bind condition-study targets to original published rosters

Maintain this ExecPlan as described in .agent/PLANS.md.

## Purpose / Big Picture

The A24/B34 weekly calculator only accepts already verified statuses. Add the
read-only path that checks those statuses against the original approved week's
official schedule, published declaration roster, and selected official result
versions. An incomplete or ambiguous result will remain visible as pending,
not be guessed, scored as wrong, or removed from the original race list.

## Progress

- [x] (2026-11-22 UTC) Located the evidence requirements and the existing raw
  source replayers. Confirmed the weekly calculator does not verify its inputs.
- [x] (2026-11-22 UTC) Implemented original population and outcome-target replay.
- [x] (2026-11-22 UTC) Verified 13 synthetic target cases and 577 related
  regressions from the Python CI working directory. Ruff lint and format
  passed. The four frozen model/commitment files and fit receipt matched.
- [ ] Pass required checks and merge normally.

## Surprises & Discoveries

The raw observer can report a unique top-three set even when its result roster
is smaller than the scheduled count. The condition study needs a separate
full roster check against the original declaration, not just the observer's
status. Its API void note and blank HTML do not verify cancellation.

The weekly protocol pins a separate schedule capture for each date; several
dates can share the same capture. The result observer binds one capture
digest per plan. A manifest therefore selects at most one plan per distinct
original schedule digest, and a selected plan must cover all its original
dates. An unselected group is pending, never a subset performance report.

## Decision Log

Use the published v2 A24/B34 protocol and separately archived approval rather
than the current runtime or registry. Verify both were merged before the
first cutoff. Compare the declared rosters to full API and official HTML result
rosters by gate and stable numeric horse identity; emit the original protocol
spelling of verified horses. Same numeric ID in two original rows is not an
alias that can be resolved safely.

Accept only a unique replayed observation with both raw result clocks within
its original start and analysis cutoff. This milestone does not establish
no-target status. A missing result, reported void, conflicting sources or
unverified roster change remains pending. Keep result extras separately and
do not mark the umbrella population closed.

## Outcomes & Retrospective

The synthetic raw archives reproduced agreed unique targets, retained all
14 declared fictional races through withheld outcomes and extras, and replayed
two correction versions without modifying either. The published model files,
scoring rules and historical evaluator are untouched. No live result, fit,
or actual prediction was used. Real population closure, historical prediction
admission, and confirmed official cancellations remain separate obligations.

## Context and Orientation

All paths below are relative to the isolated repository root.
`packages/scripts/autoresearch/condition_historical_publication.py` verifies
archived publication bytes and approval identity.
`packages/scripts/autoresearch/kra_schedule_snapshot.py` replays the dated
national and regional cards. `versioned_result_observations.py` in the same
directory replays raw API and official HTML records using an existing
hash-bound observation plan. A result target describes one specific race;
it does not prove the selected study covers every required week.

## Plan of Work

Add `packages/scripts/autoresearch/condition_target_observations.py` and the
corresponding `tests/test_condition_target_observations.py`. The verifier will
check an exact manifest digest, archived publication and review, the original
dated schedules, and only the designated result versions. It will retain
original race IDs and source version identifiers even where no target can
be established. Add the tests to the existing condition outcome CI step.

## Concrete Steps

Run from the isolated root (with the local Python 3.13 virtual environment):

    env PYTHONPATH=packages/scripts .venv/bin/python -B -m pytest -q -p no:cacheprovider -o addopts='' packages/scripts/autoresearch/tests/test_condition_target_observations.py

Run the neighboring observation, historical publication, fixed-pair outcome,
and weekly accounting suites after the new cases pass. Check formatting
with Ruff and whitespace with `git diff --check`.

## Validation and Acceptance

Synthetic source receipts exercise the same collection byte formats as an
actual result archive. An unchanged roster and agreed unique top three can
be projected, including padding differences. A wrong roster, void without
official whole-race proof, ambiguous top three, or absent version does not
produce a scoring target. A correction is selected as a new version and the
old version can still be replayed. Traps prevent requests and inference inside
the verifier.

## Idempotence and Recovery

The verifier prints a report; it does not create or overwrite source bytes.
An absent input can be replayed later only when its original evidence is
restored or a deliberately selected new version is supplied. Bad pins, scope
changes and conflicting publication identity stop replay. Do not alter a
protocol to repair results.

## Artifacts and Notes

The machine report exposes the target policy digest, official observation
version, original race IDs, capture pins, reasons for pending states and
source extras. It exposes no model accuracy or scoring denominator.

## Interfaces and Dependencies

`condition_target_observations.audit(manifest_path, expected_sha)` accepts
local evidence pins. The read-only CLI takes `--manifest` and `--sha256`.
Use the existing archive and official replay helpers; add no dependency.
