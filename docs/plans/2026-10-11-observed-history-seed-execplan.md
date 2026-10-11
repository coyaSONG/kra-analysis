# Capture And Replay Observed Race History

This living ExecPlan follows `.agent/PLANS.md`.

## Purpose / Big Picture

Give the research pipeline actual recent official result bytes for future cards,
not another empty approval list. A source seed is a frozen collection of observed
events that later predictions can reference. Preserve all four physical venues,
all requested calendar dates, failures, empty responses and identity uncertainty.
Demonstrate a pure 90-day history calculation on already archived independent
rosters without training or claiming historical pre-race availability.

## Progress

- [x] (2026-10-11) Verify PR77 is merged and inspect existing capture/replay code.
- [x] (2026-10-11T13:32Z) Implement bounded resumable collection and complete request inventory.
- [x] (2026-10-11T13:34Z) Implement outcome-independent history transformation; 28 new tests and 347 total focused/shared regressions pass.
- [ ] Collect and replay actual July 12-October 11 source bytes; preserve gaps (collection running, plan hash fixed).
- [ ] Verify actual transformation, publish source hashes, run tests and merge normally.

## Context And Orientation

Work in `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf` on
`codex/observed-history-seed`, based on merged PR77 commit
`80b761528db7c162754001887c85d663aa1ec74c`. The owner's checkout is read-only.
`packages/scripts/autoresearch/kra_result_snapshot.py` already captures complete
API214 venue/day pages and replays their hashes, identity and timestamps.
`kra_entry_sheet_snapshot.py` captures API26 pages; result replay can use their
exact full-day identity set to bind result rows whose venue field is absent.
`shared/kra_result_history.py` preserves normal ranked finishes and unresolved
statuses, explicitly not certifying complete actual start history.

The actual source-reviewed corpus is
`.cache/autoresearch/restricted-cohort/20261011T124748.785378Z_ebdf29deaaa9/corpus.json`,
SHA256 `d6598f244d6a7b7bc5e65846a4c79ee6ac96ad278b89a14268de332e77526ae2`.
Its 28 roster records, not target result rows or selected training membership,
provide the independent diagnostic targets. Replaying current history against
October 10/11 is a retrospective transformation, not approved training data.

## Decision Log

Decision: collect July 12-October 11, 2026 inclusive, all venues 1/2/3/4.
Rationale: July 14-October 11 is the proposed current 90-day seed; two additional
days provide the complete calendar lookback for the existing October 10/11
diagnostic rosters. This extension is fixed before collection and is not driven
by predictive outcomes. The 368 venue/date requests are not a national race
universe; empty responses cannot prove absence of races.
Date/Author: 2026-10-11, Codex.

Decision: reuse the existing collectors without modifying their code or the
PR76 implementation approval. Persist a request reservation before each HTTP
attempt; cap the entire plan at 2,000 reservations, one request per second.
Rationale: pagination, API26 identity binding and retries all consume quota.
Interrupted reservations conservatively count against the cap. An exclusive
OS file lock prevents two active collectors sharing the same plan.
Date/Author: 2026-10-11, Codex.

Decision: a complete observed-response window may yield observed counts zero,
but partial/failed/unresolved windows must yield null model values and explicit
coverage flags. Keep the underlying observed events and lineage in either case.
Rationale: no rows observed is different from no real starts or no data access.
Date/Author: 2026-10-11, Codex.

Decision: no historical H0/H1 fitting or production approval in this increment.
Rationale: the completed Pro consultation proposed retrospective fits, but the
Goal still requires reviewed pre-race-safe training data. Current raw acquisition
can support future source review, not backdate historical revision availability.
Date/Author: 2026-10-11, Codex.

## Plan Of Work

Add `packages/scripts/autoresearch/observed_history_seed.py` for immutable plan
creation, journaled bounded collection, verified replay and frozen seed export.
Retain append-only attempt receipts and skip previously replayable units on
resume. Retry only explicitly requested failed units with new receipt versions;
never overwrite captured source bytes. Stop a run on three consecutive failed
units or budget exhaustion rather than repeatedly consuming a broken service.

Add `packages/scripts/shared/observed_result_history.py` for a pure function that
accepts an independent roster, normalized prior events and response coverage.
Use only event dates in [target date minus 90 days, target date), never target
results, cumulative API26 statistics or odds. Produce observed finish counts,
wins, top-three count/fraction, unresolved count, 30-day finish count, days since
last observed normal finish, last rank, last-three mean rank and newer unresolved
presence. Include gate, venue, roster size and missing flags. Preserve raw-source
lineage outside the numeric matrix. No observed normal finish means date/rank
statistics are null, not an invented debut or rest interval.

## Milestones

First, tests demonstrate bounded requests and crash/resume behavior without
credentials in receipts, exact plan membership, raw tamper rejection and strict
venue binding. Second, transformation tests demonstrate target/future outcome
invariance, stable roster membership, 90/30-day boundaries, missingness and
unresolved-event semantics. Third, run the actual collector, export the full
request ledger and transform real archived rosters; report actual coverage,
event counts and source pins. Do not declare missing requests completed.

## Concrete Steps

From the isolated checkout, use the existing `.venv` and `PYTHONPATH=packages/scripts`.
The planned CLI is `python -m autoresearch.observed_history_seed init --root
.cache/autoresearch/observed-history-20261011 --start 20260712 --end 20261011`.
Then invoke `collect --root <root> --api-key-file <local secret file>` and
`export --root <root> --output <new seed.json>`. Credentials stay in the existing
local secret store and never appear as CLI literal values or persisted URLs.
The `project` command accepts that root and the pinned independent corpus,
then writes a new diagnostic projection. Exact successful commands and counts
will be added to the report after execution.

Run `PYTHONPATH=packages/scripts .venv/bin/python -m pytest` against new tests
plus existing result/entry/replay suites with `-q -o addopts=''`. Run Ruff lint,
Ruff format check and `git diff --check`; add explicit CI coverage for new files.
Commit/push source improvements and observed evidence, never raw cache or secrets.
Ordinary merge requires the current protected checks to pass.

## Validation And Acceptance

All 368 requests remain visible even when incomplete. Verify every successful
capture's page hashes before using its records. A changed source file must fail,
not silently become an empty history. Missing physical venue requires complete
independent roster binding or remains unusable. Export includes capture and plan
hashes, observation times, status counts and false flags for complete real-world
history, historical pre-race availability and 70% performance evidence.

Actual projected runner counts equal the independent input rosters, with no
target-result filtering. No model fit or prediction is asserted. A publication
hash can later bound existence of this current seed; it is not an independent
KRA certificate or a registered prediction.

## Idempotence And Recovery

Initialize only a new directory. Plan bytes and source implementation are fixed
before requests. Resume the same root; existing successful captures are replayed
and skipped. Failed attempt files remain. New exports use exclusive creation.
An OS lock is released by process exit; a filename alone is not proof of a live
collector. Poll the actual process handle before restarting interrupted work.

## Surprises & Discoveries

The existing entry collector can preserve full-day pages even when validating
one requested race. Reuse its proven complete identity binding, not an inferred
venue based only on the API query. A valid but nonmatching result/entry roster
remains identity-unresolved rather than aborting unrelated dates. Page/hash
tampering still raises an error. Same-day observations cannot be ordered by
race number across venues; ambiguous last-rank/last-three boundaries remain null.

## Outcomes & Retrospective

Implementation and 347 focused/shared regressions are complete. Actual collection
is running under the fixed plan SHA256
`86b32a93348842575d9620cf124cad31df9c4eb2fb1287a82781480a67279960`.
The Goal remains active; 70% future exact success is unproven and paid server
provisioning is unapproved.

Revision: initial concrete collection and transformation scope fixed before
implementation, following completed Pro advice while retaining training rules.

Revision: record implemented collection/transformation, live actual collection
and passing tests before publishing the first code increment. No fitting occurs.
