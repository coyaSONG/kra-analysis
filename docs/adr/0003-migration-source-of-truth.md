# SQL migration files are the source of truth for DB schema

DB schema is owned by SQL files in `apps/api/migrations/` plus the `ACTIVE_MIGRATIONS` manifest in `apps/api/infrastructure/migration_manifest.py`. SQLAlchemy `create_all()` is not a production schema source; it serves local dev and test fixtures only.

The 2026-05-03 incident — `007_runtime_db_hardening.sql` was applied to the DB but missing from `ACTIVE_MIGRATIONS` because the file was untracked — exposed how ORM-driven schema loses auditability and lets drift hide silently. Short term: add manifest-vs-filesystem consistency check to CI so the same desync cannot ship. Long term: migrate to Alembic for diffing and rollback.

Promoted from `docs/knowledge/decision-2026-05-03-migration-source-of-truth.md`.
