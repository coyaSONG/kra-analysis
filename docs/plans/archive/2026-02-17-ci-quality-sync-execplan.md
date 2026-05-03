# CI/로컬 품질검사 싱크 개선 ExecPlan

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

`PLANS.md` is checked into this repository at `.agent/PLANS.md`. This document must be maintained in accordance with `.agent/PLANS.md`.

## Purpose / Big Picture

현재 저장소는 "로컬에서 자주 실행하는 품질검사"와 "GitHub Actions가 실제로 실행하는 품질검사" 사이에 명령 소스가 분리되어 있다. 특히 Python 검사에서 일부 단계는 `apps/api` 기준으로, 일부 단계는 루트 기준으로 실행되어 경로 드리프트가 발생할 수 있다. 이 상태는 개발자가 로컬에서 통과를 확인했는데 CI에서 실패하는 상황을 반복적으로 만든다.

이 작업이 완료되면, 품질검사 명령의 단일 소스(single source of truth)가 생기고, CI는 그 소스를 호출만 하도록 단순화된다. 사용자는 로컬에서 같은 명령을 실행해 CI 결과를 더 정확히 재현할 수 있다.

## Progress

- [x] (2026-02-17 15:40Z) 기존 CI/로컬 검사 흐름을 조사하고 불일치 지점을 정리했다.
- [x] (2026-02-17 15:43Z) 본 ExecPlan 초안을 작성했다.
- [x] (2026-02-17 15:41Z) 공통 Python 품질검사 실행 스크립트(`apps/api/scripts/run_quality_ci.sh`)를 추가했다.
- [x] (2026-02-17 15:41Z) 공통 보안(repository hygiene) 검사 스크립트(`.github/scripts/security_checks.sh`)를 추가했다.
- [x] (2026-02-17 15:42Z) 루트 `package.json`에 로컬/CI 공용 품질 스크립트 엔트리 포인트(`quality:*`)를 추가했다.
- [x] (2026-02-17 15:42Z) `.github/workflows/ci.yml`을 공통 스크립트 호출 구조로 전환했다.
- [x] (2026-02-17 15:43Z) 로컬 검증 명령(`lint/format/typecheck/node/security`)을 실행하고 결과를 기록했다.

## Surprises & Discoveries

- Observation: Python job에서 `Ruff lint`는 `apps/api` 기준으로 실행되지만 `Ruff format check`는 루트 기준으로 실행되어, 검사 범위가 의도치 않게 달라질 수 있다.
  Evidence: `.github/workflows/ci.yml`의 `Ruff lint`(`working-directory: ./apps/api`)와 `Ruff format check`(working-directory 없음) 차이.

- Observation: 루트 `package.json`에는 CI 품질 체인을 그대로 재현하는 단일 스크립트가 없다.
  Evidence: `package.json`에는 `lint`, `test` 등만 있고 CI parity를 위한 `quality:*` 스크립트가 없다.

- Observation: Python `typecheck`는 현재 코드베이스 기준으로 다수의 mypy 오류가 존재하지만 CI에서 non-blocking으로 운용되고 있다.
  Evidence: `bash apps/api/scripts/run_quality_ci.sh typecheck` 실행 시 99 errors 출력, 종료 코드는 `0`(의도적으로 `|| true` 유지).

## Decision Log

- Decision: CI 명령을 YAML 내부에 중복 작성하지 않고, 스크립트 파일(쉘)로 이동해 로컬과 CI가 같은 명령 소스를 공유한다.
  Rationale: 검사 범위 드리프트를 줄이고 유지보수 비용을 낮춘다.
  Date/Author: 2026-02-17 / Codex.

- Decision: Node 검사 체인은 기존 Turbo 기반 구조를 유지하되 루트 `package.json`의 `quality:node:*` 별칭을 통해 CI 호출 대상을 명시한다.
  Rationale: 기존 동작을 유지하면서도 로컬/CI에서 동일 진입점을 제공한다.
  Date/Author: 2026-02-17 / Codex.

- Decision: 보안 검사는 `gitleaks` 액션 단계와 분리해, 현재 워크플로우의 grep 기반 hygiene 규칙만 별도 스크립트로 통합한다.
  Rationale: 로컬 실행 가능성과 CI 액션 의존성(gh token 필요)을 분리해 재현성을 높인다.
  Date/Author: 2026-02-17 / Codex.

- Decision: Python `typecheck` 단계는 기존 CI 의미를 유지하기 위해 non-blocking(오류를 출력하되 실패로 처리하지 않음)으로 둔다.
  Rationale: 이번 작업 목표는 parity/중앙화이며, mypy strictness 상향은 별도 품질개선 트랙으로 분리해야 한다.
  Date/Author: 2026-02-17 / Codex.

## Outcomes & Retrospective

완료 상태 요약:

- Python 품질검사 명령은 `apps/api/scripts/run_quality_ci.sh`로 단일 소스화되었고, CI Python job이 해당 스크립트를 단계별 호출하도록 정리되었다.
- Security hygiene 검사(`API key pattern`, `.env tracked`, `data tracked`)는 `.github/scripts/security_checks.sh`로 단일 소스화되었다.
- 루트 `package.json`에 `quality:api:*`, `quality:node:*`, `quality:security`, `quality:ci` 엔트리포인트가 추가되어 로컬에서도 동일 진입점을 사용할 수 있다.
- 로컬 검증에서 `lint/format/node/security`는 정상 종료했고, `typecheck`는 기존과 동일하게 오류 출력(non-blocking) 상태를 유지했다.

남은 리스크:

- `quality:api:ci` 전체 실행(`unit/integration/coverage`)은 PostgreSQL/Redis 등 의존 서비스가 필요하므로, 서비스 미기동 로컬에서는 CI 완전 재현이 제한된다.

## Context and Orientation

이 저장소는 pnpm workspaces + Turbo 모노레포다. 품질검사와 직접 연관된 핵심 파일은 다음과 같다.

- `.github/workflows/ci.yml`: GitHub Actions CI 파이프라인.
- `package.json`: 루트 스크립트 진입점.
- `apps/api`: Python(FastAPI) 애플리케이션. `uv`, `ruff`, `mypy`, `pytest`를 사용한다.
- `apps/collector`: TypeScript(Node) 애플리케이션. `eslint`, `tsc`, `jest`를 사용한다.

이 문서에서 "단일 소스"는 품질검사 실제 명령이 한 곳(스크립트/alias)에 정의되고, CI는 해당 엔트리 포인트를 호출만 하는 구조를 의미한다.

## Milestones

### Milestone 1: Python 품질검사 단일 소스화

`apps/api/scripts/run_quality_ci.sh`를 추가해 lint/format/typecheck/unit/integration/coverage 실행 단계를 인자로 분기한다. CI Python job은 이 스크립트를 단계별로 호출한다. 로컬에서도 동일 스크립트를 직접 실행할 수 있다.

### Milestone 2: 보안 hygiene 검사 단일 소스화

`.github/scripts/security_checks.sh`를 추가해 현재 workflow에 하드코딩된 `API key pattern`, `.env tracked`, `data/ tracked` 검사를 통합한다. CI security job은 해당 스크립트를 호출한다.

### Milestone 3: 루트 품질 엔트리포인트 정렬

루트 `package.json`에 `quality:api:*`, `quality:node:*`, `quality:security`, `quality:ci` 스크립트를 추가한다. CI Node job은 이 엔트리포인트를 사용해 실행한다.

### Milestone 4: 검증 및 기록

변경 후 로컬에서 실행 가능한 검사(ruff, node lint/typecheck/test:ci, security hygiene)를 돌리고 결과를 기록한다. 통합 테스트 등 환경 의존 명령은 실행 조건을 명확히 문서화한다.

## Plan of Work

먼저 Python 검사 명령을 셸 스크립트로 추출한다. 이 스크립트는 실행 위치를 자체적으로 `apps/api`로 고정해 경로 드리프트를 제거한다. 인자(`lint`, `format`, `typecheck`, `unit`, `integration`, `coverage`, `all`)에 따라 단계별 실행이 가능하도록 구현해 CI의 현재 step 단위를 유지한다.

다음으로 보안 hygiene 검사를 별도 셸 스크립트로 추출한다. 기존 workflow의 grep 조건식을 그대로 이식해 동작 의미를 보존한다.

그 다음 루트 `package.json`에 quality 엔트리포인트를 추가한다. 이로써 개발자는 `pnpm run quality:ci` 또는 서브 스크립트를 통해 CI와 동일한 품질검사를 실행할 수 있다.

마지막으로 `.github/workflows/ci.yml`을 스크립트 호출 구조로 변경한다. Python job은 새 스크립트를 단계별 호출하고, Node job은 루트 quality alias를 호출한다. Security job의 hygiene 단계도 스크립트로 대체한다.

## Concrete Steps

Working directory 기본값은 저장소 루트(`kra-analysis`)로 가정한다.

1. Python 공통 스크립트 추가.

   Run:
     mkdir -p apps/api/scripts
     # run_quality_ci.sh 생성 및 실행권한 부여

2. 보안 공통 스크립트 추가.

   Run:
     mkdir -p .github/scripts
     # security_checks.sh 생성 및 실행권한 부여

3. 루트 `package.json` 스크립트 갱신.

   Edit:
     `package.json`의 `scripts`에 `quality:*` 항목 추가.

4. CI workflow를 공통 스크립트 호출 방식으로 수정.

   Edit:
     `.github/workflows/ci.yml`의 Python/Node/Security 관련 step 명령 정리.

5. 로컬 검증 실행.

   Run:
     bash apps/api/scripts/run_quality_ci.sh lint
     bash apps/api/scripts/run_quality_ci.sh format
     pnpm run quality:node:ci
     pnpm run quality:security

   Note:
     `unit/integration/coverage`는 PostgreSQL/Redis 및 환경변수 요구사항이 있으므로, 서비스 미기동 환경에서는 선택 실행으로 기록한다.

## Validation and Acceptance

다음 조건이 충족되면 수용한다.

- `.github/workflows/ci.yml`의 품질 명령이 스크립트/alias 호출 중심으로 바뀌어, 동일 명령이 로컬에서도 실행 가능하다.
- Python 검사에서 실행 디렉터리 드리프트가 제거된다.
- 루트에서 `pnpm run quality:ci`를 통해 CI 품질검사 진입점에 접근할 수 있다.
- 로컬 검증 로그에서 최소 `lint/format/node/security`가 정상 종료된다.

## Idempotence and Recovery

이번 변경은 스크립트/워크플로우/package 스크립트 추가 및 수정으로만 구성되며 데이터 마이그레이션이나 파괴적 작업이 없다. 동일 명령을 반복 실행해도 상태 오염이 없다. 문제가 생기면 해당 파일 변경을 git으로 되돌려 복구할 수 있다.

## Artifacts and Notes

검증 결과는 작업 완료 후 아래에 요약 로그를 추가한다.

- `bash apps/api/scripts/run_quality_ci.sh lint` 결과
- `bash apps/api/scripts/run_quality_ci.sh format` 결과
- `bash apps/api/scripts/run_quality_ci.sh typecheck` 결과
- `pnpm run quality:node:ci` 결과
- `pnpm run quality:security` 결과

요약 로그:

- `bash apps/api/scripts/run_quality_ci.sh lint` -> `All checks passed!`
- `bash apps/api/scripts/run_quality_ci.sh format` -> `102 files already formatted`
- `bash apps/api/scripts/run_quality_ci.sh typecheck` -> mypy 오류 99건 출력, 종료코드 0(non-blocking 유지)
- `pnpm run quality:node:ci` -> lint/typecheck/test:ci 모두 성공(기존 eslint warning 다수는 유지)
- `pnpm run quality:security` -> 성공(출력 없음)

## Interfaces and Dependencies

- Python 품질검사 실행 인터페이스:
  - `apps/api/scripts/run_quality_ci.sh <stage>`
  - `<stage>`는 `lint|format|typecheck|unit|integration|coverage|all`

- Security hygiene 실행 인터페이스:
  - `.github/scripts/security_checks.sh`

- 루트 품질 엔트리포인트:
  - `pnpm run quality:api:ci`
  - `pnpm run quality:node:ci`
  - `pnpm run quality:security`
  - `pnpm run quality:ci`

## Revision Notes

- 2026-02-17 / Codex: 초기 ExecPlan 작성. 로컬/CI 품질검사 싱크 문제를 "명령 단일 소스화" 전략으로 해결하도록 범위와 마일스톤을 정의했다.
- 2026-02-17 / Codex: 계획에 따라 스크립트/워크플로우/package 스크립트를 구현하고 검증 결과(성공/known baseline)를 반영했다.
