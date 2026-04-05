# Introduce Race Processing Workflow Boundary

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

After this change, single-race collection, preprocessing, enrichment, and odds collection will have one orchestration owner instead of spreading the lifecycle across `CollectionService`, pipeline stages, async tasks, and helper functions. A contributor will be able to read one workflow module and understand how a race moves from KRA fetch to persistence. The change is visible by running the collection service and task tests and observing that the external payloads, job updates, and persistence behavior remain the same while the orchestration now delegates through the new workflow boundary.

## Progress

- [x] (2026-04-05 14:27 KST) Reviewed `.agent/PLANS.md`, the current collection service, pipeline stages, async tasks, and existing collection tests.
- [x] (2026-04-05 14:38 KST) Added `apps/api/services/race_processing_workflow.py` with workflow commands/results, default KRA and SQLAlchemy adapters, and workflow orchestration for collect/materialize/odds.
- [x] (2026-04-05 14:38 KST) Switched `CollectionService` public collect/preprocess/enrich/odds entry points to workflow delegation while keeping legacy helper seams intact through bound callable injection.
- [x] (2026-04-05 14:42 KST) Added `apps/api/tests/unit/test_race_processing_workflow.py` and ran the selected collection, task, pipeline, and module pytest subsets successfully.
- [x] (2026-04-05 14:55 KST) Migrated async tasks, pipeline stages, `DataProcessingPipeline`, and `CollectionCommands` to instantiate the workflow directly instead of routing through `CollectionService`.
- [x] (2026-04-05 14:58 KST) Updated the affected async/module/stage tests for workflow-first execution paths and revalidated the core regression suite.
- [ ] (2026-04-05 14:58 KST) Reduce legacy wrappers and seam-heavy tests after direct workflow callers are in place.

## Surprises & Discoveries

- Observation: many existing tests monkeypatch `CollectionService` private helpers such as `_collect_horse_details`, `_save_race_data`, `_get_horse_past_performances`, `_get_jockey_stats`, and `_get_trainer_stats`.
  Evidence: `apps/api/tests/unit/test_collection_new_apis.py`, `apps/api/tests/unit/test_collection_partial_failure.py`, and `apps/api/tests/unit/test_collection_service_enrich.py` all replace those helpers directly.

- Observation: `enrich_race_data()` currently accepts a permissive fallback path that can enrich `raw_data` directly when `basic_data` and `enriched_data` are absent.
  Evidence: `apps/api/services/collection_service.py` selects `race.enriched_data or race.basic_data or race.raw_data`, and `apps/api/tests/unit/test_collection_service.py::test_enrich_race_data` depends on that fallback.

- Observation: blindly preprocessing `basic_data` before enrichment breaks existing tests that store minimal horse dictionaries without `win_odds`.
  Evidence: the first run of `tests/unit/test_collection_service_enrich.py` failed with `IndexError: list index out of range` because preprocessing filtered out every horse; narrowing preprocessing to collected-shape payloads fixed the regression and the rerun passed.

- Observation: several stage and task tests were asserting against `CollectionService` mocks even though the callers really care about lifecycle outcomes, not the intermediate adapter.
  Evidence: `tests/unit/test_pipeline_stages.py`, `tests/unit/test_async_tasks.py`, and `tests/unit/test_kra_collection_module.py` all needed to swap `CollectionService` monkeypatches for workflow doubles once the direct caller migration landed.

## Decision Log

- Decision: the first implementation slice will move orchestration ownership into a new workflow module but keep the old private helpers in `CollectionService`.
  Rationale: this preserves the existing test seams and lets the refactor land incrementally without rewriting the full test suite first.
  Date/Author: 2026-04-05 / Codex

- Decision: `CollectionService` public methods will delegate to the workflow using bound helper callables for horse bundle collection, preprocessing, enrichment, and save behavior.
  Rationale: this keeps current behavior stable while still making the workflow the new public owner of the lifecycle.
  Date/Author: 2026-04-05 / Codex

- Decision: `materialize(target='enriched')` will only preprocess `basic_data` when the payload looks like collected race data, identified by horses that include `win_odds`.
  Rationale: this preserves the new canonical ordering for real collected payloads without breaking legacy tests and fallback data that omit betting fields.
  Date/Author: 2026-04-05 / Codex

- Decision: async tasks, pipeline stages, and `CollectionCommands` will build `RaceProcessingWorkflow` directly, while `CollectionService` remains only as a compatibility surface for older callers and seam-heavy tests.
  Rationale: this removes the extra orchestration hop from production paths now, without forcing a full removal of the legacy adapter in the same change.
  Date/Author: 2026-04-05 / Codex

## Outcomes & Retrospective

The first two implementation slices landed successfully. `apps/api/services/race_processing_workflow.py` now owns the collect, materialize, and odds orchestration, while `CollectionService` has been reduced to a compatibility adapter that delegates through bound helper callables. The direct callers in async tasks, pipeline stages, `DataProcessingPipeline`, and `CollectionCommands` now instantiate the workflow directly, so the legacy adapter is no longer on the main execution path for those flows.

The remaining work is now cleanup: remove or shrink the legacy wrappers that are still only preserving old seams, and replace seam-heavy tests with boundary-style workflow tests where that reduces maintenance cost without losing coverage.

## Context and Orientation

The active single-race lifecycle currently lives in `apps/api/services/collection_service.py`. That file fetches KRA race data, fans out horse detail requests, persists collection failures and successful snapshots, preprocesses data, enriches data, and upserts odds. `apps/api/pipelines/stages.py` and `apps/api/tasks/async_tasks.py` call those entry points and therefore know too much about how the lifecycle is ordered.

In this repository, a "workflow boundary" means one public module that owns the sequence of steps for a business process. For this task the new owner will be `apps/api/services/race_processing_workflow.py`. The old `CollectionService` will stay in place as a compatibility adapter so route, pipeline, and task callers do not need to change all at once.

The tests that define the current external behavior live under `apps/api/tests/unit/`. The most important ones for this slice are `test_collection_service.py`, `test_collection_service_enrich.py`, `test_collection_partial_failure.py`, `test_collection_new_apis.py`, and `test_async_tasks.py`.

## Plan of Work

Create `apps/api/services/race_processing_workflow.py` and define the stable types needed for the workflow boundary: a race key, command objects for collect, materialize, and odds collection, result objects for those operations, and small protocol-style interfaces for the KRA source and race repository. Put the default SQLAlchemy and KRA adapters in the same file for this first slice so the reader can follow the complete lifecycle in one place.

Implement `RaceProcessingWorkflow.collect(...)` by moving the orchestration out of `CollectionService.collect_race_data(...)`. The workflow must still normalize race-level auxiliary API data, collect horse bundles, enforce the horse failure threshold, build the same payload shape, and persist either a collection failure or a successful collection snapshot.

Implement `RaceProcessingWorkflow.materialize(...)` so `target='preprocessed'` applies the current preprocessing helper and persists the result, while `target='enriched'` loads the current race snapshot, preserves the existing `enriched_data -> basic_data -> raw_data` fallback semantics, and calls the bound enrichment helper before persisting.

Implement `RaceProcessingWorkflow.collect_odds(...)` so it wraps the current odds fetch and upsert behavior but returns a typed result that `CollectionService.collect_race_odds(...)` can translate back into the old dict contract.

Edit `apps/api/services/collection_service.py` so the public collect, preprocess, enrich, and odds methods build a workflow instance using bound helper callables and delegate to it. Keep the private helpers in place because the current tests use them directly.

Add a small focused test file for the workflow itself and update any collection service tests that need to assert the new owner without changing their external behavior.

## Concrete Steps

From the repository root:

    cd /Users/chsong/Developer/Personal/kra-analysis

Create `apps/api/services/race_processing_workflow.py` and update `apps/api/services/collection_service.py` using `apply_patch`.

Run the targeted tests from the API package:

    cd apps/api
    uv run pytest -q --no-cov \
      tests/unit/test_race_processing_workflow.py \
      tests/unit/test_collection_service.py \
      tests/unit/test_collection_service_enrich.py \
      tests/unit/test_collection_partial_failure.py \
      tests/unit/test_collection_new_apis.py \
      tests/unit/test_async_tasks.py

Expected result after the slice lands: the selected tests pass and confirm that public collection/materialization behavior is unchanged even though the orchestration moved into the workflow.

Observed commands:

    cd /Users/chsong/Developer/Personal/kra-analysis/apps/api
    uv run pytest -q --no-cov \
      tests/unit/test_race_processing_workflow.py \
      tests/unit/test_collection_service.py \
      tests/unit/test_collection_service_enrich.py \
      tests/unit/test_collection_partial_failure.py \
      tests/unit/test_collection_new_apis.py \
      tests/unit/test_async_tasks.py
    ...
    33 passed in 0.30s

    uv run pytest -q --no-cov \
      tests/unit/test_collection_service_coverage.py \
      tests/unit/test_collection_service_edge_cases.py \
      tests/unit/test_collection_service_past_perf.py \
      tests/unit/test_collection_service_stats.py \
      tests/unit/test_pipeline_stages.py \
      tests/unit/test_data_pipeline.py \
      tests/unit/test_kra_collection_module.py
    ...
    65 passed in 0.34s

    uv run pytest -q --no-cov \
      tests/unit/test_async_tasks.py \
      tests/unit/test_kra_collection_module.py \
      tests/unit/test_pipeline_stages.py \
      tests/unit/test_data_pipeline.py \
      tests/unit/test_coverage_kra_core_adapter.py
    ...
    133 passed in 0.17s

    uv run pytest -q --no-cov \
      tests/unit/test_race_processing_workflow.py \
      tests/unit/test_collection_service.py \
      tests/unit/test_collection_service_enrich.py \
      tests/unit/test_collection_partial_failure.py \
      tests/unit/test_collection_new_apis.py \
      tests/unit/test_async_tasks.py \
      tests/unit/test_kra_collection_module.py \
      tests/unit/test_pipeline_stages.py \
      tests/unit/test_data_pipeline.py \
      tests/unit/test_coverage_kra_core_adapter.py
    ...
    162 passed in 0.37s

## Validation and Acceptance

Acceptance is behavioral. The selected tests must prove that:

1. single-race collection still returns the same dict payload and partial-failure metadata,
2. preprocessing and enrichment still persist to the `races` table using the existing field shapes,
3. odds collection still reports the same inserted-count and error dicts,
4. async task tests still observe the same job-status and log behavior through the `CollectionService` entry points,
5. the new workflow test proves that the workflow can be exercised directly with fake source/repository dependencies.

## Idempotence and Recovery

This slice is source-only and safe to reapply. If the workflow delegation breaks a legacy seam test, restore the missing behavior by injecting the old bound helper into the workflow rather than reintroducing orchestration logic into the caller. If the new workflow test fails after an edit, compare the returned payload dict against the current `CollectionService` test expectations before retrying.

## Artifacts and Notes

The most important evidence for this slice is the targeted pytest output showing that the workflow landed without changing caller-visible behavior.

Key evidence:

    tests/unit/test_race_processing_workflow.py ...                          [  9%]
    tests/unit/test_collection_service.py ..............                     [ 51%]
    tests/unit/test_collection_service_enrich.py ..                          [ 57%]
    tests/unit/test_collection_partial_failure.py ..                         [ 63%]
    tests/unit/test_collection_new_apis.py ........                          [ 87%]
    tests/unit/test_async_tasks.py ....                                      [100%]
    ============================== 33 passed in 0.30s ==============================

    tests/unit/test_collection_service_coverage.py .......................    [ 35%]
    tests/unit/test_collection_service_edge_cases.py ....                    [ 41%]
    tests/unit/test_collection_service_past_perf.py ..                       [ 44%]
    tests/unit/test_collection_service_stats.py ...                          [ 49%]
    tests/unit/test_pipeline_stages.py ......................                [ 83%]
    tests/unit/test_data_pipeline.py ........                                [ 95%]
    tests/unit/test_kra_collection_module.py ...                             [100%]
    ============================== 65 passed in 0.34s ==============================

    tests/unit/test_async_tasks.py ....                                      [  3%]
    tests/unit/test_kra_collection_module.py ...                             [  5%]
    tests/unit/test_pipeline_stages.py .......................               [ 22%]
    tests/unit/test_data_pipeline.py ........                                [ 28%]
    tests/unit/test_coverage_kra_core_adapter.py ........................... [ 48%]
    ....................................................................     [100%]
    ============================== 133 passed in 0.17s ==============================

    tests/unit/test_race_processing_workflow.py ...                          [  1%]
    tests/unit/test_collection_service.py ..............                     [ 10%]
    tests/unit/test_collection_service_enrich.py ..                          [ 11%]
    tests/unit/test_collection_partial_failure.py ..                         [ 12%]
    tests/unit/test_collection_new_apis.py ........                          [ 17%]
    tests/unit/test_async_tasks.py ....                                      [ 20%]
    tests/unit/test_kra_collection_module.py ...                             [ 22%]
    tests/unit/test_pipeline_stages.py .......................               [ 36%]
    tests/unit/test_data_pipeline.py ........                                [ 41%]
    tests/unit/test_coverage_kra_core_adapter.py ........................... [ 58%]
    ....................................................................     [100%]
    ============================== 162 passed in 0.37s ==============================

## Interfaces and Dependencies

Define the new workflow module in `apps/api/services/race_processing_workflow.py`. The final file for this slice must contain stable names for:

- `RaceKey`
- `CollectRaceCommand`
- `MaterializeRaceCommand`
- `CollectOddsCommand`
- `CollectedRace`
- `MaterializedRace`
- `OddsCollectionResult`
- `RaceProcessingWorkflow`
- `KraRaceSourceAdapter`
- `SQLAlchemyRaceRepository`

The workflow may call existing helpers from:

- `adapters.kra_response_adapter.KRAResponseAdapter`
- `services.collection_preprocessing.preprocess_data`
- `services.collection_enrichment.enrich_data`
- `services.kra_api_service.KRAAPIService`
- `models.database_models.Race`
- `models.database_models.RaceOdds`

`CollectionService` in `apps/api/services/collection_service.py` remains the compatibility surface for callers that have not yet been migrated, but async tasks, pipeline stages, and `CollectionCommands` now build the workflow directly.

Revision note: Initial ExecPlan created for the first implementation slice of the race processing workflow boundary.

Revision note: Updated after implementation to record the new workflow module, the compatibility-preserving delegation strategy, the enrich preprocessing discovery, and the passing targeted pytest results.

Revision note: Updated after the second implementation slice to record the direct caller migration, the workflow-first test updates, and the expanded passing regression suites.
