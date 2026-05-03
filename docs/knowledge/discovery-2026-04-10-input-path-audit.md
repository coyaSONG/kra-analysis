# KRA 예측 입력 경로 감사

**Date:** 2026-04-10  
**Category:** discovery  
**Status:** active  
**Related files:** `packages/scripts/autoresearch/research_clean.py`, `packages/scripts/autoresearch/prepare.py`, `packages/scripts/autoresearch/train.py`, `packages/scripts/evaluation/data_loading.py`, `packages/scripts/evaluation/predict_only_test.py`, `packages/scripts/autoresearch/research_hgb.py`, `packages/scripts/feature_engineering.py`, `packages/scripts/shared/prediction_input_schema.py`

## 목적

출전표 확정 시점 기준으로 허용되는 정보만 사용해야 한다는 운영 원칙을 기준으로, 현재 저장소의 학습·평가·운영 추론 경로가 실제로 어떤 원천 컬럼과 파생 피처를 사용하거나 노출하는지 코드 기준으로 전수 점검한다.

이 문서는 세 가지를 고정한다.

1. 경로별 입력 생성 지점과 upstream source block
2. 현재 코드가 직접 쓰는 raw source 컬럼과 derived feature 목록
3. `ALLOW`, `ALLOW_SNAPSHOT_ONLY`, `ALLOW_STORED_ONLY`, `HOLD`, `BLOCK` 기준의 허용/금지 판정

## 기준 문서와 계약

- 필드 플래그 해석: `packages/scripts/shared/prerace_field_policy.py`
- prediction input registry: `data/contracts/prediction_input_field_registry_v1.csv`
- source timing contract: `data/contracts/feature_source_timing_contract_v1.csv`
- 상위 정책: `docs/prerace-data-whitelist-blacklist-policy.md`

## 경로별 결론 요약

| 경로 | 입력 생성 지점 | 실제 입력 상태 | 판정 |
| --- | --- | --- | --- |
| 학습 주경로 | `autoresearch/prepare.py` -> `autoresearch/research_clean.py` | `filter_prerace_payload()`와 `validate_operational_dataset_payload()`를 통과한 뒤 43개 feature row 생성 | 허용 |
| 운영 추론 주경로 | `autoresearch/prepare.py` -> `autoresearch/train.py` | snapshot 필터 후 `train.select_features()`에서 다시 정책 필터 적용 | 허용 |
| 평가 LLM 경로 | `evaluation/data_loading.py` -> `evaluation/prediction_service.py` | `compute_race_features()`는 쓰지만 payload 정책 필터를 적용하지 않아 raw `winOdds`/`plcOdds`가 prompt JSON에 남음 | 부분 위반 |
| 레거시 예측 테스트 | `evaluation/predict_only_test.py` | raw odds와 구간 필드(`se*`, `sj*`)를 직접 적재해 prompt에 전달 | 금지 |
| 레거시 HGB 연구 | `autoresearch/research_hgb.py` | `winOdds`, `plcOdds`, `odds_rank`, `se*`, `sj*` 계열을 feature로 사용 | 금지 |

## 공통 원천 블록 분류

### 1. 즉시 허용 `ALLOW`

현재 코드 기준으로 아래 raw block은 출전표 확정 시점 direct input으로 허용된다.

- `API214_1` 기본 카드 핵심 필드
  - `horses[].chul_no`
  - `horses[].hr_no`
  - `horses[].hr_name`
  - `horses[].jk_no`
  - `horses[].jk_name`
  - `horses[].tr_no`
  - `horses[].tr_name`
  - `horses[].ow_no`
  - `horses[].ow_name`
  - `horses[].age`
  - `horses[].sex`
  - `horses[].name`
  - `horses[].rank` or normalized `class_rank`
  - `horses[].rating`
  - `horses[].wg_budam`
  - `horses[].wg_budam_bigo`
  - `horses[].wg_hr`
  - `horses[].ilsu`
  - `horses[].hr_tool`
- 경주 기본 컨텍스트
  - `race_plan.rc_dist`
  - `race_plan.budam`
  - `race_info.rcDate`
  - `race_info.rcNo`
  - `race_info.meet`

### 2. snapshot 고정 필요 `ALLOW_SNAPSHOT_ONLY`

현재 값이 변동될 수 있어 cutoff 이전 snapshot으로 잠가야 하는 block이다.

- `track.weather`
- `track.track`
- `track.waterPercent`
- `cancelled_horses[]`
- `horses[].training.*`

### 3. 당시 저장본만 허용 `ALLOW_STORED_ONLY`

현재 시점 재조회로 과거 값을 오염시킬 수 있어 당시 저장본만 허용되는 block이다.

- `horses[].hrDetail.*`
- `horses[].jkDetail.*`
- `horses[].trDetail.*`
- `horses[].jkStats.*`
- `horses[].owDetail.*`
- `horses[].past_stats.*`

### 4. 보류 `HOLD`

현재 정책상 raw 저장은 가능하지만 최종 학습/운영 입력에는 넣지 말아야 하는 block이다.

- `horses[].win_odds`
- `horses[].plc_odds`
- `horses[].computed_features.odds_rank`
- `model_input.winOdds_rr`
- `model_input.plcOdds_rr`

### 5. 금지 `BLOCK`

현재 경주의 사후 정보 또는 누수 후보 block이다.

- `ord`, `ordBigo`, `rankRise`, `diffUnit`
- `race_odds.*`
- 구간/실황 패턴
  - `sj*Ord`
  - `se*AccTime`
  - `bu*Ord`
  - 그 race-relative 파생

## 공통 파생 피처 목록

`packages/scripts/feature_engineering.py` 가 생성하는 `computed_features`는 아래와 같다.

### 허용 or 조건부 허용

- `burden_ratio`
- `jockey_win_rate`
- `jockey_place_rate`
- `jockey_form`
- `jockey_recent_win_rate`
- `horse_win_rate`
- `horse_place_rate`
- `horse_avg_prize`
- `recent_top3_rate`
- `recent_win_rate`
- `recent_race_count`
- `trainer_win_rate`
- `trainer_place_rate`
- `rest_days`
- `rest_risk`
- `age_prime`
- `horse_top3_skill`
- `horse_starts_y`
- `horse_low_sample`
- `jk_qnl_rate_y`
- `jk_qnl_rate_t`
- `jk_skill`
- `tr_skill`
- `training_score`
- `training_missing`
- `days_since_training`
- `recent_training`
- `owner_win_rate`
- `owner_skill`
- `rating_rank`
- `horse_skill_rank`
- `jk_skill_rank`
- `tr_skill_rank`
- `wg_budam_rank`
- `gap_3rd_4th`
- `field_size`
- `field_size_live`
- `wet_track`
- `cancelled_count`

### 정책상 보류

- `odds_rank`

### 구현상 생성되지만 현재 모델 입력 미사용

- `horse_consistency`

## 1. 학습 주경로 감사

### 코드 경로

- snapshot 구성: `packages/scripts/autoresearch/prepare.py`
- 최종 row 생성: `packages/scripts/autoresearch/research_clean.py`
- input schema 검증: `packages/scripts/shared/prediction_input_schema.py`
- 학습 설정: `packages/scripts/autoresearch/clean_model_config.json`

### 입력 생성 순서

1. `holdout_dataset.select_allowed_basic_data()` 가 `basic_data`에서 `race_info`, `horses`, `race_plan`, `track`, `cancelled_horses`, `failed_horses`만 남긴다.
2. `prepare._build_snapshot_race_data()` 가 enriched payload를 만들고 `_extract_race_data()`에서 `strip_forbidden_fields()`를 적용한다.
3. `prepare._extract_race_data()` 가 `compute_race_features()`를 호출한다.
4. `research_clean._sanitize_training_race_payload()` 가 `filter_prerace_payload()`를 적용한다.
5. `research_clean._validate_final_training_race_payload()` 가 leakage 검사와 operational dataset 검증을 통과시킨다.
6. `research_clean._build_feature_rows()` 가 feature row를 만든다.
7. `validate_alternative_ranking_dataset_rows()` 가 row에 허용 feature만 있는지 다시 검증한다.

### 현재 학습 row가 직접 사용하는 raw source 컬럼

- core card direct
  - `rating`
  - `wgBudam`
  - `wgHr`
  - `age`
  - `chulNo`
  - `sex`
  - `class_rank`
  - `wgBudamBigo`
- race context
  - `race_info.weather`
  - `race_info.track`
  - `race_info.budam`
  - `race_info.rcDist`
- stored-only detail blocks
  - `hrDetail.rcCntY`
  - `hrDetail.rcCntT`
  - `hrDetail.ord1CntY`
  - `hrDetail.ord2CntY`
  - `hrDetail.ord3CntY`
  - `hrDetail.ord1CntT`
  - `hrDetail.ord2CntT`
  - `hrDetail.ord3CntT`
  - `jkDetail.rcCntY`
  - `jkDetail.rcCntT`
  - `jkDetail.ord1CntY`
  - `jkDetail.ord2CntY`
  - `jkDetail.ord3CntY`
  - `jkDetail.ord1CntT`
  - `jkDetail.ord2CntT`
  - `jkDetail.ord3CntT`
  - `trDetail.rcCntY`
  - `trDetail.rcCntT`
  - `trDetail.ord1CntY`
  - `trDetail.ord2CntY`
  - `trDetail.ord3CntY`
  - `trDetail.ord1CntT`
  - `trDetail.ord2CntT`
  - `trDetail.ord3CntT`
- snapshot-only blocks
  - `training.*`
  - `cancelled_horses[]`

### 현재 학습 모델이 선택한 43개 feature

모두 `clean_model_config.json` 기준이며, registry 상 `ALLOW`, `ALLOW_SNAPSHOT_ONLY`, `ALLOW_STORED_ONLY` 안에 있다.

- direct/core
  - `rating`
  - `wgBudam`
  - `wgHr_value`
  - `age`
  - `draw_no`
  - `sex_code`
  - `class_code`
  - `allowance_flag`
- race context
  - `weather_code`
  - `track_pct`
  - `budam_code`
  - `field_size`
  - `is_handicap`
  - `dist`
  - `is_sprint`
  - `is_mile`
  - `is_large`
- skill/stats
  - `horse_win_rate`
  - `jockey_win_rate`
  - `jockey_place_rate`
  - `trainer_win_rate`
  - `trainer_place_rate`
  - `rest_days`
  - `rest_risk_code`
  - `rating_rank`
  - `age_prime`
  - `year_place_rate`
  - `total_place_rate`
  - `jockey_total_place_rate`
  - `trainer_total_place_rate`
  - `horse_top3_skill`
  - `horse_starts_y`
  - `jk_skill`
  - `tr_skill`
  - `jk_place_rate_y`
  - `tr_place_rate_y`
- race-relative
  - `rating_rr`
  - `horse_place_rate_rr`
  - `jockey_place_rate_rr`
  - `trainer_place_rate_rr`
  - `year_place_rate_rr`
  - `total_place_rate_rr`
  - `draw_rr`

### 학습 경로 판정

- `ALLOW`: 직접 허용 필드만 포함된 feature 다수
- `ALLOW_SNAPSHOT_ONLY`: `weather_code`, `track_pct` 등 snapshot 계열 포함
- `ALLOW_STORED_ONLY`: performance/stat 계열 다수 포함
- `HOLD`: 최종 config 기준 미사용
- `BLOCK`: row 생성 전에 제거

결론: 학습 주경로는 현재 정책을 만족한다.

## 2. 운영 추론 주경로 감사

### 코드 경로

- snapshot 생성: `packages/scripts/autoresearch/prepare.py`
- 추론용 payload 축소: `packages/scripts/autoresearch/train.py`
- fallback ranking: `packages/scripts/shared/alternative_ranking.py`

### 운영 추론 payload에 남는 raw source 컬럼

`train.select_features()`는 `filter_prerace_payload()`를 한 번 더 호출하므로 아래 block만 남긴다.

- core card
  - `chulNo`, `hrName`, `hrNo`
  - `jkName`, `jkNo`
  - `trName`, `trNo`
  - `owName`, `owNo`
  - `age`, `sex`
  - `class_rank`
  - `rating`
  - `wgBudam`, `wgBudamBigo`, `wgHr`
  - `ilsu`, `hrTool`
- race context
  - `rcDate`, `rcNo`, `meet`, `rcDist`, `budam`, `ageCond`
- snapshot-only blocks
  - `track.*`
  - `cancelled_horses[]`
  - `training.*`
- stored-only blocks
  - `hrDetail.*`
  - `jkDetail.*`
  - `trDetail.*`
  - `jkStats.*`
  - `owDetail.*`

### 운영 추론이 실제 소비하는 파생 피처

- prompt formatting에서 직접 읽는 값
  - `horse_win_rate`
  - `horse_place_rate`
  - `jockey_win_rate`
  - `trainer_win_rate`
  - `rest_days`
  - `rest_risk`
- fallback ranking이 직접 읽는 값
  - `horse_top3_skill`
  - `jk_skill`
  - `tr_skill`
  - `training_score`
  - `recent_training`
  - `age_prime`
  - `rest_days`
  - `rating`
  - `wgBudam`
  - `wgBudamBigo`
  - `chulNo`
  - `hrNo`
  - `hrDetail.*` 기반 `year_place_rate`, `total_place_rate`

### 운영 추론 판정

- `ALLOW`와 `ALLOW_*` 계열만 노출
- `winOdds`, `plcOdds`, `odds_rank`, 결과 필드, 메타 필드는 제거

결론: 운영 추론 주경로는 현재 정책을 만족한다.

## 3. 평가 LLM 경로 감사

### 코드 경로

- 데이터 조립: `packages/scripts/evaluation/data_loading.py`
- prompt 직렬화: `packages/scripts/evaluation/prediction_service.py`

### 현재 평가 경로가 prompt JSON에 노출하는 raw source 컬럼

- `raceInfo`
  - `rcDate`
  - `rcNo`
  - `rcName`
  - `rcDist`
  - `track`
  - `weather`
  - `meet`
- `horses[]`
  - `chulNo`
  - `hrName`
  - `hrNo`
  - `jkName`
  - `jkNo`
  - `trName`
  - `trNo`
  - `wgBudam`
  - `winOdds`
  - `plcOdds`
  - `rating`
  - `rank`
  - `age`
  - `sex`
  - `hrDetail`
  - `jkDetail`
  - `trDetail`
  - `past_stats` when `with_past_stats=True`
- `candidate_filter`

### 현재 평가 경로가 생성하는 파생 피처

- `compute_race_features()` 전체
- 단, `validation_mode="exclude"` 기본값 때문에 `odds_rank`는 `None`으로 내려가고, raw `winOdds`/`plcOdds`는 그대로 남는다.

### 평가 경로 판정

- 허용
  - core card direct
  - stored-only detail blocks
  - `compute_race_features()`가 만든 non-HOLD derived feature
- 위반
  - raw `winOdds`
  - raw `plcOdds`
  - 정책 필터 미적용 상태의 전체 `hrDetail`/`jkDetail`/`trDetail` 블록 전달

결론: evaluation prompt 경로는 strict 기준의 최종 성공 판정용 입력으로는 사용할 수 없다. raw odds 제거와 payload-level `filter_prerace_payload()` 적용이 필요하다.

## 4. 레거시 예측 테스트 경로 감사

### 코드 경로

- `packages/scripts/evaluation/predict_only_test.py`

### 직접 사용하는 raw source 컬럼

- 허용 가능 core card
  - `chulNo`, `hrName`, `hrNo`, `jkName`, `jkNo`, `trName`, `trNo`
  - `wgBudam`, `wgHr`, `age`, `sex`, `rank`, `rating`, `ilsu`
- 정책상 보류
  - `winOdds`
  - `plcOdds`
- 정책상 금지
  - `se_3cAccTime`
  - `se_4cAccTime`
  - `sj_3cOrd`
  - `sj_4cOrd`
  - `seS1fAccTime`
  - `sjS1fOrd`
  - `seG1fAccTime`
  - `sjG1fOrd`

### 판정

- `winOdds == 0` 로 후보를 제외하는 로직이 들어가 있다.
- 사후 구간 필드를 직접 horse payload에 넣는다.

결론: strict 연구/운영 기준에서는 금지 경로다. 유지하더라도 legacy-only로 격리해야 한다.

## 5. 레거시 HGB 연구 경로 감사

### 코드 경로

- `packages/scripts/autoresearch/research_hgb.py`

### 직접 사용하는 feature 목록 중 금지/보류 항목

- `HOLD`
  - `winOdds`
  - `plcOdds`
  - `odds_rank`
  - `winOdds_rr`
  - `plcOdds_rr`
- `BLOCK`
  - `seG1fAccTime`
  - `sjG1fOrd`
  - `seG3fAccTime`
  - `sjG3fOrd`
  - `seS1fAccTime`
  - `sjS1fOrd`
  - `seG1fAccTime_rr`
  - `sjG1fOrd_rr`
  - `seG3fAccTime_rr`
  - `sjG3fOrd_rr`
  - `seS1fAccTime_rr`
  - `sjS1fOrd_rr`

### 판정

`research_hgb.py`는 현재 출전표 확정 시점 strict 정책과 호환되지 않는다. 회귀 테스트나 과거 탐색 참고용으로만 남겨야 한다.

## 최종 감사 결론

1. strict 기준을 만족하는 주경로는 `prepare.py` -> `research_clean.py`와 `prepare.py` -> `train.py`다.
2. `evaluation/data_loading.py`는 `compute_race_features()`의 validation만 믿고 payload-level 필터를 생략하고 있어 raw `winOdds`/`plcOdds`가 LLM prompt에 유출된다.
3. `evaluation/predict_only_test.py`와 `autoresearch/research_hgb.py`는 각각 odds/구간 필드를 직접 사용하므로 strict 평가와 실운영 기준에서 제외해야 한다.
4. 현재 최종 학습 config(`clean_model_config.json`)의 43개 feature는 registry 상 허용 범위 안에 있다.

## 후속 작업 제안

- `evaluation/data_loading.py`에 `filter_prerace_payload()`를 적용해 평가 경로를 strict 경로와 맞춘다.
- `predict_only_test.py`와 `research_hgb.py`는 `legacy_non_strict` 라벨을 문서와 실행 진입점에 명시한다.
- 운영 기준 문서에서 `evaluation` 경로가 strict/legacy 중 어디에 속하는지 실행 명령 단위로 분리한다.
