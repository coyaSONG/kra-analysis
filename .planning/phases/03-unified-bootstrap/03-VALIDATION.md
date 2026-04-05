---
phase: 03
slug: unified-bootstrap
status: ready
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-05
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | `apps/api/pyproject.toml`, `apps/api/pytest.ini` |
| **Quick run command** | `cd apps/api && uv run pytest -q tests/unit/test_migration_manifest.py tests/unit/test_database_migration_guard.py -o addopts=''` |
| **Full suite command** | `cd apps/api && uv run pytest -q tests/unit/test_migration_manifest.py tests/unit/test_database_migration_guard.py tests/platform tests/integration/test_bootstrap_manifest.py tests/integration/test_startup_manifest_rejection.py -o addopts=''` |
| **Estimated runtime** | ~30 seconds for quick loop, ~90 seconds for full suite |

---

## Sampling Rate

- **After every task commit:** Run `cd apps/api && uv run pytest -q tests/unit/test_migration_manifest.py tests/unit/test_database_migration_guard.py -o addopts=''`
- **After every plan wave:** Run `cd apps/api && uv run pytest -q tests/unit/test_migration_manifest.py tests/unit/test_database_migration_guard.py tests/platform tests/integration/test_bootstrap_manifest.py tests/integration/test_startup_manifest_rejection.py -o addopts=''`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds on the task-level quick loop; the slower ~90 second full suite is reserved for post-wave gates because bootstrap proof spans platform/integration fixtures

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | SCHEMA-01, SCHEMA-02 | T-03-01 | Unified manifest publishes one active chain and explicit inactive legacy markers | unit | `cd apps/api && uv run pytest -q tests/unit/test_migration_manifest.py -o addopts=''` | ✅ | ⬜ pending |
| 03-01-02 | 01 | 1 | SCHEMA-01, SCHEMA-02 | T-03-02 | Migration runner consumes manifest truth directly and refuses missing active files | unit | `cd apps/api && uv run pytest -q tests/unit/test_migration_manifest.py -o addopts=''` | ✅ | ⬜ pending |
| 03-02-01 | 02 | 2 | SCHEMA-02 | T-03-04 | Startup guard rejects missing, unexpected, and mixed legacy/unified schema states | unit | `cd apps/api && uv run pytest -q tests/unit/test_database_migration_guard.py -o addopts=''` | ✅ | ⬜ pending |
| 03-02-02 | 02 | 2 | SCHEMA-02 | T-03-05 | FastAPI lifespan aborts request serving when manifest guard fails | integration | `cd apps/api && uv run pytest -q tests/unit/test_database_migration_guard.py tests/integration/test_startup_manifest_rejection.py -o addopts=''` | ✅ | ⬜ pending |
| 03-03-01 | 03 | 3 | SCHEMA-01 | T-03-07 / T-03-09 | Fresh bootstrap proof uses manifest-first Postgres path rather than production-path `create_all()` | platform/integration | `cd apps/api && uv run pytest -q tests/platform tests/integration/test_bootstrap_manifest.py -o addopts='' -k 'bootstrap or migration'` | ✅ | ⬜ pending |
| 03-03-02 | 03 | 3 | SCHEMA-01, SCHEMA-02 | T-03-08 | CI runs non-test bootstrap proof and startup rejection checks against Postgres | integration/ci | `cd apps/api && uv run pytest -q tests/integration/test_bootstrap_manifest.py tests/integration/test_startup_manifest_rejection.py -o addopts=''` | ✅ | ⬜ pending |
| 03-04-01 | 04 | 4 | SCHEMA-01, SCHEMA-02 | T-03-10 | Shell and Makefile entrypoints expose only migration-first bootstrap commands | docs/smoke | `bash -n apps/api/scripts/setup.sh` | ✅ | ⬜ pending |
| 03-04-02 | 04 | 4 | SCHEMA-01, SCHEMA-02 | T-03-11 / T-03-12 | README and Supabase setup docs describe one bootstrap and fail-closed remediation path | docs/integration | `cd apps/api && uv run pytest -q tests/integration/test_bootstrap_manifest.py tests/integration/test_startup_manifest_rejection.py -o addopts=''` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers the planning-stage validation contract for this phase. Bootstrap-proof fixtures and tests are plan deliverables in Waves 2-4, not a missing Wave 0 prerequisite.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Fresh Postgres bootstrap against a disposable database | SCHEMA-01 | A real empty database instance may need Docker or external Postgres not guaranteed in CI | Run `uv run python scripts/apply_migrations.py` against an empty Postgres DB, then start `uv run uvicorn main_v2:app` with non-test `ENVIRONMENT` and confirm startup succeeds |
| Mixed legacy/unified schema rejection messaging is operator-clear | SCHEMA-02 | Failure text and remediation quality are partly UX/documentation concerns | Seed a DB with legacy-marker tables plus `schema_migrations`, start the app in non-test mode, and confirm startup fails with explicit remediation pointing to `scripts/apply_migrations.py` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s on task-level quick loop, with post-wave full suite explicitly exempted due to bootstrap proof cost
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-05
