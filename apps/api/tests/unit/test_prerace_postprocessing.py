from __future__ import annotations

import pytest

from services.prerace_postprocessing import (
    normalize_and_validate_prerace_payload,
    normalize_prerace_payload,
    validate_prerace_payload,
)
from services.prerace_storage_policy import (
    audit_prerace_storage_result,
    split_prerace_payload_for_storage,
)

pytestmark = pytest.mark.unit


def _make_race_info(items):
    item_list = items if isinstance(items, list) else [items]
    return {
        "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE."},
            "body": {
                "items": {"item": item_list},
                "numOfRows": len(item_list),
                "pageNo": 1,
                "totalCount": len(item_list),
            },
        }
    }


def _valid_payload() -> dict:
    items = [
        {
            "rcDate": "20260405",
            "rcNo": "3",
            "meet": "서울",
            "chulNo": 2,
            "hrNo": "002",
            "hrName": "말2",
            "jkNo": "J02",
            "jkName": "기수2",
            "trNo": "T02",
            "trName": "조교사2",
            "owNo": "O02",
            "owName": "마주2",
            "age": 4,
            "sex": "암",
            "name": "한국",
            "rank": "국6등급",
            "rating": 29,
            "wgBudam": 53.5,
            "wgBudamBigo": "*",
            "wgHr": "452(-3)",
            "winOdds": 6.8,
            "plcOdds": 2.1,
        },
        {
            "rcDate": "20260405",
            "rcNo": "3",
            "meet": "서울",
            "chulNo": 1,
            "hrNo": "001",
            "hrName": "말1",
            "jkNo": "J01",
            "jkName": "기수1",
            "trNo": "T01",
            "trName": "조교사1",
            "owNo": "O01",
            "owName": "마주1",
            "age": 3,
            "sex": "수",
            "name": "한국",
            "rank": "국6등급",
            "rating": 31,
            "wgBudam": 55,
            "wgBudamBigo": "-",
            "wgHr": "470(+2)",
            "winOdds": 3.4,
            "plcOdds": 1.4,
        },
    ]
    return {
        "race_date": "20260405",
        "race_no": 3,
        "date": "20260405",
        "meet": 1,
        "race_number": 3,
        "race_info": _make_race_info(items),
        "race_plan": {
            "rank": "국6등급",
            "budam": "별정A",
            "rcDist": "1200",
            "ageCond": "연령오픈",
            "schStTime": "1450",
        },
        "track": {
            "weather": "맑음",
            "track": "건조",
            "waterPercent": "4",
        },
        "cancelled_horses": [{"rcDate": "20260405", "rcNo": "3", "chulNo": "9"}],
        "horses": [
            {
                "chul_no": 2,
                "hr_no": "002",
                "hr_name": "말2",
                "jk_no": "J02",
                "jk_name": "기수2",
                "tr_no": "T02",
                "tr_name": "조교사2",
                "ow_no": "O02",
                "ow_name": "마주2",
                "age": "4",
                "sex": "암",
                "country": "한국",
                "class_rank": "국6등급",
                "rating": "29",
                "wg_budam": "53.5",
                "wg_budam_bigo": "*",
                "wg_hr": "452(-3)",
                "win_odds": "6.8",
                "plc_odds": "2.1",
            },
            {
                "chulNo": 1,
                "hrNo": "001",
                "hrName": "말1",
                "jkNo": "J01",
                "jkName": "기수1",
                "trNo": "T01",
                "trName": "조교사1",
                "owNo": "O01",
                "owName": "마주1",
                "age": 3,
                "sex": "수",
                "name": "한국",
                "rank": "국6등급",
                "rating": 31,
                "wgBudam": 55,
                "wgBudamBigo": "-",
                "wgHr": "470(+2)",
                "winOdds": 3.4,
                "plcOdds": 1.4,
                "hrDetail": {"birth": "2021-03-01"},
            },
        ],
        "failed_horses": [],
        "status": "success",
        "collected_at": "2026-04-10T09:00:00+09:00",
    }


def test_normalize_and_validate_prerace_payload_canonicalizes_payload():
    normalized = normalize_and_validate_prerace_payload(_valid_payload())

    assert normalized["schema_version"] == "prerace-source-v1"
    assert normalized["race_plan"]["rc_dist"] == 1200
    assert normalized["race_plan"]["sch_st_time"] == "1450"
    assert normalized["track"]["water_percent"] == 4
    assert normalized["cancelled_horses"][0]["chul_no"] == 9
    assert [horse["chul_no"] for horse in normalized["horses"]] == [1, 2]
    assert normalized["horses"][0]["weight"] == 470
    assert normalized["horses"][0]["hrDetail"] == {"birth": "2021-03-01"}
    assert normalized["horses"][0]["jkDetail"] == {}
    assert set(normalized["horses"][0]["normalization_flags"]) == {
        "budam_note_missing",
        "hr_tool_missing",
        "jkdetail_missing",
        "jkstats_missing",
        "ilsu_missing",
        "owdetail_missing",
        "training_missing",
        "trdetail_missing",
    }
    assert normalized["horses"][1]["name"] == "한국"
    assert normalized["horses"][1]["country"] == "한국"
    assert normalized["horses"][1]["training"] == {}
    assert normalized["snapshot_meta"]["format_version"] == "holdout-snapshot-v1"
    assert (
        normalized["snapshot_meta"]["selected_timestamp_field"]
        == "basic_data.collected_at"
    )
    assert normalized["snapshot_meta"]["timestamp_source"] == "snapshot_collected_at"
    assert normalized["snapshot_meta"]["replay_status"] == "late_snapshot_unusable"
    assert (
        normalized["snapshot_meta"]["hard_required_source_status"]["API72_2"]
        == "present"
    )


def test_normalize_prerace_payload_converts_soft_fail_values_to_standard_types():
    payload = _valid_payload()
    payload["horses"][0].update(
        {
            "sex": "M",
            "wg_budam_bigo": "-",
            "wg_hr": "-",
            "rating": "0",
            "win_odds": "0",
            "plc_odds": "bad",
            "jkDetail": {"sp_date": "-", "birthday": "1982-02-12"},
            "trDetail": {"age": "-", "birthday": "-"},
        }
    )
    payload["status"] = "partial_failure"
    payload["failed_horses"] = [{"horse_no": "9", "horse_name": "누락마", "error": "x"}]

    normalized = normalize_and_validate_prerace_payload(payload)
    horse = normalized["horses"][1]

    assert horse["sex"] == "수"
    assert horse["wg_budam_bigo"] is None
    assert horse["wg_hr"] is None
    assert horse["weight"] is None
    assert horse["weight_delta"] is None
    assert horse["rating"] == 0
    assert horse["win_odds"] is None
    assert horse["plc_odds"] is None
    assert horse["jkDetail"]["sp_date"] is None
    assert horse["jkDetail"]["birthday"] == "19820212"
    assert horse["trDetail"]["age"] is None
    assert horse["trDetail"]["birthday"] is None
    assert {
        "budam_note_missing",
        "market_signal_missing",
        "odds_parse_failed",
        "popularity_unusable",
        "rating_known_false",
        "sex_bucketed",
        "weight_missing",
        "weight_delta_missing",
    } <= set(horse["normalization_flags"])


def test_normalize_prerace_payload_attaches_source_field_tags_for_post_entry_audit():
    payload = _valid_payload()
    payload["race_info"] = _make_race_info(
        [
            {
                **payload["race_info"]["response"]["body"]["items"]["item"][0],
                "ord": 1,
                "diffUnit": "목",
            }
        ]
    )

    normalized = normalize_and_validate_prerace_payload(payload)

    tags = normalized["source_field_tags"]
    race_info_tags = tags["records"]["race_info_items"][0]["field_tags"]
    horse_tags = tags["records"]["horses"][0]["field_tags"]

    assert tags["tag_schema_version"] == "source-field-tags-v1"
    assert tags["summary"]["post_entry_field_count"] >= 2
    assert race_info_tags["ord"]["tag"] == "post_entry_only"
    assert race_info_tags["ord"]["train_inference_flag"] == "BLOCK"
    assert race_info_tags["diffUnit"]["tag"] == "post_entry_only"
    assert race_info_tags["winOdds"]["tag"] == "hold"
    assert race_info_tags["rank"]["tag"] == "pre_entry_allowed"
    assert horse_tags["win_odds"]["tag"] == "hold"
    assert horse_tags["hrDetail"]["tag"] == "stored_only"


def test_normalize_prerace_payload_blocks_joined_rows_created_after_entry_finalized_at():
    payload = _valid_payload()
    payload["entry_finalized_at"] = "2026-04-10T09:00:00+09:00"
    payload["horses"][1]["hrDetail"] = {"birth": "20210301", "cntT": 12}
    payload["horses"][1]["__join_timing__"] = {
        "hrDetail": {"row_created_at": "2026-04-10T09:05:00+09:00"}
    }

    normalized = normalize_and_validate_prerace_payload(payload)
    horse = next(row for row in normalized["horses"] if row["chul_no"] == 1)

    assert horse["hrDetail"] == {}
    assert "hrdetail_blocked_post_entry" in horse["normalization_flags"]
    assert "hrdetail_missing" in horse["normalization_flags"]
    assert normalized["join_timing_audit"]["guard_applied"] is True
    assert normalized["join_timing_audit"]["blocked_target_count"] == 1
    assert normalized["join_timing_audit"]["blocked_targets"][0]["reason_code"] == (
        "join_row_after_entry_finalized_at"
    )


def test_normalize_prerace_payload_blocks_joined_columns_created_after_entry_finalized_at():
    payload = _valid_payload()
    payload["entry_finalized_at"] = "2026-04-10T09:00:00+09:00"
    payload["horses"][1]["training"] = {
        "remkTxt": "양호",
        "late_note": "after cutoff",
    }
    payload["horses"][1]["join_timing"] = {
        "training": {
            "field_created_at": {
                "late_note": "2026-04-10T09:05:00+09:00",
                "remkTxt": "2026-04-10T08:55:00+09:00",
            }
        }
    }

    normalized = normalize_and_validate_prerace_payload(payload)
    horse = next(row for row in normalized["horses"] if row["chul_no"] == 1)
    blocked = normalized["join_timing_audit"]["blocked_targets"][0]

    assert horse["training"] == {"remkTxt": "양호"}
    assert "late_note" not in horse["training"]
    assert "training_fields_blocked_post_entry" in horse["normalization_flags"]
    assert blocked["reason_code"] == "join_fields_after_entry_finalized_at"
    assert blocked["blocked_fields"] == ["late_note"]


def test_normalize_prerace_payload_keeps_joined_data_at_entry_finalized_boundary():
    payload = _valid_payload()
    payload["entry_finalized_at"] = "2026-04-10T09:00:00+09:00"
    payload["horses"][1]["hrDetail"] = {"birth": "20210301", "cntT": 12}
    payload["horses"][1]["training"] = {
        "remkTxt": "양호",
        "gate_note": "same minute",
    }
    payload["horses"][1]["join_timing"] = {
        "hrDetail": {"row_created_at": "2026-04-10T09:00:00+09:00"},
        "training": {
            "field_created_at": {
                "remkTxt": "2026-04-10T09:00:00+09:00",
                "gate_note": "2026-04-10T08:59:59+09:00",
            }
        },
    }

    normalized = normalize_and_validate_prerace_payload(payload)
    horse = next(row for row in normalized["horses"] if row["chul_no"] == 1)

    assert horse["hrDetail"] == {"birth": "20210301", "cntT": 12}
    assert horse["training"] == {"remkTxt": "양호", "gate_note": "same minute"}
    assert "hrdetail_blocked_post_entry" not in horse["normalization_flags"]
    assert "training_fields_blocked_post_entry" not in horse["normalization_flags"]
    assert normalized["join_timing_audit"]["guard_applied"] is True
    assert normalized["join_timing_audit"]["blocked_target_count"] == 0
    assert normalized["join_timing_audit"]["blocked_targets"] == []


def test_normalize_prerace_payload_ignores_invalid_join_timing_timestamps():
    payload = _valid_payload()
    payload["entry_finalized_at"] = "2026-04-10T09:00:00+09:00"
    payload["horses"][1]["hrDetail"] = {"birth": "20210301", "cntT": 12}
    payload["horses"][1]["training"] = {
        "remkTxt": "양호",
        "late_note": "timestamp missing",
    }
    payload["horses"][1]["join_timing"] = {
        "hrDetail": {"row_created_at": "not-a-timestamp"},
        "training": {
            "field_created_at": {
                "late_note": "invalid",
                "remkTxt": "also-invalid",
            }
        },
    }

    normalized = normalize_and_validate_prerace_payload(payload)
    horse = next(row for row in normalized["horses"] if row["chul_no"] == 1)

    assert horse["hrDetail"] == {"birth": "20210301", "cntT": 12}
    assert horse["training"] == {"remkTxt": "양호", "late_note": "timestamp missing"}
    assert "hrdetail_blocked_post_entry" not in horse["normalization_flags"]
    assert "training_fields_blocked_post_entry" not in horse["normalization_flags"]
    assert normalized["join_timing_audit"]["guard_applied"] is True
    assert normalized["join_timing_audit"]["blocked_target_count"] == 0
    assert normalized["join_timing_audit"]["blocked_targets"] == []


def test_split_prerace_payload_for_storage_moves_meta_and_blocked_fields_to_shadow():
    payload = _valid_payload()
    payload["race_info"] = _make_race_info(
        [
            {
                **payload["race_info"]["response"]["body"]["items"]["item"][0],
                "ord": 1,
                "diffUnit": "목",
            }
        ]
    )

    normalized = normalize_and_validate_prerace_payload(payload)
    basic_data, raw_data = split_prerace_payload_for_storage(normalized)

    race_info_item = basic_data["race_info"]["response"]["body"]["items"]["item"][0]

    assert "source_field_tags" not in basic_data
    assert "snapshot_meta" not in basic_data
    assert "ord" not in race_info_item
    assert "diffUnit" not in race_info_item
    assert race_info_item["winOdds"] == 6.8
    assert raw_data["storage_policy_version"] == "prerace-storage-policy-v1"
    assert raw_data["snapshot_meta"]["format_version"] == "holdout-snapshot-v1"
    assert (
        raw_data["snapshot_meta"]["selected_timestamp_field"]
        == "basic_data.collected_at"
    )
    assert raw_data["source_field_tags"]["summary"]["post_entry_field_count"] >= 2
    assert raw_data["tagged_field_shadow"]["race_info_items"][0]["fields"]["ord"] == 1
    assert (
        raw_data["tagged_field_shadow"]["race_info_items"][0]["fields"]["diffUnit"]
        == "목"
    )
    assert (
        raw_data["tagged_field_shadow"]["race_info_items"][0]["fields"]["winOdds"]
        == 6.8
    )


def test_split_prerace_payload_for_storage_keeps_allowed_and_snapshot_fields_in_basic_data():
    payload = _valid_payload()
    payload["race_info"] = _make_race_info(
        [
            {
                **payload["race_info"]["response"]["body"]["items"]["item"][1],
                "ord": 1,
                "diffUnit": "목",
            }
        ]
    )
    payload["track"]["temperature"] = "18"
    payload["horses"][1]["hrDetail"] = {"birth": "20210301", "cntT": 12}
    payload["horses"][1]["training"] = {"remkTxt": "양호"}

    normalized = normalize_and_validate_prerace_payload(payload)
    basic_data, raw_data = split_prerace_payload_for_storage(normalized)

    horse = next(row for row in basic_data["horses"] if row["chul_no"] == 1)
    horse_shadow = next(
        row
        for row in raw_data["tagged_field_shadow"]["horses"]
        if row["record_key"] == "1"
    )
    race_info_item = basic_data["race_info"]["response"]["body"]["items"]["item"][0]

    assert basic_data["race_plan"]["sch_st_time"] == "1450"
    assert basic_data["track"]["temperature"] == "18"
    assert horse["hrDetail"] == {"birth": "20210301", "cntT": 12}
    assert horse["training"] == {"remkTxt": "양호"}
    assert race_info_item["rank"] == "국6등급"
    assert "ord" not in race_info_item
    assert raw_data["tagged_field_shadow"]["race_info_items"][0]["fields"]["ord"] == 1
    assert (
        raw_data["tagged_field_shadow"]["race_info_items"][0]["fields"]["winOdds"]
        == 3.4
    )
    assert horse_shadow["fields"]["win_odds"] == 3.4
    assert "hrDetail" not in horse_shadow["fields"]
    assert "training" not in horse_shadow["fields"]
    assert "race_plan" not in raw_data["tagged_field_shadow"]
    assert "track" not in raw_data["tagged_field_shadow"]


def test_split_prerace_payload_for_storage_rejects_fields_without_metadata():
    normalized = normalize_and_validate_prerace_payload(_valid_payload())
    normalized["horses"][0]["mystery_feature"] = 99

    with pytest.raises(
        ValueError, match="horses\\[\\]\\.mystery_feature is missing field metadata"
    ):
        split_prerace_payload_for_storage(normalized)


def test_split_prerace_payload_for_storage_moves_snapshot_meta_to_raw_data():
    normalized = normalize_and_validate_prerace_payload(_valid_payload())
    normalized["snapshot_meta"] = {"replay_status": "strict"}

    basic_data, raw_data = split_prerace_payload_for_storage(normalized)

    assert "snapshot_meta" not in basic_data
    assert raw_data["snapshot_meta"] == {"replay_status": "strict"}


def test_split_prerace_payload_for_storage_rejects_tagged_fields_without_canonical_metadata():
    normalized = normalize_and_validate_prerace_payload(_valid_payload())
    normalized["source_field_tags"]["records"]["horses"][0]["field_tags"]["hr_name"][
        "metadata_rule_found"
    ] = False

    with pytest.raises(
        ValueError, match="horses\\[\\]\\.hr_name is missing field metadata"
    ):
        split_prerace_payload_for_storage(normalized)


def test_audit_prerace_storage_result_reports_missing_field_metadata():
    normalized = normalize_and_validate_prerace_payload(_valid_payload())
    basic_data, raw_data = split_prerace_payload_for_storage(normalized)
    raw_data["source_field_tags"]["records"]["horses"][0]["field_tags"]["hr_name"][
        "metadata_rule_found"
    ] = False

    issues = audit_prerace_storage_result(basic_data, raw_data)

    assert "horses[].hr_name is missing field metadata" in issues


def test_audit_prerace_storage_result_reports_blocked_fields_loaded_in_basic_data():
    normalized = normalize_and_validate_prerace_payload(_valid_payload())
    basic_data, raw_data = split_prerace_payload_for_storage(normalized)
    basic_data["snapshot_meta"] = {"replay_status": "strict"}

    issues = audit_prerace_storage_result(basic_data, raw_data)

    assert "snapshot_meta includes blocked field with flag META_ONLY" in issues


def test_audit_prerace_storage_result_accepts_valid_storage_output():
    normalized = normalize_and_validate_prerace_payload(_valid_payload())
    basic_data, raw_data = split_prerace_payload_for_storage(normalized)

    assert audit_prerace_storage_result(basic_data, raw_data) == []


def test_split_prerace_payload_for_storage_moves_join_timing_audit_to_raw_data():
    payload = _valid_payload()
    payload["entry_finalized_at"] = "2026-04-10T09:00:00+09:00"
    payload["horses"][1]["hrDetail"] = {"birth": "20210301"}
    payload["horses"][1]["join_timing"] = {
        "hrDetail": {"row_created_at": "2026-04-10T09:05:00+09:00"}
    }

    normalized = normalize_and_validate_prerace_payload(payload)
    basic_data, raw_data = split_prerace_payload_for_storage(normalized)

    assert "join_timing_audit" not in basic_data
    assert raw_data["snapshot_meta"]["timestamp_source"] == "source_revision"
    assert raw_data["snapshot_meta"]["timestamp_confidence"] == "high"
    assert (
        raw_data["snapshot_meta"]["entry_finalized_at"] == "2026-04-10T09:00:00+09:00"
    )
    assert raw_data["join_timing_audit"]["blocked_target_count"] == 1
    assert raw_data["join_timing_audit"]["blocked_targets"][0]["target_path"] == (
        "horses[].hrDetail"
    )


def test_validate_prerace_payload_reports_schema_issues():
    payload = normalize_prerace_payload(_valid_payload())
    payload["race_plan"]["rank"] = None
    payload["horses"][1]["hr_name"] = None
    payload["horses"][1]["chul_no"] = payload["horses"][0]["chul_no"]

    issues = validate_prerace_payload(payload)

    assert "race_plan.rank is required" in issues
    assert "horses[2].hr_name is required" in issues
    assert "horses[2].chul_no duplicates another horse" in issues


def test_normalize_and_validate_prerace_payload_raises_for_invalid_payload():
    payload = _valid_payload()
    payload["track"] = {"weather": "맑음"}

    with pytest.raises(ValueError, match="track.track is required"):
        normalize_and_validate_prerace_payload(payload)
