# 경주 전 데이터 구조 분석

## 개요
경주 전(Pre-race) 데이터는 아직 결과가 나오지 않은 경주에 대한 사전 정보입니다. 이 데이터만으로 예측을 수행하고, 실제 결과와 비교하여 프롬프트의 성능을 검증합니다.

## 현재 수집 가능한 데이터 구조

### 1. 경주 정보 (race_info)
```json
{
  "meet": "부경",              // 경마장명
  "meet_code": "3",            // 경마장 코드 (1:서울, 2:제주, 3:부경)
  "race_date": "20250523",     // 경주 날짜 (YYYYMMDD)
  "race_no": 1,                // 경주 번호
  "distance": 1200,            // 거리(m)
  "track_condition": "건조 (2%)", // 주로 상태
  "weather": "흐림",           // 날씨
  "race_name": "일반",         // 경주명
  "age_condition": "연령오픈",  // 연령 조건
  "prize_condition": "R0~0"     // 상금 조건
}
```

### 2. 출전마 정보 (horses)
각 말에 대한 상세 정보:

#### 2.1 기본 정보
```json
{
  "chul_no": 10,               // 출전번호 (게이트 번호)
  "hr_no": "0051228",         // 말 등록번호
  "hr_name": "올라운드원",      // 말 이름
  "age": 3,                   // 나이
  "sex": "거",                // 성별 (수/암/거)
  "weight": "511(+2)",        // 체중 및 변화 (현재체중(변화량))
  "rank": "국6등급",          // 등급
  "rating": 0,                // 레이팅 점수
  "burden_weight": 57         // 부담중량(kg)
}
```

#### 2.2 기수 정보 (jockey)
```json
{
  "jk_no": "080565",          // 기수 번호
  "jk_name": "정도윤",         // 기수 이름
  "weight": 0,                // 계체중량
  "win_rate_total": 14.1,     // 통산 승률(%)
  "win_rate_year": 4.7,       // 올해 승률(%)
  "recent_stats": {
    "races": 258,             // 올해 출전 횟수
    "wins": 12,               // 올해 1착 횟수
    "seconds": 20,            // 올해 2착 횟수
    "thirds": 0               // 올해 3착 횟수
  }
}
```

#### 2.3 조교사 정보 (trainer)
```json
{
  "tr_no": "070180",          // 조교사 번호
  "tr_name": "안우성",         // 조교사 이름
  "win_rate_total": 7.2,      // 통산 승률(%)
  "win_rate_year": 5.4,       // 올해 승률(%)
  "recent_stats": {
    "races": 259,             // 올해 출전 횟수
    "wins": 14,               // 올해 1착 횟수
    "seconds": 34,            // 올해 2착 횟수
    "thirds": 0               // 올해 3착 횟수
  }
}
```

#### 2.4 말 통계 (horse_stats)
```json
{
  "total_races": 10,          // 통산 출전 횟수
  "total_wins": 1,            // 통산 1착 횟수
  "total_seconds": 2,         // 통산 2착 횟수
  "total_thirds": 1,          // 통산 3착 횟수
  "year_races": 5,            // 올해 출전 횟수
  "year_wins": 1,             // 올해 1착 횟수
  "year_seconds": 1,          // 올해 2착 횟수
  "year_thirds": 0            // 올해 3착 횟수
}
```

#### 2.5 배당률 (odds)
```json
{
  "win": 3.0,                 // 단승 배당률
  "place": 1.2                // 연승 배당률
}
```

## 예측에 활용하는 핵심 데이터

### 1. 말의 능력 평가 요소
- **체중 변화**: 급격한 변화는 컨디션 이상 신호
- **나이와 성별**: 3-5세가 전성기, 수말이 일반적으로 유리
- **등급**: 상대적 능력 수준
- **과거 성적**: 승률, 복승률(3위 이내)

### 2. 인적 요소
- **기수 능력**: 승률이 높은 기수가 유리
- **조교사 능력**: 마방 관리 능력
- **기수-말 호흡**: 과거 함께한 성적

### 3. 경주 조건
- **거리**: 단거리(1200m), 중거리(1400-1800m), 장거리(2000m+)
- **주로 상태**: 건조, 다습, 불량
- **날씨**: 맑음, 흐림, 비
- **부담중량**: 핸디캡 영향

### 4. 시장 평가
- **배당률**: 낮을수록 우승 가능성 높음
- **인기 순위**: 배당률 기반 순위

## 데이터 제약사항

### 현재 수집된 데이터의 한계
1. **최근 경주 상세 기록 부족**: 개별 경주별 착순, 기록 등
2. **혈통 정보 없음**: 부마, 모마 정보
3. **훈련 상태 정보 없음**: 조교 기록, 컨디션
4. **실시간 정보 부족**: 당일 컨디션, 마체 상태

### 데이터 부족한 말의 특징
- 신마(데뷔전): horse_stats가 모두 0
- 경험 부족: total_races < 3
- 이런 경우 배당률에 더 의존해야 함

## 검증을 위한 프로세스

### 1. 예측 프로세스
1. **경주 선택**: 아직 시작하지 않은 경주
2. **데이터 수집**: 경주 전 정보만 수집
3. **프롬프트 적용**: 수집된 데이터로 예측
4. **예측 저장**: 타임스탬프와 함께 저장

### 2. 검증 프로세스
1. **경주 완료 대기**: 실제 경주 진행
2. **결과 수집**: API에서 ord(착순) 필드 확인
3. **비교 분석**: 예측 vs 실제 결과
4. **정확도 계산**: 적중률, 부분 적중률

### 3. 평가 지표
- **완전 적중**: 3마리 모두 맞춤
- **부분 적중**: 1-2마리 맞춤
- **수익성**: 배당률 대비 수익

## 프롬프트 개발 시 고려사항

1. **데이터 완전성 처리**
   - 데이터가 충분한 말과 부족한 말 구분
   - 각각에 대한 다른 가중치 적용

2. **시장 신호 활용**
   - 배당률은 집단 지성의 결과
   - 특히 데이터 부족 시 중요

3. **조건별 전략**
   - 거리별, 주로 상태별 다른 전략
   - 날씨 영향 고려

4. **리스크 관리**
   - 불확실성이 높은 경우 명시
   - 대안 조합 제시