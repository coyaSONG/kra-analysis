"""Capture immutable local observations of official KRA race-card PDFs."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.kra_race_card_pdf import (
    MAX_PDF_BYTES,
    SOURCE_ID,
    parse_race_card_pdf,
    race_card_url,
)
from shared.kra_race_card_pdf_audit import audit_race_card_snapshot

from autoresearch.kra_entry_sheet_snapshot import collect_entry_sheet_snapshot

SNAPSHOT_VERSION = "kra-race-card-pdf-snapshot-v1"
DEFAULT_OUTPUT_DIR = Path(".cache/autoresearch/race_card_pdf_snapshots")


def _now() -> datetime:
    return datetime.now(UTC)


def _timestamp(clock: Callable[[], datetime]) -> datetime:
    value = clock()
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("capture clock must return timezone-aware timestamps")
    return value.astimezone(UTC)


async def collect_race_card_pdf(
    *,
    meet: int,
    race_date: str,
    race_no: int,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    entries: dict[str, Any] | None = None,
    scheduled_start_time: str | None = None,
    client: httpx.AsyncClient | None = None,
    clock: Callable[[], datetime] = _now,
) -> dict[str, Any]:
    """Each attempt gets its own manifest; no caller-supplied backdating CLI."""
    url = race_card_url(meet, race_date, race_no)
    started = _timestamp(clock)
    race_id = f"{race_date}_{meet}_{race_no}"
    snapshot_id = started.strftime("%Y%m%dT%H%M%S.%fZ") + "_" + uuid4().hex[:12]
    directory = output_dir / race_id / snapshot_id
    directory.mkdir(parents=True, exist_ok=False)
    manifest: dict[str, Any] = {
        "snapshot_version": SNAPSHOT_VERSION,
        "source_id": SOURCE_ID,
        "race_id": race_id,
        "meet": meet,
        "race_date": race_date,
        "race_no": race_no,
        "snapshot_id": snapshot_id,
        "url": url,
        "fetch_started_at": started.isoformat(),
        "collected_at": None,
        "collection_status": "fetch_error",
        "http_status": None,
        "headers": {},
        "raw_path": None,
        "sha256": None,
        "byte_count": 0,
        "timing_evidence": "local_capture_completion_not_server_headers",
        "eligible_for_prerace_features": False,
        "parsed": None,
        "audit": None,
        "scheduled_start_time": scheduled_start_time,
        "entry_snapshot": {
            **{
                key: entries.get(key)
                for key in (
                    "meet",
                    "race_date",
                    "race_no",
                    "collected_at",
                    "scheduled_start_time",
                    "source_id",
                    "source_manifest_path",
                )
            },
            "entries": [
                {key: entry.get(key) for key in ("chulNo", "hrName", "hrNo")}
                if isinstance(entry, dict)
                else None
                for entry in entries.get("entries", [])
            ]
            if isinstance(entries.get("entries"), list)
            else None,
        }
        if isinstance(entries, dict)
        else None,
    }
    owns_client = client is None
    client = client or httpx.AsyncClient(
        timeout=30,
        follow_redirects=False,
        headers={"User-Agent": "kra-analysis/1.0 (prerace PDF research snapshot)"},
    )
    try:
        async with client.stream("GET", url, follow_redirects=False) as response:
            manifest["http_status"] = response.status_code
            manifest["final_url"] = str(response.url)
            manifest["headers"] = {
                key: response.headers[key]
                for key in (
                    "date",
                    "last-modified",
                    "etag",
                    "content-type",
                    "content-length",
                )
                if key in response.headers
            }
            response.raise_for_status()
            content_type = (
                response.headers.get("content-type", "").split(";")[0].strip().lower()
            )
            if content_type != "application/pdf" or str(response.url) != url:
                raise ValueError("non_pdf_or_noncanonical_response")
            body = bytearray()
            async for chunk in response.aiter_bytes():
                body.extend(chunk)
                if len(body) > MAX_PDF_BYTES:
                    raise ValueError("response_too_large")
        captured = _timestamp(clock)
        if captured < started:
            raise ValueError("capture_clock_moved_backwards")
        content = bytes(body)
        if not content.startswith(b"%PDF-"):
            raise ValueError("response_not_pdf_bytes")
        manifest.update(
            collected_at=captured.isoformat(),
            sha256=hashlib.sha256(content).hexdigest(),
            byte_count=len(content),
            collection_status="captured",
        )
        raw_path = directory / f"source_{manifest['sha256']}.pdf"
        with raw_path.open("xb") as stream:
            stream.write(content)
        manifest["raw_path"] = str(raw_path)
        try:
            parsed = parse_race_card_pdf(
                content, meet=meet, race_date=race_date, race_no=race_no
            )
            audit = audit_race_card_snapshot(
                parsed,
                collected_at=captured,
                scheduled_start_time=scheduled_start_time,
                entries=entries,
            )
            manifest.update(
                parsed=parsed,
                audit=audit,
                eligible_for_prerace_features=audit["eligible_for_prerace_features"],
            )
        except Exception as exc:
            manifest.update(
                collection_status="parse_error",
                error_type=type(exc).__name__,
                error=str(exc)[:500],
            )
    except (httpx.HTTPError, ValueError) as exc:
        manifest.update(error_type=type(exc).__name__, error=str(exc)[:500])
    finally:
        if owns_client:
            await client.aclose()
    manifest["attempt_finished_at"] = _timestamp(clock).isoformat()
    manifest_path = directory / "snapshot.json"
    manifest["manifest_path"] = str(manifest_path)
    with manifest_path.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--meet", type=int, required=True, choices=(1, 2, 3))
    parser.add_argument("--race-date", required=True)
    parser.add_argument("--race-no", type=int, required=True)
    parser.add_argument(
        "--scheduled-start-time", help="HHMM from a pre-race schedule snapshot"
    )
    entry_options = parser.add_mutually_exclusive_group()
    entry_options.add_argument(
        "--entries", type=Path, help="Race identity, collected_at, and entries JSON"
    )
    entry_options.add_argument(
        "--fetch-entries",
        action="store_true",
        help="Capture the complete API26 entry sheet",
    )
    parser.add_argument("--api-key-file", type=Path)
    parser.add_argument("--require-eligible", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    if args.fetch_entries:
        key_file = args.api_key_file or Path.home() / ".codex/secrets/kra_api_key"
        key = os.environ.get("KRA_API_KEY") or (
            key_file.read_text(encoding="utf-8").strip() if key_file.is_file() else ""
        )
        if not key:
            parser.error("--fetch-entries requires KRA_API_KEY or --api-key-file")
        entry_capture = asyncio.run(
            collect_entry_sheet_snapshot(
                meet=args.meet,
                race_date=args.race_date,
                race_no=args.race_no,
                api_key=key,
                output_dir=args.output_dir,
            )
        )
        entries = entry_capture["entry_snapshot"]
    else:
        entry_capture = None
        entries = (
            json.loads(args.entries.read_text(encoding="utf-8"))
            if args.entries
            else None
        )
    schedule = args.scheduled_start_time or (
        entries.get("scheduled_start_time") if isinstance(entries, dict) else None
    )
    result = asyncio.run(
        collect_race_card_pdf(
            meet=args.meet,
            race_date=args.race_date,
            race_no=args.race_no,
            output_dir=args.output_dir,
            entries=entries,
            scheduled_start_time=schedule,
        )
    )
    parsed, audit = result.get("parsed") or {}, result.get("audit") or {}
    print(
        json.dumps(
            {
                "race_id": result["race_id"],
                "manifest_path": result["manifest_path"],
                "collection_status": result["collection_status"],
                "collected_at": result["collected_at"],
                "sha256": result["sha256"],
                "horse_count": parsed.get("horse_count", 0),
                "parser_status": parsed.get("parser_status"),
                "parser_issues": parsed.get("issues", []),
                "pdf_start_time": parsed.get("scheduled_start_time_from_pdf"),
                "eligible_for_prerace_features": result[
                    "eligible_for_prerace_features"
                ],
                "audit_reasons": audit.get("reasons", []),
                "error": result.get("error"),
                "entry_capture_manifest": entry_capture["manifest_path"]
                if entry_capture
                else None,
                "entry_capture_error": entry_capture.get("error")
                if entry_capture
                else None,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    if (
        result["collection_status"] != "captured"
        or parsed.get("parser_status") != "parsed"
    ):
        return 1
    return (
        2
        if args.require_eligible and not result["eligible_for_prerace_features"]
        else 0
    )


if __name__ == "__main__":
    raise SystemExit(main())
