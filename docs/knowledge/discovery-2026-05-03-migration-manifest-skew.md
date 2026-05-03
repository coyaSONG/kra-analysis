---
title: PR #7 머지 후 마이그레이션 매니페스트 누락
date: 2026-05-03
category: discovery
tags: [migrations, deployment, database, manifest]
status: active
related: []
---

# PR #7 머지 후 마이그레이션 매니페스트 누락

## Context
PR #7 코드 기반으로 API 서버를 띄우려 했을 때, DB 마이그레이션 검증 단계에서 상태 불일치 발견.

## Finding
`apps/api/migrations/007_runtime_db_hardening.sql` 파일이 물리적으로 존재하고 **DB에도 이미 적용되어 있음**에도 불구하고, `migration_manifest.py`의 `ACTIVE_MIGRATIONS` 리스트에 누락됨.

```
unexpected=['007_runtime_db_hardening.sql']
```

실제 마이그레이션 내용:
- `jobs.task_id` 컬럼 추가
- 4개 인덱스 생성
- `usage_events` RLS 정책 수정

**원인**: git reset 후 untracked 파일로 남거나, PR 머지 과정에서 manifest 업데이트를 놓침.

## Evidence
- Source: `apps/api/migration_manifest.py` — `ACTIVE_MIGRATIONS` 리스트 (001~006만 포함)
- Source: `apps/api/migrations/007_runtime_db_hardening.sql` — 파일 존재, Supabase에 적용됨
- Transcript: "DB와 코드의 마이그레이션 매니페스트가 어긋났습니다"

## Resolution Applied
`ACTIVE_MIGRATIONS`에 `"007_runtime_db_hardening.sql"` 추가 + 파일을 tracked 상태로 전환하여 정합성 회복.

## Lesson
- 마이그레이션은 **코드 변경과 별개**로 DB에 먼저 적용될 수 있음
- manifest와 파일 시스템의 일관성을 머지 전에 항상 검증 필요
