from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.feature_source_timing_contract import FeatureSourceTimingRow  # noqa: E402
from shared.prediction_input_schema import (  # noqa: E402
    ALTERNATIVE_RANKING_ALLOWED_AS_OF_REQUIREMENTS,
    ALTERNATIVE_RANKING_ALLOWED_FEATURES,
    ALTERNATIVE_RANKING_BLOCKED_FEATURES,
    ALTERNATIVE_RANKING_COLUMN_SPEC_BY_NAME,
    ALTERNATIVE_RANKING_DATASET_METADATA_VERSION,
    ALTERNATIVE_RANKING_FORBIDDEN_AS_OF_REQUIREMENTS,
    ALTERNATIVE_RANKING_FORBIDDEN_JOIN_SCOPES,
    ALTERNATIVE_RANKING_INPUT_SCHEMA_VERSION,
    alternative_ranking_input_schema,
    build_alternative_ranking_dataset_metadata,
    build_alternative_ranking_rows_for_race,
    normalize_alternative_ranking_row,
    validate_alternative_ranking_dataset_metadata,
    validate_alternative_ranking_dataset_rows,
    validate_alternative_ranking_feature_names,
    validate_alternative_ranking_race_payload,
    validate_alternative_ranking_row,
    validate_prediction_input_source_contract,
)


def _base_row() -> dict[str, object]:
    row = {
        "race_id": "20250101_1_1",
        "race_date": "20250101",
        "chulNo": 1,
        "target": 1,
    }
    row.update(dict.fromkeys(ALTERNATIVE_RANKING_ALLOWED_FEATURES))
    return row


def test_alternative_ranking_schema_is_fixed_to_operational_subset() -> None:
    schema = alternative_ranking_input_schema()

    assert schema["schema_version"] == ALTERNATIVE_RANKING_INPUT_SCHEMA_VERSION
    assert (
        schema["timing_contract_path"]
        == "data/contracts/feature_source_timing_contract_v1.csv"
    )
    assert len(ALTERNATIVE_RANKING_ALLOWED_FEATURES) == 65
    assert len(ALTERNATIVE_RANKING_BLOCKED_FEATURES) == 5
    assert (
        set(schema["allowed_as_of_requirements"])
        == ALTERNATIVE_RANKING_ALLOWED_AS_OF_REQUIREMENTS
    )
    assert (
        set(schema["forbidden_as_of_requirements"])
        == ALTERNATIVE_RANKING_FORBIDDEN_AS_OF_REQUIREMENTS
    )
    assert (
        set(schema["forbidden_join_scopes"])
        == ALTERNATIVE_RANKING_FORBIDDEN_JOIN_SCOPES
    )
    assert [rule["rule_id"] for rule in schema["validation_rules"]] == [
        "allowlist_columns_only",
        "feature_type_contract",
        "missing_value_policy",
        "forbid_hold_block_label_meta_features",
        "forbid_unregistered_derived_features",
        "single_canonical_source_owner",
        "forbid_timing_unverified_or_postrace_sources",
        "forbid_postrace_feedback_joins",
        "derived_feature_scope_is_fixed",
    ]
    assert len(schema["column_specs"]) == len(ALTERNATIVE_RANKING_ALLOWED_FEATURES) + 4
    assert ALTERNATIVE_RANKING_COLUMN_SPEC_BY_NAME["rating"].dtype == "float"
    assert ALTERNATIVE_RANKING_COLUMN_SPEC_BY_NAME["rating"].missing_rule == "allow_nan"
    assert (
        ALTERNATIVE_RANKING_COLUMN_SPEC_BY_NAME["draw_rr"].derivation_scope
        == "race_relative_derived"
    )
    assert (
        ALTERNATIVE_RANKING_COLUMN_SPEC_BY_NAME["horse_skill_rank"].derivation_scope
        == "same_race_derived"
    )
    assert ALTERNATIVE_RANKING_COLUMN_SPEC_BY_NAME["race_id"].dtype == "text"
    assert ALTERNATIVE_RANKING_COLUMN_SPEC_BY_NAME["target"].dtype == "binary"
    assert set(ALTERNATIVE_RANKING_BLOCKED_FEATURES) == {
        "winOdds",
        "plcOdds",
        "odds_rank",
        "winOdds_rr",
        "plcOdds_rr",
    }


def test_validate_alternative_ranking_feature_names_rejects_duplicates_and_hold() -> (
    None
):
    with pytest.raises(ValueError) as exc_info:
        validate_alternative_ranking_feature_names(["rating", "rating", "winOdds"])

    message = str(exc_info.value)
    assert "Duplicate" in message or "Non-operational" in message

    with pytest.raises(ValueError) as hold_exc:
        validate_alternative_ranking_feature_names(["rating", "winOdds"])

    assert "Non-operational" in str(hold_exc.value)
    assert "winOdds" in str(hold_exc.value)


def test_validate_alternative_ranking_row_rejects_blocked_and_missing_columns() -> None:
    row = _base_row()
    row["winOdds"] = 3.2

    with pytest.raises(ValueError) as blocked_exc:
        validate_alternative_ranking_row(row, require_label=True)

    assert "disallowed" in str(blocked_exc.value)
    assert "winOdds" in str(blocked_exc.value)

    missing = _base_row()
    missing.pop("rating")

    with pytest.raises(ValueError) as missing_exc:
        validate_alternative_ranking_row(missing, require_label=True)

    assert "missing declared allowed features" in str(missing_exc.value)
    assert "rating" in str(missing_exc.value)


def test_validate_alternative_ranking_row_rejects_unregistered_derived_feature() -> (
    None
):
    row = _base_row()
    row["synthetic_leak_signal"] = 1.0

    with pytest.raises(ValueError) as exc_info:
        validate_alternative_ranking_row(row, require_label=True)

    assert "unknown feature keys" in str(exc_info.value)
    assert "synthetic_leak_signal" in str(exc_info.value)


def test_validate_alternative_ranking_row_rejects_hold_derived_feature_residue() -> (
    None
):
    row = _base_row()
    row["odds_rank"] = 1.0

    with pytest.raises(ValueError) as exc_info:
        validate_alternative_ranking_row(row, require_label=True)

    message = str(exc_info.value)
    assert "disallowed" in message
    assert "odds_rank" in message


def test_validate_alternative_ranking_row_accepts_complete_operational_row() -> None:
    row = _base_row()

    validate_alternative_ranking_row(row, require_label=True)


def test_normalize_alternative_ranking_row_coerces_numeric_types_and_nans() -> None:
    row = _base_row()
    row["chulNo"] = "7"
    row["target"] = True
    row["rating"] = "82.5"
    row["trainer_win_rate"] = None

    normalized = normalize_alternative_ranking_row(row, require_label=True)

    assert normalized["chulNo"] == 7
    assert normalized["target"] == 1
    assert normalized["rating"] == 82.5
    assert normalized["trainer_win_rate"] != normalized["trainer_win_rate"]


def test_validate_alternative_ranking_row_rejects_invalid_context_and_feature_types() -> (
    None
):
    row = _base_row()
    row["race_id"] = ""
    row["rating"] = "not-a-number"

    with pytest.raises(ValueError) as exc_info:
        validate_alternative_ranking_row(row, require_label=True)

    message = str(exc_info.value)
    assert "race_id must be non-empty text" in message
    assert "rating must be numeric or missing" in message


def test_validate_alternative_ranking_dataset_rows_reports_row_context() -> None:
    rows = [_base_row(), _base_row()]
    rows[1]["race_id"] = "20250101_1_2"
    rows[1].pop("rating")

    with pytest.raises(ValueError) as exc_info:
        validate_alternative_ranking_dataset_rows(rows, require_label=True)

    message = str(exc_info.value)
    assert "dataset row validation failed" in message
    assert "race_id=20250101_1_2" in message
    assert "rating" in message


def test_build_alternative_ranking_dataset_metadata_embeds_canonical_contract() -> None:
    metadata = build_alternative_ranking_dataset_metadata(
        source="unit-test",
        dataset_name="holdout",
        requested_limit=10,
        race_ids=["race-1", "race-2"],
        with_past_stats=False,
    )

    assert (
        metadata["dataset_metadata_version"]
        == ALTERNATIVE_RANKING_DATASET_METADATA_VERSION
    )
    assert (
        metadata["feature_schema_version"] == ALTERNATIVE_RANKING_INPUT_SCHEMA_VERSION
    )
    assert metadata["race_count"] == 2
    assert (
        metadata["input_schema_contract"]["schema_version"]
        == ALTERNATIVE_RANKING_INPUT_SCHEMA_VERSION
    )


def test_validate_alternative_ranking_dataset_metadata_rejects_mismatched_contract() -> (
    None
):
    metadata = build_alternative_ranking_dataset_metadata(
        source="unit-test",
        dataset_name="holdout",
        requested_limit=None,
        race_ids=["race-1"],
        with_past_stats=False,
    )
    metadata["feature_schema_version"] = "race-eval-v1"

    with pytest.raises(ValueError) as exc_info:
        validate_alternative_ranking_dataset_metadata(metadata)

    assert "feature_schema_version must be" in str(exc_info.value)


def test_validate_prediction_input_source_contract_rejects_hold_feature_owner() -> None:
    with pytest.raises(ValueError) as exc_info:
        validate_prediction_input_source_contract(["winOdds"])

    message = str(exc_info.value)
    assert "entry_card_market_odds" in message
    assert "TIMING_UNVERIFIED" in message


def test_validate_prediction_input_source_contract_rejects_postrace_feedback_join_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from shared import prediction_input_schema as schema_module

    owner = FeatureSourceTimingRow(
        source_block_id="synthetic_postrace_join",
        source_system="INTERNAL_DERIVED",
        source_object="joined postrace feedback",
        storage_path="races.enriched_data.horses[].computed_features.synthetic",
        grain="race_entry",
        source_columns=("horse_top3_skill",),
        join_keys="race_id + chulNo",
        join_scope="postrace_feedback",
        output_fields=("prediction_input.horse_top3_skill",),
        availability_stage="L0",
        as_of_requirement="DIRECT_PRE_RACE",
        late_update_rule="none",
        train_inference_flag="ALLOW",
        operational_status="허용",
        evidence_refs=("tests",),
    )
    monkeypatch.setattr(
        schema_module,
        "rows_for_output_field",
        lambda output_field: (owner,)
        if output_field == "prediction_input.horse_top3_skill"
        else (),
    )

    with pytest.raises(ValueError) as exc_info:
        schema_module.validate_prediction_input_source_contract(["horse_top3_skill"])

    message = str(exc_info.value)
    assert "synthetic_postrace_join" in message
    assert "postrace_feedback" in message


def test_validate_prediction_input_source_contract_accepts_pre_race_join_owner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from shared import prediction_input_schema as schema_module

    owner = FeatureSourceTimingRow(
        source_block_id="synthetic_pre_race_join",
        source_system="INTERNAL_DERIVED",
        source_object="joined prereace snapshot",
        storage_path="races.enriched_data.horses[].computed_features.synthetic",
        grain="race_entry",
        source_columns=("horse_top3_skill",),
        join_keys="race_id + chulNo",
        join_scope="same_race_aggregate",
        output_fields=("prediction_input.horse_top3_skill",),
        availability_stage="L0",
        as_of_requirement="DIRECT_PRE_RACE",
        late_update_rule="recompute on locked prereace snapshot only",
        train_inference_flag="ALLOW",
        operational_status="허용",
        evidence_refs=("tests",),
    )
    monkeypatch.setattr(
        schema_module,
        "rows_for_output_field",
        lambda output_field: (owner,)
        if output_field == "prediction_input.horse_top3_skill"
        else (),
    )

    schema_module.validate_prediction_input_source_contract(["horse_top3_skill"])


def test_validate_prediction_input_source_contract_accepts_operational_feature_owner() -> (
    None
):
    validate_prediction_input_source_contract(["rating", "training_score"])


def test_validate_alternative_ranking_race_payload_rejects_canonical_alias_mismatches() -> (
    None
):
    race = {
        "race_id": "20250101_1_1",
        "race_date": "20250101",
        "raceInfo": {
            "rcDate": "20250101",
            "rcNo": 1,
            "rcDist": 1200,
            "weather": "맑음",
            "track": "건조 (5%)",
            "meet": "서울",
        },
        "horses": [
            {
                "chulNo": 1,
                "rank": "국6등급",
                "computed_features": {},
            }
        ],
    }

    with pytest.raises(ValueError) as exc_info:
        validate_alternative_ranking_race_payload(race)

    message = str(exc_info.value)
    assert "raceInfo -> race_info" in message
    assert "horses[].rank -> horses[].class_rank" in message


def test_validate_alternative_ranking_race_payload_rejects_unexpected_computed_features() -> (
    None
):
    race = {
        "race_id": "20250101_1_1",
        "race_date": "20250101",
        "race_info": {
            "rcDate": "20250101",
            "rcNo": 1,
            "rcDist": 1200,
            "weather": "맑음",
            "track": "건조 (5%)",
            "meet": "서울",
            "budam": "별정A",
        },
        "horses": [
            {
                "chulNo": 1,
                "hrNo": "001",
                "hrName": "A",
                "age": 4,
                "sex": "수",
                "rating": 82,
                "class_rank": "국6등급",
                "wgBudam": 55,
                "wgHr": "490(+1)",
                "computed_features": {
                    "horse_win_rate": 22.0,
                    "horse_place_rate": 44.0,
                    "age_prime": True,
                    "synthetic_leak_signal": 1.0,
                },
            }
        ],
    }

    with pytest.raises(ValueError) as exc_info:
        validate_alternative_ranking_race_payload(race)

    message = str(exc_info.value)
    assert "unexpected computed_features fields" in message
    assert "synthetic_leak_signal" in message


def test_build_alternative_ranking_rows_for_race_generates_complete_inference_rows() -> (
    None
):
    race = {
        "race_id": "20250101_1_1",
        "race_date": "20250101",
        "race_info": {
            "rcDate": "20250101",
            "rcNo": 1,
            "rcDist": 1200,
            "weather": "맑음",
            "track": "건조 (5%)",
            "budam": "별정A",
        },
        "horses": [
            {
                "chulNo": 1,
                "hrNo": "001",
                "hrName": "A",
                "age": 4,
                "sex": "수",
                "rating": 82,
                "wgBudam": 55,
                "wgHr": "490(+1)",
                "computed_features": {
                    "horse_win_rate": 22.0,
                    "horse_place_rate": 44.0,
                    "rating_rank": 1,
                    "age_prime": True,
                },
            },
            {
                "chulNo": 2,
                "hrNo": "002",
                "hrName": "B",
                "age": 3,
                "sex": "암",
                "rating": 77,
                "wgBudam": 53,
                "wgHr": "470(-1)",
                "computed_features": {
                    "horse_win_rate": 18.0,
                    "horse_place_rate": 35.0,
                    "rating_rank": 2,
                    "age_prime": False,
                },
            },
        ],
    }

    rows = build_alternative_ranking_rows_for_race(race, validate_rows=True)

    assert len(rows) == 2
    assert set(rows[0]) == {
        "race_id",
        "race_date",
        "chulNo",
        *ALTERNATIVE_RANKING_ALLOWED_FEATURES,
    }
    assert rows[0]["race_id"] == "20250101_1_1"
    assert rows[0]["draw_rr"] == 0.0
    assert rows[1]["draw_rr"] == 1.0
