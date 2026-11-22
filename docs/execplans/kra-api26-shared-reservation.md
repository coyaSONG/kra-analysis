# Reserve each new API26 collection window across linked worktrees

This ExecPlan follows .agent/PLANS.md. Work in the existing isolated
research checkout, not the owner's working checkout.

## Purpose / Big Picture

The bounded API26 collector protects the whole racecard against retries in
one output folder, but a second output folder can currently issue the
same requests. Before the next real card, make the once-only limit
independent of folder choice. An offline replay of preserved bytes must
still work without consuming a new network attempt.

## Progress

- [x] (2026-11-22) Inspect the live intake and the isolated checkout's
  shared Git directory. Reproduce the repeated requests with mock data.
- [x] (2026-11-22) Reproduce the two failures in tests and implement the
  shared live claim before HTTP, without changing the evidence format.
- [x] (2026-11-22) Verify the exact prior predictions and run the
  intake, source and paired-model regressions plus the script CI tests.
- [x] (2026-11-22) Retest after the prior-result hash publication.
  Verify a held shared lock prevents transport and output reservation.
  Run 296 focused and adjacent tests on the latest base.
- [ ] Release when the required base checks pass.

## Surprises & Discoveries

The same four-venue synthetic card was captured twice under different
folders. Both receipts said captured locally; both attempted the same
four page-1 requests. No real data request was part of the reproduction.
The isolated worktree has a distinct project root but shares the same
Git metadata directory as the original user checkout.

## Decision Log

Record one durable claim for the original set of dates immediately
before local output reservation and any HTTP call. Store it in a
dedicated shared Git directory, protected by the existing exclusive
collector lock and atomic JSON writer. A failed or interrupted claim
cannot be repeated by changing the output folder or switching to a
linked worktree. Check overlap on dates, not the schedule hash or
revised start time. Keep the existing local output guard for existing
reservations in that folder.

The shared claim applies only when this adapter will request a page.
All-reused readbacks do not claim a network attempt, and are still
subject to their output folder reservation. This does not prove that an
older receipt outside the selected folder or a different collector has
never sent a request. Preserve originals and use the existing reuse
mechanism. This change does not register dates or contact KRA.

## Context and Orientation

The CLI and capture logic are in
packages/scripts/autoresearch/kra_entry_scope_intake.py.
Tests are in packages/scripts/autoresearch/tests/test_kra_entry_scope_intake.py.
The archived receipt format is read by kra_entry_scope_inputs.py.
Git linked worktrees have one common metadata directory even when
their checkout directories and outputs differ.

## Plan of Work

First demonstrate the failure with an alternate output and a linked
worktree, using the existing synthetic schedule and transport. Then
require the actual Git worktree root for live collection, check both
reservation locations while locked, and make an immutable date claim
before the first potentially failing local output write. Validate
budget, clock and key presence before claiming. Keep the existing
result, input receipt and model artifacts byte-for-byte unchanged.

## Concrete Steps

    export PYTHONPATH=packages/scripts
    .venv/bin/python -B -m pytest -q -p no:cacheprovider \
        packages/scripts/autoresearch/tests/test_kra_entry_scope_intake.py \
        packages/scripts/autoresearch/tests/test_kra_entry_scope_witness.py \
        packages/scripts/autoresearch/tests/test_fixed_pair_forward.py \
        packages/scripts/autoresearch/tests/test_fixed_pair_evaluation.py

## Validation and Acceptance

An initial mock capture uses the same bounded requests. A second
attempt for overlapping dates fails before HTTP, including after an
authentication or rate-limit failure and across linked worktrees.
A busy shared lock stops a concurrent run before both HTTP and a local
capture reservation. A synthetic failure after the shared claim and
before the temporary local receipt does not permit a second attempt.
Independent dates and fully reused source pages are not blocked by
the shared claim.
Offline readback of previously saved receipts and cutoff checks keep
their existing behavior.

## Outcomes & Retrospective

Both duplicate cases reached the mock transport before the fix. After
the fix, 126 targeted regressions and the 80 script CI tests passed.
Ruff and the PR #95 commitment hash checks passed. The shared claim
also survived a simulated local reservation write failure, and a
reused-only readback left it unchanged. No real KRA calls were made,
and no model, evaluation population or original reservation changed.

The unrestricted autoresearch test run stopped at collection with
seven errors for missing prior-date diagnostic modules. The missing
modules are also absent from the unchanged default branch
`d61b2633b486d82db2af0272ee50a1c8042c14ba`. The script CI uses a
separate test selection. The optional Security Checks job observed
on the baseline still reports dependency audit findings; it is
distinct from the configured required Python Checks job. Do not
change dependency inputs or use any protection override in this fix.
