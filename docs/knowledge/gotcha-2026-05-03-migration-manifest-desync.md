---
title: Migration manifest와 DB 상태 불일치
date: 2026-05-03
category: gotcha
tags: [migrations, database, git-reset, startup-failure]
status: active
related: []
---

# Migration manifest와 DB 상태 불일치

## Context
PR #7 머지 후 API 서버 시작 시 `007_runtime_db_hardening.sql` 마이그레이션 미스매치 발생. DB에는 이미 007이 적용되어 있었으나 코드의 `migration_manifest.py`에는 007이 등록되지 않아 startup 실패.

## Gotcha
**Untracked 파일은 `git reset` 대상이 아니기 때문에, 이전 작업 브랜치에서 생성된 마이그레이션 SQL 파일이 디렉토리에 남아있을 수 있음.** 로컬 git 히스토리를 reset하거나 브랜치를 변경한 후, 새로운 마이그레이션이 추가될 때 manifest와 DB 상태가 어긋날 수 있음.

## Evidence
- `apps/api/migrations/007_runtime_db_hardening.sql` — untracked 상태로 디렉토리 존재
- `apps/api/alembic/versions/migration_manifest.py`:ACTIVE_MIGRATIONS에 001~006만 등록 (007 누락)
- 서버 로그: `unexpected=['007_runtime_db_hardening.sql']` 에러
- DB 상태: 007 마이그레이션 이미 적용됨 (이전 작업 세션에서 수동 적용)

## Resolution Applied
`ACTIVE_MIGRATIONS` 리스트에 `"007_runtime_db_hardening.sql"` 추가 후 파일을 tracked 상태로 전환
