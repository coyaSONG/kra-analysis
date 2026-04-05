# Plan 02 Summary

- `RequestLoggingMiddleware`를 canonical request logging 경로로 확장해 request id 생성, request lifecycle event, header/query/body redaction, debug body logging을 한 경로로 통합했다.
- `PolicyAccountingMiddleware`는 request id를 생성하지 않고 canonical logging path를 소비하는 fallback-only 동작으로 정리했다.
- unit logging 테스트와 mounted-app request-id/logging integration coverage를 새 계약에 맞게 갱신했다.

## Verification

- `cd apps/api && uv run pytest -q tests/unit/test_middleware_logging.py tests/unit/test_logging_redaction.py tests/unit/test_logging_middleware_post_body.py tests/unit/test_logging_middleware_error.py tests/integration/test_api_endpoints.py -k 'request_id or logging' -o addopts=''`

## Result

- PASS
