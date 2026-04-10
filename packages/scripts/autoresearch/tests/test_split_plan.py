from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.autoresearch_config_schema import (  # noqa: E402
    AUTORESEARCH_CONFIG_VERSION,
    default_experiment_payload,
)
from shared.read_contract import RaceKey, RaceSnapshot  # noqa: E402

from autoresearch.split_plan import (  # noqa: E402
    build_execution_matrix_from_config,
    build_temporal_split_plan,
    plan_recent_holdout_manifests_from_config,
)


def _build_config(
    *,
    holdout_minimum_race_count: int = 4,
    mini_val_minimum_race_count: int = 2,
) -> dict:
    return {
        "format_version": AUTORESEARCH_CONFIG_VERSION,
        "dataset": "full_year_2025",
        "split": {
            "train_end": "20250930",
            "dev_end": "20251130",
            "test_start": "20251201",
        },
        "rolling_windows": [
            {
                "name": "fold_a",
                "train_end": "20250731",
                "eval_start": "20250801",
                "eval_end": "20250930",
            },
            {
                "name": "fold_b",
                "train_end": "20250930",
                "eval_start": "20251001",
                "eval_end": "20251130",
            },
        ],
        "evaluation_contract": {
            "same_source_data_required": True,
            "selection_method": "time_ordered_complete_date_accumulation",
            "boundary_unit": "race_date",
            "minimum_holdout_race_count": holdout_minimum_race_count,
            "minimum_mini_val_race_count": mini_val_minimum_race_count,
            "require_complete_race_dates": True,
            "allow_intra_day_cut": False,
            "selection_seed_invariant": True,
            "active_runner_rule": "candidate_filter_minimum_info_fallback_v1",
            "target_label": "unordered_top3",
            "holdout_rule_version": "recent-holdout-split-rule-v1",
            "entry_finalization_rule_version": "holdout-entry-finalization-rule-v1",
            "strict_dataset_selector": "include_in_strict_dataset_true",
            "excluded_replay_statuses": [
                "late_snapshot_unusable",
                "missing_timestamp",
                "partial_snapshot",
            ],
            "excluded_race_reasons": [
                "insufficient_active_runners",
                "invalid_top3_result",
                "late_snapshot_unusable",
                "leakage_violation",
                "missing_basic_data",
                "missing_result_data",
                "partial_snapshot",
                "payload_conversion_failed",
                "top3_not_in_active_runners",
            ],
        },
        "model": {
            "kind": "hgb",
            "positive_class_weight": 1.0,
            "params": {"max_depth": 6},
        },
        "experiment": default_experiment_payload(),
        "features": ["rating", "wgBudam"],
        "notes": {"goal": "test"},
    }


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
        basic_data=_make_basic_data(race_date, race_number, starters=starters),
        result_data={"top3": list(top3)},
        collected_at="2025-01-01T10:30:00+09:00",
        updated_at="2025-01-01T10:31:00+09:00",
    )


def test_build_temporal_split_plan_uses_declared_boundaries_and_seed_rules() -> None:
    config = _build_config()
    dates = (
        "20250730",
        "20250815",
        "20250930",
        "20251015",
        "20251130",
        "20251201",
        "20251215",
    )

    plan = build_temporal_split_plan(
        dates,
        config=config,
        evaluation_seeds=(101, 103, 107, 109, 113, 127, 131, 137, 139, 149),
    )

    assert plan.primary_split.train_indices == (0, 1, 2)
    assert plan.primary_split.dev_indices == (3, 4)
    assert plan.primary_split.test_indices == (5, 6)
    assert [window.name for window in plan.rolling_windows] == ["fold_a", "fold_b"]
    assert plan.rolling_windows[0].train_indices == (0,)
    assert plan.rolling_windows[0].eval_indices == (1, 2)
    assert plan.execution_matrix.evaluation_seeds == (
        101,
        103,
        107,
        109,
        113,
        127,
        131,
        137,
        139,
        149,
    )
    assert plan.execution_matrix.holdout.selection_seed_invariant is True


def test_build_temporal_split_plan_rejects_empty_partition() -> None:
    config = _build_config()
    dates = ("20250730", "20250815", "20250930")

    with pytest.raises(ValueError, match="primary\\(dev\\) eval 구간이 비어 있습니다."):
        build_temporal_split_plan(dates, config=config)


def test_build_execution_matrix_from_config_rejects_invalid_seed_count() -> None:
    config = _build_config()

    with pytest.raises(ValueError, match="정확히 10개"):
        build_execution_matrix_from_config(
            config,
            evaluation_seeds=(11, 17, 23),
        )


def test_build_execution_matrix_from_config_uses_config_experiment_seeds_by_default() -> (
    None
):
    config = _build_config()
    config["experiment"]["evaluation_seeds"] = [
        71,
        73,
        79,
        83,
        89,
        97,
        101,
        103,
        107,
        109,
    ]

    execution_matrix = build_execution_matrix_from_config(config)

    assert execution_matrix.evaluation_seeds == (
        71,
        73,
        79,
        83,
        89,
        97,
        101,
        103,
        107,
        109,
    )


def test_plan_recent_holdout_manifests_from_config_uses_contract_counts_and_seed_rules() -> (
    None
):
    config = _build_config(
        holdout_minimum_race_count=4,
        mini_val_minimum_race_count=2,
    )
    snapshots = []
    for race_date in ("20250101", "20250102", "20250103", "20250104"):
        snapshots.append(_make_snapshot(race_date, 1, 1))
        snapshots.append(_make_snapshot(race_date, 3, 1))

    manifests = plan_recent_holdout_manifests_from_config(
        snapshots,
        config=config,
        manifest_created_at="2026-04-10T12:00:00+09:00",
        evaluation_seeds=(71, 73, 79, 83, 89, 97, 101, 103, 107, 109),
    )

    assert manifests["holdout"].parameters.minimum_race_count == 4
    assert manifests["mini_val"].parameters.minimum_race_count == 2
    assert manifests["holdout"].metadata.seed.evaluation_seeds == (
        71,
        73,
        79,
        83,
        89,
        97,
        101,
        103,
        107,
        109,
    )
    assert manifests["holdout"].metadata.seed.selection_seed is None
