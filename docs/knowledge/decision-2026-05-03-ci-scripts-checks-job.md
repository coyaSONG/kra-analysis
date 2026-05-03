---
title: CI에 scripts-checks 잡 추가 및 pre-commit/pre-push 정렬
date: 2026-05-03
category: decision
tags: [ci, workflow, tooling, monorepo, pnpm]
status: active
related: []
---

# CI에 scripts-checks 잡 추가

## Context

pre-commit, pre-push, CI 파이프라인 설정을 검토한 결과, 의도적 분리와 누락이 섞여 있었습니다. 특히 `packages/scripts` 디렉토리의 lint 및 test 검사가 CI에서 수행되지 않고 있었습니다.

## Decision

`.github/workflows/ci.yml`에 **`scripts-checks` 잡**을 추가합니다:

- **위치**: `python-checks`와 `security` 사이
- **실행**: 병렬 (Postgres/Redis 서비스 불필요)
- **명령**: `pnpm run quality:scripts:ci` (lint + test)
- **Trigger**: 모든 pull request

이로써 monorepo의 `packages/scripts` 패키지가 `root` 레벨 Python 검사들과 동등한 수준의 자동화를 받게 됩니다.

## Evidence

- **파일**: `.github/workflows/ci.yml` (`scripts-checks` 잡 추가)
- **스크립트 설정**: `packages/scripts/package.json` — `quality:scripts:ci` 스크립트 정의 및 turbo 의존성 구성
- **트랜스크립트**: pre-commit/pre-push/CI 비교 분석에서 `packages/scripts`의 CI 검사 공백 식별
