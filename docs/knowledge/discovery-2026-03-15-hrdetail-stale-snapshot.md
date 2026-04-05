# hrDetail/jkDetail/trDetail은 갱신되지 않는 1회성 스냅샷

**Date:** 2026-03-15
**Category:** discovery
**Status:** active
**Related files:** `packages/scripts/autoresearch/train.py`, `packages/scripts/shared/db_client.py`

## Context

GPT-5.4 Pro 리뷰에서 "누적 통계(rcCntT, ord1CntY 등)가 현재 경주 결과를 이미 포함한 post-race 데이터일 수 있다"는 우려 제기. Delta audit으로 검증.

## Finding

**누수 없음. 하지만 데이터가 아예 갱신되지 않음.**

### Delta Audit (3,370개 연속 출전 쌍)
- `rcCntT` 변화=0: **100%** (3,370/3,370)
- `rcCntT` 변화=1: 0%

### 구체 사례
- 말 0043750: 2025년 10경주 출전, 모든 경주에서 rcCntT=51, ord1CntT=2 **고정**
  - 3위 입상(20250103)해도 ord3CntT 변화 없음
- 말 0046744: 2025년 10경주 출전, 모든 통계=0 (hrDetail이 빈 상태로 고정)

### 원인
`hrDetail`은 KRA API(`/API8_2/raceHorseInfo_2`)에서 enrichment 시 1회 fetch 후 DB에 저장. 이후 경주 결과와 무관하게 동일 값 반환. `jkDetail`, `trDetail`도 동일 구조로 추정.

### 영향
1. **누수 위험 없음** — 통계가 현재 경주 결과를 절대 포함하지 않음
2. **"year_place_rate"는 올해 실적이 아님** — 데이터 수집 시점의 동결된 과거 통계
3. **일부 말은 통계=0** — hrDetail이 없거나 신마(데뷔 전 수집)
4. **경주마다 hrDetail을 재수집하면 성능 향상 가능** — 현재 가장 큰 데이터 품질 병목

## Impact

- autoresearch 모델의 set_match=0.640/0.667은 **동결된 과거 통계로 달성한 것**
- hrDetail을 경주 직전에 재수집하는 파이프라인을 구축하면 최근 폼 반영 가능
- GPT-5.4 Pro 리뷰의 "recent form" 제안과 일맥상통: 현재 데이터 자체가 recent가 아님
- 향후 `compute_race_features`에서 직접 과거 경주 결과를 집계하는 방식도 고려 가능
