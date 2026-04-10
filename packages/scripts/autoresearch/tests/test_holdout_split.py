from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.read_contract import RaceKey, RaceSnapshot  # noqa: E402

from autoresearch.holdout_split import (  # noqa: E402
    assess_race_for_recent_holdout,
    check_manifest_reproducibility,
    plan_recent_holdout_manifests,
    plan_recent_holdout_selections,
    serialize_split_manifest,
    write_split_manifests,
)

_FIXTURE_DIR = Path(__file__).with_name("fixtures")
_FIXTURE_CREATED_AT = "2026-04-10T12:00:00+09:00"
_FIXTURE_DEFAULT_EVALUATION_SEEDS = (11, 17, 23, 31, 37, 41, 47, 53, 59, 61)
_FIXTURE_ALTERNATE_EVALUATION_SEEDS = (101, 103, 107, 109, 113, 127, 131, 137, 139, 149)


def _load_split_fixture_snapshots() -> list[RaceSnapshot]:
    rows = json.loads(
        (_FIXTURE_DIR / "recent_holdout_split_snapshots.json").read_text(
            encoding="utf-8"
        )
    )
    return [RaceSnapshot.from_row(row) for row in rows]


def _load_expected_split_manifests() -> dict[str, dict]:
    return json.loads(
        (_FIXTURE_DIR / "recent_holdout_split_expected.json").read_text(
            encoding="utf-8"
        )
    )


def _strip_seed_only_manifest_fields(payload: dict) -> dict:
    normalized = deepcopy(payload)
    normalized["metadata"]["seed"] = {
        "selection_seed": None,
        "selection_seed_invariant": True,
        "evaluation_seeds": "__seed_block__",
    }
    normalized["manifest_sha256"] = "__manifest_sha256__"
    return normalized


def _make_basic_data(
    race_date: str,
    race_number: int,
    *,
    starters: tuple[int, ...] = (1, 2, 3),
    collected_at: str = "2025-01-01T10:30:00+09:00",
) -> dict:
    items = [
        {
            "rcDate": race_date,
            "rcNo": str(race_number),
            "meet": "서울",
            "rcDist": 1200,
            "track": "건조",
            "weather": "맑음",
            "budam": "별정A",
            "ageCond": "3세",
            "chulNo": chul_no,
            "hrName": f"테스트마-{chul_no}",
            "hrNo": f"HR{race_date}{race_number}{chul_no}",
            "jkName": f"기수-{chul_no}",
            "jkNo": f"JK{chul_no:03d}",
            "trName": f"조교사-{chul_no}",
            "trNo": f"TR{chul_no:03d}",
            "age": 3 + (chul_no % 3),
            "sex": "수" if chul_no % 2 else "암",
            "wgBudam": 54 + (chul_no % 2),
            "winOdds": float(chul_no),
            "plcOdds": float(chul_no) + 0.2,
        }
        for chul_no in starters
    ]
    horses = [
        {
            "chul_no": chul_no,
            "hrDetail": {"name": f"테스트마-{chul_no}"},
            "jkDetail": {"name": f"기수-{chul_no}"},
            "trDetail": {"name": f"조교사-{chul_no}"},
        }
        for chul_no in starters
    ]
    return {
        "collected_at": collected_at,
        "race_info": {"response": {"body": {"items": {"item": items}}}},
        "race_plan": {"sch_st_time": "1100"},
        "track": {"weather": "맑음"},
        "cancelled_horses": [],
        "horses": horses,
    }


def _make_snapshot(
    race_date: str,
    meet: int,
    race_number: int,
    *,
    result_status: str = "collected",
    starters: tuple[int, ...] = (1, 2, 3),
    top3: tuple[int, int, int] = (1, 2, 3),
    basic_data: dict | None = None,
) -> RaceSnapshot:
    return RaceSnapshot(
        key=RaceKey(
            race_id=f"{race_date}_{meet}_{race_number}",
            race_date=race_date,
            meet=meet,
            race_number=race_number,
        ),
        collection_status="collected",
        result_status=result_status,
        basic_data=basic_data
        or _make_basic_data(race_date, race_number, starters=starters),
        result_data={"top3": list(top3)},
        collected_at="2025-01-01T10:30:00+09:00",
        updated_at="2025-01-01T10:31:00+09:00",
    )


def test_holdout_manifest_accumulates_by_full_race_dates() -> None:
    snapshots = [
        _make_snapshot("20250101", 1, 1),
        _make_snapshot("20250101", 3, 1),
        _make_snapshot("20250102", 1, 1),
        _make_snapshot("20250102", 3, 1),
        _make_snapshot("20250103", 1, 1),
        _make_snapshot("20250103", 3, 1),
    ]

    manifests = plan_recent_holdout_manifests(
        snapshots,
        manifest_created_at="2026-04-10T12:00:00+09:00",
        holdout_minimum_race_count=3,
        mini_val_minimum_race_count=2,
    )

    holdout_manifest = manifests["holdout"]
    assert holdout_manifest.metadata.period.start_date.isoformat() == "2025-01-02"
    assert holdout_manifest.metadata.period.end_date.isoformat() == "2025-01-03"
    assert holdout_manifest.metadata.period.race_count == 4
    assert holdout_manifest.included_race_ids == (
        "20250102_1_1",
        "20250102_3_1",
        "20250103_1_1",
        "20250103_3_1",
    )
    assert set(holdout_manifest.race_input_snapshot_map) == set(
        holdout_manifest.included_race_ids
    )
    assert (
        holdout_manifest.race_input_snapshot_map[
            "20250102_1_1"
        ].snapshot_generation_basis.source_filter_basis
        == "entry_finalized_at"
    )
    assert holdout_manifest.metadata.seed.selection_seed_invariant is True
    assert holdout_manifest.excluded_race_dates == ()


def test_holdout_manifest_skips_latest_incomplete_date_deterministically() -> None:
    snapshots = [
        _make_snapshot("20250101", 1, 1),
        _make_snapshot("20250101", 3, 1),
        _make_snapshot("20250102", 1, 1),
        _make_snapshot("20250102", 3, 1),
        _make_snapshot("20250103", 1, 1),
        _make_snapshot("20250103", 3, 1),
        _make_snapshot("20250104", 1, 1),
        _make_snapshot("20250104", 3, 1, result_status="pending"),
    ]

    manifests = plan_recent_holdout_manifests(
        snapshots,
        manifest_created_at="2026-04-10T12:00:00+09:00",
        holdout_minimum_race_count=3,
        mini_val_minimum_race_count=2,
    )

    holdout_manifest = manifests["holdout"]
    assert (
        holdout_manifest.metadata.period.latest_complete_race_date.isoformat()
        == "2025-01-03"
    )
    assert tuple(item.isoformat() for item in holdout_manifest.excluded_race_dates) == (
        "2025-01-04",
    )
    assert holdout_manifest.exclusion_reason_counts == {
        "incomplete_race_date": 1,
        "missing_result_data": 1,
    }


def test_assess_race_for_recent_holdout_accepts_zero_market_runners_via_candidate_filter() -> (
    None
):
    basic_data = _make_basic_data("20250101", 1, starters=(1, 2, 3))
    items = basic_data["race_info"]["response"]["body"]["items"]["item"]
    items[1]["winOdds"] = 0.0
    items[1]["plcOdds"] = 0.0
    items[2]["winOdds"] = 0.0
    items[2]["plcOdds"] = 0.0
    snapshot = _make_snapshot("20250101", 1, 1, basic_data=basic_data)

    assessment = assess_race_for_recent_holdout(snapshot)

    assert assessment.included is True
    assert assessment.exclusion_reason is None


def test_assess_race_for_recent_holdout_applies_minimum_info_fallback_after_reinclusion_shortage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    basic_data = _make_basic_data("20250101", 1, starters=(1, 2, 3))
    snapshot = _make_snapshot("20250101", 1, 1, basic_data=basic_data)

    def _underfilled_candidate_filter(
        runners: list[dict[str, object]],
        *,
        cancelled_horses: list[dict[str, object]] | None = None,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            eligible_runners=runners[:2],
            status_records=(),
            reinclusion_decisions=(),
        )

    monkeypatch.setattr(
        "shared.runner_status.filter_candidate_runners",
        _underfilled_candidate_filter,
    )

    assessment = assess_race_for_recent_holdout(snapshot)

    assert assessment.included is True
    assert assessment.exclusion_reason is None


def test_assess_race_for_recent_holdout_accepts_snapshot_at_cutoff_boundary() -> None:
    basic_data = _make_basic_data(
        "20250101",
        1,
        collected_at="2025-01-01T10:50:00+09:00",
    )
    snapshot = _make_snapshot("20250101", 1, 1, basic_data=basic_data)

    assessment = assess_race_for_recent_holdout(snapshot)

    assert assessment.included is True
    assert assessment.exclusion_reason is None
    assert assessment.entry_finalized_at is not None
    assert assessment.entry_finalized_at.isoformat() == "2025-01-01T10:50:00+09:00"


def test_plan_recent_holdout_manifests_tracks_pre_and_post_cutoff_dates() -> None:
    snapshots = [
        _make_snapshot(
            "20241231",
            1,
            1,
            basic_data=_make_basic_data(
                "20241231",
                1,
                collected_at="2024-12-31T10:45:00+09:00",
            ),
        ),
        _make_snapshot(
            "20241231",
            3,
            1,
            basic_data=_make_basic_data(
                "20241231",
                1,
                collected_at="2024-12-31T10:47:00+09:00",
            ),
        ),
        _make_snapshot(
            "20250101",
            1,
            1,
            basic_data=_make_basic_data(
                "20250101",
                1,
                collected_at="2025-01-01T10:45:00+09:00",
            ),
        ),
        _make_snapshot(
            "20250101",
            3,
            1,
            basic_data=_make_basic_data(
                "20250101",
                1,
                collected_at="2025-01-01T10:49:00+09:00",
            ),
        ),
        _make_snapshot(
            "20250102",
            1,
            1,
            basic_data=_make_basic_data(
                "20250102",
                1,
                collected_at="2025-01-02T10:45:00+09:00",
            ),
        ),
        _make_snapshot(
            "20250102",
            3,
            1,
            basic_data=_make_basic_data(
                "20250102",
                1,
                collected_at="2025-01-02T10:55:00+09:00",
            ),
        ),
        _make_snapshot(
            "20250103",
            1,
            1,
            basic_data=_make_basic_data(
                "20250103",
                1,
                collected_at="2025-01-03T10:40:00+09:00",
            ),
        ),
        _make_snapshot(
            "20250103",
            3,
            1,
            basic_data=_make_basic_data(
                "20250103",
                1,
                collected_at="2025-01-03T10:48:00+09:00",
            ),
        ),
    ]

    manifests = plan_recent_holdout_manifests(
        snapshots,
        manifest_created_at="2026-04-10T12:00:00+09:00",
        holdout_minimum_race_count=4,
        mini_val_minimum_race_count=2,
    )

    holdout_manifest = manifests["holdout"]

    assert holdout_manifest.included_race_ids == (
        "20250101_1_1",
        "20250101_3_1",
        "20250103_1_1",
        "20250103_3_1",
    )
    assert tuple(item.isoformat() for item in holdout_manifest.excluded_race_dates) == (
        "2025-01-02",
    )
    assert holdout_manifest.exclusion_reason_counts == {
        "incomplete_race_date": 1,
        "late_snapshot_unusable": 1,
    }


def test_holdout_and_mini_val_do_not_overlap() -> None:
    snapshots = []
    for race_date in (
        "20250101",
        "20250102",
        "20250103",
        "20250104",
        "20250105",
        "20250106",
    ):
        snapshots.append(_make_snapshot(race_date, 1, 1))
        snapshots.append(_make_snapshot(race_date, 3, 1))

    manifests = plan_recent_holdout_manifests(
        snapshots,
        manifest_created_at="2026-04-10T12:00:00+09:00",
        holdout_minimum_race_count=4,
        mini_val_minimum_race_count=4,
    )

    holdout_ids = set(manifests["holdout"].included_race_ids)
    mini_val_ids = set(manifests["mini_val"].included_race_ids)

    assert holdout_ids.isdisjoint(mini_val_ids)
    assert (
        manifests["mini_val"].metadata.period.end_date
        < manifests["holdout"].metadata.period.start_date
    )


def test_plan_recent_holdout_selections_returns_expected_race_ids_per_dataset() -> None:
    snapshots = []
    for race_date in ("20250101", "20250102", "20250103", "20250104"):
        snapshots.append(_make_snapshot(race_date, 1, 1))
        snapshots.append(_make_snapshot(race_date, 3, 1))

    selections = plan_recent_holdout_selections(
        snapshots,
        holdout_minimum_race_count=4,
        mini_val_minimum_race_count=2,
    )

    assert selections["holdout"].expected_race_ids == (
        "20250103_1_1",
        "20250103_3_1",
        "20250104_1_1",
        "20250104_3_1",
    )
    assert selections["holdout"].selected_race_dates == (
        selections["holdout"].start_date,
        selections["holdout"].end_date,
    )
    assert selections["mini_val"].expected_race_ids == (
        "20250102_1_1",
        "20250102_3_1",
    )


def test_plan_recent_holdout_selections_ignores_non_kra_meet_rows() -> None:
    snapshots = [
        _make_snapshot("20250101", 1, 1),
        _make_snapshot("20250101", 3, 1),
        _make_snapshot("20250101", 9, 1),
        _make_snapshot("20250102", 1, 1),
        _make_snapshot("20250102", 3, 1),
        _make_snapshot("20250103", 1, 1),
        _make_snapshot("20250103", 3, 1),
    ]

    selections = plan_recent_holdout_selections(
        snapshots,
        holdout_minimum_race_count=4,
        mini_val_minimum_race_count=2,
    )

    assert selections["mini_val"].expected_race_ids == (
        "20250101_1_1",
        "20250101_3_1",
    )
    assert all(
        "_9_" not in race_id for race_id in selections["mini_val"].expected_race_ids
    )
    assert selections["holdout"].expected_race_ids == (
        "20250102_1_1",
        "20250102_3_1",
        "20250103_1_1",
        "20250103_3_1",
    )


def test_holdout_manifest_reproducibility_is_input_order_invariant() -> None:
    snapshots = []
    for race_date in (
        "20250101",
        "20250102",
        "20250103",
        "20250104",
        "20250105",
        "20250106",
    ):
        snapshots.append(_make_snapshot(race_date, 1, 1))
        snapshots.append(_make_snapshot(race_date, 3, 1))

    created_at = "2026-04-10T12:00:00+09:00"
    baseline = plan_recent_holdout_manifests(
        snapshots,
        manifest_created_at=created_at,
        holdout_minimum_race_count=4,
        mini_val_minimum_race_count=4,
    )
    regenerated = plan_recent_holdout_manifests(
        list(reversed(snapshots)),
        manifest_created_at=created_at,
        holdout_minimum_race_count=4,
        mini_val_minimum_race_count=4,
    )

    for dataset in ("holdout", "mini_val"):
        assert serialize_split_manifest(baseline[dataset]) == serialize_split_manifest(
            regenerated[dataset]
        )
        assert baseline[dataset].manifest_sha256 == regenerated[dataset].manifest_sha256


def test_holdout_manifest_regression_fixture_is_stable_for_same_input_and_same_seed() -> (
    None
):
    snapshots = _load_split_fixture_snapshots()
    expected = _load_expected_split_manifests()

    baseline = plan_recent_holdout_manifests(
        snapshots,
        manifest_created_at=_FIXTURE_CREATED_AT,
        holdout_minimum_race_count=4,
        mini_val_minimum_race_count=4,
        evaluation_seeds=_FIXTURE_DEFAULT_EVALUATION_SEEDS,
    )
    regenerated = plan_recent_holdout_manifests(
        snapshots,
        manifest_created_at=_FIXTURE_CREATED_AT,
        holdout_minimum_race_count=4,
        mini_val_minimum_race_count=4,
        evaluation_seeds=_FIXTURE_DEFAULT_EVALUATION_SEEDS,
    )

    for dataset in ("holdout", "mini_val"):
        baseline_payload = baseline[dataset].model_dump(mode="json")
        regenerated_payload = regenerated[dataset].model_dump(mode="json")

        assert baseline_payload == expected[dataset]
        assert regenerated_payload == expected[dataset]
        assert serialize_split_manifest(baseline[dataset]) == serialize_split_manifest(
            regenerated[dataset]
        )


def test_holdout_manifest_seed_change_only_updates_seed_block_and_checksums() -> None:
    snapshots = _load_split_fixture_snapshots()

    baseline = plan_recent_holdout_manifests(
        snapshots,
        manifest_created_at=_FIXTURE_CREATED_AT,
        holdout_minimum_race_count=4,
        mini_val_minimum_race_count=4,
        evaluation_seeds=_FIXTURE_DEFAULT_EVALUATION_SEEDS,
    )
    alternate = plan_recent_holdout_manifests(
        snapshots,
        manifest_created_at=_FIXTURE_CREATED_AT,
        holdout_minimum_race_count=4,
        mini_val_minimum_race_count=4,
        evaluation_seeds=_FIXTURE_ALTERNATE_EVALUATION_SEEDS,
    )

    for dataset in ("holdout", "mini_val"):
        baseline_payload = baseline[dataset].model_dump(mode="json")
        alternate_payload = alternate[dataset].model_dump(mode="json")

        assert (
            baseline_payload["included_race_ids"]
            == alternate_payload["included_race_ids"]
        )
        assert (
            baseline_payload["race_input_snapshot_map"]
            == alternate_payload["race_input_snapshot_map"]
        )
        assert _strip_seed_only_manifest_fields(
            baseline_payload
        ) == _strip_seed_only_manifest_fields(alternate_payload)
        assert baseline_payload["metadata"]["seed"]["evaluation_seeds"] == list(
            _FIXTURE_DEFAULT_EVALUATION_SEEDS
        )
        assert alternate_payload["metadata"]["seed"]["evaluation_seeds"] == list(
            _FIXTURE_ALTERNATE_EVALUATION_SEEDS
        )
        assert (
            baseline_payload["manifest_sha256"] != alternate_payload["manifest_sha256"]
        )


def test_check_manifest_reproducibility_reports_identical_regeneration() -> None:
    snapshots = []
    for race_date in (
        "20250101",
        "20250102",
        "20250103",
        "20250104",
        "20250105",
        "20250106",
    ):
        snapshots.append(_make_snapshot(race_date, 1, 1))
        snapshots.append(_make_snapshot(race_date, 3, 1))

    created_at = "2026-04-10T12:00:00+09:00"
    baseline = plan_recent_holdout_manifests(
        snapshots,
        manifest_created_at=created_at,
        holdout_minimum_race_count=4,
        mini_val_minimum_race_count=4,
    )

    report = check_manifest_reproducibility(
        list(reversed(snapshots)),
        manifest_created_at=created_at,
        holdout_minimum_race_count=4,
        mini_val_minimum_race_count=4,
        reference_manifests=baseline,
    )

    assert report["passed"] is True
    assert report["manifest_created_at"] == created_at
    assert set(report["datasets"]) == {"holdout", "mini_val"}
    for dataset in ("holdout", "mini_val"):
        dataset_report = report["datasets"][dataset]
        assert dataset_report["passed"] is True
        assert dataset_report["sample_composition_match"] is True
        assert dataset_report["sample_identifier_match"] is True
        assert dataset_report["canonical_payload_match"] is True
        assert (
            dataset_report["reference_manifest_sha256"]
            == dataset_report["regenerated_manifest_sha256"]
        )
        assert dataset_report["canonical_payload_sha256"]
        assert dataset_report["byte_length"] > 0
        assert dataset_report["race_id_mismatch"] is None
        assert dataset_report["snapshot_id_mismatch"] is None


def test_check_manifest_reproducibility_reports_race_and_snapshot_identifier_drift() -> (
    None
):
    snapshots = []
    for race_date in (
        "20250101",
        "20250102",
        "20250103",
        "20250104",
        "20250105",
        "20250106",
    ):
        snapshots.append(_make_snapshot(race_date, 1, 1))
        snapshots.append(_make_snapshot(race_date, 3, 1))

    created_at = "2026-04-10T12:00:00+09:00"
    baseline = plan_recent_holdout_manifests(
        snapshots,
        manifest_created_at=created_at,
        holdout_minimum_race_count=4,
        mini_val_minimum_race_count=4,
    )

    holdout = baseline["holdout"]
    first_race_id = holdout.included_race_ids[0]
    mutated_snapshot_map = {
        **holdout.race_input_snapshot_map,
        first_race_id: holdout.race_input_snapshot_map[first_race_id].model_copy(
            update={"snapshot_id": "holdout-input-v1:deadbeefdeadbeef"}
        ),
    }
    mutated_reference = {
        **baseline,
        "holdout": holdout.model_copy(
            update={
                "included_race_ids": tuple(reversed(holdout.included_race_ids)),
                "race_input_snapshot_map": mutated_snapshot_map,
            }
        ),
    }

    report = check_manifest_reproducibility(
        snapshots,
        manifest_created_at=created_at,
        holdout_minimum_race_count=4,
        mini_val_minimum_race_count=4,
        reference_manifests=mutated_reference,
    )

    assert report["passed"] is False
    holdout_report = report["datasets"]["holdout"]
    assert holdout_report["passed"] is False
    assert holdout_report["sample_composition_match"] is False
    assert holdout_report["sample_identifier_match"] is False
    assert holdout_report["race_id_mismatch"]["first_mismatch_index"] == 0
    assert holdout_report["snapshot_id_mismatch"]["first_mismatch_index"] == 0
    assert (
        holdout_report["snapshot_id_mismatch"]["reference_value"]
        != holdout_report["snapshot_id_mismatch"]["regenerated_value"]
    )


def test_plan_recent_holdout_manifests_enforces_automatic_reproducibility_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshots = []
    for race_date in (
        "20250101",
        "20250102",
        "20250103",
        "20250104",
        "20250105",
        "20250106",
    ):
        snapshots.append(_make_snapshot(race_date, 1, 1))
        snapshots.append(_make_snapshot(race_date, 3, 1))

    def _fail_check(*args: object, **kwargs: object) -> dict[str, object]:
        return {
            "passed": False,
            "datasets": {
                "holdout": {"passed": False},
                "mini_val": {"passed": True},
            },
        }

    monkeypatch.setattr(
        "autoresearch.holdout_split.check_manifest_reproducibility", _fail_check
    )

    with pytest.raises(ValueError, match="재생성 검증에 실패"):
        plan_recent_holdout_manifests(
            snapshots,
            manifest_created_at="2026-04-10T12:00:00+09:00",
            holdout_minimum_race_count=4,
            mini_val_minimum_race_count=4,
        )


def test_write_split_manifests_persists_schema_payloads(tmp_path: Path) -> None:
    snapshots = []
    for race_date in ("20250101", "20250102", "20250103", "20250104"):
        snapshots.append(_make_snapshot(race_date, 1, 1))
        snapshots.append(_make_snapshot(race_date, 3, 1))

    manifests = plan_recent_holdout_manifests(
        snapshots,
        manifest_created_at="2026-04-10T12:00:00+09:00",
        holdout_minimum_race_count=4,
        mini_val_minimum_race_count=2,
    )

    written = write_split_manifests(manifests, output_dir=tmp_path)

    holdout_payload = json.loads(written["holdout"].read_text())
    mini_val_payload = json.loads(written["mini_val"].read_text())

    assert holdout_payload["parameters"]["dataset"] == "holdout"
    assert mini_val_payload["parameters"]["dataset"] == "mini_val"
    assert holdout_payload["metadata"]["seed"]["selection_seed_invariant"] is True
    assert set(holdout_payload["race_input_snapshot_map"]) == set(
        holdout_payload["included_race_ids"]
    )
    assert holdout_payload["race_input_snapshot_map"]["20250103_1_1"][
        "snapshot_id"
    ].startswith("holdout-input-v1:")
    assert (
        holdout_payload["race_input_snapshot_map"]["20250103_1_1"][
            "snapshot_generation_basis"
        ]["selected_timestamp_field"]
        == "basic_data.collected_at"
    )
    assert holdout_payload["manifest_sha256"]
