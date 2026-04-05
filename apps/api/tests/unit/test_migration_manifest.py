from pathlib import Path

import pytest

import infrastructure.migration_manifest as migration_manifest
import scripts.apply_migrations as apply_migrations


def test_manifest_exposes_unified_chain_and_inactive_legacy_markers():
    assert migration_manifest.get_active_migration_names() == [
        "001_unified_schema.sql",
        "002_add_prediction_created_by.sql",
        "003_add_race_odds.sql",
        "004_add_job_shadow_fields.sql",
        "005_add_usage_events.sql",
        "006_canonical_job_status_backfill.sql",
    ]
    assert migration_manifest.get_required_migration_head() == (
        "006_canonical_job_status_backfill.sql"
    )
    assert "001_initial_schema.sql" not in migration_manifest.ACTIVE_MIGRATIONS
    assert migration_manifest.get_inactive_migration_names() == [
        "001_initial_schema.sql"
    ]
    assert set(migration_manifest.get_legacy_conflict_tables()) >= {
        "collection_jobs",
        "race_results",
        "prompt_versions",
    }


def test_manifest_paths_point_at_checked_in_migration_files():
    active_paths = migration_manifest.get_active_migration_paths()
    inactive_paths = migration_manifest.get_inactive_migration_paths()

    assert all(isinstance(path, Path) for path in active_paths + inactive_paths)
    assert active_paths[0].name == "001_unified_schema.sql"
    assert inactive_paths == [
        migration_manifest.get_migrations_dir() / "001_initial_schema.sql"
    ]


def test_validate_manifest_files_returns_active_manifest_paths(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    active_001 = tmp_path / "001_unified_schema.sql"
    active_006 = tmp_path / "006_canonical_job_status_backfill.sql"
    active_001.write_text("-- 001")
    active_006.write_text("-- 006")

    monkeypatch.setattr(
        apply_migrations, "get_active_migration_paths", lambda: [active_001, active_006]
    )
    monkeypatch.setattr(
        apply_migrations,
        "get_active_migration_names",
        lambda: [active_001.name, active_006.name],
    )
    monkeypatch.setattr(
        apply_migrations,
        "get_required_migration_head",
        lambda: active_006.name,
    )
    monkeypatch.setattr(
        apply_migrations,
        "get_inactive_migration_names",
        lambda: ["001_initial_schema.sql"],
    )

    paths = apply_migrations.validate_manifest_files()

    assert paths == [active_001, active_006]


def test_validate_manifest_files_rejects_missing_active_manifest_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    active_001 = tmp_path / "001_unified_schema.sql"
    missing_006 = tmp_path / "006_canonical_job_status_backfill.sql"
    active_001.write_text("-- 001")

    monkeypatch.setattr(
        apply_migrations, "get_active_migration_paths", lambda: [active_001, missing_006]
    )
    monkeypatch.setattr(
        apply_migrations,
        "get_required_migration_head",
        lambda: missing_006.name,
    )

    with pytest.raises(
        RuntimeError,
        match="Manifest references missing active migrations",
    ):
        apply_migrations.validate_manifest_files()


def test_print_manifest_contract_reports_active_head_and_inactive_legacy_files(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
):
    active_001 = tmp_path / "001_unified_schema.sql"
    active_006 = tmp_path / "006_canonical_job_status_backfill.sql"
    active_001.write_text("-- 001")
    active_006.write_text("-- 006")

    monkeypatch.setattr(
        apply_migrations,
        "get_active_migration_names",
        lambda: [active_001.name, active_006.name],
    )
    monkeypatch.setattr(
        apply_migrations,
        "get_required_migration_head",
        lambda: active_006.name,
    )
    monkeypatch.setattr(
        apply_migrations,
        "get_inactive_migration_names",
        lambda: ["001_initial_schema.sql"],
    )

    apply_migrations.print_manifest_contract([active_001, active_006])

    output = capsys.readouterr().out
    assert "Active head: 006_canonical_job_status_backfill.sql" in output
    assert "Required head: 006_canonical_job_status_backfill.sql" in output
    assert "Inactive legacy migration files:" in output
    assert "001_initial_schema.sql" in output
