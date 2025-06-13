# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

한국마사회(KRA) 경마 데이터를 분석하여 삼복연승(1-3위에 들어올 3마리 예측)을 예측하는 AI 시스템 개발 프로젝트입니다.

## 프로젝트 구조

### 📁 핵심 디렉토리

```
kra-analysis/
├── scripts/                 # 실행 스크립트
│   ├── evaluation/         # 평가 시스템 ⭐
│   ├── race_collector/     # 데이터 수집/처리 ⭐
│   └── prompt_improvement/ # 프롬프트 개선
├── prompts/                # 프롬프트 템플릿
├── data/                   # 데이터 저장소
│   ├── races/             # 경주 데이터
│   ├── cache/             # API 캐시
│   └── prompt_evaluation/ # 평가 결과
├── docs/                   # 문서화
└── tasks/                  # 작업 관리
```

### 🔧 주요 파일

#### 설정 파일
- **CLAUDE.md** (this file): 프로젝트 지침
- **.env**: 환경 변수 (API 키) - 절대 삭제 금지
- **requirements.txt**: Python 패키지

#### API 문서
- **KRA_PUBLIC_API_GUIDE.md**: KRA 공식 API 가이드
- **examples/**: API 응답 예시

## 🚀 현재 워크플로우

### 1. 데이터 수집 및 처리
```bash
# 기본 데이터 수집
node scripts/race_collector/collect_and_preprocess.js 20250608 1

# 데이터 보강 (말/기수/조교사 상세정보)
node scripts/race_collector/enrich_race_data.js 20250608 1
```

### 2. 프롬프트 평가
```bash
# 최신 평가 시스템 (v3) - enriched 데이터 사용
python3 scripts/evaluation/evaluate_prompt_v3.py v10.3 prompts/prediction-template-v10.3.md 30 3
```

### 3. 프롬프트 개선
```bash
# 재귀적 개선
python3 scripts/prompt_improvement/recursive_prompt_improvement.py
```

## 📊 현재 성과

### 최신 프롬프트: v10.3 (2025.06.13)
- **평균 적중률**: 33.3% (1.00/3)
- **완전 적중률**: 20%
- **오류율**: 0%
- **개선폭**: v9.0 대비 2.7배 향상

### 핵심 발견사항
1. ✅ 구체적인 JSON 예시 필수
2. ✅ 간결한 프롬프트 (200자 이내)
3. ✅ 기권/제외 말(win_odds=0) 필터링
4. ✅ 복합 점수 방식 (배당률+기수승률+말입상률)
5. ✅ Enriched 데이터 활용이 핵심

## 💡 개발 가이드라인

### 데이터 처리 규칙
- `win_odds=0`인 말은 기권/제외 → 반드시 제거
- enriched 데이터 우선 사용
- 결과는 `top3_*.json` 형식으로 캐싱

### Python 실행
- 항상 `python3` 사용
- Claude Code CLI 호출 시 환경변수 설정:
  ```python
  env = {
      'BASH_DEFAULT_TIMEOUT_MS': '120000',
      'DISABLE_INTERLEAVED_THINKING': 'true'
  }
  ```

### 파일 관리
- **절대 삭제 금지**: .env, data/races/, data/cache/, KRA_PUBLIC_API_GUIDE.md
- **자동 저장 경로**:
  - 경주 데이터: `data/races/YYYY/MM/DD/venue/`
  - 평가 결과: `data/prompt_evaluation/`
  - API 캐시: `data/cache/` (7일 유효)

### Git 관리 (중요!)
- **data/ 폴더는 절대 git에 push하지 않음**
  - 경주 데이터, 평가 결과, API 캐시 등은 로컬에서만 관리
  - .gitignore에 이미 설정되어 있음
  - 실수로 추가되지 않도록 주의

## 🎯 최근 완료 (2025.06.13)

### 1. v10.3 프롬프트 개발 완료
- ✅ 복합 점수 방식 도입
- ✅ 평균 적중률 33.3% 달성
- ✅ JSON 오류 0%로 개선

### 2. 평가 시스템 v3 완성
- ✅ enriched 데이터 지원
- ✅ 병렬 처리 (3개 동시 실행)
- ✅ Claude Code CLI 최적화
- ✅ stream-json 형식 지원

## 📋 다음 단계

1. **v10.3 대규모 검증**: 더 많은 데이터로 성능 확인
2. **복합 점수 최적화**: 가중치 미세 조정
3. **혈통 정보 활용**: faHrNo, moHrNo 데이터 활용
4. **앙상블 전략**: v10.3 + 다른 전략 조합

## ⚠️ 주의사항

### API 사용
- SSL 문제로 Python 대신 Node.js 사용
- API 호출 간 적절한 딜레이 필요
- 캐싱을 통한 API 호출 최소화

### 작업 관리
- 모든 작업은 tasks/todo.md에 기록
- 진행 상황 실시간 업데이트
- 완료 시 날짜와 함께 이동

### Git 커밋 규칙
- Conventional Commits 사용 ([상세 가이드](docs/git-commit-convention.md))
- 형식: `type(scope): description`
- 예: `feat(prompt): add v10.3 composite scoring`