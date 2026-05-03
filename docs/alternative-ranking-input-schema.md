# 대체 랭킹 입력 스키마 v1

## 목적

이 문서는 출전표 확정 시점 정보만 사용하는 `대체 랭킹 입력 스키마`의 운영 기준선을 고정한다.
기준 코드는 [prediction_input_schema.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/prediction_input_schema.py) 이다.

## 기준선

- 스키마 버전: `alternative-ranking-input-v1`
- 원천 레지스트리: [prediction_input_field_registry_v1.csv](/Users/chsong/Developer/Personal/kra-analysis/data/contracts/prediction_input_field_registry_v1.csv)
- 원천·조인 시점 계약: [feature_source_timing_contract_v1.csv](/Users/chsong/Developer/Personal/kra-analysis/data/contracts/feature_source_timing_contract_v1.csv)
- 허용 플래그: `ALLOW`, `ALLOW_SNAPSHOT_ONLY`, `ALLOW_STORED_ONLY`
- 허용 `as_of_requirement`: `DIRECT_PRE_RACE`, `PRE_CUTOFF_SNAPSHOT`, `STORED_AS_OF_SNAPSHOT`, `HISTORICAL_LOOKBACK_BEFORE_RACE_DATE`
- 금지 `as_of_requirement`: `TIMING_UNVERIFIED`, `POSTRACE_ONLY`
- 금지 `join_scope`: `postrace_feedback`
- context 필드: `race_id`, `race_date`, `chulNo`
- label 필드: `target`
- 단일 코드 기준선:
  - schema dict: `alternative_ranking_input_schema()`
  - row 정규화: `normalize_alternative_ranking_row()`
  - row 조립: `build_alternative_ranking_rows_for_race()`
  - 운영 추론 검증: `validate_alternative_ranking_race_payload()`

## 허용 변수 목록

- 허용 feature 수: 65개
- 허용 목록은 [prediction_input_schema.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/prediction_input_schema.py) 의 `ALTERNATIVE_RANKING_ALLOWED_FEATURES` 를 단일 기준선으로 사용한다.
- `research_clean.py` 는 row 조립 후 이 목록과 정확히 일치하는지 검증한다.

## 차단 변수 목록

다음 5개는 출전표 확정 시점 운영 스키마에서 제외한다.

- `winOdds`
- `plcOdds`
- `odds_rank`
- `winOdds_rr`
- `plcOdds_rr`

이 필드들은 레지스트리상 `HOLD` 이므로 row에 남아 있으면 검증 단계에서 실패한다.

## 검증 규칙

1. 선택된 학습 feature 목록은 허용 변수 목록의 부분집합이어야 한다.
2. 조립된 입력 row는 허용 feature 65개와 context/label 필드만 포함해야 한다.
3. context/label/feature 컬럼은 선언된 타입 계약(`text`, `int`, `binary`, `float`)을 만족해야 한다.
4. context/label은 결측 금지, feature는 schema가 허용한 결측 규칙(`allow_nan`)만 허용한다.
5. `HOLD`, `BLOCK`, `LABEL_ONLY`, `META_ONLY` 계열 입력은 row에 존재하면 실패한다.
6. registry에 없는 신규 파생변수는 누수 후보로 간주하고 즉시 실패한다.
7. 각 허용 feature는 [feature_source_timing_contract_v1.csv](/Users/chsong/Developer/Personal/kra-analysis/data/contracts/feature_source_timing_contract_v1.csv)
   에서 정확히 하나의 canonical source owner만 가져야 한다.
8. owner의 `train_inference_flag` 가 `ALLOW*` 가 아니면 실패한다.
9. owner의 `as_of_requirement` 가 `TIMING_UNVERIFIED` 또는 `POSTRACE_ONLY` 이면 실패한다.
10. owner의 `join_scope` 가 `postrace_feedback` 이면 누수 조인 결과로 판정하고 실패한다.
11. 파생변수는 선언된 범위(`source`, `per_entry_derived`, `same_race_derived`, `race_relative_derived`) 밖에서 생성하면 실패한다.

## 최종 학습 입력 판정 기준

최종 학습 입력 산출물은 아래 세 층을 모두 통과해야 한다.

1. 컬럼 allowlist
   - 허용 컬럼은 `race_id`, `race_date`, `chulNo`, `target`, 그리고 `ALTERNATIVE_RANKING_ALLOWED_FEATURES` 65개뿐이다.
   - 이 집합 밖의 컬럼은 금지 컬럼으로 판정한다.
2. 파생변수 registry gate
   - 파생변수는 반드시 [prediction_input_field_registry_v1.csv](/Users/chsong/Developer/Personal/kra-analysis/data/contracts/prediction_input_field_registry_v1.csv)
     에 등록돼 있어야 한다.
   - `HOLD`, `BLOCK`, `LABEL_ONLY`, `META_ONLY` 로 분류된 파생변수는 금지 파생변수로 판정한다.
3. 원천·조인 contract gate
   - 허용 파생변수라도 source owner가 2개 이상이면 canonical source가 고정되지 않은 것으로 보고 실패한다.
   - owner가 `TIMING_UNVERIFIED`, `POSTRACE_ONLY`, `postrace_feedback` 중 하나에 걸리면 누수 조인 결과로 판정한다.

즉, 최종 학습 입력은 "등록된 허용 피처"이면서 동시에 "출전표 확정 시점 이전 계약이 증명된 단일 원천"만 통과한다.

## 코드 참조 경로

- 학습 row 생성: [research_clean.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/autoresearch/research_clean.py)
- 홀드아웃/평가 payload 검증: [prepare.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/autoresearch/prepare.py)
- 평가용 데이터 로딩 검증: [data_loading.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/evaluation/data_loading.py)
- 운영 예측 payload 검증: [predict_only_test.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/evaluation/predict_only_test.py)

## 결정론적 정렬 규칙

실전 대체 랭킹은 [alternative_ranking.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/alternative_ranking.py) 를 단일 기준 구현으로 사용한다.

우선순위 규칙은 아래 순서대로 적용한다.

1. `model_score` 가 있으면 최우선 사용
2. `horse_top3_skill`
3. `year_place_rate`
4. `total_place_rate`
5. `jk_skill`
6. `tr_skill`
7. `rating`
8. `training_score`
9. `recent_training`
10. `age_prime`
11. `allowance_flag`
12. `wgBudam` 오름차순
13. `rest_days` 오름차순

위 규칙까지 동일하면 아래 동률 해소 규칙으로 정렬을 고정한다.

1. `chulNo` 오름차순
2. `hrNo` 오름차순
