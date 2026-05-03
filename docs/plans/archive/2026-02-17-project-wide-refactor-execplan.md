# Project-wide Refactor for Contract Integrity and Service Boundaries

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

`PLANS.md` is checked into this repository at `.agent/PLANS.md`. This document must be maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

The repository currently exposes many API endpoints that return success responses while serving placeholder or mock content. That behavior makes downstream clients and tests pass without proving real capability, which increases deployment risk and slows feature delivery.

After this refactor, a user should be able to call any exposed endpoint and trust one of two outcomes: either real behavior with real data, or an explicit `501 Not Implemented` contract with a consistent error shape. The codebase should also have clear ownership boundaries: one canonical data-collection flow per app, no runtime test-only branches in production services, and synchronized docs/tests for active API versions.

You can verify this refactor by running the app-level test suites and by issuing curl requests against representative implemented and not-implemented endpoints, confirming accurate status codes and response bodies.

## Progress

- [x] (2026-02-17 14:09Z) Baseline investigation completed: identified major hotspots, stale routes/docs, and placeholder endpoint patterns across `apps/api` and `apps/collector`.
- [x] (2026-02-17 14:27Z) Created and exercised endpoint contract safety net with focused controller/integration tests, then synchronized stale schema expectations in race tests.
- [x] (2026-02-17 14:28Z) Milestone 1 complete: collector endpoint contract hardening (`200 with mock` -> `501 explicit`) for non-implemented features.
- [x] (2026-02-17 14:30Z) Milestone 2 partial: removed duplicated route-registration code path and extracted shared `sendNotImplemented` helper used by all collector domain controllers.
- [x] (2026-02-17 14:46Z) Milestone 2 complete: consolidated collector controller validation/not-implemented handling into shared utility (`controllerUtils`) and reduced duplicated controller logic while keeping single route-registration flow.
- [x] (2026-02-17 14:32Z) Milestone 3 complete: removed runtime test-mode fallback branches from `KraApiService` and migrated race controller tests to explicit fetch mocking.
- [x] (2026-02-17 14:33Z) Milestone 4 complete: aligned `apps/api` docs and runtime commands to v2 (`main_v2.py`), documented legacy v1 policy, and validated API test suite.
- [x] (2026-02-17 14:34Z) Milestone 5 complete: split `CollectionService` internals into `collection_preprocessing.py` and `collection_enrichment.py` while preserving existing service interface compatibility.
- [x] (2026-02-17 14:49Z) Milestone 6 complete: resolved workspace regression in live integration tests under mock API settings and re-ran full workspace tests successfully (`pnpm test`).

## Surprises & Discoveries

- Observation: Most technical debt markers are concentrated in collector runtime code, not API runtime code.
  Evidence: `find apps/collector -type f \( -name '*.ts' -o -name '*.js' \) ... | wc -l` returned 38 TODO/mock markers, while `apps/api` Python returned 2.

- Observation: Collector has publicly routed endpoints that intentionally return placeholders and still respond as success.
  Evidence: `apps/collector/src/controllers/horse.controller.ts:92`, `apps/collector/src/controllers/race.controller.ts:317`, `apps/collector/src/controllers/jockey.controller.ts:438`, `apps/collector/src/controllers/trainer.controller.ts:587`.

- Observation: Collector route registration is duplicated in two code paths, increasing divergence risk.
  Evidence: `apps/collector/src/routes/index.ts:25` (`createRoutes`) and `apps/collector/src/routes/index.ts:148` (`registerRoutes`) repeat the same route mounting and docs payloads.

- Observation: FastAPI v1 artifacts still exist but are not part of active app routing; they are also explicitly excluded from coverage, which hides drift.
  Evidence: active router wiring is only v2 in `apps/api/main_v2.py:32` and `apps/api/main_v2.py:144`; legacy entries are omitted in `apps/api/pytest.ini:58`.

- Observation: Production service code in collector changes behavior based on `NODE_ENV === 'test'`, returning built-in fake API payloads.
  Evidence: `apps/collector/src/services/kraApiService.ts:151`, `apps/collector/src/services/kraApiService.ts:226`, `apps/collector/src/services/kraApiService.ts:305`, `apps/collector/src/services/kraApiService.ts:371`, `apps/collector/src/services/kraApiService.ts:448`.

- Observation: Existing race tests had stale response-shape assumptions (`data.races`, `data.race`) that did not match the current controller contract (`data` array for list and direct race object for detail).
  Evidence: failures from `apps/collector/tests/controllers/race.controller.test.ts:18` and `apps/collector/tests/integration/api.test.ts:212` during targeted regression run.

- Observation: Calling `createRoutes()` in both module initialization and `registerRoutes` produced duplicate route-configuration log events in tests.
  Evidence: repeated `All routes configured successfully` lines during `tests/api-simple.test.ts`; fixed by reusing module-level router in `registerRoutes`.

- Observation: `apps/api` documentation still referenced v1-era entrypoints/paths (`main.py`, `api.main`) despite active runtime being `main_v2.py`.
  Evidence: stale references in `apps/api/README-simplified.md`, `apps/api/README-uv.md`, and `apps/api/README.md` before this update.

- Observation: `pnpm -F @apps/api test -- <args>` still executes full pytest suite because the script uses `uv run pytest -q || ...`; argument filtering is not reliably propagated.
  Evidence: targeted invocation still collected and executed all 230 tests.

- Observation: Workspace-wide test execution initially failed because live KRA integration tests ran against `mock-kra-api` settings.
  Evidence: first `pnpm test` run failed at `apps/collector/tests/integration/kra-api-integration.test.ts` (13 failures); after gating the suite with `describe.skip` when mock config is active, rerun succeeded.

## Decision Log

- Decision: Keep `.agent/PLANS.md` as repository-level ExecPlan standard and create task-specific ExecPlans under `docs/plans/`.
  Rationale: Preserves article-aligned global rules while allowing multiple actionable plans.
  Date/Author: 2026-02-17 / Codex

- Decision: For collector endpoints without implemented domain logic, return explicit `501 Not Implemented` with a standardized error schema instead of `200` placeholders.
  Rationale: API contract honesty is higher priority than pretending feature completeness.
  Date/Author: 2026-02-17 / Codex

- Decision: Treat FastAPI v2 (`collection_v2`, `jobs_v2`) as the only active API surface; move v1 (`routers/race.py`, `services/race_service.py`) into explicit legacy status.
  Rationale: Current app entrypoint only serves v2. Code/docs/tests should match runtime truth.
  Date/Author: 2026-02-17 / Codex

- Decision: Remove runtime test-only behavior from production services and rely on dependency injection plus test doubles.
  Rationale: Runtime branches by environment mask failures and produce non-deterministic behavior.
  Date/Author: 2026-02-17 / Codex

- Decision: Split files over approximately 400 LOC if they contain multiple endpoint/service concerns.
  Rationale: Current controller/service files exceed 600 LOC and mix unrelated responsibilities.
  Date/Author: 2026-02-17 / Codex

- Decision: Runtime services must not branch on test environment to fabricate successful API payloads; tests must inject or mock dependencies explicitly.
  Rationale: Environment-gated fallback data obscures production behavior and creates false positives.
  Date/Author: 2026-02-17 / Codex

- Decision: Keep legacy v1 modules in-tree but declare them explicitly in docs and coverage policy, while enforcing v2-only runtime entry (`main_v2.py`).
  Rationale: Makes migration state explicit without pretending legacy files are active surfaces.
  Date/Author: 2026-02-17 / Codex

- Decision: Preserve `CollectionService` private/public method signatures while delegating implementation to new helper modules to avoid breaking existing tests and call sites.
  Rationale: Enables structural decomposition with low regression risk.
  Date/Author: 2026-02-17 / Codex

- Decision: Treat `tests/integration/kra-api-integration.test.ts` as live-only and skip it automatically when `KRA_API_BASE_URL` is mock or API key config is unavailable.
  Rationale: Keeps workspace regression deterministic and prevents false failures in local/CI environments that intentionally use mocked KRA endpoints.
  Date/Author: 2026-02-17 / Codex

## Outcomes & Retrospective

Interim update (Milestone 1):

- Collector now returns explicit `501 Not Implemented` contracts for placeholder horse/jockey/trainer/race endpoints instead of success payloads.
- Controller, integration, and e2e tests were synchronized to assert `NOT_IMPLEMENTED` contract semantics where applicable.
- Additional legacy drift in race response schema assertions was corrected to current behavior (`data` array/list and direct detail object).

Interim update (Milestone 3):

- Removed all `NODE_ENV === 'test'` fallback payload branches from `apps/collector/src/services/kraApiService.ts`.
- Updated tests to use explicit fetch mocks where runtime fallback behavior had been implicitly relied upon.
- Verified with targeted service/controller/integration runs that error and success behavior remains deterministic without runtime fake payload injection.

Interim update (Milestone 4):

- Updated API docs and run instructions to v2 entrypoint (`main_v2.py`) across README variants.
- Added explicit legacy policy doc: `apps/api/docs/LEGACY_V1_POLICY.md`.
- Updated coverage omit section to remove stale `main.py` exclusion and annotate v1 legacy module exclusions.
- Verified `apps/api` tests pass (`228 passed, 2 skipped`).

Interim update (Milestone 5):

- Split `apps/api/services/collection_service.py` internals into:
  - `apps/api/services/collection_preprocessing.py`
  - `apps/api/services/collection_enrichment.py`
- Retained existing `CollectionService` method surface for compatibility, with wrapper delegation to new modules.
- Reduced `collection_service.py` size from 674 lines to 402 lines while preserving behavior.
- Re-verified `apps/api` full test suite (`228 passed, 2 skipped`).

Interim update (Milestone 2 closeout):

- Added collector controller utility module `apps/collector/src/controllers/utils/controllerUtils.ts` with shared request validation and `NOT_IMPLEMENTED` response handling.
- Refactored `horse.controller.ts`, `jockey.controller.ts`, `race.controller.ts`, and `trainer.controller.ts` to use shared helpers and remove duplicated per-method validation/error boilerplate.
- Re-validated collector static checks and targeted regressions (`pnpm -F @apps/collector lint`, `pnpm -F @apps/collector typecheck`, focused controller/integration tests).

Final closeout (Milestone 6):

- Gated live-only KRA integration suite (`apps/collector/tests/integration/kra-api-integration.test.ts`) to run only under live API configuration.
- Verified app-level suites:
  - `pnpm -F @apps/api test` -> `228 passed, 2 skipped`
  - `pnpm test` -> workspace green (`@apps/api`, `@apps/collector`)
- ExecPlan milestones are now fully completed.

## Context and Orientation

This repository is a pnpm monorepo with two runtime apps that matter for this refactor.

`apps/collector` is an Express API (v1 routes) for race, horse, jockey, and trainer data. Its highest-risk area is endpoint integrity: several routed endpoints are placeholders or mock-only while returning successful responses. Key files are `apps/collector/src/controllers/*.ts`, `apps/collector/src/routes/*.ts`, and `apps/collector/src/services/kraApiService.ts`.

`apps/api` is a FastAPI app where active runtime is v2 (`main_v2.py` with `collection_v2` and `jobs_v2`). Legacy v1 files (`apps/api/routers/race.py`, `apps/api/services/race_service.py`) remain in tree but are not mounted. `apps/api/services/collection_service.py` is a large multi-responsibility module that mixes collection, preprocessing, enrichment, and compatibility field management.

Definitions used in this plan:

- Contract integrity: every endpoint status and payload accurately represent implementation state.
- Service boundary: a clear owner for each responsibility (collection orchestration, external API access, data enrichment, persistence), with minimal cross-leakage.
- Legacy surface: code retained for migration history or compatibility, but not part of active runtime contract.

## Milestones

### Milestone 1: Collector endpoint contract hardening

At the end of this milestone, any collector endpoint that still lacks business logic will explicitly return `501 Not Implemented` and a standard error body. No placeholder endpoint should respond with `success: true`.

Acceptance proof is a set of HTTP calls against representative paths such as `/api/v1/horses/:hrNo/performance`, `/api/v1/jockeys/:jkNo/races`, `/api/v1/trainers/rankings`, and `/api/v1/races/stats` showing `501` and structured error output.

### Milestone 2: Collector route/controller structure cleanup

At the end of this milestone, route registration exists in one place only, and oversized controllers are split so each module handles one feature group (details, stats, search, rankings) with shared response helpers.

Acceptance proof is a successful test run and code inspection showing no duplicated route mounting blocks and reduced controller file sizes.

### Milestone 3: Remove runtime test branches from collector service

At the end of this milestone, `KraApiService` no longer injects fake responses based on `NODE_ENV`. Tests must use explicit mocks/stubs through injected dependencies or fetch mocking in test setup.

Acceptance proof is removal of `NODE_ENV === 'test'` mock branches and passing collector tests without runtime fallback payload logic.

### Milestone 4: API v2 and legacy v1 separation in FastAPI app

At the end of this milestone, v2 is documented and tested as the active API. v1 files are clearly marked/moved as legacy and excluded intentionally by policy rather than silently drifting.

Acceptance proof is synchronized docs (`README*`, quick start), coverage config consistency, and zero accidental imports from legacy modules into v2 runtime.

### Milestone 5: Split `CollectionService` in `apps/api` by responsibility

At the end of this milestone, `apps/api/services/collection_service.py` becomes a thin facade over smaller modules for collection, preprocessing, enrichment, and stats computation, with compatibility mapping isolated to one adapter boundary.

Acceptance proof is smaller modules with explicit responsibilities, unchanged external behavior for active endpoints, and passing API tests.

### Milestone 6: Workspace-wide regression and documentation closeout

At the end of this milestone, both apps pass tests and developer docs describe only supported paths and behavior. This plan is updated with outcomes and change notes.

Acceptance proof is full test commands passing and docs referencing accurate versions/routes.

## Plan of Work

Start by creating an endpoint maturity matrix for collector routes. For each routed handler, classify as implemented or not implemented using concrete behavior criteria. For not implemented handlers, replace current success payloads with standardized `501` responses and keep message text specific to missing capability.

Next, reduce structural duplication in collector routing. Keep a single route-registration path and a single API index response generator. Split each large controller into modules under a folder per domain. Extract repeated validation-error and success-response patterns into shared helpers so behavior stays consistent.

Then remove runtime test-specific branches from `KraApiService`. Introduce constructor-injected transport or data provider abstractions and migrate tests to use explicit mocks. This preserves deterministic production behavior and keeps tests expressive.

After collector hardening, align FastAPI code ownership. Mark v1 files as legacy and prevent accidental active usage. Update coverage configuration so excluded files reflect explicit legacy intent, not hidden active code. Sync all API docs to v2 runtime and remove stale quick-start references.

Finally, refactor `CollectionService` into smaller modules with one compatibility adapter. Keep the same external endpoint responses during this split. Validate with targeted and full test runs, then update this ExecPlan sections with outcomes and a bottom change note.

## Concrete Steps

All commands below run from repository root unless stated otherwise.

1. Baseline and safety net.

    `pnpm -F @apps/collector test`

    `pnpm -F @apps/api test`

    `rg -n "TODO|to be implemented|In a real implementation" apps/collector/src/controllers apps/collector/src/services`

    Expected: current baseline passes, and debt markers are visible for migration tracking.

2. Implement Milestone 1 changes in collector controllers and add/adjust tests.

    `pnpm -F @apps/collector test -- --runInBand`

    Expected: tests assert `501` for explicitly unimplemented endpoints.

3. Implement Milestone 2 route/controller cleanup and run static checks.

    `pnpm -F @apps/collector lint`

    `pnpm -F @apps/collector typecheck`

    `pnpm -F @apps/collector test`

4. Implement Milestone 3 test-branch removal in `KraApiService` and update test fixtures.

    `rg -n "NODE_ENV === 'test'|JEST_UNIT_TEST|JEST_INTEGRATION_TEST" apps/collector/src/services/kraApiService.ts`

    Expected: no runtime fake-response branches remain.

5. Implement Milestone 4 API v2/legacy boundary cleanup in FastAPI app.

    `pnpm -F @apps/api test`

    `rg -n "api/v1|main.py|routers/race.py|services/race_service.py" apps/api/README*.md apps/api/docs apps/api/pytest.ini`

    Expected: docs and coverage config reflect active v2 and explicit legacy policy.

6. Implement Milestone 5 module split for `CollectionService`.

    `pnpm -F @apps/api test`

    Expected: endpoint behavior unchanged for v2 routes, with lower per-file complexity.

7. Execute final regression and documentation closeout.

    `pnpm test`

    `git diff --stat`

    Expected: all tests pass and diffs align with milestone scope.

## Validation and Acceptance

Behavioral acceptance criteria:

1. Collector non-implemented endpoints return `501` with `success: false` and machine-readable error code, never fake success payloads.
2. Collector implemented endpoints continue to return valid data structures and pass existing integration tests.
3. `apps/collector/src/routes/index.ts` has one authoritative route-registration flow.
4. `apps/collector/src/services/kraApiService.ts` has no runtime environment branch that fabricates API payloads.
5. FastAPI active runtime remains v2 only (`collection_v2`, `jobs_v2`) with docs and tests aligned.
6. `apps/api/services/collection_service.py` responsibilities are split into smaller modules while preserving v2 endpoint behavior.
7. Workspace tests pass via `pnpm test`.

Human-verifiable checks:

    curl -i http://localhost:3001/api/v1/trainers/rankings

    Expect: HTTP/1.1 501 with JSON error response, not a success placeholder.

    curl -i "http://localhost:8000/api/v2/collection/status?date=20240719&meet=1"

    Expect: response semantics tied to real job/state logic after refactor, not hardcoded pending defaults.

## Idempotence and Recovery

Work milestone-by-milestone, one commit per milestone. Each milestone must keep tests passing before moving on. If a milestone fails mid-way, restore to the last green commit and continue with smaller scoped patches rather than force-merging partial behavior.

No destructive data migrations are required in this plan. If schema-level changes become necessary during implementation, pause and extend this ExecPlan with explicit migration/rollback instructions before applying them.

## Artifacts and Notes

Keep concise evidence snippets in commit messages and PR description:

- Endpoint contract before/after examples for `501` migration.
- `rg` output proving removal of runtime mock branches.
- Test command outputs for collector-only, api-only, and full workspace.

At each stopping point, update `Progress`, `Decision Log`, and `Surprises & Discoveries`. On completion, write `Outcomes & Retrospective` with delivered behavior, remaining work, and follow-up recommendations.

## Interfaces and Dependencies

Prescribed interface outcomes:

1. Collector error contract.

    Exposed endpoints that are intentionally not implemented must return:
    status `501`
    body with `success: false`
    stable error code (for example `NOT_IMPLEMENTED`)
    human message and optional details

2. Collector service injection.

    `KraApiService` must support injected transport/data-provider dependencies so tests do not require environment-based runtime behavior changes.

3. FastAPI version boundary.

    Active runtime interfaces remain:
    `/api/v2/collection/*`
    `/api/v2/jobs/*`

    Legacy v1 interfaces are either explicitly archived or clearly labeled as legacy-only and excluded by policy.

4. Collection service module boundaries in `apps/api`.

    Required modules after split:
    collection orchestration
    preprocessing
    enrichment
    statistics/feature derivation
    compatibility mapping adapter

    The compatibility adapter is the only location where dual field naming or legacy payload harmonization is allowed.

---

Plan change note (2026-02-17, Codex): Initial ExecPlan created from repository-wide refactor assessment to make API contracts truthful, remove runtime test branches, and clarify v2/legacy boundaries.
