#!/usr/bin/env python3
"""JSON 파싱 로직 테스트 - prediction 필드 지원 확인"""
import json
import re

# 실제 Claude CLI 출력 (prediction 필드 사용)
test_output = {
    "type": "result",
    "result": """```json
{"prediction": [4, 6, 3], "confidence": 0.72, "reasoning": "test"}
```"""
}

print("=== Testing prediction field parsing ===")
content = test_output['result']
print(f"Content: {content}")

# 코드블록 내 JSON 추출
code_block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
if code_block_match:
    print(f"\nCode block found: {code_block_match.group(1)}")
    prediction = json.loads(code_block_match.group(1))
    print(f"Parsed JSON: {prediction}")

    # prediction 필드를 selected_horses로 변환
    if "selected_horses" not in prediction:
        if "predicted" in prediction:
            prediction["selected_horses"] = [
                {"chulNo": no} for no in prediction["predicted"]
            ]
        elif "prediction" in prediction:
            prediction["selected_horses"] = [
                {"chulNo": no} for no in prediction["prediction"]
            ]

    print(f"\nAfter conversion:")
    print(f"selected_horses: {prediction.get('selected_horses')}")
    print(f"confidence: {prediction.get('confidence')}")
    print(f"reasoning: {prediction.get('reasoning')}")
else:
    print("No code block found!")
