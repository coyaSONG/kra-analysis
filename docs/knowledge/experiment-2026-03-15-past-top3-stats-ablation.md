# Past Top3 Stats A/B 실험 설계

**Date:** 2026-03-15
**Category:** experiment
**Status:** active (실행 대기)
**Related files:** `packages/scripts/shared/db_client.py`, `packages/scripts/feature_engineering.py`, `packages/scripts/evaluation/evaluate_prompt_v3.py`

## Context

현재 예측 시스템은 hrDetail(통산/올해 성적)만 사용. 최근 3개월 실제 경주 성적(top3 진입 여부)이 예측 정확도를 높이는지 검증 필요.

## Design

### 가설
최근 90일간 top3 진입률/승률을 computed_features에 추가하면, Claude가 "최근 폼"을 더 정확히 판단하여 삼복연승 적중률이 올라갈 것이다.

### 추가되는 피처

| 피처 | 설명 | 데이터 소스 |
|------|------|-------------|
| `recent_top3_rate` | 최근 90일 top3 진입률 | DB 교차 조회 (basic_data.horses + result_data) |
| `recent_win_rate` | 최근 90일 1위 비율 | 동일 |
| `recent_race_count` | 최근 90일 출전 횟수 | 동일 |

### 기존 vs 신규 차이

| 항목 | Baseline (hrDetail) | With past_stats |
|------|---------------------|-----------------|
| 통산 승률 | 있음 (winRateT) | 있음 |
| 올해 승률 | 있음 (winRateY) | 있음 |
| 최근 3개월 top3 진입률 | **없음** | **있음** |
| 최근 폼 판단 | 통산/올해 비율로만 추정 | 실제 경주 결과 기반 |

### 데이터 제약
- result_data는 `[1위, 2위, 3위]` 배열만 저장 → 4위 이하 순위 불가
- 정확한 착순 표준편차(horse_consistency) 계산 불가, top3 진입 여부만 가능
- 기권마(win_odds=0) 제외 필터 적용

### 실행 방법

```bash
# Baseline
uv run python3 packages/scripts/evaluation/evaluate_prompt_v3.py \
  v-baseline prompts/base-prompt-v1.0.md 30 3

# With past stats
uv run python3 packages/scripts/evaluation/evaluate_prompt_v3.py \
  v-with-past-stats prompts/base-prompt-v1.0.md 30 3 --with-past-stats
```

### 비교 지표
- `success_rate` (완전 적중률)
- `average_correct_horses` (평균 적중 말 수)
- `top3` (Top-3 지표)

## Results

**미실행** — 실행 후 이 섹션 업데이트 필요

## Conclusion

미정
