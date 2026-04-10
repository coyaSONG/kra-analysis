"""prepare.py 단위 테스트"""

import sys
import tempfile
import textwrap
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

# packages/scripts/ 를 sys.path에 추가 (기존 evaluate_prompt_v3.py와 동일한 패턴)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_find_races_with_results_filters_result_status():
    """find_races_with_results()가 result_status='collected'로 필터링하는지"""
    from shared.db_client import RaceDBClient

    client = RaceDBClient.__new__(RaceDBClient)
    # SQL에 result_status 조건이 포함되는지 확인
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    client._conn = mock_conn

    client.find_races_with_results()

    executed_sql = mock_cursor.execute.call_args[0][0]
    assert "result_status" in executed_sql
    assert "collection_status" in executed_sql


def test_import_guard_blocks_forbidden_imports():
    """금지 모듈 import를 감지하는지"""
    from prepare import check_train_imports

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(
            textwrap.dedent("""\
            import os
            from pathlib import Path
            import json  # 이건 허용
        """)
        )
        f.flush()
        violations = check_train_imports(f.name)

    assert "os" in violations
    assert "pathlib" in violations
    assert "json" not in violations


def test_import_guard_allows_safe_imports():
    """허용된 모듈은 통과하는지"""
    from prepare import check_train_imports

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(
            textwrap.dedent("""\
            import json
            import re
            import math
        """)
        )
        f.flush()
        violations = check_train_imports(f.name)

    assert violations == []


def test_strip_forbidden_fields():
    """forbidden fields가 snapshot에서 제거되는지"""
    from prepare import strip_forbidden_fields

    race_data = {
        "chulNo": 1,
        "hrName": "테스트마",
        "winOdds": 5.0,
        "rank": "국6",  # forbidden → 제거 대상
        "rcTime": "1:23.4",  # forbidden → 제거 대상
    }
    cleaned = strip_forbidden_fields(race_data)
    assert "rank" not in cleaned
    assert "rcTime" not in cleaned
    assert cleaned["chulNo"] == 1
    assert cleaned["hrName"] == "테스트마"


def test_strip_forbidden_fields_removes_ord_bigo_and_sectionals():
    """사후 주석/구간통과 필드도 제거되는지"""
    from prepare import strip_forbidden_fields

    race_data = {
        "ordBigo": "-",
        "sjG1fOrd": 3,
        "nested": {"seG3fAccTime": 37.2},
        "chulNo": 1,
    }

    cleaned = strip_forbidden_fields(race_data)

    assert "ordBigo" not in cleaned
    assert "sjG1fOrd" not in cleaned
    assert "seG3fAccTime" not in cleaned["nested"]


def test_rename_rank_to_class_rank():
    """rank 필드가 class_rank로 rename되는지"""
    from prepare import strip_forbidden_fields

    race_data = {"rank": "국6", "chulNo": 1}
    cleaned = strip_forbidden_fields(race_data)
    assert "rank" not in cleaned
    assert cleaned["class_rank"] == "국6"


def test_derive_snapshot_timing_uses_cutoff_and_basic_collected_at():
    """basic_data.collected_at과 sch_st_time으로 strict timing을 산출하는지"""
    from shared.read_contract import RaceKey, RaceSnapshot

    from autoresearch.holdout_dataset import derive_snapshot_timing

    snapshot = RaceSnapshot(
        key=RaceKey(race_id="race-1", race_date="20250101", meet=1, race_number=1),
        basic_data={
            "collected_at": "2025-01-01T01:35:00+00:00",
            "race_info": {
                "response": {
                    "body": {
                        "items": {"item": [{"rcDate": "20250101", "schStTime": "1100"}]}
                    }
                }
            },
            "race_plan": {"sch_st_time": "1100"},
            "track": {"weather": "맑음"},
            "cancelled_horses": [],
        },
        collected_at="2025-01-01T01:35:00+00:00",
    )

    timing = derive_snapshot_timing(snapshot)

    assert timing.replay_status == "strict"
    assert timing.include_in_strict_dataset is True
    assert timing.operational_cutoff_at == "2025-01-01T10:50:00+09:00"
    assert timing.entry_finalized_at == "2025-01-01T10:35:00+09:00"


def test_derive_snapshot_timing_rejects_post_cutoff_snapshot():
    """snapshot_ready_at이 cutoff 이후면 strict dataset에서 제외하는지"""
    from shared.read_contract import RaceKey, RaceSnapshot

    from autoresearch.holdout_dataset import derive_snapshot_timing

    snapshot = RaceSnapshot(
        key=RaceKey(race_id="race-2", race_date="20250101", meet=1, race_number=1),
        basic_data={
            "collected_at": "2025-01-01T02:05:00+00:00",
            "race_info": {
                "response": {
                    "body": {
                        "items": {"item": [{"rcDate": "20250101", "schStTime": "1100"}]}
                    }
                }
            },
            "race_plan": {"sch_st_time": "1100"},
            "track": {"weather": "맑음"},
            "cancelled_horses": [],
        },
        collected_at="2025-01-01T02:05:00+00:00",
    )

    timing = derive_snapshot_timing(snapshot)

    assert timing.replay_status == "late_snapshot_unusable"
    assert timing.include_in_strict_dataset is False


def test_derive_snapshot_timing_prefers_persisted_snapshot_meta_from_raw_data():
    """raw_data.snapshot_meta가 있으면 holdout timing 재계산보다 우선한다."""
    from shared.read_contract import RaceKey, RaceSnapshot

    from autoresearch.holdout_dataset import derive_snapshot_timing

    snapshot = RaceSnapshot(
        key=RaceKey(race_id="race-3", race_date="20250101", meet=1, race_number=1),
        basic_data={
            "collected_at": "2025-01-01T01:35:00+00:00",
            "race_info": {
                "response": {
                    "body": {
                        "items": {"item": [{"rcDate": "20250101", "schStTime": "1100"}]}
                    }
                }
            },
            "race_plan": {"sch_st_time": "1100"},
            "track": {"weather": "맑음"},
            "cancelled_horses": [],
        },
        raw_data={
            "snapshot_meta": {
                "format_version": "holdout-snapshot-v1",
                "rule_version": "holdout-entry-finalization-rule-v1",
                "source_filter_basis": "entry_finalized_at",
                "scheduled_start_at": "2025-01-01T11:00:00+09:00",
                "operational_cutoff_at": "2025-01-01T10:50:00+09:00",
                "snapshot_ready_at": "2025-01-01T10:40:00+09:00",
                "entry_finalized_at": "2025-01-01T10:40:00+09:00",
                "selected_timestamp_field": "entry_finalized_at_override",
                "selected_timestamp_value": "2025-01-01T10:40:00+09:00",
                "timestamp_source": "source_revision",
                "timestamp_confidence": "high",
                "revision_id": "rev-001",
                "late_reissue_after_cutoff": False,
                "cutoff_unbounded": False,
                "replay_status": "strict",
                "include_in_strict_dataset": True,
                "hard_required_sources_present": True,
                "hard_required_source_status": {
                    "API214_1": "present",
                    "API72_2": "present",
                    "API189_1": "present",
                    "API9_1": "present",
                },
            }
        },
        collected_at="2025-01-01T01:35:00+00:00",
    )

    timing = derive_snapshot_timing(snapshot)

    assert timing.timestamp_source == "source_revision"
    assert timing.timestamp_confidence == "high"
    assert timing.selected_timestamp_field == "entry_finalized_at_override"
    assert timing.entry_finalized_at == "2025-01-01T10:40:00+09:00"


def test_set_match_score():
    """set_match 계산이 정확한지"""
    from prepare import set_match_score

    assert set_match_score([1, 2, 3], [1, 2, 3]) == 1.0  # 3/3
    assert set_match_score([1, 2, 3], [4, 5, 6]) == 0.0  # 0/3
    assert abs(set_match_score([1, 2, 3], [1, 4, 5]) - 1 / 3) < 0.01  # 1/3
    assert abs(set_match_score([1, 2, 3], [3, 2, 7]) - 2 / 3) < 0.01  # 2/3


def test_extract_race_data_standardizes_abnormal_runner_statuses():
    from prepare import _extract_race_data

    enriched = {
        "response": {
            "body": {
                "items": {
                    "item": [
                        {
                            "rcDate": "20250101",
                            "rcNo": 1,
                            "meet": "서울",
                            "rcDist": 1200,
                            "track": "건조",
                            "weather": "맑음",
                            "budam": "별정A",
                            "ageCond": "연령오픈",
                            "chulNo": 1,
                            "hrNo": "001",
                            "hrName": "정상마",
                            "jkNo": "J1",
                            "jkName": "기수1",
                            "trNo": "T1",
                            "trName": "조교사1",
                            "owNo": "O1",
                            "owName": "마주1",
                            "age": 4,
                            "sex": "수",
                            "name": "한국",
                            "rank": "국6",
                            "rating": 40,
                            "wgBudam": 55,
                            "wgBudamBigo": "-",
                            "wgHr": "500(+1)",
                            "winOdds": 3.2,
                            "plcOdds": 1.4,
                        },
                        {
                            "rcDate": "20250101",
                            "rcNo": 1,
                            "meet": "서울",
                            "rcDist": 1200,
                            "track": "건조",
                            "weather": "맑음",
                            "budam": "별정A",
                            "ageCond": "연령오픈",
                            "chulNo": 2,
                            "hrNo": "002",
                            "hrName": "기권마",
                            "jkNo": "J2",
                            "jkName": "기수2",
                            "trNo": "T2",
                            "trName": "조교사2",
                            "owNo": "O2",
                            "owName": "마주2",
                            "age": 4,
                            "sex": "암",
                            "name": "한국",
                            "rank": "국6",
                            "rating": 35,
                            "wgBudam": 54,
                            "wgBudamBigo": "-",
                            "wgHr": "490(+0)",
                            "winOdds": 5.0,
                            "plcOdds": 1.9,
                        },
                        {
                            "rcDate": "20250101",
                            "rcNo": 1,
                            "meet": "서울",
                            "rcDist": 1200,
                            "track": "건조",
                            "weather": "맑음",
                            "budam": "별정A",
                            "ageCond": "연령오픈",
                            "chulNo": 3,
                            "hrNo": "003",
                            "hrName": "제로배당마",
                            "jkNo": "J3",
                            "jkName": "기수3",
                            "trNo": "T3",
                            "trName": "조교사3",
                            "owNo": "O3",
                            "owName": "마주3",
                            "age": 5,
                            "sex": "거",
                            "name": "한국",
                            "rank": "국6",
                            "rating": 30,
                            "wgBudam": 53,
                            "wgBudamBigo": "-",
                            "wgHr": "0()",
                            "winOdds": 0,
                            "plcOdds": 0,
                        },
                    ]
                }
            }
        }
    }

    race_data, candidate_filter = _extract_race_data(
        enriched,
        cancelled_horses=[{"chulNo": 2, "hrName": "기권마", "reason": "기권"}],
    )

    assert [horse["chulNo"] for horse in race_data["horses"]] == [1, 3]
    assert candidate_filter["status_counts"] == {
        "normal": 1,
        "scratched": 1,
        "withdrawn": 1,
    }
    assert {row["chul_no"] for row in candidate_filter["excluded_runners"]} == {2}
    assert {row["chul_no"] for row in candidate_filter["reincluded_runners"]} == {3}
    assert candidate_filter["initial_exclusion_rule_counts"] == {
        "withdrawn": 1,
        "zero_market_signal": 1,
    }
    assert candidate_filter["reinclusion_rule_counts"] == {"zero_market_signal": 1}
    assert candidate_filter["flag_counts"]["market_signal_missing"] == 1
    assert candidate_filter["flag_counts"]["plc_odds_missing"] == 1
    assert candidate_filter["flag_counts"]["weight_missing"] == 1
    assert candidate_filter["race_diagnostics"] == {
        "minimum_prediction_candidates": 3,
        "total_runner_count": 3,
        "initial_eligible_runner_count": 1,
        "initial_excluded_runner_count": 2,
        "initial_candidate_shortage_count": 2,
        "reincluded_runner_count": 1,
        "reinclusion_applied": True,
        "eligible_runner_count": 2,
        "excluded_runner_count": 1,
        "candidate_shortage_count": 1,
        "has_candidate_shortage": True,
        "shortage_reason_counts": {"official_status": 1},
        "shortage_reason_classification": "official_status_reduced_below_minimum",
        "primary_shortage_reason": "official_status",
    }
    assert candidate_filter["final_candidate_validation"] == {
        "active_runner_rule": "candidate_filter_minimum_info_fallback_v1",
        "minimum_prediction_candidates": 3,
        "final_candidate_count": 2,
        "minimum_candidate_met": False,
        "remaining_candidate_gap": 1,
    }
    assert candidate_filter["race_trace"]["applied_rule_ids"] == [
        "candidate_shortage_reinclusion_v1"
    ]
    assert candidate_filter["race_trace"]["final_candidate_chul_nos"] == [1, 3]


def test_extract_race_data_excludes_wg_budam_outlier_and_keeps_rule_logs():
    from prepare import _extract_race_data

    enriched = {
        "response": {
            "body": {
                "items": {
                    "item": [
                        {
                            "rcDate": "20250101",
                            "rcNo": 1,
                            "meet": "서울",
                            "rcDist": 1200,
                            "track": "건조",
                            "weather": "맑음",
                            "budam": "별정A",
                            "ageCond": "연령오픈",
                            "chulNo": 1,
                            "hrNo": "001",
                            "hrName": "정상마",
                            "jkNo": "J1",
                            "jkName": "기수1",
                            "trNo": "T1",
                            "trName": "조교사1",
                            "owNo": "O1",
                            "owName": "마주1",
                            "age": 4,
                            "sex": "수",
                            "name": "한국",
                            "rank": "국6",
                            "rating": 40,
                            "wgBudam": 55,
                            "wgHr": "500(+1)",
                            "winOdds": 3.2,
                            "plcOdds": 1.4,
                        },
                        {
                            "rcDate": "20250101",
                            "rcNo": 1,
                            "meet": "서울",
                            "rcDist": 1200,
                            "track": "건조",
                            "weather": "맑음",
                            "budam": "별정A",
                            "ageCond": "연령오픈",
                            "chulNo": 9,
                            "hrNo": "009",
                            "hrName": "이상치마",
                            "jkNo": "J9",
                            "jkName": "기수9",
                            "trNo": "T9",
                            "trName": "조교사9",
                            "owNo": "O9",
                            "owName": "마주9",
                            "age": 4,
                            "sex": "암",
                            "name": "한국",
                            "rank": "국6",
                            "rating": 42,
                            "wgBudam": 70,
                            "wgHr": "480(+2)",
                            "winOdds": 4.1,
                            "plcOdds": 1.7,
                        },
                    ]
                }
            }
        }
    }

    race_data, candidate_filter = _extract_race_data(enriched)

    assert [horse["chulNo"] for horse in race_data["horses"]] == [1, 9]
    assert candidate_filter["status_counts"]["burden_outlier"] == 1
    assert candidate_filter["exclusion_rule_counts"] == {}
    assert candidate_filter["reinclusion_rule_counts"] == {"wg_budam_outlier": 1}
    reincluded = candidate_filter["reincluded_runners"][0]
    assert reincluded["exclusion_reason"] == "wg_budam_outlier"
    assert "wg_budam_outlier" in reincluded["applied_rules"]
    assert any(
        row["chul_no"] == 9 and row["status_code"] == "burden_outlier"
        for row in candidate_filter["rule_logs"]
    )
    assert candidate_filter["race_diagnostics"]["has_candidate_shortage"] is True
    assert (
        candidate_filter["race_diagnostics"]["shortage_reason_classification"]
        == "raw_field_too_small"
    )


def test_extract_race_data_classifies_data_quality_shortage():
    from prepare import _extract_race_data

    enriched = {
        "response": {
            "body": {
                "items": {
                    "item": [
                        {
                            "rcDate": "20250101",
                            "rcNo": 1,
                            "meet": "서울",
                            "rcDist": 1200,
                            "track": "건조",
                            "weather": "맑음",
                            "budam": "별정A",
                            "ageCond": "연령오픈",
                            "chulNo": 1,
                            "hrNo": "001",
                            "hrName": "정상마",
                            "jkNo": "J1",
                            "jkName": "기수1",
                            "trNo": "T1",
                            "trName": "조교사1",
                            "owNo": "O1",
                            "owName": "마주1",
                            "age": 4,
                            "sex": "수",
                            "name": "한국",
                            "rank": "국6",
                            "rating": 40,
                            "wgBudam": 55,
                            "wgHr": "500(+1)",
                            "winOdds": 3.2,
                            "plcOdds": 1.4,
                        },
                        {
                            "rcDate": "20250101",
                            "rcNo": 1,
                            "meet": "서울",
                            "rcDist": 1200,
                            "track": "건조",
                            "weather": "맑음",
                            "budam": "별정A",
                            "ageCond": "연령오픈",
                            "chulNo": 2,
                            "hrNo": "002",
                            "hrName": "부담이상치",
                            "jkNo": "J2",
                            "jkName": "기수2",
                            "trNo": "T2",
                            "trName": "조교사2",
                            "owNo": "O2",
                            "owName": "마주2",
                            "age": 4,
                            "sex": "암",
                            "name": "한국",
                            "rank": "국6",
                            "rating": 35,
                            "wgBudam": 71,
                            "wgHr": "490(+0)",
                            "winOdds": 5.0,
                            "plcOdds": 1.9,
                        },
                        {
                            "rcDate": "20250101",
                            "rcNo": 1,
                            "meet": "서울",
                            "rcDist": 1200,
                            "track": "건조",
                            "weather": "맑음",
                            "budam": "별정A",
                            "ageCond": "연령오픈",
                            "chulNo": None,
                            "hrNo": "003",
                            "hrName": "번호누락",
                            "jkNo": "J3",
                            "jkName": "기수3",
                            "trNo": "T3",
                            "trName": "조교사3",
                            "owNo": "O3",
                            "owName": "마주3",
                            "age": 5,
                            "sex": "거",
                            "name": "한국",
                            "rank": "국6",
                            "rating": 30,
                            "wgBudam": 53,
                            "wgHr": "480(+1)",
                            "winOdds": 7.2,
                            "plcOdds": 2.3,
                        },
                    ]
                }
            }
        }
    }

    race_data, candidate_filter = _extract_race_data(enriched)

    assert [horse["chulNo"] for horse in race_data["horses"]] == [1, 2]
    assert candidate_filter["status_counts"] == {
        "burden_outlier": 1,
        "invalid_entry": 1,
        "normal": 1,
    }
    assert candidate_filter["reinclusion_rule_counts"] == {"wg_budam_outlier": 1}
    assert candidate_filter["race_diagnostics"] == {
        "minimum_prediction_candidates": 3,
        "total_runner_count": 3,
        "initial_eligible_runner_count": 1,
        "initial_excluded_runner_count": 2,
        "initial_candidate_shortage_count": 2,
        "reincluded_runner_count": 1,
        "reinclusion_applied": True,
        "eligible_runner_count": 2,
        "excluded_runner_count": 1,
        "candidate_shortage_count": 1,
        "has_candidate_shortage": True,
        "shortage_reason_counts": {"data_quality": 1},
        "shortage_reason_classification": "data_quality_reduced_below_minimum",
        "primary_shortage_reason": "data_quality",
    }


def test_compute_score_perfect():
    """완벽한 예측의 스코어"""
    from prepare import compute_score

    prediction = {"predicted": [1, 2, 3], "confidence": 0.8, "reasoning": "test"}
    actual = [1, 2, 3]
    score = compute_score(prediction, actual)
    assert score["json_ok"] is True
    assert score["deferred"] is False
    assert score["status_code"] == "SCORED_OK"
    assert (
        score["status_reason"]
        == "예측과 confidence가 모두 유효하며 정상 집계 대상이다."
    )
    assert score["fallback_required"] is False
    assert score["race_status"] == {
        "status_code": "SCORED_OK",
        "status_class": "scored",
        "status_reason": "예측과 confidence가 모두 유효하며 정상 집계 대상이다.",
        "fallback_required": False,
        "fallback_action": "set_match 와 correct_count 를 정상 집계",
    }
    assert score["set_match"] == 1.0
    assert score["correct_count"] == 3


def test_compute_score_deferred():
    """confidence < 0.3이면 defer 처리"""
    from prepare import compute_score

    prediction = {"predicted": [1, 2, 3], "confidence": 0.2, "reasoning": "low"}
    actual = [1, 2, 3]
    score = compute_score(prediction, actual)
    assert score["deferred"] is True
    assert score["status_code"] == "DEFERRED_LOW_CONFIDENCE"
    assert score["fallback_required"] is True
    assert score["coverage_included"] is False
    assert score["score_aggregated"] is False


def test_compute_score_confidence_normalize():
    """confidence > 1.0이면 100으로 나눠서 정규화"""
    from prepare import compute_score

    prediction = {"predicted": [1, 2, 3], "confidence": 72, "reasoning": "high"}
    actual = [1, 2, 3]
    score = compute_score(prediction, actual)
    assert score["deferred"] is False  # 0.72 >= 0.3
    assert score["normalized_confidence"] == 0.72


def test_compute_score_invalid_schema():
    """스키마 불일치 시 json_ok=False"""
    from prepare import compute_score

    prediction = {"wrong_key": [1, 2, 3]}
    actual = [1, 2, 3]
    score = compute_score(prediction, actual)
    assert score["json_ok"] is False
    assert score["status_code"] == "MISSING_PREDICTED_TOP3"
    assert score["race_status"]["fallback_required"] is True


def test_compute_score_prediction_payload_missing_is_failed_status():
    """prediction 자체가 dict가 아니면 실패 상태와 fallback 요구를 반환한다."""
    from prepare import compute_score

    score = compute_score(None, [1, 2, 3])

    assert score["json_ok"] is False
    assert score["deferred"] is False
    assert score["status_code"] == "FAIL_PREDICTION_PAYLOAD_MISSING"
    assert score["fallback_required"] is True
    assert score["race_status"]["status_class"] == "failed"


def test_compute_score_missing_confidence_is_not_defer():
    """confidence 누락은 보류가 아니라 결측 상태로 분리한다."""
    from prepare import compute_score

    prediction = {"predicted": [1, 2, 3], "reasoning": "missing confidence"}
    actual = [1, 2, 3]

    score = compute_score(prediction, actual)

    assert score["json_ok"] is False
    assert score["deferred"] is False
    assert score["status_code"] == "MISSING_CONFIDENCE"
    assert (
        score["status_reason"]
        == "confidence 값이 없어 보류/정상 채점 여부를 결정할 수 없다."
    )


def test_compute_score_invalid_confidence_reflects_failed_status_and_fallback():
    """confidence가 비정상이면 실패 상태 코드와 fallback 요구를 그대로 반환한다."""
    from prepare import compute_score

    prediction = {"predicted": [1, 2, 3], "confidence": "nan"}
    actual = [1, 2, 3]

    score = compute_score(prediction, actual)

    assert score["json_ok"] is False
    assert score["deferred"] is False
    assert score["status_code"] == "FAIL_CONFIDENCE_INVALID"
    assert score["fallback_required"] is True
    assert score["race_status"]["status_class"] == "failed"


def test_compute_score_invalid_actual_is_failure():
    """actual 정답키가 비정상이면 별도 실패 코드로 분리한다."""
    from prepare import compute_score

    prediction = {"predicted": [1, 2, 3], "confidence": 0.8}
    actual = [1, 1, 2]

    score = compute_score(prediction, actual)

    assert score["json_ok"] is False
    assert score["status_code"] == "FAIL_ACTUAL_TOP3_INVALID"
    assert score["race_status"]["status_class"] == "failed"


def test_print_score_line(capsys):
    """스코어 라인 출력 형식"""
    from prepare import print_score_line

    results = [
        {"json_ok": True, "deferred": False, "set_match": 1.0, "correct_count": 3},
        {"json_ok": True, "deferred": False, "set_match": 0.333, "correct_count": 1},
        {"json_ok": False, "deferred": False, "set_match": 0.0, "correct_count": 0},
    ]
    print_score_line(results)
    output = capsys.readouterr().out
    assert "set_match=" in output
    assert "json_ok=" in output
    assert "coverage=" in output


# ============================================================
# Integration tests
# ============================================================


def _make_race_data(race_id: str = "test_001") -> dict:
    """테스트용 mock race_data 생성"""
    return {
        "race_id": race_id,
        "race_info": {
            "rcDate": "20250101",
            "rcNo": "1",
            "meet": "서울",
            "rcDist": "1200",
            "track": "건조",
            "weather": "맑음",
            "budam": "별정A",
            "ageCond": "3세이상",
        },
        "horses": [
            {
                "chulNo": 1,
                "hrName": "마1",
                "winOdds": 3.0,
                "computed_features": {
                    "odds_rank": 1,
                    "horse_win_rate": 30.0,
                    "jockey_win_rate": 20.0,
                },
            },
            {
                "chulNo": 2,
                "hrName": "마2",
                "winOdds": 5.0,
                "computed_features": {
                    "odds_rank": 2,
                    "horse_win_rate": 20.0,
                    "jockey_win_rate": 15.0,
                },
            },
            {
                "chulNo": 3,
                "hrName": "마3",
                "winOdds": 8.0,
                "computed_features": {
                    "odds_rank": 3,
                    "horse_win_rate": 10.0,
                    "jockey_win_rate": 10.0,
                },
            },
        ],
    }


def _make_snapshot_basic_data(
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
            "owName": f"마주-{chul_no}",
            "owNo": f"OW{chul_no:03d}",
            "sex": "수",
            "age": 3,
            "name": "한국",
            "wgBudam": 55,
            "wgBudamBigo": "-",
            "wgHr": "450(+2)",
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


def _make_prepare_snapshot(
    race_date: str,
    meet: int,
    race_number: int,
    *,
    starters: tuple[int, ...] = (1, 2, 3),
):
    from shared.read_contract import RaceKey, RaceSnapshot

    return RaceSnapshot(
        key=RaceKey(
            race_id=f"{race_date}_{meet}_{race_number}",
            race_date=race_date,
            meet=meet,
            race_number=race_number,
        ),
        collection_status="collected",
        result_status="collected",
        basic_data=_make_snapshot_basic_data(
            race_date,
            race_number,
            starters=starters,
        ),
        result_data={"top3": [1, 2, 3]},
        collected_at="2025-01-01T10:30:00+09:00",
        updated_at="2025-01-01T10:31:00+09:00",
    )


def test_build_snapshot_race_data_attaches_snapshot_meta_and_removes_post_race_fields():
    """race payload에 snapshot_meta를 붙이고 사후 필드를 제거하는지"""
    from prepare import _build_snapshot_race_data
    from shared.read_contract import RaceKey, RaceSnapshot

    snapshot = RaceSnapshot(
        key=RaceKey(race_id="race-3", race_date="20250101", meet=1, race_number=1),
        basic_data={
            "race_info": {
                "response": {
                    "body": {
                        "items": {
                            "item": [
                                {
                                    "rcDate": "20250101",
                                    "rcNo": 1,
                                    "meet": "서울",
                                    "rcDist": 1200,
                                    "track": "양호",
                                    "weather": "맑음",
                                    "budam": "별정A",
                                    "ageCond": "3세",
                                    "schStTime": "1100",
                                    "chulNo": 1,
                                    "hrName": "테스트마",
                                    "winOdds": 3.2,
                                    "ordBigo": "-",
                                    "sjG1fOrd": 2,
                                    "rank": "국6",
                                    "rating": 45,
                                    "jkName": "기수",
                                    "jkNo": "J1",
                                    "trName": "조교사",
                                    "trNo": "T1",
                                    "owName": "마주",
                                    "owNo": "O1",
                                    "sex": "수",
                                    "age": 3,
                                    "name": "한국",
                                    "wgBudam": 55,
                                    "wgBudamBigo": "-",
                                    "wgHr": "450(+2)",
                                    "plcOdds": 1.5,
                                }
                            ]
                        }
                    }
                }
            },
            "horses": [],
            "race_plan": {"sch_st_time": "1100"},
            "track": {"weather": "맑음"},
            "cancelled_horses": [],
            "collected_at": "2025-01-01T01:35:00+00:00",
        },
        collected_at="2025-01-01T01:35:00+00:00",
    )

    race_data, timing_meta = _build_snapshot_race_data(snapshot)

    assert race_data is not None
    assert race_data["snapshot_meta"]["replay_status"] == "strict"
    assert (
        race_data["snapshot_meta"]["field_policy"]["policy_version"]
        == "prerace-field-policy-v1"
    )
    assert (
        race_data["snapshot_meta"]["candidate_filter"]["race_diagnostics"][
            "eligible_runner_count"
        ]
        == 1
    )
    assert (
        race_data["snapshot_meta"]["candidate_filter"]["race_diagnostics"][
            "has_candidate_shortage"
        ]
        is True
    )
    assert race_data["horses"][0]["class_rank"] == "국6"
    assert "ordBigo" not in race_data["horses"][0]
    assert "sjG1fOrd" not in race_data["horses"][0]
    assert "winOdds" not in race_data["horses"][0]
    assert "plcOdds" not in race_data["horses"][0]
    assert "odds_rank" not in race_data["horses"][0]["computed_features"]
    assert timing_meta["removed_post_race_field_count"] >= 2


def test_build_snapshot_race_data_records_entry_resolution_audit_for_duplicate_sources():
    from prepare import _build_snapshot_race_data
    from shared.read_contract import RaceKey, RaceSnapshot

    snapshot = RaceSnapshot(
        key=RaceKey(race_id="race-dup", race_date="20250101", meet=1, race_number=1),
        basic_data={
            "race_info": {
                "response": {
                    "body": {
                        "items": {
                            "item": [
                                {
                                    "rcDate": "20250101",
                                    "rcNo": 1,
                                    "meet": "서울",
                                    "rcDist": 1200,
                                    "track": "양호",
                                    "weather": "맑음",
                                    "budam": "별정A",
                                    "ageCond": "3세",
                                    "schStTime": "1100",
                                    "chulNo": 1,
                                    "hrNo": "OLD001",
                                    "hrName": "기존말",
                                    "jkNo": "J001",
                                },
                                {
                                    "rcDate": "20250101",
                                    "rcNo": 1,
                                    "meet": "서울",
                                    "rcDist": 1200,
                                    "track": "양호",
                                    "weather": "맑음",
                                    "budam": "별정A",
                                    "ageCond": "3세",
                                    "schStTime": "1100",
                                    "chulNo": 1,
                                    "hrNo": "001",
                                    "hrName": "확정말",
                                    "jkNo": "J001",
                                    "jkName": "기수1",
                                    "trNo": "T001",
                                    "trName": "조교사1",
                                    "owNo": "O001",
                                    "owName": "마주1",
                                    "sex": "수",
                                    "age": 3,
                                    "name": "한국",
                                    "rank": "국6",
                                    "rating": 45,
                                    "wgBudam": 55,
                                    "wgBudamBigo": "-",
                                    "wgHr": "450(+2)",
                                    "winOdds": 3.2,
                                    "plcOdds": 1.5,
                                },
                            ]
                        }
                    }
                }
            },
            "horses": [
                {"chul_no": 1, "hr_no": "BAD999", "hrDetail": {"win_rate": 99}},
                {"chul_no": 1, "hr_no": "001", "hrDetail": {"win_rate": 12, "age": 4}},
            ],
            "race_plan": {"sch_st_time": "1100"},
            "track": {"weather": "맑음"},
            "cancelled_horses": [],
            "collected_at": "2025-01-01T01:35:00+00:00",
        },
        collected_at="2025-01-01T01:35:00+00:00",
    )

    race_data, timing_meta = _build_snapshot_race_data(snapshot)

    assert race_data is not None
    assert len(race_data["horses"]) == 1
    assert race_data["horses"][0]["hrName"] == "확정말"
    audit = timing_meta["entry_resolution_audit"]
    assert audit["duplicate_chul_no_group_count"] == 2
    assert audit["identifier_inconsistency_count"] >= 2


def test_train_select_features_applies_same_field_policy_to_inference_prompt():
    """train.select_features가 학습 스냅샷과 동일한 필드 판정을 사용해야 한다."""
    from train import select_features

    features = select_features(
        {
            "race_info": {"rcDate": "20250101"},
            "horses": [
                {
                    "chulNo": 1,
                    "hrName": "테스트마",
                    "winOdds": 3.2,
                    "sjG1fOrd": 2,
                    "computed_features": {
                        "odds_rank": 1,
                        "horse_win_rate": 22.5,
                    },
                }
            ],
            "snapshot_meta": {"replay_status": "strict"},
        }
    )

    horse = features["horses"][0]
    assert "winOdds" not in horse
    assert "sjG1fOrd" not in horse
    assert "odds_rank" not in horse["computed_features"]
    assert horse["computed_features"]["horse_win_rate"] == 22.5
    assert "snapshot_meta" not in features


def test_build_dataset_manifest_includes_entry_finalization_audit() -> None:
    from autoresearch.holdout_dataset import build_dataset_manifest

    manifest = build_dataset_manifest(
        mode="holdout",
        created_at="2026-04-10T12:00:00+09:00",
        races=[
            {
                "race_id": "race-1",
                "scheduled_start_at": "2025-01-01T11:00:00+09:00",
                "operational_cutoff_at": "2025-01-01T10:50:00+09:00",
                "snapshot_ready_at": "2025-01-01T10:35:00+09:00",
                "entry_finalized_at": "2025-01-01T10:35:00+09:00",
                "timestamp_source": "snapshot_collected_at",
                "timestamp_confidence": "medium",
                "replay_status": "strict",
                "cutoff_unbounded": False,
                "late_reissue_after_cutoff": False,
                "include_in_strict_dataset": True,
                "hard_required_sources_present": True,
                "source_filter_basis": "entry_finalized_at",
            }
        ],
    )

    assert manifest["audit"]["passed"] is True
    assert manifest["audit"]["checked_races"] == 1
    assert "source_filter_basis" in manifest["audit"]["required_log_fields"]
    assert manifest["audit"]["violation_counts"] == {}
    assert (
        manifest["dataset_metadata"]["feature_schema_version"]
        == "alternative-ranking-input-v1"
    )
    assert (
        manifest["dataset_metadata"]["input_schema_contract"]["schema_version"]
        == "alternative-ranking-input-v1"
    )


def test_build_dataset_manifest_flags_entry_finalization_audit_violations() -> None:
    from autoresearch.holdout_dataset import build_dataset_manifest

    manifest = build_dataset_manifest(
        mode="holdout",
        created_at="2026-04-10T12:00:00+09:00",
        races=[
            {
                "race_id": "race-bad",
                "scheduled_start_at": "2025-01-01T11:00:00+09:00",
                "operational_cutoff_at": "2025-01-01T10:50:00+09:00",
                "snapshot_ready_at": "2025-01-01T10:55:00+09:00",
                "entry_finalized_at": "2025-01-01T10:55:00+09:00",
                "timestamp_source": "snapshot_collected_at",
                "timestamp_confidence": "low",
                "replay_status": "late_snapshot_unusable",
                "cutoff_unbounded": False,
                "late_reissue_after_cutoff": False,
                "include_in_strict_dataset": True,
                "hard_required_sources_present": False,
                "source_filter_basis": "snapshot_ready_at",
            }
        ],
    )

    assert manifest["audit"]["passed"] is False
    codes = {item["code"] for item in manifest["audit"]["violations"]}
    assert "unexpected_source_filter_basis" in codes
    assert "strict_without_required_sources" in codes
    assert "post_cutoff_snapshot" in codes
    assert "excluded_status_marked_included" in codes
    assert "timestamp_confidence_mismatch" in codes


def test_build_dataset_manifest_accepts_snapshot_at_cutoff_boundary() -> None:
    from autoresearch.holdout_dataset import build_dataset_manifest

    manifest = build_dataset_manifest(
        mode="holdout",
        created_at="2026-04-10T12:00:00+09:00",
        races=[
            {
                "race_id": "race-boundary",
                "scheduled_start_at": "2025-01-01T11:00:00+09:00",
                "operational_cutoff_at": "2025-01-01T10:50:00+09:00",
                "snapshot_ready_at": "2025-01-01T10:50:00+09:00",
                "entry_finalized_at": "2025-01-01T10:50:00+09:00",
                "timestamp_source": "snapshot_collected_at",
                "timestamp_confidence": "medium",
                "replay_status": "strict",
                "cutoff_unbounded": False,
                "late_reissue_after_cutoff": False,
                "include_in_strict_dataset": True,
                "hard_required_sources_present": True,
                "source_filter_basis": "entry_finalized_at",
            }
        ],
    )

    assert manifest["audit"]["passed"] is True
    assert manifest["audit"]["violation_counts"] == {}
    assert manifest["audit"]["violations"] == []


def test_build_dataset_manifest_flags_snapshot_timestamp_logging_violations() -> None:
    from autoresearch.holdout_dataset import build_dataset_manifest

    manifest = build_dataset_manifest(
        mode="holdout",
        created_at="2026-04-10T12:00:00+09:00",
        races=[
            {
                "race_id": "race-missing-ready",
                "scheduled_start_at": "2025-01-01T11:00:00+09:00",
                "operational_cutoff_at": "2025-01-01T10:50:00+09:00",
                "snapshot_ready_at": None,
                "entry_finalized_at": "2025-01-01T10:35:00+09:00",
                "timestamp_source": "snapshot_collected_at",
                "timestamp_confidence": "medium",
                "replay_status": "strict",
                "cutoff_unbounded": False,
                "late_reissue_after_cutoff": False,
                "include_in_strict_dataset": True,
                "hard_required_sources_present": True,
                "source_filter_basis": "entry_finalized_at",
            },
            {
                "race_id": "race-mismatch",
                "scheduled_start_at": "2025-01-01T11:00:00+09:00",
                "operational_cutoff_at": "2025-01-01T10:50:00+09:00",
                "snapshot_ready_at": "2025-01-01T10:34:00+09:00",
                "entry_finalized_at": "2025-01-01T10:35:00+09:00",
                "timestamp_source": "snapshot_collected_at",
                "timestamp_confidence": "medium",
                "replay_status": "strict",
                "cutoff_unbounded": False,
                "late_reissue_after_cutoff": False,
                "include_in_strict_dataset": True,
                "hard_required_sources_present": True,
                "source_filter_basis": "entry_finalized_at",
            },
        ],
    )

    assert manifest["audit"]["passed"] is False
    codes = {item["code"] for item in manifest["audit"]["violations"]}
    assert "missing_snapshot_ready_at" in codes
    assert "entry_snapshot_timestamp_mismatch" in codes


def test_build_dataset_manifest_includes_candidate_selection_audit() -> None:
    from autoresearch.holdout_dataset import build_dataset_manifest

    manifest = build_dataset_manifest(
        mode="holdout",
        created_at="2026-04-10T12:00:00+09:00",
        races=[
            {
                "race_id": "race-1",
                "scheduled_start_at": "2025-01-01T11:00:00+09:00",
                "operational_cutoff_at": "2025-01-01T10:50:00+09:00",
                "snapshot_ready_at": "2025-01-01T10:35:00+09:00",
                "entry_finalized_at": "2025-01-01T10:35:00+09:00",
                "timestamp_source": "snapshot_collected_at",
                "timestamp_confidence": "medium",
                "replay_status": "strict",
                "cutoff_unbounded": False,
                "late_reissue_after_cutoff": False,
                "include_in_strict_dataset": True,
                "hard_required_sources_present": True,
                "source_filter_basis": "entry_finalized_at",
                "candidate_filter": {
                    "final_candidate_validation": {
                        "final_candidate_count": 3,
                        "minimum_candidate_met": True,
                    },
                    "race_trace": {
                        "applied_rule_ids": [],
                        "reintroduced_targets": [],
                        "final_candidates": [
                            {"chul_no": 1},
                            {"chul_no": 2},
                            {"chul_no": 3},
                        ],
                        "final_candidate_chul_nos": [1, 2, 3],
                        "final_candidate_count": 3,
                    },
                },
            }
        ],
    )

    assert manifest["candidate_selection_audit"]["passed"] is True
    assert manifest["candidate_selection_audit"]["checked_races"] == 1


def test_build_dataset_manifest_flags_candidate_selection_trace_violations() -> None:
    from autoresearch.holdout_dataset import build_dataset_manifest

    manifest = build_dataset_manifest(
        mode="holdout",
        created_at="2026-04-10T12:00:00+09:00",
        races=[
            {
                "race_id": "race-bad",
                "scheduled_start_at": "2025-01-01T11:00:00+09:00",
                "operational_cutoff_at": "2025-01-01T10:50:00+09:00",
                "snapshot_ready_at": "2025-01-01T10:35:00+09:00",
                "entry_finalized_at": "2025-01-01T10:35:00+09:00",
                "timestamp_source": "snapshot_collected_at",
                "timestamp_confidence": "medium",
                "replay_status": "strict",
                "cutoff_unbounded": False,
                "late_reissue_after_cutoff": False,
                "include_in_strict_dataset": True,
                "hard_required_sources_present": True,
                "source_filter_basis": "entry_finalized_at",
                "candidate_filter": {
                    "final_candidate_validation": {
                        "final_candidate_count": 2,
                        "minimum_candidate_met": False,
                    },
                    "race_trace": {
                        "applied_rule_ids": [],
                        "reintroduced_targets": [],
                        "final_candidates": [{"chul_no": 1}, {"chul_no": 2}],
                        "final_candidate_chul_nos": [1, 2],
                        "final_candidate_count": 2,
                    },
                },
            }
        ],
    )

    assert manifest["candidate_selection_audit"]["passed"] is False
    codes = {
        item["code"] for item in manifest["candidate_selection_audit"]["violations"]
    }
    assert "minimum_candidate_not_met" in codes


def test_train_prepare_integration():
    """train.py predict() + prepare.py compute_score() 통합 테스트"""
    from prepare import compute_score
    from train import predict

    race_data = _make_race_data()

    def mock_llm(system: str, user: str) -> str:
        return (
            '{"predicted": [1, 2, 3], "confidence": 0.75, "reasoning": "인기마 순서"}'
        )

    prediction = predict(race_data, call_llm=mock_llm)
    actual = [1, 2, 3]
    score = compute_score(prediction, actual)

    assert score["json_ok"] is True
    assert score["deferred"] is False
    assert score["set_match"] == 1.0
    assert score["correct_count"] == 3


def test_deferred_race_keeps_top3_output_and_only_excludes_aggregate_metrics(capsys):
    """보류 경주는 top3 출력은 유지하고 허용된 defer fallback만 적용해야 한다."""
    from prepare import compute_score, print_score_line
    from train import predict

    race_data = _make_race_data("race_deferred_contract")

    def mock_llm(system: str, user: str) -> str:
        return '{"predicted": [1, 2, 3], "confidence": 0.15, "reasoning": "보류 경주 계약 테스트"}'

    prediction = predict(race_data, call_llm=mock_llm)
    score = compute_score(prediction, [1, 2, 3])

    assert prediction["predicted"] == [1, 2, 3]
    assert prediction["confidence"] == 0.15
    assert prediction["reasoning"]

    assert score["json_ok"] is True
    assert score["deferred"] is True
    assert score["status_code"] == "DEFERRED_LOW_CONFIDENCE"
    assert score["fallback_required"] is True
    assert (
        score["fallback_action"]
        == "set_match 와 correct_count 는 계산하되 coverage 및 score 집계에서 제외"
    )
    assert score["coverage_included"] is False
    assert score["score_aggregated"] is False
    assert score["set_match"] == 1.0
    assert score["correct_count"] == 3

    scored = compute_score(
        {"predicted": [1, 4, 7], "confidence": 0.65, "reasoning": "집계 기준 경주"},
        [1, 5, 6],
    )
    print_score_line([scored, score])
    output = capsys.readouterr().out

    assert "set_match=0.333" in output
    assert "avg_correct=1.00" in output
    assert "json_ok=100%" in output
    assert "coverage=50%" in output


def test_end_to_end_with_mock_snapshot(capsys):
    """전체 파이프라인 통합 테스트: predict → compute_score → print_score_line

    4가지 시나리오를 커버:
    1. 완벽한 예측 (3/3 match)
    2. 부분 예측 (1/3 match)
    3. defer 예측 (confidence < 0.3)
    4. 실패한 예측 (invalid JSON)
    """
    from prepare import compute_score, print_score_line
    from train import predict

    # --- 시나리오별 mock race data + answer_key ---
    races = [
        {"data": _make_race_data("race_perfect"), "actual": [1, 2, 3]},
        {"data": _make_race_data("race_partial"), "actual": [1, 5, 6]},
        {"data": _make_race_data("race_defer"), "actual": [1, 2, 3]},
        {"data": _make_race_data("race_fail"), "actual": [1, 2, 3]},
    ]

    # 시나리오별 LLM 응답
    llm_responses = {
        "race_perfect": '{"predicted": [1, 2, 3], "confidence": 0.85, "reasoning": "완벽 예측"}',
        "race_partial": '{"predicted": [1, 4, 7], "confidence": 0.60, "reasoning": "부분 예측"}',
        "race_defer": '{"predicted": [1, 2, 3], "confidence": 0.15, "reasoning": "불확실"}',
        "race_fail": "이건 JSON이 아닙니다. 그냥 텍스트입니다.",
    }

    def mock_llm(system: str, user: str) -> str:
        # race_id를 user prompt에서 추출할 수 없으므로 call 순서로 구분
        return mock_llm._responses.pop(0)

    mock_llm._responses = [llm_responses[r["data"]["race_id"]] for r in races]

    # --- 전체 파이프라인 실행 ---
    results = []
    for race in races:
        prediction = predict(race["data"], call_llm=mock_llm)
        score = compute_score(prediction, race["actual"])
        results.append(score)

    # --- 시나리오 1: 완벽한 예측 ---
    perfect = results[0]
    assert perfect["json_ok"] is True
    assert perfect["deferred"] is False
    assert perfect["set_match"] == 1.0
    assert perfect["correct_count"] == 3

    # --- 시나리오 2: 부분 예측 (actual=[1,5,6], predicted=[1,4,7]) → 1/3 ---
    partial = results[1]
    assert partial["json_ok"] is True
    assert partial["deferred"] is False
    assert abs(partial["set_match"] - 1 / 3) < 0.01
    assert partial["correct_count"] == 1

    # --- 시나리오 3: defer (confidence=0.15 < 0.3) ---
    deferred = results[2]
    assert deferred["json_ok"] is True
    assert deferred["deferred"] is True
    assert deferred["set_match"] == 1.0  # 맞추긴 했지만 defer
    assert deferred["correct_count"] == 3

    # --- 시나리오 4: invalid JSON → json_ok=False ---
    failed = results[3]
    assert failed["json_ok"] is False
    assert failed["deferred"] is False
    assert failed["set_match"] == 0.0
    assert failed["correct_count"] == 0

    # --- 집계 검증 ---
    # json_ok: 3/4 (perfect, partial, defer는 ok, fail은 not ok)
    json_ok_count = sum(1 for r in results if r["json_ok"])
    assert json_ok_count == 3

    # deferred: 1/4
    deferred_count = sum(1 for r in results if r["deferred"])
    assert deferred_count == 1

    # coverage: (4 - 1) / 4 = 75%
    coverage_pct = (len(results) - deferred_count) / len(results) * 100
    assert coverage_pct == 75.0

    # --- print_score_line 출력 검증 ---
    print_score_line(results)
    output = capsys.readouterr().out

    # valid = json_ok=True & deferred=False → perfect + partial
    # avg set_match = (1.0 + 1/3) / 2 = 0.667
    assert "set_match=0.667" in output
    # avg correct = (3 + 1) / 2 = 2.0
    assert "avg_correct=2.00" in output
    # json_ok = 3/4 = 75%
    assert "json_ok=75%" in output
    # coverage = 3/4 = 75%
    assert "coverage=75%" in output
    assert "races=4" in output


def test_check_snapshot_reproducibility_reports_identical_regeneration() -> None:
    from prepare import _build_snapshot_bundle, check_snapshot_reproducibility

    snapshots = []
    for race_date in (
        "20250101",
        "20250102",
        "20250103",
        "20250104",
        "20250105",
        "20250106",
    ):
        snapshots.append(_make_prepare_snapshot(race_date, 1, 1))
        snapshots.append(_make_prepare_snapshot(race_date, 3, 1))

    created_at = datetime.fromisoformat("2026-04-10T12:00:00+09:00")
    bundle = _build_snapshot_bundle(
        snapshots,
        manifest_created_at=created_at,
        holdout_minimum_race_count=4,
        mini_val_minimum_race_count=4,
    )

    report = check_snapshot_reproducibility(
        list(reversed(snapshots)),
        manifest_created_at=created_at,
        holdout_minimum_race_count=4,
        mini_val_minimum_race_count=4,
        reference_bundle=bundle,
    )

    assert report["passed"] is True
    assert report["manifest_created_at"] == "2026-04-10T12:00:00+09:00"
    for mode in ("mini_val", "holdout"):
        dataset = report["datasets"][mode]
        assert dataset["passed"] is True
        assert dataset["record_count_match"] is True
        assert dataset["column_structure_match"] is True
        assert dataset["sort_order_match"] is True
        assert dataset["content_hash_match"] is True
        assert dataset["sort_order_mismatch"] is None
        assert dataset["column_structure_diff"] is None


def test_check_snapshot_reproducibility_reports_sort_order_and_schema_drift() -> None:
    from prepare import _build_snapshot_bundle, check_snapshot_reproducibility

    snapshots = []
    for race_date in (
        "20250101",
        "20250102",
        "20250103",
        "20250104",
        "20250105",
        "20250106",
    ):
        snapshots.append(_make_prepare_snapshot(race_date, 1, 1))
        snapshots.append(_make_prepare_snapshot(race_date, 3, 1))

    created_at = datetime.fromisoformat("2026-04-10T12:00:00+09:00")
    reference_bundle = _build_snapshot_bundle(
        snapshots,
        manifest_created_at=created_at,
        holdout_minimum_race_count=4,
        mini_val_minimum_race_count=4,
    )

    holdout_records = list(reference_bundle["snapshots"]["holdout"])
    mutated_first = {
        **holdout_records[0],
        "unexpected_debug_field": "drift",
    }
    mutated_bundle = {
        **reference_bundle,
        "snapshots": {
            **reference_bundle["snapshots"],
            "holdout": [mutated_first, *holdout_records[2:], holdout_records[1]],
        },
    }

    report = check_snapshot_reproducibility(
        snapshots,
        manifest_created_at=created_at,
        holdout_minimum_race_count=4,
        mini_val_minimum_race_count=4,
        reference_bundle=mutated_bundle,
    )

    assert report["passed"] is False
    holdout = report["datasets"]["holdout"]
    assert holdout["passed"] is False
    assert holdout["record_count_match"] is True
    assert holdout["column_structure_match"] is False
    assert holdout["sort_order_match"] is False
    assert holdout["content_hash_match"] is False
    assert holdout["sort_order_mismatch"]["first_mismatch_index"] == 1
    assert (
        "unexpected_debug_field"
        in holdout["column_structure_diff"]["missing_from_regenerated"]
    )
