# DB 데이터 저장 구조 — basic_data vs enriched_data

**Date:** 2026-03-15
**Category:** discovery
**Status:** active
**Related files:** `apps/api/services/collection_service.py`, `apps/api/models/database_models.py`, `apps/api/services/collection_enrichment.py`, `packages/scripts/shared/data_adapter.py`

## Context

Supabase DB의 `enriched_data` 컬럼이 1,762건 전부 NULL이고 `enrichment_status`가 전부 `pending`인 것을 발견. 데이터가 잘못된 곳에 저장되었는지 조사.

## Finding

### basic_data와 enriched_data는 서로 다른 용도

| 컬럼 | 용도 | 현재 상태 |
|------|------|-----------|
| `basic_data` | 수집 단계 산출물 (KRA API 원본 + hrDetail/jkDetail/trDetail) | 1,761건 정상 |
| `enriched_data` | 후속 보강 파이프라인 결과 (past_stats, jockey_stats, trainer_stats, weather_impact) | 전부 NULL |

### hrDetail/jkDetail/trDetail은 수집 단계 산출물

- `collection_service.py:355`의 `_collect_horse_details()`가 수집 중에 KRA API를 호출해서 hrDetail/jkDetail/trDetail을 붙임
- `_save_race_data()`가 이를 포함한 전체를 `basic_data`에 저장 — 이것은 **설계 의도대로**
- 초기 분석에서 "잘못된 곳에 저장"이라고 판단했으나, Codex 리뷰를 통해 설계 의도임을 확인

### enriched_data가 비어있는 이유

- `collection_v2.py`의 라우터가 `collect_race_data()`만 호출
- `preprocess_race_data()`/`enrich_race_data()`는 호출하지 않음
- `full_pipeline` (`async_tasks.py:328`)이 3단계를 모두 실행하지만, 현재 라우터에서 사용되지 않음
- `options.enrich=True`가 기본값이지만 실제로 무시됨 (API 계약 불일치)

### result_data 구조

- `[1위출전번호, 2위출전번호, 3위출전번호]` — top3 배열만 저장
- 4위 이하 순위 정보 없음
- `collection_enrichment.py:117`은 `result_data.get("horses", [])` 형태를 기대하지만 실제 구조와 불일치

### 데이터 품질 이슈

- 1건 (`20260221_1_1`): horses가 빈 배열인데 `collected` 상태 → `failed`로 교정 완료
- 1,575건: 일부 말에서 hrDetail/jkDetail/trDetail 중 하나 이상 누락

## Impact

- `data_adapter.py`가 basic_data → 평가 스크립트 포맷 변환을 담당하며, 현재 시스템은 정상 작동
- enriched_data 파이프라인 실행은 피처 ablation 실험에서 효과가 입증된 후에만 진행
- 새 데이터 수집 시에도 enriched_data는 채워지지 않음 (라우터 미수정 상태)
