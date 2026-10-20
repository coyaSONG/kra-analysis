# Audit historical time fields without retraining

This living ExecPlan follows `.agent/PLANS.md`. It uses the isolated research
checkout and changes neither A24/B34 nor the future protocol.

## Purpose / Big Picture


Current frozen models use rank-based history but not raw elapsed or sectional
times. Before proposing another feature, establish which original fields are
present, positive, zero or missing per physical venue. A zero in another
venue's field must not silently become a zero-second observation. This
read-only inventory is a source-quality decision, not a new model experiment.

## Progress


- [x] (2026-10-20) Confirmed previous progress: PR123 normally merged; checkout
  is clean at merge `9259ed5`. Read development results and existing May audit.
- [x] (2026-10-20) Checked official API214 metadata and one original raw schema.
- [x] Added raw-field inventory and identity/state tests.
- [x] (2026-10-20) Replayed all 1,029 records in 102 races; preserved aggregate
  report SHA `f844015088ae10ec754bbbfa8e2f0fc0867c9bd58881bdd16bdfed454baee75c`.
- [x] Documented source register, uncertainties and next semantic reconciliation.
- [x] Local final related tests: 125 passed in 1.18s; Ruff check/format passed.
- [ ] Test, review, commit, push and normally merge after required CI.

## Surprises & Discoveries


The API exposes venue-specific names and many zero values in other venues'
columns. Current rank/time support checks do not verify sectional semantics.
The public API description defines S1F/G1F/G3F locations but does not establish
every raw field's elapsed-versus-cumulative convention.

All 30 time-named fields are present on all 1,029 rows, but only 1,011 total
times are positive; 18 are zero. Positive time is not synonymous with usable
finish: one of the positive rows has rank 91 and a disqualification note.
The existing source conflict policy still withholds that entire race.

## Decision Log


Decision: audit the existing complete May 1-14 acquisition inventory, not
select races based on October accuracy. Preserve empty/unresolved unit statuses,
all runner exceptions and separate value states. Rationale: this window has
original API bytes and known official HTML comparison evidence; no additional
collection or learning is needed. Date/Author: 2026-10-20 / Codex.

Decision: only profile raw values after existing frozen replay succeeds and
join by date/venue/race/gate/horse, never page order. No unit conversion,
feature creation, imputation, targets or fit is authorized. Rationale: source
provenance does not establish comparability across courses or time definitions.
Date/Author: 2026-10-20 / Codex.

## Outcomes & Retrospective


Real replay and local tests are complete. The report preserves 12 row-bearing
and 44 empty-unconfirmed units without treating empty responses as no races.
It establishes raw field inventory only, not unit semantics or training
eligibility. All empirical performance claims remain those of the previous
publications. The 70% goal is not achieved. Remote CI and merge are pending;
the associated PR completion comment records those later lifecycle facts.

## Context and Orientation


Use `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf`.
`frozen_history_view.replay_frozen` rebuilds the chosen seed from original
receipts; `kra_result_snapshot.replay_result_pages` exposes validated raw rows.
New `history_time_audit` joins those rows back to the seed, then counts raw
field states. Its output has no predictions or training eligibility.

The original archive is
`.cache/autoresearch/observed-history-extension-20260501-14`.
Seed SHA256 is
`561bcfdc6fe2c4733e571b8c77034a2753e88794d5d7d3a6ee5d2ee2f25a5407`.
The historical source-clock bound is `2026-10-16T01:20:00Z`, not today's
analysis timestamp. This bounds local acquisition only; it does not show that
October-acquired observations were available before their May races.

## Plan of Work


First implement and test the source-state profiler. Then execute it once on
the original full seed with no API calls, retaining a timestamped derived
report via the existing exclusive writer. Finally publish aggregate evidence
and explicit limits, run regression checks and normally merge. Do not change
the consumed model inputs or any prior reports.

## Concrete Steps


From the isolated checkout:

    PYTHONPATH=packages/scripts PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest -q -p no:cacheprovider packages/scripts/autoresearch/tests/test_history_time_audit.py

Call `history_time_audit.audit` with the archive, seed path/hash and source
bound above. Preserve its returned JSON using the existing append-only `save`
helper, never overwriting an earlier report. Record exact output hash/counts.

Saved report:
`docs/research/experiments/2026-10-20-history-time-audit/report.json`.
The source-quality narrative and register are in
`docs/research/2026-10-20-history-time-source-audit.md`.

Executed tests:

    env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts .venv/bin/python -B -m pytest -q -p no:cacheprovider packages/scripts/autoresearch/tests/test_history_time_audit.py packages/scripts/autoresearch/tests/test_frozen_partial_history.py packages/scripts/autoresearch/tests/test_observed_history_seed.py packages/scripts/autoresearch/tests/test_kra_result_snapshot.py packages/scripts/autoresearch/tests/test_observed_result_history.py

    125 passed in 1.18s

The first command mistakenly named nonexistent `test_frozen_history_view.py`
and executed zero tests. After discovering the actual test paths, the initial
subset passed 107 tests; the final expanded set above is the reported result.
Actual source replay invoked no collectors, training or prediction generation.
Two end-to-end synthetic tests additionally trap network/process calls and
reject a changed original. Six original frozen model/receipt/registry/prediction
hashes remain unchanged. A format check initially lacked `--no-cache` and
hit the read-only cache restriction; the no-cache check passed.

## Validation and Acceptance


Tests distinguish absent/null/empty/boolean/invalid/nonfinite/negative/zero/
positive values. Duplicate, missing or wrong horse identities and changed
elapsed values must fail. Every field's state counts must sum to its venue's
full row count. Actual execution must join all seed records and retain
non-row units separately. No subsection coverage is an accuracy denominator.

## Idempotence and Recovery


CLI is stdout-only. The companion writer refuses an existing destination.
An absent/corrupt raw archive is a blocker, never replaced by a current API
response or a synthetic value. All old source bytes remain untouched.

## Artifacts and Notes


Official API description: https://www.data.go.kr/data/15063979/openapi.do.
Existing source evidence: `docs/research/2026-10-15-early-may-history.md`.
Any public report contains aggregate states and original pins, not credentials.

## Interfaces and Dependencies


`history_time_audit.audit(root, seed_path, seed_sha, cutoff)` returns the report;
`join_rows` enforces exact identity/value linkage; `profile` returns counts
without interpreting time units. Use the existing Python standard library and
archive replay helpers. No new dependencies or model changes.

Revision (2026-10-20): recorded real field-state findings, exact artifact hash,
the corrected test command and next semantic reconciliation work. Presence and
positive numeric values are explicitly not treated as feature readiness.
