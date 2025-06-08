# 경마 예측 v5.0

배당률(win_odds)이 가장 낮은 3마리를 선택하세요.

주의:
- win_odds가 0인 말은 제외
- 같은 배당률이면 번호가 작은 말 선택

결과를 다음 형식으로:
{"selected_horses": [{"chul_no": 번호, "hr_name": "이름"}, {"chul_no": 번호, "hr_name": "이름"}, {"chul_no": 번호, "hr_name": "이름"}], "confidence": 80, "reasoning": "배당률 순"}