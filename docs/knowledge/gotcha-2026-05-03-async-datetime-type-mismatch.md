---
title: Async path datetime type mismatch
date: 2026-05-03
category: gotcha
tags: [api, db, datetime, async, pr7]
status: active
related: []
---

# Async Path Datetime Type Mismatch

## Context
After PR #7 merge, the async collection endpoint (`POST /collections/{collection_id}/collect-async`) failed with a type error when updating `jobs.started_at`. The synchronous path worked fine.

## Gotcha
Code sends `datetime.timezone.utc` (timezone-aware) to `jobs.started_at`, but the schema defines this column as `TIMESTAMP WITHOUT TIME ZONE` (naive). PostgreSQL rejects the mismatch. The issue only appeared in the async codepath — synchronous collection works because it handles the datetime differently or doesn't trigger the same update.

Error:
```
UPDATE jobs SET started_at=$3::TIMESTAMP WITHOUT TIME ZONE  
값: tzinfo=datetime.timezone.utc (aware)
```

This is a schema/code alignment gap exposed in PR #7's refactored async flow — first time that code path went live.

## Resolution
Immediate workaround: use the synchronous endpoint (`POST /collections`) for production collection. 

Long-term fix: either
- Change schema to `TIMESTAMP WITH TIME ZONE` and update all datetime handling, or
- Remove timezone info before sending to DB (convert aware → naive)

## Evidence
- Sync path: 1 race smoke test passed (HTTP 200, "Collected 1 races")
- Async path: datetime type error on first collection job update
- Only exposed after PR #7 merge when async codepath first ran in production

