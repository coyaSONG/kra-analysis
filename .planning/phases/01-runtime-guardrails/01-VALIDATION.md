---
phase: 01
slug: runtime-guardrails
status: ready
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-05
---

# Phase 01 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio + pytest-cov |
| **Config file** | `apps/api/pytest.ini`, `apps/api/.coveragerc` |
| **Quick run command** | `cd apps/api && uv run pytest -v --tb=short --timeout=60 -o addopts='' tests/unit/test_health_detailed_branches.py tests/unit/test_health_dynamic.py tests/unit/test_middleware_logging.py tests/unit/test_logging_redaction.py tests/unit/test_auth_deps.py` |
| **Full suite command** | `pnpm -F @apps/api test` |
| **Estimated runtime** | ~30 seconds quick subset / full suite longer but required before verify |

---

## Sampling Rate

- **After every task commit:** Run the smallest targeted pytest subset for the touched area with `-o addopts=''`
- **After every plan wave:** Run `bash apps/api/scripts/run_quality_ci.sh unit` and the explicit focused integration files needed for health and policy accounting
- **Before `/gsd-verify-work`:** Full suite must be green via `pnpm -F @apps/api test`, then run `bash apps/api/scripts/run_quality_ci.sh integration`
- **Max feedback latency:** 30 seconds for quick subset

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | HEALTH-01 | — | degraded health reports Redis issues without 500 | unit/integration | `cd apps/api && uv run pytest -v --tb=short --timeout=60 -o addopts='' tests/unit/test_health_detailed_branches.py tests/unit/test_health_dynamic.py tests/integration/test_api_endpoints.py -k 'health'` | ✅ | ⬜ pending |
| 01-02-01 | 02 | 1 | HEALTH-02 | — | canonical logging path redacts sensitive fields and propagates request id | unit/integration | `cd apps/api && uv run pytest -v --tb=short --timeout=60 -o addopts='' tests/unit/test_middleware_logging.py tests/unit/test_logging_redaction.py tests/unit/test_logging_middleware_post_body.py tests/unit/test_logging_middleware_error.py tests/integration/test_api_endpoints.py -k 'request_id or logging'` | ✅ | ⬜ pending |
| 01-03-01 | 03 | 1 | HEALTH-03 | — | auth/policy boundary stays principal-first and accounting still persists request metadata | unit/integration | `cd apps/api && uv run pytest -v --tb=short --timeout=60 -o addopts='' tests/unit/test_auth_deps.py tests/unit/test_auth.py tests/unit/test_auth_extended.py tests/unit/test_auth_resource_access.py tests/integration/test_policy_accounting.py` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/integration/test_api_endpoints.py` degraded-Redis contract case is absorbed into `01-01-PLAN.md`.
- [x] Logging tests moving to the canonical runtime path are absorbed into `01-02-PLAN.md`.
- [x] Small JSON body redaction coverage is absorbed into `01-02-PLAN.md`.
- [x] `tests/integration/test_policy_accounting.py` integration marker and request-id correlation assertions are absorbed into `01-03-PLAN.md`.
- [x] `tests/unit/test_auth_deps.py` direct `require_action()` request-state coverage is absorbed into `01-03-PLAN.md`.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Inspect structured logs for canonical event names and stable `X-Request-ID` propagation | HEALTH-02 | automated tests can prove headers and redaction but not the operator-facing log stream quality alone | Run API locally, hit `/api/v2/jobs/` with an authenticated request, verify `request_started` and `request_completed` share the same request id and redacted fields |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** ready
