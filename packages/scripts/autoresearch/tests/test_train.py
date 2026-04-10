"""train.py 단위 테스트"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_predict_returns_correct_schema():
    """predict()가 올바른 스키마를 반환하는지"""
    from train import predict

    race_data = {
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
                "hrName": "테스트1",
                "winOdds": 3.0,
                "computed_features": {"odds_rank": 1},
            },
            {
                "chulNo": 2,
                "hrName": "테스트2",
                "winOdds": 5.0,
                "computed_features": {"odds_rank": 2},
            },
            {
                "chulNo": 3,
                "hrName": "테스트3",
                "winOdds": 8.0,
                "computed_features": {"odds_rank": 3},
            },
        ],
    }

    # mock call_llm
    def mock_llm(system: str, user: str) -> str:
        return '{"predicted": [1, 2, 3], "confidence": 0.7, "reasoning": "test"}'

    result = predict(race_data, call_llm=mock_llm)
    assert "predicted" in result
    assert "confidence" in result
    assert "reasoning" in result
    assert len(result["predicted"]) == 3


def test_predict_filters_abnormal_runner_from_llm_output():
    """LLM이 비정상 출전마를 포함해도 최종 예측에서는 제외되는지"""
    from train import predict

    race_data = {
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
                "hrName": "정상1",
                "winOdds": 3.0,
                "rating": 90,
                "computed_features": {"odds_rank": 1},
            },
            {
                "chulNo": 2,
                "hrName": "정상2",
                "winOdds": 4.5,
                "rating": 86,
                "computed_features": {"odds_rank": 2},
            },
            {
                "chulNo": 3,
                "hrName": "정상3",
                "winOdds": 6.0,
                "rating": 82,
                "computed_features": {"odds_rank": 3},
            },
            {
                "chulNo": 4,
                "hrName": "기권마",
                "winOdds": 0.0,
                "plcOdds": 0.0,
                "rating": 95,
                "computed_features": {"odds_rank": 4},
            },
        ],
    }

    def mock_llm(system: str, user: str) -> str:
        return '{"predicted": [4, 1, 2], "confidence": 0.8, "reasoning": "invalid horse included"}'

    result = predict(race_data, call_llm=mock_llm)

    assert len(result["predicted"]) == 3
    assert 4 not in result["predicted"]
    assert set(result["predicted"]) == {1, 2, 3}
    assert "제외=zero_market_signal:1" in result["reasoning"]
    assert "플래그=market_signal_missing:1" in result["reasoning"]


def test_parse_response_handles_json():
    """parse_response가 JSON을 올바르게 파싱하는지"""
    from train import parse_response

    raw = '{"predicted": [1, 5, 3], "confidence": 0.72, "reasoning": "test"}'
    result = parse_response(raw)
    assert result["predicted"] == [1, 5, 3]
    assert result["confidence"] == 0.72


def test_parse_response_handles_code_block():
    """parse_response가 코드블록 안의 JSON도 파싱하는지"""
    from train import parse_response

    raw = '```json\n{"predicted": [1, 5, 3], "confidence": 0.72, "reasoning": "test"}\n```'
    result = parse_response(raw)
    assert result["predicted"] == [1, 5, 3]


def test_parse_response_handles_malformed():
    """parse_response가 파싱 불가 시 parse_error를 반환하는지"""
    from train import parse_response

    raw = "this is not json at all, no brackets nothing"
    result = parse_response(raw)
    assert result["reasoning"] == "parse_error"
    assert result["predicted"] == []
    assert result["confidence"] == 0.0


def test_build_prompt_returns_tuple():
    """build_prompt가 (system, user) 튜플을 반환하는지"""
    from train import build_prompt

    features = {
        "race_info": {
            "rcDate": "20250101",
            "rcNo": "1",
            "meet": "서울",
            "rcDist": "1200",
        },
        "horses": [
            {
                "chulNo": 1,
                "hrName": "테스트마",
                "winOdds": 3.0,
                "computed_features": {"odds_rank": 1},
            },
        ],
    }
    result = build_prompt(features)
    assert isinstance(result, tuple)
    assert len(result) == 2
    system, user = result
    assert isinstance(system, str)
    assert isinstance(user, str)
    assert len(system) > 0
    assert len(user) > 0


def test_build_prompt_includes_candidate_filter_summary_and_flags():
    from train import build_prompt

    features = {
        "race_info": {
            "rcDate": "20250101",
            "rcNo": "1",
            "meet": "서울",
            "rcDist": "1200",
        },
        "candidate_filter": {
            "status_counts": {"normal": 1},
            "exclusion_rule_counts": {"wg_budam_outlier": 1},
            "flag_counts": {"weight_delta_missing": 1},
        },
        "horses": [
            {
                "chulNo": 1,
                "hrName": "테스트마",
                "winOdds": 3.0,
                "quality_flags": ["weight_delta_missing"],
                "computed_features": {"odds_rank": 1},
            },
        ],
    }

    _system, user = build_prompt(features)

    assert "후보 필터 요약" in user
    assert "wg_budam_outlier" in user
    assert "weight_delta_missing" in user


def test_predict_blank_response_uses_deterministic_alternative_ranking() -> None:
    from train import predict

    race_data = {
        "race_info": {
            "rcDate": "20250101",
            "rcNo": "1",
            "meet": "서울",
            "rcDist": "1400",
            "track": "건조",
            "weather": "맑음",
            "budam": "별정A",
            "ageCond": "3세이상",
        },
        "horses": [
            {
                "chulNo": 1,
                "hrNo": "001",
                "hrName": "고레이팅저입상",
                "rating": 96,
                "wgBudam": 56,
                "hrDetail": {
                    "rcCntY": 12,
                    "ord1CntY": 1,
                    "ord2CntY": 0,
                    "ord3CntY": 0,
                    "rcCntT": 30,
                    "ord1CntT": 2,
                    "ord2CntT": 1,
                    "ord3CntT": 1,
                },
                "computed_features": {"horse_top3_skill": 0.2},
            },
            {
                "chulNo": 2,
                "hrNo": "002",
                "hrName": "안정형",
                "rating": 75,
                "wgBudam": 54,
                "hrDetail": {
                    "rcCntY": 12,
                    "ord1CntY": 4,
                    "ord2CntY": 1,
                    "ord3CntY": 1,
                    "rcCntT": 30,
                    "ord1CntT": 8,
                    "ord2CntT": 3,
                    "ord3CntT": 2,
                },
                "computed_features": {"horse_top3_skill": 0.2},
            },
            {
                "chulNo": 3,
                "hrNo": "003",
                "hrName": "보통형",
                "rating": 80,
                "wgBudam": 55,
                "hrDetail": {
                    "rcCntY": 12,
                    "ord1CntY": 2,
                    "ord2CntY": 1,
                    "ord3CntY": 1,
                    "rcCntT": 30,
                    "ord1CntT": 5,
                    "ord2CntT": 2,
                    "ord3CntT": 2,
                },
                "computed_features": {"horse_top3_skill": 0.1},
            },
        ],
    }

    def mock_llm(system: str, user: str) -> str:
        return ""

    result = predict(race_data, call_llm=mock_llm)

    assert result["predicted"] == [2, 1, 3]
    assert result["confidence"] >= 0.55
