"""prepare.py 단위 테스트"""

import sys
import tempfile
import textwrap
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


def test_rename_rank_to_class_rank():
    """rank 필드가 class_rank로 rename되는지"""
    from prepare import strip_forbidden_fields

    race_data = {"rank": "국6", "chulNo": 1}
    cleaned = strip_forbidden_fields(race_data)
    assert "rank" not in cleaned
    assert cleaned["class_rank"] == "국6"


def test_set_match_score():
    """set_match 계산이 정확한지"""
    from prepare import set_match_score

    assert set_match_score([1, 2, 3], [1, 2, 3]) == 1.0  # 3/3
    assert set_match_score([1, 2, 3], [4, 5, 6]) == 0.0  # 0/3
    assert abs(set_match_score([1, 2, 3], [1, 4, 5]) - 1 / 3) < 0.01  # 1/3
    assert abs(set_match_score([1, 2, 3], [3, 2, 7]) - 2 / 3) < 0.01  # 2/3


def test_compute_score_perfect():
    """완벽한 예측의 스코어"""
    from prepare import compute_score

    prediction = {"predicted": [1, 2, 3], "confidence": 0.8, "reasoning": "test"}
    actual = [1, 2, 3]
    score = compute_score(prediction, actual)
    assert score["json_ok"] is True
    assert score["deferred"] is False
    assert score["set_match"] == 1.0
    assert score["correct_count"] == 3


def test_compute_score_deferred():
    """confidence < 0.3이면 defer 처리"""
    from prepare import compute_score

    prediction = {"predicted": [1, 2, 3], "confidence": 0.2, "reasoning": "low"}
    actual = [1, 2, 3]
    score = compute_score(prediction, actual)
    assert score["deferred"] is True


def test_compute_score_confidence_normalize():
    """confidence > 1.0이면 100으로 나눠서 정규화"""
    from prepare import compute_score

    prediction = {"predicted": [1, 2, 3], "confidence": 72, "reasoning": "high"}
    actual = [1, 2, 3]
    score = compute_score(prediction, actual)
    assert score["deferred"] is False  # 0.72 >= 0.3


def test_compute_score_invalid_schema():
    """스키마 불일치 시 json_ok=False"""
    from prepare import compute_score

    prediction = {"wrong_key": [1, 2, 3]}
    actual = [1, 2, 3]
    score = compute_score(prediction, actual)
    assert score["json_ok"] is False


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
