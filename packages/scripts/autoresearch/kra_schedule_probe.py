"""Optionally gate regional schedule reads without modifying the pinned collector."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import httpx
from shared.kra_race_identity import validate_race_identity
from shared.kra_schedule import SOURCE_URLS, parse_schedule_html

from autoresearch.kra_schedule_snapshot import (
    MAX_SOURCE_BYTES,
    _json_bytes,
    _write_new,
    collect_schedule_snapshot,
)

HTTP_STOP = {401: "authentication_required", 403: "access_denied", 429: "rate_limited"}
_SOURCE_NAMES = {url: source for source, url in SOURCE_URLS.items()}
_UNVERIFIED = "unverified_national_response"


class _FirstDateStream:
    """Wrap the one streaming method used on the collector's injected client."""

    def __init__(self, client: httpx.AsyncClient, race_date: str):
        self.client = client
        self.race_date = race_date
        self.national_status = _UNVERIFIED
        self.regional_stop: str | None = None
        self.observations: dict[str, dict[str, Any]] = {}

    async def _observe_national(self, response: httpx.Response) -> httpx.Response:
        if response.status_code != 200:
            self.national_status = HTTP_STOP.get(response.status_code, "http_error")
            return response
        if (
            str(response.url) != SOURCE_URLS["national"]
            or response.headers.get("content-type", "").split(";")[0].lower()
            != "text/html"
        ):
            return response
        raw = bytearray()
        async for chunk in response.aiter_bytes():
            raw.extend(chunk)
            if len(raw) > MAX_SOURCE_BYTES:
                raise ValueError("schedule_response_too_large")
        payload = bytes(raw)
        if not payload.strip():
            self.national_status = "empty_national_response"
        else:
            try:
                races = parse_schedule_html(
                    payload,
                    source_id="national",
                    encoding=response.encoding or "euc-kr",
                )
            except (ValueError, LookupError):
                self.national_status = "invalid_national_card"
            else:
                self.national_status = (
                    "national_date_seen"
                    if any(row.race_date == self.race_date for row in races)
                    else "date_not_in_national_card"
                )

        # The body is already decoded by httpx, so the collector can read it
        # from memory without following a second network request or decoding twice.
        headers = httpx.Headers(response.headers)
        headers.pop("content-encoding", None)
        headers.pop("content-length", None)
        relayed = httpx.Response(
            200, headers=headers, content=payload, request=response.request
        )
        relayed.encoding = response.encoding or "euc-kr"
        return relayed

    @asynccontextmanager
    async def stream(
        self, method: str, url: str, *, follow_redirects: bool
    ) -> AsyncIterator[httpx.Response]:
        source = _SOURCE_NAMES.get(url)
        if (
            method != "GET"
            or follow_redirects
            or source is None
            or source in self.observations
            or source != list(SOURCE_URLS)[len(self.observations)]
        ):
            raise ValueError("unexpected_schedule_probe_request")
        observation: dict[str, Any] = {"status": "attempted"}
        self.observations[source] = observation
        if source != "national":
            stop = self.regional_stop
            if self.national_status != "national_date_seen":
                stop = self.national_status
            if stop is not None:
                observation.update(status="not_attempted", skip_reason=stop)
                raise ValueError("schedule_source_skipped_by_first_date_probe")
        async with self.client.stream(method, url, follow_redirects=False) as response:
            observation["http_status"] = response.status_code
            if source == "national":
                yield await self._observe_national(response)
            else:
                self.regional_stop = HTTP_STOP.get(response.status_code)
                yield response


async def collect_first_date_probe(
    *,
    race_date: str,
    output_dir: Path,
    client: httpx.AsyncClient | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> Path:
    """Return the probe receipt alongside the original v1 capture manifest."""
    validate_race_identity(1, race_date, 1)
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=30, follow_redirects=False)
    gate = _FirstDateStream(client, race_date)
    try:
        capture = await collect_schedule_snapshot(
            output_dir=output_dir, client=cast(httpx.AsyncClient, gate), clock=clock
        )
    finally:
        if owns_client:
            await client.aclose()

    raw = capture.read_bytes()
    manifest = json.loads(raw)
    national = manifest["sources"]["national"]
    status = gate.national_status
    if manifest.get("error"):
        status = "unverified_capture_clock"
    elif national.get("error") == "schedule_http_failure":
        status = "transport_failure"
    elif national["status"] != "captured" and status == "national_date_seen":
        status = _UNVERIFIED
    observations = {}
    for source in SOURCE_URLS:
        observed = gate.observations.get(
            source,
            {"status": "not_attempted", "skip_reason": "collector_did_not_attempt"},
        )
        if observed.get("skip_reason") == _UNVERIFIED:
            observed = {**observed, "skip_reason": status}
        observations[source] = observed
    receipt = capture.with_name("first_date_probe.json")
    _write_new(
        receipt,
        _json_bytes(
            {
                "format_version": "kra-schedule-first-date-probe-v1",
                "race_date": race_date,
                "status": status,
                "capture": {
                    "path": capture.name,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                },
                "sources": observations,
            }
        ),
    )
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--race-date", metavar="YYYYMMDD", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    receipt = asyncio.run(
        collect_first_date_probe(race_date=args.race_date, output_dir=args.output_dir)
    )
    data = json.loads(receipt.read_bytes())
    print(
        json.dumps(
            {
                "capture": str(receipt.with_name(data["capture"]["path"])),
                "probe": str(receipt),
                "national_status": data["status"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
