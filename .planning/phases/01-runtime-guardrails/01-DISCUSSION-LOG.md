# Phase 1: Runtime Guardrails - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-05
**Phase:** 01-runtime-guardrails
**Areas discussed:** Health / Degraded Contract, Logging Contract, Authentication / Policy Boundary

---

## Health / Degraded Contract

| Option | Description | Selected |
|--------|-------------|----------|
| Redis required | Redis failure on `/health/detailed` propagates as endpoint failure or unhealthy-only response | |
| HTTP 200 degraded | Redis is optional for health checks; endpoint returns HTTP 200 with explicit degraded component state | ✓ |
| Soft-ignore Redis | Redis problems are hidden and response stays effectively healthy unless DB fails | |

**User's choice:** Recommended default accepted via "시작해" after the proposed default set.
**Notes:** Redis should remain optional for detailed health, but the response must distinguish unavailable/error states rather than reporting false healthy.

---

## Logging Contract

| Option | Description | Selected |
|--------|-------------|----------|
| Keep `LoggingMiddleware` canonical | Move current runtime back to `LoggingMiddleware` and retire `RequestLoggingMiddleware` | |
| Make `RequestLoggingMiddleware` canonical | Absorb request id, redaction, and start/complete/error structured logging into one middleware path | ✓ |
| Keep split responsibilities | Leave `LoggingMiddleware` for tests and `RequestLoggingMiddleware` for runtime body logging | |

**User's choice:** Recommended default accepted via "시작해" after the proposed default set.
**Notes:** Body logging stays limited to small JSON payloads at debug level; default operational logs should be structured start/complete/error events with one request-id source.

---

## Authentication / Policy Boundary

| Option | Description | Selected |
|--------|-------------|----------|
| `APIKey` ORM boundary | Keep router/dependency contracts centered on ORM `APIKey` objects | |
| `AuthenticatedPrincipal` boundary | Use principal objects as the public policy/router contract and keep `APIKey` internal to lookup/update steps | ✓ |
| Hybrid continuation | Keep both `APIKey` and principal types as public-facing dependency results depending on route | |

**User's choice:** Recommended default accepted via "시작해" after the proposed default set.
**Notes:** This phase is about type-contract unification. Raw-key hashing and broader security storage redesign stay out of scope for now.

---

## the agent's Discretion

- Minimal test changes required to prove `HEALTH-01` through `HEALTH-03` can ship with this phase.
- Exact internal request-id ownership implementation as long as one canonical runtime path exists.

## Deferred Ideas

- API key hashing / credential public-id redesign
- durable queue rollout and orphaned job recovery
- migration baseline unification
- broader documentation truth cleanup
