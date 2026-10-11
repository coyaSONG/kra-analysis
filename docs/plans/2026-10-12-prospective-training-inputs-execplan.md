# Seal future training inputs without changing M0

This living ExecPlan follows `.agent/PLANS.md`.

## Purpose / Big Picture

Accumulate actual pre-race learning inputs for the next model experiment rather
than repeatedly tuning the same 20 observed races. Add a read-only adapter for
the frozen M0 run: preserve its national study membership and selected API26 raw
capture, combine the existing 14 API columns with five fixed recent-history
values and five missing flags, and seal one separate input packet per race.
The 70% objective remains one unordered three-horse prediction per race over
the whole frozen future national population. Input coverage is not accuracy.

## Progress

- [x] (2026-10-11 20:42Z) Verified clean checkout at merged PR86 and read existing M0, source replay and recency boundaries.
- [x] (2026-10-11 20:53Z) Implemented the input adapter, immutable packets, complete ledger and separate historical diagnostic command.
- [x] (2026-10-11 20:53Z) 25 new tests and 170 total related tests pass, including source-backed API/history replay, fixed test clocks, failed/missing membership, late readback and occupied-slot corruption.
- [x] (2026-10-11 20:55Z) Real replay saved 28 diagnostic packets / 294 rows / 24 columns; all API14/recency10 values match and all 28 fail retrospective pre-race timing. Repeat packet bytes and readbacks are identical.
- [x] (2026-10-11 20:55Z) Actual card refresh still awaits all three dates; real adapter records zero prospective packets. All 80 parent/model files are unchanged by it.
- [ ] Push and normally merge after required CI; record remote completion evidence on the PR.

## Context and Orientation

The isolated checkout is `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf`.
The primary checkout `/Users/coyasong/Developer/coyasong/kra-analysis` is a
read-only raw archive. Never edit it. `local_m0_forward.py` owns the existing
`local_m0_20261016_18_v1` series and three dates, October 16-18. Its `study.json`
contains the complete reconciled national roster of races. `prediction_*.json`
or its reserved `input_*.json` points to the first selected raw API26 capture.
The new adapter must never replace those files, collect a preferred replacement
snapshot, use outcome rows to reconstruct missing entrants, or invoke fitting.

`official_history_recency.materialize` accepts a hash-pinned roster-only JSON
with a `ledger` of race IDs and horse/gate rosters. It replays the selected history
seed and official support archive, preserves missing source coverage and excludes
the whole target date. Its 11 MB report is diagnostic provenance, not a model.
Only the five names in `official_history_recency.FIELDS` and their missing flags
join the API14 numerical table. Other coverage and lineage fields remain evidence.

The chosen history seed SHA256 is
`0dbe7abe5bdfb0a0b422bb90bddbdf1a3face89e5016254807ba37be95c25c66` and official
archive SHA256 is `eaece57cdd27ee4e348e171e04368440da9d82a4417110476f0a1a1400e934e2`.
PR85's exact merged research document publishes both hashes. Live GitHub metadata
provides a source-content existence bound, not prediction registration. It does
not certify new target packets until their exact manifest is separately published.

## Plan of Work

Add `packages/scripts/autoresearch/prospective_training_inputs.py` and focused
tests. Reuse original raw projectors, atomic exclusive writes, source witnesses
and recency materialization without editing their hashed modules. The new contract
fixes source versions, schema, parent M0 contract and transformation hashes.
Each run reads all parent studies, retains missing-input slots, creates a roster-only
projection input, calculates history once for available rosters and writes new
packets plus a manifest. A recovered packet must match fresh raw reconstruction;
an occupied invalid slot is a conflict, not permission to replace it.

Record actual source clocks, materialization and readback separately. Check source
and completion times against each race's original T-30 cutoff. T-30 means thirty
minutes before its frozen scheduled start. A late observation stays visible and
is not backdated. A historical diagnostic run uses a separate path and status;
late history for October 10-11 must make prospective eligibility false even if
the input table computes successfully. No labels or fit approvals enter packets.

## Concrete Steps

From the isolated checkout run the new tests and existing M0/recency regressions:

    PYTHONPATH=packages/scripts .venv/bin/python -m pytest -q packages/scripts/autoresearch/tests/test_prospective_training_inputs.py packages/scripts/autoresearch/tests/test_local_m0_forward.py packages/scripts/autoresearch/tests/test_official_history_recency.py -o addopts=''

Use the existing source paths:
`.cache/autoresearch/observed-history-20261011/seed-final.json` and
`.cache/autoresearch/official-history-20261012-v2/archive.json`.
Use original plan/bundle in
`.cache/autoresearch/race_card_pdf_bundles/20261009T165933.854898Z_51a041eda9e6/`
for the real historical rehearsal. Use canonical M0 series root
`.cache/autoresearch/local-m0-forward/local_m0_20261016_18_v1` and model directory
`.cache/autoresearch/restricted-models/20261011T125457.212167Z_4113cd1060f9`
for live input collection. Document final exact CLI commands in the research note.

## Validation and Acceptance

Demonstrate 28 historical packets and 294 rows, exactly 24 model columns per row,
with original API14 and PR85 recency10 values unchanged. Historical replay must
not be accepted as pre-race input. Hash parent model, contract and all existing
M0 files before and after the adapter; their bytes must not change. Synthetic
source-backed tests must exercise a real positive prospective path, label
independence, whole membership, timing, missing history, duplicate/changed
identities, late publication and immutable retries.

If actual future cards remain absent, report zero prospective packets and three
awaiting-card dates. That is an honest external dependency, not completion of
this week's data acquisition. Research completion later requires real national
membership, source-linked packets or explicit failure slots, timely independent
publication and later versioned labels. The code milestone alone is not the goal.

## Idempotence and Recovery

Write only to a distinct new input archive. Protect it with the existing exclusive
lock and atomic no-overwrite writer. Use unique run directories for diagnostics
and manifests. Missing/unsealed inputs may be retried before cutoff; sealed slots
cannot be enriched or replaced. Hash mismatch is an explicit conflict. No paid
services, credentials in output, source deletion or database changes are needed.

## Interfaces and Dependencies

Use existing `httpx`, standard-library JSON/time/path utilities and repository
M0 and recency adapters. CI belongs in the API Python job, which already has the
model imports' NumPy dependencies; do not add packages. Separate pure 24-column
join/timing policy from I/O to keep tests focused. Preserve raw and output pins
so a later publication witness can verify the exact manifest without rewrites.

## Surprises & Discoveries

The first live publication replay rejected valid source pins because PR85 prints
them in a shell code block, not inline backticks. The bounded exact-token reader
now supports both original layouts and rejects 65-digit substring matches;
five regression cases cover it. The failed v1 output is retained, not rewritten.
The previous increment found 27 historical API-only source
candidates, but they are not new forward observations and do not provide the
pre-race history required by the new 24-column contract.

## Decision Log

2026-10-11, Codex: implement the completed Pro recommendation recorded in PR86.
Keep history fixed for the week, do not gather more features, and use the same
first raw API26 input as M0. The previous turn was concrete progress, not a
blocked wait: it added raw-verified candidate evidence and merged reproducible code.

## Outcomes & Retrospective

The code milestone is complete: 28 actual raw diagnostic packets are reproducible
and rejected as pre-race evidence; 170 tests pass. Real future collection remains
zero until cards appear. No model was fitted or promoted. Remote CI and normal
merge remain for this increment; actual future acquisition/publication is the
next external-data milestone, not a completed claim.

Revision: recorded actual replay, repeat equality, original-model invariance,
170 tests and zero genuine future packets. See the companion research note for
exact artifact hashes and commands. Remote completion will be recorded on the PR.
