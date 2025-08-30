# KRA 경마 예측 시스템 - Turborepo 모노레포

Turborepo를 사용한 모노레포 구조로 재구성된 한국마사회(KRA) 경마 데이터 분석 시스템입니다.

## 🏗️ 모노레포 구조

```
kra-analysis/
├── apps/
│   ├── api/                 # Python FastAPI 서버
│   └── collector/           # Node.js 데이터 수집 서버
├── packages/
│   ├── shared-types/        # 공유 TypeScript 타입 정의
│   ├── scripts/             # 데이터 처리 및 분석 스크립트
│   ├── typescript-config/   # 공유 TypeScript 설정
│   └── eslint-config/       # 공유 ESLint 설정
├── turbo.json              # Turborepo 설정
├── package.json            # 루트 패키지 설정
└── pnpm-workspace.yaml     # pnpm 워크스페이스 설정
```

## 🚀 시작하기

### 필수 조건
- Node.js 18+
- Python 3.11+
- pnpm 9.0+

### 설치

```bash
# pnpm 설치 (없는 경우)
npm install -g pnpm@9

# 의존성 설치
pnpm install

# Python 의존성 설치 (API용)
cd apps/api && uv sync
```

### 개발 환경 실행

```bash
# 모든 앱 개발 모드 실행
pnpm dev

# 특정 앱만 실행
pnpm dev --filter=@apps/api
pnpm dev --filter=@apps/collector

# API와 수집기 동시 실행
pnpm dev --filter=@apps/api --filter=@apps/collector
```

## 📦 앱 및 패키지

### Apps

#### `@apps/api` (Python FastAPI)
- **포트**: 8000
- **설명**: AI 예측 및 비즈니스 로직 처리
- **주요 기능**: 
  - 경주 예측 API
  - 데이터베이스 연동
  - Redis 캐싱

#### `@apps/collector` (Node.js Express)
- **포트**: 3001
- **설명**: KRA 공공데이터 수집
- **주요 기능**:
  - 경주 데이터 수집
  - 데이터 보강
  - API 프록시

### Packages

#### `@repo/shared-types`
- 공유 TypeScript 타입 정의
- API 인터페이스 타입

#### `@repo/scripts`
- 데이터 수집 스크립트
- 프롬프트 평가 및 개선 스크립트

#### `@repo/typescript-config`
- 공유 TypeScript 설정
- base, node, python 프리셋

#### `@repo/eslint-config`
- 공유 ESLint 설정
- Node.js 프리셋

## 🔧 Turborepo 명령어

### 빌드
```bash
# 모든 프로젝트 빌드
pnpm build

# 특정 프로젝트만 빌드
pnpm build --filter=@apps/api
```

### 테스트
```bash
# 모든 테스트 실행
pnpm test

# 특정 프로젝트 테스트
pnpm test --filter=@apps/api
```

### 린트
```bash
# 모든 프로젝트 린트
pnpm lint

# 특정 프로젝트만 린트
pnpm lint --filter=@apps/collector
```

### 클린
```bash
# 캐시 및 빌드 결과물 정리
pnpm clean
```

## 🔄 Turborepo 캐싱

Turborepo는 작업 결과를 캐싱하여 빌드 속도를 향상시킵니다:

- **로컬 캐싱**: `.turbo/` 디렉토리에 저장
- **원격 캐싱**: Vercel 원격 캐시 사용 가능

### 캐시 무효화
```bash
# 캐시 없이 실행
pnpm build --force

# 특정 앱만 캐시 무효화
pnpm build --force --filter=@apps/api
```

## 📊 데이터 수집 워크플로우

1. **데이터 수집**:
   ```bash
   cd packages/scripts
   node race_collector/collect_and_preprocess.js 20250608 1
   ```

2. **데이터 보강**:
   ```bash
   node race_collector/enrich_race_data.js 20250608 1
   ```

3. **예측 실행**:
   ```bash
   # API 서버를 통해
   curl -X POST http://localhost:8000/api/v2/predict \
     -H "Content-Type: application/json" \
     -d '{"date": "20250608", "meet": 1, "race_no": 1}'
   ```

## 🧪 프롬프트 평가

```bash
cd packages/scripts
python3 evaluation/evaluate_prompt_v3.py v10.3 prompts/prediction-template-v10.3.md 30 3
```

## 🔍 디버깅

### Turborepo 로그
```bash
# 자세한 로그 보기
pnpm dev --log-level=debug

# 특정 태스크 로그만 보기
pnpm dev --filter=@apps/api --log-order=stream
```

### 의존성 그래프 확인
```bash
pnpm turbo run build --graph
```

## 🚀 배포

### Docker 빌드
```bash
# API 이미지 빌드
docker build -f apps/api/Dockerfile -t kra-api .

# 수집기 이미지 빌드
docker build -f apps/collector/Dockerfile -t kra-collector .
```

## 📝 추가 정보

- **Turborepo 문서**: https://turbo.build/repo/docs
- **pnpm 문서**: https://pnpm.io/

## 🤝 기여 가이드

1. 새 패키지 추가 시 `packages/` 디렉토리에 생성
2. 새 앱 추가 시 `apps/` 디렉토리에 생성
3. 공통 설정은 패키지로 분리
4. Turborepo 캐싱을 고려한 `outputs` 설정

---

이 프로젝트는 Turborepo를 사용하여 효율적인 모노레포 관리와 빠른 빌드를 제공합니다.