# Offline Evaluation Common Snapshot And Schema Refactor

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document follows [.agent/PLANS.md](/Users/chsong/Developer/Personal/kra-analysis/.agent/PLANS.md) and must be maintained in accordance with that file.

## Purpose / Big Picture

After this change, the offline evaluation path will no longer build race payloads through local one-off helpers inside each script. Instead it will reuse a common shared builder for prerace payload/schema generation and a common snapshot lookup helper for `entry_finalized_at` anchored reloads. A contributor can verify the change by running the shared/offline evaluation pytest bundle and confirming that `evaluation/data_loading.py` and `autoresearch/offline_evaluation_dataset_job.py` both still produce valid schema-bearing race payloads.

## Progress

- [x] 2026-04-11 11:54Z `offline_evaluation_dataset_job.py`, `evaluation/data_loading.py`, `shared/read_contract.py`의 중복 책임을 조사했다.
- [x] 2026-04-11 12:05Z 공통 snapshot lookup helper는 `shared.read_contract`에, 공통 prerace payload builder는 신규 `shared.prerace_prediction_payload`에 두기로 결정했다.
- [x] 2026-04-11 12:18Z `RaceSourceLookup.from_snapshot()`와 `shared.prerace_prediction_payload.build_prerace_race_payload_from_enriched()`를 추가하고 오프라인/평가 로더 호출부를 공통 helper 기반으로 리팩터링했다.
- [x] 2026-04-11 12:21Z `uv run pytest -q packages/scripts/tests/test_shared_read_contract.py packages/scripts/tests/test_prerace_prediction_payload.py packages/scripts/evaluation/tests/test_data_loading.py packages/scripts/autoresearch/tests/test_offline_evaluation_dataset_job.py` 실행에서 22개 테스트 통과를 확인했다.
- [x] 2026-04-11 13:12Z `evaluation/predict_only_test.py`도 `RaceSnapshot` 기반 lookup과 `build_prerace_race_payload_from_enriched()`를 재사용하도록 연결했고, 관련 pytest 23개 통과를 확인했다.

## Surprises & Discoveries

- Observation: 오프라인 평가용 strict payload 조립 로직이 `evaluation/data_loading.py`와 `autoresearch/offline_evaluation_dataset_job.py`에 거의 같은 형태로 중복돼 있었다.
  Evidence: 두 파일 모두 `convert_basic_data_to_enriched_format` 이후 말 목록 추출, 후보 필터, `compute_race_features`, `filter_prerace_payload`, `validate_alternative_ranking_race_payload` 순서를 각자 직접 구현하고 있었다.

## Decision Log

- Decision: snapshot 기준 재조회 계약은 `RaceSourceLookup.from_snapshot()` classmethod로 노출한다.
  Rationale: 오프라인 평가가 공통 snapshot DTO만 알면 lookup anchor를 만들 수 있어야 하며, lookup 규약을 DTO 계층에서 발견 가능하게 두는 편이 안전하다.
  Date/Author: 2026-04-11 / Codex

- Decision: prerace payload 조립은 shared builder 한 곳에서 post-race field stripping, candidate filtering, schema validation까지 끝낸다.
  Rationale: 스크립트별로 허용/제거 규칙을 다르게 구현하면 운영 입력 계약이 쉽게 갈라지므로, schema 직전 payload를 만드는 책임을 한 모듈에 모은다.
  Date/Author: 2026-04-11 / Codex

## Outcomes & Retrospective

오프라인 평가 파이프라인의 snapshot lookup anchor와 prerace schema payload 조립을 shared 계층으로 옮겼다. `offline_evaluation_dataset_job.py`, `evaluation/data_loading.py`, `evaluation/predict_only_test.py`는 더 이상 각자 post-race field stripping, candidate filtering, schema validation 순서를 재구현하지 않는다. 온라인 추론 테스트 경로도 동일한 snapshot/schema 계약을 재사용한다.

## Context and Orientation

`packages/scripts/autoresearch/offline_evaluation_dataset_job.py`는 오프라인 평가용 snapshot 팩을 만드는 스크립트다. 여기서 각 `RaceSnapshot`을 `entry_finalized_at` 시각에 맞춰 다시 조회하고 strict race payload로 바꾼다. `packages/scripts/evaluation/data_loading.py`는 평가 실행 시 DB row를 같은 입력 스키마로 바꾸는 로더다. 두 경로 모두 `shared.prediction_input_schema`와 `shared.snapshot_query_schema` 규약을 따라야 하지만, 현재는 중간 payload 조립 로직을 각 파일이 직접 들고 있다.

이번 변경에서 “공통 snapshot 모듈”은 `packages/scripts/shared/read_contract.py`를 뜻하고, “공통 schema 모듈”은 `packages/scripts/shared/prediction_input_schema.py` 및 이를 호출하는 shared builder를 뜻한다.

## Plan of Work

먼저 `packages/scripts/shared/read_contract.py`에 `RaceSourceLookup.from_snapshot()`를 추가해 `RaceSnapshot`만으로 `entry_finalized_at` anchored lookup을 만들 수 있게 한다. 이 구현은 `shared.entry_snapshot_metadata.derive_or_restore_entry_snapshot_metadata()`를 직접 사용해 raw/basic_data에 저장된 snapshot timing 규약을 재사용한다.

그 다음 신규 `packages/scripts/shared/prerace_prediction_payload.py`를 추가한다. 이 모듈은 post-race leakage field 제거, `rank` → `class_rank` canonicalization, `select_prediction_candidates()` 적용, optional horse preprocessor, `compute_race_features()`, `filter_prerace_payload()`, `validate_alternative_ranking_race_payload()`를 한 번에 수행하는 공통 builder를 제공한다.

마지막으로 `packages/scripts/evaluation/data_loading.py`와 `packages/scripts/autoresearch/offline_evaluation_dataset_job.py`가 각자 말 리스트를 조립하지 말고 shared builder만 호출하도록 바꾼다. 오프라인 쪽은 timing audit를 위해 removed field path만 계속 수집한다.

## Concrete Steps

작업 디렉터리: `/Users/chsong/Developer/Personal/kra-analysis`

1. `shared.read_contract.py`에 snapshot lookup helper 추가.
2. `shared.prerace_prediction_payload.py` 신규 작성.
3. `evaluation/data_loading.py`와 `autoresearch/offline_evaluation_dataset_job.py`를 shared helper 사용으로 전환.
4. `packages/scripts/tests/test_shared_read_contract.py`, `packages/scripts/tests/test_prerace_prediction_payload.py`, `packages/scripts/evaluation/tests/test_data_loading.py`, `packages/scripts/autoresearch/tests/test_offline_evaluation_dataset_job.py`에 회귀 테스트 추가.
5. `uv run pytest -q packages/scripts/tests/test_shared_read_contract.py packages/scripts/tests/test_prerace_prediction_payload.py packages/scripts/evaluation/tests/test_data_loading.py packages/scripts/autoresearch/tests/test_offline_evaluation_dataset_job.py` 실행.

실제 관찰 결과:

    $ uv run pytest -q packages/scripts/tests/test_shared_read_contract.py packages/scripts/tests/test_prerace_prediction_payload.py packages/scripts/evaluation/tests/test_data_loading.py packages/scripts/autoresearch/tests/test_offline_evaluation_dataset_job.py
    ......................                                                   [100%]
    22 passed in 0.46s

## Validation and Acceptance

수용 기준은 다음과 같다. `RaceSourceLookup.from_snapshot()`는 stored snapshot timing에서 `entry_finalized_at`을 읽어 canonical lookup을 생성해야 한다. `evaluation/data_loading.py`와 `offline_evaluation_dataset_job.py`는 shared builder 결과로 동일한 schema-bearing prerace payload를 생성해야 한다. 테스트 실행 시 새 helper가 호출되어도 기존 candidate filter, input schema, snapshot lookup anchor가 유지되어야 한다.

## Idempotence and Recovery

이번 변경은 additive refactor다. 테스트는 반복 실행 가능하다. 새 shared helper 도입 후 기존 개별 helper는 thin wrapper 또는 제거로 정리하되, 외부 호환이 필요한 이름은 유지한다. 실패 시 변경 파일만 되돌리면 되며 데이터 파일 포맷은 바꾸지 않는다.

## Artifacts and Notes

핵심 변경 대상:

- `packages/scripts/shared/read_contract.py`
- `packages/scripts/shared/prerace_prediction_payload.py`
- `packages/scripts/evaluation/data_loading.py`
- `packages/scripts/autoresearch/offline_evaluation_dataset_job.py`

Revision note: 2026-04-11에 Sub-AC 1020302 구현용 ExecPlan을 신규 작성했다.

## Interfaces and Dependencies

최종 상태에서 다음 인터페이스가 존재해야 한다.

- `shared.read_contract.RaceSourceLookup.from_snapshot(snapshot: RaceSnapshot) -> RaceSourceLookup`
- `shared.prerace_prediction_payload.strip_forbidden_fields(...) -> dict[str, Any]`
- `shared.prerace_prediction_payload.build_prerace_race_payload_from_enriched(...) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]`

`evaluation/data_loading.py`와 `autoresearch/offline_evaluation_dataset_job.py`는 race payload 조립을 위해 위 builder만 호출해야 한다.
