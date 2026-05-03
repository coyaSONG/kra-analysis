# Async work is modeled as DispatchAction → Job → Task

Async work uses three distinct names with three distinct roles:

- **DispatchAction** — the command. A Pydantic request DTO at the router boundary; parameters only, no behavior.
- **Job** — the durable unit. A `Job` row in DB, with the lifecycle `pending → queued → processing → completed/failed`, that survives process restart and is the canonical thing the system owes a result for.
- **Task** — the runtime detail. Currently `asyncio.create_task()` plus a handler dispatch table inside the API process; replaceable with ARQ/Celery/etc. without renaming the domain.

Naming rules: DB models and domain conversation use **Job**; routers accept **DispatchAction**; `task_id` and `handler` stay as implementation vocabulary only — they do not leak into DTOs or doc prose. Legacy v1-era job fields are technical debt to be consolidated, not a permanent parallel track (see ADR-0005).

Industry references: Celery (task + worker + broker), DDD/CQRS (Command + Handler), FastAPI BackgroundTasks. Promoted from `docs/knowledge/decision-2026-05-03-job-task-domain-model.md`.
