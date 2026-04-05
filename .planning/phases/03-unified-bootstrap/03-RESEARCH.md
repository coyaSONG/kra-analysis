# Phase 3: Unified Bootstrap - Research

**Researched:** 2026-04-05 [VERIFIED: system date]
**Domain:** FastAPI startup bootstrap, manifest-tracked SQL migrations, fresh Postgres bootstrap verification [VERIFIED: .planning/ROADMAP.md][VERIFIED: apps/api/main_v2.py][VERIFIED: apps/api/scripts/apply_migrations.py]
**Confidence:** HIGH for codebase facts, MEDIUM for live-environment state because no real Supabase/Postgres instance was inspected in this session [VERIFIED: apps/api/infrastructure/database.py][VERIFIED: apps/api/scripts/apply_migrations.py]

<user_constraints>
## User Constraints

No `03-CONTEXT.md` exists yet for this phase, so the constraints below are derived from roadmap, state, requirements, and repository instructions instead of copied from a phase context file. [VERIFIED: gsd init phase-op 3][VERIFIED: .planning/ROADMAP.md][VERIFIED: .planning/STATE.md]

### Locked Decisions

- Phase 3 is specifically about fresh DB bootstrap and startup migration verification for the unified chain; it is not the phase for runner isolation or collection seam extraction. [VERIFIED: .planning/ROADMAP.md][VERIFIED: .planning/STATE.md]
- This phase must satisfy `SCHEMA-01` and `SCHEMA-02`. [VERIFIED: .planning/REQUIREMENTS.md][VERIFIED: .planning/ROADMAP.md]
- The unified migration chain is the active schema baseline. [VERIFIED: .planning/STATE.md][VERIFIED: apps/api/infrastructure/migration_manifest.py]
- Existing `collection`, `jobs`, `health`, and `metrics` routes must remain compatible while schema/bootstrap truth is tightened. [VERIFIED: .planning/STATE.md][VERIFIED: ./CLAUDE.md]

### Claude's Discretion

- The planner can choose how to split bootstrap proof, startup guard hardening, and CI verification because no phase-specific implementation shape has been locked yet. [VERIFIED: gsd init phase-op 3][VERIFIED: .planning/ROADMAP.md]
- The planner can decide whether legacy-file cleanup lands in this phase as code/docs changes or is minimized to fail-closed detection plus operator guidance. [VERIFIED: apps/api/scripts/setup.sh][VERIFIED: apps/api/Makefile][VERIFIED: apps/api/README.md]

### Deferred Ideas (OUT OF SCOPE)

- Durable external queue rollout is out of scope for the current milestone. [VERIFIED: .planning/REQUIREMENTS.md]
- New frontend/dashboard work is out of scope for the current milestone. [VERIFIED: .planning/REQUIREMENTS.md]
- Large prediction product expansion is out of scope until runtime/schema/doc truth is stabilized. [VERIFIED: .planning/REQUIREMENTS.md]
</user_constraints>

## Project Constraints (from CLAUDE.md)

- Python commands should use `python3`, and the repo-standard environment manager is `uv`. [VERIFIED: ./CLAUDE.md]
- Do not delete `.env`, `data/`, or `KRA_PUBLIC_API_GUIDE.md`. [VERIFIED: ./CLAUDE.md]
- The active runtime is `apps/api/main_v2.py`, and planning must preserve that reality. [VERIFIED: AGENTS.md][VERIFIED: ./CLAUDE.md]
- Domain logic belongs in `services/`; HTTP and I/O wiring belong in the API layer. [VERIFIED: AGENTS.md]
- New documentation should update existing truth instead of creating duplicate overlapping docs. [VERIFIED: ./CLAUDE.md]
- The active platform baseline is Python 3.13+, FastAPI, SQLAlchemy async ORM, PostgreSQL, Redis, `uv`, and `pnpm`. [VERIFIED: ./CLAUDE.md]

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCHEMA-01 | Operator can bootstrap a fresh database from the unified migration chain without relying on `create_all()` in the production path. [VERIFIED: .planning/REQUIREMENTS.md] | Use the existing manifest-tracked runner as the only bootstrap authority, remove production proof dependence on `Base.metadata.create_all()`, and add fresh-DB verification against non-test startup. [VERIFIED: apps/api/infrastructure/database.py][VERIFIED: apps/api/scripts/apply_migrations.py][VERIFIED: apps/api/tests/platform/fixtures.py] |
| SCHEMA-02 | App startup rejects missing or unexpected migration state against one canonical manifest in non-test environments. [VERIFIED: .planning/REQUIREMENTS.md] | Extend current manifest guard to catch mixed legacy/unified states, and prove it in non-test startup tests plus CI/bootstrap checks. [VERIFIED: apps/api/infrastructure/database.py][VERIFIED: apps/api/scripts/apply_migrations.py][VERIFIED: .github/workflows/ci.yml] |
</phase_requirements>

## Summary

The repository already contains most of the target architecture for this phase: `apps/api/infrastructure/migration_manifest.py` defines the canonical unified chain, `apps/api/scripts/apply_migrations.py` applies only that chain with checksums and advisory locks, and `apps/api/main_v2.py` calls `init_db()` during FastAPI lifespan startup before the app serves requests. [VERIFIED: apps/api/infrastructure/migration_manifest.py][VERIFIED: apps/api/scripts/apply_migrations.py][VERIFIED: apps/api/main_v2.py][CITED: https://github.com/fastapi/fastapi/blob/0.118.2/docs/en/docs/advanced/events.md]

The actual planning problem is not “how to add migrations”, but “how to make the current unified chain the only trusted bootstrap path and prove it end-to-end”. The biggest gaps are that test fixtures still create schema through `Base.metadata.create_all()`, CI runs startup checks with `ENVIRONMENT=test`, and current startup verification only compares `schema_migrations` names, not mixed legacy physical state such as `collection_jobs` or `race_results` tables left by `001_initial_schema.sql`. [VERIFIED: apps/api/tests/platform/fixtures.py][VERIFIED: .github/workflows/ci.yml][VERIFIED: apps/api/infrastructure/database.py][VERIFIED: apps/api/migrations/001_initial_schema.sql][VERIFIED: apps/api/scripts/apply_migrations.py]

Operator entrypoints are also still split: `apps/api/README.md` points at `scripts/apply_migrations.py`, but `apps/api/scripts/setup.sh` still tells users to execute `migrations/001_initial_schema.sql`, and `apps/api/Makefile` still advertises `alembic upgrade head` even though no active Alembic environment exists in `apps/api/`. That split is the main coexistence risk the planner should treat as a first-class Phase 3 concern. [VERIFIED: apps/api/README.md][VERIFIED: apps/api/scripts/setup.sh][VERIFIED: apps/api/Makefile][VERIFIED: apps/api]

**Primary recommendation:** Plan Phase 3 as four slices: `manifest truth`, `mixed-state/startup guard hardening`, `fresh-bootstrap proof`, and `operator entrypoint cleanup`. [VERIFIED: apps/api/infrastructure/migration_manifest.py][VERIFIED: apps/api/scripts/apply_migrations.py][VERIFIED: apps/api/infrastructure/database.py][VERIFIED: apps/api/scripts/setup.sh][VERIFIED: apps/api/Makefile]

## Standard Stack

Version verification for this phase should use the checked-in Python lockfile and the local `uv` environment, not `npm view`, because the affected runtime is Python-first. [VERIFIED: apps/api/pyproject.toml][VERIFIED: uv.lock][VERIFIED: `uv run python --version`]

### Core

| Library / Tool | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| FastAPI | `0.118.0` [VERIFIED: uv.lock] | Lifespan startup is the canonical place to run pre-serve bootstrap checks. [VERIFIED: apps/api/main_v2.py][CITED: https://github.com/fastapi/fastapi/blob/0.118.2/docs/en/docs/advanced/events.md] | The app already uses lifespan to initialize DB and Redis, so Phase 3 should tighten that path instead of adding a second startup hook. [VERIFIED: apps/api/main_v2.py] |
| SQLAlchemy async ORM | `2.0.43` [VERIFIED: uv.lock] | Provides ORM metadata and DB engine/session lifecycle. [VERIFIED: apps/api/infrastructure/database.py][VERIFIED: apps/api/models/database_models.py] | Official SQLAlchemy docs treat `MetaData.create_all()` as useful for tests/small/new DBs, while long-term schema evolution should use a migration tool. [CITED: https://docs.sqlalchemy.org/en/20/tutorial/metadata.html][CITED: https://docs.sqlalchemy.org/en/20/faq/metadata_schema.html] |
| Manifest-tracked SQL migrations | repo-local chain `001` through `006` [VERIFIED: apps/api/infrastructure/migration_manifest.py] | Current source of truth for schema bootstrap and backfills. [VERIFIED: apps/api/scripts/apply_migrations.py][VERIFIED: apps/api/migrations/006_canonical_job_status_backfill.sql] | The repo already uses this chain in production startup and recent schema work; Phase 3 should reinforce it, not replace it. [VERIFIED: apps/api/infrastructure/database.py][VERIFIED: .planning/phases/02-job-vocabulary/02-VERIFICATION.md] |
| Pytest | `8.4.2` [VERIFIED: uv.lock][VERIFIED: `uv run pytest --version`] | Test harness for unit/integration/bootstrap proof. [VERIFIED: apps/api/pyproject.toml] | Existing phase work and CI already use pytest, so new proof should land in the same validation path. [VERIFIED: .github/workflows/ci.yml][VERIFIED: apps/api/scripts/run_quality_ci.sh] |

### Supporting

| Library / Tool | Version | Purpose | When to Use |
|----------------|---------|---------|-------------|
| asyncpg | `0.30.0` [VERIFIED: uv.lock] | Low-level Postgres connectivity for the migration runner and DB smoke checks. [VERIFIED: apps/api/scripts/apply_migrations.py][VERIFIED: apps/api/scripts/test_db_connection.py] | Use for bootstrap/migration scripts where raw SQL execution and advisory locks are the real contract. [VERIFIED: apps/api/scripts/apply_migrations.py] |
| Docker | `29.2.1` locally available [VERIFIED: `docker info --format '{{.ServerVersion}}'`] | Local fallback for running a disposable Postgres instance when no host DB is running. [VERIFIED: `pg_isready`] | Use for fresh-bootstrap proof on developer machines, because local Postgres is not currently running. [VERIFIED: `pg_isready`] |
| Redis | `redis` Python package `6.4.0`; local server unavailable in this session [VERIFIED: uv.lock][VERIFIED: `redis-cli ping`] | Startup still attempts Redis initialization, but the runtime intentionally degrades if Redis is absent. [VERIFIED: apps/api/main_v2.py] | Phase 3 should verify bootstrap even with Redis unavailable; Redis is not a blocker for schema bootstrap proof. [VERIFIED: apps/api/main_v2.py][VERIFIED: .planning/REQUIREMENTS.md] |
| Alembic | `1.18.4` present in lockfile but not wired as active app migration env [VERIFIED: uv.lock][VERIFIED: apps/api/Makefile][VERIFIED: apps/api] | Possible long-term migration framework if the repo later chooses to standardize on it. [CITED: https://github.com/sqlalchemy/alembic/blob/main/docs/build/tutorial.md] | Do not introduce it as a second live migration system inside Phase 3. [VERIFIED: apps/api/scripts/apply_migrations.py][VERIFIED: apps/api/Makefile] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Existing manifest runner [VERIFIED: apps/api/scripts/apply_migrations.py] | New Alembic environment [CITED: https://github.com/sqlalchemy/alembic/blob/main/docs/build/tutorial.md] | Alembic is a standard migration framework, but adding it now would create two competing truths because the repo already ships a manifest runner and startup guard built around `schema_migrations`. [VERIFIED: apps/api/scripts/apply_migrations.py][VERIFIED: apps/api/infrastructure/database.py][VERIFIED: apps/api/Makefile] |
| Startup fail-closed check [VERIFIED: apps/api/infrastructure/database.py] | Startup self-healing with `create_all()` or silent table creation [CITED: https://docs.sqlalchemy.org/en/20/tutorial/metadata.html] | Self-healing would hide drift and mixed state; the requirement explicitly wants production bootstrap to come from the unified chain, not ORM DDL side effects. [VERIFIED: .planning/REQUIREMENTS.md][VERIFIED: apps/api/infrastructure/database.py] |

**Installation / sync path:**

```bash
cd apps/api
uv sync --group dev
```

[VERIFIED: AGENTS.md][VERIFIED: apps/api/README.md]

## Architecture Patterns

### Recommended Project Structure

```text
apps/api/
├── main_v2.py                        # FastAPI lifespan startup entrypoint
├── infrastructure/
│   ├── database.py                   # startup guard / engine lifecycle
│   └── migration_manifest.py         # canonical active migration chain
├── scripts/
│   └── apply_migrations.py           # manifest runner + checksum tracking
├── migrations/                       # unified SQL chain + legacy file still present
├── tests/
│   ├── unit/                         # guard behavior and manifest unit tests
│   ├── integration/                  # fresh DB bootstrap / startup rejection proof
│   └── platform/                     # shared harness, currently create_all-based
└── docs/ / README.md                 # operator-facing bootstrap truth
```

[VERIFIED: apps/api/main_v2.py][VERIFIED: apps/api/infrastructure/database.py][VERIFIED: apps/api/infrastructure/migration_manifest.py][VERIFIED: apps/api/scripts/apply_migrations.py][VERIFIED: apps/api/tests/platform/fixtures.py]

### Pattern 1: Manifest-First Bootstrap

**What:** Treat `ACTIVE_MIGRATIONS` as the only ordered list of schema files that define the live bootstrap path. [VERIFIED: apps/api/infrastructure/migration_manifest.py]
**When to use:** Any fresh DB bootstrap, schema backfill, or startup preflight in non-test environments. [VERIFIED: apps/api/infrastructure/database.py][VERIFIED: apps/api/scripts/apply_migrations.py]
**Example:**

```python
# Source pattern: apps/api/infrastructure/migration_manifest.py
ACTIVE_MIGRATIONS = [
    '001_unified_schema.sql',
    '002_add_prediction_created_by.sql',
    '003_add_race_odds.sql',
    '004_add_job_shadow_fields.sql',
    '005_add_usage_events.sql',
    '006_canonical_job_status_backfill.sql',
]
```

[VERIFIED: apps/api/infrastructure/migration_manifest.py]

### Pattern 2: Fail-Closed Startup Verification Before Serving Requests

**What:** Startup should verify migration state before the app accepts traffic; FastAPI lifespan is the correct hook for that. [VERIFIED: apps/api/main_v2.py][CITED: https://github.com/fastapi/fastapi/blob/0.118.2/docs/en/docs/advanced/events.md]
**When to use:** `ENVIRONMENT != test` and non-SQLite runtime paths. [VERIFIED: apps/api/infrastructure/database.py]
**Example:**

```python
# Source pattern: apps/api/main_v2.py + apps/api/infrastructure/database.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()   # should fail before serving if manifest state is wrong
    yield
```

[VERIFIED: apps/api/main_v2.py][VERIFIED: apps/api/infrastructure/database.py]

### Pattern 3: Fresh-Bootstrap Proof Must Be Separate From Test Harness Schema Seeding

**What:** Unit harnesses may still use `create_all()` for speed, but Phase 3 acceptance must include a production-like path that boots an empty Postgres DB only through the manifest runner. [VERIFIED: apps/api/tests/platform/fixtures.py][VERIFIED: .planning/ROADMAP.md]
**When to use:** Integration tests, CI checks, and operator runbooks for empty-database bring-up. [VERIFIED: .github/workflows/ci.yml][VERIFIED: apps/api/docs/SUPABASE_SETUP.md]
**Example:**

```bash
cd apps/api
uv run python scripts/apply_migrations.py
uv run pytest -q tests/integration/test_bootstrap_manifest.py -o addopts=""
```

The second command does not exist yet and should be created in this phase. [VERIFIED: apps/api/tests]

### Anti-Patterns to Avoid

- **Production-path `create_all()` proof:** `init_db()` already branches to `create_all()` for test/SQLite only; using that path as Phase 3 acceptance would miss the actual production contract. [VERIFIED: apps/api/infrastructure/database.py][CITED: https://docs.sqlalchemy.org/en/20/tutorial/metadata.html]
- **Second migration truth:** `apps/api/Makefile` still exposes Alembic commands while the live codebase uses a custom manifest runner; Phase 3 should converge on one operator story, not keep both active. [VERIFIED: apps/api/Makefile][VERIFIED: apps/api/scripts/apply_migrations.py]
- **Manual baseline choice:** Operator docs still warn users to pick between `001_initial_schema.sql` and `001_unified_schema.sql`; Phase 3 should eliminate “choose the right baseline” as an operational task. [VERIFIED: apps/api/README.md][VERIFIED: apps/api/docs/SUPABASE_SETUP.md][VERIFIED: apps/api/scripts/setup.sh]
- **Silent mixed-state acceptance:** `verify_schema()` logs extra tables but does not fail on them, and startup guard only checks migration names; that leaves room for legacy/unified coexistence to slip through. [VERIFIED: apps/api/scripts/apply_migrations.py][VERIFIED: apps/api/infrastructure/database.py]

## Likely Files to Modify

| File | Why It Matters | Likely Change |
|------|----------------|---------------|
| `apps/api/infrastructure/database.py` [VERIFIED] | Owns non-test startup gate. [VERIFIED: apps/api/infrastructure/database.py] | Strengthen `require_migration_manifest()` to reject mixed legacy markers or unexpected physical schema state, not only missing `schema_migrations` rows. [VERIFIED: apps/api/infrastructure/database.py][VERIFIED: apps/api/migrations/001_initial_schema.sql] |
| `apps/api/scripts/apply_migrations.py` [VERIFIED] | Owns manifest application and preflight reporting. [VERIFIED: apps/api/scripts/apply_migrations.py] | Add explicit mixed-state detection / operator-facing failure reasons / non-interactive verification hooks for fresh bootstrap proof. [VERIFIED: apps/api/scripts/apply_migrations.py] |
| `apps/api/tests/platform/fixtures.py` [VERIFIED] | Current shared harness seeds DB with `create_all()`. [VERIFIED: apps/api/tests/platform/fixtures.py] | Keep fast unit harness if needed, but stop using it as proof of SCHEMA-01. [VERIFIED: apps/api/tests/platform/fixtures.py][VERIFIED: .planning/REQUIREMENTS.md] |
| `apps/api/tests/integration/*` [VERIFIED: apps/api/tests] | Missing production-like fresh-bootstrap and mixed-state rejection tests. [VERIFIED: apps/api/tests][VERIFIED: .github/workflows/ci.yml] | Add empty-DB bootstrap and non-test startup rejection coverage. [VERIFIED: .planning/ROADMAP.md] |
| `.github/workflows/ci.yml` [VERIFIED] | Current CI forces `ENVIRONMENT=test` for tests. [VERIFIED: .github/workflows/ci.yml] | Add a bootstrap guard lane that runs migrations and startup verification in a non-test environment. [VERIFIED: .github/workflows/ci.yml][VERIFIED: apps/api/main_v2.py] |
| `apps/api/scripts/setup.sh` [VERIFIED] | Still points operators to `001_initial_schema.sql`. [VERIFIED: apps/api/scripts/setup.sh] | Replace legacy baseline instructions with manifest-first bootstrap steps. [VERIFIED: apps/api/scripts/setup.sh][VERIFIED: apps/api/README.md] |
| `apps/api/Makefile` [VERIFIED] | Still advertises Alembic. [VERIFIED: apps/api/Makefile] | Remove or demote stale Alembic targets if they are not part of the active runtime story. [VERIFIED: apps/api/Makefile][VERIFIED: apps/api] |
| `apps/api/README.md` and `apps/api/docs/SUPABASE_SETUP.md` [VERIFIED] | Current docs still frame legacy/unified coexistence as operator choice. [VERIFIED: apps/api/README.md][VERIFIED: apps/api/docs/SUPABASE_SETUP.md] | Make one bootstrap path canonical and document the verification proof. [VERIFIED: .planning/ROADMAP.md] |

## Concrete Planning Slices

1. **Slice A: Lock manifest truth.** Confirm `migration_manifest.py` is the sole active ordered chain, and decide whether `001_initial_schema.sql` is archived now or only treated as a legacy marker to reject. [VERIFIED: apps/api/infrastructure/migration_manifest.py][VERIFIED: apps/api/migrations/001_initial_schema.sql]
2. **Slice B: Harden preflight and startup rejection.** Extend `apply_migrations.py` and `database.py` so missing `schema_migrations`, unexpected migration names, and legacy-marker mixed tables all fail closed in non-test startup. [VERIFIED: apps/api/scripts/apply_migrations.py][VERIFIED: apps/api/infrastructure/database.py]
3. **Slice C: Add fresh-bootstrap proof.** Create a production-like test path that starts from an empty Postgres DB, runs the manifest chain, then exercises `init_db()` / lifespan with `ENVIRONMENT=development` or `production`, not `test`. [VERIFIED: .github/workflows/ci.yml][VERIFIED: apps/api/main_v2.py][VERIFIED: apps/api/tests/platform/fixtures.py]
4. **Slice D: Clean operator entrypoints.** Remove stale `001_initial_schema.sql` and Alembic instructions from setup scripts/docs so new operators follow one bootstrap path. [VERIFIED: apps/api/scripts/setup.sh][VERIFIED: apps/api/Makefile][VERIFIED: apps/api/README.md]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fresh schema creation in production | Ad hoc `create_all()` or table-exists heuristics at app startup [CITED: https://docs.sqlalchemy.org/en/20/tutorial/metadata.html] | The existing manifest runner plus fail-closed startup verification. [VERIFIED: apps/api/scripts/apply_migrations.py][VERIFIED: apps/api/infrastructure/database.py] | `create_all()` is fine for tests/small/new DBs, but official SQLAlchemy guidance points long-term schema evolution to migration tooling, and the repo already has a tracked chain. [CITED: https://docs.sqlalchemy.org/en/20/tutorial/metadata.html][CITED: https://docs.sqlalchemy.org/en/20/faq/metadata_schema.html][VERIFIED: apps/api/infrastructure/migration_manifest.py] |
| Mixed legacy/unified recovery | Silent auto-repair, implicit table drops, or startup self-healing [VERIFIED: apps/api/scripts/apply_migrations.py] | Explicit preflight detection plus operator-visible failure and manual remediation path. [VERIFIED: apps/api/scripts/apply_migrations.py][VERIFIED: apps/api/infrastructure/database.py] | Mixed state is high-risk because legacy and unified schemas do not describe the same tables or column names. [VERIFIED: apps/api/migrations/001_initial_schema.sql][VERIFIED: apps/api/migrations/001_unified_schema.sql] |
| Migration framework swap inside this phase | Introducing a second live Alembic chain while the manifest runner remains in use. [VERIFIED: apps/api/Makefile][VERIFIED: apps/api/scripts/apply_migrations.py] | Keep one canonical migration story in Phase 3; defer any framework migration to a separate project decision. [VERIFIED: .planning/ROADMAP.md] | Changing frameworks during a bootstrap-truth phase adds migration-risk without helping SCHEMA-01 or SCHEMA-02 directly. [VERIFIED: .planning/REQUIREMENTS.md] |

**Key insight:** Phase 3 should remove ambiguity, not maximize tooling sophistication. One chain, one startup gate, one proof path. [VERIFIED: .planning/ROADMAP.md][VERIFIED: .planning/STATE.md]

## Runtime State Inventory

| Category | Items Found | Action Required |
|----------|-------------|-----------------|
| Stored data | `schema_migrations` is the canonical applied-state table in current code, and legacy SQL can create incompatible tables such as `collection_jobs`, `race_results`, `prompt_versions`, and `performance_analysis`. Live remote DB contents were not inspected in this session. [VERIFIED: apps/api/scripts/apply_migrations.py][VERIFIED: apps/api/migrations/001_initial_schema.sql] | Add code-level mixed-state detection and require an operator audit/remediation step for any DB that already contains legacy-marker tables. This is partly a code edit and partly a runtime data audit. [VERIFIED: apps/api/infrastructure/database.py][VERIFIED: apps/api/scripts/apply_migrations.py] |
| Live service config | Operator guidance still exists in live docs/scripts, including `scripts/setup.sh` telling users to run `001_initial_schema.sql` manually and `SUPABASE_SETUP.md` describing manual baseline judgment. [VERIFIED: apps/api/scripts/setup.sh][VERIFIED: apps/api/docs/SUPABASE_SETUP.md] | Update the operator path so the live service configuration flow points only to manifest-first bootstrap. This is a code/doc edit, not a data migration. [VERIFIED: apps/api/README.md][VERIFIED: apps/api/scripts/setup.sh] |
| OS-registered state | No active runtime registration files for `systemd`, `launchd`, `pm2`, or similar were found in repo-tracked runtime assets; only stale docs mention cron/Celery-style schedules. [VERIFIED: repo-wide `rg -n "systemd|launchd|pm2|Task Scheduler|cron|crontab|plist|service unit"`] | None for Phase 3 code, but stale docs referencing scheduler-style legacy runtime should stay out of bootstrap instructions. [VERIFIED: docs/unified-collection-api-design.md] |
| Secrets / env vars | `DATABASE_URL`, `ENVIRONMENT`, `SECRET_KEY`, `VALID_API_KEYS`, `REDIS_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, and `SUPABASE_SERVICE_ROLE_KEY` are part of the active runtime/config path. [VERIFIED: apps/api/.env.template][VERIFIED: apps/api/config.py][VERIFIED: .github/workflows/ci.yml] | Keep env names stable in this phase; adjust docs/CI only where startup verification needs non-test env coverage. This is a code/config edit, not a secret rotation. [VERIFIED: apps/api/config.py][VERIFIED: .github/workflows/ci.yml] |
| Build artifacts | The deployable runtime remains the API app/container, and local proof can use Docker because no local Postgres service is running in this session. [VERIFIED: apps/api/Dockerfile][VERIFIED: `docker info --format '{{.ServerVersion}}'`][VERIFIED: `pg_isready`] | Rebuild/redeploy the API artifact after startup-guard changes; use Docker Postgres for local bootstrap proof if host Postgres is unavailable. [VERIFIED: apps/api/Dockerfile][VERIFIED: `docker info --format '{{.ServerVersion}}'`] |

## Common Pitfalls

### Pitfall 1: Treating current unit tests as bootstrap proof

**What goes wrong:** The suite stays green while production bootstrap is still unproven because shared fixtures create schema with `Base.metadata.create_all()`. [VERIFIED: apps/api/tests/platform/fixtures.py]
**Why it happens:** The fast test harness optimizes for isolated in-memory DB setup, not production-like migration bootstrap. [VERIFIED: apps/api/tests/platform/fixtures.py][CITED: https://docs.sqlalchemy.org/en/20/tutorial/metadata.html]
**How to avoid:** Keep the fast harness, but add a separate Postgres bootstrap test that uses only `scripts/apply_migrations.py` plus non-test startup. [VERIFIED: apps/api/scripts/apply_migrations.py][VERIFIED: apps/api/main_v2.py]
**Warning signs:** CI only sets `ENVIRONMENT=test`, and no test starts from an empty Postgres DB through the manifest runner. [VERIFIED: .github/workflows/ci.yml]

### Pitfall 2: Believing startup already rejects all unexpected schema states

**What goes wrong:** Startup can reject missing/unknown migration names, but it does not currently reject a DB that also carries legacy physical tables if `schema_migrations` looks correct. [VERIFIED: apps/api/infrastructure/database.py][VERIFIED: apps/api/scripts/apply_migrations.py]
**Why it happens:** `require_migration_manifest()` reads `schema_migrations` only, and `verify_schema()` reports extra tables without failing. [VERIFIED: apps/api/infrastructure/database.py][VERIFIED: apps/api/scripts/apply_migrations.py]
**How to avoid:** Add explicit legacy-marker table detection to startup/preflight and fail closed when mixed schema state is detected. [VERIFIED: apps/api/migrations/001_initial_schema.sql][VERIFIED: apps/api/infrastructure/database.py]
**Warning signs:** Tables like `collection_jobs`, `race_results`, or `prompt_versions` appear beside unified tables like `jobs` and `job_logs`. [VERIFIED: apps/api/migrations/001_initial_schema.sql][VERIFIED: apps/api/migrations/001_unified_schema.sql]

### Pitfall 3: Cleaning docs too late

**What goes wrong:** Operators keep following stale bootstrap instructions even after code is fixed. [VERIFIED: apps/api/scripts/setup.sh][VERIFIED: apps/api/Makefile]
**Why it happens:** Bootstrap truth currently lives across README, setup script, Makefile, and setup docs, and they disagree. [VERIFIED: apps/api/README.md][VERIFIED: apps/api/scripts/setup.sh][VERIFIED: apps/api/Makefile][VERIFIED: apps/api/docs/SUPABASE_SETUP.md]
**How to avoid:** Include operator entrypoint cleanup in Phase 3 acceptance, not as a docs-only afterthought. [VERIFIED: .planning/ROADMAP.md]
**Warning signs:** Instructions still mention `001_initial_schema.sql` or `alembic upgrade head` after the phase lands. [VERIFIED: apps/api/scripts/setup.sh][VERIFIED: apps/api/Makefile]

## Code Examples

Verified patterns from the current repo and official docs:

### Startup Verification in FastAPI Lifespan

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()   # fail before serving requests if schema state is wrong
    yield
```

Source pattern: `apps/api/main_v2.py` [VERIFIED: apps/api/main_v2.py]  
Official lifecycle reference: FastAPI lifespan docs [CITED: https://github.com/fastapi/fastapi/blob/0.118.2/docs/en/docs/advanced/events.md]

### Manifest Comparison Guard

```python
required = get_active_migration_names()
applied = await get_applied_migrations()

missing = [name for name in required if name not in applied]
unexpected = [name for name in applied if name not in required]

if missing or unexpected:
    raise RuntimeError("Database migration manifest mismatch")
```

Source pattern: `apps/api/infrastructure/database.py` [VERIFIED: apps/api/infrastructure/database.py]

### SQLAlchemy `create_all()` Scope

```python
Base.metadata.create_all(engine)
```

Official SQLAlchemy docs describe this as useful for tests, small/new apps, or short-lived databases, while recommending a migration tool for long-term schema evolution. [CITED: https://docs.sqlalchemy.org/en/20/tutorial/metadata.html][CITED: https://docs.sqlalchemy.org/en/20/faq/metadata_schema.html]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Legacy baseline SQL such as `001_initial_schema.sql` manually chosen by operators. [VERIFIED: apps/api/migrations/001_initial_schema.sql] | Active baseline is the ordered manifest ending at `006_canonical_job_status_backfill.sql`. [VERIFIED: apps/api/infrastructure/migration_manifest.py] | Canonicalized in rollout work on 2026-03-20. [VERIFIED: docs/plans/2026-03-19-architecture-rollout-execplan.md] | Phase 3 should prove and operationalize this truth, not rediscover it. [VERIFIED: .planning/STATE.md] |
| Startup could silently create schema in non-production `development` paths. [VERIFIED: docs/plans/2026-03-19-architecture-remediation-execplan.md] | Current `init_db()` uses `create_all()` only for `test` or SQLite and otherwise requires manifest state. [VERIFIED: apps/api/infrastructure/database.py] | Landed by 2026-03-20 rollout work. [VERIFIED: docs/plans/2026-03-19-architecture-rollout-execplan.md] | Acceptance now depends on proving this path in real bootstrap tests and CI. [VERIFIED: .github/workflows/ci.yml][VERIFIED: apps/api/tests/platform/fixtures.py] |
| Migration verification previously assumed legacy tables like `race_results` and `collection_jobs`. [VERIFIED: docs/plans/2026-03-19-architecture-rollout-execplan.md] | Current runner verifies unified required tables and tracks applied files in `schema_migrations`. [VERIFIED: apps/api/scripts/apply_migrations.py] | Changed during candidate I rollout on 2026-03-20. [VERIFIED: docs/plans/2026-03-19-architecture-rollout-execplan.md] | Remaining gap is explicit mixed-state rejection and end-to-end proof. [VERIFIED: apps/api/scripts/apply_migrations.py][VERIFIED: apps/api/infrastructure/database.py] |

**Deprecated / outdated:**

- Treating `001_initial_schema.sql` as the bootstrap baseline is outdated. [VERIFIED: apps/api/README.md][VERIFIED: apps/api/docs/SUPABASE_SETUP.md][VERIFIED: apps/api/scripts/setup.sh]
- `apps/api/Makefile` Alembic targets are outdated relative to the active runtime path. [VERIFIED: apps/api/Makefile][VERIFIED: apps/api/scripts/apply_migrations.py]
- Using CI green under `ENVIRONMENT=test` as evidence of production-like bootstrap health is outdated. [VERIFIED: .github/workflows/ci.yml][VERIFIED: apps/api/tests/platform/fixtures.py]

## Assumptions Log

All material claims in this research were either verified from the codebase or cited from official documentation. The only missing information is live database state, which is recorded as an open question rather than treated as an assumption. [VERIFIED: apps/api/infrastructure/database.py][VERIFIED: apps/api/scripts/apply_migrations.py]

## Open Questions

1. **Should Phase 3 physically archive `001_initial_schema.sql`, or only detect and reject it as legacy state?** [VERIFIED: apps/api/migrations/001_initial_schema.sql][VERIFIED: .planning/ROADMAP.md]  
   What we know: the active chain ignores it, but operator docs and scripts still expose it. [VERIFIED: apps/api/infrastructure/migration_manifest.py][VERIFIED: apps/api/scripts/setup.sh]  
   Recommendation: decide this explicitly in planning because it changes the cleanup scope and doc touches. [VERIFIED: apps/api/scripts/setup.sh][VERIFIED: apps/api/README.md]

2. **How strict should mixed-state rejection be at startup?** [VERIFIED: apps/api/infrastructure/database.py][VERIFIED: apps/api/scripts/apply_migrations.py]  
   What we know: current startup guard checks migration names only; current runner logs extra tables without failing. [VERIFIED: apps/api/infrastructure/database.py][VERIFIED: apps/api/scripts/apply_migrations.py]  
   Recommendation: plan a fail-closed rule for obvious legacy markers, and keep the allowlist small and explicit. [VERIFIED: apps/api/migrations/001_initial_schema.sql][VERIFIED: apps/api/migrations/001_unified_schema.sql]

3. **Does Phase 3 include all operator doc cleanup or only the bootstrap-critical ones?** [VERIFIED: apps/api/README.md][VERIFIED: apps/api/docs/SUPABASE_SETUP.md][VERIFIED: apps/api/scripts/setup.sh][VERIFIED: apps/api/Makefile]  
   What we know: SCHEMA-03 and broader docs cleanup are assigned to Phase 6, but Phase 3 success criteria still require a documented migration-first verification path. [VERIFIED: .planning/ROADMAP.md][VERIFIED: .planning/REQUIREMENTS.md]  
   Recommendation: update only the bootstrap-critical entrypoints in Phase 3, and defer broader doc harmonization to Phase 6. [VERIFIED: .planning/ROADMAP.md]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `uv` | Python dependency sync and test execution [VERIFIED: AGENTS.md] | ✓ [VERIFIED: `uv --version`] | `0.10.9` [VERIFIED: `uv --version`] | — |
| Python via `uv run` | App runtime baseline and migration scripts [VERIFIED: apps/api/pyproject.toml] | ✓ [VERIFIED: `uv run python --version`] | `3.13.12` [VERIFIED: `uv run python --version`] | System `python3` is `3.14.3`, but project commands should stay on `uv run` for the repo baseline. [VERIFIED: `python3 --version`][VERIFIED: ./CLAUDE.md] |
| `pnpm` | Workspace commands / CI parity [VERIFIED: AGENTS.md] | ✓ [VERIFIED: `pnpm --version`] | `9.0.0` [VERIFIED: `pnpm --version`] | — |
| Docker | Local disposable Postgres for fresh-bootstrap proof [VERIFIED: `docker info --format '{{.ServerVersion}}'`] | ✓ [VERIFIED: `docker info --format '{{.ServerVersion}}'`] | `29.2.1` [VERIFIED: `docker info --format '{{.ServerVersion}}'`] | — |
| Local PostgreSQL service | Real bootstrap verification against Postgres semantics [VERIFIED: .github/workflows/ci.yml] | ✗ in this session [VERIFIED: `pg_isready`] | — | Use Docker Postgres or CI service container. [VERIFIED: `docker info --format '{{.ServerVersion}}'`][VERIFIED: .github/workflows/ci.yml] |
| Local Redis service | Optional runtime startup path [VERIFIED: apps/api/main_v2.py] | ✗ in this session [VERIFIED: `redis-cli ping`] | — | Use degraded startup path; Redis is not required to prove schema bootstrap. [VERIFIED: apps/api/main_v2.py][VERIFIED: .planning/REQUIREMENTS.md] |

**Missing dependencies with no fallback:**

- None for planning and local proof, because Docker is available for Postgres bootstrap and Redis is intentionally optional for startup. [VERIFIED: `docker info --format '{{.ServerVersion}}'`][VERIFIED: apps/api/main_v2.py]

**Missing dependencies with fallback:**

- Host Postgres is not running, but Docker or CI service containers can provide a fresh DB. [VERIFIED: `pg_isready`][VERIFIED: .github/workflows/ci.yml]
- Host Redis is not running, but Phase 3 bootstrap proof can deliberately exercise the degraded path. [VERIFIED: `redis-cli ping`][VERIFIED: apps/api/main_v2.py]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest 8.4.2` with `pytest-asyncio`, `pytest-cov`, and `pytest-timeout` in the repo environment. [VERIFIED: uv.lock][VERIFIED: apps/api/pyproject.toml] |
| Config file | `apps/api/pyproject.toml` for pytest options and markers. [VERIFIED: apps/api/pyproject.toml] |
| Quick run command | `cd apps/api && uv run pytest -q tests/unit/test_database_migration_guard.py -o addopts=""` [VERIFIED: successful local command] |
| Full suite command | `bash apps/api/scripts/run_quality_ci.sh all` or `pnpm -F @apps/api test` for workspace entry. [VERIFIED: apps/api/scripts/run_quality_ci.sh][VERIFIED: AGENTS.md] |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCHEMA-01 | Empty Postgres DB can be bootstrapped only through the active manifest, then app startup passes without `create_all()` in non-test mode. [VERIFIED: .planning/REQUIREMENTS.md] | integration | `cd apps/api && uv run pytest -q tests/integration/test_bootstrap_manifest.py -o addopts=""` | ❌ Wave 0 [VERIFIED: apps/api/tests] |
| SCHEMA-02 | Startup rejects missing manifest rows, unexpected migration names, and mixed legacy/unified state in non-test environments. [VERIFIED: .planning/REQUIREMENTS.md] | unit + integration | `cd apps/api && uv run pytest -q tests/unit/test_database_migration_guard.py -o addopts=""` | ✅ partial [VERIFIED: successful local command][VERIFIED: apps/api/tests/unit/test_database_migration_guard.py] |
| SCHEMA-02 | Non-test app lifespan fails before serving when startup verification sees wrong schema state. [VERIFIED: .planning/REQUIREMENTS.md][VERIFIED: apps/api/main_v2.py] | integration | `cd apps/api && uv run pytest -q tests/integration/test_startup_manifest_rejection.py -o addopts=""` | ❌ Wave 0 [VERIFIED: apps/api/tests] |

### Sampling Rate

- **Per task commit:** `cd apps/api && uv run pytest -q tests/unit/test_database_migration_guard.py -o addopts=""` plus any new targeted bootstrap tests. [VERIFIED: successful local command]
- **Per wave merge:** `bash apps/api/scripts/run_quality_ci.sh all` plus the new non-test bootstrap lane. [VERIFIED: apps/api/scripts/run_quality_ci.sh][VERIFIED: .github/workflows/ci.yml]
- **Phase gate:** Fresh-DB bootstrap and non-test startup rejection must both pass before `/gsd-verify-work`. [VERIFIED: .planning/ROADMAP.md][VERIFIED: .planning/REQUIREMENTS.md]

### Wave 0 Gaps

- [ ] `apps/api/tests/integration/test_bootstrap_manifest.py` — empty Postgres bootstrap using only `scripts/apply_migrations.py`. [VERIFIED: apps/api/tests][VERIFIED: apps/api/scripts/apply_migrations.py]
- [ ] `apps/api/tests/integration/test_startup_manifest_rejection.py` — non-test lifespan/startup failure on wrong schema state. [VERIFIED: apps/api/tests][VERIFIED: apps/api/main_v2.py]
- [ ] CI bootstrap lane in `.github/workflows/ci.yml` — runs migrations and startup verification with `ENVIRONMENT != test`. [VERIFIED: .github/workflows/ci.yml]
- [ ] Optional helper script or fixture for disposable Postgres lifecycle in tests if Docker-based local proof is required. [VERIFIED: `docker info --format '{{.ServerVersion}}'`]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no direct phase scope [VERIFIED: .planning/REQUIREMENTS.md] | Existing API key auth remains unchanged in this phase. [VERIFIED: apps/api/dependencies/auth.py] |
| V3 Session Management | no [VERIFIED: .planning/REQUIREMENTS.md] | No session mechanism is introduced by bootstrap work. [VERIFIED: apps/api/main_v2.py] |
| V4 Access Control | yes [VERIFIED: apps/api/migrations/001_unified_schema.sql] | Unified schema enables RLS on core tables; bootstrap truth must not silently fall back to legacy schema that carries different table/security shape. [VERIFIED: apps/api/migrations/001_unified_schema.sql][VERIFIED: apps/api/migrations/001_initial_schema.sql] |
| V5 Input Validation | yes [VERIFIED: apps/api/config.py] | `Settings` validation and fail-closed startup protect against unsafe production env defaults. [VERIFIED: apps/api/config.py] |
| V6 Cryptography | no direct new crypto [VERIFIED: .planning/REQUIREMENTS.md] | Reuse existing `SECRET_KEY` handling; do not introduce custom crypto in this phase. [VERIFIED: apps/api/config.py] |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| App starts against an un-migrated or partially migrated DB and serves incorrect behavior. [VERIFIED: apps/api/infrastructure/database.py] | Tampering | Fail-closed startup guard before request serving. [VERIFIED: apps/api/main_v2.py][VERIFIED: apps/api/infrastructure/database.py][CITED: https://github.com/fastapi/fastapi/blob/0.118.2/docs/en/docs/advanced/events.md] |
| Operator bootstraps the wrong baseline (`001_initial_schema.sql`) and gets a schema that does not match the live ORM/runtime. [VERIFIED: apps/api/scripts/setup.sh][VERIFIED: apps/api/migrations/001_initial_schema.sql][VERIFIED: apps/api/models/database_models.py] | Tampering | One canonical manifest path plus doc/script cleanup and mixed-state rejection. [VERIFIED: apps/api/infrastructure/migration_manifest.py][VERIFIED: apps/api/scripts/apply_migrations.py] |
| Production env accidentally uses development-safe defaults or wrong DB target. [VERIFIED: apps/api/config.py] | Elevation of Privilege / Misconfiguration | Existing production config validation for `SECRET_KEY`, `VALID_API_KEYS`, and `DATABASE_URL`; Phase 3 should keep bootstrap checks on the same fail-closed axis. [VERIFIED: apps/api/config.py] |

## Sources

### Primary (HIGH confidence)

- `apps/api/infrastructure/database.py` — current startup guard, `init_db()` branching, manifest enforcement. [VERIFIED: apps/api/infrastructure/database.py]
- `apps/api/infrastructure/migration_manifest.py` — active migration chain and canonical head. [VERIFIED: apps/api/infrastructure/migration_manifest.py]
- `apps/api/scripts/apply_migrations.py` — checksum/advisory-lock migration runner and current schema verification behavior. [VERIFIED: apps/api/scripts/apply_migrations.py]
- `apps/api/main_v2.py` — FastAPI lifespan startup path. [VERIFIED: apps/api/main_v2.py]
- `apps/api/tests/platform/fixtures.py` — current `create_all()`-based test harness. [VERIFIED: apps/api/tests/platform/fixtures.py]
- `.github/workflows/ci.yml` — current test environment strategy and missing non-test bootstrap lane. [VERIFIED: .github/workflows/ci.yml]
- `apps/api/migrations/001_initial_schema.sql` and `apps/api/migrations/001_unified_schema.sql` — legacy/unified coexistence evidence. [VERIFIED: apps/api/migrations/001_initial_schema.sql][VERIFIED: apps/api/migrations/001_unified_schema.sql]
- SQLAlchemy 2.0 official docs on `MetaData.create_all()` and migration-tool guidance. [CITED: https://docs.sqlalchemy.org/en/20/tutorial/metadata.html][CITED: https://docs.sqlalchemy.org/en/20/faq/metadata_schema.html]
- FastAPI official docs on lifespan startup/shutdown handling. [CITED: https://github.com/fastapi/fastapi/blob/0.118.2/docs/en/docs/advanced/events.md]
- Alembic official docs on standard upgrade workflow. [CITED: https://github.com/sqlalchemy/alembic/blob/main/docs/build/tutorial.md]

### Secondary (MEDIUM confidence)

- `docs/plans/2026-03-19-architecture-rollout-execplan.md` — confirms the repo’s earlier migration-truth rollout intent and what was considered “done” on 2026-03-20. [VERIFIED: docs/plans/2026-03-19-architecture-rollout-execplan.md]
- `.planning/codebase/CONCERNS.md` — captures repository-level risk framing for migration truth and missing CI bootstrap proof. [VERIFIED: .planning/codebase/CONCERNS.md]

### Tertiary (LOW confidence)

- None. [VERIFIED: this research file]

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH — the active runtime, lockfile versions, and startup path are all directly visible in repo files and local tool output. [VERIFIED: apps/api/pyproject.toml][VERIFIED: uv.lock][VERIFIED: apps/api/main_v2.py]
- Architecture: HIGH — bootstrap, manifest, and startup behavior are explicitly implemented in a small set of files. [VERIFIED: apps/api/infrastructure/database.py][VERIFIED: apps/api/scripts/apply_migrations.py][VERIFIED: apps/api/infrastructure/migration_manifest.py]
- Pitfalls: MEDIUM-HIGH — repo evidence clearly shows coexistence/doc drift and missing CI proof, but live remote DB mixed state still requires operator inspection. [VERIFIED: apps/api/scripts/setup.sh][VERIFIED: apps/api/Makefile][VERIFIED: .github/workflows/ci.yml]

**Research date:** 2026-04-05 [VERIFIED: system date]  
**Valid until:** 2026-05-05 for repo-internal facts, or earlier if migration/bootstrap code changes before planning. [VERIFIED: apps/api/infrastructure/database.py][VERIFIED: apps/api/scripts/apply_migrations.py]
