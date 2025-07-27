# Race Collector 모듈

경마 데이터 수집 및 처리를 위한 스크립트 모음입니다.

## 📁 파일 구성

### 1. `collect_and_preprocess.js`
기본 경주 데이터 수집 및 전처리
- API214_1을 사용하여 경주 정보 수집
- 완료된 경주를 경주 전 상태로 전처리
- 날짜/경마장별로 자동 정리

### 2. `api_clients.js` (NEW)
개별 API 클라이언트 및 캐싱 시스템
- API8_2: 경주마 상세정보
- API12_1: 기수 정보
- API19_1: 조교사 정보
- 7일간 캐시 유지로 중복 호출 방지

### 3. `enrich_race_data.js` (NEW)
경주 데이터 보강 스크립트
- 기본 데이터에 말/기수/조교사 상세 정보 추가
- 혈통, 성적 통계, 승률 등 추가
- enriched 파일로 별도 저장
- 재시도 로직으로 API 제한 대응

### 4. `retry_failed_enrichment.js` (NEW)
실패한 데이터 재수집 스크립트
- 누락된 정보만 선택적 재처리
- 캐시 활용으로 효율적 재시도
- 더 긴 딜레이로 안정성 확보

### 5. `smart_preprocess_races.py`
스마트 전처리 스크립트
- 경주 상태 자동 판단
- 완료된 경주만 전처리

### 6. `preprocess_race_data_v2.py`
전처리 핵심 로직
- 경주 결과 필드 초기화
- 기권/제외 말 필터링

## 🚀 사용 방법

### 1단계: 기본 데이터 수집
```bash
# 오늘 서울 경마장 데이터 수집
node collect_and_preprocess.js

# 특정 날짜 수집
node collect_and_preprocess.js 20250608 1
```

### 2단계: 데이터 보강
```bash
# 단일 경주 파일 보강
node enrich_race_data.js data/races/2025/06/20250608/seoul/race_1_20250608_1_prerace.json

# 날짜별 전체 보강
node enrich_race_data.js 20250608 1
```

### 3단계: 실패한 데이터 재수집 (필요시)
```bash
# 단일 파일 재시도
node retry_failed_enrichment.js data/races/2025/06/20250608/seoul/race_1_20250608_7_enriched.json

# 날짜별 전체 재시도
node retry_failed_enrichment.js 20250608 1
```

## 📊 데이터 구조

### 기본 데이터 (`_prerace.json`)
```json
{
  "hrName": "말이름",
  "hrNo": "말번호",
  "jkName": "기수이름",
  "jkNo": "기수번호",
  "trName": "조교사이름",
  "trNo": "조교사번호"
}
```

### 보강된 데이터 (`_enriched.json`)
```json
{
  "hrName": "말이름",
  "hrNo": "말번호",
  "hrDetail": {
    "faHrName": "부마이름",
    "moHrName": "모마이름",
    "rcCntT": 15,
    "ord1CntT": 3,
    "winRateT": "20.0"
  },
  "jkName": "기수이름",
  "jkNo": "기수번호", 
  "jkDetail": {
    "age": "35",
    "debut": "20100505",
    "ord1CntT": 968,
    "winRateT": "15.5"
  },
  "trName": "조교사이름",
  "trNo": "조교사번호",
  "trDetail": {
    "meet": "서울",
    "ord1CntT": 323,
    "winRateT": 12.0,
    "plcRateT": 35.0
  }
}
```

## 💾 캐시 시스템

- 위치: `data/cache/`
  - `horses/`: 말 정보 캐시
  - `jockeys/`: 기수 정보 캐시
  - `trainers/`: 조교사 정보 캐시
- 유효기간: 7일
- 자동 갱신: 만료 시 자동으로 새 데이터 조회

## ⚡ 성능 최적화

### API 딜레이 전략
- 말 정보: 1000ms (가장 많은 호출)
- 기수/조교사 정보: 800ms
- 경주 간 추가 딜레이: 3000ms
- 재시도 시 지수 백오프 적용

### 효율성 개선
- 캐시 활용으로 중복 호출 최소화
- 고유 기수/조교사만 조회
- 재시도 로직으로 실패 최소화

## 📝 주의사항

1. `.env` 파일에 `KRA_SERVICE_KEY` 필수
2. API 일일 호출 제한 확인
3. 네트워크 오류 시 재시도 필요