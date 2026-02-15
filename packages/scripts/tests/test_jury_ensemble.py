"""JuryEnsemble 단위 테스트"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluation.jury_ensemble import JuryEnsemble


class TestJuryEnsembleUnanimous:
    """모든 모델이 동일한 top-3을 예측하는 경우"""

    def test_unanimous_prediction(self):
        ensemble = JuryEnsemble()
        model_predictions = {
            "claude": {"predicted": [1, 2, 3], "confidence": 80},
            "codex": {"predicted": [1, 2, 3], "confidence": 70},
            "gemini": {"predicted": [1, 2, 3], "confidence": 90},
        }

        result = ensemble.aggregate(model_predictions)

        assert result.predicted == [1, 2, 3]
        assert result.agreement_level == "unanimous"
        assert result.agreement_score == 1.0
        assert result.consistency_score == 1.0
        # 동일 가중치(1.0)이므로 평균 confidence = (80+70+90)/3 = 80
        assert abs(result.confidence - 80.0) < 0.1


class TestJuryEnsembleMajority:
    """2개 모델이 유사한 예측, 1개가 다른 경우"""

    def test_majority_prediction(self):
        ensemble = JuryEnsemble()
        model_predictions = {
            "claude": {"predicted": [1, 2, 3], "confidence": 80},
            "codex": {"predicted": [1, 2, 5], "confidence": 70},
            "gemini": {"predicted": [4, 6, 7], "confidence": 60},
        }

        result = ensemble.aggregate(model_predictions)

        # 1번 말: claude(3pt) + codex(3pt) = 6pt → 1위
        # 2번 말: claude(2pt) + codex(2pt) = 4pt → 2위
        # 3번 말: claude(1pt) = 1pt
        # 5번 말: codex(1pt) = 1pt
        # 4번 말: gemini(3pt) = 3pt → 3위
        assert result.predicted[0] == 1
        assert result.predicted[1] == 2
        assert result.predicted[2] == 4  # gemini 1위(3pt) > claude 3위(1pt)

    def test_majority_agreement_level(self):
        ensemble = JuryEnsemble()
        model_predictions = {
            "claude": {"predicted": [1, 2, 3], "confidence": 80},
            "codex": {"predicted": [1, 2, 4], "confidence": 70},
            "gemini": {"predicted": [1, 5, 6], "confidence": 60},
        }

        result = ensemble.aggregate(model_predictions)
        # claude-codex: {1,2} overlap=2, claude-gemini: {1} overlap=1, codex-gemini: {1} overlap=1
        # avg_overlap = (2+1+1)/3 = 1.33 < 2 → split
        assert result.agreement_level in ("majority", "split")


class TestJuryEnsembleSplit:
    """모든 모델이 완전히 다른 예측을 하는 경우"""

    def test_split_prediction(self):
        ensemble = JuryEnsemble()
        model_predictions = {
            "claude": {"predicted": [1, 2, 3], "confidence": 80},
            "codex": {"predicted": [4, 5, 6], "confidence": 70},
            "gemini": {"predicted": [7, 8, 9], "confidence": 60},
        }

        result = ensemble.aggregate(model_predictions)

        assert result.agreement_level == "split"
        assert result.consistency_score == 0.0
        assert len(result.predicted) == 3


class TestJuryEnsembleWeights:
    """모델별 가중치가 적용되는 경우"""

    def test_weighted_aggregation(self):
        ensemble = JuryEnsemble(
            model_weights={"claude": 2.0, "codex": 1.0, "gemini": 0.5}
        )
        model_predictions = {
            "claude": {"predicted": [1, 2, 3], "confidence": 80},
            "codex": {"predicted": [4, 5, 6], "confidence": 70},
            "gemini": {"predicted": [7, 8, 9], "confidence": 60},
        }

        result = ensemble.aggregate(model_predictions)

        # claude의 1위(1번): 3pt * 2.0 = 6pt → 가장 높아야 함
        assert result.predicted[0] == 1
        # claude의 2위(2번): 2pt * 2.0 = 4pt
        assert result.predicted[1] == 2

    def test_weighted_confidence(self):
        ensemble = JuryEnsemble(
            model_weights={"claude": 2.0, "codex": 1.0, "gemini": 1.0}
        )
        model_predictions = {
            "claude": {"predicted": [1, 2, 3], "confidence": 100},
            "codex": {"predicted": [1, 2, 3], "confidence": 0},
            "gemini": {"predicted": [1, 2, 3], "confidence": 0},
        }

        result = ensemble.aggregate(model_predictions)
        # weighted avg: (100*2 + 0*1 + 0*1) / (2+1+1) = 50
        assert abs(result.confidence - 50.0) < 0.1


class TestJuryEnsembleEdgeCases:
    def test_single_model(self):
        ensemble = JuryEnsemble()
        model_predictions = {
            "claude": {"predicted": [1, 2, 3], "confidence": 80},
        }

        result = ensemble.aggregate(model_predictions)
        assert result.predicted == [1, 2, 3]
        assert result.agreement_level == "unanimous"
        assert result.consistency_score == 1.0

    def test_empty_predictions(self):
        ensemble = JuryEnsemble()
        result = ensemble.aggregate({})
        assert result.predicted == []
        assert result.confidence == 50.0

    def test_partial_predictions(self):
        """모델이 3개 미만의 예측을 하는 경우"""
        ensemble = JuryEnsemble()
        model_predictions = {
            "claude": {"predicted": [1, 2], "confidence": 80},
            "codex": {"predicted": [1], "confidence": 70},
        }

        result = ensemble.aggregate(model_predictions)
        assert 1 in result.predicted  # 두 모델이 공통으로 예측한 1번은 반드시 포함
        assert len(result.predicted) <= 3


class TestConsistencyScore:
    def test_perfect_consistency(self):
        ensemble = JuryEnsemble()
        model_predictions = {
            "claude": {"predicted": [1, 2, 3], "confidence": 80},
            "codex": {"predicted": [1, 2, 3], "confidence": 70},
        }
        result = ensemble.aggregate(model_predictions)
        assert result.consistency_score == 1.0

    def test_no_consistency(self):
        ensemble = JuryEnsemble()
        model_predictions = {
            "claude": {"predicted": [1, 2, 3], "confidence": 80},
            "codex": {"predicted": [4, 5, 6], "confidence": 70},
        }
        result = ensemble.aggregate(model_predictions)
        assert result.consistency_score == 0.0

    def test_partial_consistency(self):
        ensemble = JuryEnsemble()
        model_predictions = {
            "claude": {"predicted": [1, 2, 3], "confidence": 80},
            "codex": {"predicted": [1, 4, 5], "confidence": 70},
        }
        result = ensemble.aggregate(model_predictions)
        # Jaccard: |{1}| / |{1,2,3,4,5}| = 1/5 = 0.2
        assert abs(result.consistency_score - 0.2) < 0.01
