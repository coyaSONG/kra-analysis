# 경마 예측 v5.1

다음 규칙으로 3마리를 선택하세요:

1. 기본: win_odds가 낮은 순으로 1-4위 중 3마리
2. 단, 5-6위 말이 다음 중 하나면 포함 고려:
   - 기수의 최근 3경주 승률 30% 이상
   - 같은 조교사의 다른 말이 최근 입상
3. win_odds가 0인 말은 항상 제외

결과: {"selected_horses": [{"chul_no": 번호, "hr_name": "이름"}, {"chul_no": 번호, "hr_name": "이름"}, {"chul_no": 번호, "hr_name": "이름"}], "confidence": 75, "reasoning": "선택 근거"}