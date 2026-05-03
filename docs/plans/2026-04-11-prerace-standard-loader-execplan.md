# Prerace Intermediate Snapshot To Standard Schema Loader

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document follows [.agent/PLANS.md](/Users/chsong/Developer/Personal/kra-analysis/.agent/PLANS.md) and must be maintained in accordance with that file.

## Purpose / Big Picture

After this change, downstream evaluation and offline snapshot builders will no longer each perform their own ad hoc `basic_data -> enriched payload -> alternative-ranking payload` conversion. Instead they will use one shared loader that validates the stored intermediate snapshot, normalizes it into the repository’s standard prerace schema, and exposes the same contract metadata everywhere. A contributor can verify the change by running the shared/evaluation/offline pytest bundle and confirming that all three paths still produce the same `input_schema`, candidate filter, and snapshot lookup anchor.

## Progress

- [x] (2026-04-10 16:01Z) 현재 `evaluation/data_loading.py`, `evaluation/predict_only_test.py`, `autoresearch/offline_evaluation_dataset_job.py`가 중간 스키마를 각자 조합하는 방식을 조사했다.
- [x] (2026-04-10 16:07Z) `packages/scripts/shared/prerace_standard_loader.py`를 추가해 lookup 해석, intermediate snapshot 검증, enriched 변환, 표준 payload 생성 결과를 `StandardizedPreracePayload` dataclass로 묶었다.
- [x] (2026-04-10 16:10Z) evaluation/offline/predict-only 경로를 새 로더만 사용하도록 리팩터링했다.
- [x] (2026-04-10 16:14Z) 새 로더 전용 테스트와 회귀 테스트를 추가하고 `UV_CACHE_DIR=.uv-cache uv run pytest -q ...`로 19개 테스트 통과를 확인했다.

## Surprises & Discoveries

- Observation: 공통 builder가 이미 존재해도 호출부마다 `basic_data` 존재 검사, `cancelled_horses` 전달, resolution audit 수집, lookup 해석을 직접 반복하고 있었다.
  Evidence: `packages/scripts/evaluation/data_loading.py`, `packages/scripts/evaluation/predict_only_test.py`, `packages/scripts/autoresearch/offline_evaluation_dataset_job.py` 모두 `load_race_basic_data` 이후 개별 후처리를 갖고 있었다.

## Decision Log

- Decision: 이번 단계의 “표준 스키마 적재 계층”은 DB/저장 스냅샷을 읽는 공통 loader dataclass와 helper 함수로 구현한다.
  Rationale: 다운스트림 계약을 맞추는 핵심은 새 포맷 하나를 더 만드는 것이 아니라, 기존 중간 스키마를 표준 payload로 올리는 절차와 부가 메타데이터를 한 API로 고정하는 것이다.
  Date/Author: 2026-04-10 / Codex

- Decision: shared loader는 `basic_data`가 없거나 intermediate 변환에 실패할 때 `ValueError`를 일관되게 발생시키고, 상위 호출부가 기존 `None`/제외 처리 규약을 유지하도록 둔다.
  Rationale: 검증 실패를 shared 계층에서 숨기면 호출부마다 실패 조건이 다시 갈라지므로, 실패 원인은 중앙에서 만들고 처리 정책만 상위에서 결정하는 편이 계약이 선명하다.
  Date/Author: 2026-04-10 / Codex

## Outcomes & Retrospective

중간 prerace 스키마를 표준 alternative-ranking 입력 스키마로 올리는 공통 loader를 추가했고, evaluation/offline/predict-only 세 경로가 모두 이를 소비하도록 정리했다. 결과적으로 호출부는 더 이상 `convert_snapshot_to_enriched_format()`와 `build_prerace_race_payload_from_enriched()`를 직접 조합하지 않고, `StandardizedPreracePayload`에서 표준 payload와 메타데이터만 읽는다. 이 단계에서는 holdout split처럼 strict 포함 여부만 판단하는 경로는 건드리지 않았다. 목적이 “다운스트림 동일 계약”이었기 때문에 실제 표준 payload를 만드는 세 경로를 우선 수렴시키는 것이 맞았다.

## Context and Orientation

`packages/scripts/shared/data_adapter.py`는 저장된 `basic_data`를 평가 스크립트가 소비하는 enriched payload로 바꾸는 어댑터다. `packages/scripts/shared/prerace_prediction_payload.py`는 enriched payload를 alternative-ranking 표준 입력 payload로 바꾸는 builder다. 하지만 현재 `packages/scripts/evaluation/data_loading.py`, `packages/scripts/evaluation/predict_only_test.py`, `packages/scripts/autoresearch/offline_evaluation_dataset_job.py`는 lookup 해석과 intermediate validation을 각자 하고 있다. 이번 작업의 목표는 이 세 경로 앞단에 shared loader를 두어 downstream이 동일한 데이터 계약만 소비하게 만드는 것이다.

여기서 “중간 스키마”는 DB `basic_data`와 그것을 `convert_snapshot_to_enriched_format()`으로 바꾼 enriched payload를 뜻한다. “표준 스키마”는 `build_prerace_race_payload_from_enriched()`가 생산하는 alternative-ranking 입력 payload와 그 검증 리포트(`input_schema`, candidate filter, field policy)를 뜻한다.

## Plan of Work

먼저 `packages/scripts/shared/` 아래에 새 loader 모듈을 만든다. 이 모듈은 `RaceSnapshot` 또는 lookup 정보를 가진 mapping을 받아 canonical lookup을 해석하고, query port를 통해 `basic_data`를 재조회하며, `convert_snapshot_to_enriched_format()`과 `build_prerace_race_payload_from_enriched()`를 연쇄 호출해 표준 payload를 만든다. 결과는 `standard_payload`, `candidate_filter`, `field_policy`, `removed_post_race_paths`, `entry_resolution_audit`, `lookup`, `basic_data`, `enriched_data`를 포함하는 dataclass로 반환한다.

그 다음 `packages/scripts/evaluation/data_loading.py`와 `packages/scripts/evaluation/predict_only_test.py`가 이 shared loader만 사용하도록 바꾼다. 각 파일은 더 이상 직접 `convert_basic_data_to_enriched_format()`이나 shared builder를 호출하지 않고, loader 반환값에서 표준 payload와 메타데이터만 꺼낸다.

마지막으로 `packages/scripts/autoresearch/offline_evaluation_dataset_job.py`에서도 `select_allowed_basic_data()` 이후 새 builder를 사용하도록 바꾼다. timing metadata는 loader dataclass에서 `entry_resolution_audit`, `removed_post_race_paths`, `candidate_filter`, `field_policy`를 읽어 채운다.

## Concrete Steps

작업 디렉터리: `/Users/chsong/Developer/Personal/kra-analysis`

1. `packages/scripts/shared/prerace_standard_loader.py`를 추가한다.
2. `packages/scripts/evaluation/data_loading.py`, `packages/scripts/evaluation/predict_only_test.py`, `packages/scripts/autoresearch/offline_evaluation_dataset_job.py`를 새 loader 사용으로 전환한다.
3. `packages/scripts/tests/test_prerace_standard_loader.py`를 추가하고 기존 evaluation/offline/predict-only 테스트를 갱신한다.
4. 다음 명령을 실행한다.

    uv run pytest -q packages/scripts/tests/test_prerace_standard_loader.py packages/scripts/evaluation/tests/test_data_loading.py packages/scripts/evaluation/tests/test_predict_only_test.py packages/scripts/autoresearch/tests/test_offline_evaluation_dataset_job.py packages/scripts/tests/test_offline_operational_contracts.py

## Validation and Acceptance

수용 기준은 다음과 같다. evaluation, offline snapshot, predict-only 세 경로 모두 shared loader 반환값을 통해 같은 `input_schema`와 candidate filter를 가져야 한다. `RaceSnapshot` 기반 경로와 mapping 기반 경로 모두 canonical lookup(`entry_snapshot_at`)을 유지해야 한다. intermediate snapshot이 비어 있거나 변환에 실패하면 loader가 명시적 오류를 내고, 상위 호출부는 이를 기존 방식대로 `None` 또는 제외 처리로 다뤄야 한다.

## Idempotence and Recovery

이번 변경은 additive refactor다. 새 loader는 기존 `data_adapter`와 `prerace_prediction_payload`를 조합하므로 저장 포맷을 바꾸지 않는다. 실패 시 새 모듈과 호출부 변경만 되돌리면 되며, 테스트는 반복 실행 가능하다.

## Artifacts and Notes

검증 명령과 관찰 결과:

    $ UV_CACHE_DIR=.uv-cache uv run pytest -q packages/scripts/tests/test_prerace_standard_loader.py packages/scripts/evaluation/tests/test_data_loading.py packages/scripts/evaluation/tests/test_predict_only_test.py packages/scripts/autoresearch/tests/test_offline_evaluation_dataset_job.py packages/scripts/tests/test_offline_operational_contracts.py
    ...................
    19 passed in 0.54s

## Interfaces and Dependencies

최종 상태에서 다음 인터페이스가 존재해야 한다.

- `shared.prerace_standard_loader.StandardizedPreracePayload`
- `shared.prerace_standard_loader.resolve_race_record_reference(race_record) -> tuple[dict[str, Any], RaceSourceLookup]`
- `shared.prerace_standard_loader.build_standardized_prerace_payload(...) -> StandardizedPreracePayload`
- `shared.prerace_standard_loader.load_standardized_prerace_payload(...) -> StandardizedPreracePayload`

`packages/scripts/evaluation/data_loading.py`, `packages/scripts/evaluation/predict_only_test.py`, `packages/scripts/autoresearch/offline_evaluation_dataset_job.py`는 표준 payload 조립을 위해 위 helper만 사용해야 한다.

Revision note: 2026-04-10에 Sub-AC 5000003 구현용 ExecPlan을 신규 작성했고, 같은 날 shared loader 구현과 검증 결과를 반영해 Progress/Decision Log/Artifacts를 갱신했다. 이유는 evaluation/offline/predict-only 경로를 실제로 공통 표준 로더 계약으로 수렴시켰기 때문이다.
