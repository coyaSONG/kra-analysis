---
title: Migration manifest mismatch with untracked file
date: 2026-05-03
category: gotcha
tags: [migrations, db, git, pr7]
status: active
related: []
---

# Migration Manifest Mismatch with Untracked File

## Context
PR #7 merged with 001–006 migrations registered in `ACTIVE_MIGRATIONS`, but DB already had `007_runtime_db_hardening.sql` applied from prior local work. The 007 file remained untracked in git, causing a schema validation error at startup.

## Gotcha
`git reset` does not affect untracked files. When the repo was reset during branch work, `apps/api/migrations/007_runtime_db_hardening.sql` stayed in the filesystem even though its manifest entry was removed. This created a mismatch: DB had the migration applied, but code's `migration_manifest.py` had no record of it. Error: `unexpected=['007_runtime_db_hardening.sql']`.

The 007 migration contains live changes (`jobs.task_id` column + 4 indices + RLS policy), so rollback was too risky.

## Resolution
Added `"007_runtime_db_hardening.sql"` to `ACTIVE_MIGRATIONS` list and converted the file from untracked to tracked. This restored environment parity without rollback.

## Evidence
- Source: DB startup validation, migration_manifest.py comparison with actual files
- 007 contains: `jobs.task_id` column addition, 4 indices, `usage_events` RLS policy
- Lesson: after local DB schema changes, track the migration file even if the branch later resets — the DB state doesn't auto-revert.

