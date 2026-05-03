# 피처 생성·조인 원천 시간 메타데이터 계약 v1

## 목적

이 문서는 현재 KRA top-3 무순서 예측 파이프라인이 사용하는 원천 컬럼, 외부 조인 블록, 내부 파생 블록을
`출전표 확정 시점(entry_finalized_at)` 기준으로 언제까지 사용할 수 있는지 한 계약으로 고정한다.

이 계약의 역할은 네 가지다.

1. 피처 생성 코드가 참조하는 원천 컬럼 묶음을 block 단위로 명시한다.
2. 각 block이 `L-1`, `L0`, `L0 snapshot`, `?`, `L+1` 중 어디에 속하는지 고정한다.
3. 외부 테이블/API 조인 시 어떤 key와 어떤 as-of 조건이 필요한지 명시한다.
4. 현재 경주의 사후 정보와 과거 경주의 합법적 historical lookup을 구분하는 최소 기준선을 제공한다.

즉, 이 문서는 "이 피처가 좋아 보이느냐"를 다루지 않는다. 대신 "이 피처 upstream이 출전표 확정 시점 이후 정보인지 아닌지"를 일관되게 판정하는 계약이다.

## 기준 파일

- 설명 문서: [feature-source-timing-contract.md](/Users/chsong/Developer/Personal/kra-analysis/docs/feature-source-timing-contract.md)
- 코드 기준선: [feature_source_timing_contract.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/feature_source_timing_contract.py)
- 정규 CSV: [feature_source_timing_contract_v1.csv](/Users/chsong/Developer/Personal/kra-analysis/data/contracts/feature_source_timing_contract_v1.csv)

## 이 계약이 다루는 범위

- `packages/scripts/feature_engineering.py` 의 원천 블록
- `packages/scripts/autoresearch/research_clean.py` 의 현재 예측 입력 70개
- `races.basic_data`, `races.enriched_data`, `race_odds`, `predictions` 로 이어지는 내부 저장 경로
- KRA API 기반 외부 조인 블록 `API214_1`, `API72_2`, `API189_1`, `API9_1`, `API8_2`, `API12_1`, `API19_1`, `API11_1`, `API14_1`, `API329`

## 저장 포맷

- 경로: `data/contracts/feature_source_timing_contract_v1.csv`
- 포맷: UTF-8 CSV
- 기본 키: `source_block_id`
- 다중 값 컬럼: `source_columns`, `output_fields`, `evidence_refs` 는 `|` 구분자를 사용한다

## 필수 컬럼

| 컬럼 | 의미 |
| --- | --- |
| `contract_version` | 계약 버전 |
| `source_block_id` | 원천 block 식별자 |
| `source_system` | `KRA_API`, `POSTGRES`, `INTERNAL_DERIVED` |
| `source_object` | 원천 API/테이블/파생 블록 |
| `storage_path` | 현재 저장 구조에서 materialize 되는 위치 |
| `grain` | `race`, `race_entry`, `horse`, `jockey`, `trainer`, `owner`, `race_odds_row`, `prediction_row` |
| `source_columns` | 피처 생성 또는 차단 판정에 직접 쓰는 컬럼 목록 |
| `join_keys` | 조인 anchor 설명 |
| `join_scope` | `self_materialized`, `race_key`, `horse_id`, `jockey_id`, `trainer_id`, `owner_id`, `horse_name_fallback`, `same_race_aggregate`, `historical_lookup`, `postrace_feedback` |
| `output_fields` | 이 block이 책임지는 prediction input, computed feature, metadata, blocked source 목록 |
| `availability_stage` | `L-1`, `L0`, `L0 snapshot`, `?`, `L+1` |
| `as_of_requirement` | pre-race 직접 사용, snapshot 고정, stored-only, historical lookup, post-race only 등을 구분 |
| `late_update_rule` | cutoff 이후 정정/재조회 발생 시 처리 규칙 |
| `train_inference_flag` | 기존 field policy와 같은 허용 플래그 |
| `operational_status` | 허용/조건부 허용/보류/금지/메타 전용 등 |
| `evidence_refs` | 판정 근거 문서/코드 |

## `as_of_requirement` 값 정의

| 값 | 의미 |
| --- | --- |
| `DIRECT_PRE_RACE` | 출전표 확정 시점 이전에 직접 조회 가능 |
| `PRE_CUTOFF_SNAPSHOT` | 값은 사전 정보지만 cutoff 이전 snapshot으로 잠가야 함 |
| `STORED_AS_OF_SNAPSHOT` | 사전 정보이나 과거 재조회 오염을 막기 위해 당시 저장본만 허용 |
| `HISTORICAL_LOOKBACK_BEFORE_RACE_DATE` | 과거 경주의 확정 결과를 현재 경주 날짜 이전 범위로만 집계 |
| `TIMING_UNVERIFIED` | 사전 공개 여부가 실측으로 아직 확정되지 않음 |
| `POSTRACE_ONLY` | 현재 경주의 사후 정보라서 feature 조인 금지 |

## 핵심 판정 규칙

1. 같은 API 안에 허용 컬럼과 금지 컬럼이 섞여 있으면 반드시 block을 분리한다.
   - 예: `API214_1` 은 `entry_card_core`, `entry_card_market_odds`, `entry_card_postrace_fields` 로 분리한다.
2. 외부 조인 block은 `join_keys` 와 `join_scope` 가 비어 있으면 안 된다.
3. `ALLOW_SNAPSHOT_ONLY` block은 `availability_stage = L0 snapshot` 또는 `as_of_requirement = PRE_CUTOFF_SNAPSHOT` 이어야 한다.
4. `ALLOW_STORED_ONLY` block은 과거 재조회 최신값 사용 금지를 `late_update_rule` 에 반드시 명시한다.
5. `BLOCK` block은 현재 경주의 결과/배당/예측 피드백처럼 `POSTRACE_ONLY` 여야 한다.
6. historical lookup은 현재 경주보다 이전 날짜만 포함해야 하며, 현재 경주 이후 row가 한 건이라도 들어오면 누수 후보로 본다.

## 현재 계약이 고정하는 최소 결론

1. `API214_1` 기본 카드 비시장 컬럼은 `L0` 직접 사용 가능이지만, 같은 row 안의 결과/구간 기록은 `L+1` 차단이다.
2. `API214_1` 의 `winOdds`, `plcOdds` 와 그 파생은 아직 `TIMING_UNVERIFIED` 이므로 `HOLD` 다.
3. `track`, `cancelled_horses`, `training` 은 모두 `PRE_CUTOFF_SNAPSHOT` 없이는 운영 입력으로 사용할 수 없다.
4. `hrDetail`, `jkDetail`, `trDetail`, `jkStats`, `owDetail` 는 사전 정보이지만 `STORED_AS_OF_SNAPSHOT` 조건을 만족해야 한다.
5. `race_odds`, `predictions.actual_result/accuracy_score/correct_count`, 현재 경주의 post-race raw field는 모두 `POSTRACE_ONLY` 다.

## 구현/검증 기준

- 계약 행 정의: [feature_source_timing_contract.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/feature_source_timing_contract.py)
- 정규 CSV 검증: [test_feature_source_timing_contract.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/tests/test_feature_source_timing_contract.py)
- prediction input 커버리지 기준: [prediction_input_field_registry_v1.csv](/Users/chsong/Developer/Personal/kra-analysis/data/contracts/prediction_input_field_registry_v1.csv)

## 이 문서를 우선 적용해야 하는 상황

- 새 feature를 추가하기 전에 upstream source가 cutoff 이후 정보인지 판단할 때
- 기존 feature가 어느 외부 block과 어떤 join key에 의존하는지 추적할 때
- holdout 재현 입력과 실운영 입력이 같은 as-of 계약을 쓰는지 검증할 때
- `API214_1` 처럼 mixed source 안의 safe field와 blocked field를 분리할 때
