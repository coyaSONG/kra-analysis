# Evaluate Prompt V3 분해 및 평가 파이프라인 중복 제거 ExecPlan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

`PLANS.md` is checked into this repository at `.agent/PLANS.md`. This document must be maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

이 변경의 목표는 `packages/scripts/evaluation/evaluate_prompt_v3.py`의 1,030라인짜리 단일 파일을 작고 검증 가능한 모듈들로 분해하면서도, 현재 사용 중인 두 가지 진입 경로를 깨지 않는 것이다. 첫 경로는 `packages/scripts/prompt_improvement/recursive_prompt_improvement_v5.py`가 `PromptEvaluatorV3`를 직접 import 하는 경로이고, 둘째 경로는 `packages/scripts/pyproject.toml`과 `packages/scripts/package.json`이 `evaluation/evaluate_prompt_v3.py`를 CLI 엔트리포인트로 실행하는 경로다.

완료 후에는 신규 기여자가 데이터 로드, 예측 실행, JSON 파싱, 보상 계산, 병렬 배치 실행, 리포트 저장을 각각 독립 모듈에서 수정할 수 있어야 한다. 동시에 `evaluate_prompt_v3.py`와 `evaluate_prompt_v3_base.py` 사이의 중복도 공통 런타임 모듈로 흡수되어, 한쪽에 버그를 고치면 다른 쪽에도 같은 수정이 자연스럽게 반영되는 상태를 만든다.

## Progress

- [x] (2026-03-19 22:50 KST) `packages/scripts/evaluation/evaluate_prompt_v3.py`, `packages/scripts/evaluation/evaluate_prompt_v3_base.py`, `packages/scripts/prompt_improvement/recursive_prompt_improvement_v5.py`, `packages/scripts/pyproject.toml`, `packages/scripts/package.json`의 의존 경로를 확인했다.
- [x] (2026-03-19 22:56 KST) 분해 대상 책임을 데이터 접근, 예측 전략, 파싱, 점수 계산, 병렬 파이프라인, CLI/호환 계층으로 나눴다.
- [x] (2026-03-19 23:04 KST) 이 ExecPlan 초안을 작성했다.
- [ ] Phase 1 셸 고정 및 무중단 파일 이동을 구현한다.
- [ ] Phase 2 공통 런타임 추출과 v3 위임 전환을 구현한다.
- [ ] Phase 3 예측 전략 분리와 파서 정규화를 구현한다.
- [ ] Phase 4 병렬 파이프라인 공유화와 `evaluate_prompt_v3_base.py` 중복 제거를 구현한다.
- [ ] Phase 5 레거시 본문 제거와 최종 회귀 검증을 완료한다.

## Surprises & Discoveries

- Observation: `PromptEvaluatorV3`는 단순 CLI 클래스가 아니라 외부 모듈이 직접 import 해서 메서드를 호출하는 런타임 계약이다.
  Evidence: `packages/scripts/prompt_improvement/recursive_prompt_improvement_v5.py`가 `from evaluation.evaluate_prompt_v3 import PromptEvaluatorV3`로 import 한 뒤 `find_test_races()`를 직접 호출한다.

- Observation: `evaluate_prompt_v3.py`와 `evaluate_prompt_v3_base.py`는 데이터 로드, JSON 파싱, 재시도, 보상 계산, 병렬 실행 루프를 거의 같은 형태로 중복 구현하고 있다.
  Evidence: 두 파일 모두 `find_test_races`, `load_race_data`, `_parse_stream_json`, `_parse_regular_output`, `run_prediction_with_retry`, `calculate_reward`, `process_single_race`, `evaluate_all_parallel`를 갖는다.

- Observation: 이미 분리된 모듈도 있다. 따라서 이번 작업은 모든 것을 새로 설계하는 것이 아니라 이미 독립된 경계를 기준으로 남은 비대 파일을 줄이는 방향이 맞다.
  Evidence: `packages/scripts/evaluation/metrics.py`, `packages/scripts/evaluation/report_schema.py`, `packages/scripts/evaluation/mlflow_tracker.py`는 현재도 별도 모듈로 사용 중이다.

- Observation: 직접적인 evaluator 테스트가 거의 없다. 현재 테스트는 메트릭과 리포트 스키마 중심이라, 리팩터링 전용 계약 테스트를 먼저 추가하지 않으면 안전한 단계 배포가 어렵다.
  Evidence: `packages/scripts/tests/`에는 `test_metrics.py`, `test_report_schema.py` 등은 있지만 `PromptEvaluatorV3` 공개 계약을 고정하는 테스트는 없다.

## Decision Log

- Decision: `packages/scripts/evaluation/evaluate_prompt_v3.py` 파일 경로와 `PromptEvaluatorV3` 클래스명은 마이그레이션이 끝날 때까지 유지한다.
  Rationale: `recursive_prompt_improvement_v5.py`, `pyproject.toml`, `package.json`이 이 경로와 이름에 결합돼 있으므로, 내부 분해보다 외부 계약 안정성이 우선이다.
  Date/Author: 2026-03-19 / Codex.

- Decision: 첫 단계는 기능 분해가 아니라 "호환 셸 고정"이다. 즉 기존 본문을 안전한 내부 모듈로 옮기고, 기존 파일은 얇은 wrapper로 바꾼다.
  Rationale: 이후 단계에서 내부 구조를 바꾸더라도 외부 import/CLI 경로를 고정할 수 있어 독립 배포와 빠른 rollback이 가능하다.
  Date/Author: 2026-03-19 / Codex.

- Decision: 공통 코드는 `evaluation/runtime/` 아래로, v3 전용 코드는 `evaluation/v3/` 아래로 이동한다.
  Rationale: 이번 작업의 본질은 거대 파일 분해와 `v3`/`base` 중복 제거를 동시에 달성하는 것이다. `runtime`은 두 evaluator가 공유하는 안정 계층이 되고, `v3`는 jury/ensemble 같은 전용 전략만 담는다.
  Date/Author: 2026-03-19 / Codex.

- Decision: 이미 분리된 `metrics.py`, `report_schema.py`, `mlflow_tracker.py`는 이번 마이그레이션의 이동 대상에서 제외한다.
  Rationale: 현재 경계가 충분히 명확하고 테스트도 있어, 다시 섞는 것보다 그대로 둔 채 evaluator 내부 책임만 줄이는 편이 안전하다.
  Date/Author: 2026-03-19 / Codex.

## Outcomes & Retrospective

현재 시점의 산출물은 구현용 기준 문서다. 아직 코드 변경은 없지만, phase 경계, 파일 이동 순서, 호환 래퍼, rollback 지점을 확정했다. 구현이 시작되면 각 phase 종료 시 실제 이동된 파일, 통과한 테스트, 제거된 중복량, 남은 legacy surface를 이 섹션에 기록한다.

## Context and Orientation

현재 `packages/scripts/evaluation/evaluate_prompt_v3.py`는 하나의 클래스 안에서 여섯 가지 책임을 동시에 수행한다. 첫째, `RaceDBClient`를 통한 경주 조회와 결과 추출이다. 둘째, DB 응답을 evaluator 입력 형식으로 변환하고 파생 피처를 계산하는 데이터 준비다. 셋째, Claude 단일 예측, self-consistency ensemble, LLM jury라는 세 가지 예측 실행 방식이다. 넷째, JSON 응답 파싱과 `selected_horses`/`predicted` 형태 정규화다. 다섯째, 적중 보상 계산과 결과 레코드 조립이다. 여섯째, `ThreadPoolExecutor` 기반 병렬 실행, 메트릭 계산, MLflow 로깅, 결과 파일 저장, CLI 인자 파싱이다.

`packages/scripts/evaluation/evaluate_prompt_v3_base.py`는 이름만 다른 별도 evaluator처럼 보이지만 실제로는 같은 파이프라인의 축소판이다. CLI 호출 방식과 일부 출력 필드만 다를 뿐, 레이스 조회, 데이터 적재, 파싱, 재시도, 보상, 병렬 실행 구조가 거의 동일하다. 따라서 `evaluate_prompt_v3.py`를 분해할 때 공통 런타임을 만들지 않으면 거대 파일만 쪼개고 중복 자체는 남게 된다.

이 계획에서 "호환 래퍼"는 바깥 호출자에게는 기존 이름과 경로를 그대로 제공하면서, 안쪽 구현만 새 모듈로 위임하는 얇은 계층을 뜻한다. "rollback point"는 각 phase가 통과 테스트와 함께 하나의 안전한 되돌림 지점으로 남는 커밋 또는 태그를 뜻한다. 이 작업에는 데이터베이스 스키마 변경이 없으므로 rollback은 모두 코드 레벨 revert로 처리한다.

## Phase Plan

### Phase 1. 셸 고정과 무중단 파일 이동

이 phase의 목적은 외부 계약을 고정하는 것이다. 현재 `packages/scripts/evaluation/evaluate_prompt_v3.py`의 본문을 거의 변경 없이 `packages/scripts/evaluation/v3/legacy_runtime.py`로 이동하고, 원래 파일은 `PromptEvaluatorV3`와 `main()`을 재노출하는 얇은 wrapper로 바꾼다. 이 시점의 동작은 완전히 동일해야 하며, 변경 후에도 `uv run python evaluation/evaluate_prompt_v3.py ...`와 `from evaluation.evaluate_prompt_v3 import PromptEvaluatorV3`가 모두 동일하게 동작해야 한다.

독립 배포 기준은 "파일 경로는 그대로인데 내부 구현이 새 모듈에서 실행된다"는 점이다. 이 상태가 확보되면 이후 phase들은 `legacy_runtime.py` 내부만 점진적으로 비워도 외부 계약을 건드리지 않는다.

### Phase 2. 공통 런타임 추출과 v3 위임 전환

이 phase에서는 두 evaluator에 공통인 순수하거나 저위험인 책임을 `packages/scripts/evaluation/runtime/`으로 뺀다. 우선 `find_test_races`, `load_race_data`, `extract_actual_result`를 `runtime/race_loader.py`로, `_parse_stream_json`과 `_parse_regular_output`을 `runtime/parsing.py`로, `calculate_reward`와 `_convert_race_data_for_v5`를 `runtime/scoring.py`로 이동한다.

이 phase 끝에서 `PromptEvaluatorV3`는 여전히 같은 메서드명을 가지지만, 내부 구현은 새 runtime 모듈에 위임한다. `evaluate_prompt_v3_base.py`는 아직 wrapper로 바꾸지 않아도 되지만, 같은 runtime 모듈을 쓸 수 있도록 계약을 맞춰 둔다. 독립 배포 기준은 "v3는 새 runtime을 사용하지만 base는 아직 손대지 않아도 정상"이다.

### Phase 3. 예측 전략과 프롬프트 조립 분리

이 phase에서는 v3 전용 복잡도를 떼어낸다. `run_claude_prediction`은 `packages/scripts/evaluation/v3/predictors/claude_sdk.py`로, `run_ensemble_prediction`은 `v3/predictors/ensemble.py`로, `_init_jury`와 `run_jury_prediction`은 `v3/predictors/jury.py`로, 프롬프트 파일 로드와 prompt string 조립은 `v3/prompting.py`로 이동한다. `run_prediction_with_retry`는 `v3/retry.py` 또는 `v3/predictors/retry.py`로 분리한다.

이 phase 끝에서 `PromptEvaluatorV3`는 오케스트레이터 역할만 수행한다. 공개 메서드 이름은 유지하되 내부에서는 새 strategy 객체를 호출한다. 독립 배포 기준은 "단일 예측, ensemble, jury 세 모드가 기존 CLI 옵션과 같은 결과 JSON 형태를 유지한다"이다.

### Phase 4. 병렬 파이프라인 공유화와 base 중복 제거

이 phase에서는 `process_single_race`, `evaluate_all_parallel`, summary 조립, 출력 파일 저장을 `packages/scripts/evaluation/runtime/pipeline.py`와 `packages/scripts/evaluation/runtime/reporting.py`로 분리한다. 그리고 `packages/scripts/evaluation/evaluate_prompt_v3_base.py`도 `packages/scripts/evaluation/base/evaluator.py` 및 같은 runtime 모듈을 사용하도록 전환한다.

이 phase가 끝나면 `v3`와 `base`는 "예측기만 다른 같은 파이프라인"이 된다. 데이터 적재, JSON 정규화, 보상 계산, 병렬 실행, 결과 저장은 공통 코드가 담당하고, 각 evaluator는 predictor 구성만 다르게 가진다. 독립 배포 기준은 "`evaluate_prompt_v3.py`와 `evaluate_prompt_v3_base.py` 둘 다 동작하면서 중복된 핵심 파이프라인 코드가 제거된다"이다.

### Phase 5. 레거시 본문 제거와 영구 래퍼 유지

마지막 phase에서는 `legacy_runtime.py`에 남아 있는 임시 위임 코드와 죽은 helper를 제거한다. 다만 `packages/scripts/evaluation/evaluate_prompt_v3.py`와 `packages/scripts/evaluation/evaluate_prompt_v3_base.py` 두 파일 자체는 영구 wrapper로 유지한다. 이유는 외부 호출자가 이미 이 파일 경로를 계약처럼 사용하고 있기 때문이다.

이 phase의 독립 배포 기준은 "public surface는 그대로인데, 내부에 더 이상 대형 legacy class 본문이 존재하지 않는다"이다. 이때부터는 새 모듈 구조가 canonical source of truth가 된다.

## File Moves

다음 이동은 phase별로 수행한다. 각 move는 한 번에 너무 많이 하지 말고, 파일 이동 후 import 정리와 계약 테스트를 같은 커밋 또는 바로 이어지는 작은 커밋으로 묶는다.

- Phase 1에서 현재 `packages/scripts/evaluation/evaluate_prompt_v3.py` 본문을 `packages/scripts/evaluation/v3/legacy_runtime.py`로 이동한다.
- Phase 1에서 새 `packages/scripts/evaluation/evaluate_prompt_v3.py`를 만들고, 이 파일은 `PromptEvaluatorV3`와 `main`만 재노출한다.
- Phase 1에서 `packages/scripts/evaluation/v3/__init__.py`, `packages/scripts/evaluation/v3/cli.py`, `packages/scripts/evaluation/v3/config.py`를 추가한다.
- Phase 2에서 `find_test_races`, `load_race_data`, `extract_actual_result`를 `packages/scripts/evaluation/runtime/race_loader.py`로 옮긴다.
- Phase 2에서 `_parse_stream_json`, `_parse_regular_output`을 `packages/scripts/evaluation/runtime/parsing.py`로 옮긴다.
- Phase 2에서 `calculate_reward`, `_convert_race_data_for_v5`를 `packages/scripts/evaluation/runtime/scoring.py`로 옮긴다.
- Phase 3에서 prompt template 읽기와 prompt 조립 로직을 `packages/scripts/evaluation/v3/prompting.py`로 옮긴다.
- Phase 3에서 `run_claude_prediction`을 `packages/scripts/evaluation/v3/predictors/claude_sdk.py`로 옮긴다.
- Phase 3에서 `run_ensemble_prediction`을 `packages/scripts/evaluation/v3/predictors/ensemble.py`로 옮긴다.
- Phase 3에서 `_init_jury`, `run_jury_prediction`을 `packages/scripts/evaluation/v3/predictors/jury.py`로 옮긴다.
- Phase 3에서 `run_prediction_with_retry`를 `packages/scripts/evaluation/v3/retry.py`로 옮긴다.
- Phase 4에서 `process_single_race`, `evaluate_all_parallel`, summary 조립을 `packages/scripts/evaluation/runtime/pipeline.py`로 옮긴다.
- Phase 4에서 콘솔 요약 출력, 결과 파일 저장, MLflow 기록 접점을 `packages/scripts/evaluation/runtime/reporting.py`로 옮긴다.
- Phase 4에서 `packages/scripts/evaluation/evaluate_prompt_v3_base.py`의 본문을 `packages/scripts/evaluation/base/evaluator.py`로 이동하고, 원래 파일은 wrapper로 바꾼다.
- Phase 5에서 `packages/scripts/evaluation/v3/legacy_runtime.py`에 남은 중복 코드를 제거하거나 파일 자체를 삭제하고 `packages/scripts/evaluation/v3/evaluator.py`를 canonical 구현으로 승격한다.

## Compatibility Wrappers

호환성은 파일 경로, 공개 클래스명, CLI 인자, 결과 JSON shape 네 층으로 유지한다.

- `packages/scripts/evaluation/evaluate_prompt_v3.py`는 끝까지 유지한다. 이 파일은 최종적으로도 `main()`과 `PromptEvaluatorV3`를 재노출하는 thin wrapper여야 한다.
- `packages/scripts/evaluation/evaluate_prompt_v3_base.py`도 base 전환 이후 thin wrapper로 유지한다. 외부 사용자가 파일 경로를 스크립트 계약으로 사용할 수 있기 때문이다.
- `PromptEvaluatorV3`의 공개 메서드 `find_test_races()`와 `evaluate_all_parallel()`은 시그니처를 유지한다. `recursive_prompt_improvement_v5.py`가 의존하는 메서드는 호환성 보장 대상이다.
- CLI 인자 집합은 유지한다. `prompt_version`, `prompt_file`, `test_limit`, `max_workers`, `--report-format`, `--asof-check`, `--topk`, `--metrics-profile`, `--defer-threshold`, `--ensemble-k`, `--jury`, `--jury-models`, `--jury-weights`, `--with-past-stats`는 새 CLI 계층에서도 그대로 받아야 한다.
- 파서 정규화 계층은 migration 동안 `selected_horses`, `predicted`, `prediction` 입력을 모두 받아들이고, 내부 공통 표현으로 바꾼 뒤 필요한 legacy alias를 다시 채워 넣는다.
- 결과 파일 이름 패턴 `data/prompt_evaluation/evaluation_{prompt_version}_{timestamp}.json`은 유지한다. 다운스트림 자동화가 파일명 패턴에 묶여 있을 가능성이 높기 때문이다.
- `report_format == "v2"`일 때 생성되는 top-level JSON shape는 유지한다. 이미 `build_report_v2()`와 `validate_report_v2()` 테스트가 있으므로 이 계약을 migration boundary로 사용한다.
- `prediction` 원문 필드는 detailed result에 계속 남긴다. 디버깅과 후속 분석이 이 필드를 사용할 수 있기 때문이다.

## Rollback Points

각 phase는 "작은 커밋 묶음 + 테스트 통과 + 태그"로 끝내야 한다. rollback은 데이터를 건드리지 않으므로 코드 revert만으로 충분하다.

- `rp-eval-v3-shell`: Phase 1 완료 직후 태그다. 이 시점에는 wrapper만 바뀌었고 실제 실행 코드는 `v3/legacy_runtime.py`에 그대로 있으므로, 문제가 생기면 wrapper import를 이전 경로로 되돌리거나 Phase 1 커밋만 revert 하면 된다.
- `rp-eval-v3-runtime-core`: Phase 2 완료 직후 태그다. 데이터 적재, 파싱, 보상 계산이 `runtime/`으로 이동했지만 predictor와 병렬 파이프라인은 아직 크게 바뀌지 않았다. 회귀가 나면 해당 위임 커밋만 revert 하면 된다.
- `rp-eval-v3-predictors`: Phase 3 완료 직후 태그다. 이 시점 rollback은 predictor strategy 분리만 되돌리면 되고, `runtime/` 계층은 유지할 수 있다.
- `rp-eval-v3-shared-pipeline`: Phase 4 완료 직후 태그다. 이 시점에는 `base`도 공유 파이프라인으로 넘어와 있으므로, 문제가 생기면 `base` wrapper만 legacy adapter로 잠시 되돌리고 `runtime/pipeline.py` 전환 커밋을 revert 한다.
- `rp-eval-v3-final-cutover`: Phase 5 직전 태그다. `legacy_runtime.py`를 삭제하거나 대폭 축소하기 전 마지막 안전 지점이므로, 최종 정리 후 회귀가 나오면 이 태그로 즉시 돌아가 원인을 좁힌다.

## Plan of Work

구현 순서는 반드시 "외부 계약 고정 → 공통 저위험 코드 추출 → v3 전용 전략 추출 → 공유 파이프라인 전환 → 레거시 제거"를 따른다. 이 순서를 거꾸로 하면 초반부터 import path와 CLI contract를 동시에 건드리게 되어 rollback이 비싸진다.

먼저 `evaluate_prompt_v3.py`를 wrapper로 고정하고 계약 테스트를 추가한다. 그 다음 공통 코드 추출은 파싱, 점수 계산, 레이스 적재처럼 부작용이 적은 순서로 진행한다. predictor 계층은 외부 I/O와 결합돼 있으므로 공통 runtime이 안정화된 뒤에 분리한다. 마지막으로 병렬 실행 루프를 shared pipeline으로 만들고, 그때 `evaluate_prompt_v3_base.py`를 같은 runtime에 붙인다.

이 계획은 "중복 제거"와 "거대 파일 분해"를 같은 순간에 한 번에 끝내지 않는다. v3를 먼저 canonical path로 만들고, base는 뒤에서 공통 런타임 소비자로 붙인다. 그래야 한 phase가 실패해도 v3 실사용 경로를 우선 보호할 수 있다.

## Concrete Steps

모든 명령은 저장소 루트 `/Users/chsong/Developer/Personal/kra-analysis` 또는 `packages/scripts`에서 실행한다.

1. 현재 계약을 고정하는 테스트를 먼저 추가한다.

    cd packages/scripts
    uv run pytest -q tests/test_metrics.py tests/test_report_schema.py

   여기에 이어 `tests/test_evaluate_v3_contract.py`를 추가해 `PromptEvaluatorV3` import, `main` import, CLI help, `find_test_races` 메서드 존재를 고정한다.

2. Phase 1 구현 후 wrapper 경로가 유지되는지 확인한다.

    cd packages/scripts
    uv run python - <<'PY'
    from evaluation.evaluate_prompt_v3 import PromptEvaluatorV3, main
    print(PromptEvaluatorV3.__name__)
    print(callable(main))
    PY

   기대 결과는 `PromptEvaluatorV3`와 `main`이 여전히 import 가능하다는 것이다.

3. Phase 2와 Phase 3에서는 공통 모듈 단위 테스트를 추가한다.

    cd packages/scripts
    uv run pytest -q tests/test_evaluation_parsing.py tests/test_evaluation_scoring.py tests/test_evaluation_race_loader.py

   기대 결과는 파서가 `selected_horses`, `predicted`, `prediction`을 모두 정규화하고, 보상 계산과 데이터 적재가 evaluator 클래스 없이도 검증된다는 것이다.

4. Phase 4에서는 공유 파이프라인 테스트와 base 회귀 테스트를 추가한다.

    cd packages/scripts
    uv run pytest -q tests/test_evaluation_pipeline.py tests/test_evaluate_v3_contract.py

   기대 결과는 v3와 base가 같은 pipeline helper를 사용해도 기존 출력 계약을 유지한다는 것이다.

5. 각 phase 끝에서 CLI 스모크 테스트를 수행한다.

    cd packages/scripts
    pnpm run evaluate:help

   기대 결과는 CLI usage가 계속 노출되고 엔트리포인트가 깨지지 않는다는 것이다.

## Validation and Acceptance

이 계획의 수용 기준은 코드 스타일이 아니라 관찰 가능한 동작이다. 첫째, 어느 phase에서든 `from evaluation.evaluate_prompt_v3 import PromptEvaluatorV3`가 계속 성공해야 한다. 둘째, `pnpm --filter=@repo/scripts run evaluate:v3 --help` 또는 동등한 help 호출이 실패하지 않아야 한다. 셋째, `report_format == "v2"` 결과 JSON의 top-level schema가 유지되어 기존 `test_report_schema.py`와 신규 계약 테스트를 통과해야 한다.

각 phase별 acceptance는 더 구체적이어야 한다. Phase 1은 import path와 CLI path가 유지되는 것이 핵심이다. Phase 2는 데이터 적재, 파싱, 보상 계산이 evaluator 본문 밖으로 이동해도 동일 동작을 보이는 것이 핵심이다. Phase 3은 single, ensemble, jury 세 예측 경로가 동일한 normalized prediction contract를 생산하는 것이 핵심이다. Phase 4는 v3와 base가 같은 pipeline helper를 사용하면서도 각자의 출력 필드를 유지하는 것이 핵심이다. Phase 5는 legacy 본문 제거 후에도 외부 호출자가 변화를 느끼지 못하는 것이 핵심이다.

## Idempotence and Recovery

이 작업은 데이터 마이그레이션이 없으므로 반복 실행과 rollback이 상대적으로 안전하다. 안전성을 높이기 위해 각 phase는 additive change로 시작하고 subtraction은 마지막에만 한다. 예를 들어 새 runtime 모듈을 도입할 때는 먼저 기존 evaluator가 그 모듈을 호출하도록 바꾸고, 충분한 테스트가 붙은 뒤에만 옛 중복 코드를 삭제한다.

실패 복구 원칙은 단순하다. import path가 깨졌으면 wrapper commit만 revert 한다. predictor 회귀가 났으면 predictor strategy 분리 commit만 revert 한다. shared pipeline 회귀가 났으면 base 전환 commit과 pipeline 전환 commit만 revert 한다. `metrics.py`, `report_schema.py`, `mlflow_tracker.py`는 이 계획의 rollback 범위에서 제외한다.

## Artifacts and Notes

이번 계획 수립의 핵심 근거 파일은 다음과 같다.

    packages/scripts/evaluation/evaluate_prompt_v3.py
    packages/scripts/evaluation/evaluate_prompt_v3_base.py
    packages/scripts/evaluation/metrics.py
    packages/scripts/evaluation/report_schema.py
    packages/scripts/evaluation/mlflow_tracker.py
    packages/scripts/prompt_improvement/recursive_prompt_improvement_v5.py
    packages/scripts/pyproject.toml
    packages/scripts/package.json

추가로 구현 시점에 아래 테스트 파일을 신규 도입하는 것을 권장한다.

    packages/scripts/tests/test_evaluate_v3_contract.py
    packages/scripts/tests/test_evaluation_parsing.py
    packages/scripts/tests/test_evaluation_scoring.py
    packages/scripts/tests/test_evaluation_race_loader.py
    packages/scripts/tests/test_evaluation_pipeline.py

## Interfaces and Dependencies

최종 상태에서 `evaluation.evaluate_prompt_v3:main`은 기존과 같은 CLI surface를 제공해야 한다. 단, 실제 argparse와 config 해석은 `packages/scripts/evaluation/v3/cli.py`와 `packages/scripts/evaluation/v3/config.py`로 이동해도 된다.

최종 상태에서 `PromptEvaluatorV3`는 얇은 오케스트레이터여야 한다. 이 클래스는 `RaceDBClient`, `ClaudeClient`, `ExperimentTracker`, jury/ensemble predictor, runtime pipeline을 조립하는 역할만 하고, 직접 JSON regex나 reward 계산식을 들고 있지 않아야 한다.

최종 상태에서 `runtime/parsing.py`는 입력 변형을 흡수하는 유일한 곳이어야 한다. 이 모듈은 `selected_horses`, `predicted`, `prediction`을 모두 받아 내부 공통 표현으로 정규화하고, 필요할 때만 legacy alias를 다시 추가해야 한다.

최종 상태에서 `runtime/pipeline.py`는 "한 경주를 평가 결과 한 건으로 바꾸는 절차"와 "여러 경주를 병렬로 돌려 summary/report를 만드는 절차"를 제공해야 한다. `v3`와 `base`는 이 파이프라인에 predictor만 주입하는 구조가 바람직하다.

Change note: 2026-03-19 / Codex. `evaluate_prompt_v3.py` 거대 파일 분해와 평가 파이프라인 중복 제거를 위한 최초 ExecPlan을 추가했다. 이유는 외부 import/CLI 계약을 유지한 채 독립 배포 가능한 phase와 rollback 지점을 먼저 고정하기 위해서다.
