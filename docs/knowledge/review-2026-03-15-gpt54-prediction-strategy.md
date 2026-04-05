# GPT-5.4 Pro 예측 전략 컨설팅

**Date:** 2026-03-15
**Category:** review
**Status:** active
**Related files:** packages/scripts/autoresearch/train.py, docs/enriched-data-structure.md, docs/new-api-integration-design.md, apps/api/models/database_models.py

## Context

8개 신규 KRA API 통합 완료 후, 기존 + 신규 API 데이터를 어떻게 활용해야 높은 예측률(삼복연승 set_match 70%+)을 달성할 수 있는지 GPT-5.4 Pro에게 전체 코드베이스 컨텍스트와 함께 컨설팅 요청.

## 핵심 경고: Leakage Audit 필수

- API214_1(경주성적정보)은 순위와 배당률 포함 → 사후 데이터일 가능성
- API160_1은 제목은 "확정배당율"이지만 설명에 "예상배당률" 표기 → 문서 불일치
- API301은 명시적으로 "확정배당율종합" → 사후 확정값
- **`ord`, 확정/사후 배당률이 입력에 섞이면 leakage** → `docs/project-overview.md`의 "경기 전 정보만 사용" 원칙과 충돌
- **0단계로 시점 검증 필수**

## 신규 API 피처 우선순위

| 순위 | 피처 | 이유 |
|------|------|------|
| 1 | 사전 시점 odds / combo odds | crowd prior, QPL/TLA는 삼복연승과 직접 정렬 |
| 2 | training.remkTxt + trngDt | 연초/저경험마 보정에 가장 실용적 |
| 3 | jkStats.qnlRateY/T, winRateY/T | top3 가장 가까운 사람 측 성능 신호 |
| 4 | race_plan.rank/budam/rcDist | "조건 선택자"로 교차 시 효과적 |
| 5 | track.condition/waterPercent | interaction 효과 큼 (jockey/trainer와 교차) |
| 6 | owDetail | 약한 말·신마에서 fallback |
| 7 | cancelled_horses | 예측 신호가 아닌 "상태 재계산 트리거" |

숨은 카드: 기존 `hrDetail.faHrNo/moHrNo` (혈통 ID) → 저표본 말에서 owDetail보다 유용 가능

## 피처 엔지니어링 핵심 원칙

### 1. 경주 내 상대값 우선 (절대값 < 상대 랭크)
- `horse_place_y_rank`, `jk_qnl_rank`, `rating_rank_in_race`
- `gap_to_4th_best` 계열이 단순 rank보다 유용 (top3 경계)

### 2. 신뢰도 가중 Blending (연초 약세 해결)
```python
def blend(rate_y, n_y, rate_t, k):
    w = n_y / (n_y + k)
    return w * rate_y + (1 - w) * rate_t
```
- 말 k=2~4, 기수 k=10~20, 조교사 k=15~30, 마주 k=20~40

### 3. Training 4분할
- training_score (양호=+1, 보통=0, 불량=-1)
- days_since_training, recent_training_flag, training_missing_flag
- 강한 조합: training_score × horse_rcCntY_low, × rest_days_high, × wet_track_flag

### 4. Odds 확률화 (사전 snapshot일 때만)
- pool별 inverse odds → 정규화 → market_top3_prior, market_entropy, favorite_gap
- TLA/QPL을 말 단위 marginal로 변환 → 삼복연승 목적함수와 직접 정렬

### 5. 취소마 = 상태 재계산 트리거
- field_size_live, cancelled_count, favorite_cancelled_flag 재계산
- 취소 반영 후 odds_rank, relative_rank, top3 boundary gap 재산출

## 모델 아키텍처 로드맵

| 단계 | 내용 | 기대 효과 |
|------|------|----------|
| 0 | Leakage audit | 필수 (점수 하락 가능) |
| 1 | Flat modeling table + race-relative features | +1.0~2.5%p |
| 2 | jkStats + training + cancelled 재계산 + context gating heuristic v2 | +1.0~2.0%p |
| 3 | CatBoost y_top3 classifier (categorical + missing 기본 지원) | +1.5~3.0%p |
| 4 | LightGBM rank_xendcg / CatBoostRanker + ensemble | +0.5~1.5%p |
| 5 | Top6 → C(6,3)=20 triplet re-ranker | +0.5~1.5%p |
| 6 | Valid pre-race odds stack / combo marginals | +1.0~2.5%p |

**향상폭은 합산 아님.** 현실적 기대:
- Baseline 0.64~0.67 → **0.68~0.72** 가능
- Baseline 0.612 → **0.65~0.68** 현실적, 70%는 불확실

## Triplet Re-ranker (set_match 직접 최적화)

1. Horse model로 상위 6두 추림
2. C(6,3)=20 조합 생성
3. 조합별 피처: sum_p_top3, min_p_top3, pairwise QPL support, triplet TLA support, score 분산
4. 최고 점수 조합 선택

**핵심 메시지**: 말별 점수 → 3두 조합 점수로 전환해야 ceiling 돌파 가능

## Impact

- **즉시 적용**: leakage audit, race-relative features, blend 함수
- **중기**: CatBoost classifier 전환, context gating
- **장기**: triplet re-ranker, odds marginal 활용
- **`year_place_rate` 중심 단일 스코어 heuristic의 ceiling이 낮다**는 것이 핵심 진단
- odds는 source 혼합 금지 (API160_1과 API301 중 하나로 고정)
