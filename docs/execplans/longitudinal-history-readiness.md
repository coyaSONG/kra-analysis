# Inventory repeated historical starts and original time tables

This living plan follows `.agent/PLANS.md`.

## Purpose / Big Picture

PR128 found no repeated horses in its short May archive. Determine whether the
already preserved longer history can support a longitudinal time study without
collecting more data or fitting a model. The deliverable is a reproducible
inventory of the complete existing supported history, exact-distance prior
support and the status of its original HTML tables. It is not an accuracy test.

## Progress

- [x] Inspect pinned history and condition manifests; find 11,523 historical
  records / 3,275 horses and 5,173 records with an exact-distance prior.
- [x] Implement bounded original-source replay and structural support inventory.
- [x] Test boundary, missingness, source-tier, identity and layout behavior.
- [x] Preserve original-source results and interpret feasibility limits.
- [ ] Pass required CI and normally merge; preserve completion receipt on PR.

## Surprises & Discoveries

The short May archive has one observation per horse, but the longer corpus has
up to 12. The preliminary 5,173 count is structural, not time-feature readiness.
The condition registry contains more events than the admitted history and keeps
unknown/unadmitted groups. They must not be silently confused with selected rows.

The original replay verified 1,233 condition groups and exact selected roster/
rank joins for all 1,156 admitted races. Known literal layouts cover 1,113 races;
17 Busan 1000m races, two Busan 2000m races and 24 Yeongcheon races remain
unrecognized/unsupported. Jeju's readable labels still do not verify pace
semantics. SQLite independently reproduced every race's support counts.

## Decision Log

Keep the existing supported-history corpus as the declared starting population,
not a new claim of complete national racing history. It contains 8,994 baseline,
1,528 later-May and 1,001 early-May rows. Preserve all tiers and exclusions.
Only read historical records and conditions from pinned artifacts; never use
their legacy prediction/coverage fields, October 16-18 targets or saved models.
Verify raw HTML pins, receipt clocks, header conditions, full roster sizes and
selected historical rank/horse joins. Count recognizable time tables but do not
equate recognized columns with verified sectional units or stable abilities.
Keep Yeongcheon distinct from Busan. Use one fixed 1-180-day same-horse,
same-physical-venue, exact-distance rule; no search over windows or thresholds.

## Context and Orientation

The existing history is in
`.cache/autoresearch/condition-form-research-20261013/run-1/history.json` and its
`conditions.json`. May additions are the `extension_history` and
`extension_conditions` fields of
`.cache/autoresearch/history-gap-expansion-20261014/report-v2.json` and
`.cache/autoresearch/observed-history-extension-20260501-14/audit-report.json`.
Their exact pins will be constants in
`packages/scripts/autoresearch/longitudinal_history_inventory.py`.
The derived history has race/horse/rank/roster-size/tier, not time features.

`race_conditions.from_capture` reconstructs condition records from original
bytes. `shared.official_result_support.parse_detail` recovers the original
roster/ranks. `sectional_source_audit.timing_rows` recognizes already-tested
literal headers and column counts. These are read-only functions, not collectors.
Unknown timing layouts are retained with a reason, not auto-mapped.

## Plan of Work

Add a small inventory module with `load`, `inspect_source`, `profile` and `audit`.
Load only the declared historical fields, reject overlapping keys and preserve
all condition-only events. Verify each original receipt and HTML, then classify
recognized timing layouts without deriving new quantities. Compute per-race and
venue/distance structural support counts and summarize source tiers and clocks.
Publish an immutable JSON report and a concise research interpretation. Add
focused tests to the historical-source CI step.

## Concrete Steps

From the isolated checkout, run:

    env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts .venv/bin/python -B -m pytest -q -p no:cacheprovider packages/scripts/autoresearch/tests/test_longitudinal_history_inventory.py
    env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/scripts .venv/bin/python -B -m autoresearch.longitudinal_history_inventory

The audit prints JSON only. Save a new version with an exclusive file create.
Do not invoke the historical training/evaluation runners or recollect sources.

## Validation and Acceptance

All 11,523 historical identities must be represented without changing rank,
tier or admission. Every selected event must have an exact historical
horse/rank/roster-size join and a replayed condition. Malformed or changed source
bytes fail; unrecognized time layouts remain classified, not learned.
Synthetic tests must cover duplicate keys, missing/wrong conditions, same-day
and future exclusion, 180/181-day boundaries, physical venue isolation, class
not used as a hidden filter, unknown layouts and read-only operation.
Report both raw structural support and support with recognized tables; neither
is future accuracy, PIT training approval or longitudinal stability.

Observed validation: 36 new cases and 275 related regression cases passed;
Ruff lint and format checks passed. Independent SQLite self-join counts match
all 1,156 original race ledgers. The immutable output SHA256 is
`a338c67f005c1ff56d3ab418f44073d7d76de0a2e3b879d7172a2a8f430e9701`.

## Idempotence and Recovery

Reads are bounded by pinned files and no network collection is allowed. A failed
pin or identity check stops the inventory. Preserve failed output evidence and
fix the adapter rather than changing source versions or historical admission.
Never overwrite originals or alter the user's primary dirty checkout.

## Artifacts and Notes

The prior endpoint and time-information reports remain unchanged. The new
report must include source pins and all original receipt/raw hashes so a future
researcher can trace every selected race without loading October targets.

## Interfaces and Dependencies

Use the standard library plus existing replay/parser helpers, no new dependency.
`profile(records, conditions, sources)` computes only descriptive counts.
`inspect_source` proves original bytes/identity before layout classification.
No trainer, prediction publisher or enrollment function belongs in this module.

## Outcomes & Retrospective

Original-source replay completed at 2026-10-20T18:34:18.996274Z. All 11,523
historical records remain in the 1,156-race ledger. There are 5,173 exact-prior
records, of which 5,123 have recognizable literal layouts on both sides; 1,943
of those are Jeju and still need semantic evidence. Seoul/known-Busan
measurement readiness is 3,180 records, not a validation subset. New endpoint
and operand audits remain necessary before deriving broader quantities.
The 70% exact-single-triple goal remains unmet. A24/B34 remain frozen and future
interval/N remain unset.

Initial plan: evaluate the broader preserved corpus after the negative repeat
finding, rather than tune the short May archive.
Updated after original replay and independent SQL verification: preserve the
positive structural finding and the separate semantic gaps without claiming
stable features or training eligibility.
