# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

한국마사회(KRA) 경마 데이터를 분석하여 삼복연승(1-3위에 들어올 3마리 예측)을 예측하는 AI 시스템 개발 프로젝트입니다.

## 프로젝트 구조

### 핵심 파일 및 폴더

#### 1. 설정 파일
- **CLAUDE.md** (this file): 프로젝트 지침 및 개발 가이드
- **.env**: 환경 변수 (API 키 등) - 절대 삭제 금지
- **requirements.txt**: Python 패키지 의존성

#### 2. API 관련
- **KRA_PUBLIC_API_GUIDE.md**: KRA 공식 API 가이드 (5개 API)
- **examples/**: API 응답 예시 파일들
  - `api214_response.json/xml`: 출전 정보 (API214_1)  
  - `api299_response.json/xml`: 경주 결과 (API299)
  - 추가 API: API8_2(말), API12_1(기수), API19_1(조교사)

#### 3. 핵심 스크립트 (/scripts)
- **evaluate_prompt.py**: 프롬프트 평가 메인 스크립트
- **recursive_prompt_improvement.py**: 재귀 개선 프로세스 자동화
- **analyze_and_improve_prompt.py**: 평가 결과 분석 및 개선안 도출
- **evaluate_prompt_debug.py**: 디버그용 평가 스크립트
- **evaluate_all_races.py**: 전체 경주 평가 스크립트

#### 3-1. 데이터 수집 (/scripts/race_collector)
- **collect_and_preprocess.js**: API214_1 데이터 수집 및 전처리
- **api_clients.js**: API8_2, API12_1, API19_1 클라이언트 및 캐싱
- **enrich_race_data.js**: 데이터 보강 (말/기수/조교사 상세정보 추가)
- **smart_preprocess_races.py**: 스마트 전처리 (완료된 경주만)

#### 4. 프롬프트 템플릿 (/prompts)
- **v2.0 ~ v9.0**: 각 버전별 프롬프트 템플릿
- **최종 권장**: `prediction-template-v9.0-final.md`

#### 5. 데이터 (/data)
- **races/**: 전처리된 경주 데이터 (YYYY/MM/DD/venue 구조)
  - `*_prerace.json`: 기본 전처리 데이터
  - `*_enriched.json`: 상세정보 보강 데이터
- **cache/**: API 캐시 (horses/, jockeys/, trainers/)
- **prompt_evaluation/**: 각 프롬프트 버전별 평가 결과
- **full_evaluation/**: 전체 데이터셋 평가 결과

#### 6. 문서 (/docs)
- **recursive-improvement-results.md**: 재귀 개선 프로세스 전체 결과
- **prompt-engineering-guide.md**: 프롬프트 엔지니어링 일반 가이드
- **prompt-improvement-analysis.md**: 경마 예측 특화 개선 분석
- **api-analysis.md**: KRA API 상세 분석
- **data-structure.md**: 데이터 구조 설명
- **data-enrichment-system.md**: 데이터 보강 시스템 설명
- **enriched-data-structure.md**: 보강된 데이터 구조 상세
- **claude-code-prompt-best-practices.md**: Claude Code 효과적 사용법

#### 7. 작업 관리 (/tasks)
- **todo.md**: 프로젝트 작업 관리 (모든 작업 기록 필수)

## 재귀 개선 프로세스 요약

### 핵심 발견사항
1. **Execution Error의 원인**
   - ❌ 프롬프트 길이
   - ✅ 구체적인 JSON 예시 부재
   - ✅ 기권/제외 말 (win_odds=0) 데이터

2. **최적 프롬프트 구조**
   - 간결한 지시 (200자 이내)
   - 명확한 JSON 출력 예시 필수
   - 1-2위 필수 + 3-5위 중 선택 전략

### 성능 추이
- v1.0: 테스트 안됨
- v3.1: 평균 1.26/3 (42%)
- v5.0: 평균 1.40/3 (47%) ← 최고 성능
- v9.0: 평균 1.32/3 (44%) ← 최종 선택

### 최종 성과
- 평균 적중률: 42% → 44%
- 완전 적중률: 0% → 10%
- 오류율: 50% → 18%

## 개발 가이드라인

### 작업 관리 (중요!)
1. **모든 신규 작업은 tasks/todo.md에 먼저 기록**
   - 작업 시작 전 todo.md 확인 및 업데이트
   - 진행 상황을 실시간으로 반영
   - 완료된 작업은 날짜와 함께 완료 섹션으로 이동
2. **작업 단위가 명확할 때마다 todo.md 활용**
   - 데이터 수집, API 개발, 문서화, 버그 수정 등
   - 구체적이고 측정 가능한 목표로 작성
   - 관련 파일이나 커밋은 링크로 연결

### 프롬프트 개발 시
1. 구체적인 JSON 예시를 반드시 포함
2. 프롬프트는 간결하게 (200자 이내 권장)
3. 기권/제외 말(win_odds=0) 필터링 필수
4. 시장 평가(배당률) 중심 전략 사용

### 평가 프로세스
```bash
# 단일 프롬프트 평가
python3 scripts/evaluate_prompt.py v9.0 prompts/prediction-template-v9.0-final.md 30

# 디버그 모드 실행
python3 scripts/evaluate_prompt_debug.py [프롬프트파일] [경주파일]

# 전체 경주 평가
python3 scripts/evaluate_all_races.py [프롬프트파일] [버전명]
```

### 데이터 수집 및 전처리

#### 기본 데이터 수집
```bash
# API214_1로 경주 데이터 수집
node scripts/race_collector/collect_and_preprocess.js 20250608 1
```

#### 데이터 보강
```bash
# 말/기수/조교사 상세정보 추가
node scripts/race_collector/enrich_race_data.js 20250608 1
```

#### 전처리 규칙
- win_odds가 0인 말은 기권/제외이므로 반드시 제거
- 결과 필드(ord, rcTime) 0으로 초기화
- 배당률(winOdds, plcOdds)은 유지
- 보강 데이터는 `_enriched.json`으로 저장

### Python 실행
- 항상 `python3` 명령어 사용
- subprocess 실행 시 timeout 설정 필수 (기본 120초)

## 주의사항

### 절대 삭제 금지
1. **.env 파일** - 환경 변수
2. **/data/races/** - 모든 경주 데이터
3. **/data/cache/** - API 캐시 (성능 중요)
4. **KRA_PUBLIC_API_GUIDE.md** - API 공식 문서

### 파일 관리
- 새로운 분석은 docs/ 폴더에 문서화
- 프롬프트는 버전 번호와 함께 prompts/ 폴더에 저장
- 평가 결과는 data/prompt_evaluation/에 자동 저장
- 경주 데이터는 data/races/YYYY/MM/DD/venue/ 구조로 저장
- API 캐시는 data/cache/에 7일간 보관

## Current Status

### 완료된 작업
- 재귀 개선 프로세스 9차 완료 (v1.0 → v9.0)
- 최적 프롬프트 도출 및 검증
- Execution Error 원인 파악 및 해결
- 전체 프로세스 문서화
- 데이터 수집/전처리 시스템 구축
- 데이터 보강 시스템 구현 (API8_2, API12_1, API19_1)
- 캐싱 시스템 구현 (7일 유효)

### 향후 개선 방향
1. 보강된 데이터를 활용한 프롬프트 개선
2. 혈통/성적 정보 활용 전략 개발
3. 남은 18% Execution Error 추가 분석
4. 앙상블 전략 도입 검토
5. 실시간 배당률 변화 반영
6. 기계학습 모델과의 하이브리드 접근