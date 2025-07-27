# uv를 사용한 Python 환경 구성

[uv](https://github.com/astral-sh/uv)는 Rust로 작성된 초고속 Python 패키지 매니저입니다.

## uv 설치

### macOS/Linux
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Windows (PowerShell)
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Homebrew (macOS)
```bash
brew install uv
```

## 프로젝트 설정

### 1. Python 버전 설치 (필요시)
```bash
# Python 3.11 설치
uv python install 3.11

# 설치된 Python 버전 확인
uv python list
```

### 2. 가상환경 생성 및 의존성 설치
```bash
# api 디렉토리로 이동
cd api

# 가상환경 생성 및 의존성 설치 (pyproject.toml 기반)
uv sync

# 개발 의존성 포함 설치
uv sync --dev
```

### 3. 가상환경 활성화
```bash
# uv는 자동으로 .venv를 생성합니다
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate  # Windows
```

## 주요 uv 명령어

### 패키지 관리
```bash
# 패키지 추가
uv add fastapi

# 개발 의존성 추가
uv add --dev pytest

# 패키지 제거
uv remove fastapi

# 의존성 동기화
uv sync

# requirements.txt 생성
uv pip compile pyproject.toml -o requirements.txt
```

### Python 버전 관리
```bash
# Python 버전 설치
uv python install 3.12

# 프로젝트 Python 버전 설정
uv python pin 3.11

# 사용 가능한 Python 버전 확인
uv python list --all-versions
```

### 스크립트 실행
```bash
# 가상환경 내에서 명령 실행
uv run python api/main.py

# FastAPI 서버 실행
uv run uvicorn api.main:app --reload

# 테스트 실행
uv run pytest
```

## 기존 pip 프로젝트에서 마이그레이션

### requirements.txt가 있는 경우
```bash
# requirements.txt를 pyproject.toml로 변환
uv add $(cat requirements.txt)
```

### 기존 가상환경 대체
```bash
# 기존 venv 삭제
rm -rf venv

# uv로 새 환경 생성
uv sync
```

## 성능 비교

- **설치 속도**: pip 대비 10-100배 빠름
- **캐싱**: 효율적인 캐싱으로 재설치 시 더욱 빠름
- **병렬 처리**: 여러 패키지 동시 다운로드/설치

## CI/CD 통합

### GitHub Actions
```yaml
- name: Install uv
  uses: astral-sh/setup-uv@v3
  
- name: Install dependencies
  run: uv sync
  
- name: Run tests
  run: uv run pytest
```

### Docker
```dockerfile
FROM python:3.11-slim

# uv 설치
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml .
RUN uv sync --no-dev

COPY . .
CMD ["uv", "run", "uvicorn", "api.main:app", "--host", "0.0.0.0"]
```

## 장점

1. **속도**: 매우 빠른 패키지 설치
2. **통합성**: pip, venv, pyenv 기능을 하나로 통합
3. **호환성**: pip와 완벽 호환
4. **신뢰성**: Rust로 작성되어 안정적
5. **개발 경험**: 간단하고 직관적인 명령어

## 주의사항

- uv는 `.venv` 디렉토리에 가상환경을 생성합니다
- `pyproject.toml`을 기본 설정 파일로 사용합니다
- 캐시는 `~/.cache/uv`에 저장됩니다