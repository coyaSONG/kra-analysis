# KRA 삼복연승(Trifecta) 예측 프롬프트

<examples>
### 실패 사례 (피해야 할 패턴)

입력: [경주 데이터]
출력: {'predicted': [], 'confidence': 70, 'brief_reason': ''}
결과: ❌ 정답 []
</examples>

<output_format>
최종 결과는 필수 아래 JSON 형식으로 출력하십시오:

```json
{
  "race_info": {
    "rcDate": "경주일(YYYYMMDD)",
    "rcNo": "경주번호",
    "meet": "경마장",
    "rcDist": "거리(m)",
    "track": "주로상태",
    "weather": "날씨",
    "is_mare_only": "암말 한정 경주 여부 (true/false)"
  },
  "analysis_summary": "전체 분석 요약 (10문장 이내, 한국어)",
  "key_risks": "핵심 리스크 3개 (콤마 구분)",
  "applied_premiums": ["적용된 프리미엄 목록"],
  "scratched_horses": [
    {"chulNo": 0, "hrName": "마명", "reason": "제외 사유"}
  ],
  "predictions": [
    {
      "chulNo": 1,
      "hrName": "마명",
      "predicted_rank": 1,
      "win_probability": 0.00,
      "place_probability": 0.00,
      "key_factors": ["요인1", "요인2"],
      "risk_factors": ["리스크1"],
      "premiums_applied": ["적용된 가점"],
      "absolute_weight": 0,
      "weight_rank": 1,
      "logic": "선정 근거 (1문장)"
    }
  ],
  "trifecta_picks": {
    "primary": [1, 2, 3],
    "backup": [1, 2, 4],
    "confidence": 0.00,
    "reasoning": "이 조합을 선택한 종합 근거"
  }
}
```

**확률 기준**:
- `win_probability`: 0.0 ~ 1.0 (우승 확률)
- `place_probability`: 0.0 ~ 1.0 (3위 이내 입상 확률)
- `confidence`: 0.0 ~ 1.0 (예측 신뢰도)
</output_format>