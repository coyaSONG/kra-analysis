---
status: complete
phase: 01-runtime-guardrails
source:
  - 01-runtime-guardrails-01-SUMMARY.md
  - 01-runtime-guardrails-02-SUMMARY.md
  - 01-runtime-guardrails-03-SUMMARY.md
started: 2026-04-05T06:00:56Z
updated: 2026-04-05T06:08:42Z
---

## Current Test

[testing complete]

## Tests

### 1. Detailed Health Reports Explicit Redis Degradation
expected: |
  `/health/detailed` 호출 시 Redis가 없거나 깨져 있어도 HTTP 200을 유지하고,
  flat `redis` 필드가 `unavailable` 또는 `error`로 원인을 구분해 보여야 한다.
result: pass
evidence:
  - `cd apps/api && uv run pytest -q tests/unit/test_health_detailed_branches.py tests/unit/test_health_dynamic.py tests/integration/test_api_endpoints.py -k 'health' -o addopts=''`
  - `bash apps/api/scripts/run_quality_ci.sh integration`

### 2. Canonical Logging Path Propagates One Request ID
expected: |
  mounted app 기준으로 하나의 request logging 경로가 `request_started` / `request_completed`
  이벤트를 같은 request id로 남기고, 응답 헤더의 `X-Request-ID`도 일관되게 전파해야 한다.
result: pass
evidence:
  - `cd apps/api && uv run pytest -q tests/unit/test_middleware_logging.py tests/unit/test_logging_redaction.py tests/unit/test_logging_middleware_post_body.py tests/unit/test_logging_middleware_error.py tests/integration/test_api_endpoints.py -k 'request_id or logging' -o addopts=''`
  - `bash apps/api/scripts/run_quality_ci.sh integration`

### 3. Principal-First Auth Contract Persists Usage Accounting
expected: |
  보호된 경로가 `AuthenticatedPrincipal` 기준으로 동작하고,
  usage event가 request id와 함께 append-only로 저장되어야 한다.
result: pass
evidence:
  - `cd apps/api && uv run pytest -q tests/unit/test_auth_deps.py tests/unit/test_auth.py tests/unit/test_auth_extended.py tests/unit/test_auth_resource_access.py tests/integration/test_policy_accounting.py -o addopts=''`
  - `cd apps/api && uv run pytest -q -m integration tests/integration/test_policy_accounting.py -o addopts=''`
  - `bash apps/api/scripts/run_quality_ci.sh integration`
  - `cd apps/api && uv run pytest -q`

## Summary

total: 3
passed: 3
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

none

## External Blockers

none
