# hrDetail/jkDetail/trDetail은 갱신되지 않는 1회성 스냅샷

**Date:** 2026-03-15
**Category:** discovery
**Status:** active
**Related files:** `packages/scripts/autoresearch/train.py`, `packages/scripts/shared/db_client.py`

## Context

GPT-5.4 Pro 리뷰에서 "누적 통계(rcCntT, ord1CntY 등)가 현재 경주 결과를 이미 포함한 post-race 데이터일 수 있다"는 우려 제기. Delta audit으로 검증.

## Finding

**보존본에서 값이 갱신되지 않았지만, 최초 수집 시점과 누수 여부는 이 검사로 검증할 수 없다.**

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
1. **누수 미검증**: 연속 출전에서 값이 불변이라는 사실만으로 최초 수집본이 해당 경기 이전 값인지, 이후 결과가 빠졌는지 알 수 없다.
2. **"year_place_rate"는 올해 실적이 아님** — 데이터 수집 시점의 동결된 과거 통계
3. **일부 말은 통계=0** — hrDetail이 없거나 신마(데뷔 전 수집)
4. **경주마다 hrDetail을 재수집하면 성능 향상 가능** — 현재 가장 큰 데이터 품질 병목

## Impact

- 보고된 0.640/0.667은 부분점수이며, 해당 실험은 `winOdds`도 사용했다. [보존본 재현](../research/2026-11-19-legacy-metric-lineage.md)은 이 수치를 경기 전 완전 적중률로 사용할 수 없음을 확인했다.
- hrDetail을 경주 직전에 재수집하는 파이프라인을 구축하면 최근 폼 반영 가능
- GPT-5.4 Pro 리뷰의 "recent form" 제안과 일맥상통: 현재 데이터 자체가 recent가 아님
- 향후 `compute_race_features`에서 직접 과거 경주 결과를 집계하는 방식도 고려 가능
