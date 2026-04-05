# Codebase Concerns

**Analysis Date:** 2026-04-05

## Tech Debt

**In-process job execution is the runtime bottleneck and failure domain:**
- Issue: Background jobs run via `asyncio.create_task()` inside the API process, with no durable queue, no worker separation, and no startup reconciliation for orphaned jobs.
- Files: `apps/api/infrastructure/background_tasks.py`, `apps/api/main_v2.py`, `apps/api/services/job_service.py`, `apps/api/tasks/async_tasks.py`, `apps/api/bootstrap/runtime.py`
- Impact: Process restart, crash, deploy, or memory pressure can silently drop in-flight collection jobs while API callers still depend on `jobs` state.
- Fix approach: Move job execution to a durable worker/queue, or add a startup reconciler that marks orphaned `jobs` rows as failed/retryable and replays safe tasks.

**Large multi-responsibility modules hide behavior and increase regression risk:**
- Issue: Core modules combine orchestration, transport, persistence, compatibility mapping, and domain logic in a single file.
- Files: `apps/api/services/collection_service.py`, `apps/api/services/kra_api_service.py`, `apps/api/services/job_service.py`, `apps/api/models/database_models.py`, `apps/api/tasks/async_tasks.py`
- Impact: Safe refactoring is expensive; a change in one concern can easily break another because boundaries are implicit.
- Fix approach: Split orchestration from persistence and transport. Keep API-facing orchestration thin and move DB writes, KRA fetches, and enrichment helpers behind explicit seams.

**Migration source-of-truth is still split between legacy and unified schema paths:**
- Issue: The active manifest points to `001_unified_schema.sql`, but `001_initial_schema.sql` remains in the same directory and multiple docs still warn operators about choosing the right baseline manually.
- Files: `apps/api/migrations/001_initial_schema.sql`, `apps/api/migrations/001_unified_schema.sql`, `apps/api/infrastructure/migration_manifest.py`, `apps/api/scripts/apply_migrations.py`, `apps/api/README.md`, `apps/api/docs/SUPABASE_SETUP.md`
- Impact: New environment bootstrap is easy to get wrong, and schema debugging starts with "which baseline is real?" instead of a single answer.
- Fix approach: Archive legacy SQL out of the active migration directory, keep one canonical chain, and make CI validate that chain against an empty database.

**Config, packaging, and test configuration drift create multiple truths:**
- Issue: Runtime version and test settings are duplicated and disagree across files.
- Files: `apps/api/config.py`, `apps/api/pyproject.toml`, `apps/api/pytest.ini`
- Impact: Release metadata, coverage behavior, and local-vs-CI execution can diverge without code changes.
- Fix approach: Keep one source of truth for versioning and one source of truth for pytest/coverage configuration. Remove the duplicate block that is not authoritative.

**Stale documentation and absent legacy targets still shape developer behavior:**
- Issue: The repo contains multiple active-looking READMEs and policy docs that reference Celery, `apps/collector`, or legacy files that are not present in the current tree.
- Files: `README.md`, `apps/api/README.md`, `apps/api/README-uv.md`, `apps/api/README-simplified.md`, `apps/api/docs/LEGACY_V1_POLICY.md`, `docs/api-implementation-guide.md`, `docs/unified-collection-api-design.md`
- Impact: Planning and onboarding start from obsolete architecture assumptions, which slows execution and increases wrong-file edits.
- Fix approach: Reduce to one maintained API README and one archived docs area. Remove references to files that no longer exist.

**Repository carries large experimental artifacts with unclear retention rules:**
- Issue: Experimental datasets and snapshots are committed alongside runtime code.
- Files: `packages/scripts/data/**`, `packages/scripts/autoresearch/snapshots/**`, `docs/_archive/**`
- Impact: Clone/index time grows, review noise increases, and ownership between runtime code and experiment outputs stays unclear.
- Fix approach: Move bulky generated artifacts to external storage or release assets, keep only minimal fixtures in git, and document ownership/retention for experiment outputs.

## Known Bugs

**Background task status can be reported as completed when Redis is unavailable:**
- Symptoms: `get_task_status()` falls back to in-memory task inspection and reports `completed` for any finished task when Redis state is missing, even if the task failed.
- Files: `apps/api/infrastructure/background_tasks.py`
- Trigger: Redis is down or state persistence fails during a background task run.
- Workaround: Inspect the `jobs` table and `job_logs` instead of trusting only background-task state.

**Partial batch collections are persisted as failed jobs:**
- Symptoms: Batch payload returns `"status": "partial"` while the persisted job lifecycle is set to `"failed"` if any race fails.
- Files: `apps/api/tasks/async_tasks.py`
- Trigger: `batch_collect()` completes with mixed success and error entries.
- Workaround: Read `job.result` payload details instead of treating job lifecycle status as the only truth.

**Detailed health can report Redis healthy for an object that is not a real Redis client:**
- Symptoms: `/health/detailed` returns Redis healthy when the injected object has no `ping()` method.
- Files: `apps/api/routers/health.py`, `apps/api/tests/unit/test_coverage_low_files.py`
- Trigger: Dependency override, mock, or incorrect runtime wiring provides a non-Redis object.
- Workaround: Use real Redis connectivity checks in deployment monitoring instead of depending only on `/health/detailed`.

## Security Considerations

**API keys are stored and propagated as raw credentials:**
- Risk: Raw API keys are stored in the database and reused as `principal_id`, `owner_ref`, `credential_id`, and job ownership fields.
- Files: `apps/api/models/database_models.py`, `apps/api/dependencies/auth.py`, `apps/api/policy/authentication.py`, `apps/api/policy/accounting.py`
- Current mitigation: Format validation, active flag checks, expiration checks, and per-key limits exist.
- Recommendations: Hash API keys at rest, introduce a public key identifier for ownership/audit fields, and stop persisting raw keys in `jobs` and `usage_events`.

**Default development credentials and fail-open behavior rely on environment discipline:**
- Risk: Non-production defaults include `debug=True`, a development secret key, and a default test API key; rate limiting bypasses in development/test and also bypasses on Redis failure.
- Files: `apps/api/config.py`, `apps/api/middleware/rate_limit.py`, `apps/api/tests/unit/test_rate_limit.py`
- Current mitigation: Production mode raises on some unsafe defaults.
- Recommendations: Require explicit environment selection at startup, disable implicit test keys outside local-only mode, and decide whether Redis failure should be fail-closed or at least page operators immediately.

**Usage accounting amplifies secret exposure in audit data:**
- Risk: Append-only usage events store credential identifiers derived from the presented key, which broadens the blast radius of any database read exposure.
- Files: `apps/api/models/database_models.py`, `apps/api/policy/accounting.py`, `apps/api/policy/authentication.py`
- Current mitigation: Events are append-only and structured.
- Recommendations: Persist opaque credential ids only, not bearer material or raw presented keys.

## Performance Bottlenecks

**Protected requests perform synchronous write-heavy authentication/accounting work:**
- Problem: API key verification updates counters and commits immediately, then policy accounting inserts another row after the request.
- Files: `apps/api/dependencies/auth.py`, `apps/api/policy/accounting.py`, `apps/api/middleware/policy_accounting.py`
- Cause: Request authentication doubles as usage mutation, and accounting is persisted inline on the request path.
- Improvement path: Move counters to Redis or an append-only stream, batch flush usage stats, and keep authentication read-mostly.

**Race collection performs high-latency external I/O sequentially:**
- Problem: Collection loops races sequentially, then loops horses sequentially, then performs multiple KRA API calls per horse.
- Files: `apps/api/services/collection_service.py`, `apps/api/services/kra_collection_module.py`, `apps/api/services/kra_api_service.py`
- Cause: No bounded concurrency or bulk-fetch pattern exists around horse/jockey/trainer/detail requests.
- Improvement path: Introduce controlled concurrency with semaphores, prefetch repeated entities, and cache invariant lookups more aggressively.

**Backfill and odds collection are row-by-row and operator-driven:**
- Problem: Backfill scripts iterate one race at a time, sleep between requests, and mix ORM queries with direct SQL.
- Files: `apps/api/scripts/batch_backfill.py`, `apps/api/services/result_collection_service.py`
- Cause: Operational tooling is implemented as ad hoc scripts rather than resumable jobs.
- Improvement path: Convert backfill into resumable jobs with checkpointing, bounded concurrency, and explicit observability.

## Fragile Areas

**Shared DB session across multi-race collection batches:**
- Files: `apps/api/services/kra_collection_module.py`, `apps/api/services/collection_service.py`
- Why fragile: `collect_batch()` keeps one `AsyncSession` across many races while swallowing per-race exceptions. A single transactional failure can poison later iterations.
- Safe modification: Give each race its own transaction boundary or dedicated session.
- Test coverage: Unit tests cover handler branches heavily, but there is no production-like stress test for batch failure and session recovery.

**Mixed KRA client lifecycle ownership:**
- Files: `apps/api/services/kra_api_service.py`, `apps/api/services/kra_collection_module.py`, `apps/api/tasks/async_tasks.py`, `apps/api/main_v2.py`
- Why fragile: Some flows use a global singleton HTTP client, others instantiate per-task clients and close them. The singleton client is not closed during app shutdown.
- Safe modification: Standardize on one lifecycle model, preferably app-scoped dependency management in `lifespan`.
- Test coverage: Tests cover request helpers and branches, but not long-lived client lifecycle behavior.

**Scripts depend on private service internals and alternate data paths:**
- Files: `apps/api/scripts/batch_backfill.py`, `apps/api/services/result_collection_service.py`, `apps/api/infrastructure/supabase_client.py`
- Why fragile: Operational scripts call private methods like `_collect_odds_after_result()` and legacy Supabase code still exists beside the SQLAlchemy path.
- Safe modification: Promote stable service APIs for backfill use and isolate legacy-only infrastructure behind an explicit archive boundary.
- Test coverage: There is no contract test for script-to-service compatibility.

## Scaling Limits

**Job concurrency is unbounded inside one API process:**
- Current capacity: Limited by a single FastAPI process event loop and host memory; `submit_task()` does not enforce queue depth or admission control.
- Limit: Burst submission can exhaust process resources and make the API itself unstable.
- Scaling path: Move to worker processes or a queue with concurrency controls, visibility timeouts, and backpressure.

**Background task observability expires quickly and is not restart-safe:**
- Current capacity: Redis task state TTL is 1 hour and live handles exist only in `_running_tasks`.
- Limit: Long-running or interrupted jobs lose accurate per-task visibility after TTL expiration or process restart.
- Scaling path: Persist durable execution records in the database and add reconciliation/retry semantics on startup.

## Dependencies at Risk

**Supabase SDK path remains in dependency and docs despite the runtime standardizing on SQLAlchemy/Postgres:**
- Risk: The codebase still carries a second persistence story that is not part of the mounted runtime.
- Impact: New changes can accidentally revive legacy access patterns or waste time supporting an inactive integration.
- Migration plan: Remove `supabase` from the active API dependency path once no maintained module imports `infrastructure/supabase_client.py`, or move the legacy code into an archived package.

## Missing Critical Features

**No durable recovery path for interrupted jobs:**
- Problem: A crash or deploy can leave `jobs` records stuck in `queued` or `processing` without an automatic repair path.
- Blocks: Reliable async collection, safe deploys during long-running work, and accurate operator dashboards.

**No production-like startup verification in CI:**
- Problem: CI runs with `ENVIRONMENT=test`, which routes `init_db()` through `create_all()` instead of validating the migration manifest used in real deployments.
- Blocks: Early detection of migration drift and empty-database bootstrap failures.

**No clear ownership boundary between runtime product code and experimental analysis assets:**
- Problem: `apps/api` and `packages/scripts` share one repo, while docs and committed datasets blur what is production-supported.
- Blocks: Fast planning, selective review, and confident cleanup of stale artifacts.

## Test Coverage Gaps

**Coverage is high, but much of it is branch-chasing rather than behavior validation:**
- What's not tested: Production-like worker durability, crash recovery, real migration bootstrap, and sustained KRA collection throughput.
- Files: `apps/api/tests/unit/test_coverage_*.py`, `apps/api/tests/unit/test_router_handlers_direct.py`, `apps/api/tests/unit/test_main_v2_celery_lifespan.py`, `.github/workflows/ci.yml`
- Risk: The suite can stay green while the highest operational risks remain untreated.
- Priority: High

**Migration correctness is not exercised by the default CI path:**
- What's not tested: Fresh database startup using only the manifest-driven migration chain.
- Files: `apps/api/infrastructure/database.py`, `apps/api/scripts/apply_migrations.py`, `.github/workflows/ci.yml`
- Risk: Schema drift or a broken migration can surface only during deployment/bootstrap.
- Priority: High

**Legacy/stale doc assertions are not guarded by tests or lint rules:**
- What's not tested: That README and policy documents reference only files that still exist.
- Files: `README.md`, `apps/api/README.md`, `apps/api/docs/LEGACY_V1_POLICY.md`, `docs/api-implementation-guide.md`
- Risk: Planning and implementation continue to drift from the actual runtime.
- Priority: Medium

---

*Concerns audit: 2026-04-05*
