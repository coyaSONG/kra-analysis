# 구간 통과 순위/시간 필드 — 경주 후 데이터 (누수)

**Date:** 2026-03-15
**Category:** discovery
**Status:** active
**Related files:** `packages/scripts/evaluation/leakage_checks.py`

## Context

Autoresearch 피처 자동 탐색에서 `sjG1fOrd`(서울/제주 1구간 순위)가 단독 set_match=0.842, 모델에 추가 시 0.640→0.783(+14%p)으로 극적 개선. 너무 강력해서 누수 의심 후 검증.

## Finding

**`sjG1fOrd`, `buG1fOrd` 등 구간 통과 순위는 현재 경주의 경주 중 데이터 (post-race).**

### 증거
1. **값이 1~N 연속**: 125/126 경주에서 `sjG1fOrd` 최대값 == non-zero 마 수 (99.2% 일치)
2. **실시간 API 검증**: 미발주 경주(서울 9R)에서 전 마필 `sjG1fOrd=0` — 경주 전에는 값이 없음
3. **의미**: "이전 경주 1구간 순위"가 아닌 "현재 경주 200m 통과 시점의 위치"

### 영향받는 필드 (모두 FORBIDDEN에 추가됨)
```
구간 순위: sjG1fOrd, sjG3fOrd, sjS1fOrd, sj_1cOrd~sj_4cOrd,
          buG1fOrd, buG6fOrd, buG8fOrd, buS1fOrd
구간 시간: seG1fAccTime, seG3fAccTime, seS1fAccTime, se_1cAccTime~se_4cAccTime,
          buG1fAccTime~buG8fAccTime, buS1fAccTime
```

### 검증 방법 (향후 새 피처 추가 시)
1. 값이 1~N 연속이면 현재 경주 데이터 (누수)
2. 실시간 API에서 미발주 경주 값이 0이면 경주 전 미확정 (누수)
3. 같은 경주의 모든 말에 동일한 값이면 경주 정보 (무해하지만 무용)

## Impact

- `FORBIDDEN_POST_RACE_FIELDS`에 27개 필드 추가 완료
- 향후 피처 탐색 시 반드시 실시간 API에서 미발주 경주 데이터로 교차 검증 필요
- snapshot 데이터에서 "놀랍도록 예측력 높은" 피처는 항상 누수부터 의심할 것
