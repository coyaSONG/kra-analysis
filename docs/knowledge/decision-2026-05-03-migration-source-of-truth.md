---
title: DB Schema source of truth is migration, not ORM
date: 2026-05-03
category: decision
tags: [database, schema, migrations, alembic]
adr: docs/adr/0003-migration-source-of-truth.md
status: active
related: []
---

# DB Schema source of truth is migration, not ORM

## Context
This project has two competing schema sources: SQL migrations (`apps/api/migrations/`) and ORM `create_all()` in Python. The May 3 incident (migration manifest desync on migration 007) exposed the ambiguity. A clear source of truth was needed to prevent future incidents.

## Decision
**Migration files are the canonical source of truth for database schema.**

- **Short-term (2026-05): Strengthen validation** — Add manifest consistency checks to CI to catch desync early (007 incident should not repeat).
- **Long-term (post-2026-05): Adopt Alembic** — Migrate from raw SQL migrations to Alembic for automatic schema tracking, diff detection, and rollback safety.
- **Current state**: ORM `create_all()` exists but should not be the production schema source; it serves local dev only.

## Evidence
- Source: User decision on 2026-05-03 after investigation of migration manifest vs ORM divergence
- Incident: `007_runtime_db_hardening.sql` was in DB but not in `ACTIVE_MIGRATIONS` list; git reset did not catch it (untracked file)
- Trade-off documented: Migrations are harder to review but guarantee auditability; ORM `create_all()` is faster to develop but loses schema history
- Related: `discovery-2026-03-21-architecture-refactoring-legacy-map.md` identified that schema is currently managed ad-hoc

## ADR Candidates
- Migration manifest validation policy (5月 3 post-incident)
- Alembic adoption roadmap and timeline
