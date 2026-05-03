---
title: 비동기 수집 경로의 timezone 타입 미스매치
date: 2026-05-03
category: gotcha
tags: [async, datetime, database, timezone, jobs]
status: active
related: []
---

# 비동기 수집 경로의 timezone 타입 미스매치

## Context
PR #7 머지 후 비동기 경로로 경주 데이터를 수집하려 했을 때, `jobs.started_at` 컬럼 타입 불일치로 인한 DB 에러 발생.

## Gotcha
코드는 timezone-aware datetime (UTC)을 `jobs.started_at`에 전달하려 하는데, 해당 컬럼은 `TIMESTAMP WITHOUT TIME ZONE` (naive)로 정의됨.

```sql
UPDATE jobs SET started_at=$3::TIMESTAMP WITHOUT TIME ZONE  
값: tzinfo=datetime.timezone.utc (aware)
```

**동기 경로는 정상 작동**하므로, 비동기 오류는 최근 리팩터링 과정에서 처음 노출된 것.

## Evidence
- Source: `apps/api/migrations/007_runtime_db_hardening.sql` — `jobs.task_id` 추가, `jobs` 테이블 변경
- Transcript quote: "DB 타입 미스매치 발견... 비동기만 datetime 버그"
- Workaround: 동기 경로(`POST /api/v2/collection/`)로 우회 (현재 상태)

## Next Steps
- `jobs.started_at` 컬럼을 `TIMESTAMP WITH TIME ZONE`으로 변경하거나
- 비동기 수집 코드에서 naive datetime으로 변환 필요
