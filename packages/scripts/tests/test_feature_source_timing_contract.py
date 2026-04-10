from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.feature_source_timing_contract import (  # noqa: E402
    ALL_COLUMNS,
    AS_OF_REQUIREMENTS,
    CANONICAL_STORAGE_ENCODING,
    CANONICAL_STORAGE_RELATIVE_PATH,
    CONTRACT_VERSION,
    FEATURE_SOURCE_TIMING_ROWS,
    JOIN_SCOPES,
    REQUIRED_COLUMNS,
    SOURCE_GRAINS,
    SOURCE_SYSTEMS,
    canonical_feature_source_timing_rows,
    contract_row_by_id,
    covered_prediction_inputs,
    csv_header,
    rows_for_output_field,
)

ROOT = Path(__file__).resolve().parents[3]
PREDICTION_REGISTRY_PATH = (
    ROOT / "data/contracts/prediction_input_field_registry_v1.csv"
)


def _load_prediction_input_names() -> set[str]:
    with PREDICTION_REGISTRY_PATH.open(encoding="utf-8", newline="") as handle:
        return {
            row["prediction_input_name"]
            for row in csv.DictReader(handle)
            if row["prediction_input_name"]
        }


def test_contract_version_is_fixed():
    assert CONTRACT_VERSION == "feature-source-timing-contract-v1"


def test_required_columns_cover_temporal_contract():
    required = set(REQUIRED_COLUMNS)
    assert "source_block_id" in required
    assert "source_columns" in required
    assert "join_keys" in required
    assert "output_fields" in required
    assert "availability_stage" in required
    assert "as_of_requirement" in required
    assert "late_update_rule" in required
    assert "train_inference_flag" in required


def test_enum_sets_remain_explicit():
    assert SOURCE_SYSTEMS == ("KRA_API", "POSTGRES", "INTERNAL_DERIVED")
    assert SOURCE_GRAINS == (
        "race",
        "race_entry",
        "horse",
        "jockey",
        "trainer",
        "owner",
        "race_odds_row",
        "prediction_row",
    )
    assert JOIN_SCOPES == (
        "self_materialized",
        "race_key",
        "horse_id",
        "jockey_id",
        "trainer_id",
        "owner_id",
        "horse_name_fallback",
        "same_race_aggregate",
        "historical_lookup",
        "postrace_feedback",
    )
    assert AS_OF_REQUIREMENTS == (
        "DIRECT_PRE_RACE",
        "PRE_CUTOFF_SNAPSHOT",
        "STORED_AS_OF_SNAPSHOT",
        "HISTORICAL_LOOKBACK_BEFORE_RACE_DATE",
        "TIMING_UNVERIFIED",
        "POSTRACE_ONLY",
    )


def test_contract_rows_cover_core_timing_boundaries():
    assert FEATURE_SOURCE_TIMING_ROWS

    assert contract_row_by_id("entry_card_core").train_inference_flag == "ALLOW"
    assert contract_row_by_id("entry_card_market_odds").train_inference_flag == "HOLD"
    assert (
        contract_row_by_id("entry_card_postrace_fields").train_inference_flag == "BLOCK"
    )
    assert (
        contract_row_by_id("track_snapshot_block").train_inference_flag
        == "ALLOW_SNAPSHOT_ONLY"
    )
    assert (
        contract_row_by_id("horse_detail_history_block").train_inference_flag
        == "ALLOW_STORED_ONLY"
    )
    assert (
        contract_row_by_id("race_plan_cutoff_anchor").train_inference_flag
        == "META_ONLY"
    )
    assert contract_row_by_id("race_odds_postrace_block").availability_stage == "L+1"
    assert contract_row_by_id("historical_result_lookback_block").as_of_requirement == (
        "HISTORICAL_LOOKBACK_BEFORE_RACE_DATE"
    )


def test_every_prediction_input_is_covered_by_temporal_contract():
    registry_names = _load_prediction_input_names()
    assert registry_names == set(covered_prediction_inputs())


def test_rows_for_output_field_returns_expected_sources():
    owners = rows_for_output_field("prediction_input.training_score")
    assert [row.source_block_id for row in owners] == ["training_snapshot_block"]

    market_rows = rows_for_output_field("prediction_input.winOdds")
    assert [row.source_block_id for row in market_rows] == ["entry_card_market_odds"]


def test_csv_template_matches_declared_contract_rows():
    template_path = ROOT / CANONICAL_STORAGE_RELATIVE_PATH
    with template_path.open(encoding=CANONICAL_STORAGE_ENCODING, newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert tuple(rows[0].keys()) == ALL_COLUMNS
    assert csv_header() == ",".join(ALL_COLUMNS)
    assert rows == list(canonical_feature_source_timing_rows())
