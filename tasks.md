# 프로젝트 작업 목록 (업데이트: 2025-09-14)

아래 체크리스트는 현재 레포 상태 점검 결과를 바탕으로 정리된 우선순위 작업 항목입니다. 각 항목 완료 시 체크해주세요.

## P0 — 즉시 수정 필요 (Failing/Flaky 방지)
- [x] Collector 테스트 버그 수정: `TEST_DATA.meetCode` → `TEST_DATA.meet` (파일: `apps/collector/tests/integration/kra-api-integration.test.ts`).
- [x] Collector 커버리지 활성화: CI에서 `jest --coverage` 실행 또는 `pnpm -F @apps/collector run test:coverage` 사용. `jest.config.js`의 `collectCoverage`를 CI에서만 활성화하도록 조정.
- [x] Python 커버리지 임계치 정렬: `.github/workflows/test.yml`의 `--cov-fail-under=30` 제거 및 `.coveragerc` 기준(제안: 70% 또는 팀 합의치)으로 통일.
- [x] 문서/안내 최신화: 루트 `README.md`와 관련 문서의 경로·명령을 모노레포(`apps/*`)와 v2 엔드포인트(`/api/v2`) 기준으로 업데이트.
- [x] 루트 `pyproject.toml` 스타일 설정 정리: Black line length 88 및 Ruff 채택으로 일원화(중복 flake8/isort/pylint 제거 또는 `apps/api` 기준으로 맞춤).

## P1 — CI/빌드 최적화
- [x] Node 워크플로 캐시 적용: `actions/setup-node@v4`에 `cache: 'pnpm'` 추가 및 일관된 워크스페이스 설치 전략 적용. (변경: `.github/workflows/collector-test.yml`, `code-quality.yml`)
- [x] Python 워크플로 uv 전환: `astral-sh/setup-uv@v3` 사용, `uv sync`로 의존성 설치(현 `requirements.txt` 기반 설치 제거). (변경: `.github/workflows/test.yml`)
- [x] API Dockerfile 정비: `apps/api/Dockerfile`을 `pyproject.toml`/uv 기반 설치로 전환(이미지 빌드 속도·일관성 개선). (변경: `apps/api/Dockerfile`)
- [x] Collector Docker 베이스 상향: `node:18-alpine` → `node:22-alpine`로 갱신(런타임/CI 노드 버전과 정합). (변경: `apps/collector/Dockerfile`)
- [x] 코드 품질 워크플로 경로/도구 수정: `scripts/` → `packages/scripts/`로 검사 경로 수정, Node는 `pnpm -w run lint`, Python은 `ruff check`/`black --check` 사용. (변경: `.github/workflows/code-quality.yml`)

## P1 — 구현 안정화/리팩터링
- [x] API 엔트리포인트 정리: `apps/api/main.py` 제거 또는 명시적 deprecated 주석 추가(표준은 `main_v2.py`).
- [x] Celery 의존성 느슨화: `apps/api/services/job_service.py`에서 Celery 임포트를 지연/가드 처리하여 비구성 환경에서 ImportError 방지.
- [x] Redis 설정 개선(Collector): `utils/redis.ts`가 `REDIS_URL` 전체 문자열 파싱을 우선 사용하도록 개선(현재 host/port만 사용). (변경: `apps/collector/src/utils/redis.ts`)

## P2 — 레포 정리/청소
- [x] `.gitignore` 보강: `**/*.tsbuildinfo`, `apps/collector/{cache,logs,tmp}/`, `coverage/`, `htmlcov/` 등 추가.
- [x] 커밋된 빌드 산출물 제거: `packages/shared-types/tsconfig.tsbuildinfo` 삭제 후 무시 처리.
- [x] Node/TS 설정 점검: 워크스페이스 전반 `module`/`moduleResolution`(NodeNext) 및 Node 20/22 호환성 재확인.

## P2 — 테스트/문서 보강
- [x] `apps/api/test_api.py`의 v1 경로를 v2로 갱신하거나 legacy 스크립트로 명시.
- [x] Codecov 설정 보강: `collector`/`api` 플래그, 배지 추가 및 업로드 경로 확인.
- [x] 통합/E2E 테스트 게이팅 정비: 시크릿(`KRA_SERVICE_KEY`) 존재 시에만 외부 호출 테스트가 실행되도록 조건 일관성 확인.

## 결정 필요(팀 합의 후 일괄 반영)
- [x] 커버리지 임계치 최종 확정: Node/Python 모두 80%로 통일 → 설정 및 워크플로 반영 완료.
- [ ] Python 린트 도구 정책: flake8 유지 여부 또는 Ruff 단일화 결정(워크플로와 설정 파일 동기화).

## 선택(미래 개선)
- [ ] pnpm workspace constraints 도입(Typescript/ESLint 버전 상한·하한 고정).
- [ ] Renovate/Bot 도입으로 의존성 자동 업데이트 파이프라인 구축.

---
본 목록은 레포 점검 결과를 반영한 실행 계획 초안입니다. 우선 P0 항목부터 PR로 분리하여 진행하는 것을 권장합니다.
