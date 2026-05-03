# 홀드아웃 출전표 확정 시점 산출 규칙 v1

## 목적

이 문서는 최근 기간 홀드아웃에 포함되는 각 KRA 경주별로 "출전표 확정 시점"을 어떻게 산출할지 정의한다. 여기서 목표는 다음 3가지를 동시에 만족하는 것이다.

- 홀드아웃 재생 시 실제 운영과 같은 시점 제약을 강제한다.
- 정정/재발행이 있는 경주도 어떤 스냅샷을 써야 하는지 일관되게 결정한다.
- 현재 저장소가 복원 가능한 시각과 아직 복원 불가능한 시각을 구분해, 실전 운영과 최종 인증의 기준을 분리한다.

이 규칙은 홀드아웃 생성, 재학습 직전 회귀 검증, 실전 예측 잠금 시각 산출에 공통 적용한다.

## 용어

- `scheduled_start_at`: `race_date`와 `race_plan.sch_st_time`을 결합한 예정 출발 시각. 타임존은 항상 `Asia/Seoul`이다.
- `operational_cutoff_at`: 실제 운영에서 예측 입력을 더 이상 바꾸지 않는 잠금 시각. 기본식은 `scheduled_start_at - 10분`이다.
- `snapshot_ready_at`: 해당 경주의 예측 입력 스냅샷이 완전히 준비된 시각. 선택된 리비전에서 필요한 사전 소스가 모두 모인 가장 늦은 시각이다.
- `entry_finalized_at`: 홀드아웃 재생과 운영 로그에 함께 기록하는 "이 스냅샷을 예측에 사용해도 된다"고 판단한 기준 시각.
- `revision`: 같은 경주에 대해 다시 수집된 출전표/주로/취소 정보 묶음. 정정, 재발행, 재수집을 모두 포함한다.
- `strict replay`: 리비전 시각이 보존돼 있어 `entry_finalized_at`을 높은 신뢰도로 복원할 수 있는 상태.
- `degraded replay`: 명시적 리비전 시각이 없어 대체 규칙으로 시각을 추정한 상태.

## 기준 시각

### 1. 예정 출발 시각

각 경주는 아래 순서로 `scheduled_start_at`을 산출한다.

1. `basic_data.race_plan.sch_st_time`
2. 같은 값이 경주 raw item에 중복 저장돼 있으면 그 값
3. 같은 날짜, 같은 `meet` 내 인접 경주의 `sch_st_time`으로 보간한 값
4. 학습 구간에서 계산한 `(meet, race_number)` 기준 역사적 중앙값 시각

`sch_st_time`은 `HHMM` 정수/문자열로 해석한다. 세 자리면 앞에 `0`을 붙이고, 네 자리가 아니면 누락으로 본다.

### 2. 운영 잠금 시각

기본 운영 잠금 시각은 다음과 같다.

`operational_cutoff_at = scheduled_start_at - 10분`

10분 버퍼를 두는 이유는 다음과 같다.

- 모든 KRA 경주에 대해 예측을 반드시 생성해야 하므로, 수집 완료 직후 검증/직렬화/저장 시간이 필요하다.
- 현재 저장소의 시각 정밀도는 대부분 분 단위이며, `sch_st_time` 역시 분 단위라 추가 완충이 필요하다.
- 출발 직전의 변동을 추격하기보다, 운영 재현성과 자동화 안정성을 우선한다.

### 3. 출전표 확정 시각

`entry_finalized_at`은 "선택된 예측 입력 리비전이 실제로 사용 가능해진 시각"으로 정의한다. 즉, 선택된 리비전의 `snapshot_ready_at`이며, 반드시 `operational_cutoff_at` 이하여야 한다.

공식으로 쓰면 다음과 같다.

`snapshot_ready_at = max(ts(API214_1), ts(API72_2), ts(API189_1), ts(API9_1))`

여기서 `ts(source)`는 선택된 리비전에서 해당 hard-required source가 준비된 시각이다. soft-required source(API8_2, API12_1, API19_1, API11_1, API14_1, API329)는 성능 향상용이므로 `snapshot_ready_at` 계산에는 포함하지 않는다.

최종 산출은 다음과 같다.

- `snapshot_ready_at <= operational_cutoff_at`이면 `entry_finalized_at = snapshot_ready_at`
- `snapshot_ready_at > operational_cutoff_at`이면 해당 리비전은 운영 불가다. 직전 리비전 중 조건을 만족하는 것을 다시 찾는다.
- 조건을 만족하는 리비전이 하나도 없으면 그 경주는 `late_snapshot_unusable`로 기록한다.

## 우선순위 규칙

각 경주의 `entry_finalized_at` 산출에는 아래 우선순위를 적용한다.

1. 리비전별 원천 시각이 모두 남아 있는 경우
   - 각 hard-required source의 `published_at` 또는 `collected_at`을 사용한다.
   - `snapshot_ready_at`은 그 최대값이다.
   - 신뢰도는 `high`다.
2. 리비전별 원천 시각은 없지만, 조립된 스냅샷의 `basic_data.collected_at`이 있는 경우
   - `snapshot_ready_at = basic_data.collected_at`
   - 단, `basic_data`가 hard-required source를 모두 포함해야 한다.
   - 신뢰도는 `medium`이다.
3. 명시적 수집 시각이 없고 `scheduled_start_at`만 복원 가능한 경우
   - `entry_finalized_at = operational_cutoff_at`
   - 이는 "이 시각 이전 정보만 사용했어야 한다"는 보수적 프록시이며, 실제 준비 완료 시각이 아니다.
   - 신뢰도는 `low`다.
4. `scheduled_start_at`까지 누락된 경우
   - 인접 경주/역사적 중앙값으로 `scheduled_start_at`을 먼저 복원한다.
   - 그래도 복원 실패하면 `entry_finalized_at = basic_data.collected_at`만 기록하고 `cutoff_unbounded = true`로 남긴다.
   - 이 상태는 운영 참고용으로만 사용하고 strict replay 인증에서는 별도 집계한다.

같은 경주에 대해 여러 후보가 있으면 항상 더 높은 우선순위의 시각을 선택한다. 같은 우선순위 안에서는 `operational_cutoff_at` 이하인 가장 최신 리비전을 선택한다.

## 정정/재발행 예외 처리

### 1. 잠금 시각 이전 정정

- `operational_cutoff_at` 이전에 여러 번 정정/재발행된 경우, 가장 늦은 pre-cutoff 리비전을 사용한다.
- 예측과 홀드아웃 재생 모두 동일 규칙을 쓴다.

### 2. 잠금 시각 이후 정정

- 잠금 시각 이후 정정이 있었더라도, 잠금 시각 이전 리비전이 보존돼 있으면 그 리비전을 사용한다.
- 이 경우 `late_reissue_after_cutoff = true`를 기록한다.
- 잠금 이후 정정본은 결과 해석용 참고 자료일 뿐, 예측 입력으로 사용하지 않는다.

### 3. 잠금 시각 이후 정정만 남고 이전 리비전이 없는 경우

- 운영 당시에는 예측이 생성됐더라도, 사후 홀드아웃에서는 그 경주를 strict replay로 재현할 수 없다.
- 이 경우 `replay_status = unrecoverable_post_cutoff_reissue`로 기록한다.
- strict replay 지표에서는 별도 탈락 목록으로 집계하고, degraded replay 참고 지표에서는 최신 저장본으로 재생할 수 있다.

## 시각 누락 대체 규칙

### 1. `sch_st_time` 누락

아래 순서로 대체한다.

1. 같은 날짜, 같은 `meet`에서 바로 앞/뒤 경주의 `sch_st_time`이 모두 있으면 중간값을 사용한다.
2. 한쪽만 있으면, 같은 날짜·같은 `meet`의 중앙 race interval을 더하거나 빼서 복원한다.
3. 그래도 안 되면 학습 구간의 `(meet, race_number)` 역사적 중앙값 시각을 사용한다.
4. 이것도 불가능하면 `scheduled_start_at = null`, `cutoff_unbounded = true`로 남기고 `basic_data.collected_at`만 기록한다.

### 2. `basic_data.collected_at` 누락

- 리비전별 원천 시각이 있으면 그 최대값으로 대체한다.
- 둘 다 없으면 `entry_finalized_at = operational_cutoff_at` 프록시를 쓴다.
- 이 경우 `timestamp_source = derived_from_schedule`로 기록한다.

### 3. hard-required source 일부 누락

- `API214_1`, `API72_2`, `API189_1`, `API9_1` 중 하나라도 빠지면 해당 리비전은 snapshot-ready 리비전으로 인정하지 않는다.
- 단, `API9_1`은 "빈 배열 응답"도 정상 수집으로 간주한다.
- hard-required source가 빠진 채 저장된 `basic_data`만 있으면 `partial_snapshot`으로 기록하고 strict replay 대상에서 제외한다.

## 홀드아웃 매니페스트 필수 필드

경주별 매니페스트에 아래 필드를 남겨야 한다.

- `race_id`
- `scheduled_start_at`
- `operational_cutoff_at`
- `entry_finalized_at`
- `timestamp_source`
- `timestamp_confidence`
- `revision_id`
- `late_reissue_after_cutoff`
- `cutoff_unbounded`
- `replay_status`

권장 상태값은 다음과 같다.

- `timestamp_source`: `source_revision`, `snapshot_collected_at`, `derived_from_schedule`, `fallback_collected_only`
- `timestamp_confidence`: `high`, `medium`, `low`
- `replay_status`: `strict`, `degraded`, `partial_snapshot`, `unrecoverable_post_cutoff_reissue`

## 현재 저장소 기준 적용 메모

현재 구현에서 바로 활용 가능한 필드는 다음뿐이다.

- `basic_data.collected_at`
- `basic_data.race_plan.sch_st_time`
- `races.collected_at`
- `races.updated_at`

반면, 리비전별 원천 시각과 정정 이력은 아직 별도 보존되지 않는다. 따라서 현재 상태에서 대부분의 과거 경주는 `medium` 또는 `low` 신뢰도의 degraded replay가 된다. 최종 70% 인증용 strict replay를 안정적으로 만들려면, 최소한 hard-required source별 `collected_at`과 리비전 이력을 저장해야 한다.

## 구현 기준점

- 공통 사전 스키마: [packages/scripts/shared/prerace_source_schema.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/shared/prerace_source_schema.py)
- 현재 홀드아웃 규칙: [docs/recent-holdout-split-rule.md](/Users/chsong/Developer/Personal/kra-analysis/docs/recent-holdout-split-rule.md)
- 현재 스냅샷 생성 로직: [packages/scripts/autoresearch/prepare.py](/Users/chsong/Developer/Personal/kra-analysis/packages/scripts/autoresearch/prepare.py)
- 현재 경주 ORM 타임스탬프: [apps/api/models/database_models.py](/Users/chsong/Developer/Personal/kra-analysis/apps/api/models/database_models.py)
