# enriched_data 파이프라인 정비 보류 결정

**Date:** 2026-03-15
**Category:** decision
**Status:** active
**Related files:** `apps/api/routers/collection_v2.py`, `apps/api/tasks/async_tasks.py`

## Context

enriched_data가 전부 NULL인 상태에서, P0~P3 전체 정비(라우터 수정, 백필, 데이터 복구, 모니터링)를 할지 검토. Codex에 현실적 조언 요청.

## Decision

**P0~P3 전체 정비를 보류하고, 피처 ablation 실험을 우선.**

### 선택한 방향
1. 파이프라인/라우터 구조 개편 보류
2. past_stats 피처를 평가 경로에만 임시 주입하여 A/B 테스트
3. 성능이 유의미하게 오르면 그때 enriched_data 파이프라인 정식 승격

### 거절한 방향
- P0: 라우터/작업 디스패치 수정, _save_race_data() 검증 추가
- P1: 1,762건 preprocess → enrich 백필
- P2: 1,575건 부분 상세 누락 복구
- P3: warnings, data_quality_score 모니터링

### 이유
- 개인 프로젝트, 사용자 1명 — 운영 정합성보다 실험 속도 우선
- 현재 예측 시스템은 basic_data + data_adapter로 정상 작동
- enriched_data 피처가 실제로 적중률을 올리는지 증명되지 않음
- "데이터 아키텍처를 예쁘게 만드는 단계가 아니라, 어떤 피처가 적중률을 올리는지 빨리 증명하는 단계" (Codex 조언)

## Impact

- 새 데이터 수집 시 enriched_data는 계속 NULL로 쌓임 (의도적 허용)
- A/B 실험 결과에 따라 이 결정은 `superseded`될 수 있음
