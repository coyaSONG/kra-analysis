"""Preserve complete API26 pages without persisting credential-bearing URLs."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote
from uuid import uuid4

import httpx
from shared.kra_entry_sheet import (
    SOURCE_ID,
    build_entry_snapshot,
    parse_entry_sheet_page,
)
from shared.kra_race_card_pdf import validate_identity

ENTRY_URL = "https://apis.data.go.kr/B551015/API26_2/entrySheet_2"
PAGE_SIZE = 100
MAX_PAGE_BYTES = 5 * 1024 * 1024


def _timestamp(clock: Callable[[], datetime]) -> datetime:
    value = clock()
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("entry_capture_requires_timezone")
    return value.astimezone(UTC)


async def collect_entry_sheet_snapshot(
    *,
    meet: int,
    race_date: str,
    race_no: int,
    api_key: str,
    output_dir: Path,
    client: httpx.AsyncClient | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict[str, Any]:
    """The entry capture time is completion of every required response page."""
    validate_identity(meet, race_date, race_no)
    key = unquote(api_key.strip())
    if not key:
        raise ValueError("missing_kra_api_key")
    started = _timestamp(clock)
    directory = (
        output_dir
        / f"{race_date}_{meet}_{race_no}"
        / ("entries_" + started.strftime("%Y%m%dT%H%M%S.%fZ") + "_" + uuid4().hex[:12])
    )
    directory.mkdir(parents=True, exist_ok=False)
    path = directory / "entry_capture.json"
    manifest: dict[str, Any] = {
        "source_id": SOURCE_ID,
        "meet": meet,
        "race_date": race_date,
        "race_no": race_no,
        "url": ENTRY_URL,
        "fetch_started_at": started.isoformat(),
        "collected_at": None,
        "collection_status": "fetch_error",
        "pages": [],
        "entry_snapshot": None,
        "manifest_path": str(path),
        "entry_snapshot_path": None,
    }
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=30, follow_redirects=False)
    rows: list[dict[str, Any]] = []
    total = None
    captured = started
    try:
        page_no = 1
        while total is None or len(rows) < total:
            params = {
                "meet": meet,
                "rc_date": race_date,
                "rc_no": race_no,
                "numOfRows": PAGE_SIZE,
                "pageNo": page_no,
                "_type": "json",
            }
            async with client.stream(
                "GET",
                ENTRY_URL,
                params={**params, "serviceKey": key},
                follow_redirects=False,
            ) as response:
                response.raise_for_status()
                if str(response.url.copy_with(query=None)) != ENTRY_URL:
                    raise ValueError("noncanonical_entry_response")
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_PAGE_BYTES:
                        raise ValueError("entry_response_too_large")
            completed = _timestamp(clock)
            if completed < captured:
                raise ValueError("entry_capture_clock_moved_backwards")
            captured = completed
            content = bytes(body)
            if key.encode() in content or api_key.strip().encode() in content:
                raise ValueError("credential_echo_in_entry_response")
            try:
                payload = json.loads(content)
            except (UnicodeError, json.JSONDecodeError) as exc:
                raise ValueError("invalid_entry_json") from exc
            page_rows, page_total = parse_entry_sheet_page(
                payload, page_no=page_no, page_size=PAGE_SIZE
            )
            if total is not None and total != page_total:
                raise ValueError("entry_total_changed_during_capture")
            total = page_total
            digest = hashlib.sha256(content).hexdigest()
            raw_path = directory / f"page_{page_no}_{digest}.json"
            with raw_path.open("xb") as stream:
                stream.write(content)
            manifest["pages"].append(
                {
                    "page_no": page_no,
                    "collected_at": completed.isoformat(),
                    "sha256": digest,
                    "raw_path": str(raw_path),
                    "byte_count": len(content),
                    "row_count": len(page_rows),
                    "request_parameters": params,
                }
            )
            rows.extend(page_rows)
            page_no += 1
        manifest.update(collected_at=captured.isoformat(), total_count=total)
        entries = build_entry_snapshot(
            rows, meet=meet, race_date=race_date, race_no=race_no, collected_at=captured
        )
        entries["source_manifest_path"] = str(path)
        entry_path = directory / "entries.json"
        with entry_path.open("x", encoding="utf-8") as stream:
            json.dump(entries, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
        manifest.update(
            entry_snapshot=entries,
            entry_snapshot_path=str(entry_path),
            collection_status="captured",
        )
    except httpx.HTTPError as exc:
        # HTTP exception strings can contain serviceKey in their request URL.
        manifest.update(error_type=type(exc).__name__, error="entry_http_failure")
    except ValueError as exc:
        manifest.update(
            collection_status="validation_error",
            error_type=type(exc).__name__,
            error=str(exc),
        )
    finally:
        if owns_client:
            await client.aclose()
    with path.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
    return manifest
