# 데이터 보강 시스템 (Data Enrichment System)

## 📋 개요

KRA 경마 예측 시스템의 데이터 보강 모듈은 기본 경주 데이터(API214_1)에 말, 기수, 조교사의 상세 정보를 추가하여 더 풍부한 예측 데이터를 생성합니다.

## 🏗️ 시스템 구조

### 1. API 구성
- **기본 데이터**: API214_1 (경주 상세 결과)
- **보강 데이터**:
  - API8_2: 경주마 상세정보 (혈통, 성적)
  - API12_1: 기수 정보 (경력, 성적)
  - API19_1: 조교사 정보 (성적, 승률)

### 2. 파일 구조
```
scripts/race_collector/
├── collect_and_preprocess.js    # 기본 데이터 수집
├── api_clients.js               # API 클라이언트 및 캐싱
├── enrich_race_data.js          # 데이터 보강 메인 스크립트
└── README.md                    # 모듈 문서

data/
├── races/                       # 경주 데이터
│   └── YYYY/MM/YYYYMMDD/venue/
│       ├── *_prerace.json      # 기본 데이터
│       └── *_enriched.json     # 보강된 데이터
└── cache/                       # API 캐시
    ├── horses/                  # 말 정보 캐시
    ├── jockeys/                 # 기수 정보 캐시
    └── trainers/                # 조교사 정보 캐시
```

## 💡 핵심 기능

### 1. 캐싱 시스템
- **유효기간**: 7일
- **저장 위치**: `data/cache/`
- **효과**: 
  - 중복 API 호출 방지
  - 응답 속도 향상
  - API 제한 회피

### 2. 스마트 데이터 수집
- 고유한 기수/조교사만 조회
- 캐시 우선 확인
- API 호출 간 딜레이 (500ms)

### 3. 데이터 보강 내용

#### 🐎 말 상세 정보 (hrDetail)
```json
{
  "faHrName": "부마 이름",
  "moHrName": "모마 이름",
  "rcCntT": 15,        // 통산 출전
  "ord1CntT": 3,       // 통산 1착
  "ord2CntT": 2,       // 통산 2착
  "winRateT": "20.0",  // 통산 승률
  "winRateY": "25.0",  // 올해 승률
  "chaksunT": 50000000,// 통산 상금
  "hrLastAmt": "거래가 정보"
}
```

#### 🏇 기수 상세 정보 (jkDetail)
```json
{
  "age": 35,
  "birthday": "19890101",
  "debut": "20100505",
  "ord1CntT": 968,     // 통산 1착
  "rcCntT": 6254,      // 통산 출전
  "winRateT": "15.5",  // 통산 승률
  "winRateY": "14.2"   // 올해 승률
}
```

#### 👨‍🏫 조교사 상세 정보 (trDetail)
```json
{
  "meet": "서울",
  "stDate": 20050601,
  "ord1CntT": 323,     // 통산 1착
  "rcCntT": 2684,      // 통산 출전
  "winRateT": 12.0,    // 통산 승률
  "plcRateT": 35.0,    // 통산 복승률
  "winRateY": 6.3      // 올해 승률
}
```

## 🚀 사용 방법

### 1. 단일 경주 보강
```bash
node scripts/race_collector/enrich_race_data.js data/races/2025/06/20250608/seoul/race_1_20250608_1_prerace.json
```

### 2. 날짜별 전체 보강
```bash
node scripts/race_collector/enrich_race_data.js 20250608 1
# 20250608: 날짜
# 1: 경마장 코드 (1=서울, 2=제주, 3=부산)
```

### 3. 워크플로우
```
1. collect_and_preprocess.js로 기본 데이터 수집
   ↓
2. enrich_race_data.js로 상세 정보 추가
   ↓
3. _enriched.json 파일 생성
```

## 📊 성능 및 제한사항

### API 호출 최적화
- **캐싱 효과**: 첫 실행 시 100% API 호출 → 재실행 시 90% 이상 캐시 사용
- **예상 소요 시간**: 
  - 첫 실행: 경주당 약 30-60초
  - 재실행: 경주당 약 5-10초

### API 제한 대응
- 호출 간 500ms 딜레이
- 실패 시 null 반환 (부분 실패 허용)
- 일일 호출 한도 고려 필요

## 🔍 데이터 활용 예시

### 1. 혈통 기반 분석
```javascript
// 부모마의 성적이 좋은 말 찾기
const goodBloodline = horses.filter(h => 
  h.hrDetail && h.hrDetail.faHrName.includes("유명한부마")
);
```

### 2. 기수-말 조합 분석
```javascript
// 승률 높은 기수가 탄 신마
const promising = horses.filter(h => 
  h.hrDetail && h.hrDetail.rcCntT <= 3 &&  // 신마
  h.jkDetail && parseFloat(h.jkDetail.winRateT) > 15  // 승률 15% 이상 기수
);
```

### 3. 조교사 최근 폼 분석
```javascript
// 올해 성적이 좋은 조교사의 말
const hotTrainer = horses.filter(h =>
  h.trDetail && h.trDetail.winRateY > h.trDetail.winRateT  // 올해가 평균보다 좋음
);
```

## 🛠️ 유지보수

### 캐시 관리
```bash
# 캐시 전체 삭제 (강제 새로고침)
rm -rf data/cache/*

# 특정 타입만 삭제
rm -rf data/cache/horses/*
```

### 에러 처리
- API 응답 오류 시 해당 데이터만 null
- 전체 프로세스는 계속 진행
- 로그에 실패 내역 표시

## 🔗 관련 문서
- [프로젝트 개요](project-overview.md)
- [데이터 구조](data-structure.md)
- [API 분석](api-analysis.md)
- [프롬프트 개발 전략](prompt-development-strategy.md)