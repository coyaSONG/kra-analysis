# 홀드아웃 스냅샷 필터링 절차 및 저장 포맷 v1

## 목적

이 문서는 최근 기간 홀드아웃/`mini_val` 데이터셋 생성 시 각 경주에 `출전표 확정 시점`을 연결하고, 그 시점 이전에 허용되는 입력만 남기기 위한 실행 절차와 저장 포맷을 정의한다.

핵심 목표는 다음 두 가지다.

- 경주별 snapshot이 언제 잠겼는지 재현 가능하게 남긴다.
- 사후 결과 필드나 cutoff 이후 snapshot을 최종 평가 입력에서 배제한다.

세부 시각 산출 규칙은 [docs/holdout-entry-finalization-rule.md](/Users/chsong/Developer/Personal/kra-analysis/docs/holdout-entry-finalization-rule.md)를, 허용/금지 필드 정책은 [docs/prerace-data-whitelist-blacklist-policy.md](/Users/chsong/Developer/Personal/kra-analysis/docs/prerace-data-whitelist-blacklist-policy.md)를 따른다.

## 적용 절차

1. `RaceSnapshot` row를 읽는다.
   - 입력 소스: `races.basic_data`, `races.collected_at`, `races.updated_at`
2. 경주별 시각을 산출한다.
   - `scheduled_start_at = race_date + race_plan.sch_st_time`
   - `operational_cutoff_at = scheduled_start_at - 10분`
   - `snapshot_ready_at`은 `basic_data.collected_at`, 없으면 `races.collected_at`, 그래도 없으면 `races.updated_at`을 쓴다.
   - `entry_finalized_at`은 현재 저장소 기준으로 `snapshot_ready_at` 또는 schedule 기반 fallback이다.
3. hard-required source 존재 여부를 검증한다.
   - `race_info`, `race_plan`, `track`, `cancelled_horses`
   - `cancelled_horses`는 빈 배열도 정상으로 인정한다.
4. strict 포함 가능 여부를 결정한다.
   - hard-required source가 빠지면 `partial_snapshot`
   - `entry_finalized_at > operational_cutoff_at`이면 `late_snapshot_unusable`
   - 위 두 경우는 strict dataset에서 제외한다.
5. payload를 필터링한다.
   - top-level은 prerace schema의 허용 블록만 남긴다.
   - raw horse item에서는 `ord`, `ordBigo`, `rcTime`, `diffUnit`, `rankRise`, sectional `*Ord/*AccTime/*GTime` 같은 사후 필드를 제거한다.
   - `rank`는 결과 순위가 아니라 등급 문자열이므로 `class_rank`로 rename해서 보존한다.
6. 평가용 race payload에 `snapshot_meta`를 붙인다.
   - 모델/평가 코드가 race payload 하나만 읽어도 timing audit 정보를 확인할 수 있게 한다.
7. dataset-level sidecar manifest를 함께 저장한다.
   - 경주별 timing 상태, strict 포함 여부, replay 상태 분포를 한 파일에 고정한다.

## 경주별 저장 포맷

`packages/scripts/autoresearch/snapshots/{mode}.json` 의 각 원소는 기존 race array 포맷을 유지하되 `snapshot_meta`를 추가한다.

```json
{
  "race_id": "20250101_1_1",
  "race_date": "20250101",
  "meet": "서울",
  "race_info": {},
  "horses": [],
  "snapshot_meta": {
    "format_version": "holdout-snapshot-v1",
    "scheduled_start_at": "2025-01-01T11:00:00+09:00",
    "operational_cutoff_at": "2025-01-01T10:50:00+09:00",
    "snapshot_ready_at": "2025-01-01T10:35:00+09:00",
    "entry_finalized_at": "2025-01-01T10:35:00+09:00",
    "timestamp_source": "snapshot_collected_at",
    "timestamp_confidence": "medium",
    "replay_status": "strict",
    "include_in_strict_dataset": true,
    "hard_required_sources_present": true,
    "removed_post_race_fields": [
      "horses[0].ordBigo",
      "horses[0].sjG1fOrd"
    ],
    "removed_post_race_field_count": 2
  }
}
```

## 데이터셋 sidecar 포맷

`packages/scripts/autoresearch/snapshots/{mode}_manifest.json` 은 dataset-level audit 용도다.

```json
{
  "format_version": "holdout-dataset-manifest-v1",
  "dataset": "holdout",
  "created_at": "2026-04-10T12:00:00",
  "race_count": 500,
  "strict_race_count": 487,
  "filter_policy": {
    "source_filter_basis": "entry_finalized_at",
    "required_pre_cutoff": true,
    "hard_required_sources": ["API214_1", "API72_2", "API189_1", "API9_1"],
    "payload_shape": "legacy-race-array+snapshot_meta"
  },
  "replay_status_counts": {
    "strict": 487,
    "degraded": 8,
    "partial_snapshot": 3,
    "late_snapshot_unusable": 2
  },
  "races": []
}
```

## 운영 해석 규칙

- 최종 성공 판정용 strict holdout은 `include_in_strict_dataset = true` 인 경주만 집계한다.
- `degraded`는 참고용 회귀 감시에는 남길 수 있지만, strict 인증 지표와 섞지 않는다.
- `partial_snapshot`과 `late_snapshot_unusable`은 제외 사유 로그로 남기고, 데이터/수집 체계 개선의 backlog로 보낸다.

## 감사 로그와 점검 규칙

홀드아웃 생성 시 `*_manifest.json` 에는 각 경주 timing 메타데이터 외에 `audit` 블록이 함께 저장된다. 이 블록은 "모든 홀드아웃 경주가 출전표 확정 시점 입력만 사용했는지"를 사후 검증하기 위한 최소 로그, 자동 점검 규칙, 위반 코드 목록을 고정한다.

### 필수 감사 로그

각 경주는 최소한 아래 필드를 남겨야 한다.

- `race_id`
- `source_filter_basis`
- `timestamp_source`
- `timestamp_confidence`
- `replay_status`
- `include_in_strict_dataset`
- `hard_required_sources_present`
- `late_reissue_after_cutoff`
- `cutoff_unbounded`

아래 필드는 조건부 필수다.

- `include_in_strict_dataset=true` 면 `entry_finalized_at`
- `cutoff_unbounded=false` 면 `scheduled_start_at`, `operational_cutoff_at`
- `timestamp_source=snapshot_collected_at` 면 `snapshot_ready_at`

### 자동 점검 규칙

- `basis_locked_to_entry_finalized_at`: 모든 경주의 `source_filter_basis` 는 반드시 `entry_finalized_at` 이어야 한다.
- `included_races_require_prerace_inputs`: `include_in_strict_dataset=true` 인 경주는 `hard_required_sources_present=true` 이고 `entry_finalized_at` 이 있어야 한다.
- `included_races_must_be_pre_cutoff`: `operational_cutoff_at` 이 있는 경주는 `entry_finalized_at <= operational_cutoff_at` 이어야 한다.
- `excluded_statuses_cannot_be_included`: `partial_snapshot`, `late_snapshot_unusable`, `missing_timestamp` 는 strict 집계에 포함되면 안 된다.
- `timestamp_source_and_confidence_must_match`: `snapshot_collected_at -> medium`, `derived_from_schedule -> low`, `fallback_collected_only -> low` 조합만 허용한다.
- `snapshot_ready_log_required_for_snapshot_source`: `timestamp_source=snapshot_collected_at` 면 `snapshot_ready_at` 이 있어야 하고 `entry_finalized_at` 과 같아야 한다.

### 위반 탐지 기준

- `missing_log_field`: 필수 감사 로그 누락 또는 빈 값
- `unexpected_source_filter_basis`: 필터 기준이 `entry_finalized_at` 이 아님
- `strict_without_required_sources`: strict 집계 포함 경주에 hard-required source 누락
- `missing_entry_finalized_at`: strict 집계 포함 경주에 `entry_finalized_at` 누락
- `missing_operational_cutoff_at`: cutoff가 bounded 인데 cutoff 로그 누락
- `missing_scheduled_start_at`: cutoff가 bounded 인데 예정 출발 시각 로그 누락
- `post_cutoff_snapshot`: `entry_finalized_at > operational_cutoff_at`
- `excluded_status_marked_included`: 제외 대상 `replay_status` 가 strict 집계에 포함됨
- `timestamp_confidence_mismatch`: `timestamp_source` 와 `timestamp_confidence` 조합 불일치
- `missing_snapshot_ready_at`: snapshot 기반 시각인데 `snapshot_ready_at` 로그 없음
- `entry_snapshot_timestamp_mismatch`: snapshot 기반인데 `entry_finalized_at != snapshot_ready_at`

## 감사 블록 예시

```json
{
  "audit": {
    "passed": true,
    "checked_races": 500,
    "required_log_fields": [
      "race_id",
      "source_filter_basis",
      "timestamp_source",
      "timestamp_confidence",
      "replay_status",
      "include_in_strict_dataset",
      "hard_required_sources_present",
      "late_reissue_after_cutoff",
      "cutoff_unbounded"
    ],
    "inspection_rules": [
      {
        "rule_id": "basis_locked_to_entry_finalized_at",
        "description": "모든 홀드아웃 경주는 source_filter_basis가 entry_finalized_at 이어야 한다."
      }
    ],
    "violation_catalog": {
      "post_cutoff_snapshot": "entry_finalized_at 이 operational_cutoff_at 이후임"
    },
    "violation_counts": {},
    "violations": []
  }
}
```
