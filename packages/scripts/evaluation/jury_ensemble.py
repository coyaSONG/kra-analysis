"""
Jury 앙상블 시스템 - 가중 Borda Count

여러 모델의 예측을 Weighted Borda Count로 집계하여
최종 top-3 예측을 선출합니다.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from itertools import combinations


@dataclass
class JuryAggregation:
    """Jury 앙상블 집계 결과"""

    predicted: list[int]  # 최종 top-3 출전번호
    confidence: float  # 집계된 신뢰도
    model_predictions: dict[str, list[int]]  # 모델별 예측
    vote_counts: dict[int, float]  # 출전번호별 가중 투표 점수
    agreement_level: str  # "unanimous", "majority", "split"
    agreement_score: float  # 합의 점수 (0.0 ~ 1.0)
    consistency_score: float  # Jaccard 기반 교차 일관성


class JuryEnsemble:
    """가중 Borda Count 기반 Jury 앙상블

    각 모델의 예측에 가중치를 적용한 Borda Count로 투표하여
    최종 top-3를 선출합니다.

    Borda 점수: 1위=3점, 2위=2점, 3위=1점 (가중치 곱)
    """

    # 기본 Borda 점수: 순위별
    BORDA_POINTS = {0: 3, 1: 2, 2: 1}

    def __init__(self, model_weights: dict[str, float] | None = None):
        """
        Args:
            model_weights: 모델별 가중치 (예: {"claude": 1.0, "codex": 0.8, "gemini": 0.9})
                          None이면 모든 모델 동일 가중치(1.0)
        """
        self.model_weights = model_weights or {}

    def aggregate(self, model_predictions: dict[str, dict]) -> JuryAggregation:
        """모델별 예측을 가중 Borda Count로 집계.

        Args:
            model_predictions: {model_name: {"predicted": [1, 3, 5], "confidence": 70}}

        Returns:
            JuryAggregation: 집계 결과
        """
        vote_counts: dict[int, float] = defaultdict(float)
        pred_map: dict[str, list[int]] = {}
        confidences: list[float] = []

        for model_name, prediction in model_predictions.items():
            predicted = prediction.get("predicted", [])
            confidence = prediction.get("confidence", 50)
            weight = self.model_weights.get(model_name, 1.0)

            pred_map[model_name] = predicted
            confidences.append(confidence)

            # Borda Count 투표
            for rank, horse_no in enumerate(predicted[:3]):
                borda_points = self.BORDA_POINTS.get(rank, 0)
                vote_counts[horse_no] += borda_points * weight

        # 가중 투표 점수 기준 정렬 → top-3 선출
        sorted_horses = sorted(vote_counts.items(), key=lambda x: x[1], reverse=True)
        final_predicted = [h[0] for h in sorted_horses[:3]]

        # 신뢰도: 가중 평균
        total_weight = sum(self.model_weights.get(m, 1.0) for m in model_predictions)
        if total_weight > 0 and confidences:
            weights = [self.model_weights.get(m, 1.0) for m in model_predictions]
            avg_confidence = (
                sum(c * w for c, w in zip(confidences, weights, strict=False))
                / total_weight
            )
        else:
            avg_confidence = 50.0

        # 합의 분석
        agreement_level, agreement_score = self._compute_agreement(pred_map)

        # 일관성 점수
        consistency_score = self._compute_consistency(pred_map)

        return JuryAggregation(
            predicted=final_predicted,
            confidence=avg_confidence,
            model_predictions=pred_map,
            vote_counts=dict(vote_counts),
            agreement_level=agreement_level,
            agreement_score=agreement_score,
            consistency_score=consistency_score,
        )

    def _compute_agreement(self, pred_map: dict[str, list[int]]) -> tuple[str, float]:
        """합의 수준 판정.

        - unanimous: 모든 모델이 동일한 top-3 선택
        - majority: 2개 이상 모델이 2개 이상 공유
        - split: 그 외

        Returns:
            (agreement_level, agreement_score)
        """
        pred_sets = [set(p[:3]) for p in pred_map.values() if p]

        if len(pred_sets) < 2:
            return "unanimous", 1.0

        # 전체 교집합 크기
        intersection = pred_sets[0]
        for s in pred_sets[1:]:
            intersection = intersection & s

        if len(intersection) == 3:
            return "unanimous", 1.0

        # 쌍별 교집합 평균
        pair_overlaps = []
        for a, b in combinations(pred_sets, 2):
            pair_overlaps.append(len(a & b))

        avg_overlap = sum(pair_overlaps) / len(pair_overlaps) if pair_overlaps else 0

        if avg_overlap >= 2:
            score = avg_overlap / 3.0
            return "majority", score

        score = avg_overlap / 3.0
        return "split", score

    def _compute_consistency(self, pred_map: dict[str, list[int]]) -> float:
        """Jaccard similarity 기반 교차 일관성 점수.

        모든 모델 쌍의 Jaccard 유사도 평균을 반환합니다.
        """
        pred_sets = [set(p[:3]) for p in pred_map.values() if p]

        if len(pred_sets) < 2:
            return 1.0

        jaccard_scores = []
        for a, b in combinations(pred_sets, 2):
            union = a | b
            if not union:
                jaccard_scores.append(1.0)
            else:
                jaccard_scores.append(len(a & b) / len(union))

        return sum(jaccard_scores) / len(jaccard_scores) if jaccard_scores else 0.0
