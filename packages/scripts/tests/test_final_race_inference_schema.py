from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.final_race_inference_schema import (  # noqa: E402
    RESULT_SCHEMA_VERSION,
    normalize_final_race_inference_payload,
)


def test_result_schema_version_is_fixed():
    assert RESULT_SCHEMA_VERSION == "final-race-inference-v1"


def test_normalize_payload_derives_primary_scores_and_backup_ranking():
    payload = {
        "trifecta_picks": {"primary": [4, 1, 6], "backup": [4, 6, 1]},
        "predictions": [
            {"chulNo": 4, "hrName": "지리산", "win_probability": 0.32},
            {"chulNo": 1, "hrName": "캐논황후", "win_probability": 0.25},
            {"chulNo": 6, "hrName": "으뜸천하", "win_probability": 0.18},
        ],
        "confidence": 0.72,
        "reasoning": "primary result",
    }

    normalized = normalize_final_race_inference_payload(payload, execution_time=1.5)

    assert normalized["schema_version"] == RESULT_SCHEMA_VERSION
    assert normalized["predicted"] == [4, 1, 6]
    assert normalized["top3"] == [4, 1, 6]
    assert normalized["selected_horses"] == [
        {"chulNo": 4},
        {"chulNo": 1},
        {"chulNo": 6},
    ]
    assert normalized["primary_scores"] == [
        {"chulNo": 4, "score": 0.32, "hrName": "지리산", "source": "win_probability"},
        {"chulNo": 1, "score": 0.25, "hrName": "캐논황후", "source": "win_probability"},
        {"chulNo": 6, "score": 0.18, "hrName": "으뜸천하", "source": "win_probability"},
    ]
    assert normalized["fallback_ranking"] == [
        {
            "rank": 1,
            "chulNo": 4,
            "hrName": None,
            "primary_score": None,
            "source": "trifecta_picks.backup",
            "metadata": None,
        },
        {
            "rank": 2,
            "chulNo": 6,
            "hrName": None,
            "primary_score": None,
            "source": "trifecta_picks.backup",
            "metadata": None,
        },
        {
            "rank": 3,
            "chulNo": 1,
            "hrName": None,
            "primary_score": None,
            "source": "trifecta_picks.backup",
            "metadata": None,
        },
    ]
    assert normalized["fallback_meta"] == {
        "available": True,
        "applied": False,
        "reason_code": None,
        "reason": None,
        "source": "trifecta_picks.backup",
        "details": None,
    }
    assert normalized["fallback_used"] is False
    assert normalized["fallback_reason_code"] is None
    assert normalized["fallback_reason"] is None
    assert normalized["execution_time"] == 1.5


def test_normalize_payload_uses_primary_scores_for_final_candidate_generation():
    payload = {
        "model_scores": {"3": 0.45, "1": 0.91, "2": 0.62},
        "fallback_ranking": [
            {"rank": 1, "chulNo": 2, "source": "alternative_ranking_v1"},
            {"rank": 2, "chulNo": 1, "source": "alternative_ranking_v1"},
            {"rank": 3, "chulNo": 3, "source": "alternative_ranking_v1"},
        ],
    }

    normalized = normalize_final_race_inference_payload(payload)

    assert normalized["predicted"] == [1, 2, 3]
    assert normalized["selected_horses"] == [
        {"chulNo": 1},
        {"chulNo": 2},
        {"chulNo": 3},
    ]
    assert normalized["primary_scores"] == [
        {"chulNo": 1, "score": 0.91, "hrName": None, "source": "model_scores"},
        {"chulNo": 2, "score": 0.62, "hrName": None, "source": "model_scores"},
        {"chulNo": 3, "score": 0.45, "hrName": None, "source": "model_scores"},
    ]
    assert normalized["fallback_meta"]["available"] is True
    assert normalized["fallback_meta"]["applied"] is False


def test_normalize_payload_merges_primary_and_fallback_when_primary_scores_are_partial():
    payload = {
        "predictions": [
            {"chulNo": 4, "hrName": "에이스", "win_probability": 0.88},
            {"chulNo": 6, "hrName": "결측", "win_probability": None},
            {"chulNo": 1, "hrName": "비정상", "win_probability": "NaN"},
        ],
        "fallback_ranking": [
            {"rank": 1, "chulNo": 6, "source": "alternative_ranking_v1"},
            {"rank": 2, "chulNo": 4, "source": "alternative_ranking_v1"},
            {"rank": 3, "chulNo": 1, "source": "alternative_ranking_v1"},
        ],
    }

    normalized = normalize_final_race_inference_payload(payload)

    assert normalized["predicted"] == [4, 6, 1]
    assert normalized["top3"] == [4, 6, 1]
    assert normalized["selected_horses"] == [
        {"chulNo": 4},
        {"chulNo": 6},
        {"chulNo": 1},
    ]
    assert normalized["primary_scores"] == [
        {"chulNo": 4, "score": 0.88, "hrName": "에이스", "source": "win_probability"},
    ]
    assert normalized["fallback_meta"] == {
        "available": True,
        "applied": True,
        "reason_code": "PRIMARY_SCORES_PARTIAL",
        "reason": "primary 점수가 3두를 채우지 못해 fallback ranking으로 부족한 자리를 보강했다.",
        "source": "alternative_ranking_v1",
        "details": {
            "valid_primary_score_count": 1,
            "fallback_candidate_count": 3,
            "fallback_used_count": 2,
            "fallback_used_chul_nos": [6, 1],
        },
    }
    assert normalized["fallback_used"] is True
    assert normalized["fallback_reason_code"] == "PRIMARY_SCORES_PARTIAL"
    assert normalized["fallback_reason"] == normalized["fallback_meta"]["reason"]


def test_normalize_payload_uses_fallback_contract_when_primary_inputs_are_entirely_missing():
    payload = {
        "reasoning": "경주 단위 입력이 전량 결측이라 fallback ranking만 사용",
        "fallback_ranking": [
            {
                "rank": 1,
                "chulNo": 9,
                "hrName": "폴백1",
                "source": "alternative_ranking_v1",
            },
            {
                "rank": 2,
                "chulNo": 3,
                "hrName": "폴백2",
                "source": "alternative_ranking_v1",
            },
            {
                "rank": 3,
                "chulNo": 5,
                "hrName": "폴백3",
                "source": "alternative_ranking_v1",
            },
        ],
    }

    normalized = normalize_final_race_inference_payload(payload, execution_time=0.25)

    assert normalized["predicted"] == [9, 3, 5]
    assert normalized["top3"] == [9, 3, 5]
    assert normalized["selected_horses"] == [
        {"chulNo": 9},
        {"chulNo": 3},
        {"chulNo": 5},
    ]
    assert normalized["primary_scores"] == []
    assert normalized["fallback_ranking"] == [
        {
            "rank": 1,
            "chulNo": 9,
            "hrName": "폴백1",
            "primary_score": None,
            "source": "alternative_ranking_v1",
            "metadata": None,
        },
        {
            "rank": 2,
            "chulNo": 3,
            "hrName": "폴백2",
            "primary_score": None,
            "source": "alternative_ranking_v1",
            "metadata": None,
        },
        {
            "rank": 3,
            "chulNo": 5,
            "hrName": "폴백3",
            "primary_score": None,
            "source": "alternative_ranking_v1",
            "metadata": None,
        },
    ]
    assert normalized["fallback_meta"] == {
        "available": True,
        "applied": True,
        "reason_code": "PRIMARY_SCORES_MISSING",
        "reason": "primary 점수 입력이 없어 fallback ranking으로 최종 3두를 구성했다.",
        "source": "alternative_ranking_v1",
        "details": {
            "valid_primary_score_count": 0,
            "fallback_candidate_count": 3,
            "fallback_used_count": 3,
            "fallback_used_chul_nos": [9, 3, 5],
        },
    }
    assert normalized["fallback_used"] is True
    assert normalized["fallback_reason_code"] == "PRIMARY_SCORES_MISSING"
    assert normalized["fallback_reason"] == normalized["fallback_meta"]["reason"]
    assert normalized["execution_time"] == 0.25


def test_normalize_payload_keeps_primary_order_and_skips_duplicate_fallback_entries():
    payload = {
        "model_scores": {"4": 0.91, "1": 0.67},
        "fallback_ranking": [
            {"rank": 1, "chulNo": 1, "source": "alternative_ranking_v1"},
            {"rank": 2, "chulNo": 4, "source": "alternative_ranking_v1"},
            {"rank": 3, "chulNo": 7, "source": "alternative_ranking_v1"},
            {"rank": 4, "chulNo": 9, "source": "alternative_ranking_v1"},
        ],
    }

    normalized = normalize_final_race_inference_payload(payload)

    assert normalized["predicted"] == [4, 1, 7]
    assert normalized["selected_horses"] == [
        {"chulNo": 4},
        {"chulNo": 1},
        {"chulNo": 7},
    ]
    assert normalized["fallback_meta"]["applied"] is True
    assert normalized["fallback_meta"]["details"] == {
        "valid_primary_score_count": 2,
        "fallback_candidate_count": 3,
        "fallback_used_count": 1,
        "fallback_used_chul_nos": [7],
    }


def test_normalize_final_race_inference_payload_respects_explicit_fallback_meta():
    payload = {
        "predicted": [2, 1, 3],
        "model_scores": {"2": 0.91, "1": 0.33},
        "fallback_ranking": [
            {"rank": 1, "chulNo": 2, "primary_score": 0.91},
            {"rank": 2, "chulNo": 1, "primary_score": 0.33},
            {"rank": 3, "chulNo": 3, "primary_score": None},
        ],
        "fallback_meta": {
            "available": True,
            "applied": True,
            "reason_code": "PRIMARY_SCORES_PARTIAL",
            "reason": "일부 말의 점수가 비정상이어서 fallback ranking을 적용했다.",
            "source": "alternative_ranking_v1",
            "details": {"invalid_score_count": 1},
        },
    }

    normalized = normalize_final_race_inference_payload(payload)

    assert normalized["primary_scores"] == [
        {"chulNo": 2, "score": 0.91, "hrName": None, "source": "model_scores"},
        {"chulNo": 1, "score": 0.33, "hrName": None, "source": "model_scores"},
    ]
    assert normalized["fallback_meta"]["applied"] is True
    assert normalized["fallback_meta"]["reason_code"] == "PRIMARY_SCORES_PARTIAL"
    assert normalized["fallback_meta"]["source"] == "alternative_ranking_v1"
