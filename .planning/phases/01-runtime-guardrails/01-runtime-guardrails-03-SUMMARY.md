# Plan 03 Summary

- auth helper public contract를 `AuthenticatedPrincipal` 중심으로 정리하고, permission/resource-access helper도 principal-only surface로 맞췄다.
- `APIKey`는 lookup/update 내부 seam에만 남기고, public helper는 principal coercion을 거쳐 하나의 caller contract로 수렴시켰다.
- `test_policy_accounting.py`에 integration marker와 request-id persistence 검증을 추가했다.

## Verification

- `cd apps/api && uv run pytest -q tests/unit/test_auth_deps.py tests/unit/test_auth.py tests/unit/test_auth_extended.py tests/unit/test_auth_resource_access.py tests/integration/test_policy_accounting.py -o addopts=''`
- `cd apps/api && uv run pytest -q -m integration tests/integration/test_policy_accounting.py -o addopts=''`

## Result

- PASS
