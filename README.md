# KRA 경마 예측 시스템

[![API Coverage](https://codecov.io/gh/OWNER/REPO/branch/main/graph/badge.svg?flag=api)](https://codecov.io/gh/OWNER/REPO)
[![Collector Coverage](https://codecov.io/gh/OWNER/REPO/branch/main/graph/badge.svg?flag=collector)](https://codecov.io/gh/OWNER/REPO)

한국마사회(KRA) 경마 데이터를 분석하여 삼복연승(1-3위 예측)을 수행하는 AI 시스템입니다.

## 🚀 주요 기능

### 1. 데이터 수집 및 전처리

- KRA 공식 API를 통한 실시간 데이터 수집
- 경주 완료 데이터를 경주 전 상태로 자동 전처리
- 5개 API 활용: API214_1(기본), API8_2(말), API12_1(기수), API19_1(조교사), API299(통계)

### 2. 데이터 보강 시스템

- 말: 혈통 정보, 통산/연간 성적, 승률
- 기수: 경력, 나이, 통산/연간 성적
- 조교사: 소속, 승률, 복승률, 연승률
- 7일 캐싱으로 API 호출 최적화

### 3. AI 프롬프트 최적화

- 재귀 개선 프로세스로 v10.3 개발 완료
- 평균 적중률 12.3% → 33.3% 향상 (2.7배)
- 완전 적중률 3.7% → 20% 달성 (5.4배)
- JSON 오류 20% → 0% 완전 해결

## 📁 프로젝트 구조 (Monorepo)

```
kra-analysis/
├─ apps/
│  ├─ api/                     # FastAPI 서버 (v2, Python 3.11+)
│  │  ├─ routers/ services/ models/ middleware/ infrastructure/ tasks/
│  │  └─ tests/                # unit / integration / utils
│  └─ collector/               # 데이터 수집 서버 (TypeScript Node ESM)
│     ├─ src/                  # routes / controllers / services / middleware / utils
│     └─ tests/                # unit / integration / e2e
├─ packages/
│  ├─ scripts/                 # 수집·전처리·평가·프롬프트 개선 스크립트
│  ├─ shared-types/            # 공용 TS 타입
│  ├─ typescript-config/       # TS 공통 설정
│  └─ eslint-config/           # ESLint 공통 설정
├─ docs/                       # 설계·아키텍처·가이드 문서
├─ examples/                   # KRA API 응답 샘플
├─ .github/workflows/          # CI 워크플로우
└─ turbo.json, pnpm-workspace.yaml, package.json
```

참고: API 서버 실행 시 `./data`, `./logs`, `./prompts` 등 런타임 디렉터리는 애플리케이션 시작 시 자동 생성됩니다.

## 🛠️ 설치 및 실행 (Monorepo)

### 1) 의존성 설치

```bash
pnpm i
```

### 2) 개발 서버 실행

```bash
# 전체 앱 동시 실행 (Turbo)
pnpm dev

# Collector만 실행
pnpm -w -F @apps/collector dev

# API만 실행 (uv 기반)
pnpm -w -F @apps/api dev
```

### 3) 테스트

```bash
# 전체 워크스페이스 테스트
pnpm test

# Collector만
pnpm -w -F @apps/collector test

# API만 (직접 실행)
cd apps/api && uv run pytest -q
```

### 4) 데이터 수집

```bash
# 기본 데이터 수집 (API214_1)
node packages/scripts/race_collector/collect_and_preprocess.js 20250608 1

# 데이터 보강 (API8_2, API12_1, API19_1)
node packages/scripts/race_collector/enrich_race_data.js 20250608 1
```

### 5) 예측 실행

```bash
# 프롬프트 평가 (최신 v3 시스템)
python3 scripts/evaluation/evaluate_prompt_v3.py v10.3 prompts/prediction-template-v10.3.md 30 3

# 예측 전용 테스트 (경주 전 데이터만 사용, 결과 비교 없음)
python3 scripts/evaluation/predict_only_test.py prompts/base-prompt-v1.0.md 20250601 10

# 재귀적 프롬프트 개선 (v4)
python3 scripts/prompt_improvement/recursive_prompt_improvement_v4.py prompts/base-prompt-v1.0.md all 5 3

# 파라미터: 버전명, 프롬프트파일, 테스트경주수, 병렬실행수
```

## 📊 성능 현황

### 현재 성과 (base-prompt-v1.0)

- **평균 적중률**: 50% (초기 테스트 2경주 기준)
- **목표**: 70% 이상 완전 적중률

### 이전 성과 (v10.3)

- **평균 적중률**: 33.3% (3마리 중 평균 1.00마리 적중)
- **완전 적중률**: 20% (3마리 모두 적중)
- **오류율**: 0% (JSON 파싱 오류 완전 해결)
- **평균 실행시간**: 56.3초/경주

## 🛠 기술 스택

- Python 3.11+ (FastAPI, AI 예측)
- Node.js 18+ (데이터 수집, ESM)
- Claude API/CLI, KRA 공공 데이터 API

## 🏗️ 아키텍처

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Client    │────▶│ Python FastAPI   │────▶│ Node.js Collector│
└─────────────┘     │   (port 8000)    │     │   (port 3001)   │
                    └──────────────────┘     └────────┬────────┘
                                                      │
                                             ┌────────▼────────┐
                                             │  KRA Public API │
                                             │     (HTTP)      │
                                             └─────────────────┘
```

## 📚 문서

- KRA 공공 API 가이드: `apps/collector/KRA_PUBLIC_API_GUIDE.md`
- 통합 문서 인덱스: `docs/README.md`
  - 1) 시스템 개요/아키텍처: `docs/01-overview-architecture.md`
  - 2) API v2 가이드: `docs/02-api-v2-guide.md`
  - 3) 데이터 모델/구조: `docs/03-data-models.md`
  - 4) 프롬프트/평가: `docs/04-prompt-and-evaluation.md`
  - 5) 로드맵/개발 표준: `docs/05-roadmap-and-standards.md`

### API v2 엔드포인트 예시

```bash
# 수집 작업 트리거(예: 특정 날짜/경마장)
POST http://localhost:8000/api/v2/collection/collect

# 작업 상태 조회
GET  http://localhost:8000/api/v2/jobs/{job_id}
```

## ✅ CI / 품질 체크

- GitHub Actions 워크플로우
  - Python(API v2) 테스트: `.github/workflows/test.yml` — Postgres/Redis 컨테이너로 유닛/통합/커버리지 실행, Codecov 업로드
  - Collector(Node) 테스트: `.github/workflows/collector-test.yml` — ESM/ts-jest, 린트/타입체크/CI 서브셋 테스트, 필요 시 E2E
- 코드 품질: `.github/workflows/code-quality.yml` — Ruff/Black, ESLint/Prettier 체크
  - 보안 스캔: `.github/workflows/security-scan.yml` — Gitleaks, Safety, npm audit-ci, CodeQL, 커스텀 시크릿/`.env`/`data/` 검사

## 🔒 보안 / 환경설정

- 비밀 관리: `.env`는 커밋 금지. 예시는 `apps/api/.env.example`, `apps/collector/.env.example` 참고
- 시크릿 스캔: 루트 `.gitleaks.toml` 구성 + Gitleaks 액션으로 PR 차단
- 환경 변수 요약
  - API: `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `PORT(기본 8000)`, `VALID_API_KEYS`, `KRA_API_KEY`
  - Collector: `PORT(기본 3001)`, `KRA_SERVICE_KEY` 등
- 레이트리밋: API 기본 100req/분(`RateLimitMiddleware`), 필요 시 env로 비활성화/조정 가능

## 🔑 핵심 발견사항

1. **복합 점수 방식 효과적**: 배당률 + 기수 승률 + 말 입상률
2. **Enriched 데이터 필수**: 기본 데이터만으로는 한계 명확
3. **기권/제외 말 필터링**: win_odds=0인 말 제거
4. **간결한 프롬프트**: 200자 이내 + 명확한 JSON 예시
5. **평가 시스템 v3**: 병렬 처리로 3배 빠른 평가

## 🚧 향후 계획

1. 웹 인터페이스 개발

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 참고: 기여자 가이드

프로젝트 구조, 빌드/테스트 명령, 코드 스타일, 보안/설정 팁은 저장소 루트의 AGENTS.md(Repository Guidelines)를 참고하세요.
### Pre-commit 훅 (Ruff/Black)

- 설정 파일: `.pre-commit-config.yaml`
- 설치/적용
  - 설치: `uv run pre-commit install`
  - 수동 실행: `uv run pre-commit run -a`
  - 도구 버전: `ruff==0.13.0`, `black==24.10.0` (uvx로 자동 관리)
