"""Prediction prompt and response helpers for evaluation runs."""

from __future__ import annotations

import json
import re
from typing import Any


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


def parse_prediction_output(output: str, execution_time: float) -> dict[str, Any] | None:
    for candidate in _candidate_json_blobs(output):
        try:
            prediction = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        return normalize_prediction_payload(prediction, execution_time)

    return None


def normalize_prediction_payload(
    prediction: dict[str, Any], execution_time: float
) -> dict[str, Any]:
    normalized = dict(prediction)
    normalized["execution_time"] = execution_time

    if "selected_horses" not in normalized:
        if "predicted" in normalized:
            normalized["selected_horses"] = [
                {"chulNo": no} for no in normalized["predicted"]
            ]
        elif "prediction" in normalized:
            normalized["selected_horses"] = [
                {"chulNo": no} for no in normalized["prediction"]
            ]

    if "predicted" not in normalized and "selected_horses" in normalized:
        normalized["predicted"] = [
            horse.get("chulNo") for horse in normalized["selected_horses"]
        ]

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
