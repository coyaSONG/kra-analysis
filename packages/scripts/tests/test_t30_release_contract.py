from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.prediction_input_schema import PREDICTION_INPUT_NAMES  # noqa: E402
from shared.t30_release_contract import (  # noqa: E402
    T30_RELEASE_FEATURE_BY_NAME,
    T30_RELEASE_FEATURE_SPECS,
    t30_disallowed_overlay_feature_names,
    t30_feature_names_by_bucket,
    t30_release_feature_names,
    validate_t30_release_overlay_features,
)


def test_t30_release_contract_has_unique_features_and_required_buckets() -> None:
    names = [spec.feature_name for spec in T30_RELEASE_FEATURE_SPECS]

    assert len(names) == len(set(names))
    assert set(t30_feature_names_by_bucket("RELEASE")) >= {
        "recent_race_count",
        "recent_win_rate",
        "recent_top3_rate",
        "weight_delta",
        "cancelled_count",
        "field_size_live",
        "changed_jockey_flag",
    }
    assert set(t30_feature_names_by_bucket("BACKFILL_ONLY")) >= {
        "training_score",
        "jk_skill",
        "owner_skill",
        "past_speed_index",
    }
    assert set(t30_feature_names_by_bucket("AUDIT_ONLY")) == {
        "winOdds",
        "plcOdds",
        "odds_rank",
        "winOdds_rr",
        "plcOdds_rr",
    }


def test_t30_release_contract_marks_current_and_planned_model_inputs() -> None:
    current_release = set(t30_release_feature_names(current_model_only=True))

    assert current_release <= set(PREDICTION_INPUT_NAMES)
    assert {
        "recent_race_count",
        "recent_top3_rate",
        "recent_win_rate",
    } <= current_release
    assert "cancelled_count" in current_release
    assert "field_size_live" in current_release
    assert (
        T30_RELEASE_FEATURE_BY_NAME["weight_delta"].model_feature_status
        == "current_model_input"
    )
    assert (
        T30_RELEASE_FEATURE_BY_NAME["changed_jockey_flag"].model_feature_status
        == "planned_nullable"
    )


def test_t30_release_overlay_rejects_audit_and_backfill_features() -> None:
    disallowed = set(t30_disallowed_overlay_feature_names())

    assert {"winOdds", "odds_rank", "training_score", "jk_skill"} <= disallowed

    with pytest.raises(ValueError) as exc_info:
        validate_t30_release_overlay_features(
            ["rating", "recent_top3_rate", "winOdds", "training_score"]
        )

    message = str(exc_info.value)
    assert "winOdds" in message
    assert "AUDIT_ONLY" in message
    assert "training_score" in message
    assert "BACKFILL_ONLY" in message


def test_t30_release_overlay_allows_core_features_and_release_features() -> None:
    validate_t30_release_overlay_features(
        ["rating", "draw_no", "recent_top3_rate", "field_size_live"]
    )
