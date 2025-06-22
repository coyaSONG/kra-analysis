# CLAUDE.md

Claude Code 작업 시 필수 지침입니다.

## 프로젝트 개요
한국마사회(KRA) 경마 데이터 분석으로 삼복연승(1-3위) 예측 AI 시스템 개발

## 핵심 원칙

### 1. 프롬프트 작성
- **필수**: `docs/prompt-engineering-guide.md` 준수
- XML 태그 구조화, Chain of Thought, Few-shot 예시 사용

### 2. 데이터 처리
- `win_odds=0` → 기권/제외마 (필터링 필수)
- enriched 데이터 우선 사용
- 상세 구조: `docs/enriched-data-structure.md`

### 3. 파일 관리
- **절대 삭제 금지**: .env, data/, KRA_PUBLIC_API_GUIDE.md
- **Git 제외**: data/ 폴더 (로컬 전용)

## 주요 명령어

```bash
# 데이터 수집
node scripts/race_collector/collect_and_preprocess.js [날짜] [경주번호]
node scripts/race_collector/enrich_race_data.js [날짜] [경주번호]

# 프롬프트 평가
python3 scripts/evaluation/evaluate_prompt_v3.py [버전] [프롬프트파일] [경주수] [병렬수]

# 예측 전용 테스트 (결과 비교 없음)
python3 scripts/evaluation/predict_only_test.py [프롬프트파일] [날짜/all] [제한]

# 재귀 개선 (v4 - 최신)
python3 scripts/prompt_improvement/recursive_prompt_improvement_v4.py [프롬프트] [날짜/all] [반복] [병렬]

# 데이터 패턴 분석
python3 scripts/prompt_improvement/analyze_enriched_patterns.py
```

## 현재 상태
- 기본 프롬프트: base-prompt-v1.0.md (50% 적중률 - 2경주 테스트)
- 최고 성능: prediction-template-v2.2.md (10.9% 적중률 - Few-shot 효과)
- 목표: 70% 이상
- v4 개선 시스템 문제점 발견 (2025-06-22)
  - 프롬프트 내용 개선 없이 examples만 변경
  - 실제 개선은 Few-shot Learning 효과
- v5 시스템 설계 완료 (2025-06-22)
  - 프롬프트 파싱 시스템
  - 인사이트 분석 엔진
  - 동적 재구성 시스템

## 참조 문서
- 프로젝트 상세: `docs/project-overview.md`
- API 가이드: `KRA_PUBLIC_API_GUIDE.md`
- Git 규칙: `docs/git-commit-convention.md`
- 재귀 개선: `docs/recursive-improvement-guide.md`
- v4 시스템: `scripts/prompt_improvement/recursive_prompt_improvement_v4.py`
- v4 문제점 분석: `docs/recursive-improvement-v4-analysis.md`
- 성능 개선 분석: `docs/performance-improvement-analysis.md`
- v5 설계 문서:
  - `docs/prompt-parsing-system-design.md`
  - `docs/insight-analysis-engine-design.md`
  - `docs/dynamic-prompt-reconstruction-design.md`

## 중요 규칙
- Python 실행: 항상 `python3` 사용
- 새 문서 생성 전 기존 문서 확인 필수
- 중복 내용 생성 금지
- Git 커밋 시 Claude 워터마크 제거 (Co-Authored-By 등)