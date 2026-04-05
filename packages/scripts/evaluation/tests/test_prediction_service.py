import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from evaluation.prediction_service import (
    build_prediction_prompt,
    normalize_prediction_payload,
    parse_prediction_output,
)


def test_build_prediction_prompt_embeds_json_payload():
    prompt = build_prediction_prompt(
        "PROMPT",
        {"raceInfo": {"rcDate": "20240719"}, "horses": [{"chulNo": 1}]},
    )

    assert "PROMPT" in prompt
    assert '"chulNo": 1' in prompt
    assert "selected_horses" in prompt


def test_parse_prediction_output_normalizes_code_block():
    output = """```json
{"predicted":[1,2,3],"confidence":80}
```"""

    parsed = parse_prediction_output(output, 1.25)

    assert parsed is not None
    assert parsed["execution_time"] == 1.25
    assert parsed["predicted"] == [1, 2, 3]
    assert parsed["selected_horses"] == [
        {"chulNo": 1},
        {"chulNo": 2},
        {"chulNo": 3},
    ]


def test_normalize_prediction_payload_preserves_selected_horses():
    normalized = normalize_prediction_payload(
        {"selected_horses": [{"chulNo": 9}], "confidence": 10}, execution_time=0.3
    )

    assert normalized["execution_time"] == 0.3
    assert normalized["predicted"] == [9]
    assert normalized["selected_horses"] == [{"chulNo": 9}]
