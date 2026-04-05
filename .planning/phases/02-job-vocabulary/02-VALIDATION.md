---
phase: 02
slug: job-vocabulary
status: ready
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-05
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio + pytest-cov |
| **Config file** | `apps/api/pytest.ini`, `apps/api/.coveragerc` |
| **Quick run command** | `cd apps/api && uv run pytest -v --tb=short --timeout=60 -o addopts='' tests/unit/test_job_contract.py tests/unit/test_job_dispatch.py tests/unit/test_job_service.py tests/unit/test_async_tasks.py tests/integration/test_jobs_v2_router_additional.py tests/integration/test_api_endpoints.py -k 'job or async_collect or cancel_job'` |
| **Full suite command** | `pnpm -F @apps/api test` |
| **Estimated runtime** | ~35 seconds quick subset / full suite longer but required before verify |

---

## Sampling Rate

- **After every task commit:** Run the smallest targeted pytest subset for the touched job vocabulary seam with `-o addopts=''`.
- **After every plan wave:** Run `bash apps/api/scripts/run_quality_ci.sh unit` plus the explicit jobs integration files for collection async and jobs router coverage.
- **Before `/gsd-verify-work`:** Full suite must be green via `pnpm -F @apps/api test`.
- **Max feedback latency:** 35 seconds for quick subset

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | JOBS-01 | T-02-01 | persisted/public job vocabulary stays on product terms while dispatch aliases remain internal | unit | `cd apps/api && uv run pytest -v --tb=short --timeout=60 -o addopts='' tests/unit/test_job_contract.py tests/unit/test_job_dispatch.py tests/unit/test_job_service.py -k 'create_job or dispatch or contract'` | ✅ | ⬜ pending |
| 02-02-01 | 02 | 2 | JOBS-02 | T-02-02 | jobs read/filter/cancel surfaces expose only canonical lifecycle values after backfill | unit/integration | `cd apps/api && uv run pytest -v --tb=short --timeout=60 -o addopts='' tests/unit/test_job_service.py tests/integration/test_jobs_v2_router_additional.py tests/integration/test_api_endpoints.py -k 'jobs_v2 or cancel_job or get_job_detail or list_jobs'` | ✅ | ⬜ pending |
| 02-03-01 | 03 | 3 | JOBS-01, JOBS-02 | T-02-03 | async collection submission, task updates, and job follow-up reads stay on `batch` plus canonical lifecycle vocabulary | unit/integration | `cd apps/api && uv run pytest -v --tb=short --timeout=60 -o addopts='' tests/unit/test_async_tasks.py tests/unit/test_job_service.py tests/integration/test_api_endpoints.py -k 'async_collect or batch_collect or get_job_detail or statistics'` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] Existing pytest infrastructure, database fixtures, and authenticated client fixtures already cover this phase.
- [x] No new framework install or watch-mode harness is needed.
- [x] Migration manifest infrastructure already exists if a targeted `006_*` backfill migration is added during execution.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 35s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** ready
