---
title: Autoresearch 병렬 개발로 인한 충돌 위험
date: 2026-05-03
category: gotcha
tags: [autoresearch, parallel-development, rebase-risk, worktree-conflict]
status: active
related: []
---

# Autoresearch 병렬 개발: 광범위 충돌 위험

## Context
로컬 main의 53개 커밋과 origin/main(PR #7)을 분석하던 중 발견된 패턴. autoresearch 패키지가 같은 분기점(`e357434`, 4주 전)에서 두 라인(autoresearch-pilot worktree의 PR #7 vs 로컬 main의 rrx/phase 시리즈)으로 평행 발전하였다.

## 발견
**75/113 파일이 공통 변경 영역** — autoresearch 패키지 자체가 두 라인에서 거의 동일한 파일들을 수정했다.

### 로컬 53 커밋의 분포
| 카테고리 | 커밋 수 | PR #7과의 관계 |
|---|---|---|
| rrx 실험 | 26 | 부분 공통 파일, 별개 흐름 |
| phase-03 문서/구현 | 17 | 거의 로컬 전용 (보존 가치 높음) |
| autoresearch | 5 | **PR #7과 직접 충돌** |
| 기타 (jobs router 등) | 2 | 버그픽스 |

### 충돌 예상 시나리오
단순 `git rebase` 또는 `git merge`를 시도할 경우:
- `packages/scripts/autoresearch/` 전체 영역 충돌 (두 라인이 같은 모듈을 다르게 구현)
- `apps/api/services/`, `apps/api/routes/` 관련 충돌
- `data/contracts/` CSV 추적 문제 (두 라인의 컨트랙트 스키마 차이)
- "거의 전 영역에서 충돌 예상"

## Lesson
- **worktree 기반 병렬 실험은 조기에 main으로 통합**해야 diverge를 피할 수 있음
- **실험 브랜치가 장기화되면** (4주+) 공통 코드 영역의 충돌 가능성이 기하급수적으로 증가
- 향후 유사한 상황에서는 **cherry-pick 선별 적용** 또는 **강제 재구현**이 단순 merge보다 낫을 수 있음

## Evidence
- 로컬 vs origin/main diff 분석: 75개 파일이 공통 변경
- 분기점: `e357434` (4주 전, 2026-04-06 경)
- 트랜스크립트 라인 126-140: "거의 전 영역에서 충돌 예상"
