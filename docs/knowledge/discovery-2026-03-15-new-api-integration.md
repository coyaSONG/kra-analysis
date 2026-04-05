# 신규 KRA API 8건 통합

**Date:** 2026-03-15
**Category:** discovery
**Status:** active
**Related files:** apps/api/services/collection_service.py, apps/api/services/result_collection_service.py, utils/field_mapping.py

## Context

기존 collect_race_data에 6개 API가 자동 통합되고, 배당률 수집용 신규 메서드 1개(2개 소스)가 추가됨.

## Finding

### 1. collect_race_data 자동 통합 (6개 API)

`collect_race_data(date, meet, race_no, db)` 호출 시 자동 포함. 별도 호출 불필요.

basic_data에 새로 추가되는 키:

| 키 | API | 내용 |
|----|-----|------|
| `race_plan` | API72_2 | 등급, 상금, 거리, 출발시간, 부담조건 |
| `track` | API189_1 | 날씨, 주로상태, 함수율 |
| `cancelled_horses[]` | API9_1 | 취소마 번호, 사유 |
| `horses[].jkStats` | API11_1 | 기수 성적 (jkDetail과 별도 네임스페이스) |
| `horses[].owDetail` | API14_1 | 마주 정보 |
| `horses[].training` | API329 | 조교 현황, 훈련 상태 |

- 신규 API 실패해도 기존 수집은 계속됨 (warning만 로깅)
- jkStats는 jkDetail과 필드명이 겹치지만 출처가 다르므로 별도 키

### 2. 배당률 수집 (API160_1 / API301)

**일상 수집 (API160_1)**: `collect_result()` 내부에서 자동 수집. 별도 호출 불필요.
```
collect_result() 호출
  → 1-3위 결과 저장 + commit
  → _collect_odds_after_result() 자동 호출 (API160_1)
  → 실패해도 결과 데이터에 영향 없음 (non-blocking)
```

**백필 (API301)**: 과거 대량 수집 시에만 별도 호출.
```python
await collection_service.collect_race_odds(
    race_date="20260315", meet=1, race_no=1, db=db,
    source="API301"
)
```

- source는 "API160_1" 또는 "API301"만 허용
- race_odds 테이블에 별도 저장 (UPSERT)

### 2-1. pool_map 공통화

POOL_NAME_MAP, VALID_POOLS를 `utils/field_mapping.py`로 추출. collection_service.py와 result_collection_service.py 모두 공통 상수 참조.

### 3. 주의사항

- `_collect_horse_details`에 `meet` 파라미터 추가됨 (정수)
- training 매칭은 hrName 기반 (API329에 hrNo 미제공) → 동명이마 시 부정확, unmatched 시 warning
- race_odds 쿼리 시 반드시 source 필터 포함 (없으면 중복 집계)

## Impact

- 2026년 배치 수집 시 8개 API 모두 자동 수집됨 (기존 스크립트 수정 불필요)
  - collect_race_data → 6개 API 자동 포함
  - collect_result → 배당률(API160_1) 자동 포함
- enriched_data 파이프라인에서 새 필드(race_plan, track, cancelled_horses, jkStats, owDetail, training) 활용 가능
- 프롬프트에서 날씨/주로상태, 취소마, 조교 현황 등 새 피처 활용 가능
