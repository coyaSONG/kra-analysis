# 📚 Documentation Overview

이 폴더는 KRA 경마 데이터 분석 및 삼복연승 예측 AI 시스템의 문서들을 포함합니다.

## 🏗️ 시스템 아키텍처

### 핵심 문서
- [`project-overview.md`](project-overview.md) - 프로젝트 전체 개요 및 워크플로우
- [`data-structure.md`](data-structure.md) - 데이터 저장 구조 및 관리 방식

### 데이터 시스템
- [`data-enrichment-system.md`](data-enrichment-system.md) - 데이터 보강 시스템 설계
- [`enriched-data-structure.md`](enriched-data-structure.md) - 보강된 데이터 상세 구조
- [`prerace-data-structure.md`](prerace-data-structure.md) - 경주 전 데이터 구조

## 🔧 도구 및 사용법

### 평가 도구
- [`evaluation-tools-guide.md`](evaluation-tools-guide.md) - 평가 도구 완전 가이드
- [`recursive-improvement-guide.md`](recursive-improvement-guide.md) - v5 재귀 개선 시스템 사용법

### CLI 도구 활용
- [`claude-code-prompt-best-practices.md`](claude-code-prompt-best-practices.md) - Claude Code CLI 전문 활용법

## 🧠 프롬프트 엔지니어링

### 가이드
- [`prompt-engineering-guide.md`](prompt-engineering-guide.md) - 프롬프트 작성 모범 사례

### v5 시스템 설계
- [`prompt-parsing-system-design.md`](prompt-parsing-system-design.md) - 프롬프트 파싱 시스템
- [`insight-analysis-engine-design.md`](insight-analysis-engine-design.md) - 인사이트 분석 엔진
- [`dynamic-prompt-reconstruction-design.md`](dynamic-prompt-reconstruction-design.md) - 동적 재구성 시스템

## 📊 성과 및 분석

### 결과 분석
- [`recursive-improvement-results.md`](recursive-improvement-results.md) - 재귀 개선 프로세스 결과
- [`prompt-improvement-june-2025.md`](prompt-improvement-june-2025.md) - 2025년 6월 개선 성과
- [`performance-improvement-analysis.md`](performance-improvement-analysis.md) - 성능 개선 요인 분석

## ⚙️ 개발 규칙

### 규칙 및 컨벤션
- [`git-commit-convention.md`](git-commit-convention.md) - Git 커밋 메시지 규칙

## 📈 현재 상태 (2025-06-22)

### 주요 성과
- ✅ v5 재귀 개선 시스템 구현 완료
- ✅ 경주 결과 수집 시스템 복구 (`get_race_result.js`)
- ✅ 6월 22일 17경기 결과 데이터 수집 완료
- ✅ 평가 시스템 완전 복구

### 현재 성능
- **base-prompt-v1.0**: 50% 적중률 (baseline)
- **목표**: 70% 이상 달성
- **시스템**: v5 재귀 개선으로 자동 최적화 가능

### 다음 단계
1. v5 시스템으로 base-prompt 개선 실행
2. 6월 22일 데이터로 성능 검증
3. 장기적 성능 모니터링
4. 고급 프롬프트 엔지니어링 기법 효과 측정

---
*Last updated: 2025-06-22*