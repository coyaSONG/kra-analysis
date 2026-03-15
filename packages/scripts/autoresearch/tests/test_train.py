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
