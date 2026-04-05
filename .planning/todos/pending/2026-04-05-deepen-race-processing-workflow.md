---
created: 2026-04-05T04:35:23.266Z
title: Deepen race processing workflow
area: api
files:
  - apps/api/services/collection_service.py:54
  - apps/api/services/collection_enrichment.py:32
  - apps/api/pipelines/stages.py:17
  - apps/api/pipelines/data_pipeline.py:16
---

## Problem

`CollectionService` currently owns too many responsibilities for one race lifecycle: KRA API aggregation, horse detail fetching, failure persistence, odds collection, preprocessing, enrichment, and DB writes. The pipeline layer then re-expresses the same workflow through `CollectionStage`, `PreprocessingStage`, `EnrichmentStage`, and `ValidationStage`, so understanding one race flow requires bouncing across service helpers, stage wrappers, and pipeline factories.

This makes the codebase shallow and seam-heavy. Behavior changes in collection or enrichment tend to touch multiple files, while tests are spread across service-level, helper-level, and pipeline-level assertions instead of a smaller set of boundary tests around one cohesive race-processing module.

## Solution

Create a deeper race-processing module that owns the end-to-end workflow for a race and hides the current orchestration details behind a smaller interface. The module should centralize:

- KRA data fetch coordination and partial-failure policy
- persistence and status transitions for collect/preprocess/enrich
- preprocessing and enrichment orchestration
- boundary-level result reporting for callers

The existing pipeline stages should either become thin adapters over that module or disappear if they add no independent value. Replace the current spread of shallow tests with boundary tests that cover the observable race lifecycle, partial-failure behavior, and persistence outcomes.
