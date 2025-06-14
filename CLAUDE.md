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

# 재귀 개선
python3 scripts/prompt_improvement/recursive_prompt_improvement_v3.py [프롬프트] [날짜/all] [반복] [병렬]
```

## 현재 상태
- 최고 성능: v10.3 (적중률 33.3%)
- 목표: 40% 이상

## 참조 문서
- 프로젝트 상세: `docs/project-overview.md`
- API 가이드: `KRA_PUBLIC_API_GUIDE.md`
- Git 규칙: `docs/git-commit-convention.md`
- 재귀 개선: `docs/recursive-improvement-guide.md`

## 중요 규칙
- Python 실행: 항상 `python3` 사용
- 새 문서 생성 전 기존 문서 확인 필수
- 중복 내용 생성 금지