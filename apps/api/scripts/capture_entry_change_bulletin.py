"""Capture KRA entry-change bulletin snapshots for T-30 replay.

Usage:
    uv run python scripts/capture_entry_change_bulletin.py --meet 1
    uv run python scripts/capture_entry_change_bulletin.py --meet 1 --meet 3
"""

# ruff: noqa: E402, I001

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

API_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = API_DIR.parent.parent
sys.path.insert(0, str(API_DIR))
os.chdir(API_DIR)

from infrastructure.prerace_sources.base import RawSourceResponse  # noqa: E402
from infrastructure.prerace_sources.changes import (  # noqa: E402
    EntryChangeConnector,
    EntryChangeNotice,
    parse_entry_change_bulletin_response,
)


SNAPSHOT_SCHEMA_VERSION = "entry-change-bulletin-snapshot-v1"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "data" / "source_snapshots" / "entry_change_bulletin"


@dataclass(frozen=True, slots=True)
class EntryChangeSnapshotPaths:
    raw_html_path: Path
    manifest_path: Path


def _safe_timestamp(value: str) -> str:
    return value.replace(":", "").replace("-", "").replace("+", "p").replace(".", "_")


def _content_sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def build_snapshot_paths(
    *,
    output_dir: Path,
    meet: int,
    fetched_at: str,
) -> EntryChangeSnapshotPaths:
    stem = f"meet{meet}_{_safe_timestamp(fetched_at)}"
    return EntryChangeSnapshotPaths(
        raw_html_path=output_dir / f"{stem}.html",
        manifest_path=output_dir / f"{stem}.json",
    )


def build_snapshot_manifest(
    *,
    response: RawSourceResponse,
    meet: int,
    notices: tuple[EntryChangeNotice, ...],
    raw_html_path: Path,
) -> dict[str, Any]:
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "source_id": response.spec.source_id,
        "meet": meet,
        "source_snapshot_at": response.fetched_at,
        "requested_url": response.requested_url,
        "status_code": response.status_code,
        "encoding": response.encoding,
        "content_sha256": _content_sha256(response.body),
        "raw_html_path": str(raw_html_path),
        "notice_count": len(notices),
        "notices": [notice.to_dict() for notice in notices],
    }


def write_entry_change_snapshot(
    *,
    response: RawSourceResponse,
    meet: int,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    notices = parse_entry_change_bulletin_response(response, meet=meet)
    paths = build_snapshot_paths(
        output_dir=output_dir,
        meet=meet,
        fetched_at=response.fetched_at,
    )
    paths.raw_html_path.parent.mkdir(parents=True, exist_ok=True)
    paths.raw_html_path.write_bytes(response.body)
    manifest = build_snapshot_manifest(
        response=response,
        meet=meet,
        notices=notices,
        raw_html_path=paths.raw_html_path,
    )
    paths.manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "manifest_path": str(paths.manifest_path),
        "raw_html_path": str(paths.raw_html_path),
        "notice_count": len(notices),
        "source_snapshot_at": response.fetched_at,
    }


async def capture_entry_change_bulletin(
    *,
    meet: int,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    async with EntryChangeConnector() as connector:
        response = await connector.fetch_raw(meet=meet)
    return write_entry_change_snapshot(
        response=response,
        meet=meet,
        output_dir=output_dir,
    )


async def capture_many(
    *,
    meets: list[int],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> list[dict[str, Any]]:
    results = []
    for meet in meets:
        results.append(
            await capture_entry_change_bulletin(
                meet=meet,
                output_dir=output_dir,
            )
        )
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture KRA entry-change bulletin raw HTML and parsed notices."
    )
    parser.add_argument(
        "--meet",
        action="append",
        type=int,
        required=True,
        help="KRA meet code. Repeat to capture multiple meets.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for raw HTML and JSON manifests.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = asyncio.run(
        capture_many(
            meets=args.meet,
            output_dir=args.output_dir,
        )
    )
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
