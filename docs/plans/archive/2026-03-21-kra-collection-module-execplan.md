# Introduce KRA Collection Module Facade

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

After this change, the collection API routes will call one public module instead of directly coordinating `CollectionWorkflow`, `CollectionService`, `ResultCollectionService`, and `JobService`. A contributor will be able to read one module entry point and understand how synchronous batch collection, asynchronous batch submission, status lookup, and result collection fit together. The change is visible by running the API tests for `/api/v2/collection/*` and observing that the routes still return the same HTTP behavior while their implementation now delegates through the new facade.

## Progress

- [x] (2026-03-21 02:35Z) Reviewed `.agent/PLANS.md`, current collection routes, workflow, service, job, result, and test files.
- [x] (2026-03-21 02:46Z) Added `apps/api/services/kra_collection_module.py` with query, command, and job interfaces plus the default implementation.
- [x] (2026-03-21 02:49Z) Switched `apps/api/routers/collection_v2.py` to use the new module instead of calling workflow and result service directly.
- [x] (2026-03-21 02:52Z) Updated route-facing tests to assert delegation through the new module and added focused module tests.
- [x] (2026-03-21 02:54Z) Ran targeted API tests without coverage gating and confirmed the selected collection tests pass.
- [x] (2026-03-21 02:54Z) Recorded the targeted coverage-gated run result showing 12 tests passed but repository-wide fail-under coverage blocked the command.
- [x] (2026-03-21 03:00Z) Updated remaining router error tests and README files to reflect the new facade module and current collection endpoints.
- [x] (2026-03-21 03:01Z) Re-ran the widened collection route/module test subset and confirmed 15 tests pass.

## Surprises & Discoveries

- Observation: synchronous batch collection currently fans out multiple coroutines that share one `AsyncSession`.
  Evidence: `apps/api/services/collection_workflow.py` passes the same `db` object into every `_collect_one_race(...)` task created by `asyncio.gather(...)`.

- Observation: request DTO options are currently not wired into the implementation.
  Evidence: `apps/api/models/collection_dto.py` defines `enrich`, `get_results`, `force_refresh`, and `parallel_count`, but route and service code only consume `date`, `meet`, and `race_numbers`.

- Observation: the targeted collection tests all passed immediately after the facade migration, but the first command still failed because the repository enforces whole-project coverage even for a small test subset.
  Evidence: `uv run pytest -q ...` reported `12 passed` followed by `Coverage failure: total of 32 is less than fail-under=75`; rerunning with `--no-cov` passed cleanly.

## Decision Log

- Decision: introduce a facade module shaped as `queries / commands / jobs` rather than a single `execute(...)` entry point.
  Rationale: read behavior, synchronous execution, and asynchronous submission are different contracts in the current application and should stay explicit at the call site.
  Date/Author: 2026-03-21 / Codex

- Decision: keep existing lower-level services in place and wrap them rather than deleting them during this refactor.
  Rationale: this reduces migration risk and preserves existing tests that exercise service-level behavior.
  Date/Author: 2026-03-21 / Codex

- Decision: make synchronous batch collection in the new facade use one request-scoped `AsyncSession` sequentially.
  Rationale: correctness is more important than preserving the current unsafe parallelism that shares one session across concurrent tasks.
  Date/Author: 2026-03-21 / Codex

- Decision: keep `CollectionWorkflow` intact for service-level compatibility tests even though the router no longer calls it directly.
  Rationale: the facade migration is safer when lower-level orchestration behavior remains available for existing unit tests and potential internal callers.
  Date/Author: 2026-03-21 / Codex

## Outcomes & Retrospective

The collection routes now delegate through `apps/api/services/kra_collection_module.py`, which centralizes status lookup, synchronous batch collection, result collection, and asynchronous batch submission behind one public API. The route contracts remain unchanged, and the targeted collection route tests and module tests pass.

This refactor intentionally stopped short of deleting `CollectionWorkflow` or removing the unused DTO options from `CollectionRequest`. The important architectural improvement is that the router no longer coordinates multiple lower-level services directly. A later cleanup can now remove or reshape older internal helpers without touching the route layer again.

## Context and Orientation

The active API runtime is `apps/api/main_v2.py`. The collection endpoints live in `apps/api/routers/collection_v2.py`. Today that router imports `CollectionWorkflow`, `CollectionService`, `JobService`, and `ResultCollectionService` and knows too much about which helper to call for each route. `apps/api/services/collection_workflow.py` handles synchronous batch planning and asynchronous batch job submission. `apps/api/services/collection_service.py` performs single-race collection and collection-status aggregation. `apps/api/services/result_collection_service.py` handles result parsing and persists final odds after a result is collected. `apps/api/services/job_service.py` creates jobs and dispatches background tasks through `apps/api/infrastructure/background_tasks.py`.

In this repository, a "facade" means one small public module that hides several lower-level services behind a simpler API. The facade for this task will expose three groups: queries for read-only status lookup, commands for synchronous collection actions, and jobs for asynchronous submission. The new module will live in `apps/api/services/kra_collection_module.py`.

The public route contracts must stay stable. `POST /api/v2/collection/` still returns `CollectionResponse`, returns HTTP 502 when every requested race fails, and returns status `partial` when only some races fail. `POST /api/v2/collection/async` still returns a job receipt wrapped in `CollectionResponse`. `GET /api/v2/collection/status` still returns `CollectionStatus`. `POST /api/v2/collection/result` still returns a `CollectionResponse` payload that contains the collected result entry.

## Plan of Work

Create `apps/api/services/kra_collection_module.py` and define small dataclasses for batch collection input, result collection input, collection status snapshot, collection outcome, and job receipt. In the same file, define three protocol-like interfaces or concrete helper classes named `CollectionQueries`, `CollectionCommands`, and `CollectionJobs`, then create a top-level `KRACollectionModule` implementation that exposes them as attributes.

Implement `CollectionQueries.get_status(...)` by delegating to `CollectionService.get_collection_status(...)` and wrapping the result in a typed snapshot object. Implement `CollectionCommands.collect_batch(...)` by normalizing `race_numbers`, obtaining a `KRAAPIService`, and calling `CollectionService.collect_race_data(...)` for each race while accumulating successes and failures. Keep this path sequential for the shared request session. Implement `CollectionCommands.collect_result(...)` by delegating to `ResultCollectionService.collect_result(...)`. Implement `CollectionJobs.submit_batch_collect(...)` by normalizing race numbers and delegating to `JobService.create_job(...)` plus `JobService.start_job(...)`, then returning a typed receipt.

Edit `apps/api/routers/collection_v2.py` so the router imports and instantiates the new module. The route functions should convert Pydantic request DTOs into module inputs, call the appropriate query, command, or job method, and then translate the typed result back into the existing `CollectionResponse` or `CollectionStatus` DTOs. Preserve existing HTTP status mapping and error handling.

Update route-facing tests in `apps/api/tests/integration/test_collection_workflow_router.py` and `apps/api/tests/unit/test_collection_result_router.py` so they monkeypatch the new module rather than the old workflow or result service globals. Add a new focused unit test file for `apps/api/services/kra_collection_module.py` that proves batch collection returns `partial` when one race fails and that job submission normalizes `race_numbers=None` to `1..15`.

## Concrete Steps

From the repository root:

    cd /Users/chsong/Developer/Personal/kra-analysis

Create the new module and update the router and tests using `apply_patch`.

Run the targeted tests from the repository root:

    pnpm -F @apps/api test -- tests/unit/test_kra_collection_module.py tests/unit/test_collection_result_router.py tests/integration/test_collection_workflow_router.py tests/unit/test_collection_router_errors.py tests/unit/test_collection_workflow.py

If the workspace test command is awkward, run the API tests directly:

    cd apps/api
    uv run pytest -q tests/unit/test_kra_collection_module.py tests/unit/test_collection_result_router.py tests/integration/test_collection_workflow_router.py tests/unit/test_collection_router_errors.py tests/unit/test_collection_workflow.py

Expected result after the implementation: all selected tests pass, and the router tests prove the routes delegate through the facade module.

Observed command transcript:

    cd /Users/chsong/Developer/Personal/kra-analysis/apps/api
    uv run pytest -q tests/unit/test_kra_collection_module.py tests/unit/test_collection_result_router.py tests/integration/test_collection_workflow_router.py tests/unit/test_collection_router_errors.py tests/unit/test_collection_workflow.py
    ...
    12 passed
    ERROR: Coverage failure: total of 32 is less than fail-under=75

    uv run pytest -q --no-cov tests/unit/test_kra_collection_module.py tests/unit/test_collection_result_router.py tests/integration/test_collection_workflow_router.py tests/unit/test_collection_router_errors.py tests/unit/test_collection_workflow.py
    ...
    12 passed in 0.18s

## Validation and Acceptance

Acceptance is behavioral. A contributor should be able to run the targeted tests and see that:

1. synchronous collection still returns HTTP 200 with `status=partial` when only some races fail,
2. synchronous collection still returns HTTP 502 with the aggregated error payload when every requested race fails,
3. asynchronous collection still returns HTTP 202 with a `job_id`,
4. result collection still returns HTTP 200 or HTTP 404/500 according to the underlying service outcome,
5. the new module tests prove the facade itself aggregates partial failures and normalizes default race ranges.

If manual verification is desired, start the API and issue the same curl examples documented in `apps/api/README.md`. The returned JSON schema must remain unchanged.

## Idempotence and Recovery

All edits in this plan are source-level changes and are safe to reapply by rerunning the patching steps carefully. If a route test fails after switching the router to the new module, compare the router's JSON response mapping against the previous implementation and restore the existing response DTO shape before retrying. Because this refactor is additive at the service layer, rollback is straightforward: revert `apps/api/routers/collection_v2.py` and remove `apps/api/services/kra_collection_module.py`.

## Artifacts and Notes

The most important evidence for this refactor will be concise pytest output showing the selected router and module tests passing. This section will be updated after test execution.

Key evidence:

    tests/unit/test_kra_collection_module.py ...                             [ 25%]
    tests/unit/test_collection_result_router.py ...                          [ 50%]
    tests/integration/test_collection_workflow_router.py ..                  [ 66%]
    tests/unit/test_collection_router_errors.py .                            [ 75%]
    tests/unit/test_collection_workflow.py ...                               [100%]
    ============================== 12 passed in 0.18s ==============================

    tests/unit/test_kra_collection_module.py ...                             [ 20%]
    tests/unit/test_collection_result_router.py ...                          [ 40%]
    tests/integration/test_collection_workflow_router.py ..                  [ 53%]
    tests/unit/test_collection_router_errors.py .                            [ 60%]
    tests/unit/test_collection_router_more_errors.py ...                     [ 80%]
    tests/unit/test_collection_workflow.py ...                               [100%]
    ============================== 15 passed in 0.24s ==============================

## Interfaces and Dependencies

Define the new public module in `apps/api/services/kra_collection_module.py`. The final file must contain stable names for:

- `BatchCollectInput`
- `ResultCollectInput`
- `CollectionStatusSnapshot`
- `CollectionOutcome`
- `JobReceipt`
- `KRACollectionModule`

The implementation may call existing classes from:

- `services.collection_service.CollectionService`
- `services.result_collection_service.ResultCollectionService`
- `services.job_service.JobService`
- `services.kra_api_service.get_kra_api_service`

The router in `apps/api/routers/collection_v2.py` must depend only on the new module plus request/response DTOs and FastAPI dependencies.

Revision note: Initial ExecPlan created to support the collection facade refactor and the route migration away from direct workflow/service coordination.

Revision note: Updated after implementation to record the new module, router migration, test coverage surprise, and targeted validation results.
