"""Capture official dated schedules and freeze local future-universe candidates."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from shared.kra_schedule import (
    SOURCE_URLS,
    parse_schedule_html,
    reconcile_schedule_cards,
)

FORMAT_VERSION = "kra-schedule-capture-v1"
MAX_SOURCE_BYTES = 5 * 1024 * 1024
MAX_CAPTURE_SECONDS = 300
SOURCE_TIMEOUT_SECONDS = 30
FEATURE_CUTOFF_MINUTES = 30


def _utc(value: datetime | str) -> datetime:
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    if (
        not isinstance(parsed, datetime)
        or parsed.tzinfo is None
        or parsed.utcoffset() is None
    ):
        raise ValueError("schedule_timestamp_requires_timezone")
    return parsed.astimezone(UTC)


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, ensure_ascii=True, indent=2) + "\n"
    ).encode()


def _hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _write_new(path: Path, content: bytes) -> None:
    """Publish only complete bytes without replacing a concurrent output."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = stream.name
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)


async def collect_schedule_snapshot(
    *,
    output_dir: Path,
    client: httpx.AsyncClient | None = None,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> Path:
    started = _utc(clock())
    directory = output_dir / (
        started.strftime("%Y%m%dT%H%M%S.%fZ") + "_" + uuid4().hex[:12]
    )
    directory.mkdir(parents=True, exist_ok=False)
    manifest: dict[str, Any] = {
        "format_version": FORMAT_VERSION,
        "fetch_started_at": started.isoformat(),
        "capture_completed_at": None,
        "clock_basis": "local_system_utc_not_independent_registration",
        "sources": {},
    }
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=30, follow_redirects=False)
    previous = started
    try:
        for source_id, url in SOURCE_URLS.items():
            source: dict[str, Any] = {"url": url, "status": "fetch_error"}
            manifest["sources"][source_id] = source
            try:
                request_started = _utc(clock())
                if request_started < previous:
                    raise ValueError("schedule_clock_moved_backwards")
                source["fetch_started_at"] = request_started.isoformat()
                async with (
                    asyncio.timeout(SOURCE_TIMEOUT_SECONDS),
                    client.stream("GET", url, follow_redirects=False) as response,
                ):
                    if response.status_code != 200 or str(response.url) != url:
                        raise ValueError("noncanonical_schedule_response")
                    if (
                        response.headers.get("content-type", "").split(";")[0].lower()
                        != "text/html"
                    ):
                        raise ValueError("non_html_schedule_response")
                    raw = bytearray()
                    async for chunk in response.aiter_bytes():
                        raw.extend(chunk)
                        if len(raw) > MAX_SOURCE_BYTES:
                            raise ValueError("schedule_response_too_large")
                    encoding = response.encoding or "euc-kr"
                    http_date = response.headers.get("date")
                completed = _utc(clock())
                if completed < request_started:
                    raise ValueError("schedule_clock_moved_backwards")
                if (completed - started).total_seconds() > MAX_CAPTURE_SECONDS:
                    raise ValueError("schedule_capture_window_exceeded")
                content = bytes(raw)
                digest = _hash(content)
                filename = f"{source_id}_{digest}.html"
                _write_new(directory / filename, content)
                source.update(
                    status="captured",
                    capture_completed_at=completed.isoformat(),
                    sha256=digest,
                    byte_count=len(content),
                    raw_file=filename,
                    encoding=encoding,
                    http_date=http_date,
                )
                previous = completed
            except (httpx.HTTPError, TimeoutError, ValueError) as exc:
                source.update(
                    error_type=type(exc).__name__,
                    error="schedule_http_failure"
                    if isinstance(exc, (httpx.HTTPError, TimeoutError))
                    else str(exc),
                )
    finally:
        if owns_client:
            await client.aclose()
        completed = _utc(clock())
        manifest["capture_completed_at"] = completed.isoformat()
        if (
            completed < previous
            or (completed - started).total_seconds() > MAX_CAPTURE_SECONDS
        ):
            manifest["error"] = "invalid_schedule_capture_clock_window"
        _write_new(directory / "capture.json", _json_bytes(manifest))
    return directory / "capture.json"


def replay_schedule_snapshot(capture_path: Path, *, race_date: str) -> dict[str, Any]:
    """Parse exactly the pinned original bytes; supplied derived summaries are ignored."""
    manifest_bytes = capture_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    if (
        not isinstance(manifest, dict)
        or manifest.get("format_version") != FORMAT_VERSION
    ):
        raise ValueError("unsupported_schedule_capture")
    started = _utc(manifest["fetch_started_at"])
    completed = _utc(manifest["capture_completed_at"])
    if (
        completed < started
        or (completed - started).total_seconds() > MAX_CAPTURE_SECONDS
        or manifest.get("error")
    ):
        raise ValueError("invalid_schedule_capture_clock_window")
    sources = manifest.get("sources")
    if not isinstance(sources, dict) or set(sources) != set(SOURCE_URLS):
        raise ValueError("incomplete_schedule_source_manifest")
    cards = {}
    failures = []
    pins = {}
    previous = started
    for source_id, url in SOURCE_URLS.items():
        source = sources[source_id]
        try:
            if not isinstance(source, dict) or source.get("url") != url:
                raise ValueError("noncanonical_schedule_source")
            if source.get("status") != "captured":
                raise ValueError("schedule_source_not_captured")
            request_at = _utc(source["fetch_started_at"])
            captured_at = _utc(source["capture_completed_at"])
            if not previous <= request_at <= captured_at <= completed:
                raise ValueError("invalid_schedule_source_time")
            previous = captured_at
            filename = source["raw_file"]
            expected_name = f"{source_id}_{source['sha256']}.html"
            if (
                not isinstance(filename, str)
                or filename != expected_name
                or Path(filename).name != filename
            ):
                raise ValueError("invalid_schedule_source_filename")
            path = capture_path.parent / filename
            if path.is_symlink():
                raise ValueError("schedule_source_symlink")
            if path.stat().st_size > MAX_SOURCE_BYTES:
                raise ValueError("schedule_response_too_large")
            content = path.read_bytes()
            if (
                type(source["byte_count"]) is not int
                or len(content) != source["byte_count"]
                or _hash(content) != source["sha256"]
            ):
                raise ValueError("schedule_source_hash_mismatch")
            cards[source_id] = parse_schedule_html(
                content, source_id=source_id, encoding=source["encoding"]
            )
            pins[source_id] = {
                "sha256": source["sha256"],
                "byte_count": len(content),
                "capture_completed_at": captured_at.isoformat(),
                "url": url,
            }
        except (KeyError, TypeError, ValueError, LookupError, OSError) as exc:
            failures.append(
                {
                    "source_id": source_id,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                }
            )
    report = reconcile_schedule_cards(cards, race_date=race_date)
    report.update(
        capture_manifest_sha256=_hash(manifest_bytes),
        capture_completed_at=completed.isoformat(),
        source_pins=pins,
        source_failures=failures,
    )
    return report


def freeze_universe_candidate(
    capture_path: Path,
    *,
    race_date: str,
    output: Path,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict[str, Any]:
    report = replay_schedule_snapshot(capture_path, race_date=race_date)
    if (
        report["status"] != "reconciled"
        or report["source_failures"]
        or not report["races"]
    ):
        raise ValueError("universe_requires_complete_reconciled_official_cards")
    races = []
    for item in report["races"]:
        observations = item["source_observations"]
        national = observations["national"]
        start = _utc(national["scheduled_start_at"])
        races.append(
            {
                **national,
                "feature_cutoff_at": (
                    start - timedelta(minutes=FEATURE_CUTOFF_MINUTES)
                ).isoformat(),
                "source_observations": observations,
            }
        )
    earliest = min(_utc(race["feature_cutoff_at"]) for race in races)
    frozen_at = _utc(clock())
    if not _utc(report["capture_completed_at"]) <= frozen_at < earliest:
        raise ValueError("universe_must_be_frozen_before_earliest_cutoff")
    candidate = {
        "format_version": "kra-local-universe-candidate-v1",
        "race_date": race_date,
        "scope": report["scope"],
        "race_count": len(races),
        "frozen_at": frozen_at.isoformat(),
        "feature_cutoff_minutes": FEATURE_CUTOFF_MINUTES,
        "capture_manifest_sha256": report["capture_manifest_sha256"],
        "source_pins": report["source_pins"],
        "races": races,
        "registration_status": "pending_independent_server_receipt",
        "independent_time_verified": False,
        "target_accuracy_verified": False,
    }
    content = _json_bytes(candidate)
    _write_new(output, content)
    return {
        "path": str(output),
        "sha256": _hash(content),
        "race_count": len(races),
        "registration_status": candidate["registration_status"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    capture = sub.add_parser("capture")
    capture.add_argument("--output-dir", type=Path, required=True)
    for name in ("audit", "freeze"):
        command = sub.add_parser(name)
        command.add_argument("--capture", type=Path, required=True)
        command.add_argument("--race-date", required=True)
        if name == "freeze":
            command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "capture":
        result = {
            "capture": str(
                asyncio.run(collect_schedule_snapshot(output_dir=args.output_dir))
            )
        }
    elif args.command == "audit":
        result = replay_schedule_snapshot(args.capture, race_date=args.race_date)
    else:
        result = freeze_universe_candidate(
            args.capture, race_date=args.race_date, output=args.output
        )
    print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if args.command != "audit" or result["status"] == "reconciled" else 2


if __name__ == "__main__":
    raise SystemExit(main())
