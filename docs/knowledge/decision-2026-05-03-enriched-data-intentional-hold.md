---
title: enriched_data Pipeline is Intentionally On Hold
date: 2026-05-03
category: decision
tags: [data-lifecycle, pipeline, architecture]
status: active
related: [decision-2026-03-15-skip-pipeline-overhaul.md]
---

# enriched_data Pipeline: Intentional Hold (Pending A/B Verification)

## Context
The data lifecycle design was ambiguous: `basic_data` (collection stage) vs `enriched_data` (preprocessing/feature stage) vs canonical-v2 (final). Question arose whether `enriched_data` is an "active concept" (part of current pipeline) or "on hold" (planned but deferred). Caused confusion when reviewing CONTEXT.md and architecture docs.

## Decision
- **basic_data**: Active — used in current production pipeline (collection → storage in DB)
- **enriched_data**: Intentionally **on hold** — awaiting A/B verification (feature engineering benefit validation) before full activation
- **canonical-v2**: TBD (three-layer architecture deferred until enriched_data A/B gate passes)

### Implication
- NULL values in enriched_data columns are **expected and normal** during hold period
- Do NOT backfill enriched_data until A/B results confirm the feature lift
- Future pipeline overhauls should reference this decision when planning enrichment stage activation

## Evidence
- Source: User session clarification 2026-05-03 (selected "Story A")
- Ref: Existing knowledge `decision-2026-03-15-skip-pipeline-overhaul.md` (related freeze on broader refactoring; enriched_data hold is narrower scope)
- Architecture: `apps/api/services/collector/` (collects to basic_data; enriched_data initialization pending)
