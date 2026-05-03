# 최근 기간 홀드아웃 평가 분할 규칙 v1

## 목적

이 문서는 KRA 전 경주 대상 상위 3두 무순서 적중 시스템의 최종 성공 판정에 사용할 "최근 기간 홀드아웃"을 어떻게 고정할지 정의한다. 목적은 다음 3가지를 동시에 만족하는 것이다.

- 실제 운영과 같은 시간순 평가만 허용한다.
- 최근 구간 일부 경주만 골라 쓰는 선택 편향을 막는다.
- 출전표 확정 시점에 알 수 있는 정보만 사용했다는 점을 검증 가능하게 남긴다.

이 규칙은 최종 성공 판정, 10개 랜덤 시드 반복 안정성 평가, 자동 재학습 직전 회귀 검증에 공통 적용한다.

출전표 확정 시점 산출 자체의 상세 규칙은 [docs/holdout-entry-finalization-rule.md](/Users/chsong/Developer/Personal/kra-analysis/docs/holdout-entry-finalization-rule.md)를 따른다.

## 용어

- 평가 단위: `race_id` 기준 개별 경주
- 평가일: `races.date` 기준 KRA 경주일. 같은 날짜의 서울/제주/부산경남 경주는 하나의 묶음으로 취급한다.
- 최신 완결 평가일: 해당 날짜의 KRA 경주가 모두 평가 가능 상태이거나, 평가 제외 사유가 공식적으로 확정된 날짜
- 최근 기간 홀드아웃: 최신 완결 평가일부터 역순으로 누적한 최종 판정용 최근 구간
- 연구용 검증 구간(`mini_val`): 홀드아웃 바로 이전 구간. 탐색과 조기 회귀 감시에만 사용

## 분할 원칙

1. 시간순 고정 분할만 허용한다. 무작위 분할은 탐색용 내부 검증에만 사용하고 최종 성공 판정에는 절대 사용하지 않는다.
2. 분할 경계는 경주 단위가 아니라 평가일 단위로 자른다. 같은 날짜의 일부 경주만 홀드아웃에 넣고 일부는 학습/검증에 남기지 않는다.
3. 홀드아웃 대상은 "최근"이어야 하며, 최신 완결 평가일에서 시작해 역순으로 잡는다.
4. 홀드아웃과 `mini_val`은 서로 겹치면 안 된다.
5. 홀드아웃과 `mini_val`은 모두 출전표 확정 시점 정보만으로 재현 가능한 입력 스냅샷을 기준으로 해야 한다.

## 포함 조건

개별 경주가 평가 모집단에 포함되려면 아래 조건을 모두 만족해야 한다.

- `races.collection_status = 'collected'`
- `races.result_status = 'collected'`
- `basic_data`가 존재하고 `convert_basic_data_to_enriched_format()` 변환에 성공한다.
- 변환 후 활성 출전마가 3두 이상이다.
- 활성 출전마 판정은 `filter_candidate_runners()` 기준을 우선 적용한다.
- 1차 보완(`zero_market_signal`, `wg_budam_outlier` 재편입) 이후에도 3두 미만이면, 공식 취소마를 제외한 raw row 중 `chulNo`, `hrName`, `age`, `sex`, `wgBudam` 최소 정보가 남은 마필을 최종 폴백으로 포함한다.
- `result_data`에서 정규화한 top-3 결과가 정확히 3개의 서로 다른 출전번호로 복원된다.
- `packages/scripts/evaluation/leakage_checks.py` 기준 사후 결과 필드 누수 검사를 통과한다.

## 제외 조건

다음 중 하나라도 해당하면 해당 경주는 점수 집계 대상에서 제외한다.

- 공식 취소, 불성립, 중지 등으로 top-3 결과가 성립하지 않는 경주
- 출전취소 반영 후 활성 출전마가 3두 미만인 경주
- `basic_data` 누락, 손상, 변환 실패로 출전표 확정 시점 입력을 재구성할 수 없는 경주
- `result_data` 누락 또는 비정상 형태로 top-3 정답을 확정할 수 없는 경주
- 누수 검사 실패 경주

공식 취소/불성립은 "의도적 제외"로 분류하고, 단순 수집 실패/변환 실패는 "데이터 결손"으로 분리 기록한다.

## 누락 데이터 처리 기준

### 1. 마필 단위 부분 누락

다음과 같은 부분 누락은 경주 제외 사유로 사용하지 않는다.

- `hrDetail`, `jkDetail`, `trDetail` 일부 필드 누락
- `track`, `weather`, `race_plan`, `cancelled_horses` 등 부가 메타데이터 누락
- 수치형 상세 필드의 공란 또는 0 치환 가능 값

이 경우 현재 로더/피처 엔지니어링 기본값으로 채우고 경주는 유지한다. 부분 누락 때문에 최근 경주를 골라 버리면 운영 현실성과 최신성 평가가 무너진다.

### 2. 경주 단위 필수 누락

다음 중 하나라도 누락되면 해당 경주는 "평가 불가 경주"로 본다.

- `race_id`, `date`, `meet`, `race_number`
- 변환 가능한 `basic_data`
- 활성 출전마 3두 이상
- 정규화 가능한 top-3 결과

### 3. 평가일 단위 완결성 규칙

최종 홀드아웃은 평가일 단위 완결성을 만족해야 한다.

- 어떤 날짜라도 KRA 경주 중 하나가 단순 데이터 결손 상태면, 그 날짜 전체를 최종 홀드아웃에서 제외한다.
- 최신 날짜가 완결되지 않았으면, 홀드아웃 종료 경계는 직전 완결 날짜로 되돌린다.
- 공식 취소/불성립 경주만 있는 경우는 결손이 아니라 "완결된 제외"로 간주한다.

즉, 최신 구간 평가에서 일부 경주만 빠진 날짜를 그대로 쓰지 않는다. 최신 날짜의 운영 품질이 확인될 때만 홀드아웃 끝점으로 채택한다.

## 기간 경계 결정 규칙

### 1. 정렬 키

전체 후보 경주는 아래 키로 오름차순 정렬한다.

1. `date`
2. `meet`
3. `race_number`

평가일 경계는 `date` 기준으로만 자른다.

### 2. 최종 홀드아웃

최종 홀드아웃은 아래 절차로 고정한다.

1. 최신 완결 평가일 `D_end`를 찾는다.
2. `D_end`부터 과거로 거슬러 올라가며 완결 평가일을 누적한다.
3. 누적 평가 가능 경주 수가 최소 500경주가 되는 가장 이른 날짜를 `D_start`로 정한다.
4. 홀드아웃 구간은 `D_start <= date <= D_end`인 모든 평가 가능 경주다.
5. 어떤 날짜를 포함한 결과 경주 수가 500을 초과해도 그대로 유지한다. 500에 맞추기 위해 날짜 내부를 잘라내지 않는다.

따라서 홀드아웃 경주 수는 "최소 500"이며, 실제 수치는 날짜 경계 때문에 500보다 클 수 있다.

### 3. 연구용 `mini_val`

`mini_val`은 홀드아웃 직전의 완결 평가일을 같은 방식으로 역누적해 최소 200경주가 되도록 잡는다.

1. `mini_val` 종료일은 홀드아웃 시작일의 직전 완결 평가일이다.
2. 그 종료일부터 과거로 역누적해 최소 200경주가 되는 날짜를 `mini_val` 시작일로 정한다.
3. 날짜 내부 절단은 금지한다.

### 4. 학습 구간

학습 구간은 `mini_val` 시작일 이전의 모든 완료 경주다. 학습 내부에서 랜덤 시드 반복, 하이퍼파라미터 탐색, 특징 실험은 허용하지만 최종 홀드아웃 날짜 범위를 보면서 튜닝하면 안 된다.

## 안정성 평가 규칙

- 최종 성공 판정은 같은 홀드아웃 날짜 구간에 대해 10개 랜덤 시드 반복으로 수행한다.
- 시드마다 바뀌는 것은 모델 초기화, 샘플링, tie-break 등 내부 난수뿐이다.
- 홀드아웃 경주 목록, 날짜 경계, 제외 사유 목록은 시드와 무관하게 고정한다.
- 성공 기준은 10개 시드 결과의 최저 상위 3두 무순서 적중률이 70% 이상인 경우다.

## 운영 산출물

최종 홀드아웃을 생성할 때 아래 메타데이터를 함께 남긴다.

- 생성 시각
- `D_start`, `D_end`
- 포함 경주 수
- 포함 평가일 수
- 제외 경주 수와 사유별 건수
- 데이터 결손 때문에 탈락한 최신 날짜 목록
- 경주별 `entry_finalized_at`, `operational_cutoff_at`, `timestamp_confidence`
- 사용한 누수 검사 버전과 피처 스키마 버전

권장 저장 경로는 `.ralph/outputs/holdout_split_manifest.json`이다.

## 매니페스트 스키마 기준선

홀드아웃 경주 선정 결과는 문서만이 아니라 코드 스키마로도 고정해야 한다. 현재 기준선은 [holdout_split_manifest_schema.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/holdout_split_manifest_schema.py) 이다.
동일 원천 데이터와 동일 규칙으로 manifest를 다시 생성했을 때 byte-level 내용이 동일한지는 [holdout_split.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/autoresearch/holdout_split.py)의 `check_manifest_reproducibility(...)` 로 검증한다.

top-level 필수 블록은 다음과 같다.

- `format_version`
- `parameters`: `dataset`, `selection_method`, `minimum_race_count`, `boundary_unit`, `require_complete_race_dates`, `allow_intra_day_cut`, `active_runner_rule`, `target_label`, `leakage_policy_version`
- `metadata.period`: `start_date`, `end_date`, `latest_complete_race_date`, `race_count`, `race_date_count`
- `metadata.seed`: `selection_seed`, `selection_seed_invariant`, `evaluation_seeds`
- `metadata.data_snapshot`: `data_as_of`, `results_as_of`, `entry_snapshot_as_of`
- `metadata.rule`: `rule_version`, `rule_path`, `entry_finalization_rule_version`
- `included_race_ids`
- `excluded_race_dates`
- `exclusion_reason_counts`

여기서 `metadata.seed.selection_seed_invariant=true` 는 "홀드아웃 경주 목록이 랜덤 시드와 무관하게 고정된다"는 본 문서의 안정성 평가 규칙을 기계적으로 강제하기 위한 필드다.
현재 `active_runner_rule` 값은 `candidate_filter_minimum_info_fallback_v1` 이다.

## 현재 저장소 상태에 대한 적용 메모

현재 체크인된 스냅샷을 확인하면 다음과 같다.

- `packages/scripts/autoresearch/snapshots/mini_val.json`: 200경주, `2025-09-05` ~ `2025-10-19`
- `packages/scripts/autoresearch/snapshots/holdout.json`: 500경주, `2025-10-19` ~ `2026-02-14`

즉 현재 스냅샷은 `2025-10-19`가 `mini_val`과 `holdout` 양쪽에 걸친 race-level 절단 상태다. 이 문서의 v1 규칙에서는 이를 허용하지 않는다. 이후 홀드아웃 재생성 로직은 반드시 평가일 단위로 경계를 맞춰야 한다.

## 구현 기준점

이 규칙은 아래 현재 구현을 기준으로 정의했다.

- 결과 확정 경주 조회: [packages/scripts/shared/db_client.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/db_client.py)
- 평가 데이터 로딩: [packages/scripts/evaluation/data_loading.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/evaluation/data_loading.py)
- 누수 검사: [packages/scripts/evaluation/leakage_checks.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/evaluation/leakage_checks.py)
- 기존 스냅샷 생성 로직: [packages/scripts/autoresearch/prepare.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/autoresearch/prepare.py)
