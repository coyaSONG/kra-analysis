"""경주별 최종 추론 결과 공통 계약.

LLM 응답과 결정론적 fallback 랭킹 결과를 동일한 필드명으로 저장하기 위한
경주 단위 DTO/정규화 헬퍼를 제공한다.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

RESULT_SCHEMA_VERSION = "final-race-inference-v1"


def _coerce_int(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _coerce_float(value: object) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _dedupe_top3(values: Sequence[object]) -> tuple[int, ...]:
    predicted: list[int] = []
    seen: set[int] = set()
    for value in values:
        chul_no = _coerce_int(value)
        if chul_no is None or chul_no in seen:
            continue
        predicted.append(chul_no)
        seen.add(chul_no)
        if len(predicted) == 3:
            break
    return tuple(predicted)


def _extract_predicted(payload: Mapping[str, Any]) -> tuple[int, ...]:
    raw_selected_horses = payload.get("selected_horses")
    if isinstance(raw_selected_horses, Sequence) and not isinstance(
        raw_selected_horses, (str, bytes)
    ):
        return _dedupe_top3(
            horse.get("chulNo")
            for horse in raw_selected_horses
            if isinstance(horse, Mapping)
        )

    for key in ("predicted", "prediction"):
        raw = payload.get(key)
        if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
            predicted = _dedupe_top3(raw)
            if predicted:
                return predicted

    trifecta_picks = payload.get("trifecta_picks")
    if isinstance(trifecta_picks, Mapping):
        primary = trifecta_picks.get("primary")
        if isinstance(primary, Sequence) and not isinstance(primary, (str, bytes)):
            return _dedupe_top3(primary)

    return ()


def _sort_primary_scores(
    entries: Sequence[PrimaryScoreEntry],
) -> tuple[PrimaryScoreEntry, ...]:
    deduped: dict[int, PrimaryScoreEntry] = {}
    for entry in entries:
        if entry.score is None:
            continue
        current = deduped.get(entry.chul_no)
        if current is None or (current.score or 0.0) < (entry.score or 0.0):
            deduped[entry.chul_no] = entry

    return tuple(
        sorted(
            deduped.values(),
            key=lambda entry: (
                -(entry.score or 0.0),
                entry.chul_no,
            ),
        )
    )


def _ordered_primary_top3(
    primary_scores: Sequence[PrimaryScoreEntry],
) -> tuple[int, ...]:
    return tuple(entry.chul_no for entry in _sort_primary_scores(primary_scores)[:3])


def _ordered_fallback_top3(
    fallback_ranking: Sequence[FallbackRankingEntry],
) -> tuple[int, ...]:
    ordered: list[int] = []
    seen: set[int] = set()
    for entry in sorted(
        fallback_ranking,
        key=lambda item: (
            item.rank,
            item.chul_no is None,
            item.chul_no or 0,
        ),
    ):
        if entry.chul_no is None or entry.chul_no in seen:
            continue
        ordered.append(entry.chul_no)
        seen.add(entry.chul_no)
        if len(ordered) == 3:
            break
    return tuple(ordered)


def _merge_primary_and_fallback_top3(
    primary_scores: Sequence[PrimaryScoreEntry],
    fallback_ranking: Sequence[FallbackRankingEntry],
) -> tuple[int, ...]:
    ordered: list[int] = list(_ordered_primary_top3(primary_scores))
    seen = set(ordered)
    if len(ordered) >= 3:
        return tuple(ordered[:3])

    for chul_no in _ordered_fallback_top3(fallback_ranking):
        if chul_no in seen:
            continue
        ordered.append(chul_no)
        seen.add(chul_no)
        if len(ordered) == 3:
            break

    return tuple(ordered)


def _has_primary_score_source(payload: Mapping[str, Any]) -> bool:
    raw_primary_scores = payload.get("primary_scores")
    if isinstance(raw_primary_scores, Sequence) and not isinstance(
        raw_primary_scores, (str, bytes)
    ):
        return True

    raw_model_scores = payload.get("model_scores")
    if isinstance(raw_model_scores, Mapping):
        return True

    raw_predictions = payload.get("predictions")
    if isinstance(raw_predictions, Sequence) and not isinstance(
        raw_predictions, (str, bytes)
    ):
        for item in raw_predictions:
            if not isinstance(item, Mapping):
                continue
            for field_name in (
                "primary_score",
                "model_score",
                "win_probability",
                "place_probability",
                "edge",
            ):
                if field_name in item:
                    return True

    return False


def _extract_primary_scores(
    payload: Mapping[str, Any],
) -> tuple[PrimaryScoreEntry, ...]:
    raw_primary_scores = payload.get("primary_scores")
    if isinstance(raw_primary_scores, Sequence) and not isinstance(
        raw_primary_scores, (str, bytes)
    ):
        entries: list[PrimaryScoreEntry] = []
        for item in raw_primary_scores:
            if not isinstance(item, Mapping):
                continue
            chul_no = _coerce_int(item.get("chulNo"))
            if chul_no is None:
                continue
            entries.append(
                PrimaryScoreEntry(
                    chul_no=chul_no,
                    score=_coerce_float(item.get("score")),
                    hr_name=str(item.get("hrName") or "") or None,
                    source=str(item.get("source") or "primary_scores"),
                )
            )
        return _sort_primary_scores(entries)

    raw_model_scores = payload.get("model_scores")
    if isinstance(raw_model_scores, Mapping):
        entries: list[PrimaryScoreEntry] = []
        for chul_no_raw, score_raw in raw_model_scores.items():
            chul_no = _coerce_int(chul_no_raw)
            if chul_no is None:
                continue
            entries.append(
                PrimaryScoreEntry(
                    chul_no=chul_no,
                    score=_coerce_float(score_raw),
                    source="model_scores",
                )
            )
        return _sort_primary_scores(entries)

    raw_predictions = payload.get("predictions")
    if isinstance(raw_predictions, Sequence) and not isinstance(
        raw_predictions, (str, bytes)
    ):
        candidates: list[PrimaryScoreEntry] = []
        for item in raw_predictions:
            if not isinstance(item, Mapping):
                continue
            chul_no = _coerce_int(item.get("chulNo"))
            if chul_no is None:
                continue
            score = None
            source = None
            for field_name in (
                "primary_score",
                "model_score",
                "win_probability",
                "place_probability",
                "edge",
            ):
                if item.get(field_name) is None:
                    continue
                score = _coerce_float(item.get(field_name))
                source = field_name
                break
            candidates.append(
                PrimaryScoreEntry(
                    chul_no=chul_no,
                    score=score,
                    hr_name=str(item.get("hrName") or "") or None,
                    source=source or "predictions",
                )
            )
        if candidates:
            return _sort_primary_scores(candidates)

    return ()


def _extract_fallback_ranking(
    payload: Mapping[str, Any],
) -> tuple[FallbackRankingEntry, ...]:
    raw_fallback_ranking = payload.get("fallback_ranking")
    if isinstance(raw_fallback_ranking, Sequence) and not isinstance(
        raw_fallback_ranking, (str, bytes)
    ):
        entries: list[FallbackRankingEntry] = []
        for item in raw_fallback_ranking:
            if not isinstance(item, Mapping):
                continue
            rank = _coerce_int(item.get("rank"))
            if rank is None:
                continue
            entries.append(
                FallbackRankingEntry(
                    rank=rank,
                    chul_no=_coerce_int(item.get("chulNo")),
                    hr_name=str(item.get("hrName") or "") or None,
                    primary_score=_coerce_float(item.get("primary_score")),
                    source=str(item.get("source") or "fallback_ranking"),
                    metadata=dict(item.get("metadata", {}))
                    if isinstance(item.get("metadata"), Mapping)
                    else None,
                )
            )
        return tuple(entries)

    trifecta_picks = payload.get("trifecta_picks")
    if isinstance(trifecta_picks, Mapping):
        backup = trifecta_picks.get("backup")
        if isinstance(backup, Sequence) and not isinstance(backup, (str, bytes)):
            entries = []
            for index, value in enumerate(backup, start=1):
                chul_no = _coerce_int(value)
                if chul_no is None:
                    continue
                entries.append(
                    FallbackRankingEntry(
                        rank=index,
                        chul_no=chul_no,
                        source="trifecta_picks.backup",
                    )
                )
            return tuple(entries)

    return ()


def _extract_fallback_meta(
    payload: Mapping[str, Any],
    fallback_ranking: Sequence[FallbackRankingEntry],
    *,
    primary_scores: Sequence[PrimaryScoreEntry],
    predicted: Sequence[int],
) -> FallbackReasonMetadata:
    raw_meta = payload.get("fallback_meta")
    if isinstance(raw_meta, Mapping):
        return FallbackReasonMetadata(
            available=bool(raw_meta.get("available", bool(fallback_ranking))),
            applied=bool(raw_meta.get("applied", False)),
            reason_code=str(raw_meta.get("reason_code") or "") or None,
            reason=str(raw_meta.get("reason") or "") or None,
            source=str(raw_meta.get("source") or "") or None,
            details=dict(raw_meta.get("details", {}))
            if isinstance(raw_meta.get("details"), Mapping)
            else None,
        )

    fallback_top3 = _ordered_fallback_top3(fallback_ranking)
    primary_top3 = _ordered_primary_top3(primary_scores)
    predicted_tuple = tuple(predicted)
    fallback_set = set(fallback_top3)
    fallback_contribution = tuple(
        chul_no
        for chul_no in predicted_tuple
        if chul_no in fallback_set and chul_no not in set(primary_top3)
    )
    fallback_applied = bool(fallback_contribution)

    if fallback_applied:
        reason_code = (
            "PRIMARY_SCORES_PARTIAL"
            if _has_primary_score_source(payload)
            else "PRIMARY_SCORES_MISSING"
        )
        reason = (
            "primary 점수가 3두를 채우지 못해 fallback ranking으로 부족한 자리를 보강했다."
            if reason_code == "PRIMARY_SCORES_PARTIAL"
            else "primary 점수 입력이 없어 fallback ranking으로 최종 3두를 구성했다."
        )
        return FallbackReasonMetadata(
            available=True,
            applied=True,
            reason_code=reason_code,
            reason=reason,
            source=fallback_ranking[0].source if fallback_ranking else None,
            details={
                "valid_primary_score_count": len(primary_top3),
                "fallback_candidate_count": len(fallback_top3),
                "fallback_used_count": len(fallback_contribution),
                "fallback_used_chul_nos": list(fallback_contribution),
            },
        )

    return FallbackReasonMetadata(
        available=bool(fallback_ranking),
        applied=False,
        source=fallback_ranking[0].source if fallback_ranking else None,
    )


@dataclass(frozen=True, slots=True)
class PrimaryScoreEntry:
    chul_no: int
    score: float | None = None
    hr_name: str | None = None
    source: str = "primary_model"

    def to_dict(self) -> dict[str, Any]:
        return {
            "chulNo": self.chul_no,
            "score": self.score,
            "hrName": self.hr_name,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class FallbackRankingEntry:
    rank: int
    chul_no: int | None = None
    hr_name: str | None = None
    primary_score: float | None = None
    source: str = "fallback_ranking"
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "chulNo": self.chul_no,
            "hrName": self.hr_name,
            "primary_score": self.primary_score,
            "source": self.source,
            "metadata": self.metadata,
        }


@dataclass(frozen=True, slots=True)
class FallbackReasonMetadata:
    available: bool
    applied: bool
    reason_code: str | None = None
    reason: str | None = None
    source: str | None = None
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "applied": self.applied,
            "reason_code": self.reason_code,
            "reason": self.reason,
            "source": self.source,
            "details": self.details,
        }


@dataclass(frozen=True, slots=True)
class FinalRaceInferenceResult:
    predicted: tuple[int, ...]
    confidence: float | None = None
    reasoning: str = ""
    primary_scores: tuple[PrimaryScoreEntry, ...] = field(default_factory=tuple)
    fallback_ranking: tuple[FallbackRankingEntry, ...] = field(default_factory=tuple)
    fallback_meta: FallbackReasonMetadata = field(
        default_factory=lambda: FallbackReasonMetadata(available=False, applied=False)
    )
    execution_time: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": RESULT_SCHEMA_VERSION,
            "predicted": list(self.predicted),
            "top3": list(self.predicted),
            "selected_horses": [{"chulNo": chul_no} for chul_no in self.predicted],
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "primary_scores": [entry.to_dict() for entry in self.primary_scores],
            "fallback_ranking": [entry.to_dict() for entry in self.fallback_ranking],
            "fallback_meta": self.fallback_meta.to_dict(),
            "fallback_used": self.fallback_meta.applied,
            "fallback_reason_code": self.fallback_meta.reason_code,
            "fallback_reason": self.fallback_meta.reason,
            "execution_time": self.execution_time,
        }


def normalize_final_race_inference_payload(
    payload: Mapping[str, Any],
    *,
    execution_time: float | None = None,
) -> dict[str, Any]:
    """입력 payload를 경주별 공통 최종 추론 결과 계약으로 정규화한다."""

    primary_scores = _extract_primary_scores(payload)
    fallback_ranking = _extract_fallback_ranking(payload)
    primary_predicted = _ordered_primary_top3(primary_scores)
    merged_predicted = _merge_primary_and_fallback_top3(
        primary_scores, fallback_ranking
    )
    legacy_predicted = _extract_predicted(payload)
    if len(merged_predicted) == 3:
        predicted = merged_predicted
    elif len(primary_predicted) == 3:
        predicted = primary_predicted
    else:
        predicted = legacy_predicted
    fallback_meta = _extract_fallback_meta(
        payload,
        fallback_ranking,
        primary_scores=primary_scores,
        predicted=predicted,
    )
    confidence = _coerce_float(payload.get("confidence"))
    reasoning = str(payload.get("reasoning") or "")

    result = FinalRaceInferenceResult(
        predicted=predicted,
        confidence=confidence,
        reasoning=reasoning,
        primary_scores=primary_scores,
        fallback_ranking=fallback_ranking,
        fallback_meta=fallback_meta,
        execution_time=execution_time,
    )
    return result.to_dict()
