# KRA 경마 예측 시스템

[![API Coverage](https://codecov.io/gh/chsong/kra-analysis/branch/main/graph/badge.svg?flag=api)](https://codecov.io/gh/chsong/kra-analysis)
[![Collector Coverage](https://codecov.io/gh/chsong/kra-analysis/branch/main/graph/badge.svg?flag=collector)](https://codecov.io/gh/chsong/kra-analysis)
[![CI](https://github.com/chsong/kra-analysis/actions/workflows/test.yml/badge.svg)](https://github.com/chsong/kra-analysis/actions/workflows/test.yml)

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

## 📁 프로젝트 구조 (Turborepo Monorepo)

```
kra-analysis/
├─ apps/                           # 애플리케이션
│  ├─ api/                         # FastAPI 서버 (@apps/api)
│  │  ├─ routers/ services/ models/ middleware/ infrastructure/ tasks/
│  │  └─ tests/                    # unit / integration / utils
│  └─ collector/                   # 데이터 수집 서버 (@apps/collector)
│     ├─ src/                      # routes / controllers / services / middleware / utils
│     └─ tests/                    # unit / integration / e2e
├─ packages/                       # 공유 패키지
│  ├─ scripts/                     # 수집·전처리·평가·프롬프트 개선 (@repo/scripts)
│  ├─ shared-types/                # 공용 TypeScript 타입 (@repo/shared-types)
│  ├─ typescript-config/           # TypeScript 공통 설정 (@repo/typescript-config)
│  └─ eslint-config/               # ESLint 공통 설정 (@repo/eslint-config)
├─ docs/                           # 설계·아키텍처·가이드 문서
├─ examples/                       # KRA API 응답 샘플
├─ .github/workflows/              # CI/CD 워크플로우
├─ .turbo/                         # Turborepo 캐시 (자동 생성)
├─ turbo.json                      # Turborepo 설정
├─ pnpm-workspace.yaml             # pnpm 워크스페이스 설정
└─ package.json                    # 루트 패키지 설정
```

**Turborepo 특징:**
- 🚀 **캐싱**: 빌드/테스트 결과 자동 캐싱으로 재실행 시 빠른 속도
- 🔄 **의존성 그래프**: 패키지 간 의존성 자동 추적 및 병렬 실행
- 📊 **변경 감지**: 파일 변경 시에만 해당 패키지 빌드/테스트 실행

참고: API 서버 실행 시 `./data`, `./logs`, `./prompts` 등 런타임 디렉터리는 애플리케이션 시작 시 자동 생성됩니다(경로 기준: `apps/api`).

## 🔐 환경 변수 준비

### 0) `.env` 파일 복사

```bash
cp apps/api/.env.example apps/api/.env
cp apps/collector/.env.example apps/collector/.env
```

필요한 값을 아래 표를 참고해 채워 넣으세요. 운영 환경에서는 **실제 비밀 값**으로 교체하고 `.env` 파일은 절대 커밋하지 마세요.

| 앱 | 필수 변수 | 설명 |
| --- | --- | --- |
| `apps/api` | `DATABASE_URL` | Async SQLAlchemy URL (`postgresql+asyncpg://...`) |
|  | `REDIS_URL` | Redis 캐시 및 세션 저장소 URL |
|  | `SECRET_KEY` | JWT/보안 토큰 서명용 시크릿 |
|  | `KRA_API_KEY` | KRA 공공데이터 API 키 (외부 연동 필요 시) |
|  | `VALID_API_KEYS` | API 인증에 사용되는 키 목록(JSON 배열 또는 콤마 구분) |
|  | `SUPABASE_URL` | Supabase 프로젝트 URL (Supabase 연동 시 필수) |
|  | `SUPABASE_ANON_KEY` | Supabase anon/public 키 |
|  | `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role 키 (서버 전용, 절대 노출 금지) |
| `apps/collector` | `KRA_API_KEY` | 수집 시 사용할 KRA 공공데이터 서비스 키 |
|  | `API_KEY` | Collector 엔드포인트 보호용 클라이언트 키 |
|  | `JWT_SECRET` | 관리자/내부 인증 토큰 서명용 시크릿 |
|  | `REDIS_URL` *(선택)* | 캐시·레이트 리밋에 Redis 사용 시 설정 |

로컬 개발에서는 `.env.example`에 포함된 기본값으로 충분하지만, 운영 배포 시에는 **별도의 보안 저장소(예: GitHub Actions Secrets, AWS Parameter Store)**를 통해 주입하는 것을 권장합니다.

## 🛠️ 설치 및 실행 (Monorepo)

### 1) 의존성 설치

#### Node.js/TypeScript 의존성

```bash
# pnpm 설치 (없는 경우)
npm install -g pnpm@9

# 전체 워크스페이스 의존성 설치
pnpm install
```

#### Python 의존성 (uv 사용)

```bash
# uv 설치 (없는 경우) - https://github.com/astral-sh/uv
curl -LsSf https://astral.sh/uv/install.sh | sh
# 또는 macOS
brew install uv

# Python 3.13 자동 설치 및 가상환경 생성
uv sync

# 개발 의존성 포함 설치
uv sync --group dev

# 특정 워크스페이스만 동기화
uv sync --package kra-scripts
uv sync --package kra-race-prediction-api
```

**uv 주요 명령어:**
- `uv sync` - 의존성 설치 및 lock 파일 업데이트
- `uv add <패키지>` - 새 패키지 추가
- `uv remove <패키지>` - 패키지 제거
- `uv run <명령>` - 가상환경 내에서 명령 실행
- `uv pip list` - 설치된 패키지 목록

### 2) 개발 서버 실행

```bash
# 전체 앱 동시 실행 (Turborepo)
pnpm dev

# 특정 앱만 실행
pnpm dev --filter=@apps/collector
pnpm dev --filter=@apps/api

# 여러 앱 동시 실행
pnpm dev --filter=@apps/api --filter=@apps/collector
```

### 3) 빌드 및 테스트

```bash
# 전체 워크스페이스 빌드
pnpm build

# 전체 워크스페이스 테스트
pnpm test

# 특정 패키지만 실행
pnpm test --filter=@apps/collector
pnpm lint --filter=@apps/api

# 여러 패키지 동시 실행
pnpm test --filter=@apps/api --filter=@apps/collector

# 의존성 그래프 기반 실행 (변경된 패키지만)
pnpm build --filter=...@apps/collector
pnpm test --filter=...@apps/api

# 캐시 관리
pnpm build --force                    # 캐시 무효화 실행
turbo prune @apps/api --docker        # Docker용 프루닝
pnpm turbo run build --dry-run        # 실행 계획 미리보기
```

### 3.1) 개발 시 유용한 명령어

```bash
# 파일 변경 감지 모드 (권장)
pnpm turbo run dev --watch

# 특정 앱만 워치 모드
pnpm turbo run dev --watch --filter=@apps/collector

# 캐시 상태 확인
turbo run build --summarize

# 의존성 그래프 시각화
turbo run build --graph
```

### 4) 데이터 수집

```bash
# 도움말 보기
pnpm --filter=@repo/scripts run collect:help

# 기본 데이터 수집 (API214_1)
pnpm --filter=@repo/scripts run collect:basic 20250608 1

# 데이터 보강 (말/기수/조교사 상세정보)
pnpm --filter=@repo/scripts run collect:enrich 20250608 1

# 경주 결과 수집
pnpm --filter=@repo/scripts run collect:result 20250608 서울 1
```

### 5) 예측 실행

주의: 프롬프트 파일은 저장소에 포함되어 있지 않습니다. 실행 전 `prompts/` 디렉터리를 만들고 필요한 프롬프트 파일을 준비하세요.

```bash
# 도움말 보기
pnpm --filter=@repo/scripts run evaluate:help
pnpm --filter=@repo/scripts run improve:help

# 프롬프트 평가 (최신 v3 시스템)
pnpm --filter=@repo/scripts run evaluate:v3 v10.3 prompts/prediction-template-v10.3.md 30 3

# 예측 전용 테스트 (경주 전 데이터만 사용, 결과 비교 없음)
pnpm --filter=@repo/scripts run evaluate:predict-only prompts/base-prompt-v1.0.md 20250601 10

# 재귀적 프롬프트 개선 (v5 최신)
pnpm --filter=@repo/scripts run improve:v5 prompts/base-prompt-v1.0.md all -i 5 -p 3

# 데이터 패턴 분석
pnpm --filter=@repo/scripts run improve:analyze
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

- Python 3.13+ (FastAPI, AI 예측)
- Node.js 20+ (데이터 수집, ESM)
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
- 시스템 개요: `docs/project-overview.md`
- 통합 API v2 설계: `docs/unified-collection-api-design.md`
- 데이터 구조(경주 전): `docs/data-structure.md`
- 보강 데이터 구조: `docs/enriched-data-structure.md`
- 프롬프트/개선 가이드: `docs/recursive-improvement-guide.md`

### API v2 엔드포인트 예시

```bash
# 수집 작업 트리거(예: 특정 날짜/경마장)
POST http://localhost:8000/api/v2/collection

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
  - Collector: `PORT(기본 3001)`, `KRA_API_KEY` (또는 `KRA_SERVICE_KEY` 지원) 등
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

## ExecPlan 워크플로우

복잡한 기능 추가 또는 큰 리팩터링은 ExecPlan 방식으로 진행합니다.

1. `AGENTS.md`의 `ExecPlans` 섹션을 확인합니다.
2. `.agent/PLANS.md`를 기준으로 실행 계획(ExecPlan)을 작성/갱신합니다.
3. 구현 중에는 계획 문서의 `Progress`, `Surprises & Discoveries`, `Decision Log`, `Outcomes & Retrospective`를 계속 업데이트합니다.

### Pre-commit 훅 (Ruff/Black)

- 설정 파일: `.pre-commit-config.yaml`
- 설치/적용
  - 설치: `uv run pre-commit install`
  - 수동 실행: `uv run pre-commit run -a`
  - 도구 버전: `ruff==0.13.0`, `black==24.10.0` (uvx로 자동 관리)
