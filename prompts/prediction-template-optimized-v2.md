# 경마 예측 v10.3 - 복합 전략

삼복연승 예측. winOdds=0 제외.

## 핵심 지표
1. **복합 점수** = (배당률 순위 점수) + (기수 실력) + (말 실력)
   - 배당률 순위 점수: 1위(10점), 2위(8점), 3위(6점), 4위(4점), 5위(2점), 6위 이하(1점)
   - 기수 실력: 승률(ord1CntT/rcCntT) × 20
   - 말 실력: 입상률((ord1CntT+ord2CntT+ord3CntT)/rcCntT) × 10

## 선택
복합 점수 상위 3개 선택

{"selected_horses": [{"chulNo": 번호, "hrName": "이름"}, {"chulNo": 번호, "hrName": "이름"}, {"chulNo": 번호, "hrName": "이름"}], "confidence": 75, "reasoning": "복합점수 1-3위"}