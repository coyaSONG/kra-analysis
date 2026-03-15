# Autoresearch 휴리스틱 최적화 실험

**Date:** 2026-03-15
**Category:** experiment
**Status:** completed
**Related files:** `packages/scripts/autoresearch/train.py`, `packages/scripts/autoresearch/prepare.py`

## Context

Codex가 초기 autoresearch 실험(horse_place_rate 기반, set_match=0.700)을 수행한 후, Claude가 후속 최적화를 진행. 총 1,842경주 데이터를 활용하여 체계적 피처 탐색 및 가중치 최적화.

## Method

1. **Snapshot 확대**: 20+50 → 200+500경주 (prepare.py 수정)
2. **123개 수치 피처 자동 탐색**: 모든 numeric 필드를 단일 예측자로 테스트
3. **Grid search**: k (smoothing), w2 (2위 가중치), favorite bonus, odds signal 등 조합 탐색
4. **LLM 하이브리드 테스트**: Sonnet으로 full/selective 접근 시도

## Results

### 최종 모델
```
score = places_y / (starts_y + 2) + 0.06 / winOdds
fallback: total_places / (total_starts + 15)
tiebreaker: (total_place_rate, -odds_rank)
```

### 성능
| 평가 세트 | 경주 수 | set_match |
|-----------|---------|-----------|
| mini_val | 200 | 0.640 |
| holdout | 500 | 0.667 |
| 전체 | 1,842 | 0.612 |

### 월별 추세 (연도 통계 축적 효과)
- 1-2월: 0.44-0.47 (연초, 통계 부족)
- 7-10월: 0.61-0.65
- 11-12월: 0.67-0.68 (통계 풍부)

### 시도했지만 효과 없었던 것들
- 2위 가중치 할인 (w2=0.8) — 20경주에서만 유효, 대규모에서 과적합
- Favorite bonus — 소규모에서만 유효
- 기수/조교사 통계 — year_rate 대비 추가 정보 없음
- LLM 하이브리드 (Sonnet) — 0.683/0.767로 순수 휴리스틱(0.800) 대비 악화
- Adaptive blend (연초 보정) — 모든 threshold에서 악화
- rest_penalty, age_prime, horse_win_rate — 무효

## Impact

- **year_place_rate가 단일 최강 피처**: 총 경력보다 당해년도 실적이 중요
- **odds는 보조 신호로만 유효**: 단독 0.50, 보정 신호로 +0.7%p
- **LLM은 구조화 수치 데이터 판단에 부적합** (Sonnet 기준)
- **20경주 mini_val 최적화는 위험**: 반드시 대규모 검증 필요
- **연초(1-2월) 성능 약화**는 구조적 한계 — 연도 통계가 핵심 신호인 이상 불가피
