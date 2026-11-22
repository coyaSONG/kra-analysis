# Score an approved fixed M0/API27 card from selected raw result versions

Maintain under .agent/PLANS.md. Use the isolated research checkout and
preserve the original October protocols, models and data.

## Purpose / Big Picture

The new whole-card runner can publish one paired M0/API27 packet, but the
October evaluator accepts only the October series. A new read-only command
should verify the original public authority, join one selected raw result
version to all frozen races, and expose an exact paired comparison only
when complete. This must not open a new study, obtain a result, or alter
the old evaluator.

## Progress

- [x] (2026-11-22) Inspect the published October policy, new execution
  contract, raw-replay collectors, and fixture-only result rehearsal.
- [x] (2026-11-22) Connect the immutable authorities, predictions and
  raw results, preserving the historical evaluator unchanged.
- [x] (2026-11-22) Exercise partial, complete, late and corrected
  observations; 699 focused and adjacent tests pass in 54.88 seconds.
- [ ] Verify and release through the normal required checks.

## Surprises & Discoveries

The original result observer distinguishes a reported void from final
settlement and retains incomplete results. GitHub publication can be valid
even if the original runnable model environment is no longer available.
We must not turn missing evidence or runtime drift into a miss, or turn a
stored local selection into a public prediction.

## Decision Log

Use the existing M0/API27 versioned-result and paired counting policies
without modification. Require a known, exact original whole-card receipt,
schedule and independent protocol/approval archives. A known prebound
prediction PR merged at or after the original cutoff proves a late
submission; an unavailable archive does not prove absence. A timely
packet additionally needs read-only reproduction of the original stored
predictions, not a new execution with a newer runtime.

Replay the selected result plan and its archived API and HTML, checking
date, venue, exact scheduled race IDs, source clocks and the original
declared gate/horse mapping. Missing starters and lower blank rows stay
visible. Unresolved identities remain pending. The old void observation
classification does not certify public settlement. Extra result events
hold the complete-universe comparison; they do not resize the ledger.

Keep distance, literal grade and physical-venue counts diagnostic only.
Recover the first two from the original API26 rows, never with result
data or a later lookup. Explicitly keep unknown context. Compare two
selected result versions with identical authority, population and
prediction evidence. Capture all deltas without mutating either input.

## Outcomes & Retrospective

Saved mock API214 pages and matching official HTML exercised two race
days, all four venues and 14 frozen races. A one-race correction
changed the descriptive winner with the exact same frozen prediction
and population. Partial results retain four statuses, including
ties, the old policy's reported-void observation, a lower exclusion,
an omitted declaration and source/roster conflicts. No requests or
archive writes occur during evaluation. Missing original inference
evidence leaves a verified timely publication visible but unscored.

Separately, the real October archive replay reproduced the exact
sealed 50-race observation and existing paired report: both arms
missed all 50. No new race or result request was made. No genuine
study, model execution, prediction or score was created.

## Context and Orientation

fixed_pair_forward.py retains the new official publication slot and can
replay a fixed prediction read-only. fixed_pair_forward_contract.py binds
owner, reviewer, original scope and cutoff. versioned_result_observations.py
replays immutable observations, local_m0_evaluation.py classifies each
outcome, and api27_evaluation.py aggregates the same full population. The
new module composes these under a new report format.

## Plan of Work

First verify all original scope and authority evidence offline. Then
distinguish an exact timely, exact late and still-unverified prediction.
Only after those facts are established read the optional selected version
of outcomes. Left-join all frozen races, retain the links and clocks for
each source, and compute the existing paired statistics. Derive result
deltas by replaying a second designated old version with exactly the same
prediction state. Print canonical JSON without changing any source files.

## Concrete Steps

From the isolated repository root:

    export PYTHONPATH=packages/scripts
    .venv/bin/python -B -m autoresearch.fixed_pair_evaluation --help
    .venv/bin/python -B -m pytest -q -p no:cacheprovider -o addopts='' \
      packages/scripts/autoresearch/tests/test_fixed_pair_evaluation.py

The scripts README documents exact analysis arguments. Run the existing
schedule, input-witness, fixed model and result regressions as well.

## Validation and Acceptance

Use only fictional dates for new full/missing/tied/void/corrected cases.
Show the same exact frozen race count in all outcome states, including a
wrong extra result and an unrecognized roster change. Verify that a late
merger does not count before a valid result exists, missing evidence is
not a miss, and a correction can change the comparative winner without
changing predictions or population. Confirm the October files retain
their original hashes and results.

## Idempotence and Recovery

The evaluator makes no requests, file writes, fits or new attempts.
Re-running on the same pins reproduces the same observations and
calculations with a new report clock. Missing or changed evidence
remains separate from prediction failure. Select an explicit new
version for a correction, not a mutable latest file.

## Artifacts and Notes

Keep raw source files in their original archive. Preserve each report
version separately. Neither publication verification nor one completed
block is a promotion decision or independent generalization evidence.

## Interfaces and Dependencies

Use existing Python libraries, source replay, classifier and paired
metrics. Add no network clients, dependency or paid server.
