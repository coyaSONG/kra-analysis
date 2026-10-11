"""Capture and replay complete API214 venue/day pages with safe provenance."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote
from uuid import uuid4

import httpx
from shared.kra_entry_sheet import parse_entry_sheet_page
from shared.kra_race_identity import validate_race_identity
from shared.kra_result_history import normalize_result_rows

from autoresearch.kra_race_card_pdf_replay import parse_json

RESULT_URL = "https://apis.data.go.kr/B551015/API214_1/RaceDetailResult_1"
FORMAT = "kra-result-day-capture-v1"
PAGE_SIZE = 100
MAX_BYTES = 5 * 1024 * 1024
MAX_CAPTURE_SECONDS = 300
REQUEST_SECONDS = 30


def _utc(value: datetime | str) -> datetime:
    stamp = datetime.fromisoformat(value) if isinstance(value, str) else value
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("result_capture_requires_timezone")
    return stamp.astimezone(UTC)


def _params(meet: int, day: str, page: int) -> dict[str, Any]:
    return {
        "meet": meet,
        "rc_date": day,
        "pageNo": page,
        "numOfRows": PAGE_SIZE,
        "_type": "json",
    }


def _hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


async def collect_result_snapshot(
    *,
    meet: int,
    race_date: str,
    api_key: str,
    output_dir: Path,
    client: httpx.AsyncClient | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> Path:
    validate_race_identity(meet, race_date, 1)
    key = unquote(api_key.strip())
    if not key:
        raise ValueError("missing_kra_api_key")
    started = _utc(clock())
    directory = (
        output_dir
        / f"{race_date}_{meet}_{started.strftime('%Y%m%dT%H%M%S.%fZ')}_{uuid4().hex[:12]}"
    )
    directory.mkdir(parents=True, exist_ok=False)
    manifest: dict[str, Any] = {
        "format_version": FORMAT,
        "url": RESULT_URL,
        "meet": meet,
        "race_date": race_date,
        "fetch_started_at": started.isoformat(),
        "capture_completed_at": None,
        "status": "failed",
        "pages": [],
    }
    owned = client is None
    client = client or httpx.AsyncClient(
        timeout=REQUEST_SECONDS, follow_redirects=False
    )
    rows, total, previous = [], None, started
    try:
        async with asyncio.timeout(MAX_CAPTURE_SECONDS):
            page = 1
            while total is None or len(rows) < total:
                if page > 100:
                    raise ValueError("invalid_result_page_count")
                request_at = _utc(clock())
                if request_at < previous:
                    raise ValueError("result_capture_clock_order")
                async with asyncio.timeout(REQUEST_SECONDS):
                    async with client.stream(
                        "GET",
                        RESULT_URL,
                        params={**_params(meet, race_date, page), "serviceKey": key},
                        follow_redirects=False,
                    ) as response:
                        response.raise_for_status()
                        if str(response.url.copy_with(query=None)) != RESULT_URL:
                            raise ValueError("noncanonical_result_response")
                        body = bytearray()
                        async for chunk in response.aiter_bytes():
                            body.extend(chunk)
                            if len(body) > MAX_BYTES:
                                raise ValueError("result_response_too_large")
                completed = _utc(clock())
                if completed < request_at:
                    raise ValueError("result_capture_clock_order")
                previous = completed
                content = bytes(body)
                if any(
                    secret.encode() in content
                    for secret in (
                        key,
                        api_key.strip(),
                        quote(key, safe=""),
                        json.dumps(key)[1:-1],
                    )
                ):
                    raise ValueError("credential_echo_in_result_response")
                digest = _hash(content)
                filename = f"page_{page}_{digest}.json"
                with (directory / filename).open("xb") as stream:
                    stream.write(content)
                manifest["pages"].append(
                    {
                        "page_no": page,
                        "raw_file": filename,
                        "sha256": digest,
                        "byte_count": len(content),
                        "request_parameters": _params(meet, race_date, page),
                        "fetch_started_at": request_at.isoformat(),
                        "capture_completed_at": completed.isoformat(),
                    }
                )
                # API214 uses the same KRA envelope and pagination contract as API26.
                page_rows, page_total = parse_entry_sheet_page(
                    parse_json(content), page_no=page, page_size=PAGE_SIZE
                )
                if total is not None and page_total != total:
                    raise ValueError("result_total_changed")
                total = page_total
                rows.extend(page_rows)
                page += 1
            projection = normalize_result_rows(rows, meet=meet, race_date=race_date)
            manifest.update(
                status="captured",
                total_count=total,
                summary={k: v for k, v in projection.items() if k != "records"},
            )
    except (httpx.HTTPError, ValueError, UnicodeError, TimeoutError) as exc:
        # Never persist exception strings: request URLs can contain the credential.
        manifest.update(error_type=type(exc).__name__, error="result_capture_failed")
        if type(exc) is ValueError and str(exc) == "missing_result_venue":
            manifest.update(
                status="identity_unresolved",
                error="missing_result_venue",
                total_count=total,
            )
    finally:
        if owned:
            await client.aclose()
    ended = _utc(clock())
    manifest["capture_completed_at"] = ended.isoformat()
    if not previous <= ended or (ended - started).total_seconds() > MAX_CAPTURE_SECONDS:
        manifest.update(status="failed", error="result_capture_clock_window")
    path = directory / "capture.json"
    with path.open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return path


def replay_result_pages(path: Path) -> dict[str, Any]:
    """Verify captured bytes, not event identity; raw rows may lack venue."""
    original = path.read_bytes()
    manifest = parse_json(original)
    if manifest.get("format_version") != FORMAT or manifest.get("url") != RESULT_URL:
        raise ValueError("unsupported_result_capture")
    unresolved_venue = (
        manifest.get("status") == "identity_unresolved"
        and manifest.get("error") == "missing_result_venue"
    )
    if not unresolved_venue and (
        manifest.get("status") != "captured" or manifest.get("error")
    ):
        raise ValueError("result_capture_not_successful")
    meet, day = manifest["meet"], manifest["race_date"]
    validate_race_identity(meet, day, 1)
    start, end = (
        _utc(manifest["fetch_started_at"]),
        _utc(manifest["capture_completed_at"]),
    )
    if not 0 <= (end - start).total_seconds() <= MAX_CAPTURE_SECONDS:
        raise ValueError("result_capture_clock_window")
    pages = manifest["pages"]
    if not isinstance(pages, list) or not 1 <= len(pages) <= 100:
        raise ValueError("invalid_result_page_count")
    rows, total, previous = [], None, start
    pins = []
    for index, page in enumerate(pages, 1):
        if page["page_no"] != index or page["request_parameters"] != _params(
            meet, day, index
        ):
            raise ValueError("result_page_request_mismatch")
        request_at, completed = (
            _utc(page["fetch_started_at"]),
            _utc(page["capture_completed_at"]),
        )
        if not previous <= request_at <= completed <= end:
            raise ValueError("result_page_clock_order")
        previous = completed
        filename = page["raw_file"]
        if (
            filename != f"page_{index}_{page['sha256']}.json"
            or Path(filename).name != filename
        ):
            raise ValueError("invalid_result_raw_path")
        raw_path = path.parent / filename
        if raw_path.is_symlink() or raw_path.stat().st_size > MAX_BYTES:
            raise ValueError("invalid_result_raw_file")
        content = raw_path.read_bytes()
        if (
            type(page["byte_count"]) is not int
            or len(content) != page["byte_count"]
            or _hash(content) != page["sha256"]
        ):
            raise ValueError("result_raw_hash_mismatch")
        current, page_total = parse_entry_sheet_page(
            parse_json(content), page_no=index, page_size=PAGE_SIZE
        )
        if total is not None and page_total != total:
            raise ValueError("result_total_changed")
        total = page_total
        rows.extend(current)
        pins.append({"page_no": index, "sha256": _hash(content)})
    if (
        type(manifest["total_count"]) is not int
        or total != len(rows)
        or total != manifest["total_count"]
        or len(pages) != max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    ):
        raise ValueError("incomplete_result_capture")
    return {
        "manifest": manifest,
        "rows": rows,
        "capture_manifest_sha256": _hash(original),
        "page_pins": pins,
        "event_identity_verified": False,
    }


def replay_result_snapshot(
    path: Path, *, entry_capture: Path | None = None, archive_root: Path | None = None
) -> dict[str, Any]:
    raw = replay_result_pages(path)
    manifest, rows = raw["manifest"], raw["rows"]
    meet, day = manifest["meet"], manifest["race_date"]
    end = _utc(manifest["capture_completed_at"])
    entry_rosters, entry_pins, available_at = None, None, end
    if entry_capture is not None:
        if archive_root is None:
            raise ValueError("result_binding_requires_archive_root")
        # Reuse page provenance checks without claiming an active pre-race roster.
        from autoresearch.kra_race_card_pdf_replay import (
            archive_path,
            replay_entry_pages,
        )

        entry_path = archive_path(str(entry_capture), archive_root=archive_root)
        entry_rows, entry_manifest, evidence = replay_entry_pages(
            entry_path,
            archive_root=archive_root,
            meet=meet,
            race_date=day,
        )
        if not rows:
            raise ValueError("empty_result_cannot_bind_venue")
        # Use the same strict identity checks; no entry-sheet outcome is inferred.
        entry_identity = normalize_result_rows(entry_rows, meet=meet, race_date=day)
        entry_rosters = {}
        for entry in entry_identity["records"]:
            entry_rosters.setdefault(entry["race_id"], []).append(
                {
                    "chulNo": entry["chul_no"],
                    "hrNo": entry["horse_id"],
                }
            )
        entry_pins = [evidence]
        available_at = max(available_at, _utc(entry_manifest["collected_at"]))
    return {
        **normalize_result_rows(
            rows, meet=meet, race_date=day, entry_rosters=entry_rosters
        ),
        "capture_completed_at": end.isoformat(),
        "combined_sources_available_at": available_at.isoformat(),
        "capture_manifest_sha256": raw["capture_manifest_sha256"],
        "page_pins": raw["page_pins"],
        "entry_binding_pins": entry_pins,
        "independent_timestamp_verified": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    capture = commands.add_parser("capture")
    capture.add_argument("--meet", type=int, required=True)
    capture.add_argument("--race-date", required=True)
    capture.add_argument("--api-key-file", type=Path, required=True)
    capture.add_argument("--output-dir", type=Path, required=True)
    audit = commands.add_parser("audit")
    audit.add_argument("--capture", type=Path, required=True)
    audit.add_argument("--entry-capture", type=Path)
    audit.add_argument("--archive-root", type=Path)
    args = parser.parse_args(argv)
    if args.command == "capture":
        credentials = {"api_key": args.api_key_file.read_text()}
        path = asyncio.run(
            collect_result_snapshot(
                meet=args.meet,
                race_date=args.race_date,
                output_dir=args.output_dir,
                **credentials,
            )
        )
        print(json.dumps({"capture": str(path)}))
    else:
        path = args.capture
    try:
        result = replay_result_snapshot(
            path,
            entry_capture=getattr(args, "entry_capture", None),
            archive_root=getattr(args, "archive_root", None),
        )
    except ValueError as exc:
        print(
            json.dumps(
                {"status": "unresolved", "capture": str(path), "error": str(exc)}
            )
        )
        return 2
    print(
        json.dumps(
            {k: v for k, v in result.items() if k != "records"},
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
