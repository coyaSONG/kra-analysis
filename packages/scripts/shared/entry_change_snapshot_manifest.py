"""Read captured entry-change bulletin manifests for strict replay."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_ENTRY_CHANGE_SNAPSHOT_DIR = (
    ROOT_DIR / "data" / "source_snapshots" / "entry_change_bulletin"
)
ENTRY_CHANGE_SNAPSHOT_SCHEMA_VERSION = "entry-change-bulletin-snapshot-v1"


@dataclass(frozen=True, slots=True)
class EntryChangeSnapshotSelection:
    source_present: bool
    notices: list[dict[str, Any]] | None
    manifest_path: str | None
    source_snapshot_at: str | None
    available_manifest_count: int
    skipped_after_cutoff_count: int
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_present": self.source_present,
            "manifest_path": self.manifest_path,
            "source_snapshot_at": self.source_snapshot_at,
            "available_manifest_count": self.available_manifest_count,
            "skipped_after_cutoff_count": self.skipped_after_cutoff_count,
            "reason": self.reason,
        }


def _parse_instant(value: object) -> datetime | None:
    if value in ("", None):
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone() if parsed.tzinfo is not None else parsed


def _load_manifest(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("schema_version") != ENTRY_CHANGE_SNAPSHOT_SCHEMA_VERSION:
        return None
    return payload if isinstance(payload, dict) else None


def select_entry_change_snapshot_for_replay(
    *,
    meet: int,
    cutoff_at: str,
    snapshot_dir: Path = DEFAULT_ENTRY_CHANGE_SNAPSHOT_DIR,
) -> EntryChangeSnapshotSelection:
    """Select the latest captured bulletin manifest at or before cutoff."""

    cutoff = _parse_instant(cutoff_at)
    if cutoff is None:
        return EntryChangeSnapshotSelection(
            source_present=False,
            notices=None,
            manifest_path=None,
            source_snapshot_at=None,
            available_manifest_count=0,
            skipped_after_cutoff_count=0,
            reason="invalid_cutoff_at",
        )
    if not snapshot_dir.exists():
        return EntryChangeSnapshotSelection(
            source_present=False,
            notices=None,
            manifest_path=None,
            source_snapshot_at=None,
            available_manifest_count=0,
            skipped_after_cutoff_count=0,
            reason="snapshot_dir_missing",
        )

    candidates: list[tuple[datetime, Path, dict[str, Any]]] = []
    skipped_after_cutoff = 0
    available_count = 0
    for path in sorted(snapshot_dir.glob("*.json")):
        manifest = _load_manifest(path)
        if not manifest or int(manifest.get("meet") or 0) != meet:
            continue
        source_snapshot_at = _parse_instant(manifest.get("source_snapshot_at"))
        if source_snapshot_at is None:
            continue
        available_count += 1
        if source_snapshot_at > cutoff:
            skipped_after_cutoff += 1
            continue
        candidates.append((source_snapshot_at, path, manifest))

    if not candidates:
        reason = (
            "no_manifest_for_meet"
            if available_count == 0
            else "all_manifests_after_cutoff"
        )
        return EntryChangeSnapshotSelection(
            source_present=False,
            notices=None,
            manifest_path=None,
            source_snapshot_at=None,
            available_manifest_count=available_count,
            skipped_after_cutoff_count=skipped_after_cutoff,
            reason=reason,
        )

    _source_snapshot_at, path, selected = max(candidates, key=lambda item: item[0])
    raw_notices = selected.get("notices") or []
    notices = [notice for notice in raw_notices if isinstance(notice, dict)]
    return EntryChangeSnapshotSelection(
        source_present=True,
        notices=notices,
        manifest_path=str(path),
        source_snapshot_at=str(selected.get("source_snapshot_at")),
        available_manifest_count=available_count,
        skipped_after_cutoff_count=skipped_after_cutoff,
        reason="selected_latest_before_cutoff",
    )
