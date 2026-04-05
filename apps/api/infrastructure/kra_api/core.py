"""
Shared KRA transport and policy primitives.
"""

import asyncio
import email.utils
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from urllib.parse import unquote

import httpx
import structlog

logger = structlog.get_logger()


@dataclass(frozen=True, slots=True)
class KRARequestPolicy:
    base_url: str
    api_key: str | None
    timeout: int | float
    max_retries: int
    verify_ssl: bool
    user_agent: str | None = None


CACHE_TTLS: dict[str, int] = {
    "race_info": 3600,
    "horse_info": 86400,
    "jockey_info": 86400,
    "trainer_info": 86400,
    "track_info": 3600,
    "race_plan": 86400,
    "cancelled_horses": 1800,
    "jockey_stats": 86400,
    "owner_info": 86400,
    "training_status": 21600,
}


class KRAApiRequestError(Exception):
    """Base transport error for KRA requests."""


class KRAApiRetryableRequestError(KRAApiRequestError):
    """Transport failure that may be retried by callers."""


class KRAApiAuthenticationError(KRAApiRequestError):
    """Raised when the KRA API rejects the credential."""


class KRAApiRateLimitError(KRAApiRequestError):
    """Raised when the KRA API rate limit is exhausted."""


def build_httpx_client_kwargs(policy: KRARequestPolicy) -> dict[str, Any]:
    headers = {"Accept": "application/json"}
    if policy.user_agent:
        headers["User-Agent"] = policy.user_agent

    return {
        "timeout": httpx.Timeout(policy.timeout),
        "verify": policy.verify_ssl,
        "follow_redirects": True,
        "limits": httpx.Limits(max_keepalive_connections=5, max_connections=10),
        "http2": False,
        "headers": headers,
    }


def build_request_params(
    params: dict[str, Any] | None, api_key: str | None, *, include_json_type: bool = True
) -> dict[str, Any]:
    request_params = dict(params or {})
    if api_key:
        request_params["serviceKey"] = unquote(api_key)
    if include_json_type:
        request_params["_type"] = "json"
    return request_params


def cache_ttl_for(namespace: str) -> int:
    try:
        return CACHE_TTLS[namespace]
    except KeyError as exc:
        raise KeyError(f"Unknown cache namespace: {namespace}") from exc


def log_rate_limit_headers(response: httpx.Response) -> None:
    headers = getattr(response, "headers", None)
    if headers is None:
        return

    request = getattr(response, "request", None)
    rate_limit_headers = {
        "rate_limit_limit": headers.get("X-RateLimit-Limit"),
        "rate_limit_remaining": headers.get("X-RateLimit-Remaining"),
        "rate_limit_reset": headers.get("X-RateLimit-Reset"),
        "retry_after": headers.get("Retry-After"),
    }
    rate_limit_headers = {
        key: value for key, value in rate_limit_headers.items() if value is not None
    }
    if rate_limit_headers:
        logger.info(
            "KRA API rate limit headers",
            url=str(request.url) if request is not None else None,
            **rate_limit_headers,
        )


def _retry_delay(attempt: int, response: httpx.Response | None = None) -> float:
    if response is not None and response.status_code == 429:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(0.0, float(retry_after))
            except ValueError:
                retry_at = email.utils.parsedate_to_datetime(retry_after)
                if retry_at is not None:
                    if retry_at.tzinfo is None:
                        retry_at = retry_at.replace(tzinfo=UTC)
                    return max(0.0, (retry_at - datetime.now(UTC)).total_seconds())

    return float(2**attempt)


async def request_json_with_retry(
    client: httpx.AsyncClient,
    policy: KRARequestPolicy,
    endpoint: str,
    *,
    method: str = "GET",
    params: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"{policy.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    request_params = build_request_params(params, policy.api_key)

    for attempt in range(policy.max_retries):
        try:
            response = await client.request(
                method=method, url=url, params=request_params, json=data
            )
            log_rate_limit_headers(response)
            response.raise_for_status()

            try:
                result = response.json()
            except ValueError as exc:
                logger.warning(
                    "KRA API response JSON decode failed",
                    endpoint=endpoint,
                    attempt=attempt + 1,
                    error=str(exc),
                )
                if attempt < policy.max_retries - 1:
                    await asyncio.sleep(_retry_delay(attempt))
                    continue
                raise KRAApiRetryableRequestError("Invalid JSON response") from exc

            if result.get("status") == "error":
                message = result.get("message", "Unknown error")
                logger.warning(
                    "KRA API logical error",
                    endpoint=endpoint,
                    attempt=attempt + 1,
                    message=message,
                )
                if attempt < policy.max_retries - 1:
                    await asyncio.sleep(_retry_delay(attempt))
                    continue
                raise KRAApiRetryableRequestError(f"KRA API error: {message}")

            return result

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            logger.warning(
                "KRA API request failed",
                endpoint=endpoint,
                attempt=attempt + 1,
                status_code=status_code,
                error=str(e),
            )

            if status_code in {401, 403}:
                raise KRAApiAuthenticationError(
                    f"KRA API authentication failed with status {status_code}"
                ) from e

            should_retry = status_code == 429 or 500 <= status_code < 600
            if not should_retry:
                raise KRAApiRequestError(
                    f"HTTP {status_code}: {e.response.text[:200]}"
                ) from e

            if attempt < policy.max_retries - 1:
                await asyncio.sleep(_retry_delay(attempt, response=e.response))
                continue

            if status_code == 429:
                raise KRAApiRateLimitError(
                    "KRA API rate limit exceeded after retries"
                ) from e
            raise KRAApiRetryableRequestError(
                f"HTTP {status_code}: {e.response.text[:200]}"
            ) from e

        except httpx.HTTPError as e:
            logger.warning(
                "KRA API request failed",
                endpoint=endpoint,
                attempt=attempt + 1,
                error=str(e),
            )

            if attempt < policy.max_retries - 1:
                await asyncio.sleep(_retry_delay(attempt))
                continue

            raise KRAApiRetryableRequestError(f"Connection error: {str(e)}") from e

    raise KRAApiRequestError("All retries exhausted")
