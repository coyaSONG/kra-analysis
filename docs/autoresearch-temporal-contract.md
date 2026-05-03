# Autoresearch 기간·경계 계약 v1

## 목적

이 문서는 동일 원천 데이터 입력을 기준으로 autoresearch 학습·검증 대상 기간, 최근 기간 홀드아웃 경계 규칙, 포함·제외 조건을 한 번에 고정한다. 목적은 다음 3가지다.

- 같은 입력 데이터로 다시 실행하면 기간 경계와 제외 집합이 바뀌지 않게 한다.
- 학습/dev/test 기간과 최종 홀드아웃 경계를 서로 다른 임시 규칙으로 해석하는 일을 막는다.
- 문서 설명과 실제 설정 파일이 같은 계약을 따르도록 기계 검증 가능한 스키마를 둔다.

이 계약은 [최근 기간 홀드아웃 평가 분할 규칙](/Users/chsong/Developer/Personal/kra-analysis/docs/recent-holdout-split-rule.md), [홀드아웃 출전표 확정 시점 산출 규칙](/Users/chsong/Developer/Personal/kra-analysis/docs/holdout-entry-finalization-rule.md), [홀드아웃 스냅샷 필터링 절차 및 저장 포맷](/Users/chsong/Developer/Personal/kra-analysis/docs/holdout-snapshot-filtering-format.md)를 설정 파일 수준으로 연결하는 역할을 한다.

## 동일 원천 데이터 불변식

- `evaluation_contract.same_source_data_required = true` 여야 한다.
- 주 학습 split, rolling window, `mini_val`, `holdout`은 모두 같은 원천 데이터 버전에서 파생돼야 한다.
- 동일 원천 데이터 여부는 실행 시점 재현성 매니페스트의 `source_data.version_id` 와 split manifest의 `manifest_sha256` 조합으로 추적한다.
- 10개 랜덤 시드 반복에서 바뀔 수 있는 것은 모델 내부 난수뿐이며, 기간 경계와 제외 집합은 바뀌면 안 된다.

## 학습·검증 대상 기간

현재 기준 설정 파일은 [clean_model_config.json](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/autoresearch/clean_model_config.json) 이고, 기본 기간 규칙은 다음과 같다.

- `split.train_end` 이전 또는 같은 날짜: 주 학습 구간
- `split.train_end < date <= split.dev_end`: 주 dev 구간
- `date >= split.test_start`: 동일 원천 데이터 내 후행 test 구간

현재 체크인된 기본값은 아래와 같다.

- 학습 종료일: `20250930`
- dev 종료일: `20251130`
- test 시작일: `20251201`

추가 walk-forward 검증은 `rolling_windows` 로 고정한다.

- `fold_a`: 학습 `<= 20250731`, 평가 `20250801 ~ 20250930`
- `fold_b`: 학습 `<= 20250930`, 평가 `20251001 ~ 20251130`
- `fold_c`: 학습 `<= 20251130`, 평가 `20251201 ~ 20251231`

기간 필드는 모두 `YYYYMMDD` 형식이어야 하며 `train_end < dev_end < test_start`, 각 rolling window는 `train_end < eval_start <= eval_end` 를 만족해야 한다.

## 최근 기간 홀드아웃 경계 규칙

최종 성공 판정용 최근 기간 홀드아웃과 연구용 `mini_val` 은 아래 계약으로 고정한다.

- 선택 방식: `time_ordered_complete_date_accumulation`
- 경계 단위: `race_date`
- 날짜 내부 절단: 금지
- 완결 날짜만 선택: 강제
- 시드 불변성: 강제
- 타깃 라벨: `unordered_top3`
- 활성 출전마 규칙: `candidate_filter_minimum_info_fallback_v1`

현재 계약상 최소 규모는 다음과 같다.

- `minimum_holdout_race_count = 500`
- `minimum_mini_val_race_count = 200`

실제 경계 계산은 [recent-holdout-split-rule.md](/Users/chsong/Developer/Personal/kra-analysis/docs/recent-holdout-split-rule.md)의 절차를 그대로 따른다.

1. 최신 완결 평가일부터 역순으로 누적한다.
2. 날짜 내부를 자르지 않는다.
3. 최소 경주 수를 처음 만족하는 가장 이른 날짜를 시작일로 잡는다.
4. `mini_val` 종료일은 holdout 시작일의 직전 완결 평가일이다.
5. 10개 랜덤 시드 반복에서도 이 경계는 바뀌지 않는다.

## 포함·제외 조건

홀드아웃 후보 경주의 포함 조건은 아래를 모두 만족해야 한다.

- `result_status = collected`
- `basic_data` 존재
- 출전표 payload 변환 성공
- 활성 출전마 3두 이상
- top-3 결과가 정확히 3개의 서로 다른 출전번호로 복원 가능
- 누수 검사 통과

strict dataset 판정은 `strict_dataset_selector = include_in_strict_dataset_true` 로 고정한다. 즉 최종 집계 포함 여부는 경주별 `include_in_strict_dataset` 값으로 결정한다.

strict 집계에서 반드시 제외되는 replay 상태는 다음 3개다.

- `late_snapshot_unusable`
- `missing_timestamp`
- `partial_snapshot`

현재 구현 기준 공식 제외 사유 목록은 다음과 같다.

- `insufficient_active_runners`
- `invalid_top3_result`
- `late_snapshot_unusable`
- `leakage_violation`
- `missing_basic_data`
- `missing_result_data`
- `partial_snapshot`
- `payload_conversion_failed`
- `top3_not_in_active_runners`

위 목록은 [holdout_split.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/autoresearch/holdout_split.py)와 [holdout_dataset.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/autoresearch/holdout_dataset.py)의 현재 구현과 동일해야 한다.

## 설정 스키마 기준선

이 계약의 기계 검증 기준선은 [autoresearch_config_schema.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/autoresearch_config_schema.py) 이다.

스키마가 강제하는 핵심 항목은 다음과 같다.

- `format_version`
- `split`
- `rolling_windows`
- `evaluation_contract`
- `model`
- `features`

특히 `evaluation_contract` 는 아래 값을 명시적으로 저장해야 한다.

- `same_source_data_required`
- `selection_method`
- `boundary_unit`
- `minimum_holdout_race_count`
- `minimum_mini_val_race_count`
- `require_complete_race_dates`
- `allow_intra_day_cut`
- `selection_seed_invariant`
- `active_runner_rule`
- `target_label`
- `holdout_rule_version`
- `entry_finalization_rule_version`
- `strict_dataset_selector`
- `excluded_replay_statuses`
- `excluded_race_reasons`

현재 구현에서는 [research_clean.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/autoresearch/research_clean.py)가 평가 시작 전에 이 스키마를 검증한다. 따라서 설정 파일이 문서 계약과 어긋나면 실행 전에 즉시 실패해야 한다.
