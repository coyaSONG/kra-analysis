# PNPM 사용 가이드 - KRA Data Collector

이 프로젝트는 PNPM을 메인 패키지 매니저로 사용합니다.

## 🚀 Quick Start

### 설치
```bash
# 프로젝트 루트에서 모든 의존성 설치
pnpm install

# 특정 워크스페이스만 설치
pnpm install --filter @apps/nodejs-collector
```

### 개발
```bash
# 프로젝트 루트에서 실행
pnpm dev --filter @apps/nodejs-collector

# 또는 앱 디렉토리에서
cd apps/nodejs-collector
pnpm dev
```

### 빌드
```bash
# TypeScript 컴파일
pnpm build --filter @apps/nodejs-collector

# 프로덕션 실행
pnpm start --filter @apps/nodejs-collector
```

### 테스트
```bash
# 모든 테스트 실행
pnpm test --filter @apps/nodejs-collector

# 커버리지 포함
pnpm test:coverage --filter @apps/nodejs-collector
```

## 📦 의존성 관리

### 패키지 추가
```bash
# 일반 의존성
pnpm add express --filter @apps/nodejs-collector

# 개발 의존성
pnpm add -D @types/express --filter @apps/nodejs-collector

# 워크스페이스 의존성
pnpm add @packages/shared-types --workspace --filter @apps/nodejs-collector
```

### 패키지 제거
```bash
pnpm remove express --filter @apps/nodejs-collector
```

### 패키지 업데이트
```bash
# 특정 워크스페이스 업데이트
pnpm update --filter @apps/nodejs-collector

# 모든 워크스페이스 업데이트
pnpm update -r
```

## 🔧 PNPM 명령어

### 워크스페이스 관련
```bash
# 모든 워크스페이스 목록 보기
pnpm ls -r --depth 0

# 특정 워크스페이스에서 스크립트 실행
pnpm --filter @apps/nodejs-collector <script>

# 모든 워크스페이스에서 스크립트 실행
pnpm -r <script>

# 워크스페이스 의존성 확인
pnpm why <package-name>
```

### 캐시 관리
```bash
# 캐시 정리
pnpm store prune

# 캐시 상태 확인
pnpm store status

# 캐시 경로 확인
pnpm store path
```

## 🏗️ 프로젝트 구조

```
kra-analysis/
├── pnpm-workspace.yaml       # PNPM 워크스페이스 설정
├── package.json              # 루트 패키지 설정
├── pnpm-lock.yaml           # 락 파일
├── apps/
│   └── nodejs-collector/    # Node.js API 서버
│       ├── package.json
│       └── .npmrc           # PNPM 설정
└── packages/
    ├── shared-types/        # 공유 타입 정의
    ├── eslint-config/       # ESLint 설정
    └── typescript-config/   # TypeScript 설정
```

## ⚙️ PNPM 설정 (.npmrc)

```ini
# 워크스페이스 패키지 우선 사용
prefer-workspace-packages=true

# Peer 의존성 자동 설치
auto-install-peers=true

# 가상 저장소 디렉토리
virtual-store-dir=node_modules/.pnpm

# 네트워크 타임아웃
network-timeout=60000
```

## 🆚 NPM/Yarn과의 차이점

| NPM/Yarn | PNPM |
|----------|------|
| `npm install` | `pnpm install` |
| `npm run dev` | `pnpm dev` |
| `npm install express` | `pnpm add express` |
| `npm install -D` | `pnpm add -D` |
| `npm uninstall` | `pnpm remove` |
| `npm run dev --workspace=app` | `pnpm dev --filter app` |

## 💡 장점

1. **디스크 공간 절약**: Content-addressable 저장소로 중복 제거
2. **빠른 설치**: 병렬 설치 및 캐싱
3. **엄격한 의존성**: Non-flat node_modules 구조
4. **모노레포 지원**: 우수한 워크스페이스 지원

## 🐛 문제 해결

### PNPM 설치 문제
```bash
# 캐시 정리 후 재설치
pnpm store prune
rm -rf node_modules pnpm-lock.yaml
pnpm install
```

### 의존성 충돌
```bash
# 의존성 트리 확인
pnpm list --depth 2

# 특정 패키지 의존성 확인
pnpm why <package-name>
```

### 워크스페이스 연결 문제
```bash
# 워크스페이스 재연결
pnpm install --force
```

## 📚 추가 자료

- [PNPM 공식 문서](https://pnpm.io)
- [워크스페이스 가이드](https://pnpm.io/workspaces)
- [마이그레이션 가이드](https://pnpm.io/installation#migrating-from-npm-or-yarn)