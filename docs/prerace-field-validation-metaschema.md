# 출전표 확정 시점 입력 필드 검증 메타스키마 v1

## 목적

이 문서는 각 입력 필드가 출전표 확정 시점 기준으로 허용 가능한지 판단할 때 반드시 남겨야 하는 최소 검증 규격을 고정한다.

핵심 목표는 하나다.

- 어떤 필드든 `허용`, `조건부 허용`, `보류`, `차단`, `라벨 전용`, `메타 전용` 판정을 내릴 때 같은 행 구조와 같은 필수 근거를 쓰게 만든다.

이 메타스키마는 필드 카탈로그 자체를 대체하지 않는다.

- [prerace-field-metadata-schema.md](/Users/chsong/Developer/Personal/kra-analysis/docs/prerace-field-metadata-schema.md)는 필드별 저장 계약과 운영 플래그를 고정한다.
- [feature-source-timing-contract.md](/Users/chsong/Developer/Personal/kra-analysis/docs/feature-source-timing-contract.md)는 피처 블록 단위의 시간 계약을 고정한다.
- 이 문서는 위 두 계약을 실제 허용 여부 판정으로 연결할 때 필요한 최소 증빙 구조를 고정한다.

## 정규 저장 포맷

- 파일 경로: [data/contracts/prerace_field_validation_spec_v1.csv](/Users/chsong/Developer/Personal/kra-analysis/data/contracts/prerace_field_validation_spec_v1.csv)
- 코드 기준선: [prerace_field_validation_metaschema.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/prerace_field_validation_metaschema.py)
- 포맷: UTF-8 CSV
- 기본 키: `field_path`
- 다중 참조 값: `judgment_basis_refs` 는 `|` 구분자를 사용한다
- 다중 식별자 값: `identifier_aliases`, `identifier_source_tags` 도 `|` 구분자를 사용한다

## 필수 속성

Sub-AC 1에서 요구한 네 가지 필수 속성은 아래 컬럼으로 강제한다.

| 필수 속성 | 메타스키마 컬럼 | 의미 |
| --- | --- | --- |
| 데이터 출처 | `data_source` | 어떤 API 필드, 저장 테이블, 내부 파생 경로를 판정 대상으로 삼았는지 |
| 생성 시점 | `generated_at_kind`, `generated_at_basis` | 값이 언제 생성되는지와 그 시간을 어떻게 판단하는지 |
| 갱신 시점 | `updated_at_kind`, `updated_at_basis` | 값이 언제까지 바뀔 수 있는지와 cutoff 이후 처리 방식 |
| 판정 근거 | `judgment_basis`, `judgment_basis_refs` | 허용/보류/차단 결론의 직접 근거와 참조 문서 |

이 네 묶음 중 하나라도 비어 있으면 해당 행은 운영 기준선 검증 규격으로 인정하지 않는다.

## 필수 컬럼

| 컬럼 | 의미 |
| --- | --- |
| `validation_spec_version` | 검증 규격 버전 |
| `field_path` | 판정 대상 canonical field path |
| `consumer_scope` | `train_inference`, `label_only`, `metadata_only` |
| `availability_stage` | `L-1`, `L0`, `L0 snapshot`, `?`, `L+1` |
| `as_of_requirement` | `DIRECT_PRE_RACE`, `PRE_CUTOFF_SNAPSHOT`, `STORED_AS_OF_SNAPSHOT`, `HISTORICAL_LOOKBACK_BEFORE_RACE_DATE`, `TIMING_UNVERIFIED`, `POSTRACE_ONLY` |
| `train_inference_flag` | 기존 공통 허용 플래그 |
| `allowed_data_category` | 허용/차단 판정 대상 데이터 범주 |
| `time_boundary_rule` | 검증기가 직접 적용할 시간 경계 규칙 |
| `data_source` | 직접 원천 |
| `generated_at_kind` | 생성 시점 분류 |
| `generated_at_basis` | 생성 시점 설명 |
| `updated_at_kind` | 갱신 시점 분류 |
| `updated_at_basis` | 갱신 시점 설명 |
| `judgment_basis` | 판정 핵심 근거 |
| `judgment_basis_refs` | 판정 근거 문서/코드 참조 |
| `identifier_kind` | 검증기 식별 규칙 타입 (`canonical_path`, `leaf_key`, `prefix_path`, `regex_pattern`) |
| `identifier_pattern` | 검증기가 직접 대조할 canonical path, leaf key, prefix, regex |
| `identifier_aliases` | raw/평가 payload에서 함께 탐지해야 하는 별칭 목록 |
| `identifier_source_tags` | `source_field_tags` 기반 탐지용 태그 목록 |
| `late_update_rule` | cutoff 이후 정정 처리 규칙 |
| `exception_rule` | soft-fail, snapshot 유지, raw 저장 전용 등 운영 예외 규칙 식별자 |

선택 컬럼은 `notes` 하나다.

## `allowed_data_category` 값 정의

| 값 | 의미 |
| --- | --- |
| `core_card_direct` | 출전표 핵심 카드처럼 cutoff 이전 직접 사용 가능한 필수/핵심 입력 |
| `race_plan_direct` | 경주계획표처럼 확정 전부터 제공되는 사전 공지 입력 |
| `snapshot_locked_race_state` | 주로/취소/조교처럼 `L0 snapshot` 잠금이 필요한 가변 입력 |
| `stored_detail_lookup` | 상세/누적 정보처럼 당시 저장본만 허용되는 재조회 의존 입력 |
| `historical_aggregate` | 현재 경주보다 과거인 결과만 집계해 만든 합법적 히스토리 파생 |
| `timing_unverified_market` | 존재는 확인됐지만 공개 시점 실측이 끝나지 않아 `HOLD` 인 시장성 신호 |
| `postrace_feedback` | 현재 경주 결과/배당/실황처럼 사후 정보라서 차단해야 하는 입력 |
| `label_result` | 정답/평가 전용 결과 라벨 |
| `metadata_anchor` | `entry_finalized_at` 같은 시점 감사/판정 anchor 메타데이터 |

## `time_boundary_rule` 값 정의

| 값 | 의미 |
| --- | --- |
| `VALUE_AT_OR_BEFORE_ENTRY_FINALIZED_AT` | 값 자체가 `entry_finalized_at` 이전에 이미 확정되어 있어야 함 |
| `SNAPSHOT_CAPTURED_AT_OR_BEFORE_ENTRY_FINALIZED_AT` | 값은 가변이므로 cutoff 이전 캡처본만 허용 |
| `STORED_ROW_AT_OR_BEFORE_ENTRY_FINALIZED_AT` | 과거 재조회 금지. 당시 저장본 시각이 cutoff 이하여야 함 |
| `LOOKBACK_EVENT_DATE_STRICTLY_BEFORE_RACE_DATE` | 과거 집계는 현재 경주보다 과거 날짜만 허용 |
| `MEASUREMENT_REQUIRED_BEFORE_ENTRY_USE` | 공개 시점 실측이 끝나기 전에는 운영 입력 승격 금지 |
| `GENERATED_AFTER_RESULT_CONFIRMATION` | 결과 확정 뒤에만 생성되므로 train/inference 입력 금지 |

## `exception_rule` 값 정의

| 값 | 의미 |
| --- | --- |
| `NONE` | 추가 예외 규칙 없음 |
| `ENTRY_DROP_FROM_OPERATIONAL_SNAPSHOT` | 핵심 키 결손 시 해당 엔트리를 운영 snapshot에서 제외 |
| `KEEP_LOCKED_SNAPSHOT` | cutoff 이전 snapshot을 잠그고 이후 값으로 덮어쓰지 않음 |
| `KEEP_STORED_AS_OF_SNAPSHOT` | 과거 재조회 최신값 금지. 당시 저장본만 사용 |
| `STRICT_PAST_ONLY` | 현재 경주보다 과거인 historical row만 허용 |
| `SOFT_FAIL_EMPTY_BLOCK` | 조인/수집 실패 시 빈 블록을 유지하고 예측은 계속 생성 |
| `RAW_STORE_ONLY` | raw/shadow 감사 보존만 허용하고 feature 입력은 차단 |
| `LABEL_RECOMPUTE_ONLY` | 라벨 재생성만 허용하고 feature 공간에는 절대 병합하지 않음 |
| `METADATA_RETAIN_ONLY` | 시점 감사용 메타데이터로만 유지 |

## `generated_at_kind` / `updated_at_kind` 값 정의

| 값 | 의미 |
| --- | --- |
| `SOURCE_PUBLICATION_TIME` | 원천 API나 공지 row가 공개될 때 생성/갱신됨 |
| `SNAPSHOT_COLLECTION_TIME` | snapshot 수집 시점에 잠가야 함 |
| `STORED_AS_OF_TIME` | 당시 저장본 시각을 기준으로만 해석해야 함 |
| `DERIVED_PARENT_LOCK_TIME` | 부모 snapshot이나 cutoff anchor에서 내부 파생됨 |
| `POSTRACE_CONFIRMATION_TIME` | 결과 확정 후에만 생성됨 |
| `UNVERIFIED_TIME` | 생성/갱신 시점이 아직 실측으로 입증되지 않음 |

## `identifier_kind` 값 정의

| 값 | 의미 |
| --- | --- |
| `canonical_path` | canonical field path 그대로 검증한다 |
| `leaf_key` | payload leaf key 단위로 탐지한다 |
| `prefix_path` | 특정 블록/접두 경로 전체를 차단한다 |
| `regex_pattern` | 구간 실황처럼 패턴으로만 식별 가능한 필드를 정규식으로 탐지한다 |

## 작성 규칙

1. 각 `field_path` 는 판정 행을 정확히 한 개만 가진다.
2. `data_source` 는 추상 설명이 아니라 가능한 한 실제 경로를 적는다.
   - 예: `API214_1.response.body.items.item.winOdds`
   - 예: `POSTGRES.race_odds.odds`
3. `generated_at_basis` 와 `updated_at_basis` 는 반드시 시간 anchor 를 포함해야 한다.
   - 예: `snapshot_meta.entry_finalized_at 이전 수집본`
   - 예: `당시 저장본의 created_at/collected_at 기준`
4. `judgment_basis` 는 결론 문장이어야 한다.
   - 예: `사전 정보이지만 변동성이 있으므로 snapshot 잠금 없이는 허용할 수 없다`
5. `judgment_basis_refs` 는 최소 1개 이상이어야 하며 문서와 구현 중 적어도 하나를 포함하는 것을 권장한다.
6. `late_update_rule` 은 cutoff 이후 값이 들어왔을 때 실제 운영 동작을 적는다.
   - 예: `감사 로그만 남기고 잠긴 입력은 덮어쓰지 않는다`
   - 예: `raw 감사 보존만 허용하고 feature 조인에서는 무조건 차단한다`
7. `BLOCK` 또는 `LABEL_ONLY` 행은 `identifier_kind`, `identifier_pattern`, `identifier_source_tags` 를 비워둘 수 없다.
8. 금지 필드의 `identifier_aliases` 는 raw key, 평가 payload key, legacy alias를 모두 포함해야 한다.
9. 구간 실황처럼 필드명이 규칙적이면 `identifier_kind=regex_pattern` 으로 등록하고 대표 alias를 최소 1개 이상 남긴다.

## 대표 예시

현재 정규 CSV에는 아래 대표 케이스를 포함한다.

- `horses[].chul_no`: `core_card_direct` + `ENTRY_DROP_FROM_OPERATIONAL_SNAPSHOT`
- `race_plan.rank`: 사전 공지 정보라서 `ALLOW`
- `track.weather`: 변동 가능하므로 `ALLOW_SNAPSHOT_ONLY`
- `horses[].training`: snapshot 고정 + `soft-fail empty block`
- `horses[].jkDetail.winRateT`: 과거 재조회 오염 방지를 위해 `ALLOW_STORED_ONLY`
- `horses[].past_stats.recent_top3_rate`: 현재 경주보다 과거 결과만 허용하는 `historical_aggregate`
- `horses[].win_odds`: 공개 시점 미실측이므로 `HOLD`
- `race_odds.win`: 사후 배당이라 `BLOCK`
- `result_data.top3`: 정답 전용이라 `LABEL_ONLY`
- `finish_position` + alias `rank|ord`: 현재 경주 착순이라 `BLOCK`
- `rcTime` + alias `resultTime`: 현재 경주 공식 기록이라 `BLOCK`
- `payout` + alias `dividend`: 결과 확정 후 정산값이라 `BLOCK`
- `sectional_live_metric_pattern`: `sj|bu|se` + `Ord/AccTime/GTime` 패턴 전체를 `BLOCK`
- `snapshot_meta.entry_finalized_at`: 판정 기준 시각이라 `META_ONLY`

## 구현 검증

- 코드 검증: [test_prerace_field_validation_metaschema.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/tests/test_prerace_field_validation_metaschema.py)
- 관련 상위 문서:
  - [prerace-field-availability-judgment-rules.md](/Users/chsong/Developer/Personal/kra-analysis/docs/prerace-field-availability-judgment-rules.md)
  - [holdout-entry-finalization-rule.md](/Users/chsong/Developer/Personal/kra-analysis/docs/holdout-entry-finalization-rule.md)
  - [feature-source-timing-contract.md](/Users/chsong/Developer/Personal/kra-analysis/docs/feature-source-timing-contract.md)
