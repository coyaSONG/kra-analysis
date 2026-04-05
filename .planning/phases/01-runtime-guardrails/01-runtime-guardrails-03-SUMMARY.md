# Plan 03 Summary

- auth helper public contract를 `AuthenticatedPrincipal` 중심으로 정리하고, permission/resource-access 경계가 principal-first로 동작하도록 맞췄다.
- direct-call compatibility가 필요한 legacy helper/tests는 `api_key_obj` 경로를 유지하되, FastAPI runtime path는 principal-first를 유지하도록 호환 계층을 추가했다.
- `test_policy_accounting.py`에 integration marker와 request-id persistence 검증을 추가했다.

## Verification

- `cd apps/api && uv run pytest -q tests/unit/test_auth_deps.py tests/unit/test_auth_extended.py tests/unit/test_auth_resource_access.py tests/integration/test_policy_accounting.py -o addopts=''`
- `cd apps/api && uv run pytest -q -m integration tests/integration/test_policy_accounting.py -o addopts=''`

## Result

- PASS
