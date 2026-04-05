# Testing Patterns

**Analysis Date:** 2026-04-05

## Evidence Sources

**Documented testing sources:**
- Workspace commands in `package.json`
- API test command in `apps/api/package.json`
- API pytest configuration in `apps/api/pyproject.toml` and `apps/api/pytest.ini`
- API coverage policy in `apps/api/.coveragerc`
- Script-package test command in `packages/scripts/package.json`

**Patterns inferred from code:**
- API test harness in `apps/api/tests/conftest.py` and `apps/api/tests/platform/fixtures.py`
- API platform fakes and contract tests in `apps/api/tests/platform/fakes/` and `apps/api/tests/platform/contracts/`
- Representative API unit and integration suites such as `apps/api/tests/unit/test_job_service.py`, `apps/api/tests/unit/test_middleware_rate_limit.py`, `apps/api/tests/unit/test_logging_redaction.py`, `apps/api/tests/integration/test_api_endpoints.py`, and `apps/api/tests/integration/test_collection_workflow_router.py`
- Representative script-package suites such as `packages/scripts/tests/test_llm_client.py`, `packages/scripts/tests/test_shared_read_contract.py`, and `packages/scripts/evaluation/tests/test_data_loading.py`

## Test Framework

**Runner:**
- API tests use `pytest`, `pytest-asyncio`, `pytest-cov`, and `pytest-timeout` declared in `apps/api/pyproject.toml`.
- Script-package tests use `pytest` and `pytest-asyncio` declared in `packages/scripts/pyproject.toml`.

**Config:**
- Primary API config exists in both `apps/api/pyproject.toml` and `apps/api/pytest.ini`.
- Coverage behavior is further controlled by `apps/api/.coveragerc`.
- No dedicated `pytest.ini` or `.coveragerc` was detected for `packages/scripts`.

**Run Commands:**
```bash
pnpm test                           # Workspace test task via Turbo from `package.json`
pnpm -F @apps/api test              # API package test command from `apps/api/package.json`
cd apps/api && uv run pytest -q     # Direct API invocation noted in `AGENTS.md`
pnpm run quality:api:coverage       # API coverage-oriented CI command from `package.json`
pnpm --filter=@repo/scripts test    # Script-package tests via `packages/scripts/package.json`
cd packages/scripts && uv run pytest -q tests
```

## Test Layout

**API package layout:**
- Shared fixture export: `apps/api/tests/conftest.py`
- Shared harness and deterministic fakes: `apps/api/tests/platform/fixtures.py`, `apps/api/tests/platform/fakes/redis.py`, `apps/api/tests/platform/fakes/runner.py`, `apps/api/tests/platform/fakes/kra.py`
- Contract tests for fakes: `apps/api/tests/platform/contracts/test_fake_redis_contract.py`, `apps/api/tests/platform/contracts/test_runner_fakes_contract.py`
- Unit tests: `apps/api/tests/unit/`
- Integration tests: `apps/api/tests/integration/`
- Smoke tests: `apps/api/tests/test_smoke.py`
- Legacy compatibility helpers: `apps/api/tests/utils/mocks.py`

**Script-package layout:**
- General tests: `packages/scripts/tests/`
- Evaluation-specific tests: `packages/scripts/evaluation/tests/`
- Autoresearch tests: `packages/scripts/autoresearch/tests/`

**Observed counts at analysis time:**
- `apps/api/tests/unit/`: 69 `test_*.py` files
- `apps/api/tests/integration/`: 6 `test_*.py` files
- `apps/api/tests/platform/contracts/`: 2 `test_*.py` files
- `packages/scripts/**/tests/`: 15 `test_*.py` files

## Test Discovery and Markers

**Documented:**
- API discovery patterns are `test_*.py` and `*_test.py` via `apps/api/pytest.ini` and `apps/api/pyproject.toml`.
- API markers are declared for `unit`, `integration`, `e2e`, `slow`, `auth`, `db`, `external`, and `smoke` in `apps/api/pytest.ini` and `apps/api/pyproject.toml`.

**Inferred from code:**
- `unit`, `integration`, `auth`, and `smoke` are actively used, for example in `apps/api/tests/unit/test_auth.py`, `apps/api/tests/integration/test_api_endpoints.py`, and `apps/api/tests/test_smoke.py`.
- No active tests using `@pytest.mark.e2e`, `@pytest.mark.external`, `@pytest.mark.slow`, or `@pytest.mark.db` were detected in the analyzed tree.
- Most async API tests add both `@pytest.mark.asyncio` and a domain marker such as `@pytest.mark.unit`.
- Script-package tests do not use a comparable shared marker taxonomy.

## Shared Fixture and Harness Patterns

**API standard harness:**
- `apps/api/tests/conftest.py` re-exports fixtures from `apps/api/tests/platform/fixtures.py`. New API tests should import fixtures by parameter name and avoid local harness duplication.
- `test_settings()` in `apps/api/tests/platform/fixtures.py` builds a `Settings` instance for the `test` environment, then mutates the global `config.settings` singleton through `_apply_test_settings_to_global()`.
- `test_db_engine()` creates an ephemeral SQLite database using `create_async_engine(..., poolclass=StaticPool)` in `apps/api/tests/platform/fixtures.py`.
- `db_session()` wraps the SQLAlchemy `AsyncSession` in a helper that accepts raw SQL strings and always rolls back after each test in `apps/api/tests/platform/fixtures.py`.
- `redis_client()` yields the deterministic in-memory `FakeRedis` implementation from `apps/api/tests/platform/fakes/redis.py`.
- `client()` creates an `httpx.AsyncClient` with `ASGITransport(app=api_app)` and overrides `get_db`, `get_redis`, and `get_optional_redis` dependencies in `apps/api/tests/platform/fixtures.py`.
- `authenticated_client()` seeds a real `APIKey` row and attaches `X-API-Key` to the shared client in `apps/api/tests/platform/fixtures.py`.

**Script-package harness:**
- No shared `conftest.py` was detected under `packages/scripts`.
- Script tests usually define minimal fake classes inline, for example `FakeDBClient` in `packages/scripts/evaluation/tests/test_data_loading.py`.
- Script tests frequently patch constructors or preload import paths manually with `sys.path.insert(...)`, for example `packages/scripts/tests/test_llm_client.py` and `packages/scripts/tests/test_shared_read_contract.py`.

## Suite Structure

**API tests:**
- Function-based tests dominate, even inside class wrappers. Examples: `apps/api/tests/unit/test_job_service.py` and `apps/api/tests/integration/test_collection_workflow_router.py`.
- Some files use class-based organization only for topical grouping, not shared mutable state, for example `apps/api/tests/test_smoke.py` and `apps/api/tests/integration/test_api_endpoints.py`.
- Integration tests usually exercise the FastAPI app over HTTP using `authenticated_client` or `client`, then assert both status code and response payload.
- Unit tests frequently bypass HTTP and call helpers or handlers directly, for example `apps/api/tests/unit/test_logging_redaction.py` and `apps/api/tests/unit/test_router_handlers_direct.py`.

**Script-package tests:**
- Pure function tests are common, with direct assertions on return payloads or parser behavior. See `packages/scripts/evaluation/tests/test_prediction_service.py`.
- ABCs and subprocess wrappers are tested with class-based grouping and `unittest.mock`, as in `packages/scripts/tests/test_llm_client.py`.

## Mocking Patterns

**What the repo mocks heavily:**
- Async service boundaries with `AsyncMock`, for example `apps/api/tests/integration/test_collection_workflow_router.py` and `apps/api/tests/unit/test_job_service.py`
- Module-level globals and settings via `monkeypatch`, for example `apps/api/tests/unit/test_middleware_rate_limit.py`, `apps/api/tests/unit/test_logging_redaction.py`, and `apps/api/tests/unit/test_kra_api_core.py`
- Sync subprocess and DB cursor behavior with `MagicMock` and `patch`, for example `packages/scripts/tests/test_llm_client.py` and `packages/scripts/tests/test_shared_read_contract.py`

**Preferred fake strategy in the API package:**
- Use deterministic fake implementations when behavior matters across multiple tests. `FakeRedis` in `apps/api/tests/platform/fakes/redis.py` is the reference standard.
- Validate the fake itself with contract tests. See `apps/api/tests/platform/contracts/test_fake_redis_contract.py` and `apps/api/tests/platform/contracts/test_runner_fakes_contract.py`.
- Override FastAPI dependencies at the app boundary rather than mocking every call site. `client()` in `apps/api/tests/platform/fixtures.py` is the canonical example.

**When direct patching is still used:**
- To intercept external side effects or async orchestration paths, for example patching `submit_task`, `get_task_status`, or `collection_module` members in `apps/api/tests/unit/test_job_service.py` and `apps/api/tests/integration/test_collection_workflow_router.py`.
- To isolate CLI or subprocess behavior in script tests, for example `@patch("subprocess.run")` in `packages/scripts/tests/test_llm_client.py`.

## Fixture and Test Data Patterns

**API package:**
- Common sample payloads live in fixtures such as `sample_race_data()` and `mock_kra_api_response()` in `apps/api/tests/platform/fixtures.py`.
- Tests often build inline payload dictionaries that mirror real KRA response shapes instead of loading JSON fixtures from disk. See `apps/api/tests/unit/test_collection_new_apis.py` and `apps/api/tests/unit/test_collection_service_coverage.py`.
- Database assertions typically use real ORM rows inserted through `db_session`, for example `apps/api/tests/integration/test_api_endpoints.py` and `apps/api/tests/unit/test_job_service.py`.

**Script package:**
- Inline fake objects are the norm; the suite does not maintain a shared fixture library.
- `FakeDBClient` in `packages/scripts/evaluation/tests/test_data_loading.py` and patched `RaceDBClient` instances in `packages/scripts/tests/test_shared_read_contract.py` show the expected pattern.

## Common Assertion Patterns

**HTTP/API path:**
```python
response = await authenticated_client.post("/api/v2/collection/", json=payload)
assert response.status_code == 200
assert response.json()["status"] == "partial"
```
- Reference: `apps/api/tests/integration/test_collection_workflow_router.py`

**Direct service or helper path:**
```python
result = await service.start_job(job.job_id, db_session)
assert result == "stub-task-id"
```
- Reference: `apps/api/tests/unit/test_job_service.py`

**Monkeypatched logging/assertion path:**
```python
monkeypatch.setattr(logging_middleware.logger, "info", fake_info)
assert request_started["headers"]["authorization"] == "Bear***"
```
- Reference: `apps/api/tests/unit/test_logging_redaction.py`

**Sync script-parser path:**
```python
result = LLMClient.parse_json(text)
assert result == {"selected_horses": [1, 2, 3]}
```
- Reference: `packages/scripts/tests/test_llm_client.py`

## Async Testing Patterns

**API package:**
- Use `pytest.mark.asyncio` for async tests, even when `asyncio_mode = auto` is configured.
- Use `httpx.AsyncClient` with `ASGITransport` to avoid starting a network server. See `apps/api/tests/platform/fixtures.py`.
- Use async fixtures from `pytest_asyncio.fixture`, especially for DB engines, DB sessions, Redis fakes, and HTTP clients in `apps/api/tests/platform/fixtures.py`.
- Async background-task helpers are exercised by patching async collaborators instead of spinning full workers, as in `apps/api/tests/unit/test_async_tasks.py` and `apps/api/tests/unit/test_background_tasks.py`.

**Script package:**
- Most script tests are synchronous; async patterns are uncommon outside shared client abstractions.

## Coverage Posture

**Documented:**
- API test runs always enable coverage, branch coverage, terminal missing-line reporting, HTML output, and XML output via `apps/api/pytest.ini` and `apps/api/pyproject.toml`.
- API coverage threshold is `fail_under = 75` in `apps/api/.coveragerc`.
- API coverage omits tests, migrations, config, selected infrastructure modules, and some legacy paths in `apps/api/.coveragerc`.

**Inferred from code and artifacts:**
- The API suite includes multiple explicitly coverage-oriented files such as `apps/api/tests/unit/test_coverage_boost.py`, `apps/api/tests/unit/test_coverage_final_gaps.py`, `apps/api/tests/unit/test_coverage_low_files.py`, and `apps/api/tests/unit/test_coverage_jobs_pipeline.py`. The existing practice is to add narrow targeted tests to lift weak files.
- Generated coverage artifacts are present in the repository root and API package, including `.coverage`, `coverage.xml`, `htmlcov/`, `apps/api/.coverage`, `apps/api/coverage.xml`, and `apps/api/htmlcov/`. Treat these as snapshots, not as source-of-truth documentation.
- The checked-in `apps/api/coverage.xml` currently reflects a low line-rate snapshot, which conflicts with the configured `fail_under = 75`; planners should assume the artifact is stale unless regenerated.
- `packages/scripts/package.json` runs `uv run pytest -q tests` without enabling coverage by default, so the script package has no enforced coverage gate.

## Notable Gaps and Risks

**No active E2E layer:**
- `e2e` is a declared marker in `apps/api/pytest.ini`, but no `@pytest.mark.e2e` tests were detected.
- Future system-level verification will need a separate harness; current integration tests stop at in-process HTTP plus fake infrastructure.

**Markers are broader than usage:**
- `slow`, `db`, and `external` markers are declared in `apps/api/pytest.ini`, but no active tests using them were detected.
- This means the suite cannot currently filter true external-service or long-running tests cleanly.

**Script-package imports are brittle:**
- Many script tests and modules modify `sys.path` manually, including `packages/scripts/tests/test_llm_client.py`, `packages/scripts/tests/test_shared_read_contract.py`, and `packages/scripts/prompt_improvement/jury_prompt_improver.py`.
- New tests in `packages/scripts` will likely need the same workaround unless packaging is normalized.

**Shared fixtures are API-only:**
- `apps/api/tests/platform/fixtures.py` is a strong reusable harness, but `packages/scripts` has no equivalent.
- Script tests repeat local fake setup, which increases drift risk between suites.

**Coverage emphasis is tactical:**
- The API suite clearly contains behavior tests, but it also contains many narrow coverage-backfill files.
- When extending coverage, follow the repository’s current reality: add the smallest test that protects the target branch, and prefer staying near the affected subsystem.

**No active TypeScript test surface in the current tree:**
- No active `*.ts` or `*.tsx` source files were detected outside `.worktrees/`, so the JS/TS lint toolchain is configured but not backed by a living test suite in the checked-out repo.

## Practical Guidance for Future Tests

- For new API unit tests, start in `apps/api/tests/unit/` and reuse fixtures from `apps/api/tests/platform/fixtures.py` through parameter injection.
- For new API integration tests, use `authenticated_client` or `client` and assert on real HTTP responses rather than calling router helpers directly.
- If a test needs Redis behavior, prefer `FakeRedis` from `apps/api/tests/platform/fakes/redis.py` over ad hoc mocks; add or extend a contract test if you broaden the fake.
- If a test needs DB state, seed rows through `db_session` instead of patching ORM models away.
- Keep marker usage explicit. New API tests should add `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.auth`, or `@pytest.mark.smoke` as appropriate.
- For script-package tests, match the existing local style: inline fake classes, `MagicMock` for cursor/subprocess behavior, and `monkeypatch` for module globals.
- Do not rely on checked-in coverage artifacts to assess current quality. Re-run the package-local pytest command when actual coverage numbers matter.

---

*Testing analysis: 2026-04-05*
