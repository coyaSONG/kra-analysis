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
- 9차에 걸친 재귀 개선 프로세스 완료
- 평균 적중률 42% → 44% 향상
- Execution Error 50% → 18% 감소

## 📁 프로젝트 구조

```
kra-analysis/
├── scripts/
│   ├── race_collector/     # 데이터 수집 모듈
│   └── prompt_evaluator/   # 프롬프트 평가 모듈
├── data/
│   ├── races/             # 경주 데이터
│   └── cache/             # API 캐시
├── prompts/               # AI 프롬프트 템플릿
├── docs/                  # 프로젝트 문서
└── examples/              # API 응답 예시
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
# 프롬프트 평가
python3 scripts/evaluate_prompt.py v9.0 prompts/prediction-template-v9.0-final.md 30
```

## 📊 성능

- **평균 적중률**: 44% (3마리 중 평균 1.32마리 적중)
- **완전 적중률**: 10% (3마리 모두 적중)
- **오류율**: 18% (주로 API 타임아웃)

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

1. **Execution Error 해결**: 구체적인 JSON 예시 필수
2. **기권/제외 말 필터링**: win_odds=0인 말 제거
3. **최적 프롬프트**: 간결한 지시 + 명확한 출력 형식
4. **데이터 보강 효과**: 혈통/성적 정보로 예측 정확도 향상 가능

## 🚧 향후 계획

1. 보강된 데이터를 활용한 프롬프트 개선
2. 혈통/성적 정보 활용 전략 개발
3. 앙상블 모델 도입
4. 실시간 배당률 변화 반영

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.