from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.prerace_field_policy import (
    ALLOW,
    ALLOW_SNAPSHOT_ONLY,
    ALLOW_STORED_ONLY,
    BLOCK,
    FINAL_BLOCKED_LEAF_FIELDS,
    FINAL_BLOCKED_PREFIX_PATHS,
    FINAL_HOLD_FIELD_PATHS,
    FINAL_LABEL_ONLY_FIELD_PATHS,
    FINAL_LABEL_ONLY_PREFIX_PATHS,
    FINAL_META_ONLY_PREFIX_PATHS,
    HOLD,
    LABEL_ONLY,
    META_ONLY,
    filter_prerace_payload,
    resolve_train_inference_flag,
    validate_operational_dataset_payload,
)


def test_resolve_train_inference_flag_matches_core_policy_groups():
    assert resolve_train_inference_flag("horses[0].rank") == ALLOW
    assert resolve_train_inference_flag("race_plan.rank") == ALLOW
    assert resolve_train_inference_flag("horses[0].winOdds") == HOLD
    assert resolve_train_inference_flag("horses[0].computed_features.odds_rank") == HOLD
    assert resolve_train_inference_flag("track.weather") == ALLOW_SNAPSHOT_ONLY
    assert (
        resolve_train_inference_flag("horses[0].training.remkTxt")
        == ALLOW_SNAPSHOT_ONLY
    )
    assert (
        resolve_train_inference_flag("horses[0].jkDetail.winRateT") == ALLOW_STORED_ONLY
    )
    assert resolve_train_inference_flag("race_odds.total_sales") == BLOCK
    assert resolve_train_inference_flag("horses[0].result") == BLOCK
    assert resolve_train_inference_flag("horses[0].payout") == BLOCK
    assert resolve_train_inference_flag("horses[0].sjG1fOrd") == BLOCK
    assert resolve_train_inference_flag("snapshot_meta.replay_status") == META_ONLY
    assert resolve_train_inference_flag("source_field_tags.summary") == META_ONLY
    assert resolve_train_inference_flag("horses[0].hrName") == ALLOW


def test_filter_prerace_payload_removes_hold_block_and_meta_fields():
    payload = {
        "race_info": {"rcDate": "20250101", "weather": "맑음"},
        "track": {"weather": "맑음"},
        "horses": [
            {
                "chulNo": 1,
                "hrName": "테스트마",
                "winOdds": 3.2,
                "plcOdds": 1.5,
                "sjG1fOrd": 2,
                "jkDetail": {"winRateT": 11},
                "training": {"remkTxt": "양호"},
                "computed_features": {
                    "odds_rank": 1,
                    "horse_win_rate": 20.5,
                    "training_score": 1,
                },
            }
        ],
        "snapshot_meta": {"replay_status": "strict"},
        "source_field_tags": {"summary": {"post_entry_field_count": 1}},
        "race_odds": {"win": [1.2, 2.4]},
    }

    filtered, report = filter_prerace_payload(payload)

    horse = filtered["horses"][0]
    assert "winOdds" not in horse
    assert "plcOdds" not in horse
    assert "sjG1fOrd" not in horse
    assert "odds_rank" not in horse["computed_features"]
    assert horse["computed_features"]["horse_win_rate"] == 20.5
    assert horse["computed_features"]["training_score"] == 1
    assert filtered["track"]["weather"] == "맑음"
    assert "race_odds" not in filtered
    assert "snapshot_meta" not in filtered
    assert "source_field_tags" not in filtered
    assert report["encountered_flag_counts"][HOLD] >= 3
    assert "horses[].winOdds" in report["removed_by_flag"][HOLD]
    assert "horses[].sjG1fOrd" in report["removed_by_flag"][BLOCK]
    assert "race_odds" in report["removed_by_flag"][BLOCK]
    assert "snapshot_meta" in report["removed_by_flag"][META_ONLY]
    assert "source_field_tags" in report["removed_by_flag"][META_ONLY]


def test_filter_prerace_payload_can_keep_hold_fields_for_research_only():
    payload = {
        "horses": [
            {
                "chulNo": 1,
                "winOdds": 3.2,
                "computed_features": {"odds_rank": 1},
            }
        ]
    }

    filtered, report = filter_prerace_payload(payload, include_hold=True)

    assert filtered["horses"][0]["winOdds"] == 3.2
    assert filtered["horses"][0]["computed_features"]["odds_rank"] == 1
    assert report["removed_by_flag"][HOLD] == []


def test_final_operational_block_catalog_is_explicit_and_stable():
    assert FINAL_HOLD_FIELD_PATHS == {
        "horses[].win_odds",
        "horses[].plc_odds",
        "horses[].computed_features.odds_rank",
    }
    assert FINAL_BLOCKED_LEAF_FIELDS == {
        "ord",
        "ordBigo",
        "rankRise",
        "diffUnit",
        "rcTime",
        "result",
        "resultTime",
        "finish_position",
        "dividend",
        "payout",
    }
    assert FINAL_BLOCKED_PREFIX_PATHS == {"race_odds"}
    assert FINAL_LABEL_ONLY_FIELD_PATHS == {"top3", "is_top3", "actual_result"}
    assert FINAL_LABEL_ONLY_PREFIX_PATHS == {"result_data"}
    assert FINAL_META_ONLY_PREFIX_PATHS == {
        "snapshot_meta",
        "field_policy",
        "source_field_tags",
    }


def test_validate_operational_dataset_payload_reports_blocking_checklist():
    payload = {
        "horses": [
            {
                "chulNo": 1,
                "hrName": "테스트마",
                "winOdds": 3.2,
                "result": "1",
                "computed_features": {"odds_rank": 1},
            }
        ],
        "result_data": {"top3": [1, 2, 3]},
        "snapshot_meta": {"replay_status": "strict"},
        "race_odds": {"win": [1.2, 2.4]},
    }

    report = validate_operational_dataset_payload(payload)

    assert report["passed"] is False
    assert "horses[].winOdds" in report["violations_by_flag"][HOLD]
    assert "horses[].result" in report["violations_by_flag"][BLOCK]
    assert "result_data" in report["violations_by_flag"][LABEL_ONLY]
    assert "snapshot_meta" in report["violations_by_flag"][META_ONLY]
    checklist = {item["flag"]: item for item in report["checklist"]}
    assert checklist["ALL"]["passed"] is False
    assert checklist[HOLD]["passed"] is False
    assert checklist[BLOCK]["passed"] is False
    assert checklist[LABEL_ONLY]["passed"] is False
    assert checklist[META_ONLY]["passed"] is False


def test_validate_operational_dataset_payload_passes_for_filtered_payload():
    payload = {
        "horses": [
            {
                "chulNo": 1,
                "hrName": "테스트마",
                "winOdds": 3.2,
                "training": {"remkTxt": "양호"},
                "computed_features": {"horse_win_rate": 20.5, "odds_rank": 1},
            }
        ],
        "track": {"weather": "맑음"},
        "snapshot_meta": {"replay_status": "strict"},
    }

    filtered, _ = filter_prerace_payload(payload)
    report = validate_operational_dataset_payload(filtered)

    assert report["passed"] is True
    assert report["violations_by_flag"] == {}
    assert all(item["passed"] is True for item in report["checklist"])
