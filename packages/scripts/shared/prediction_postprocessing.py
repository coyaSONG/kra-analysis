"""예측 후보 리스트 후처리/검증 helpers.

원시 예측 payload를 경주별 후보 리스트로 정규화하고, 말 번호 형식/중복/개수
계약을 검증한다.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class NormalizedPredictionCandidate:
    rank: int
    chul_no: int
    score: float | None
    hr_name: str | None
    source_field: str
    raw_index: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "chulNo": self.chul_no,
            "score": self.score,
            "hrName": self.hr_name,
            "source_field": self.source_field,
            "raw_index": self.raw_index,
        }


@dataclass(frozen=True, slots=True)
class PredictionValidationIssue:
    code: str
    message: str
    source_field: str | None = None
    candidate_index: int | None = None
    raw_value: object | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "source_field": self.source_field,
            "candidate_index": self.candidate_index,
            "raw_value": self.raw_value,
        }


@dataclass(frozen=True, slots=True)
class PredictionPostprocessReport:
    valid: bool
    source_field: str | None
    raw_candidate_count: int
    normalized_candidate_count: int
    normalized_candidates: tuple[NormalizedPredictionCandidate, ...]
    issues: tuple[PredictionValidationIssue, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "source_field": self.source_field,
            "raw_candidate_count": self.raw_candidate_count,
            "normalized_candidate_count": self.normalized_candidate_count,
            "normalized_candidates": [
                candidate.to_dict() for candidate in self.normalized_candidates
            ],
            "issue_codes": [issue.code for issue in self.issues],
            "issues": [issue.to_dict() for issue in self.issues],
        }


@dataclass(frozen=True, slots=True)
class _RawCandidateSource:
    source_field: str | None
    raw_items: tuple[object, ...]
    issues: tuple[PredictionValidationIssue, ...]


def _coerce_positive_chul_no(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, float):
        if not math.isfinite(value) or not value.is_integer():
            return None
        number = int(value)
        return number if number > 0 else None
    if isinstance(value, str):
        text = value.strip()
        if not text or not text.isdigit():
            return None
        number = int(text)
        return number if number > 0 else None
    return None


def _as_sequence(value: object) -> tuple[object, ...] | None:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return tuple(value)
    return None


def _coerce_score(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(score):
        return None
    return score


def _extract_valid_chul_nos(
    payload: Mapping[str, Any],
    normalized_payload: Mapping[str, Any] | None,
    valid_chul_nos: Sequence[object] | None,
) -> set[int] | None:
    if valid_chul_nos is not None:
        valid = {
            chul_no
            for value in valid_chul_nos
            if (chul_no := _coerce_positive_chul_no(value)) is not None
        }
        return valid or None

    for container in (payload, normalized_payload):
        if not isinstance(container, Mapping):
            continue
        for field_name in ("horses", "entries"):
            items = _as_sequence(container.get(field_name))
            if items is None:
                continue
            valid = set()
            for item in items:
                raw_number, _, _ = _extract_candidate_fields(item)
                chul_no = _coerce_positive_chul_no(raw_number)
                if chul_no is not None:
                    valid.add(chul_no)
            if valid:
                return valid

    return None


def _register_score(
    score_lookup: dict[int, float],
    raw_chul_no: object,
    raw_score: object,
) -> None:
    chul_no = _coerce_positive_chul_no(raw_chul_no)
    score = _coerce_score(raw_score)
    if chul_no is None or score is None:
        return
    existing = score_lookup.get(chul_no)
    if existing is None or existing < score:
        score_lookup[chul_no] = score


def _build_score_lookup(
    payload: Mapping[str, Any],
    normalized_payload: Mapping[str, Any] | None,
) -> dict[int, float]:
    score_lookup: dict[int, float] = {}

    def register_sequence(
        value: object,
        *,
        score_keys: Sequence[str],
    ) -> None:
        items = _as_sequence(value)
        if items is None:
            return
        for item in items:
            if not isinstance(item, Mapping):
                continue
            raw_number, _, extracted_score = _extract_candidate_fields(item)
            if extracted_score is not None:
                _register_score(score_lookup, raw_number, extracted_score)
                continue
            for score_key in score_keys:
                if score_key in item:
                    _register_score(score_lookup, raw_number, item.get(score_key))
                    break

    for container in (payload, normalized_payload):
        if not isinstance(container, Mapping):
            continue
        register_sequence(
            container.get("predictions"),
            score_keys=(
                "primary_score",
                "model_score",
                "win_probability",
                "place_probability",
                "edge",
            ),
        )
        register_sequence(container.get("primary_scores"), score_keys=("score",))
        register_sequence(
            container.get("fallback_ranking"), score_keys=("primary_score",)
        )

        model_scores = container.get("model_scores")
        if isinstance(model_scores, Mapping):
            for raw_chul_no, raw_score in model_scores.items():
                _register_score(score_lookup, raw_chul_no, raw_score)

    return score_lookup


def _select_raw_candidate_source(
    payload: Mapping[str, Any],
    normalized_payload: Mapping[str, Any] | None,
) -> _RawCandidateSource:
    issues: list[PredictionValidationIssue] = []

    candidates: list[tuple[str, object | None]] = [
        ("selected_horses", payload.get("selected_horses")),
        ("predicted", payload.get("predicted")),
        ("prediction", payload.get("prediction")),
    ]

    trifecta_picks = payload.get("trifecta_picks")
    if isinstance(trifecta_picks, Mapping):
        candidates.append(("trifecta_picks.primary", trifecta_picks.get("primary")))

    for source_field, raw_value in candidates:
        if raw_value is None:
            continue
        sequence = _as_sequence(raw_value)
        if sequence is not None:
            return _RawCandidateSource(
                source_field=source_field,
                raw_items=sequence,
                issues=tuple(issues),
            )
        issues.append(
            PredictionValidationIssue(
                code="invalid_candidate_source_type",
                message=(f"{source_field} 필드는 리스트 형태여야 한다."),
                source_field=source_field,
                raw_value=raw_value,
            )
        )

    if normalized_payload is not None:
        for source_field in (
            "selected_horses",
            "primary_scores",
            "predictions",
        ):
            sequence = _as_sequence(normalized_payload.get(source_field))
            if sequence is not None:
                return _RawCandidateSource(
                    source_field=f"normalized.{source_field}",
                    raw_items=sequence,
                    issues=tuple(issues),
                )

    for source_field in ("primary_scores", "predictions"):
        sequence = _as_sequence(payload.get(source_field))
        if sequence is not None:
            return _RawCandidateSource(
                source_field=source_field,
                raw_items=sequence,
                issues=tuple(issues),
            )

    return _RawCandidateSource(
        source_field=None,
        raw_items=(),
        issues=tuple(issues),
    )


def _extract_candidate_fields(item: object) -> tuple[object, str | None, float | None]:
    if isinstance(item, Mapping):
        raw_number = None
        for key in ("chulNo", "horse_no", "horseNo", "number"):
            if key in item:
                raw_number = item.get(key)
                break
        hr_name = item.get("hrName")
        if hr_name is None:
            hr_name = item.get("horse_name")
        if hr_name is None:
            hr_name = item.get("name")
        score = None
        for key in (
            "score",
            "primary_score",
            "model_score",
            "win_probability",
            "place_probability",
            "edge",
        ):
            if key not in item:
                continue
            score = _coerce_score(item.get(key))
            if score is not None:
                break
        return raw_number, str(hr_name) if hr_name not in (None, "") else None, score
    return item, None, None


def _candidate_priority_key(
    candidate: NormalizedPredictionCandidate,
) -> tuple[int, float, int, int]:
    return (
        0 if candidate.score is not None else 1,
        -(candidate.score or 0.0),
        candidate.raw_index,
        candidate.chul_no,
    )


def _merge_duplicate_candidate(
    existing: NormalizedPredictionCandidate,
    incoming: NormalizedPredictionCandidate,
) -> NormalizedPredictionCandidate:
    preferred, fallback = sorted(
        (existing, incoming),
        key=_candidate_priority_key,
    )
    return NormalizedPredictionCandidate(
        rank=0,
        chul_no=preferred.chul_no,
        score=preferred.score if preferred.score is not None else fallback.score,
        hr_name=preferred.hr_name or fallback.hr_name,
        source_field=preferred.source_field,
        raw_index=preferred.raw_index,
    )


def _register_supplement_sequence(
    candidates: dict[int, NormalizedPredictionCandidate],
    value: object,
    *,
    source_field: str,
    score_lookup: Mapping[int, float],
    valid_numbers: set[int] | None,
) -> None:
    items = _as_sequence(value)
    if items is None:
        return

    for raw_index, raw_item in enumerate(items, start=1):
        raw_number, hr_name, raw_score = _extract_candidate_fields(raw_item)
        chul_no = _coerce_positive_chul_no(raw_number)
        if chul_no is None:
            continue
        if valid_numbers is not None and chul_no not in valid_numbers:
            continue

        candidate = NormalizedPredictionCandidate(
            rank=0,
            chul_no=chul_no,
            score=raw_score if raw_score is not None else score_lookup.get(chul_no),
            hr_name=hr_name,
            source_field=source_field,
            raw_index=raw_index,
        )
        existing = candidates.get(chul_no)
        if existing is None:
            candidates[chul_no] = candidate
            continue
        candidates[chul_no] = _merge_duplicate_candidate(existing, candidate)


def _register_supplement_mapping(
    candidates: dict[int, NormalizedPredictionCandidate],
    value: object,
    *,
    source_field: str,
    valid_numbers: set[int] | None,
) -> None:
    if not isinstance(value, Mapping):
        return

    for raw_index, (raw_chul_no, raw_score) in enumerate(value.items(), start=1):
        chul_no = _coerce_positive_chul_no(raw_chul_no)
        score = _coerce_score(raw_score)
        if chul_no is None or score is None:
            continue
        if valid_numbers is not None and chul_no not in valid_numbers:
            continue

        candidate = NormalizedPredictionCandidate(
            rank=0,
            chul_no=chul_no,
            score=score,
            hr_name=None,
            source_field=source_field,
            raw_index=raw_index,
        )
        existing = candidates.get(chul_no)
        if existing is None:
            candidates[chul_no] = candidate
            continue
        candidates[chul_no] = _merge_duplicate_candidate(existing, candidate)


def _build_supplement_candidates(
    payload: Mapping[str, Any],
    normalized_payload: Mapping[str, Any] | None,
    *,
    score_lookup: Mapping[int, float],
    valid_numbers: set[int] | None,
    excluded_chul_nos: set[int],
) -> list[NormalizedPredictionCandidate]:
    supplement_candidates: dict[int, NormalizedPredictionCandidate] = {}

    for container_name, container in (
        ("normalized", normalized_payload),
        ("raw", payload),
    ):
        if not isinstance(container, Mapping):
            continue

        _register_supplement_sequence(
            supplement_candidates,
            container.get("primary_scores"),
            source_field=f"{container_name}.primary_scores",
            score_lookup=score_lookup,
            valid_numbers=valid_numbers,
        )
        _register_supplement_sequence(
            supplement_candidates,
            container.get("predictions"),
            source_field=f"{container_name}.predictions",
            score_lookup=score_lookup,
            valid_numbers=valid_numbers,
        )
        _register_supplement_sequence(
            supplement_candidates,
            container.get("fallback_ranking"),
            source_field=f"{container_name}.fallback_ranking",
            score_lookup=score_lookup,
            valid_numbers=valid_numbers,
        )
        _register_supplement_mapping(
            supplement_candidates,
            container.get("model_scores"),
            source_field=f"{container_name}.model_scores",
            valid_numbers=valid_numbers,
        )

    return [
        candidate
        for candidate in sorted(
            supplement_candidates.values(),
            key=_candidate_priority_key,
        )
        if candidate.chul_no not in excluded_chul_nos
    ]


def _rank_candidates(
    candidates: Sequence[NormalizedPredictionCandidate],
    *,
    limit: int | None = None,
) -> list[NormalizedPredictionCandidate]:
    ordered_candidates = sorted(candidates, key=_candidate_priority_key)
    if limit is not None:
        ordered_candidates = ordered_candidates[:limit]

    return [
        NormalizedPredictionCandidate(
            rank=index,
            chul_no=candidate.chul_no,
            score=candidate.score,
            hr_name=candidate.hr_name,
            source_field=candidate.source_field,
            raw_index=candidate.raw_index,
        )
        for index, candidate in enumerate(ordered_candidates, start=1)
    ]


def postprocess_prediction_candidates(
    payload: Mapping[str, Any],
    *,
    normalized_payload: Mapping[str, Any] | None = None,
    valid_chul_nos: Sequence[object] | None = None,
) -> dict[str, Any]:
    """원시 예측 payload를 후보 리스트로 정규화하고 검증 report를 반환한다."""

    source = _select_raw_candidate_source(payload, normalized_payload)
    issues: list[PredictionValidationIssue] = list(source.issues)
    score_lookup = _build_score_lookup(payload, normalized_payload)
    valid_numbers = _extract_valid_chul_nos(payload, normalized_payload, valid_chul_nos)

    if not source.raw_items:
        issues.append(
            PredictionValidationIssue(
                code="missing_prediction_candidates",
                message="예측 후보 리스트를 찾지 못했다.",
                source_field=source.source_field,
            )
        )
        report = PredictionPostprocessReport(
            valid=False,
            source_field=source.source_field,
            raw_candidate_count=0,
            normalized_candidate_count=0,
            normalized_candidates=(),
            issues=tuple(issues),
        )
        return report.to_dict()

    merged_candidates: dict[int, NormalizedPredictionCandidate] = {}

    for raw_index, raw_item in enumerate(source.raw_items, start=1):
        raw_number, hr_name, raw_score = _extract_candidate_fields(raw_item)
        chul_no = _coerce_positive_chul_no(raw_number)
        if chul_no is None:
            issues.append(
                PredictionValidationIssue(
                    code="invalid_horse_number_format",
                    message="말 번호는 양의 정수 또는 숫자 문자열이어야 한다.",
                    source_field=source.source_field,
                    candidate_index=raw_index,
                    raw_value=raw_number,
                )
            )
            continue
        if valid_numbers is not None and chul_no not in valid_numbers:
            issues.append(
                PredictionValidationIssue(
                    code="horse_number_not_in_race_card",
                    message=f"말 번호 {chul_no}는 출전표 확정 시점 출주마 목록에 없다.",
                    source_field=source.source_field,
                    candidate_index=raw_index,
                    raw_value=raw_number,
                )
            )
            continue

        candidate = NormalizedPredictionCandidate(
            rank=0,
            chul_no=chul_no,
            score=raw_score if raw_score is not None else score_lookup.get(chul_no),
            hr_name=hr_name,
            source_field=source.source_field or "unknown",
            raw_index=raw_index,
        )
        existing = merged_candidates.get(chul_no)
        if existing is None:
            merged_candidates[chul_no] = candidate
            continue
        merged_candidates[chul_no] = _merge_duplicate_candidate(existing, candidate)

    normalized_candidates = _rank_candidates(merged_candidates.values(), limit=3)

    if len(normalized_candidates) < 3:
        selected_chul_nos = {candidate.chul_no for candidate in normalized_candidates}
        supplement_candidates = _build_supplement_candidates(
            payload,
            normalized_payload,
            score_lookup=score_lookup,
            valid_numbers=valid_numbers,
            excluded_chul_nos=selected_chul_nos,
        )
        for supplement in supplement_candidates:
            normalized_candidates.append(supplement)
            selected_chul_nos.add(supplement.chul_no)
            if len(normalized_candidates) == 3:
                break

        normalized_candidates = _rank_candidates(normalized_candidates, limit=3)

    if len(normalized_candidates) != 3:
        issues.append(
            PredictionValidationIssue(
                code="prediction_count_not_three",
                message=(
                    "정규화된 예측 후보 수가 3두가 아니다."
                    f" raw={len(source.raw_items)} normalized={len(normalized_candidates)}"
                ),
                source_field=source.source_field,
                raw_value=[candidate.chul_no for candidate in normalized_candidates],
            )
        )

    report = PredictionPostprocessReport(
        valid=len(issues) == 0,
        source_field=source.source_field,
        raw_candidate_count=len(source.raw_items),
        normalized_candidate_count=len(normalized_candidates),
        normalized_candidates=tuple(normalized_candidates),
        issues=tuple(issues),
    )
    return report.to_dict()
