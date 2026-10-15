# Capture supplemental pre-race PDF inputs without changing forecasts

This living plan follows `.agent/PLANS.md`. Keep Progress, Surprises &
Discoveries, Decision Log and Outcomes & Retrospective current.

## Purpose / Big Picture

Expand genuinely pre-race research inputs for the already frozen October 16-18
50-race / 534-runner block. Official PDF cards contain training information
absent from API-only M0/API27. Acquire original bytes before cutoff, replay their
identity and timing checks, and publish hashes for later research. No model
training, scoring, new evaluation arm, prediction overwrite or success claim.

## Progress

- [x] (2026-10-15) Revalidated merged PR98 and read current training/PDF gates.
- [x] (2026-10-15) Confirmed no current-block PDF archive in the research checkout.
- [ ] Implement bounded orchestration using the existing collectors and replay.
- [ ] Capture once, replay raw evidence and retain all 50 statuses.
- [ ] Document source coverage and exclusions; publish hashes, test, push and merge.

## Surprises & Discoveries

Only the old October 10-11 PDF archive exists in this checkout. Its features
were not used by the current API-only predictors. Existing PDF parser supports
physical venues 1, 2 and 3, not venue 4. The full frozen population contains six
venue-4 races; they must remain explicit unsupported source records.

## Decision Log

On 2026-10-15 choose pre-race acquisition over more tuning of spent historical
labels. Use one fresh complete entry capture per supported date/venue so the
existing PDF replay same-archive provenance requirement stays intact. Compare
fresh raw rows with the original pinned M0 source; any difference blocks that
unit for this supplement. Do not relax replay or rewrite old source paths.

Request each supported PDF once. Maximum 60 HTTP requests total, serial pacing,
zero retry, stop after three consecutive failed PDFs or any failed entry unit.
Use the earliest published cutoff as the entire acquisition deadline. A failed
or unattempted race remains in the full inventory, with no exported rows.
The supplement is not a replacement input reservation or a new evaluation arm.

## Context and Orientation

Use `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf`, branch
`codex/prospective-pdf-expansion-20261015`. Preserve the original user checkout.
`condition_delta_diagnostic` loads the three pinned public commitments and
full source-verified rosters. `kra_entry_sheet_snapshot` captures complete API
pages. `kra_race_card_pdf_snapshot` captures/parses/audits PDF originals.
`kra_race_card_pdf_bundle` replays source chains and projects numeric fields
with missing flags. These modules retain their original behavior.

The new module `prospective_pdf_supplement.py` orchestrates them. Its canonical
archive is `.cache/autoresearch/prospective-pdf-supplement-20261015`. The full
manifest lists all 50 races; an inner PDF bundle covers only the 44 supported
source requests. Never describe the inner bundle as the evaluation population.

## Plan of Work

First add an identity/full-population check and bounded capture function, plus
tests for missing/extra/duplicate rows, unsupported venues, original-roster
mismatches, request budget and deadline. Save the complete acquisition plan
before network access. Existing directories reject a repeated run so an
interruption cannot silently recapture occupied slots.

Use original M0 packets to recover original entry manifests and deadlines.
Read the API key only from the existing secret file. New raw entries and PDFs
live in the same new capture archive; credentials never enter the report.
Retain every receipt, source URL, capture timestamp, hash and failure reason.
Export through the unchanged verified bundle builder, join eligible features
back to every frozen roster, and report field missing counts over the full
534 expected rows as well as actually exported rows.

## Milestones

The software milestone passes new orchestration tests and existing PDF/source
tests. The acquisition milestone produces actual captured originals or explicit
failures, not empty scaffolding. The publication milestone exposes plan, bundle
and complete supplement hashes through a small normal PR before the cutoff;
any missed publication deadline stays visible, never backdated.

## Concrete Steps

From the isolated checkout:

    PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.prospective_pdf_supplement
    PYTHONPATH=packages/scripts .venv/bin/pytest -q packages/scripts/autoresearch/tests/test_prospective_pdf_supplement.py

Run the existing entry snapshot, PDF parser/audit/snapshot/replay/bundle suites
as well. Inspect actual statuses and missing counts before making any coverage
claim. Add the focused tests to Scripts Checks and publish only nonsecret
metadata/hashes, keeping raw PDFs local.

## Validation and Acceptance

The report retains exactly the public 50 IDs and 534 expected runners. All
eligible exports match full original horse/gate rosters and cutoffs. Every
blocked source has zero feature rows. All three public commitments remain
unchanged. API calls plus PDF calls never exceed 60; no retries occur. No new
prediction or result endpoint request is made. Accuracy remains undefined.

## Idempotence and Recovery

Create the canonical output directory exclusively; refuse a second run. A crash
preserves plan, completed captures and failures. Inspect those sources before
an explicitly planned continuation; never delete the archive to retry. No
changes to the original collectors, model files or forward directories.

## Artifacts and Notes

Record final source/feature/status hashes and actual request counts in the
research document after capture. The original fixed predictions remain the
only registered M0/API27 comparison. Pro access was checked earlier today and
was logged out; no new consultation is claimed.

## Interfaces and Dependencies

Use standard-library datetime, Counter and existing httpx/PDF dependencies.
`finalize(targets, bundle)` must reject membership drift and return all 50
source statuses and full-denominator missingness. `capture()` uses the fixed
commitment scope and refuses late or duplicate execution.

## Outcomes & Retrospective

Pending actual acquisition. More source rows do not imply more correct
predictions. Future training admission requires explicit recipe/label review
and later independent validation, not a claim based on this cohort's coverage.

Initial plan written before collection, with no target outcomes inspected.
