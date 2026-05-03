---
title: _v2 suffix naming (3-track split)
date: 2026-05-03
category: decision
tags: [naming, refactoring, versioning, api]
adr: docs/adr/0005-v2-suffix-policy.md
status: active
related: []
---

# _v2 suffix naming (3-track split)

## Context
`_v2` suffixes appear throughout the codebase (`main_v2.py`, `collection_v2.py`, `jobs_v2.py`, `job_kind_v2` column, `canonical_v2` data format). These suggest "v1 exists elsewhere," but v1 was already deleted (`discovery-2026-03-21-architecture-refactoring-legacy-map.md`). The naming creates confusion and suggests incomplete refactoring.

## Decision
**Split _v2 handling by scope:**

| Scope | Action | Reasoning |
|-------|--------|-----------|
| **API routes** (e.g. `/api/v2/`) | Keep permanently | HTTP versioning is standard; clients depend on it |
| **Modules/files** (e.g. `main_v2.py`, `collection_v2.py`) | Clean up (rename to canonical names) | v1 is gone; these are implementation details not APIs |
| **DB columns** (e.g. `job_kind_v2`) | Remove post-cutover | After migration fully adopted, drop _v2 alias; keep canonical column name only |

**Timeline:**
- Next refactor cycle: rename module files to drop `_v2` (e.g. `collection_v2.py` → `collection.py`)
- After Phase 2 prerace pipeline stabilizes: audit DB columns for `_v2` aliases and remove

## Evidence
- Source: User decision on 2026-05-03 after reviewing module and DB schema structure
- Discovery: `discovery-2026-03-21-architecture-refactoring-legacy-map.md` confirmed v1 code fully removed, making _v2 a historical artifact
- Examples: `apps/api/main_v2.py`, `apps/api/routers/collection_v2.py`, `apps/api/routers/jobs_v2.py`, `apps/api/models/collection_models.py` (job_kind_v2 field)

## Trade-off
- **Clarity gain**: Removes false signal that v1 codepath still exists
- **Cost**: Requires careful rename to avoid breaking imports; should batch with other refactoring

## ADR Candidates
- Module `_v2` suffix cleanup policy
- API path versioning strategy (`/api/v2/` longevity)
