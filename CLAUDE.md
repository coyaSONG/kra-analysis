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
- **KRA_PUBLIC_API_GUIDE.md**: KRA 공식 API 가이드
- **examples/**: API 응답 예시 파일들
  - `api12_response.json/xml`: 경주 상세 정보 (API12_1)
  - `api214_response.json/xml`: 출전 정보 (API214_1)  
  - `api299_response.json/xml`: 경주 결과 (API299)

#### 3. 핵심 스크립트 (/scripts)
- **evaluate_prompt.py**: 프롬프트 평가 메인 스크립트
- **recursive_prompt_improvement.py**: 재귀 개선 프로세스 자동화
- **analyze_and_improve_prompt.py**: 평가 결과 분석 및 개선안 도출
- **evaluate_prompt_debug.py**: 디버그용 평가 스크립트
- **compare_success_fail_data.py**: 성공/실패 경주 데이터 비교 분석
- **find_problematic_chars.py**: 특수문자 문제 분석
- **evaluate_all_races.py**: 전체 경주 평가 스크립트

#### 4. 프롬프트 템플릿 (/prompts)
- **v2.0 ~ v9.0**: 각 버전별 프롬프트 템플릿
- **최종 권장**: `prediction-template-v9.0-final.md`

#### 5. 데이터 (/data)
- **raw/results/2025/**: 2025년 경주 결과 데이터 (절대 삭제 금지)
- **prompt_evaluation/**: 각 프롬프트 버전별 평가 결과
- **full_evaluation/**: 전체 데이터셋 평가 결과

#### 6. 문서 (/docs)
- **recursive-improvement-results.md**: 재귀 개선 프로세스 전체 결과
- **prompt-engineering-guide.md**: 프롬프트 엔지니어링 일반 가이드
- **prompt-improvement-analysis.md**: 경마 예측 특화 개선 분석
- **api-analysis.md**: KRA API 상세 분석
- **data-structure.md**: 데이터 구조 설명
- **claude-code-prompt-best-practices.md**: Claude Code 효과적 사용법

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

### 데이터 전처리
- win_odds가 0인 말은 기권/제외이므로 반드시 제거
- 결과 필드(result, ord, rc_time) 제거 후 예측
- 예측 시에는 win_odds와 plc_odds는 유지

### Python 실행
- 항상 `python3` 명령어 사용
- subprocess 실행 시 timeout 설정 필수 (기본 120초)

## 주의사항

### 절대 삭제 금지
1. **.env 파일** - 환경 변수
2. **/data/raw/results/** - 모든 경주 원본 데이터
3. **KRA_PUBLIC_API_GUIDE.md** - API 공식 문서

### 파일 관리
- 새로운 분석은 docs/ 폴더에 문서화
- 프롬프트는 버전 번호와 함께 prompts/ 폴더에 저장
- 평가 결과는 data/prompt_evaluation/에 자동 저장

## Current Status

### 완료된 작업
- 재귀 개선 프로세스 9차 완료 (v1.0 → v9.0)
- 최적 프롬프트 도출 및 검증
- Execution Error 원인 파악 및 해결
- 전체 프로세스 문서화
- 불필요한 파일 정리 완료

### 향후 개선 방향
1. 남은 18% Execution Error 추가 분석
2. 앙상블 전략 도입 검토
3. 실시간 배당률 변화 반영
4. 기계학습 모델과의 하이브리드 접근