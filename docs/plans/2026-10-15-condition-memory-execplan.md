# Isolate older career memory from recent condition form

This living ExecPlan follows `.agent/PLANS.md`. Maintain Progress, Surprises &
Discoveries, Decision Log and Outcomes & Retrospective throughout execution.

## Purpose / Big Picture

Use the newly acquired May history without overwriting the published M0/API27
predictions. Produce an outcome-free research feature snapshot for all 50 frozen
October 16-18 races and 534 runner appearances. Separate recent condition form
from older general career evidence, and quantify sensitivity to losing one
recent observation. This enables later controlled model research; it does not
fit a model, choose a new three-horse combination or measure accuracy.

## Progress

- [x] (2026-10-15) Read prior protocols, expansion evidence and source modules.
- [x] (2026-10-15) Tried the authorized Pro conversation; it is logged out.
- [x] (2026-10-15) Implemented isolated projector and 26 targeted tests; 245 combined regressions pass.
- [ ] Freeze and run the recipe once; independently check arithmetic and pins.
- [ ] Record results, run checks, push and use normal PR merge after required checks.

## Surprises & Discoveries

May observations lie outside this cohort's fixed 90-day window. They cannot
change the existing condition contrast. The expansion adds Busan history to
Yeongcheon entrants, not physical Yeongcheon experience. Historical captures
are late relative to their own races, so retrospective pre-race training
availability remains unverified.

## Decision Log

On 2026-10-15, retain the exact `joint90 - expanded90` contrast and its runner
fallback. Add an explicitly separate older band `[D-180,D-90)` rather than
silently extending the recent window. Use the existing rank-form estimator
with prior mean 1/2 and pseudo-count two only as an older-career descriptor.
Return null for no older support, not observed 0.5. Keep same-venue similarity
counts separate from other-venue experience; never pool class labels across
physical venues. No window sweep, outcome comparison or hyperparameter fit.

Delete each recent observation in turn and recompute the unchanged contrast.
Retain its min/max, fallback count and sign reversal indicator as diagnostics,
not candidate model inputs, confidence intervals or independent samples.
These deletions expose sparse-support sensitivity without selecting a winner.

## Context and Orientation

`packages/scripts/autoresearch/condition_delta_diagnostic.py` pins public
commitments and loads identity-only target rosters from reserved entry pages.
Its `project` is the unchanged recent contrast. `history_form_research.py`
contains strict-day window selection and the exact Fraction rank estimator.
`history_gap_expansion.py` replays May API/HTML evidence. Its pinned report at
`.cache/autoresearch/history-gap-expansion-20261014/report-v2.json` has SHA256
`3302c5bb1abb62f70565535751991c01896b9b437e4160168ea3700fbbc09866` and contains
extension history and dated-header conditions. Baseline history has 8,994 rows;
extension has 1,528 supported rows. Missing observed history is not proof of
no lifetime starts. Every analytical count refers to this partial archive.

## Plan of Work

Add `condition_memory_research.py` beside existing modules and a matching test
under `packages/scripts/autoresearch/tests/`. Its pure projector accepts
identity-only targets, baseline and extension records, and conditions. It
rejects duplicate/invalid history, target/future results, physical-venue
conflicts, target labels and any extension that changes the frozen 90-day
ledger. For each runner retain recent contrast/support, older-band descriptor,
counts and source IDs, added-May IDs and separate deletion diagnostics.

The CLI reads pinned artifacts, checks public commitments before and after,
compares its original recent ledger with the previously pinned ledger, and
writes exclusively to a new research directory. Record creation time, source
and implementation hashes, null accuracy, zero fits and non-training status.
Reject snapshot creation at or after the earliest frozen cutoff. Reading old
artifacts after cutoff is still possible, but do not reissue a timely snapshot.
No network requests or API calls are needed for this offline research.

## Milestones

First implement the projector and synthetic tests. Demonstrate exact window
boundaries, sparse/absent support, deletion fallback and sign reversal, and
physical venue separation. Then run one pinned full-cohort projection and an
independent direct-arithmetic calculation over every row. Finally document
findings, add the tests to Scripts Checks and publish through a normal PR.

## Concrete Steps

From `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf`:

    PYTHONPATH=packages/scripts .venv/bin/pytest -q packages/scripts/autoresearch/tests/test_condition_memory_research.py
    PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.condition_memory_research --output-dir .cache/autoresearch/condition-memory-20261015/run-1

Use a new directory on replay. Run existing condition delta, condition form,
history expansion, historical form and forward contract tests too. Ruff lint
and formatting must pass. Record exact output and required CI evidence later.

## Validation and Acceptance

All 534 candidate rows and 50 races remain; recent contrast ledger equals the
old pinned ledger exactly. Independent calculations must match older counts,
Fractions and deletion diagnostics. All three public manifest hashes remain
unchanged. No target outcome read, prediction, fitted artifact, promotion,
published input mutation or accuracy number is produced. Tests must reject
unsafe inputs and existing output paths, including a late creation timestamp.

## Idempotence and Recovery

Only new source/test/docs and CI test entries are changed. Original worktree,
frozen forward directories and commitments are read-only. Partial runs retain
their files; retry in a new output directory. Do not erase or overwrite evidence.
Keep work on the isolated `codex/condition-memory-research-20261015` branch.

## Artifacts and Notes

The prior Pro conversation opened to the logged-out screen on 2026-10-15;
no prompt was sent and no new consultation occurred. The previous completed
advice to avoid tuning repeatedly viewed outcomes remains in force.

## Interfaces and Dependencies

Reuse standard-library Fraction, datetime and existing local pure helpers.
`project(targets, baseline, extension, contexts)` returns full per-runner
features, provenance and stress diagnostics. `run(output_dir)` returns the
exclusive report hash and denominator-preserving summaries. No new dependency
or production API integration is introduced. Inspectable Python and JSON are
the primary research artifacts, following the repository's established workflow.

## Outcomes & Retrospective

Pending execution. This work cannot establish accuracy improvement while the
registered target outcomes are pending. If these rows later inform training,
evaluate the resulting model on a different prospectively frozen population.

Initial plan recorded before running the candidate projection.

Implementation milestone: synthetic sign-reversal example required four priors
because the two-pseudo-observation shrinkage can prevent reversal with the
initial three-prior example. Corrected the fixture, not the scoring rule. All
245 tests pass before the real-data projection.
