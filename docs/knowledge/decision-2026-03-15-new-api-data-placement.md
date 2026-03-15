# 8개 신규 KRA API 데이터 배치 설계

**Date:** 2026-03-15
**Category:** decision
**Status:** active
**Related files:** `docs/new-api-integration-design.md`, `apps/api/migrations/003_add_race_odds.sql`, `apps/api/services/collection_service.py`, `apps/api/models/database_models.py`

## Context

8개 신규 KRA 공공 API(경주로정보, 경주계획표, 출전취소, 기수성적, 마주정보, 조교현황, 확정배당율 2종)를 기존 수집 파이프라인에 통합해야 했다. 핵심 질문은 "어디에 저장할 것인가" (basic_data vs enriched_data vs 별도 테이블).

## Decision

### 1. 6개 API → basic_data JSONB 임베딩

| API | 저장 키 | 이유 |
|-----|---------|------|
| API72_2 경주계획표 | `basic_data.race_plan` | 경주 메타데이터, 수집 시점에 확정 |
| API189_1 경주로정보 | `basic_data.track` | 경주 단위 날씨/주로 상태 |
| API9_1 출전취소 | `basic_data.cancelled_horses[]` | 경주 단위 취소마 목록 |
| API11_1 기수성적 | `basic_data.horses[].jkStats` | 기수 성적 (jkDetail과 필드 충돌 방지로 별도 네임스페이스) |
| API14_1 마주정보 | `basic_data.horses[].owDetail` | 기존 hrDetail/jkDetail/trDetail 패턴 따름 |
| API329 조교현황 | `basic_data.horses[].training` | 말별 훈련 상태 |

**rejected:** enriched_data에 저장 → 현재 코드에서 수집 단계 산출물은 모두 basic_data에 저장되고 enriched_data는 후속 전처리 결과 전용. Codex 리뷰에서 P0으로 지적.

### 2. API11_1 기수성적 → `jkStats` 별도 네임스페이스

기존 `jkDetail` (API12_1)과 `ord1CntT`, `rcCntT`, `winRateT`, `winRateY` 등 필드가 겹침. 같은 키명이지만 출처/집계 기준이 다를 수 있으므로 병합 대신 분리.

- 예측 프롬프트에서 성적 수치 필요 시 `jkStats` 우선 (qnlRateT/Y 포함)
- 기수 프로필(나이, 데뷔일)은 `jkDetail`에서만 제공

### 3. 배당률 2개 API → `race_odds` 별도 테이블

API160_1 + API301은 데이터 볼륨이 커서(175K+) JSONB 임베딩 부적합.

```sql
CREATE TABLE race_odds (
    -- UNIQUE(race_id, pool, chul_no, chul_no2, chul_no3, source)
    -- CHECK(pool IN ('WIN','PLC','QNL','EXA','QPL','TLA','TRI','XLA'))
    -- CHECK(source IN ('API160_1','API301'))
    -- ON DELETE CASCADE
);
```

- 일상 수집: API160_1, 백필: API301
- 소비 쿼리 시 반드시 source 필터 포함

## Impact

- `collect_race_data`에서 신규 API 호출 실패해도 기존 수집은 계속됨 (try/except warning)
- `_collect_horse_details`에 meet 파라미터 추가됨 (정수, API 경마장 코드)
- training 매칭은 API329에 hrNo가 없어서 hrName 기반 + unmatched 로깅
- 예측 프롬프트에서 새 필드 활용 시 `basic_data` 구조 참조 필요
