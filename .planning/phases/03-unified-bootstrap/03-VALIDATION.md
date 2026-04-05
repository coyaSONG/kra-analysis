---
phase: 03
slug: unified-bootstrap
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| **Full suite command** | `cd apps/api && uv run pytest -q tests/unit/test_database_migration_guard.py tests/platform tests/integration -o addopts=''` |
| **Estimated runtime** | ~30 seconds for quick loop, ~90 seconds for full suite |

---

## Sampling Rate

- **After every task commit:** Run `cd apps/api && uv run pytest -q tests/unit/test_migration_manifest.py tests/unit/test_database_migration_guard.py -o addopts=''`
- **After every plan wave:** Run `cd apps/api && uv run pytest -q tests/unit/test_database_migration_guard.py tests/platform tests/integration -o addopts=''`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds on the task-level quick loop; the slower ~90 second full suite is reserved for post-wave gates because bootstrap proof spans platform/integration fixtures

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | SCHEMA-01 | T-03-01 | Unified manifest is the only active bootstrap chain and legacy baseline is not treated as current truth | unit | `cd apps/api && uv run pytest -q tests/unit/test_database_migration_guard.py -o addopts=''` | ✅ | ⬜ pending |
| 03-02-01 | 02 | 2 | SCHEMA-02 | T-03-02 | Startup fails closed on missing, unexpected, or mixed legacy/unified migration state | unit/integration | `cd apps/api && uv run pytest -q tests/unit/test_database_migration_guard.py tests/integration -o addopts='' -k 'migration or startup or bootstrap'` | ✅ | ⬜ pending |
| 03-03-01 | 03 | 3 | SCHEMA-01 | T-03-03 | Fresh database bootstrap is proven through manifest-first setup without production-path `create_all()` fallback | platform/integration | `cd apps/api && uv run pytest -q tests/platform tests/integration -o addopts='' -k 'bootstrap or migration'` | ✅ | ⬜ pending |
| 03-04-01 | 04 | 4 | SCHEMA-01, SCHEMA-02 | T-03-04 | Operator-facing entrypoints describe one migration-first bootstrap command set | docs/smoke | `cd apps/api && uv run pytest -q tests/integration -o addopts='' -k 'bootstrap or migration'` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `apps/api/tests/integration/test_bootstrap_*` or equivalent bootstrap-proof coverage — fresh DB migration-first proof
- [ ] `apps/api/tests/platform/fixtures.py` — remove production-proof dependence on `Base.metadata.create_all()`
- [ ] Existing pytest infrastructure covers all phase requirements once bootstrap-specific tests are added

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Fresh Postgres bootstrap against a disposable database | SCHEMA-01 | A real empty database instance may need Docker or external Postgres not guaranteed in CI | Run `uv run python scripts/apply_migrations.py` against an empty Postgres DB, then start `uv run uvicorn main_v2:app` with non-test `ENVIRONMENT` and confirm startup succeeds |
| Mixed legacy/unified schema rejection messaging is operator-clear | SCHEMA-02 | Failure text and remediation quality are partly UX/documentation concerns | Seed a DB with legacy-marker tables plus `schema_migrations`, start the app in non-test mode, and confirm startup fails with explicit remediation pointing to `scripts/apply_migrations.py` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s on task-level quick loop, with post-wave full suite explicitly exempted due to bootstrap proof cost
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
