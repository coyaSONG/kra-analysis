# Yeongcheon Supplement Without Replacing Frozen Predictions

This living ExecPlan follows `.agent/PLANS.md`.

## Purpose / Big Picture

Close the missing six Yeongcheon races in the October 16-18 pre-race PDF
archive. Preserve all 50 frozen races, original M0/API27 predictions and the
PR99 44-race archive. A source URL under `busan` is a shared storage location,
not evidence that the physical race is Busan. Only an explicit Yeongcheon
footer on every page, complete API26 identity join and matching schedule may
admit venue 4 inputs. This improves source coverage, not measured accuracy.

## Progress

- [x] (2026-10-15 11:58Z) Verified six official schedule links with physical meet 4; one schema probe has explicit Yeongcheon footers.
- [x] (2026-10-15 12:03Z) Added a distinct venue-4 parser profile and bounded supplement options; original defaults remain restricted to venues 1/2/3.
- [x] (2026-10-15 12:12Z) Inspected actual PDF layout; final 360 regression tests passed after isolating the replay extension.
- [x] (2026-10-15 12:03Z) Captured six venue-4 sources / 66 runners with seven calls, zero retries, before first block cutoff.
- [x] (2026-10-15 12:14Z) Verified all 50 original source chains, full 534-row historical join and unchanged public predictions; real M0 model admission still passes.
- [ ] Publish additive source receipt after tests and required CI, then normal merge.

## Surprises & Discoveries

Both the captured national and regional schedule HTML associate the
`b_run_hr_261018_01.pdf` storage path with physical venue 4. The schema probe
using the old venue-3 collector correctly produced no eligible features,
because every page says Yeongcheon. That diagnostic is immutable and never
promoted by relabeling its manifest. The authorized ChatGPT browser is logged
out; no Pro consultation occurred.

The first broader test run failed 14 cases because the legacy PDF replay file
is hash-pinned by M0 admission and the result evaluator. Restored that file
byte-for-byte (SHA256 `2db618a34a77fe7ff03b8ea30e38e00a5d79ca94dbba75ffdb9a616a41ab45e0`),
instead of changing any frozen pins. An independent venue-4 replay module now
mirrors the validation body and shares the unchanged raw/API helpers. The same
negative replay tests run against both venues 1 and 4. Final suite: 360 passed.

## Decision Log

Use a separate `kra-race-card-pdf-yeongcheon-v1` profile while retaining legacy
profile output for meets 1/2/3. Validate exact footer, not URL directory as
venue evidence. Do not change feature extraction geometry or strip names.
Use a fresh archive and actual fresh capture times. These decisions were made
on 2026-10-15 after inspecting the official HTML and raw PDF.

Source-code fingerprints intentionally change. Old bundle plans continue to
require their exact original implementation at PR99 commit
`c0367769150211961349c6e7f52ec5b5db9bf5b7`. Never edit their fingerprints to
make a newer implementation pass. Individually reparse old raw captures to
check feature compatibility, and preserve the original bundle files.

After discovering the frozen replay dependency, retain all original capture
artifacts from commit `2ac5bc5`. Derive a new `input-plan-v2.json` and
`feature-bundle-v2.json` from exactly the same six manifests under the isolated
implementation, with a new fingerprint and timestamp. Never edit the original
plan, bundle, source bytes, capture clocks or original report. Require the v2
bundle to equal v1 except for the implementation fingerprint. This is a new
offline verification, not a second acquisition or retroactive reservation.

## Outcomes & Retrospective

Six additional races are captured and identity-validated. No labels, model fit, predictions,
evaluation arm or training approval is part of this increment. The 70% goal
remains unachieved.

The union registry hash is `10074357d3582c5aa94b6c8d0c7b9dbcbfa84e4cff9844457c020bc82369a104`.
All 534 appearances have training count/minutes, including all 79 without
observed recent history and all 225 condition-fallback rows. Four of the new
66 trainer summaries are missing; all 66 training-window durations are unknown.
These are data-quality results, not predictive performance.

## Context and Orientation

`packages/scripts/shared/kra_race_card_pdf.py` owns bounded current-horse
panel extraction. `autoresearch/kra_race_card_pdf_snapshot.py` owns immutable
HTTP capture. `kra_race_card_pdf_replay.py` validates saved bytes and complete
API entry joins; `kra_race_card_pdf_bundle.py` locks implementation fingerprints.
Paths in this paragraph are relative to `packages/scripts` where applicable.
`prospective_pdf_supplement.py` freezes all targets and collects selected venues.
Its default archive is `.cache/autoresearch/prospective-pdf-supplement-20261015`.
The new archive must be `.cache/autoresearch/yeongcheon-pdf-supplement-20261015`.
Original public pins are in `docs/research/commitments/2026-10-16-18/`.

## Plan of Work

Extend the supported footer map with Yeongcheon, preserving Busan as a distinct
venue. Choose parser version by physical meet at parsing and replay. Extend
CLI venue choices. Parameterize supplement output root, supported set and
request budget without changing defaults. Add PDF round-trip, shared-path
wrong-venue rejection, capture/replay, version and population tests.
No new dependencies or API endpoints are needed.

`packages/scripts/autoresearch/yeongcheon_pdf_replay.py` isolates the new
profile from the frozen legacy replay. The bundle dispatcher selects it only
for physical venue 4 and fingerprints it. Deliberate validation-body duplication
preserves the old model/evaluation implementation; shared helper code remains
in the original module. Never merge with changes to the frozen legacy file.

## Concrete Steps

Work in `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf`.
Run `.venv/bin/pytest -q packages/scripts/autoresearch/tests/test_kra_race_card_pdf*.py packages/scripts/autoresearch/tests/test_prospective_pdf_supplement.py`.
After tests, use `PYTHONPATH=packages/scripts .venv/bin/python -c` to invoke
`asyncio.run(capture(output_root=Path(".cache/autoresearch/yeongcheon-pdf-supplement-20261015"), supported={4}, max_requests=10))`
with imports from `asyncio`, `pathlib` and `autoresearch.prospective_pdf_supplement`.
Expect six venue-4 rows in the race registry and 66 runner features only if
all eligibility gates pass. Otherwise keep failures without retries.

## Validation and Acceptance

Every source must match physical venue 4 on all pages and every API runner.
Reject a Busan PDF requested as Yeongcheon and vice versa. Recompute complete
bundle offline with its new fingerprint. Reparse prior 44 captures and compare
every saved parsed output/audit to prove source compatibility without changing
old pins. Check original public M0/API27/input SHA256 values unchanged.
Publish full population counts, missingness, raw hashes and actual capture
times. Required branch CI must pass; do not force merge failing required gates.

## Idempotence and Recovery

The new root is created exclusively. Duplicate runs refuse; existing captures,
including the diagnostic probe, cannot be overwritten. Requests have zero
retries, a ten-call cap and a three-failure breaker. The earliest frozen block
cutoff is 2026-10-16T01:20:00Z. Failure remains recorded, never backdated.

## Artifacts and Notes

National HTML hash `88f26631089b81a62042e37f88d4a3287c4efc43bd233420174efafef7b52fe5`;
regional HTML hash `49c67c03204b9ef08ae032c7e50fe98c813f6a7b6338c549e3687e5a31693eba`.
Both are in `.cache/autoresearch/published-card-monitor/20261015T110510.316500Z_71d9f02f4bc6`.
Schema PDF hash `371a8ea59d3126bebd74d3129bd5593bb3e006a4f990bebdcbe464060592bf5e`
is retained under `.cache/autoresearch/yeongcheon-pdf-schema-20261015` and is
ineligible as captured with the old venue-3 diagnostic identity.

## Interfaces and Dependencies

`parser_version_for_meet(meet)` selects only the output schema profile.
`capture(*, output_root=ROOT, supported=None, max_requests=60)` defaults to the
unchanged PR99 collection scope. `finalize(..., supported=None)` defaults to
the original scope; an extension labels other venues `not_requested` and keeps
their denominator. Existing httpx, pdfplumber and hashlib are sufficient.

Initial plan records source evidence and immutable compatibility strategy.
Revision: isolated venue-4 replay after the broad test exposed frozen model
dependencies; retained original capture artifacts and added v2 offline review.
