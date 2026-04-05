# 8개 신규 KRA API 통합 설계안

> Codex 리뷰 반영 (2026-03-15)

## 수정된 핵심 원칙

1. **새 수집 데이터는 `basic_data`에 저장** (기존 hrDetail/jkDetail/trDetail과 동일한 패턴)
2. **API11_1은 `jkStats`로 별도 네임스페이스** (기존 jkDetail과 필드 충돌 방지)
3. **배당률(API160_1/301)만 별도 `race_odds` 테이블** (고볼륨 + UPSERT 필요)

---

## 데이터 배치

### basic_data JSONB 확장

```jsonc
{
  // === 기존 ===
  "date": "20260315",
  "meet": 1,
  "race_number": 5,
  "race_info": { /* API214_1 */ },

  // === NEW: 경주 메타데이터 (수집 시점에 확정) ===
  "race_plan": {                    // ← API72_2 경주계획표
    "rank": "국6등급",
    "budam": "별정A",
    "rcDist": 1200,
    "schStTime": 1035,
    "chaksun1": 16500000,
    "chaksun2": 6600000,
    "chaksun3": 4200000,
    "chaksun4": 1500000,
    "chaksun5": 1200000,
    "ageCond": "연령오픈",
    "sexCond": "성별오픈",
    "spRating": 0,
    "stRating": 0
  },

  // === NEW: 주로/날씨 ===
  "track": {                        // ← API189_1 경주로정보
    "weather": "맑음",
    "condition": "건조",
    "waterPercent": 3,
    "temperature": "-",
    "humidity": "-",
    "windDirection": "-",
    "windSpeed": "-"
  },

  // === NEW: 출전취소 ===
  "cancelled_horses": [             // ← API9_1 출전취소정보
    {
      "chulNo": 2,
      "hrName": "거센빅맨",
      "hrNo": "0054782",
      "reason": "마체이상"
    }
  ],

  // === 기존 + 확장 ===
  "horses": [
    {
      "hrNo": "0054782",
      "hrName": "천년의질주",
      "chulNo": 3,
      "winOdds": 5.2,
      "jkNo": "090123",
      "jkName": "문세영",
      "trNo": "070123",
      "trName": "김영관",

      "hrDetail": { /* API8_2 - 기존 */ },
      "jkDetail": { /* API12_1 - 기존 (age, debut, ord1CntT, winRateT...) */ },
      "trDetail": { /* API19_1 - 기존 */ },

      // === NEW: 기수 성적 (별도 네임스페이스) ===
      "jkStats": {                  // ← API11_1 기수 성적 정보
        "ord1CntT": 92,             //   jkDetail과 겹치는 필드가 있지만
        "ord1CntY": 0,              //   출처/기준이 다를 수 있으므로 분리
        "ord2CntT": 94,
        "ord2CntY": 0,
        "rcCntT": 992,
        "rcCntY": 0,
        "winRateT": 9.3,
        "winRateY": 0,
        "qnlRateT": 18.8,
        "qnlRateY": 0
      },

      // === NEW: 마주 정보 ===
      "owDetail": {                 // ← API14_1 마주 정보
        "owName": "(주)나스카",
        "owNo": 110034,
        "ord1CntT": 205,
        "ord1CntY": 28,
        "rcCntT": 1262,
        "rcCntY": 142,
        "chaksunT": 11967001000,
        "chaksunY": 1544950000,
        "ownerHorses": 24,
        "totHorses": 124
      },

      // === NEW: 조교 현황 ===
      "training": {                 // ← API329 서울출발조교현황
        "beloNo": "1조",            //   매칭: hrName 대신 hrNo 기반 매칭 권장
        "beloTrngNo": 1,            //   hrNo 불가 시 race_id + chulNo 보조 검증
        "remkTxt": "양호",          //   핵심: 훈련 상태 (양호/보통/불량 등)
        "ridrNm": "관",             //   unmatched 발생 시 warnings에 로깅
        "trngDt": 20260313
      }
    }
  ]
}
```

### race_odds 테이블 (별도)

```sql
-- API160_1 (확정배당율 통합) + API301 (확정배당율종합) → race_odds
-- UNIQUE 제약으로 UPSERT 지원, ON DELETE CASCADE로 경주 삭제 시 자동 정리

CREATE TABLE race_odds (
    id SERIAL PRIMARY KEY,
    race_id VARCHAR(50) NOT NULL REFERENCES races(race_id) ON DELETE CASCADE,
    pool VARCHAR(10) NOT NULL,
    chul_no INTEGER NOT NULL,
    chul_no2 INTEGER NOT NULL DEFAULT 0,
    chul_no3 INTEGER NOT NULL DEFAULT 0,
    odds DECIMAL(10,1) NOT NULL,
    rc_date VARCHAR(8) NOT NULL,
    source VARCHAR(20) NOT NULL,        -- 'API160_1' or 'API301'
    collected_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_race_odds_entry UNIQUE (race_id, pool, chul_no, chul_no2, chul_no3, source)
);
```

UPSERT 패턴:
```sql
INSERT INTO race_odds (race_id, pool, chul_no, chul_no2, chul_no3, odds, rc_date, source)
VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
ON CONFLICT ON CONSTRAINT uq_race_odds_entry
DO UPDATE SET odds = EXCLUDED.odds, collected_at = CURRENT_TIMESTAMP;
```

---

## 수집 파이프라인 변경

### 기존 collect_race_data 흐름에 추가

```
collect_race_data(date, meet, race_no)
  │
  ├─ [기존] API214_1 → race_info + horses 기본정보
  ├─ [기존] 말별: API8_2 → hrDetail
  ├─ [기존] 말별: API12_1 → jkDetail
  ├─ [기존] 말별: API19_1 → trDetail
  │
  ├─ [NEW] API72_2 → race_plan (경주 단위, 1회 호출)
  ├─ [NEW] API189_1 → track (경주 단위, 1회 호출)
  ├─ [NEW] API9_1 → cancelled_horses (경주 단위, 1회 호출)
  │
  ├─ [NEW] 말별: API11_1 → jkStats (기수번호로 조회)
  ├─ [NEW] 말별: API14_1 → owDetail (마주번호로 조회)
  ├─ [NEW] 말별: API329 → training (hrNo 기반 매칭, 불가 시 race_id+chulNo 보조 검증)
  │
  └─ basic_data에 통합 저장

collect_race_odds(date, meet, race_no)  ← 별도 메서드
  │
  ├─ API160_1 → race_odds 테이블 UPSERT
  └─ API301 → race_odds 테이블 UPSERT
```

### 캐시 전략

| API | TTL | 이유 |
|-----|-----|------|
| API72_2 경주계획표 | 24시간 | 경주 전 확정, 잘 안 바뀜 |
| API189_1 경주로정보 | 1시간 | 경주 당일 날씨 변동 |
| API9_1 출전취소 | 30분 | 경주 직전까지 변동 가능 |
| API11_1 기수성적 | 24시간 | 누적 통계, 느리게 변함 |
| API14_1 마주정보 | 24시간 | 마스터 데이터 |
| API329 조교현황 | 6시간 | 훈련일 기준 |
| API160_1 배당률 | 캐시 안 함 | 경주 종료 후 확정값 |
| API301 배당률 | 캐시 안 함 | 경주 종료 후 확정값 |

---

## API160_1 vs API301

| 항목 | API160_1 | API301 |
|------|----------|--------|
| 이름 | 확정배당율 통합 | 경마시행당일 확정배당율종합 |
| 볼륨 | 경주당 ~100건 | 175K+ 총건 |
| 필터 | rc_date, pool, rc_no | rc_date, pool, rc_no, rc_year/month |
| 용도 | 특정 경주 배당률 조회 | 대량 히스토리/분석 |
| 권장 | 경주별 수집에 사용 | 백필(backfill) 시 사용 |

→ **일상 수집은 API160_1**, **과거 데이터 대량 수집은 API301** 사용

---

## 소비 규칙

### jkDetail vs jkStats

| 항목 | jkDetail (API12_1) | jkStats (API11_1) |
|------|-------|--------|
| 출처 | 기수 상세정보 API | 기수 성적 API |
| 포함 정보 | age, debut, part + 성적 | 성적 전용 (더 상세) |
| 겹치는 필드 | ord1CntT, rcCntT, winRateT, winRateY | 동일 키명, 출처/집계 기준 다를 수 있음 |
| 예측 시 사용 | 기수 프로필 (나이, 경력, 구분) | 기수 성적 수치 (qnlRateT/Y 포함) |

**규칙**: 예측 프롬프트에서 성적 수치가 필요하면 `jkStats` 우선 사용 (qnlRateT/Y 포함). 기수 프로필(나이, 데뷔일)은 `jkDetail`에서만 제공.

### race_odds 소비 쿼리

race_odds에는 API160_1과 API301 데이터가 공존하므로, **반드시 source 필터 포함**:

```sql
-- 특정 경주의 단승식 배당률 (API160_1 기준)
SELECT chul_no, odds
FROM race_odds
WHERE race_id = $1 AND pool = 'WIN' AND source = 'API160_1'
ORDER BY odds;

-- 날짜별 배당률 분석 (source 필터 필수)
SELECT rc_date, pool, AVG(odds)
FROM race_odds
WHERE rc_date BETWEEN $1 AND $2 AND source = 'API160_1'
GROUP BY rc_date, pool;
```
