# 현재 예측 입력 필드 레지스트리 v1

## 목적

이 문서는 `ralph` 자동 탐색과 현재 `research_clean.py` 예측 경로가 인식하는 입력 후보 전체를
출전표 확정 시점 메타데이터 스키마와 `train_inference_flag` 체계에 맞춰 고정한다.

핵심 목표는 세 가지다.

- 현재 예측 후보군과 T-30 릴리스 승격 후보 76개를 빠짐없이 표준 필드로 등록한다.
- 각 후보가 `ALLOW`, `ALLOW_SNAPSHOT_ONLY`, `ALLOW_STORED_ONLY`, `HOLD` 중 어디에 속하는지 명시한다.
- 최근 기간 홀드아웃과 실전 운영 직전 기준에서 어떤 필드가 즉시 사용 가능하고 어떤 필드가 보류인지 한 번에 확인할 수 있게 한다.

## 기준 파일

- 기계 판독 레지스트리: [prediction_input_field_registry_v1.csv](/Users/chsong/Developer/Personal/kra-analysis/data/contracts/prediction_input_field_registry_v1.csv)
- 상위 정책: [prerace-data-whitelist-blacklist-policy.md](/Users/chsong/Developer/Personal/kra-analysis/docs/prerace-data-whitelist-blacklist-policy.md)
- 메타데이터 저장 계약: [prerace-field-metadata-schema.md](/Users/chsong/Developer/Personal/kra-analysis/docs/prerace-field-metadata-schema.md)
- 플래그 해석 코드: [prerace_field_policy.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/prerace_field_policy.py)

## 현재 결론

- 전체 후보 76개 중 `ALLOW` 30개, `ALLOW_SNAPSHOT_ONLY` 8개, `ALLOW_STORED_ONLY` 33개, `HOLD` 5개로 고정한다.
- `HOLD` 5개는 `winOdds`, `plcOdds`, `odds_rank`, `winOdds_rr`, `plcOdds_rr` 이다.
- 현재 기준선 설정인 [clean_model_config.json](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/autoresearch/clean_model_config.json)은 43개 필드를 사용하며, 모두 `ALLOW` 또는 조건부 허용 플래그 안에 있어야 한다.
- `HOLD` 필드는 raw 저장과 오프라인 분석은 허용하지만, 최근 기간 홀드아웃 최종 성공 판정과 실전 운영 직전 scorecard에는 넣지 않는다.

## T-30 운영 릴리스 overlay

2026-04-26 기준 2주 운영 릴리스는 기존 전체 입력 레지스트리를 대체하지 않고, 새 보강 feature overlay만 별도 계약으로 고정한다. 기계 판독 계약은 [t30_operational_release_features_v1.csv](/Users/chsong/Developer/Personal/kra-analysis/data/contracts/t30_operational_release_features_v1.csv) 이며, 코드는 [t30_release_contract.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/t30_release_contract.py) 로 읽는다.

확정 규칙은 다음과 같다.

- 공식 예측 기준시각은 예정 출발 `T-30분`이다.
- 과거 성적은 `history.race_date < target.race_date` 만 허용하고, 같은 날짜 이전 경주는 제외한다.
- 1차 릴리스 보강 feature는 `past_stats`, `body_weight_delta`, `cancelled_changed_jockey` 로 제한한다.
- `training`, `jkStats`, `ownerStats`, `sectional_speed` 는 이번 릴리스에서 `BACKFILL_ONLY` 이며 모델 입력으로 승격하지 않는다.
- `winOdds`, `plcOdds`, `odds_rank`, `winOdds_rr`, `plcOdds_rr` 는 `AUDIT_ONLY` 이며 운영 릴리스 feature matrix에 들어가면 실패다.
- 기존 core card feature는 이 overlay가 아니라 본 문서의 `ALLOW*` 플래그와 source timing contract로 계속 검증한다.

## 해석 규칙

1. `ALLOW`
   - 출전표 확정 시점 기준으로 바로 학습/추론 입력에 사용할 수 있다.
2. `ALLOW_SNAPSHOT_ONLY`
   - `track.*`, `cancelled_horses[]`, `training` 계열처럼 값이 변할 수 있으므로 cutoff 이전에 잠긴 snapshot만 허용한다.
3. `ALLOW_STORED_ONLY`
   - `hrDetail`, `jkDetail`, `trDetail`, `jkStats`, `owDetail` 기반 피처처럼 사전 정보지만 과거 재조회 오염이 가능한 경우 당시 저장본만 허용한다.
4. `HOLD`
   - 공개 시점 실측이 끝나지 않았거나 odds 의존성이 남아 있는 필드다. 연구는 가능하지만 최종 운영 표준에서는 제외한다.

## 운영 메모

- `weather_code`, `track_pct`, `budam_code`, `dist`, `is_sprint`, `is_mile`, `is_route`, `is_handicap` 은 레지스트리상 `track.*`, `race_plan.*` 를 정규 upstream으로 본다.
- 실제 학습/평가/운영 row 조립은 [prediction_input_schema.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/prediction_input_schema.py)
  의 `build_alternative_ranking_rows_for_race()` 와 `normalize_alternative_ranking_row()` 를 단일 기준으로 사용한다.
- 운영 추론 payload는 같은 모듈의 `validate_alternative_ranking_race_payload()` 로 사전 검증한다.
- 새 입력 후보를 추가할 때는 `SAFE_FEATURES` 수정 전에 이 레지스트리에 먼저 행을 추가하고, 플래그가 `ALLOW*` 인지 확인해야 한다.
