---
title: Job (durable unit) + DispatchAction (command) terminology
date: 2026-05-03
category: decision
tags: [async, domain-model, terminology, job-queue]
status: active
related: []
---

# Job (durable unit) + DispatchAction (command) terminology

## Context
The codebase has three overlapping terms for async work: `Job` (DB table), `Task` (background operation), and implicit "dispatch" concept. This caused confusion about domain boundaries. Research into industry standards (Celery, DDD/CQRS, FastAPI) showed the appropriate pattern.

## Decision
**Adopt 3-level model:**
1. **DispatchAction** — The command (request DTO, parameters only, no behavior)
2. **Job** — The durable unit (DB record, lifecycle: pending → queued → processing → completed/failed, survives restart)
3. **Task** — Internal implementation detail (asyncio, Handler, worker semantics)

**Naming in code:**
- DB model: `Job` (not `Task`, not `job_v2`)
- Pydantic request: `DispatchAction` (not `JobRequest`)
- Async implementation: use `task_id` and `handler` but refer to the domain concept as `Job`

**v2 fields:**
- Consolidate v1/v2 field divergence in `Job` schema during next refactor
- Treat legacy v1-era fields as technical debt, not permanent parallel tracks

## Evidence
- Source: User investigation on 2026-05-03 after reviewing `apps/api/models/database_models.py:221-282` and `apps/api/routers/jobs_v2.py`
- Industry patterns: Celery (task + worker + broker), DDD/CQRS (Command + Handler), FastAPI (BackgroundTasks)
- Recommendation: Favor CQRS pattern for clarity, with path to durable queue (Celery/ARQ) post-Phase-2

## Trade-off
- **Clarity gains**: Consistent terminology across docs, code, and team conversations
- **Cost**: Requires audit of existing code to align naming (v2 consolidation during next refactor)

## ADR Candidates
- Job terminology v2 cutover policy
- Durable queue adoption strategy (asyncio → ARQ/Celery)
