# KRA 경마 예측 시스템

한국마사회(KRA) 경마 데이터를 분석하여 삼복연승(1-3위 예측)을 예측하는 AI 시스템입니다.

## 📋 프로젝트 개요

- **목표**: 경마 삼복연승 예측 정확도 향상
- **방법**: KRA 공공 API 활용 및 프롬프트 엔지니어링
- **성과**: 평균 적중률 44% 달성

## 🛠 기술 스택

- Python 3.8+
- Node.js (API 테스트)
- Claude API (예측 모델)
- KRA 공공 데이터 API

## 📁 프로젝트 구조

```
kra-analysis/
├── data/               # 경주 데이터
├── docs/               # 프로젝트 문서
├── examples/           # API 응답 예시
├── prompts/            # 예측 프롬프트
├── scripts/            # 데이터 수집 및 분석 스크립트
└── tests/              # 테스트 코드
```

## 🚀 시작하기

1. 환경 설정
```bash
# 저장소 클론
git clone https://github.com/coyaSONG/kra-analysis.git
cd kra-analysis

# 의존성 설치
pip install -r requirements.txt
npm install
```

2. 환경 변수 설정
```bash
# .env 파일 생성
echo "KRA_SERVICE_KEY=your_api_key_here" > .env
```

3. 데이터 수집
```bash
python scripts/collect_data.py
```

## 📖 주요 문서

- [KRA API 가이드](KRA_PUBLIC_API_GUIDE.md) - KRA 공공 API 상세 사용법
- [프로젝트 개요](docs/project-overview.md) - 전체 프로젝트 설명
- [프롬프트 개선 분석](docs/prompt-improvement-analysis.md) - 예측 프롬프트 최적화 과정

## 📊 성능

- **최종 프롬프트**: v9.0
- **평균 적중률**: 44% (1.32/3마리)
- **완전 적중률**: 10%

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.