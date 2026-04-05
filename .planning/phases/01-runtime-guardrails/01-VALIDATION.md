---
phase: 01
slug: runtime-guardrails
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| **Quick run command** | `cd apps/api && uv run pytest -q tests/unit/test_health_detailed_branches.py tests/unit/test_health_dynamic.py tests/unit/test_middleware_logging.py tests/unit/test_logging_redaction.py tests/unit/test_auth_deps.py` |
| **Full suite command** | `cd apps/api && uv run pytest -q` |
| **Estimated runtime** | ~30 seconds quick subset / full suite longer but required before verify |

---

## Sampling Rate

- **After every task commit:** Run the smallest targeted pytest subset for the touched area
- **After every plan wave:** Run `cd apps/api && uv run pytest -q tests/unit/test_health_detailed_branches.py tests/unit/test_health_dynamic.py tests/unit/test_middleware_logging.py tests/unit/test_logging_redaction.py tests/unit/test_auth_deps.py tests/unit/test_auth.py tests/unit/test_auth_extended.py tests/unit/test_auth_resource_access.py tests/integration/test_policy_accounting.py`
- **Before `/gsd-verify-work`:** Full suite must be green via `cd apps/api && uv run pytest -q`
- **Max feedback latency:** 30 seconds for quick subset

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 01-01-01 | 01 | 1 | HEALTH-01 | — | degraded health reports Redis issues without 500 | unit/integration | `cd apps/api && uv run pytest -q tests/unit/test_health_detailed_branches.py tests/unit/test_health_dynamic.py tests/integration/test_api_endpoints.py` | ✅ | ⬜ pending |
| 01-02-01 | 02 | 1 | HEALTH-02 | — | canonical logging path redacts sensitive fields and propagates request id | unit | `cd apps/api && uv run pytest -q tests/unit/test_middleware_logging.py tests/unit/test_logging_redaction.py tests/unit/test_logging_middleware_post_body.py tests/unit/test_logging_middleware_error.py` | ✅ | ⬜ pending |
| 01-03-01 | 03 | 2 | HEALTH-03 | — | auth/policy boundary stays principal-first and accounting still persists request metadata | unit/integration | `cd apps/api && uv run pytest -q tests/unit/test_auth_deps.py tests/unit/test_auth.py tests/unit/test_auth_extended.py tests/unit/test_auth_resource_access.py tests/integration/test_policy_accounting.py` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Inspect structured logs for canonical event names and stable `X-Request-ID` propagation | HEALTH-02 | automated tests can prove headers and redaction but not the operator-facing log stream quality alone | Run API locally, hit `/api/v2/jobs/` with an authenticated request, verify `request_started` and `request_completed` share the same request id and redacted fields |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
