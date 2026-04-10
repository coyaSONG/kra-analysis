"""Prediction prompt and response helpers for evaluation runs."""

from __future__ import annotations

import json
import re
from typing import Any

from shared.final_race_inference_schema import normalize_final_race_inference_payload
from shared.prediction_output_guard import guard_prediction_output

FINAL_OUTPUT_FORMAT_VERSION = "unordered-top3-unique-v1"


def build_prediction_prompt(prompt_template: str, race_data: dict[str, Any]) -> str:
    return f"""{prompt_template}

경주 데이터:
```json
{json.dumps(race_data, ensure_ascii=False, indent=2)}
```

다음 JSON 형식으로 예측 결과를 제공하세요:
{{
  "selected_horses": [
    {{"chulNo": 번호, "hrName": "말이름"}},
    {{"chulNo": 번호, "hrName": "말이름"}},
    {{"chulNo": 번호, "hrName": "말이름"}}
  ],
  "confidence": 70,
  "reasoning": "1위 인기마 포함, 기수 성적 우수"
}}"""


def parse_prediction_output(
    output: str, execution_time: float, race_data: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    for candidate in _candidate_json_blobs(output):
        try:
            prediction = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        finalized = finalize_prediction_payload(
            prediction,
            execution_time=execution_time,
            race_data=race_data,
        )
        if finalized is not None:
            return finalized

    return None


def normalize_prediction_payload(
    prediction: dict[str, Any],
    execution_time: float,
    *,
    race_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = normalize_final_race_inference_payload(
        prediction,
        execution_time=execution_time,
    )
    valid_chul_nos = (
        [
            horse.get("chulNo")
            for horse in race_data.get("horses", [])
            if isinstance(horse, dict)
        ]
        if isinstance(race_data, dict)
        else None
    )

    # 기존 소비자가 기대하는 원본 부가 필드는 보존한다.
    for key, value in prediction.items():
        if key not in normalized:
            normalized[key] = value

    normalized["prediction_correction"] = guard_prediction_output(
        prediction,
        normalized_payload=normalized,
        valid_chul_nos=valid_chul_nos,
    )
    validation_report = dict(normalized["prediction_correction"]["validation_report"])
    validation_report["normalized_candidates"] = list(
        normalized["prediction_correction"].get("final_candidates", [])
    )
    validation_report["normalized_candidate_count"] = len(
        validation_report["normalized_candidates"]
    )
    normalized["prediction_validation"] = validation_report

    corrected_predicted = normalized["prediction_correction"].get("final_predicted", [])
    if len(corrected_predicted) == 3:
        predicted = [int(chul_no) for chul_no in corrected_predicted]
        normalized["predicted"] = predicted
        normalized["top3"] = list(predicted)
        normalized["selected_horses"] = [{"chulNo": chul_no} for chul_no in predicted]

    return normalized


def finalize_prediction_payload(
    prediction: dict[str, Any],
    *,
    race_data: dict[str, Any] | None = None,
    execution_time: float | None = None,
) -> dict[str, Any] | None:
    """저장/평가 직전 전달용 최종 산출물을 3두 고유 형식으로 강제한다."""

    resolved_execution_time = execution_time
    if resolved_execution_time is None:
        try:
            resolved_execution_time = float(prediction.get("execution_time", 0.0))
        except (TypeError, ValueError):
            resolved_execution_time = 0.0

    normalized = normalize_prediction_payload(
        prediction,
        execution_time=resolved_execution_time,
        race_data=race_data,
    )

    correction = normalized.get("prediction_correction", {})
    if correction.get("accepted") is not True:
        return None

    final_predicted = correction.get("final_predicted", [])
    if not isinstance(final_predicted, list):
        return None

    canonical_predicted: list[int] = []
    seen: set[int] = set()
    for raw_chul_no in final_predicted:
        try:
            chul_no = int(raw_chul_no)
        except (TypeError, ValueError):
            return None
        if chul_no <= 0 or chul_no in seen:
            return None
        canonical_predicted.append(chul_no)
        seen.add(chul_no)

    if len(canonical_predicted) != 3:
        return None

    normalized["predicted"] = list(canonical_predicted)
    normalized["top3"] = list(canonical_predicted)
    normalized["selected_horses"] = [
        {"chulNo": chul_no} for chul_no in canonical_predicted
    ]
    normalized["prediction_output_format"] = {
        "version": FINAL_OUTPUT_FORMAT_VERSION,
        "predicted_count": 3,
        "is_unique": True,
    }
    return normalized


def _candidate_json_blobs(output: str) -> list[str]:
    candidates = [output.strip()]

    code_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", output, re.DOTALL)
    if code_block_match:
        candidates.append(code_block_match.group(1))

    loose_match = re.search(
        r'\{[^{}]*"(?:selected_horses|predicted|prediction)"[^{}]*\}',
        output,
        re.DOTALL,
    )
    if loose_match:
        candidates.append(loose_match.group(0))

    return candidates
