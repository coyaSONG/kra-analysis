# KRA 경마 예측 시스템

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

## 📁 프로젝트 구조

```
kra-analysis/
├── scripts/
│   ├── race_collector/        # 데이터 수집 모듈
│   ├── evaluation/           # 평가 시스템 v3
│   └── prompt_improvement/    # 프롬프트 개선 도구
├── data/
│   ├── races/                # 경주 데이터
│   ├── cache/                # API 캐시
│   └── prompt_evaluation/     # 평가 결과
├── prompts/                  # AI 프롬프트 템플릿
├── docs/                     # 프로젝트 문서
└── examples/                 # API 응답 예시
```

## 🛠️ 설치 및 실행

### 환경 설정

```bash
# 저장소 클론
git clone https://github.com/coyaSONG/kra-analysis.git
cd kra-analysis

# 환경 변수 설정
echo "KRA_SERVICE_KEY=your_api_key_here" > .env

# Node.js 패키지 설치
npm install

# Python 패키지 설치
pip install -r requirements.txt
```

### 데이터 수집

```bash
# 기본 데이터 수집 (API214_1)
node scripts/race_collector/collect_and_preprocess.js 20250608 1

# 데이터 보강 (API8_2, API12_1, API19_1)
node scripts/race_collector/enrich_race_data.js 20250608 1
```

### 예측 실행

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

- Python 3.8+
- Node.js 18+ (API 클라이언트)
- Claude API (예측 모델)
- KRA 공공 데이터 API

## 📚 문서

### 핵심 문서

- [KRA API 가이드](KRA_PUBLIC_API_GUIDE.md) - KRA 공공 API 상세 사용법
- [프로젝트 개요](docs/project-overview.md)
- [데이터 보강 시스템](docs/data-enrichment-system.md)
- [보강된 데이터 구조](docs/enriched-data-structure.md)

### 분석 및 전략

- [API 분석](docs/api-analysis.md)
- [데이터 구조](docs/data-structure.md)
- [프롬프트 개발 전략](docs/prompt-development-strategy.md)
- [재귀 개선 결과](docs/recursive-improvement-results.md)

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

