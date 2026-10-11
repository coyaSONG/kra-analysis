# Inspect Actual Top-Three Result Readiness

This living ExecPlan follows `.agent/PLANS.md`.

## Purpose / Big Picture

Identify which captured results contain an ordinary, unique first/second/third
finish and which need review before prediction evaluation. Preserve every
scheduled race, including void races and missing results. This is evidence
inspection, not a backtest or approval of official finality. The user's target
remains one unordered three-horse selection per race, 70% exact success over the
entire pre-race-frozen universe.

## Progress

- [x] Inspect the existing result normalizer and schedule-left-joined audit.
- [x] Add per-race rank/identity diagnostics without changing collection or scoring.
- [x] Test exceptional ranks, missing data, duplicate identities, and all-race totals: 84 focused and 434 regression tests passed.
- [x] Replay the six pinned October 9-11 captures and record findings: 50 races retained, 37 ordinary observations and 13 requiring review; repeat is byte-identical.
- [ ] Commit, push, verify required CI and ordinary merge.

## Surprises & Discoveries

The existing audit establishes row-count reconciliation only. A void race can
have the correct count and remain reconciled, without any usable finish ranks.
That behavior is preserved; the new diagnostic is explicitly separate.

## Decision Log

Decision: use conservative diagnostic blockers, not a new settlement policy.
Rationale: cancellation, dead-heat and official finality contracts are not yet
reviewed. Missing information must not silently become a scored subset.
Date/Author: 2026-10-11, Codex.

Decision: extend the existing audit and tests additively.
Rationale: original replay, pin checks, CLI and CI already exist. No new service,
dependency, database change, model training, or prediction registration is needed.
Date/Author: 2026-10-11, Codex.

## Context and Orientation

`packages/scripts/shared/kra_result_history.py` normalizes API214 observations
without assuming meanings for special result codes. `ranked_finish_observed`
means a numeric rank 1-20, positive elapsed time and no exceptional note, not a
verified official final result. `packages/scripts/autoresearch/kra_result_population_audit.py`
replays pinned originals and keeps the entire official schedule as the report's
base list. Its `reconciled_observation_population` concerns counts only.

## Plan of Work

Add `inspect_top3` to the existing audit. It accepts normalized rows and the
scheduled runner count and returns blockers, a candidate unordered three-ID
set when unique ranks 1/2/3 are observed, and an observation status. Any unresolved
runner, missing row, invalid/duplicate identity, duplicate rank or rank gap
requires review. Even an ordinary observation never certifies finality or counts
as target evidence. Candidate IDs are diagnostic and can coexist with blockers.

## Milestones

First, demonstrate pure diagnostic behavior through table-driven tests in
`packages/scripts/autoresearch/tests/test_kra_result_population_audit.py`. Second,
replay the existing six pinned captures using the existing CLI and document the
all-race status counts. Third, ship this independently tested research increment.

## Concrete Steps

From the isolated repository root run:

    .venv/bin/python -m pytest -q packages/scripts/autoresearch/tests/test_kra_result_population_audit.py packages/scripts/autoresearch/tests/test_kra_result_snapshot.py -o addopts=''
    PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.kra_result_population_audit --plan .cache/autoresearch/prior-results/population-plan.json --output .cache/autoresearch/prior-results/population-top3-audit.json

The real replay should retain 50 races and 510 rows, with nine count mismatches,
and exit 2 because the original population reconciliation remains false. Inspect
top3 statuses separately. Run Ruff check/format check on both changed Python files.

## Validation and Acceptance

Tests must retain void/missing races, reject duplicate top ranks and horse IDs,
report lower-rank gaps/ties, tolerate normalized numeric strings, and preserve
all-race status totals. Existing capture/replay tests must remain green. Replay
again into a fresh output and require byte-identical reports. No success rate is
printed. Original raw sources, champion, training reviews and forward DB stay unchanged.

## Idempotence and Recovery

Audit outputs use exclusive creation. Use a new output filename to repeat.
No captured file is overwritten. A failed pin remains a source failure and its
scheduled races remain present. Work only in the clean isolated checkout, never
the owner's dirty checkout. No force merge or bypass of required checks.

## Artifacts and Notes

Input plan SHA256 is
`4c3385228e1f80d5a0cd609d9a78b236e3a3d53efdc8676920276039455cfb03`.
Output SHA256 is
`a0ba48dff04841990a52ac0029df4c79d13ec4cff8bf98e4a6c8e69fd2c3851d`.
Both replay commands exited 2 for the existing nine row-count mismatches.
All six sources replayed successfully, and `cmp` exited 0.

## Interfaces and Dependencies

`inspect_top3(rows: list[dict[str, Any]], scheduled_count: int) -> dict[str, Any]`
consumes the existing normalizer's output, not arbitrary raw API rows. Only the
Python standard library and existing replay functions are used.

## Outcomes & Retrospective

Implementation and local verification are complete; remote CI and merge remain.
There are 49 candidate top-three sets, not 49 successful predictions. The one
missing candidate is the void Seoul race `20261010_1_1`. Production registration still requires
separate DB owner/runtime connections and a published future card. This diagnostic
does not fix historical pre-race provenance or establish predictive performance.

Revision: initialized 2026-10-11 to close the gap between row-count reconciliation
and candidate outcome inspection without inventing a scoring policy.

Revision: added actual replay counts and passing tests on 2026-10-11. Kept the
existing CLI reconciliation status unchanged to avoid silently redefining it.
