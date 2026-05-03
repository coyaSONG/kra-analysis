"""최종 예측 산출물의 3두 고유 말 번호 계약을 강제하는 보정 래퍼.

`prediction_postprocessing`의 검증 결과를 입력으로 받아 허용된 오류
(중복/누락/형식 불일치)에 대해서만 결정적으로 3두를 보정한다.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from shared.prediction_postprocessing import (
    NormalizedPredictionCandidate,
    postprocess_prediction_candidates,
)

REPAIRABLE_ISSUE_CODES = frozenset(
    {
        "invalid_horse_number_format",
        "prediction_count_not_three",
    }
)


def _coerce_positive_chul_no(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, float):
        if not value.is_integer():
            return None
        number = int(value)
        return number if number > 0 else None
    if isinstance(value, str):
        text = value.strip()
        if not text.isdigit():
            return None
        number = int(text)
        return number if number > 0 else None
    return None


def _ordered_valid_chul_nos(valid_chul_nos: Sequence[object] | None) -> tuple[int, ...]:
    if valid_chul_nos is None:
        return ()

    ordered: list[int] = []
    seen: set[int] = set()
    for raw_value in valid_chul_nos:
        chul_no = _coerce_positive_chul_no(raw_value)
        if chul_no is None or chul_no in seen:
            continue
        ordered.append(chul_no)
        seen.add(chul_no)
    return tuple(ordered)


def _candidate_from_dict(
    item: Mapping[str, Any],
) -> NormalizedPredictionCandidate | None:
    chul_no = _coerce_positive_chul_no(item.get("chulNo"))
    rank = _coerce_positive_chul_no(item.get("rank"))
    raw_index = _coerce_positive_chul_no(item.get("raw_index"))
    if chul_no is None or rank is None or raw_index is None:
        return None
    score = item.get("score")
    score_value = float(score) if isinstance(score, (int, float)) else None
    hr_name = item.get("hrName")
    source_field = item.get("source_field")
    if not isinstance(source_field, str) or not source_field:
        return None
    return NormalizedPredictionCandidate(
        rank=rank,
        chul_no=chul_no,
        score=score_value,
        hr_name=str(hr_name) if isinstance(hr_name, str) and hr_name else None,
        source_field=source_field,
        raw_index=raw_index,
    )


def _repair_action(
    *,
    code: str,
    message: str,
    chul_no: int | None = None,
) -> dict[str, Any]:
    action = {
        "code": code,
        "message": message,
    }
    if chul_no is not None:
        action["chulNo"] = chul_no
    return action


@dataclass(frozen=True, slots=True)
class PredictionOutputGuardResult:
    accepted: bool
    repaired: bool
    repairable: bool
    final_candidates: tuple[NormalizedPredictionCandidate, ...]
    blocking_issue_codes: tuple[str, ...]
    repair_actions: tuple[dict[str, Any], ...]
    validation_report: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        validation = dict(self.validation_report)
        validation["normalized_candidates"] = [
            dict(candidate) for candidate in validation.get("normalized_candidates", [])
        ]
        validation["issues"] = [dict(issue) for issue in validation.get("issues", [])]
        return {
            "accepted": self.accepted,
            "repaired": self.repaired,
            "repairable": self.repairable,
            "final_predicted": [
                candidate.chul_no for candidate in self.final_candidates
            ],
            "final_selected_horses": [
                {"chulNo": candidate.chul_no} for candidate in self.final_candidates
            ],
            "final_candidates": [
                candidate.to_dict() for candidate in self.final_candidates
            ],
            "blocking_issue_codes": list(self.blocking_issue_codes),
            "repair_action_codes": [action["code"] for action in self.repair_actions],
            "repair_actions": [dict(action) for action in self.repair_actions],
            "validation_report": validation,
        }


def guard_prediction_output(
    payload: Mapping[str, Any],
    *,
    normalized_payload: Mapping[str, Any] | None = None,
    valid_chul_nos: Sequence[object] | None = None,
) -> dict[str, Any]:
    """예측 산출물을 검증하고 허용된 오류에 대해 3두 top3를 결정적으로 보정한다."""

    validation_report = postprocess_prediction_candidates(
        payload,
        normalized_payload=normalized_payload,
        valid_chul_nos=valid_chul_nos,
    )
    issue_codes = tuple(validation_report.get("issue_codes", []))
    blocking_issue_codes = tuple(
        code for code in issue_codes if code not in REPAIRABLE_ISSUE_CODES
    )
    repair_actions: list[dict[str, Any]] = []

    base_candidates: list[NormalizedPredictionCandidate] = []
    for raw_candidate in validation_report.get("normalized_candidates", []):
        if not isinstance(raw_candidate, Mapping):
            continue
        candidate = _candidate_from_dict(raw_candidate)
        if candidate is not None:
            base_candidates.append(candidate)

    final_candidates = list(base_candidates)
    selected_chul_nos = {candidate.chul_no for candidate in final_candidates}

    if validation_report.get("raw_candidate_count", 0) > validation_report.get(
        "normalized_candidate_count", 0
    ):
        repair_actions.append(
            _repair_action(
                code="deduped_or_trimmed_candidates",
                message="중복 또는 초과 후보를 제거해 top3 후보를 정규화했다.",
            )
        )

    if "invalid_horse_number_format" in issue_codes:
        repair_actions.append(
            _repair_action(
                code="discarded_invalid_format_candidates",
                message="형식이 잘못된 말 번호 후보를 버리고 유효 후보만 유지했다.",
            )
        )

    if not blocking_issue_codes and len(final_candidates) < 3:
        for chul_no in _ordered_valid_chul_nos(valid_chul_nos):
            if chul_no in selected_chul_nos:
                continue
            final_candidates.append(
                NormalizedPredictionCandidate(
                    rank=len(final_candidates) + 1,
                    chul_no=chul_no,
                    score=None,
                    hr_name=None,
                    source_field="race_card_fallback",
                    raw_index=0,
                )
            )
            selected_chul_nos.add(chul_no)
            repair_actions.append(
                _repair_action(
                    code="filled_from_race_card",
                    message="출전표 확정 시점 출주마 목록 순서로 누락된 자리를 채웠다.",
                    chul_no=chul_no,
                )
            )
            if len(final_candidates) == 3:
                break

    final_candidates = [
        NormalizedPredictionCandidate(
            rank=index,
            chul_no=candidate.chul_no,
            score=candidate.score,
            hr_name=candidate.hr_name,
            source_field=candidate.source_field,
            raw_index=candidate.raw_index,
        )
        for index, candidate in enumerate(final_candidates[:3], start=1)
    ]

    repaired = bool(repair_actions) or bool(issue_codes)
    accepted = len(final_candidates) == 3 and not blocking_issue_codes
    repairable = not blocking_issue_codes

    result = PredictionOutputGuardResult(
        accepted=accepted,
        repaired=repaired,
        repairable=repairable,
        final_candidates=tuple(final_candidates),
        blocking_issue_codes=blocking_issue_codes,
        repair_actions=tuple(repair_actions),
        validation_report=validation_report,
    )
    return result.to_dict()
