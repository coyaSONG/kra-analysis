# 경마 예측 v10.0 - Enriched Data 활용

삼복연승(1-3위) 예측. 다음 정보를 종합 분석:

## 평가 우선순위
1. **배당률** (winOdds): 시장 평가의 핵심
2. **기수 최근 성적** (jkDetail.last3Rcord): 최근 폼
3. **말 최근 성적** (hrDetail.last3Rcord): 최근 경기력
4. **기수-말 궁합** (jkDetail.with_hr): 조합 성적

## 선택 전략
- winOdds=0인 말은 제외 (기권/제외)
- 배당률 1-2위는 필수 포함
- 3번째 말은 다음 중 선택:
  - 기수 최근 3경주 승률 40% 이상
  - 말 최근 3경주 입상률 60% 이상
  - 해당 기수와 함께 탄 성적이 우수한 경우

## 출력 형식
```json
{
  "selected_horses": [
    {"chulNo": 번호, "hrName": "말이름"},
    {"chulNo": 번호, "hrName": "말이름"},
    {"chulNo": 번호, "hrName": "말이름"}
  ],
  "confidence": 70-90,
  "reasoning": "선택 근거 간단히"
}
```