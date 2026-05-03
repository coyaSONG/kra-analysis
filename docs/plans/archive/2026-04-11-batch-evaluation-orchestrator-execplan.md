# Batch Evaluation Orchestrator For Multi-Seed Runs

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document follows [.agent/PLANS.md](/Users/chsong/Developer/Personal/kra-analysis/.agent/PLANS.md) and must be maintained in accordance with that file.

## Purpose / Big Picture

After this change, the autoresearch evaluation path can accept a full seed batch and run each repeat as an isolated execution unit while still sharing one execution journal and one summary report. A user can verify the behavior by running the autoresearch seed-matrix tests and seeing that sequential and parallel batch execution both preserve per-seed status, result ordering, and failure isolation.

## Progress

- [x] 2026-04-11 03:35Z 기존 `evaluation_orchestrator.py`와 `seed_matrix_runner.py`의 역할 분리를 조사했다.
- [x] 2026-04-11 03:42Z 오케스트레이터 요청 형식을 `task` 또는 `tasks`로 확장하는 설계를 결정했다.
- [x] 2026-04-11 03:50Z 오케스트레이터에 순차/병렬 batch 실행과 공통 execution journal 경로 계산 로직을 추가했다.
- [x] 2026-04-11 03:57Z `seed_matrix_runner.py`가 외부 스레드풀 대신 batch 오케스트레이터를 직접 호출하도록 정리했다.
- [x] 2026-04-11 04:06Z consistency 메타데이터가 batch 결과의 첫 번째 항목만 읽던 버그를 수정했다.
- [x] 2026-04-11 04:07Z `uv run pytest -q packages/scripts/autoresearch/tests/test_evaluation_orchestrator.py packages/scripts/autoresearch/tests/test_seed_matrix_runner.py` 검증을 완료했다.
- [x] 2026-04-11 06:19Z 재실행 시 기존 execution journal과 detailed repository를 읽어 completed+storage-complete run은 재사용하고, failed/incomplete/non-terminal run만 다시 실행하도록 recovery flow를 추가했다.
- [x] 2026-04-11 06:19Z batch 재실행 후에도 seed result repository와 summary report가 journal 기준으로 다시 맞춰 써지도록 aggregate storage synchronization을 추가했다.
- [x] 2026-04-11 06:20Z 재사용/재실행/집계 복구 회귀 테스트를 추가하고 같은 pytest 묶음 24개 통과를 확인했다.

## Surprises & Discoveries

- Observation: 기존 `run_batch()`는 이름만 batch이고 실제로는 단일 태스크 `run_sequential()` 호출에 불과했다.
  Evidence: `packages/scripts/autoresearch/evaluation_orchestrator.py`의 기존 구현은 `run_batch()`에서 바로 `run_sequential()`을 반환했다.

- Observation: `seed_matrix_runner.py`는 이미 상위 레벨에서 병렬화를 수행하고 있었기 때문에, 오케스트레이터 확장 후에는 중복 책임이 생겼다.
  Evidence: 기존 `execute_seed_matrix()`는 `ThreadPoolExecutor`로 각 `OrchestratorRequest`를 별도 제출하고 있었다.

- Observation: execution journal만으로는 detailed seed result repository를 재구성할 수 없어서, completed run 재사용 여부를 판정할 때 detailed record 존재 여부까지 같이 확인해야 했다.
  Evidence: journal에는 `common_result`와 핵심 metrics만 있고 `DetailedSeedResultRecord` 본문은 저장되지 않는다.

## Decision Log

- Decision: 다중 반복 batch 실행 책임을 `evaluation_orchestrator.py`로 이동한다.
  Rationale: 반복 실행 단위 관리, 실패 격리, journaling, 결과 ordering을 한 계층에서 보장해야 AC 2의 “오케스트레이터” 의미에 맞다.
  Date/Author: 2026-04-11 / Codex

- Decision: batch 요청은 `task` 1개와 `tasks` 여러 개를 상호 배타적으로 받는다.
  Rationale: 기존 단일 태스크 CLI/호출부와의 하위 호환을 유지하면서 새로운 다중 태스크 사용례를 추가하기 가장 단순하다.
  Date/Author: 2026-04-11 / Codex

- Decision: batch 기본 execution journal 저장 위치는 첫 태스크 디렉터리가 아니라 모든 출력 디렉터리의 공통 상위 경로를 사용한다.
  Rationale: 반복별 결과는 분리하되 journal/repository/report는 batch 전체 공용 산출물이어야 재시작과 추적이 쉽다.
  Date/Author: 2026-04-11 / Codex

- Decision: 재실행 기본 동작은 “completed + output/manifest + detailed record 보존” 상태만 skip/reuse 하고, failed/non-terminal/storage-incomplete run은 다시 실행한다.
  Rationale: 성공한 반복은 중복 비용 없이 유지하면서도 저장 불완전 상태와 이전 실패 상태는 자동 복구해야 AC 4의 운영 복원력이 만족된다.
  Date/Author: 2026-04-11 / Codex

## Outcomes & Retrospective

오케스트레이터가 다중 시드 batch를 직접 실행하도록 구조를 바꿨고, seed-matrix 상위 러너의 중복 병렬화 책임을 제거했다. 여기에 더해 재실행 시 기존 성공 run 재사용, 실패 run 재실행, aggregate 산출물 재동기화까지 포함한 recovery flow를 넣었다. 관련 테스트 24개가 모두 통과했다. 남은 과제는 이 배치 오케스트레이터를 실제 연구 자동화 엔트리포인트와 연결하면서 운영 로그/스케줄링 레벨의 추가 검증을 넓히는 일이다.

## Context and Orientation

이 저장소의 autoresearch 평가는 `packages/scripts/autoresearch/` 아래에 있다. `evaluation_orchestrator.py`는 단일 시드 평가를 실행하고 execution journal과 holdout seed summary report를 갱신하는 진입점이다. `seed_matrix_runner.py`는 10개 시드 recent-holdout 반복 평가를 준비하고 실행하는 상위 러너다. “execution journal”은 각 반복의 상태와 핵심 지표를 기록하는 JSON 파일이고, “seed result repository”는 최종 holdout hit rate만 모아 gate 판정에 쓰는 JSON 파일이다. 이번 작업은 두 파일 사이의 책임을 정리해 batch 실행을 오케스트레이터가 직접 담당하게 만드는 것이다.

## Plan of Work

`packages/scripts/autoresearch/evaluation_orchestrator.py`에서 요청 스키마를 확장해 여러 `SingleSeedEvaluationTask`를 받을 수 있게 한다. 같은 파일에서 batch 실행 시 `max_workers`에 따라 순차 또는 병렬로 `_invoke_task()`를 실행하고, 결과를 입력 순서대로 반환하게 만든다. 기본 journal 경로는 다중 태스크 출력 디렉터리의 공통 상위 경로를 사용하도록 바꾼다.

`packages/scripts/autoresearch/seed_matrix_runner.py`에서는 계획된 10개 request를 하나의 batch request로 합쳐 오케스트레이터에 넘긴다. 기존 상위 레벨 `ThreadPoolExecutor`는 제거하고, 이후 메타데이터 집계와 flattened run 생성은 batch 결과의 전체 `results` 배열을 처리하도록 바꾼다.

`packages/scripts/autoresearch/tests/test_evaluation_orchestrator.py`에는 task list payload 파싱, 다중 태스크 순차 batch 실행, 병렬 batch 실행을 검증하는 테스트를 추가한다. 기존 저널/리포트 테스트는 하위 호환 확인 용도로 유지한다.

## Concrete Steps

작업 디렉터리: `/Users/chsong/Developer/Personal/kra-analysis`

1. 오케스트레이터 배치 기능 구현.
2. seed matrix runner를 batch request 기반으로 전환.
3. 테스트 추가.
4. `uv run pytest -q packages/scripts/autoresearch/tests/test_evaluation_orchestrator.py packages/scripts/autoresearch/tests/test_seed_matrix_runner.py` 실행.

실제 관찰 결과:

    $ UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q packages/scripts/autoresearch/tests/test_evaluation_orchestrator.py packages/scripts/autoresearch/tests/test_seed_matrix_runner.py
    .....................                                                    [100%]
    21 passed in 1.04s

## Validation and Acceptance

수용 기준은 다음과 같다. 여러 시드 태스크를 한 요청으로 넘기면 오케스트레이터가 각 반복을 독립 실행 단위로 기록해야 한다. `max_workers=1`이면 결과 순서가 입력 순서를 유지한 채 순차 실행되어야 한다. `max_workers>1`이면 동시에 두 개 이상 실행된 흔적이 테스트에서 관찰되어야 한다. `seed_matrix_runner.py`는 여전히 execution journal, seed result repository, summary report를 생성해야 한다.

## Idempotence and Recovery

이 변경은 additive 성격이며 테스트는 반복 실행 가능하다. batch 실행 도중 일부 태스크가 실패해도 execution journal은 실패 상태를 기록하고 다른 태스크 결과를 유지해야 한다. 동일 output directory에 다시 실행하면 journal upsert 로직이 같은 run_id 기준으로 최신 상태를 반영한다.

## Artifacts and Notes

핵심 변경 파일:

- `packages/scripts/autoresearch/evaluation_orchestrator.py`
- `packages/scripts/autoresearch/seed_matrix_runner.py`
- `packages/scripts/autoresearch/tests/test_evaluation_orchestrator.py`

Revision note: 2026-04-11에 AC 4000202 구현을 위해 신규 ExecPlan을 작성했고, 같은 날 batch 결과 consistency 수집 버그 수정, 재실행 recovery flow, aggregate storage synchronization, 테스트 통과 결과를 반영하도록 문서를 갱신했다.

## Interfaces and Dependencies

`packages/scripts/autoresearch/evaluation_orchestrator.py`에는 다음 형태가 최종적으로 존재해야 한다.

- `OrchestratorRequest(task: SingleSeedEvaluationTask | None, tasks: tuple[SingleSeedEvaluationTask, ...] | None, ...)`
- `run_batch(..., tasks: tuple[SingleSeedEvaluationTask, ...] | None = None, ...) -> list[dict[str, Any]]`
- `orchestrate_request(...) -> dict[str, Any]`

`packages/scripts/autoresearch/seed_matrix_runner.py`는 `SeedMatrixPlan.requests`를 유지하되 실행 시에는 이를 하나의 batch request로 합쳐 `orchestrate_request()`에 전달해야 한다.
