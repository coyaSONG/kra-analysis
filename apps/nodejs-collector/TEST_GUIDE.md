# 테스트 가이드

## 📊 테스트 구조

```
tests/
├── api-simple.test.ts           # 기본 검증 테스트 (API 키 불필요)
├── middleware/
│   └── validation.test.ts       # 검증 미들웨어 테스트
├── integration/
│   └── kra-api-integration.test.ts  # KRA API 서비스 직접 테스트
└── e2e/
    └── api-e2e.test.ts         # HTTP → KRA API 전체 플로우 테스트
```

## 🎯 테스트 범위

### 1. **기본 테스트** (API 키 불필요)
- 날짜 형식 검증
- ID 형식 검증 (Horse: 7자리, Jockey/Trainer: 6자리)
- 404 처리
- Health check

### 2. **KRA API 통합 테스트** (API 키 필요)
- **API214_1**: 경주 결과 조회
- **API8_2**: 말 상세정보
- **API12_1**: 기수 정보
- **API19_1**: 조교사 정보

### 3. **E2E 테스트** (API 키 필요)
- 전체 요청/응답 플로우
- 캐싱 동작 확인
- 에러 처리 검증

## 🚀 테스트 실행 방법

### 환경 설정
```bash
# .env 파일에 KRA API 키 설정
KRA_SERVICE_KEY=your_actual_key_here
```

### 테스트 명령어

```bash
# 기본 테스트만 (API 키 불필요, 빠름)
pnpm test:simple

# KRA API 테스트 (API 키 필요, 느림)
pnpm test:kra

# 모든 테스트
pnpm test:all

# 특정 테스트만
pnpm test tests/integration/kra-api-integration.test.ts

# 커버리지 확인
pnpm test:coverage
```

## ✅ 테스트되는 KRA API

| API | 엔드포인트 | 테스트 내용 |
|-----|----------|-----------|
| API214_1 | /RaceDetailResult_1 | 경주 결과, 말/기수/조교사 정보 |
| API8_2 | /horseInfo_2 | 말 상세정보, 통계 |
| API12_1 | /jockeyInfo_1 | 기수 정보, 승률 |
| API19_1 | /trainerInfo_1 | 조교사 정보, 성적 |

## 📝 테스트 데이터

```javascript
// 검증된 테스트 데이터 (실제 존재하는 데이터)
const TEST_DATA = {
  date: '20240106',
  meet: '서울',
  raceNo: 1,
  horseNo: '0053587',   // 서부특송
  jockeyNo: '080476',   // 장추열
  trainerNo: '070165',  // 서인석
};
```

## 🔍 테스트 검증 항목

### Race API
- ✅ 경주 정보 (rcName, rcDist, totalHorses)
- ✅ 말 정보 (hrName, hrNo, age, sex)
- ✅ 기수 정보 (jkName, jkNo)
- ✅ 조교사 정보 (trName, trNo)
- ✅ 결과 정보 (ord, rcTime, chulNo)

### Horse API
- ✅ 기본 정보 (hrName, birthday, sex)
- ✅ 등급 정보 (rank, rating)
- ✅ 통계 (rcCntT, ord1CntT, ord2CntT)

### Jockey API
- ✅ 개인 정보 (jkName, age, debut)
- ✅ 소속 정보 (part, meet)
- ✅ 성적 통계 (승률, 연대율)

### Trainer API
- ✅ 개인 정보 (trName, birthday, debut)
- ✅ 성적 통계 (winRateT, top2RateT, top3RateT)

## ⚠️ 주의사항

1. **Rate Limiting**: KRA API는 분당 60회 제한이 있습니다
2. **테스트 간격**: 각 테스트 사이에 1초 대기 시간이 있습니다
3. **타임아웃**: 각 테스트는 15-20초 타임아웃이 설정되어 있습니다
4. **캐싱**: 두 번째 요청부터는 캐시된 데이터를 사용할 수 있습니다

## 🐛 트러블슈팅

### API 키 오류
```
⚠️ KRA_SERVICE_KEY not found in environment
```
→ `.env` 파일에 `KRA_SERVICE_KEY` 설정 필요

### Rate Limit 오류
```
Error: Rate limit exceeded
```
→ 잠시 후 다시 시도하거나 테스트 간격 늘리기

### 네트워크 오류
```
Error: ENOTFOUND apis.data.go.kr
```
→ 네트워크 연결 확인, KRA API 서버 상태 확인