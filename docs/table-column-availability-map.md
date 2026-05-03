# 출전표 확정 시점 기준 DB 테이블·컬럼 가용 시점 매핑 v1

## 목적

이 문서는 현재 활성 스키마의 각 테이블·컬럼이 출전표 확정 시점(`entry_finalized_at`) 기준으로 언제 실제로 가용한지, 그리고 최종 운영에서 `확정 이전 사용 가능`인지 `확정 이후 생성 또는 갱신`인지 `메타/운영 전용`인지를 DB 저장 단위로 고정한다.

이 문서는 필드 카탈로그보다 한 단계 아래인 **실제 저장 컬럼** 기준 문서다. 따라서 `races.basic_data` 같은 JSONB 컬럼은 운영상 의미 있는 하위 경로까지 함께 표기한다.

## 범위

- 포함: 현재 활성 마이그레이션/ORM 기준 테이블 `races`, `race_odds`, `predictions`, `jobs`, `job_logs`, `api_keys`, `prompt_templates`, `usage_events`
- 제외: `001_initial_schema.sql`에만 남아 있는 레거시 테이블 `race_results`, `collection_jobs`, `horse_cache`, `jockey_cache`, `trainer_cache`, `prompt_versions`, `performance_analysis`

## 판정 라벨

| 값 | 의미 |
| --- | --- |
| `확정 이전 사용 가능` | `entry_finalized_at` 이하에서 수집·생성 가능하며, 모델 입력 후보가 될 수 있음 |
| `확정 이후 생성 또는 갱신` | 출전표 확정 이후에만 생성되거나, 확정 이후 값이 채워지거나 바뀜 |
| `메타/운영 전용` | 감사·제어 평면용이며 모델 입력에는 넣지 않음 |

추가 표기:

- `L-1`: 출전표 확정 전에도 조회 가능한 누적/마스터 정보
- `L0`: 출전표 확정 시점에 최초 운영 사용 가능
- `L0 snapshot`: `L0`에 존재하지만 cutoff 이전 스냅샷 고정이 필요한 값
- `L+1`: 출전표 확정 이후에만 의미가 생기거나 갱신되는 값
- `mixed`: 한 컬럼 안에 사전/사후 성격이 섞여 있어 하위 경로 분리가 필요한 경우

## 근거 우선순위

1. 스키마 정의
   - `apps/api/migrations/001_unified_schema.sql`
   - `apps/api/migrations/003_add_race_odds.sql`
   - `apps/api/migrations/004_add_job_shadow_fields.sql`
   - `apps/api/migrations/005_add_usage_events.sql`
2. 실제 쓰기 경로
   - `apps/api/services/race_processing_workflow.py`
   - `apps/api/services/result_collection_service.py`
   - `apps/api/services/prerace_storage_policy.py`
3. 운영 시점 규칙
   - `docs/kra-race-lifecycle-timing-matrix.md`
   - `docs/prerace-field-availability-judgment-rules.md`
   - `docs/holdout-entry-finalization-rule.md`

## 1. `races`

| 컬럼/경로 | 실제 가용 시점 | 판정 | 근거 | 메모 |
| --- | --- | --- | --- | --- |
| `races.race_id` | `L-1~L0` | 확정 이전 사용 가능 | `RaceKey.race_id`를 수집 전에 생성하고 `save_collection()`에서 PK로 저장 | 운영 식별자. feature가 아니라 key |
| `races.date`, `races.meet`, `races.race_number` | `L-1~L0` | 확정 이전 사용 가능 | `save_collection()`이 `basic_data`의 식별자를 컬럼으로 복제 | 경주 식별용 정규화 컬럼 |
| `races.race_name`, `races.distance` | 현재 런타임에서는 대체로 `NULL`; 값이 채워지면 사전 원천 상속 | 메타/운영 전용 | 활성 저장 경로는 `basic_data` 중심이고 직접 assign 경로가 없음 | 현재 기준으로는 모델 입력 근거 컬럼으로 쓰면 안 됨 |
| `races.track`, `races.weather` | 현재 런타임에서는 대체로 `NULL`; 값이 채워지면 `L0 snapshot` 상속 | 메타/운영 전용 | 활성 저장 경로는 `basic_data.track.*`; 직접 assign 경로가 없음 | 컬럼값보다 `basic_data.track.*`를 기준으로 써야 함 |
| `races.collection_status` | row 생성 시점부터 존재, 수집 성공 시 `collected` | 메타/운영 전용 | `save_collection()`, `save_collection_failure()` | 제어 평면 상태 |
| `races.enrichment_status` | 전처리/강화 완료 시 갱신 | 메타/운영 전용 | `save_materialized()` | pre-cutoff에 끝나더라도 feature가 아니라 파이프라인 상태 |
| `races.result_status` | `L+1` | 확정 이후 생성 또는 갱신 | `collect_result()`가 결과 수집 후 갱신 | 결과 수집 상태 |
| `races.basic_data` | `mixed`; 하위 경로 기준 사용 | 메타/운영 전용 | `split_prerace_payload_for_storage()` 후 저장 | 컬럼 전체를 통째로 쓰지 말고 하위 경로 기준으로 판정 |
| `races.basic_data.race_info.response.body.items.item[*]` | `mixed` | 메타/운영 전용 | `API214_1` raw 보존 + storage policy shadow 분리 | 같은 raw 안에 허용 필드와 결과 필드가 섞여 있음 |
| `races.basic_data.race_plan.rank`, `budam`, `rc_dist`, `age_cond`, `sex_cond`, `chaksun*` | `L-1~L0` | 확정 이전 사용 가능 | `fetch_race_plan()` + 시점 매트릭스 | `sch_st_time` 제외 경주 조건 블록 |
| `races.basic_data.race_plan.sch_st_time` | `L0 snapshot` | 확정 이전 사용 가능 | `holdout-entry-finalization-rule.md`, `kra-race-lifecycle-timing-matrix.md` | cutoff 이전 스냅샷만 허용 |
| `races.basic_data.track.*` | `L0 snapshot` | 확정 이전 사용 가능 | `fetch_track()` + 시점 매트릭스 | 변동 가능한 사전 컨텍스트 |
| `races.basic_data.cancelled_horses[*]` | `L0 snapshot` | 확정 이전 사용 가능 | `fetch_cancelled_horses()` + 시점 매트릭스 | cutoff 이후 취소 추가분으로 덮어쓰면 안 됨 |
| `races.basic_data.horses[*].{chul_no,hr_no,hr_name,jk_no,jk_name,tr_no,tr_name,ow_no,ow_name,age,sex,name,rank,rating,wg_budam,wg_budam_bigo,wg_hr,ilsu,hr_tool}` | `L0` | 확정 이전 사용 가능 | `fetch_race_card()` + `normalize_and_validate_prerace_payload()` | 출전표 핵심 입력 |
| `races.basic_data.horses[*].win_odds`, `plc_odds` | `?` | 메타/운영 전용 | 시점 매트릭스와 화이트리스트 정책에서 `HOLD` | raw 저장은 허용, 최종 성공 판정 feature는 보류 |
| `races.basic_data.horses[*].hrDetail`, `jkDetail`, `trDetail`, `jkStats`, `owDetail` | `L-1` | 확정 이전 사용 가능 | `fetch_horse_bundle()` + stored-only 규칙 | 과거 재조회 최신값이 아니라 당시 저장본만 허용 |
| `races.basic_data.horses[*].training` | `L0 snapshot` | 확정 이전 사용 가능 | `fetch_training_map()` + 시점 매트릭스 | 이름 매칭 기반이라 soft-fail 허용 |
| `races.basic_data.collected_at` | `L0` | 메타/운영 전용 | `race_processing_workflow.collect()` payload에 기록되고 홀드아웃 시각 산출에 사용 | feature 금지, cutoff 감사용 |
| `races.basic_data.status`, `failed_horses[*]` | `L0` | 메타/운영 전용 | 수집 실패/부분 실패 진단용 | 모델 입력 금지 |
| `races.raw_data.source_field_tags.*` | 수집 시 생성 | 메타/운영 전용 | `build_source_field_tags()` + storage policy | 필드별 허용/차단 감사 정보 |
| `races.raw_data.tagged_field_shadow.*` | 주로 `L+1` shadow | 확정 이후 생성 또는 갱신 | `split_prerace_payload_for_storage()`가 blocked/HOLD 필드를 shadow로 분리 | 결과/구간기록/보류 odds 같은 금지/보류 경로 보관용 |
| `races.raw_data.failure_reason`, `failed_at`, `race_info` | 실패 시 생성 | 메타/운영 전용 | `save_collection_failure()` | 실패 진단용 |
| `races.enriched_data` | 원칙적으로 `L0/L0 snapshot/L-1` 허용 입력의 파생 결과 | 확정 이전 사용 가능 | `save_materialized()`는 `basic_data` 기반 전처리/강화 결과를 저장 | 단, 실제 사용은 필드 registry 화이트리스트를 다시 통과해야 함 |
| `races.enriched_data` 안의 odds 의존 파생(`odds_rank` 등) | `?` 또는 `L+1` 오염 가능 | 메타/운영 전용 | `prediction-input-field-registry.md`에서 `HOLD` | enriched_data 전체를 무조건 feature로 쓰면 안 되는 이유 |
| `races.result_data` | `L+1` | 확정 이후 생성 또는 갱신 | `collect_result()`가 top3/result_items 투영 저장 | 라벨 전용 |
| `races.collected_at` | `L0` | 메타/운영 전용 | `save_collection()`에서 저장, 홀드아웃 fallback 시각으로 사용 | snapshot 준비 시각 추정 근거 |
| `races.enriched_at` | pre-cutoff면 `L0`, 아니면 `L+1`까지 늦어질 수 있음 | 메타/운영 전용 | `save_materialized()` | 운영 SLA 감시용이지 feature 아님 |
| `races.result_collected_at` | `L+1` | 확정 이후 생성 또는 갱신 | `collect_result()` | 결과 확정 시각 근사치 |
| `races.created_at` | row 최초 생성 시점 | 메타/운영 전용 | DB default timestamp | feature 금지 |
| `races.updated_at` | 수집·강화·결과 수집 때마다 갱신 | 메타/운영 전용 | `save_collection()`, `save_materialized()`, `collect_result()` | `L+1` 갱신이 섞이므로 snapshot 시간의 보조 fallback만 허용 |
| `races.data_quality_score`, `warnings`, `horse_count` | 현재 런타임 미사용 또는 사전 데이터 요약 | 메타/운영 전용 | 스키마만 존재, 활성 쓰기 경로는 제한적 | 값이 채워져도 feature보다 품질 진단용으로 다뤄야 함 |

## 2. `race_odds`

| 컬럼/경로 | 실제 가용 시점 | 판정 | 근거 | 메모 |
| --- | --- | --- | --- | --- |
| `race_odds.race_id`, `pool`, `chul_no`, `chul_no2`, `chul_no3`, `source` | `L+1` | 확정 이후 생성 또는 갱신 | `003_add_race_odds.sql`, `_collect_odds_after_result()`, `collect_odds()` | 결과/확정배당 row 식별자 |
| `race_odds.odds` | `L+1` | 확정 이후 생성 또는 갱신 | `API160_1`, `API301` 수집 경로 | 최종 운영 feature 금지 |
| `race_odds.rc_date` | `L+1` row와 함께 적재 | 확정 이후 생성 또는 갱신 | odds UPSERT payload | 검색 키이지만 row 자체가 사후 |
| `race_odds.collected_at` | `L+1` | 확정 이후 생성 또는 갱신 | UPSERT 시 `func.now()` | 결과 직후 배당 수집 시각 |
| `race_odds.id` | row insert 시 생성 | 메타/운영 전용 | DB surrogate key | feature 의미 없음 |

## 3. `predictions`

| 컬럼/경로 | 실제 가용 시점 | 판정 | 근거 | 메모 |
| --- | --- | --- | --- | --- |
| `predictions.prediction_id`, `race_id`, `prompt_id`, `prompt_version`, `created_by`, `model_version` | `L+1` | 확정 이후 생성 또는 갱신 | prediction row는 예측 실행 시점에 생성 | 출전표 확정 이후, 경주 시작 전 생성 가능 |
| `predictions.predicted_positions`, `confidence`, `reasoning`, `execution_time_ms` | `L+1` | 확정 이후 생성 또는 갱신 | 예측 실행 산출물 | 예측 결과 저장용 |
| `predictions.actual_result`, `accuracy_score`, `correct_count` | `L+1` 중에서도 결과 확정 후 | 확정 이후 생성 또는 갱신 | 평가/정답 결합 컬럼 | 학습/평가 감사용, feature 금지 |
| `predictions.created_at` | `L+1` | 확정 이후 생성 또는 갱신 | DB default timestamp | 예측 생성 시각 |

## 4. `jobs`

| 컬럼/경로 | 실제 가용 시점 | 판정 | 근거 | 메모 |
| --- | --- | --- | --- | --- |
| `jobs.job_id`, `type`, `job_kind_v2`, `created_by` | 제어 평면 요청 시 생성 | 메타/운영 전용 | `001_unified_schema.sql`, `004_add_job_shadow_fields.sql` | 모델 입력과 무관 |
| `jobs.status`, `lifecycle_state_v2`, `progress`, `current_step`, `total_steps`, `retry_count`, `task_id` | 실행 중 계속 갱신 | 메타/운영 전용 | job service + canonical status backfill | 운영 상태 머신 |
| `jobs.parameters`, `result`, `error_message`, `tags` | 실행 전후 기록 | 메타/운영 전용 | job orchestration 저장 경로 | 운영 로그/재현용 |
| `jobs.created_at`, `started_at`, `completed_at` | job 생애주기 중 생성/갱신 | 메타/운영 전용 | unified schema | cutoff 판정 근거로 쓰면 안 됨 |

## 5. `job_logs`

| 컬럼/경로 | 실제 가용 시점 | 판정 | 근거 | 메모 |
| --- | --- | --- | --- | --- |
| `job_logs.id`, `job_id` | 로그 row 생성 시 | 메타/운영 전용 | unified schema | 운영 로그 anchor |
| `job_logs.timestamp`, `level`, `message`, `log_metadata` | 실행 중 append-only | 메타/운영 전용 | unified schema | 관측/디버깅용 |

## 6. `api_keys`

| 컬럼/경로 | 실제 가용 시점 | 판정 | 근거 | 메모 |
| --- | --- | --- | --- | --- |
| `api_keys.*` | 운영 계정 생성/사용 시 | 메타/운영 전용 | unified schema | 인증/과금 제어 평면 데이터 |

## 7. `prompt_templates`

| 컬럼/경로 | 실제 가용 시점 | 판정 | 근거 | 메모 |
| --- | --- | --- | --- | --- |
| `prompt_templates.prompt_id`, `version`, `name`, `description`, `template_content` | 프롬프트 등록 시 | 메타/운영 전용 | unified schema | 모델 입력 원천이 아니라 프롬프트 자산 |
| `prompt_templates.total_uses`, `success_rate`, `avg_accuracy`, `is_active`, `is_baseline`, `tags`, `template_metadata`, `created_at`, `updated_at` | 운영 중 갱신 | 메타/운영 전용 | unified schema | 프롬프트 운영 메타데이터 |

## 8. `usage_events`

| 컬럼/경로 | 실제 가용 시점 | 판정 | 근거 | 메모 |
| --- | --- | --- | --- | --- |
| `usage_events.*` | API 요청 처리 시 append | 메타/운영 전용 | `005_add_usage_events.sql`, policy accounting 경로 | 사용량 회계/감사 테이블 |

## 레거시 테이블 처리

`001_initial_schema.sql`의 아래 테이블은 현재 활성 런타임 기준선이 아니므로 본 문서의 운영 판정 범위에서 제외한다.

- `race_results`
- `collection_jobs`
- `horse_cache`
- `jockey_cache`
- `trainer_cache`
- `prompt_versions`
- `performance_analysis`

이 테이블들을 다시 활성화하려면, 재도입 전에 본 문서와 `prerace-field-availability-judgment-rules.md`에 동일한 수준의 시점 판정을 먼저 추가해야 한다.

## 현재 결론

1. **실제 예측 입력 후보가 저장되는 주 테이블은 `races.basic_data`와 제한적으로 `races.enriched_data`뿐이다.**
2. **`races.result_data`, `race_odds`, `predictions.actual_result`, `predictions.accuracy_score`, `predictions.correct_count`는 모두 `L+1`로 고정해야 한다.**
3. **제어 평면 테이블 `jobs`, `job_logs`, `api_keys`, `prompt_templates`, `usage_events`는 전부 메타/운영 전용이며 모델 입력에서 제외해야 한다.**
4. **`races.raw_data`와 `races.basic_data.race_info`는 mixed 컬럼이므로 컬럼 단위 허용이 아니라 하위 경로 단위 허용만 인정해야 한다.**
