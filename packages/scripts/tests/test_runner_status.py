from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.runner_status import filter_candidate_runners, select_prediction_candidates


def test_filter_candidate_runners_reincludes_by_priority_until_minimum_candidates():
    runners = [
        {
            "chulNo": 1,
            "hrNo": "001",
            "hrName": "정상마",
            "wgBudam": 55,
            "wgHr": "500(+1)",
            "winOdds": 2.5,
            "plcOdds": 1.4,
        },
        {
            "chulNo": 2,
            "hrNo": "002",
            "hrName": "시장결측마",
            "wgBudam": 54,
            "wgHr": "490(+0)",
            "winOdds": 0,
            "plcOdds": 0,
        },
        {
            "chulNo": 3,
            "hrNo": "003",
            "hrName": "부담중량이상치마",
            "wgBudam": 70,
            "wgHr": "480(+2)",
            "winOdds": 4.1,
            "plcOdds": 1.8,
        },
        {
            "chulNo": 4,
            "hrNo": "004",
            "hrName": "공식취소마",
            "wgBudam": 53,
            "wgHr": "470(+1)",
            "winOdds": 5.0,
            "plcOdds": 2.0,
        },
    ]

    result = filter_candidate_runners(
        runners,
        cancelled_horses=[{"chulNo": 4, "reason": "출전취소"}],
    )

    assert [runner["chulNo"] for runner in result.eligible_runners] == [1, 2, 3]
    assert result.reinclusion_rule_counts == {
        "wg_budam_outlier": 1,
        "zero_market_signal": 1,
    }
    assert result.exclusion_rule_counts == {"cancelled": 1}
    assert result.race_diagnostics["reincluded_runner_count"] == 2
    assert result.race_diagnostics["candidate_shortage_count"] == 0


def test_filter_candidate_runners_keeps_invalid_entry_excluded_even_when_shortage_remains():
    runners = [
        {
            "chulNo": 1,
            "hrNo": "001",
            "hrName": "정상마",
            "wgBudam": 55,
            "wgHr": "500(+1)",
            "winOdds": 2.5,
            "plcOdds": 1.4,
        },
        {
            "hrNo": "002",
            "hrName": "출전번호누락마",
            "wgBudam": 54,
            "wgHr": "495(+0)",
            "winOdds": 3.0,
            "plcOdds": 1.6,
        },
        {
            "chulNo": 3,
            "hrNo": "003",
            "hrName": "시장결측마",
            "wgBudam": 53,
            "wgHr": "485(+2)",
            "winOdds": 0,
            "plcOdds": 0,
        },
    ]

    result = filter_candidate_runners(runners)

    assert [runner["chulNo"] for runner in result.eligible_runners] == [1, 3]
    assert result.reinclusion_rule_counts == {"zero_market_signal": 1}
    assert result.exclusion_rule_counts == {"invalid_entry_missing_chul_no": 1}
    assert result.race_diagnostics["candidate_shortage_count"] == 1


def test_select_prediction_candidates_records_race_traceability() -> None:
    runners = [
        {
            "chulNo": 1,
            "hrNo": "001",
            "hrName": "정상마",
            "age": 4,
            "sex": "수",
            "wgBudam": 55,
            "wgHr": "500(+1)",
            "winOdds": 2.5,
            "plcOdds": 1.4,
        },
        {
            "chulNo": 2,
            "hrNo": "002",
            "hrName": "시장결측마",
            "age": 4,
            "sex": "암",
            "wgBudam": 54,
            "wgHr": "490(+0)",
            "winOdds": 0,
            "plcOdds": 0,
        },
        {
            "chulNo": 3,
            "hrNo": "003",
            "hrName": "부담중량이상치마",
            "age": 4,
            "sex": "암",
            "wgBudam": 70,
            "wgHr": "480(+2)",
            "winOdds": 4.1,
            "plcOdds": 1.8,
        },
    ]

    result = select_prediction_candidates(runners)
    audit = result.to_audit_dict()

    assert audit["final_candidate_validation"] == {
        "active_runner_rule": "candidate_filter_minimum_info_fallback_v1",
        "minimum_prediction_candidates": 3,
        "final_candidate_count": 3,
        "minimum_candidate_met": True,
        "remaining_candidate_gap": 0,
    }
    assert audit["race_trace"]["applied_rule_ids"] == [
        "candidate_shortage_reinclusion_v1"
    ]
    assert [row["chul_no"] for row in audit["race_trace"]["reincluded_targets"]] == [
        2,
        3,
    ]
    assert audit["race_trace"]["minimum_info_fallback_targets"] == []
    assert audit["race_trace"]["final_candidate_chul_nos"] == [1, 2, 3]
