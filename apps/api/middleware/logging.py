"""
로깅 미들웨어
요청/응답 로깅 및 추적
"""

import json
import time
import uuid
from collections.abc import Mapping
from contextvars import ContextVar
from typing import Any

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger()

# 요청 ID 컨텍스트 변수
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
_request_count = 0

_SENSITIVE_FIELD_MARKERS = (
    "apikey",
    "token",
    "password",
    "secret",
    "authorization",
    "servicekey",
)


def _is_sensitive_field(field_name: str) -> bool:
    normalized = "".join(ch for ch in field_name.lower() if ch.isalnum())
    return any(marker in normalized for marker in _SENSITIVE_FIELD_MARKERS)


def _mask_sensitive_value(value: Any) -> Any:
    if value is None:
        return None

    value_str = str(value)
    if not value_str:
        return value_str

    return f"{value_str[:4]}***"


def _mask_sensitive_fields(data: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: _mask_sensitive_value(value) if _is_sensitive_field(key) else value
        for key, value in data.items()
    }


def increment_request_count() -> None:
    global _request_count
    _request_count += 1


def get_request_count() -> int:
    return _request_count


class LoggingMiddleware(BaseHTTPMiddleware):
    """구조화된 로깅 미들웨어"""

    async def dispatch(self, request: Request, call_next):
        # 요청 ID 생성
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)

        # 시작 시간
        start_time = time.time()

        # 요청 정보 추출
        request_info: dict[str, Any] = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": _mask_sensitive_fields(dict(request.query_params)),
            "headers": _mask_sensitive_fields(dict(request.headers)),
            "client_host": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent", ""),
        }

        # API 키 확인 (헤더에서)
        if "x-api-key" in request.headers:
            request_info["has_api_key"] = True

        # 요청 로깅
        logger.info("request_started", **request_info)

        # 에러 처리
        response = None
        error_occurred = False
        error_detail = None

        try:
            # 요청 처리
            response = await call_next(request)

        except Exception as e:
            error_occurred = True
            error_detail = str(e)
            logger.error(
                "request_failed",
                request_id=request_id,
                error=error_detail,
                exc_info=True,
            )
            raise

        finally:
            # 처리 시간 계산
            duration = time.time() - start_time

            # 응답 로깅
            if response:
                logger.info(
                    "request_completed",
                    request_id=request_id,
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    duration_ms=round(duration * 1000, 2),
                    error=error_occurred,
                )

                # 응답 헤더에 요청 ID 추가
                response.headers["X-Request-ID"] = request_id

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """상세 요청/응답 로깅 미들웨어"""

    async def dispatch(self, request: Request, call_next):
        increment_request_count()

        # 요청 바디 읽기 (주의: 메모리 사용)
        request_body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                request_body = await request.body()

                # 바디를 다시 읽을 수 있도록 설정
                async def receive():
                    return {"type": "http.request", "body": request_body}

                request._receive = receive
            except Exception:
                pass

        # 요청 상세 로깅
        if request_body and len(request_body) < 10000:  # 10KB 제한
            try:
                body_json = json.loads(request_body)
                logger.debug("request_body", path=request.url.path, body=body_json)
            except Exception:
                logger.debug(
                    "request_body_raw",
                    path=request.url.path,
                    body_length=len(request_body),
                )

        # 응답 처리
        response = await call_next(request)

        return response
