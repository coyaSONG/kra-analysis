# `_v2` suffix is API-only; modules and DB columns get cleaned up

The `_v2` suffix only stays where external clients depend on it — HTTP route prefixes like `/api/v2/`. Anywhere else it is a historical artifact, because v1 was already deleted (see `docs/knowledge/discovery-2026-03-21-architecture-refactoring-legacy-map.md`).

| Scope | Action |
|-------|--------|
| API routes (`/api/v2/`) | Keep permanently — this is HTTP versioning, not a refactor smell. |
| Module files (`main_v2.py`, `collection_v2.py`, `jobs_v2.py`) | Rename to canonical names in the next refactor cycle. |
| DB columns (`job_kind_v2`, `lifecycle_state_v2`) | Drop the `_v2` alias after Phase 2 prerace stabilizes; keep the canonical column name only. |

This stops new readers from assuming a v1 codepath still exists, while protecting the one place (HTTP) where the suffix carries real meaning. Promoted from `docs/knowledge/decision-2026-05-03-v2-suffix-strategy.md`.
