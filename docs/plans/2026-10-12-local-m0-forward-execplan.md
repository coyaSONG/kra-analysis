# Run the frozen M0 model locally on the full official race population

This living ExecPlan follows `.agent/PLANS.md`. Update Progress, discoveries,
decisions and outcomes as implementation and evidence change.

## Purpose / Big Picture

The owner has deferred paid infrastructure. A reviewed model already exists,
but only the untrained B0 rule has an executable forward submission path and it
requires PostgreSQL. Add a separate local research path that captures all
official races, uses exactly the existing full M0 API-only model, and retains
one three-horse prediction or an explicit missing status for every race.
This enables real prospective collection when cards appear without buying a
server. It does not promote a model, prove 70% performance, or turn a laptop
clock into an independent timestamp. Past-source rehearsal is software evidence,
not a backdated prediction. The complete future denominator remains mandatory.

## Progress

- [x] (2026-10-11 18:22Z) Rechecked Oct16 cards: unpublished; retained all four
  source responses. Local Docker daemon is unavailable.
- [x] (2026-10-11 18:26Z) Verified existing full/development M0 artifact hashes
  and nonempty inference on the 20 reviewed races, without fitting.
- [x] (2026-10-11 18:38Z) Read completed Pro advice (10m30s); it recommends A.
- [x] (2026-10-11 18:42Z) Implemented fixed model admission, API-only projection,
  local run/resume, pinned pending inputs, read-back and commitment manifests.
- [x] (2026-10-11 18:42Z) Actual 28/294 inventory scored; full 50-race schedule
  retained 21 scored, 7 conflicts, 22 missing. Reference matrix 209x14 and scores
  matched exactly. All 206 focused regressions passed.
- [x] (2026-10-11 18:42Z) Live three-date run retained 12 official responses;
  all dates await cards, zero future studies/predictions. Contract retained.
- [ ] Record evidence, run checks, push and normally merge the increment.

## Surprises & Discoveries

Current `restricted_ablation.admit` rejects refitting the old corpus because
`kra_result_snapshot.py` changed after the review. The inference and entry
projection files are unchanged. Do not relax that refit gate. Existing portable
JSON models can be admitted separately against their original fit receipt,
review, exact artifact bytes and unchanged inference dependencies.

The first remote CI run put the new tests in the lightweight scripts environment,
which has no NumPy. Move the step into Python Checks using the existing API
environment, alongside the restricted model tests. No dependency or lockfile
changes are needed; the model and already saved local contract stay unchanged.

## Decision Log

Choose M0 for its lack of PDF dependency, not because its 1/7 observed-development
score beats M1 (it does not). Freeze one research arm for October 16-18 before
future outcomes; no per-race arm selection, outcome-based fallback, new fitting,
or command-line study aliases. Preserve all missing races. This is a proposed
implementation accepted after completed methodological advice. The optional
fallback suggestion is deferred: preserve pure M0 and report failed slots rather
than silently introducing an unreviewed hybrid. No failed race leaves membership.

## Outcomes & Retrospective

The local executable path and positive actual-source rehearsal are complete.
Both raw features and stored preprocessing are equal to the original reference;
the API-only path also handles the inventory race previously blocked by PDF.
New future cards remain unpublished. Paid resources and production approvals
are unchanged. Publication checks/merge remain pending and will be recorded
on the PR. No future score or 70% success has been measured.

## Context and Orientation

Work in the isolated `kra-analysis-race-card-pdf` checkout, not the dirty primary
checkout. `autoresearch/kra_schedule_snapshot.py` captures and reconciles dated
national plus three regional cards and freezes a whole day's population before
the earliest T30 deadline (scheduled start minus 30 minutes).
`autoresearch/kra_entry_sheet_snapshot.py` retains paginated API26 bytes;
`kra_race_card_pdf_replay.replay_entry_pages` verifies those bytes without PDFs.
`shared/kra_entry_sheet.build_entry_snapshot` validates the complete same-race
roster. `restricted_cohort.numeric` defines the seven API numeric fields.
`restricted_ablation.predict` reconstructs stored scaling and coefficients,
selecting exactly three IDs by descending linear score, ascending gate and ID.
It needs no labels. M0 is not a calibrated joint three-horse probability model.

The original full model is in
`.cache/autoresearch/restricted-models/20261011T125457.212167Z_4113cd1060f9/full_M0_model.json`,
SHA256 `0c0078fb513d4acc2695427475b91668f20441bfab1f4ce05e0418277c8bbb74`.
The adjacent receipt is SHA256
`70cf1f7de5a51ae68f4706b6349686276c6bf23978d37f116072bcd61a7ef69b`.
`data/contracts/restricted_training_review_v1.json` records its original reviewed
20-race/209-runner training population. Never modify that approval in this work.

## Plan of Work

Add a fixed contract and additive inference/runner modules under
`packages/scripts/autoresearch`. Admit exact model and receipt bytes, original
review linkage, and the unchanged inference dependencies. Project API fields
directly without requiring PDF or labels, with exact parity against the reviewed
corpus. Validate roster size and schedule time against the frozen full schedule.

Persist the study contract before predictions. Local slots are keyed by fixed
series/date/race, not changeable model or source hashes. Atomic exclusive writes
retain original packets. Resume reads and verifies original packets and source
bytes instead of reranking from fresh data. Record a separate post-write
read-back time; missing/late observation cannot prove timely persistence.
Local owner modification, changing the archive root, laptop sleep and clock
manipulation remain outside these operational protections and must be disclosed.

Provide a separate past-source rehearsal command that uses pinned schedule and
entry captures with the same inference adapter, retains the complete schedule
population, and cannot write a prospective slot. No accuracy calculation belongs
in rehearsal because the full model was fitted after those races.

## Concrete Steps

From the isolated repository root run focused tests with:

    .venv/bin/python -m pytest -q packages/scripts/autoresearch/tests/test_local_m0_forward.py -o addopts=''

Use existing `.venv`, original ignored caches and API secret file outside Git.
Exact live/rehearsal CLI commands and actual hashes are recorded in
`docs/research/2026-10-12-local-m0-forward.md`. Use its fixed original archive root
and model directory; do not start a new root to bypass the pinned contract.
Never put credential values in commands, reports or Git. No dev server is needed.

## Validation and Acceptance

Require nonempty replay from real API26 source bytes; compare the complete 14
feature columns to all matching reviewed rows and saved-model predictions.
Rehearse full official dated populations, including missing sources and roster
conflicts. Synthetic tests must cover all physical venues, missing PDF/results,
API-only field whitelist, canonical duplicate IDs, changed model/contract/raw
bytes, deadline crossing, lost observation, immutable resume, missing-race
retention and source failure. Existing training tests must remain unchanged.

Actual future cards are unavailable at initial inspection. A correct live
invocation must retain that evidence and return awaiting-card, not fabricate an
empty complete population or prediction. This is not a substitute for eventual
real prospective execution and evaluation.

## Idempotence and Recovery

Never overwrite archives, predictions or old model files. A conflicting packet
fails visibly; identical retries recover the same original slot. A source failure
before a packet exists may be retried before the fixed deadline. Interrupted
atomic writes cannot publish partial JSON. Do not delete an existing study to
change a model. Failed future capture leaves a report, not a successful study.

## Artifacts and Notes

The initial next-card check is
`.cache/autoresearch/forward-b0/run_20261011T182231110624.json`, reporting
`awaiting_card` and `future_submissions_started=false`. Pro consultation started
in the authorized existing browser conversation at approximately 18:23Z; do not
use a partial answer or claim completion before the UI finishes.

## Interfaces and Dependencies

Reuse Python standard library, installed NumPy/sklearn inference and existing
httpx collectors. Add no dependency or paid service. Keep the original fit
approval and B0 PostgreSQL schema unchanged. The local runner is research-only;
independent timestamp, operational server receipt and 70% evidence flags remain
false until separately established.

Revision 2026-10-12: initial plan based on the owner's paid-server deferral and
verified existing model/source availability. Updated after completed Pro advice,
actual 28/294 plus 50-race replay, zero-difference matrix comparison, 206 tests
and the three-date live unpublished-card check. Publication remains pending.
CI follow-up: corrected the test job environment after the first remote run
reported `ModuleNotFoundError: numpy`; rerun all required checks before merging.
