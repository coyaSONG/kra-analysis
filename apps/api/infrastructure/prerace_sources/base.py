"""No-auth KRA prerace source connector primitives."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

import httpx

SourceContentKind = Literal["html", "pdf", "text", "binary"]
SourceMethod = Literal["GET", "POST"]
SourceTier = Literal["hard_required", "soft_required", "supporting"]
SourceRequest = tuple[SourceMethod, str, dict[str, str] | None, dict[str, str] | None]

_DEFAULT_TIMEOUT = 20.0
_DEFAULT_RETRIES = 3


class PublicSourceFetchError(RuntimeError):
    """Raised when a public source cannot be fetched successfully."""


@dataclass(frozen=True, slots=True)
class PublicSourceSpec:
    source_id: str
    name: str
    host: str
    path: str
    method: SourceMethod = "GET"
    content_kind: SourceContentKind = "html"
    description: str = ""
    operational_tier: SourceTier = "supporting"
    update_hint: str = ""
    requires_auth: bool = False
    supported_meets: tuple[int, ...] = (1, 2, 3)
    default_query: dict[str, str] = field(default_factory=dict)

    @property
    def url(self) -> str:
        return f"{self.host.rstrip('/')}/{self.path.lstrip('/')}"


@dataclass(frozen=True, slots=True)
class RawSourceResponse:
    spec: PublicSourceSpec
    requested_url: str
    status_code: int
    headers: dict[str, str]
    body: bytes
    fetched_at: str
    encoding: str

    @property
    def text(self) -> str:
        return self.body.decode(self.encoding, errors="replace")


def infer_response_encoding(
    headers: dict[str, str] | httpx.Headers,
    body: bytes,
) -> str:
    content_type = headers.get("content-type", "")
    lower = content_type.lower()
    if "charset=" in lower:
        return lower.split("charset=", 1)[1].split(";", 1)[0].strip()

    sniff = body[:512].lower()
    if b"euc-kr" in sniff or b"ks_c_5601" in sniff:
        return "euc-kr"

    try:
        body.decode("utf-8")
    except UnicodeDecodeError:
        return "euc-kr"
    return "utf-8"


def validate_meet(meet: int) -> str:
    if meet not in {1, 2, 3}:
        raise ValueError(f"Unsupported KRA meet: {meet}")
    return str(meet)


class BasePublicSourceConnector:
    """Shared retrying fetcher for public KRA web sources."""

    spec: PublicSourceSpec

    def __init__(
        self,
        *,
        client: httpx.AsyncClient | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        max_retries: int = _DEFAULT_RETRIES,
    ) -> None:
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            follow_redirects=True,
            headers={
                "User-Agent": "kra-analysis-prerace-source/1.0",
                "Accept": "*/*",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            },
        )
        self._max_retries = max_retries

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def __aenter__(self) -> BasePublicSourceConnector:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    def build_request(
        self,
        **kwargs: Any,
    ) -> SourceRequest:
        raise NotImplementedError

    async def fetch_raw(self, **kwargs: Any) -> RawSourceResponse:
        method, url, params, data = self.build_request(**kwargs)
        last_error: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                response = await self._client.request(
                    method=method,
                    url=url,
                    params=params,
                    data=data,
                )
                if response.status_code >= 500:
                    raise PublicSourceFetchError(
                        f"{self.spec.source_id} returned HTTP {response.status_code}"
                    )
                if response.status_code >= 400:
                    raise PublicSourceFetchError(
                        f"{self.spec.source_id} returned HTTP {response.status_code}"
                    )

                headers = {
                    key.lower(): value for key, value in response.headers.items()
                }
                encoding = infer_response_encoding(headers, response.content)
                return RawSourceResponse(
                    spec=self.spec,
                    requested_url=str(response.request.url),
                    status_code=response.status_code,
                    headers=headers,
                    body=response.content,
                    fetched_at=datetime.now(UTC).isoformat(),
                    encoding=encoding,
                )
            except (httpx.HTTPError, PublicSourceFetchError) as exc:
                last_error = exc
                if attempt == self._max_retries:
                    break
                await asyncio.sleep(min(2 ** (attempt - 1), 4))

        raise PublicSourceFetchError(
            f"Failed to fetch {self.spec.source_id}"
        ) from last_error
