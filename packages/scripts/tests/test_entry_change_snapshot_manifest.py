from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.entry_change_snapshot_manifest import (  # noqa: E402
    ENTRY_CHANGE_SNAPSHOT_SCHEMA_VERSION,
    select_entry_change_snapshot_for_replay,
)


def _write_manifest(
    snapshot_dir: Path,
    *,
    meet: int,
    source_snapshot_at: str,
    notices: list[dict[str, object]],
) -> Path:
    path = snapshot_dir / f"meet{meet}_{source_snapshot_at.replace(':', '')}.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": ENTRY_CHANGE_SNAPSHOT_SCHEMA_VERSION,
                "source_id": "entry_change_bulletin",
                "meet": meet,
                "source_snapshot_at": source_snapshot_at,
                "notices": notices,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def test_select_entry_change_snapshot_uses_latest_manifest_before_cutoff(
    tmp_path: Path,
) -> None:
    older = _write_manifest(
        tmp_path,
        meet=1,
        source_snapshot_at="2025-01-01T09:00:00+09:00",
        notices=[{"change_type": "jockey_change", "chul_no": 1}],
    )
    selected = _write_manifest(
        tmp_path,
        meet=1,
        source_snapshot_at="2025-01-01T10:00:00+09:00",
        notices=[{"change_type": "jockey_change", "chul_no": 2}],
    )
    _write_manifest(
        tmp_path,
        meet=1,
        source_snapshot_at="2025-01-01T10:45:00+09:00",
        notices=[{"change_type": "jockey_change", "chul_no": 3}],
    )
    _write_manifest(
        tmp_path,
        meet=2,
        source_snapshot_at="2025-01-01T10:10:00+09:00",
        notices=[{"change_type": "jockey_change", "chul_no": 4}],
    )

    result = select_entry_change_snapshot_for_replay(
        meet=1,
        cutoff_at="2025-01-01T10:30:00+09:00",
        snapshot_dir=tmp_path,
    )

    assert result.source_present is True
    assert result.manifest_path == str(selected)
    assert result.manifest_path != str(older)
    assert result.notices == [{"change_type": "jockey_change", "chul_no": 2}]
    assert result.available_manifest_count == 3
    assert result.skipped_after_cutoff_count == 1


def test_select_entry_change_snapshot_ignores_late_only_manifests(
    tmp_path: Path,
) -> None:
    _write_manifest(
        tmp_path,
        meet=1,
        source_snapshot_at="2025-01-01T10:45:00+09:00",
        notices=[{"change_type": "jockey_change", "chul_no": 3}],
    )

    result = select_entry_change_snapshot_for_replay(
        meet=1,
        cutoff_at="2025-01-01T10:30:00+09:00",
        snapshot_dir=tmp_path,
    )

    assert result.source_present is False
    assert result.notices is None
    assert result.reason == "all_manifests_after_cutoff"
    assert result.skipped_after_cutoff_count == 1
