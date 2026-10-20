# Verify original time operands across the preserved history

This living ExecPlan follows `.agent/PLANS.md`.

## Purpose / Big Picture

PR129 established repeated identities, not valid measurements. Verify the actual
printed time operands and endpoint arithmetic for the entire unchanged 11,523-row
historical corpus. This allows a later no-fit stability study to distinguish
verified endpoints from readable labels, missing values and source conflicts.
It does not authorize training or enroll future races.

## Progress

- [x] Read PR129 inventory and existing May source/arithmetic/quantity auditors.
- [x] Implement full-corpus original-time replay and focused regression tests.
- [x] Execute the bounded local audit and independently verify its tallies.
- [ ] Publish interpretation, pass required CI and normally merge.

## Surprises & Discoveries

The old detail parser obtains total time from the same timing tables. Agreement
with that parser is an internal consistency check, not a second source.
Seoul's initial-200 value has no independent cumulative counterpart in the
existing arithmetic mapper. Preserve this distinction from Busan's checked span.

The first execution stopped before producing output: numeric histogram keys
sort differently after JSON turns them into strings. Independent replay proved
every compared field equal as JSON values; only encoded ledger order differed.
Keep the file hash check and use structural JSON equality for the replay.
The integration fixture includes keys 2 and 10 to guard this behavior.

The first completed run exposed a missing 4-2F cell for horse51248 in
20260703_3_6. Inspecting its raw cells revealed a 1000m clock of1:34.0 preceding
a 1200m clock of1:16.8. Six local equations match despite this reversal.
Added monotonic checks over known distance-labelled positions and withheld
the row's candidate measurements. Preserved the initial output, then wrote v2.

## Decision Log

Reuse `sectional_arithmetic_audit.evaluate` and the pinned official guide; do not
infer new layouts for Busan 1000/2000m or Yeongcheon. Keep Jeju's labels readable
but its pace endpoints unverified. Inspect every selected historical identity,
retaining unknown layouts in the denominator. Classify malformed operands rather
than converting them to zero. Keep source tiers unchanged; this run does not
replay API times. Do not use October 16-18 outcomes or saved model scoring.

## Context and Orientation

`packages/scripts/autoresearch/longitudinal_history_inventory.py` replays the
original receipts, HTML, conditions and selected horse/rank/roster joins.
Its immutable report is
`docs/research/experiments/2026-10-20-longitudinal-readiness/report.json`,
SHA256 `a338c67f005c1ff56d3ab418f44073d7d76de0a2e3b879d7172a2a8f430e9701`.
Its source pins identify 8,994 baseline, 1,528 later-May and 1,001 early-May
admitted records. The admitted corpus is not all raw starters or all national
racing history. `sectional_source_audit.timing_rows` recognizes literal headers;
`sectional_arithmetic_audit.evaluate` subtracts named cumulative endpoints and
compares printed segments exactly using Decimal. No tolerance is fitted.

## Plan of Work

First add `longitudinal_time_audit.py`, retaining raw time cells and one
measurement status per total, initial 200m and final 600m. A measurement is a
printed duration, not a predictor. Replay the inventory and compare its immutable
population/source evidence before scanning tables. Then add tests for invalid
values, missing operands, conflicting totals/segments, unknown venues/layouts,
row identity preservation and strict temporal joins. Finally save a new immutable
report and interpretation, add CI coverage and verify a normal merge.

## Concrete Steps

From `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf`:

    env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts .venv/bin/python -B -m pytest -q -p no:cacheprovider packages/scripts/autoresearch/tests/test_longitudinal_time_audit.py
    env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts .venv/bin/python -B -m autoresearch.longitudinal_time_audit

The audit prints JSON only. Preserve output once via exclusive file creation.
Never call a trainer, prediction publisher or evaluation registration tool.

## Validation and Acceptance

The report must retain all 11,523 selected identities and 1,156 races, preserve
all source tiers, and reproduce the immutable inventory. Distinguish positive,
blank, zero and malformed operands. Exact final-600 checks require positive
ordered cumulative endpoints and equality to the printed segment. Initial-200
in Seoul stays label-only. Conflicts withhold the affected row's candidate
measurements, without deleting that row. Unknown layouts remain visible.
Report missingness by physical venue/distance and calendar month. Pair counts
require the same horse, venue and distance within 1-180 earlier days and usable
measurement status on both sides; they are structural, not pre-race validation.
Independent tallies and focused tests must match before publishing.

## Idempotence and Recovery

Source reads are local and pinned. Failed pins or changed identities stop the
run. Do not overwrite source evidence or an existing generated report; append
a new version if a correction is necessary. Keep the original dirty checkout
untouched. No API or official-page requests are needed by this audit.

## Artifacts and Notes

Keep implementation hashes, original source pins, collection clocks, raw cells,
arithmetic exceptions, full population and explicit missingness in the report.
The guide's October collection clock is not proof of earlier publication.

## Interfaces and Dependencies

Use standard-library Decimal and existing parser functions. Expose `operand`,
`measure`, `summarize` and `audit`; no new package dependency. The CLI has no
write/network/fit path. Both A24/B34 fit allowances remain exhausted.

## Outcomes & Retrospective

At 2026-10-20T19:00:36.981995Z, v3 completed with all 11,523 records/1,156 races.
It reproduces v2's research values after a lint-only explicit zip setting.
28,848 equations match, 4,289 endpoints are unsupported and one has missing
operands. One cumulative-order conflict is preserved. Checked final-600
measurements remain for 7,694 rows, with 3,179 current/prior supported records.
Independent raw-cell Decimal arithmetic and SQLite pair counts reproduce
the result. Related tests passed 312 cases, including 37 new cases and the
immutable report/code-hash test. Ruff lint and format checks passed.
Required CI/normal merge receipt remains to be recorded on the PR.
The 70% goal is unmet; future dates, roster and N remain unset.

Initial plan: progress from structural repeat counts to original measurement
validation without turning post-race historical snapshots into pre-race examples.
Updated after real execution: local equation agreement was insufficient;
explicit cumulative-order checks found a source anomaly hidden by a blank
segment. The final immutable report and detailed version comparison are in
`docs/research/2026-10-20-longitudinal-time-operands.md`.
