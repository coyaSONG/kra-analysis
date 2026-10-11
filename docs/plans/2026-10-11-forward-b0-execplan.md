# Execute B0 submissions against a PostgreSQL forward ledger

This living ExecPlan follows `.agent/PLANS.md`.

## Purpose / Big Picture

Create an executable path from official dated schedules and API26 originals to one immutable baseline prediction per frozen race, with server-side evidence that another transaction saw the committed prediction before its deadline. B0 means a deliberately untrained baseline selecting the stable horse IDs at the three smallest numeric gates. It is an operational control, not a claim of strong performance. The research target remains exact unordered three-horse success of 70% across the entire frozen universe using pre-race information only.

## Progress

- [x] Revalidated PR71 merged at a3f2489c27a8c3d572b8b51b46515bcf67bea64f; created isolated `codex/forward-b0-registration` from current main.
- [x] Read repository plan rules, existing schedule/entry replay, DB session behavior and actual PostgreSQL migration test patterns. Local PostgreSQL binaries and Docker daemon are unavailable; CI already provides PostgreSQL16.
- [ ] Implement isolated append-only SQL ledger and service, including a separate committed-row witness.
- [ ] Connect official capture/replay and all-race B0 execution in an API-package CLI; preserve original payloads on retry.
- [ ] Test real PostgreSQL concurrent requests, deadline boundaries, permissions, retry and complete-population reports in CI.
- [ ] Run an actual next-card check and report configuration/card limitations without claiming future performance.
- [ ] Commit, push and normally merge validated work.

## Context and Orientation

Work in `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf`; do not edit the owner's dirty checkout. `packages/scripts/autoresearch/kra_schedule_snapshot.py` preserves four dated official pages, replays coverage and can create a local universe candidate. A universe is the complete fixed list of races, independent of feature or result availability. Each race's cutoff is thirty minutes before its scheduled start. `kra_entry_sheet_snapshot.py` captures API26; `kra_race_card_pdf_replay.py::replay_entry_pages` verifies its raw pages without requiring PDF input. `shared.kra_entry_sheet.build_entry_snapshot` strictly reconstructs a complete pre-race roster. PR71 history is deliberately not consumed by B0.

The main API DB session dependency does not commit automatically. The new service uses explicit asyncpg transactions and a fresh connection for observation. It must never infer committed-before-deadline from transaction start or insert return time. A witness is a later DB read of a committed row followed by DB `clock_timestamp()`. Stored top-level transaction ID prevents a function being used to witness its own uncommitted insert, including through a savepoint.

## Plan of Work

Add `apps/api/infrastructure/forward_ledger.sql` as an explicit research-schema installation, not an automatic production migration. Tables hold frozen study membership, original submission text and hashes, and first observation times. No foreign key links to mutable operational Race rows. Immutable triggers reject update/delete; runtime gets read and narrowly scoped function execution only. A separate owner performs installation and freeze. Schema-qualified SQL and fixed function search paths prevent caller-controlled lookup. Owner/DB-clock trust remains explicit; this is not external notarization.

Add `apps/api/services/forward_ledger.py` for canonical payload construction, B0 validation, owner freeze, runtime registration plus independent witness and full membership left-join reporting. Freeze preserves every race and refuses late population creation. Runtime cannot change arms, membership or deadlines. Identical payloads return original receipts; different payloads conflict. Persist original request bytes before sending so an interrupted retry cannot silently recompute from a changed roster.

Add `apps/api/scripts/run_forward_b0.py` with explicit install and run commands. It uses the existing official collection/replay functions; no synthetic-data mode is available in the operational CLI. A day not fully published reports `awaiting_card`, not an empty successful universe. After freeze, iterate all members, reuse an existing submission before collecting new data, and retain failures in the final ledger. Missing history never blocks B0. Missing/invalid roster leaves a failed slot, never an invented 1/2/3 combination. Configuration comes from named environment variables, never DSNs or keys printed to logs.

## Milestones

First establish the service and SQL contracts with pure B0 tests. Then add actual PostgreSQL integration tests using disposable schemas and a restricted role, proving transactions and permissions instead of mocking them. Finally connect the operational collector and verify both awaiting-card and synthetic full-path test scenarios. The synthetic scenarios establish software behavior only. Real future evidence starts only after real official cards, real server freeze and real pre-deadline submission witnesses exist.

## Validation and Acceptance

From the repository root run API tests with the existing environment and `PYTHONPATH=apps/api:packages/scripts`. Pure tests must reject duplicate identities, string-sort errors, short rosters and changed payloads. PostgreSQL integration tests use only loopback `test_db` via `KRA_MIGRATION_TEST_DSN`, fail rather than silently skip in CI, and clean up only their own random schema/role. Test simultaneous same/different requests, locks held through deadline, late commits, same-transaction/savepoint witnesses, lost acknowledgments, explicit commits, denied direct writes and all-membership reports. Existing API and 410 research regressions must remain valid. Required checks must pass before normal merge; no force/admin merge.

## Idempotence and Recovery

Install is explicit and refuses an existing schema rather than replacing it. Freeze is idempotent only for identical canonical bytes under one study ID. A single operational study/date identity cannot acquire parallel aliases. Runtime submission locks existing membership, then checks the current server time. Retry reads original receipts and saved request files. Observation after the deadline remains unproven rather than backdated. Do not deploy to production or create credentials implicitly; report missing owner/runtime configuration. No real key or DSN belongs in artifacts.

## Surprises & Discoveries

The local Docker CLI is installed but no Docker socket exists, and PostgreSQL executables are absent. Real DB validation must therefore use the repository's already-configured disposable CI PostgreSQL service unless another authorized local service becomes available. Existing API migrations cannot be repurposed as proof that this research ledger is installed.

## Decision Log

Decision (2026-10-11): Use a separately installed research schema and restricted runtime role, keeping production migration head unchanged. This permits real CI testing and an explicit deployment path without making the unrelated API fail startup before research deployment.

Decision (2026-10-11): Follow the completed Pro consultation from PR71: B0 consumes only verified roster and fixed rule; history capture/status interpretation stays independent. No new consultation is needed to repeat advice already fully received. Consult again if new substantive uncertainty remains after tests.

## Outcomes & Retrospective

Pending. Actual 70% success is unproven. Future card availability and operational DB configuration are separate from code correctness and must remain separately reported.

## Interfaces and Dependencies

Use existing asyncpg, httpx, pytest and standard-library JSON/hashlib/datetime. PostgreSQL16 supplies `clock_timestamp`, `pg_current_xact_id` and SHA-256 functions. No new dependency or version change is planned. Keep I/O in the API-package script and deterministic selection/registration contracts in its service module. The first runtime arm is fixed as `b0_numeric_gate_v1`.

Revision note (2026-10-11): Created before implementation after inspecting authoritative current code and the completed Pro recommendation. The plan targets an executable registration path, not a further diagnostic registry.
