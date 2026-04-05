# Cross-Cutting Test Platform, Fixture, and Fake Strategy

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document must be maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

After this change, contributors should be able to add or refactor tests in `apps/api` without inventing one-off mocks for Redis, KRA HTTP, background tasks, authentication, or Supabase on every file. The visible outcome is that the repository gains one coherent test platform: a shared app factory, deterministic fixtures, reusable fakes, and contract-test harnesses that prove those fakes behave like the production boundaries they replace.

The goal is not just “more tests.” The goal is to make test behavior predictable across nine repository areas that are currently tested with a mix of dependency overrides, direct monkeypatching, and partial mocks. A contributor should be able to run the API test suite from `apps/api` with `uv run pytest -q`, choose the right fixture by intent, and know whether they are exercising a unit, slice, contract, or legacy-compatibility path.

## Progress

- [x] (2026-03-19 13:40Z) Surveyed the current `apps/api/tests` layout, existing `conftest.py`, and reusable mocks in `apps/api/tests/utils/mocks.py`.
- [x] (2026-03-19 13:40Z) Traced the production boundaries for KRA HTTP, SQLAlchemy DB, Redis/cache, in-process background runner, auth dependencies, and Supabase legacy routes.
- [x] (2026-03-19 13:40Z) Defined the A~I taxonomy for this cross-cutting stream because no repository document currently names those areas.
- [ ] (2026-03-20 00:16 KST) Create `apps/api/tests/platform/` and migrate the current ad hoc fixtures into layered harness modules. Completed: `tests/platform/` package, shared `fixtures.py`, deterministic `FakeRedis`, compatibility shim in `tests/utils/mocks.py`, and a first Redis contract test. Remaining: split builders, fresh app harness, and more explicit auth/runner fixtures.
- [ ] (2026-03-20 00:16 KST) Add fake KRA, DB, runner, auth, Redis, and Supabase implementations with shared contract suites. Completed: Redis fake and KRA fake module extraction. Remaining: runner/auth/supabase fakes and their contract suites.
- [ ] Convert the highest-churn router and service tests to the new harness first, then retire duplicated local mocks.

## Surprises & Discoveries

- Observation: the main FastAPI application in `apps/api/main_v2.py` mounts `collection_v2`, `jobs_v2`, `health`, and `metrics`, but does not mount `routers/race.py`.
  Evidence: `main_v2.py` includes `collection_v2`, `jobs_v2`, `health`, and `metrics` only, while `test_race_router_supabase_guard.py` builds a separate FastAPI app just for `race.py`.

- Observation: the repository currently has two KRA client layers, `services/kra_api_service.py` and `infrastructure/kra_api/client.py`, with separate retry and transport behavior.
  Evidence: both files implement outbound HTTP, endpoint mapping, retry behavior, and response parsing, but the tests patch them independently.

- Observation: `apps/api/tests/utils/mocks.py` provides a partial `MockRedisClient`, but production `CacheService` uses methods the fake does not implement, including `setex`, `scan_iter`, and the pipeline behavior required by the rate limiter.
  Evidence: `CacheService.set()` calls `self.client.setex(...)`, `CacheService.clear_pattern()` uses `scan_iter`, and `RateLimitMiddleware` requires `.pipeline()`.

- Observation: many auth tests are ambiguous about whether they are verifying the environment-key path or the database-backed API key path.
  Evidence: `tests/conftest.py` seeds `Settings.valid_api_keys` while `authenticated_client` also inserts an `APIKey` row using one of those same values.

- Observation: the current suite already has the shape of a platform, but it is encoded as repeated monkeypatches instead of named test boundaries.
  Evidence: the search over `apps/api/tests` shows many direct patches to `submit_task`, `get_task_status`, `get_redis`, `KRAAPIService`, and `CollectionService`, with little central ownership.

- Observation: the repository-wide coverage gate makes small contract-suite bring-up awkward unless the command uses `--no-cov`.
  Evidence: focused runs for the new Redis contract and existing auth subset passed test bodies but exited non-zero because `pytest-cov` still enforced the global 75% threshold.

## Decision Log

- Decision: define A~I explicitly in this plan instead of waiting for an external taxonomy.
  Rationale: the user requested recommendations “across A~I,” but the repository does not name those areas anywhere searchable. The implementation needs a stable vocabulary now.
  Date/Author: 2026-03-19 / Codex

- Decision: standardize on layered harnesses instead of a single giant `conftest.py`.
  Rationale: the current test suite spans pure units, HTTP slices, dependency contracts, and legacy router compatibility. One flat fixture module encourages accidental coupling and broad autouse state.
  Date/Author: 2026-03-19 / Codex

- Decision: prefer “fake plus contract suite” over broad monkeypatching for external boundaries.
  Rationale: monkeypatch-heavy tests are cheap to write once but expensive to trust later. Shared fakes become safe only when the same behavioral assertions run against both the fake and the production boundary.
  Date/Author: 2026-03-19 / Codex

- Decision: keep SQLite as the default application-level persistence test backend and treat Supabase as a legacy compatibility boundary, not the canonical test database.
  Rationale: the main app stack is already wired around SQLAlchemy in `infrastructure/database.py`; Supabase currently matters mainly for `race.py` and `race_service.py`.
  Date/Author: 2026-03-19 / Codex

- Decision: separate auth-fixture modes for “real dependency,” “overridden identity,” and “header-only client.”
  Rationale: today those paths blur together. Router tests need low-friction identity injection, while auth tests need the real `require_api_key` behavior.
  Date/Author: 2026-03-19 / Codex

## Outcomes & Retrospective

This planning pass produced a repository-specific test platform design rather than a generic testing recipe. The main gaps are implementation and migration: the current codebase still uses partial Redis mocks, two unrelated KRA client layers, and many direct patches at call sites. The plan below resolves those gaps by introducing stable harness modules, a fake catalog, and contract suites per boundary.

The biggest risk is not technical complexity. It is partial migration. If only some tests adopt the new platform while old local mocks remain authoritative, the suite will become harder to understand, not easier. Migration therefore needs an explicit order and clear deprecation points.

## Context and Orientation

This repository’s active API test surface lives under `apps/api/tests`. The current shared test entry point is `apps/api/tests/conftest.py`, which creates an in-memory SQLite engine, a Redis fixture that falls back to `MockRedisClient`, and an `httpx.AsyncClient` bound directly to `main_v2.app`. The reusable mocks currently live in `apps/api/tests/utils/mocks.py`.

The production boundaries relevant to this plan are:

- A. App bootstrap and dependency wiring: `apps/api/main_v2.py`, `apps/api/infrastructure/database.py`, `apps/api/infrastructure/redis_client.py`.
- B. Authentication and authorization: `apps/api/dependencies/auth.py`.
- C. Collection HTTP flows: `apps/api/routers/collection_v2.py`, `apps/api/services/collection_service.py`, `apps/api/services/result_collection_service.py`.
- D. Job and workflow orchestration: `apps/api/routers/jobs_v2.py`, `apps/api/services/job_service.py`.
- E. Background execution: `apps/api/infrastructure/background_tasks.py`, `apps/api/tasks/async_tasks.py`.
- F. KRA outbound adapters: `apps/api/services/kra_api_service.py`, `apps/api/infrastructure/kra_api/client.py`, `apps/api/adapters/kra_response_adapter.py`.
- G. Persistence boundaries: `apps/api/infrastructure/database.py`, `apps/api/infrastructure/supabase_client.py`, `apps/api/services/race_service.py`, `apps/api/routers/race.py`.
- H. Redis, cache, rate limiting, and observability: `apps/api/infrastructure/redis_client.py`, `apps/api/middleware/rate_limit.py`, `apps/api/routers/health.py`, `apps/api/routers/metrics.py`.
- I. Contract harness and golden data management: new shared test platform modules and fixtures to be introduced under `apps/api/tests/platform/` and `apps/api/tests/fixtures/`.

In this document, a “fixture” means a pytest-provided object with a stable lifecycle. A “fake” means a lightweight in-memory implementation of a production dependency, such as Redis or the background task runner. A “contract test” means a test suite that verifies both the real implementation and the fake obey the same observable rules. A “slice test” means an HTTP-level or service-level test that exercises several modules together while still replacing true external systems.

## Plan of Work

Create a new package at `apps/api/tests/platform/` and treat it as the only place allowed to define cross-test infrastructure. Keep `apps/api/tests/conftest.py` as a thin re-export layer that assembles the most common fixtures from that package instead of owning all logic itself.

Add `apps/api/tests/platform/types.py` with the shared vocabulary. Define small, explicit protocol-style interfaces such as `RedisLike`, `TaskRunnerLike`, `KRAServiceLike`, and `AuthIdentity`. The immediate benefit is not runtime polymorphism; it is forcing the test platform to name what each fake must actually support. For example, the Redis-like boundary must include `get`, `setex`, `delete`, `exists`, `ttl`, `scan_iter`, `pipeline`, and `ping` because those are the production operations used today.

Add `apps/api/tests/platform/builders.py` for deterministic data builders. Builders must replace raw inline dictionaries in tests wherever the same domain objects recur. Start with `build_api_key`, `build_job`, `build_race`, `build_kra_race_detail_payload`, `build_kra_race_result_payload`, and `build_auth_headers`. The rule is that tests should describe intent in arguments, not rebuild production payload shape manually.

Add `apps/api/tests/platform/fakes/` as a directory with one file per boundary: `fake_kra.py`, `fake_redis.py`, `fake_runner.py`, `fake_auth.py`, `fake_supabase.py`, and optionally `fake_clock.py`. Each fake must be stateful enough to represent success, failure, retries, and missing data, but it must not silently invent behavior not present in production. The fake catalog is described in the “Interfaces and Dependencies” section below.

Add `apps/api/tests/platform/harness.py` with a top-level `PlatformHarness` object. This should compose the fake boundaries and hold references to the test database session factory, deterministic clock, and configuration overrides. The harness should be the thing a test asks for when it wants to steer multiple systems coherently. For example, a collection router slice test should be able to seed KRA payloads, pre-create an API key, and inspect emitted job state through one object.

Add `apps/api/tests/platform/app_factory.py` with a function that constructs a FastAPI app for tests from explicit dependencies rather than by mutating global module state in many places. The existing main app can remain intact; the test app factory should mirror the router mounting and dependency overrides used by the real app. The immediate target is not to rewrite production bootstrapping. It is to stop every router test from hand-writing overrides for DB, Redis, auth, or Supabase.

Add `apps/api/tests/platform/contracts/` with parameterized test helpers, not just ad hoc test files. Each contract suite should accept both a fake and a production-like boundary. The first contract suites should target Redis semantics, task-runner state transitions, KRA response normalization, and auth identity resolution. The contract suites are the mechanism that keeps the fake implementations honest.

Create `apps/api/tests/fixtures/` for golden payloads and narrow snapshots. This directory should hold representative KRA JSON payloads, normalized payload expectations, and contract cases for HTTP error envelopes. Do not put arbitrary large archives here. Only keep payloads that anchor a production boundary and are needed by contract or slice tests.

Migrate tests by layer, not by file name. Start with the cross-cutting boundaries that are currently the least complete: Redis and task runner. Then move auth, then KRA service/client tests, then router slice tests, then legacy Supabase compatibility tests. Each migration batch must delete duplicated local fakes after the shared version is proven by contract tests.

## Common Fixture Plan

The repository needs a three-layer fixture model.

The first layer is foundational and mostly session-scoped. It should expose `test_settings`, `event_loop`, a deterministic clock fixture, and a stable `platform_seed` fixture that provides reproducible IDs and timestamps. This layer must not create app state or database rows by itself.

The second layer is resource-scoped and mostly function-scoped. It should expose `db_harness`, `redis_harness`, `runner_harness`, `kra_harness`, `auth_harness`, and `supabase_harness`. Each harness owns setup, teardown, and inspection for one boundary. These fixtures should be composable without requiring the HTTP app.

The third layer is app-scoped and request-facing. It should expose `app_harness`, `client`, `authenticated_client`, `admin_client`, and `legacy_race_client`. These fixtures should be thin wrappers over the second layer plus the shared app factory. `authenticated_client` must not implicitly choose whether the auth path is environment-backed or DB-backed; the fixture name must encode that distinction, such as `db_authenticated_client` and `env_authenticated_client`.

The migration rule is that tests under `tests/unit/` should use only first- and second-layer fixtures unless they are explicitly testing HTTP contracts. Tests under `tests/integration/` should use the third layer. Contract suites should sit outside both mental buckets and accept factories or parameters directly.

## Fake Patterns

### Fake KRA Pattern

Provide two KRA fakes because the repository has two KRA boundaries.

`FakeKRAService` should mirror the callable methods used by `CollectionService` and `ResultCollectionService`, such as `get_race_info`, `get_race_result`, `get_horse_info`, `get_jockey_info`, `get_trainer_info`, `get_race_plan`, `get_track_info`, `get_cancelled_horses`, and `get_training_status`. The fake should be scenario-driven: tests preload responses or failures by method name and argument tuple, then inspect the recorded calls afterward.

`FakeKRATransport` should operate one layer lower for tests that validate `KRAAPIService` or `KRAApiClient`. It should model HTTP status, headers, JSON payload, retry-after semantics, and transient failure sequences. This fake belongs in transport or client tests, not router tests.

Golden payload fixtures must live beside the fake. The contract suite should prove that a golden KRA payload passed through `KRAResponseAdapter` or the client layer yields the expected normalized shape. The repository should stop open-coding nested government API payloads inside individual tests once the builder and golden fixtures exist.

### Fake DB Pattern

Do not build a fake ORM for the main app path. The canonical application-level database fixture should remain SQLAlchemy backed by in-memory SQLite, because that is already the repository’s production abstraction for `collection_v2`, `jobs_v2`, auth, health, and metrics.

Wrap that setup in a `DbHarness` that owns engine creation, schema creation, per-test session creation, and transaction cleanup. The harness should also expose helper methods like `insert_api_key`, `insert_job`, `insert_race`, and `fetch_one` so tests stop repeating low-level setup.

For pure unit tests that should not touch SQLAlchemy at all, define small repository fakes only behind explicit interfaces introduced for those units. Do not replace SQLAlchemy broadly until the production code exposes cleaner repository seams.

### Fake Runner Pattern

Introduce `InlineTaskRunner` and `ControlledTaskRunner`.

`InlineTaskRunner` executes submitted coroutines immediately and stores the same state transitions the production background runner exposes: pending, processing, completed, failed, and cancelled. It is the default for router and service slice tests because it removes event-loop timing races.

`ControlledTaskRunner` queues tasks until the test calls `drain_one()` or `drain_all()`. Use it for tests that need to inspect the “queued” or “processing” state before completion.

Both runners must satisfy a shared task-runner contract suite against the public behavior in `infrastructure/background_tasks.py`. If the production module exposes `submit_task`, `get_task_status`, `cancel_task`, and task statistics, the fake must expose equivalent observable behavior or the contract suite must reject it.

### Fake Auth Pattern

Provide an `AuthHarness` with named identities, not raw header strings. It should support at least `anonymous`, `reader`, `writer`, `admin`, and `resource_owner`.

The harness should issue two kinds of identity explicitly. First, DB-backed API keys by inserting rows through `DbHarness`. Second, environment-backed API keys by temporarily overriding `settings.valid_api_keys`. The fixture names and helper methods must force the caller to choose one, because those paths have different behavior in `verify_api_key`.

For router tests that do not care about auth internals, allow an override mode that bypasses `require_api_key` entirely and returns a synthetic identity. For auth tests and resource-access tests, require the real dependency path and assert on HTTP 401, 403, and 429 outcomes.

### Fake Redis Pattern

Replace the current `MockRedisClient` with a fuller `FakeRedis` that supports the production surface the repository actually uses: `ping`, `get`, `setex`, `delete`, `exists`, `ttl`, `expire`, `incr`, `flushdb`, `scan_iter`, and `pipeline`.

The pipeline implementation does not need to emulate Redis perfectly. It does need to behave consistently for `zremrangebyscore`, `zadd`, `zcount`, and `expire`, because that is the contract required by `RateLimitMiddleware`.

The fake should support explicit fail-open modes. A test must be able to say “next call to `pipeline.execute()` raises a connection error” or “`get()` times out” and then assert that the middleware or cache layer degrades safely. This is more useful than the current all-or-nothing fallback because production code already contains fail-open behavior.

### Fake Supabase Pattern

Treat Supabase as a legacy compatibility boundary. Build `FakeSupabaseClient` around recorded table operations: `table(name)`, then chainable verbs like `select`, `insert`, `update`, `upsert`, `eq`, and `execute`.

The fake should return simple objects with `.data` or equivalent attributes matching what `RaceService` expects. It must also record executed table operations for assertions. The goal is not to mimic the whole Supabase SDK. The goal is to stabilize tests around `race.py` and `race_service.py` without a networked Supabase instance.

## Contract-Test Harness Recommendations Across A~I

### A. App Bootstrap and Dependency Wiring

Use an `AppHarness` contract that proves the test app mounts the same routers and middleware expectations as `main_v2.app`, except where the repository intentionally omits legacy routes. The contract should verify `/health`, `/metrics`, `/api/v2/collection`, and `/api/v2/jobs` wiring, plus dependency override behavior for DB and Redis. Keep `race.py` out of this contract and cover it separately as a legacy path.

### B. Auth and Authorization

Create an auth contract matrix that runs the same endpoint or dependency against anonymous, env-backed, DB-backed, expired, inactive, and unauthorized identities. The contract should prove `require_api_key`, `verify_api_key`, and `require_resource_access` return the same outcomes whether the caller uses the harness helpers or direct HTTP requests.

### C. Collection Router and Service Flows

Use HTTP slice tests with `FakeKRAService`, real SQLite via `DbHarness`, and `InlineTaskRunner` only when asynchronous dispatch is involved. Contract coverage should focus on request validation, partial-failure envelopes, result collection behavior, and normalized KRA payload handling. Avoid monkeypatching `CollectionService.collect_race_data` directly once the fake KRA path exists.

### D. Job Router and Job Service

Use `DbHarness` plus `ControlledTaskRunner` to assert the transition from job creation to queued to processing to completion. The contract suite should verify job listing filters, user scoping, job detail retrieval, and cancellation semantics. Tests should stop patching `submit_task` at the call site once `JobService` can be wired to a runner interface in the harness.

### E. Background Runner and Async Tasks

Split the tests into two bands. The first band is a runner contract suite that targets `infrastructure/background_tasks.py` and the runner fakes. The second band targets `apps/api/tasks/async_tasks.py` with fake KRA and real SQLite. This lets the repository prove task state semantics separately from business logic.

### F. KRA Outbound Adapters

Run transport-level contract tests against both `KRAAPIService` and `KRAApiClient`. The shared cases should cover success payloads, 4xx and 5xx behavior, 429 with `Retry-After`, malformed payloads, and cache-hit versus cache-miss behavior where applicable. Use the same golden responses so the two client layers cannot drift silently.

### G. Persistence Boundaries, Including Legacy Supabase

For SQLAlchemy-backed code, the contract is repository behavior against SQLite: schema setup, inserts, updates, and lookup semantics. For Supabase-backed legacy code, the contract is request-to-table-operation translation against `FakeSupabaseClient`. Do not mix both persistence models in one contract suite; name one `db_contract` and the other `supabase_compat_contract`.

### H. Redis, Cache, Rate Limit, Health, and Metrics

Use `FakeRedis` plus contract suites for `CacheService`, `RateLimitMiddleware`, the health detailed endpoint, and metrics generation. The shared assertions should cover healthy path, degraded path, missing Redis client, connection error, TTL behavior, and rate-limit counting windows. This is the area where the current fake gap is most likely to create false confidence.

### I. Cross-Cutting Contract Harness and Golden Data

Add one repository-level harness entry point that parameterizes the fake versus production-like boundary under test. This area owns the golden KRA payloads, normalized snapshots, and error-envelope assertions that other contract suites reuse. Its success criterion is that adding a new fake requires adding it to the contract matrix before any router or service test can depend on it.

## Concrete Steps

From the repository root, create the shared test platform directories and skeleton modules.

    cd /Users/chsong/Developer/Personal/kra-analysis
    mkdir -p apps/api/tests/platform/contracts
    mkdir -p apps/api/tests/platform/fakes
    mkdir -p apps/api/tests/fixtures/kra

Move the current reusable mock logic out of `apps/api/tests/utils/mocks.py` into the new fake modules, but only after the contract suites exist. Until then, keep `tests/utils/mocks.py` as a compatibility shim that imports the new fake classes and emits no new behavior of its own.

Refactor `apps/api/tests/conftest.py` so it imports fixtures from `apps/api/tests/platform/` instead of owning engine setup, Redis fallback logic, and app overrides directly. The thin top-level `conftest.py` should remain the stable import root for pytest discovery.

Add the first contract suites in this order:

    1. Redis contract
    2. Background runner contract
    3. Auth contract
    4. KRA payload normalization and retry contract

After those contracts pass for both the fake and production-like boundary, migrate router slice tests and delete local monkeypatch-based substitutes that became redundant.

## Validation and Acceptance

Validation is complete when a contributor can do the following from `apps/api` and observe the expected behavior.

Run the test suite:

    cd /Users/chsong/Developer/Personal/kra-analysis/apps/api
    uv run pytest -q

Expected outcome after implementation:

- tests that exercise cache or rate-limit behavior pass without depending on a real local Redis process
- router tests choose explicit auth modes instead of relying on incidental `settings.valid_api_keys` state
- job and async-task tests can deterministically assert queued, processing, completed, failed, and cancelled states
- collection and KRA tests reuse golden payloads instead of rebuilding nested government response shapes in each file
- legacy Supabase tests run through a named compatibility harness instead of bespoke router-local overrides

Add focused validation commands during migration. For example:

    cd /Users/chsong/Developer/Personal/kra-analysis/apps/api
    uv run pytest -q tests/platform/contracts/test_redis_contract.py
    uv run pytest -q tests/platform/contracts/test_runner_contract.py
    uv run pytest -q tests/unit/test_auth.py tests/unit/test_auth_resource_access.py
    uv run pytest -q tests/integration/test_api_endpoints.py tests/integration/test_jobs_router.py

Each contract suite must fail if a fake omits a method or returns state inconsistent with production behavior. Passing tests are the proof that the fake catalog is safe to reuse.

## Idempotence and Recovery

The directory creation and test-platform module additions are additive and safe to rerun. Re-running pytest should not depend on external Redis or Supabase availability once the fake catalog is complete.

If a migration batch breaks many existing tests at once, restore compatibility by keeping a shim in `apps/api/tests/utils/mocks.py` and importing the new fake classes through it until all call sites are converted. Do not remove old helper names and local imports in the same change that introduces the new platform unless the relevant test subset is already green.

If a contract suite reveals that a fake is too weak, strengthen the fake or narrow its declared interface. Do not loosen the contract just to keep the fake cheap.

## Artifacts and Notes

The most important implementation artifact should be the new directory structure:

    apps/api/tests/platform/
      app_factory.py
      builders.py
      harness.py
      types.py
      fakes/
        fake_auth.py
        fake_kra.py
        fake_redis.py
        fake_runner.py
        fake_supabase.py
      contracts/
        test_auth_contract.py
        test_kra_contract.py
        test_redis_contract.py
        test_runner_contract.py

The compatibility artifact should be:

    apps/api/tests/utils/mocks.py

with contents reduced to imports or thin aliases pointing at the new fake implementations.

## Interfaces and Dependencies

In `apps/api/tests/platform/harness.py`, define a `PlatformHarness` data holder that owns the following fields or equivalent properties:

    db: DbHarness
    redis: FakeRedis | RedisLike
    runner: InlineTaskRunner | ControlledTaskRunner | TaskRunnerLike
    kra: FakeKRAService | KRAServiceLike
    auth: AuthHarness
    supabase: FakeSupabaseClient | None
    clock: DeterministicClock

In `apps/api/tests/platform/app_factory.py`, define:

    def create_test_app(harness: PlatformHarness, *, include_legacy_race: bool = False) -> FastAPI:
        ...

This function should mount the same routers as `main_v2.app` by default and optionally mount `race.py` for legacy compatibility tests.

In `apps/api/tests/platform/fakes/fake_runner.py`, define methods equivalent to:

    submit(coro_func, *args, **kwargs) -> str
    get_status(task_id: str) -> dict[str, Any] | None
    cancel(task_id: str) -> bool
    stats() -> dict[str, Any]
    drain_one() -> None
    drain_all() -> None

In `apps/api/tests/platform/fakes/fake_redis.py`, define the Redis-like surface needed by current production code:

    async def ping() -> bool
    async def get(key: str) -> str | None
    async def setex(key: str, ttl: int, value: str) -> bool
    async def delete(*keys: str) -> int
    async def exists(key: str) -> int
    async def ttl(key: str) -> int
    async def expire(key: str, seconds: int) -> bool
    async def incr(key: str) -> int
    async def flushdb() -> None
    def pipeline() -> FakeRedisPipeline
    async def scan_iter(match: str): ...

In `apps/api/tests/platform/fakes/fake_auth.py`, expose helpers equivalent to:

    async def issue_env_key(name: str, permissions: list[str]) -> str
    async def issue_db_key(name: str, permissions: list[str], *, expired: bool = False, active: bool = True) -> str
    def headers(api_key: str) -> dict[str, str]
    def override_identity(name: str, permissions: list[str]) -> Callable

In `apps/api/tests/platform/fakes/fake_kra.py`, expose both method-level and transport-level setup:

    def seed_method(method_name: str, key: tuple[Any, ...], result: Any | Exception) -> None
    def seed_http(endpoint: str, params: dict[str, Any], responses: list[FakeHTTPResponse]) -> None
    @property
    def calls(self) -> list[RecordedCall]

At the bottom of this plan, maintain a revision note whenever the strategy changes.

Revision note: 2026-03-19. Initial cross-cutting plan created to define the common fixture model, fake catalog, and A~I contract-test recommendations for the API test platform.
