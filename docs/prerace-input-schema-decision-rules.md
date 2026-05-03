# 출전표 확정 시점 입력 스키마 결정 규칙 v1

## 목적

이 문서는 `입력 스키마 행만 보고` 해당 필드를 최종 예측 입력에
`허용(ALLOW)`, `금지(BLOCK)`, `검토 필요(REVIEW_REQUIRED)` 중 어디로 분류할지
보수적으로 판정하는 최소 결정 규칙을 고정한다.

이 문서가 다루는 범위는 "운영 입력으로 바로 써도 되는가"에 한정된다.

- 필드 자체의 저장 계약은 [출전표 확정 시점 필드 메타데이터 스키마](/Users/chsong/Developer/Personal/kra-analysis/docs/prerace-field-metadata-schema.md)
  를 따른다.
- 필드별 증빙 구조는 [출전표 확정 시점 입력 필드 검증 메타스키마](/Users/chsong/Developer/Personal/kra-analysis/docs/prerace-field-validation-metaschema.md)
  를 따른다.
- 피처 블록 단위 시간 계약은 [피처 생성·조인 원천 시간 메타데이터 계약](/Users/chsong/Developer/Personal/kra-analysis/docs/feature-source-timing-contract.md)
  을 따른다.

코드 기준선은
[prerace_input_schema_decision.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/prerace_input_schema_decision.py)
이다.

## 입력 전제

판정기는 아래 속성만 사용한다.

| 속성 | 의미 |
| --- | --- |
| `consumer_scope` | 이 행이 train/inference 입력인지, label 전용인지, metadata 전용인지 |
| `availability_stage` | `L-1`, `L0`, `L0 snapshot`, `?`, `L+1` |
| `as_of_requirement` | direct pre-race, snapshot lock, stored-only, historical-only, timing-unverified, postrace-only |
| `train_inference_flag` | 기존 공통 운영 플래그 |
| `time_boundary_rule` | cutoff 이전/이후를 구분하는 직접 규칙 |
| `generated_at_kind`, `updated_at_kind` | 생성/갱신 시점 증빙 분류 |
| `identifier_kind`, `identifier_pattern` | 검증기가 해당 필드를 탐지할 수 있는 식별 규칙 |
| `identifier_source_tags` | `pre_entry_allowed`, `snapshot_only`, `stored_only`, `hold`, `post_entry_only` 같은 태그 |

즉, 판정기는 원천 API 실제 응답이나 런타임 로그를 직접 보지 않는다. 스키마 행이
자기 일관성을 갖고 있는지만 평가한다.

## 결정 우선순위

동시에 여러 신호가 보이면 항상 더 보수적인 결론이 이긴다.

| 우선순위 | 규칙 ID | 결론 | 의미 |
| --- | --- | --- | --- |
| 100 | `block_postrace_or_leakage_signal` | `BLOCK` | `L+1`, `POSTRACE_ONLY`, 결과 확정 후 생성, `post_entry_only` 태그가 하나라도 보이면 즉시 금지 |
| 90 | `block_non_feature_scope` | `BLOCK` | `label_only`, `metadata_only`, `LABEL_ONLY`, `META_ONLY` 는 입력 스키마 대상이 아님 |
| 80 | `review_unverified_timing_signal` | `REVIEW_REQUIRED` | `HOLD`, `?`, `TIMING_UNVERIFIED`, `UNVERIFIED_TIME`, 실측 필요 규칙은 운영 승격 전 검토 필요 |
| 70 | `review_inconsistent_allowed_contract` | `REVIEW_REQUIRED` | 허용 플래그와 snapshot/stored-only 시간 계약이 서로 모순되면 검토 필요 |
| 10 | `allow_explicit_prerace_contract` | `ALLOW` | train/inference 범위에서 pre-race 시간 계약이 완결되면 허용 |
| 0 | `review_fallback_incomplete_schema` | `REVIEW_REQUIRED` | 어느 규칙에도 명확히 맞지 않으면 기본값은 검토 필요 |

핵심 원칙은 다음 세 가지다.

1. `BLOCK` 신호가 하나라도 보이면 다른 허용 신호를 무시한다.
2. `BLOCK` 이 없더라도 `HOLD`, `?`, `TIMING_UNVERIFIED` 같은 미실측 신호가 있으면
   자동 허용하지 않는다.
3. `ALLOW` 는 "명시적 pre-race 계약이 완결된 경우" 에만 나온다.

## 허용으로 판정되는 최소 조건

다음 조건을 모두 만족해야 한다.

1. `consumer_scope = train_inference`
2. `train_inference_flag` 가 `ALLOW`, `ALLOW_SNAPSHOT_ONLY`, `ALLOW_STORED_ONLY`
3. `availability_stage` 가 `L-1`, `L0`, `L0 snapshot`
4. `as_of_requirement` 가 `DIRECT_PRE_RACE`, `PRE_CUTOFF_SNAPSHOT`,
   `STORED_AS_OF_SNAPSHOT`, `HISTORICAL_LOOKBACK_BEFORE_RACE_DATE` 중 하나
5. `time_boundary_rule` 가 위 시간 계약과 모순되지 않음
6. `generated_at_kind`, `updated_at_kind` 가 `POSTRACE_CONFIRMATION_TIME`,
   `UNVERIFIED_TIME` 가 아님
7. `identifier_pattern` 이 비어 있지 않음

이 조건 중 하나라도 빠지면 기본값은 `REVIEW_REQUIRED` 다.

## 대표 스키마 예시

### 1. 허용 예시

`horses[].chul_no`

| 속성 | 값 |
| --- | --- |
| `consumer_scope` | `train_inference` |
| `availability_stage` | `L0` |
| `as_of_requirement` | `DIRECT_PRE_RACE` |
| `train_inference_flag` | `ALLOW` |
| `time_boundary_rule` | `VALUE_AT_OR_BEFORE_ENTRY_FINALIZED_AT` |
| 판정 | `ALLOW` |

`track.weather`

| 속성 | 값 |
| --- | --- |
| `availability_stage` | `L0 snapshot` |
| `as_of_requirement` | `PRE_CUTOFF_SNAPSHOT` |
| `train_inference_flag` | `ALLOW_SNAPSHOT_ONLY` |
| `time_boundary_rule` | `SNAPSHOT_CAPTURED_AT_OR_BEFORE_ENTRY_FINALIZED_AT` |
| 판정 | `ALLOW` |

`horses[].jkDetail.winRateT`

| 속성 | 값 |
| --- | --- |
| `availability_stage` | `L-1` |
| `as_of_requirement` | `STORED_AS_OF_SNAPSHOT` |
| `train_inference_flag` | `ALLOW_STORED_ONLY` |
| `time_boundary_rule` | `STORED_ROW_AT_OR_BEFORE_ENTRY_FINALIZED_AT` |
| 판정 | `ALLOW` |

### 2. 검토 필요 예시

`horses[].win_odds`

| 속성 | 값 |
| --- | --- |
| `availability_stage` | `?` |
| `as_of_requirement` | `TIMING_UNVERIFIED` |
| `train_inference_flag` | `HOLD` |
| `time_boundary_rule` | `MEASUREMENT_REQUIRED_BEFORE_ENTRY_USE` |
| 판정 | `REVIEW_REQUIRED` |

### 3. 금지 예시

`race_odds.win`

| 속성 | 값 |
| --- | --- |
| `availability_stage` | `L+1` |
| `as_of_requirement` | `POSTRACE_ONLY` |
| `train_inference_flag` | `BLOCK` |
| `identifier_source_tags` | `post_entry_only` |
| 판정 | `BLOCK` |

`result_data.top3`

| 속성 | 값 |
| --- | --- |
| `consumer_scope` | `label_only` |
| `train_inference_flag` | `LABEL_ONLY` |
| 판정 | `BLOCK` |

`snapshot_meta.entry_finalized_at`

| 속성 | 값 |
| --- | --- |
| `consumer_scope` | `metadata_only` |
| `train_inference_flag` | `META_ONLY` |
| 판정 | `BLOCK` |

## 적용 규칙

새 입력 후보를 추가할 때는 아래 순서를 고정한다.

1. 먼저 검증 메타스키마 행을 작성한다.
2. 그 행을 이 결정 규칙에 넣어 `ALLOW`, `BLOCK`, `REVIEW_REQUIRED` 중 하나를 얻는다.
3. `ALLOW` 가 아니면 최근 기간 홀드아웃 성공 판정용 입력 세트에 넣지 않는다.
4. `REVIEW_REQUIRED` 는 실측 로그 또는 추가 근거 문서가 채워질 때까지 보류한다.
5. `BLOCK` 은 raw 감사 보존만 허용하고 학습/추론 입력 생성 단계에서는 즉시 제거한다.

## 검증

- 단위 테스트:
  [test_prerace_input_schema_decision.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/tests/test_prerace_input_schema_decision.py)
- 대표 예시 상수:
  [prerace_input_schema_decision.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/prerace_input_schema_decision.py)
