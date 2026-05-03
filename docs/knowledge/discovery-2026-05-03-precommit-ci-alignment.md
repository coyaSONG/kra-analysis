---
title: Pre-commit과 CI 설정 의도적 분리
date: 2026-05-03
category: discovery
tags: [infra, ci-cd, pre-commit, quality-gates]
status: active
related: []
---

# Pre-commit과 CI 설정 의도적 분리

## Context

프로젝트의 quality 보증 파이프라인은 pre-commit hooks (pre-commit, pre-push)와 CI (.github/workflows/quality.yml)로 나뉘어 운영 중입니다. 두 파이프라인 간 범위와 타이밍이 의도적으로 분리되어 있지만, 일부 검사는 누락되었습니다.

## 의도적 분리와 실수

**의도적으로 분리된 영역:**

- **Ruff (lint/format)**: pre-commit은 staged 파일만 autofix (속도 최적화), CI는 전체 코드 검사
- **Gitleaks**: pre-commit은 staged 파일만 (local 보호), CI는 full history (push 차단)
- **mypy**: pre-push와 CI에 양쪽 다 있음 (dual-gate)

**의도하지 않은 누락:**

- commitlint는 로컬 pre-commit-msg에만 있고 CI에 없음 → PR 제목 검증이 CI에서 누락
- pre-commit의 gitleaks는 staged만 검사하므로 이미 커밋된 시크릿은 CI pre-push 이전에 탐지 불가

## Evidence

- Source: `.pre-commit-config.yaml` (staged files, hooks: commit, push)
- Source: `.github/workflows/quality.yml` (full repository scope)
- Configuration table shows Ruff/mypy/gitleaks 범위가 각 파이프라인마다 다름
- mypy 설정: `scripts/mypy_changed.sh` 이름과 달리 full repository 검사 수행

## 권장사항

1. CI에 commitlint 추가하여 PR 제목 검증 일관성 확보
2. Pre-commit gitleaks 범위 확대 검토 (staged → committed 포함)
3. 각 hook의 의도 (속도 vs 완전성)를 문서화하여 향후 유지보수성 개선
