# Freeze observed-history inputs and expose partial observations

This living plan follows `.agent/PLANS.md`. The research target remains one
unordered three-horse prediction per race, with 70% exact success over a complete
frozen future national race universe. This change provides reproducible inputs,
not model approval or evidence that the target has been attained.

## Purpose / Big Picture

The current history reader chooses the latest receipt per date and venue. A
later correction therefore changes which source it reads. Add an explicit
reader that reconstructs only the result and entry captures selected in a
SHA-256-pinned seed, regardless of subsequently appended receipts. SHA-256 is
a digest of file bytes, not proof of their publication time. Project a separate
`observed_partial_v1` block from verified observations without changing the
existing H0 features, which remain null when their response window is incomplete.

## Progress

- [x] Inspected the clean PR79 merge and created `codex/frozen-partial-history`.
- [x] Revalidated the preceding server-only turn: it confirmed configuration,
  but did not advance research state. No paid resource approval is assumed.
- [x] Implement and test selected-source replay, partial features and diagnostics.
- [x] Materialize all 28 pinned diagnostic rosters and 294 runners, retaining
  source collisions and unresolved identity records in the quality report.
- [x] Run 349 regression tests, Ruff and diff checks; document actual evidence.
- [ ] Commit, push and merge only after required remote checks pass.

## Surprises & Discoveries

The seed records source-manifest pins but not receipt-file pins. Replay can
therefore verify the selected capture bytes and normalized rows, but cannot
claim receipt timestamps or independent publication solely from that seed.
PR79 found 100 identity-bound groups with exact roster collisions, plus 172
identity-unresolved rows. No side of a collision is automatically removed.
Actual projection links 58 of 294 runner appearances to collision groups through
132 lineage links. JSON-serialized comparison is necessary because Python dict
equality would otherwise treat integer 1 and boolean true as identical evidence.

## Decision Log

- Decision: preserve existing `replay` and audit defaults; add an explicit
  frozen-reader path, sharing the raw collision audit implementation.
  Rationale: collection-resume and latest-view diagnostics keep their behavior.
  Date: 2026-10-11.
- Decision: no model fitting, relabeling or removal of affected target runners.
  Rationale: the frozen seed is not historical pre-race evidence and observed
  identity conflicts still need source review. The completed Pro consultation
  recommended a separate partial-observation contract with no new fits.
  Date: 2026-10-11.
- Decision: optional cutoff validation is explicitly local-clock history-source
  validation only. It is not full future-study registration or target-card proof.
  Rationale: entry cards, complete national universe and prediction commit
  observation require the existing forward workflow and its pending deployment.
  Date: 2026-10-11.

## Outcomes & Retrospective

Selected-source replay and a separate five-field partial contract work on all
28/294 actual diagnostic targets. The entire old H0/H1 projection is unchanged.
Partial rates are available for 246 appearances, with 48 null denominators.
All collisions and source gaps remain visible. There are no new research fits
or 70% evidence. Remaining work includes source review, actual future card
integration and independent forward registration; the goal remains active.

## Context and Orientation

Work in `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf` without
touching the owner's dirty primary checkout. `observed_history_seed.py` owns
plans, capture pins and receipt inspection. `shared/observed_result_history.py`
owns existing H0/H1 semantics. `history_identity_audit.py` compares raw full
rosters without inferring physical event identity from a match. Tests live in
`packages/scripts/autoresearch/tests`. Local test dependencies are installed in
the isolated checkout's `.venv`; CI uses the frozen uv environments.

## Plan of Work

First add `autoresearch/frozen_history_view.py`. Verify the seed digest, original
plan, ordered complete date/venue inventory, source manifests and original pages,
then compare reconstructed inventory, normalized records and status counts.
Treat request counts and original implementation as pinned historical metadata,
not independently verified claims. Never read the latest receipt or current
journal to choose a capture. Corrupt selected sources fail; no missing-to-zero
fallback is allowed. A timezone-aware optional cutoff must bound seed creation,
result captures and entry bindings, including unresolved units.

Next add `shared/observed_partial_history.py`. Use existing projection validation
and lineage; count ranked finishes, wins, top-three finishes and unresolved
statuses in [D-90,D), plus top-three fraction with a null zero-denominator rate.
Counts refer to observed records, not actual starts. Preserve the entire target
roster and explicit missing, empty-unconfirmed and identity-unresolved coverage.
The full collision ledger is diagnostic metadata, not a model feature.

Finally add a CLI that reads the pinned diagnostic corpus, uses every ledger
roster without inspecting labels or training-selection flags, and stores the
projection, source audit and implementation provenance atomically without
overwrite. Keep all approval/evidence claims false. Add CI regression coverage.

## Concrete Steps

From the isolated checkout root, run:

    .venv/bin/python -m pytest -q packages/scripts/autoresearch/tests/test_frozen_partial_history.py packages/scripts/autoresearch/tests/test_history_identity_audit.py packages/scripts/autoresearch/tests/test_observed_history_seed.py packages/scripts/autoresearch/tests/test_observed_result_history.py -o addopts=''

The actual source root is `.cache/autoresearch/observed-history-20261011`.
Its `seed-final.json` digest is
`0dbe7abe5bdfb0a0b422bb90bddbdf1a3face89e5016254807ba37be95c25c66`.
Use corpus `.cache/autoresearch/restricted-cohort/20261011T124748.785378Z_ebdf29deaaa9/corpus.json`,
digest `d6598f244d6a7b7bc5e65846a4c79ee6ac96ad278b89a14268de332e77526ae2`.
Invoke the new module with explicit root, seed, corpus, their digests and a new
output path. Record the final command and output digest in the research report.

## Validation and Acceptance

Tests must prove: later receipts and request reservations do not change an old
view; changed selected bytes and cached-row tampering fail; all planned units
remain present; entry-binding availability is checked even for unknown identity;
naive/late cutoff rejection; old H0 unchanged; partial counts survive known gaps;
zero observations produce null rate; same-day/future records and target labels
do not affect counts; duplicate rosters fail; all diagnostic runners survive.
Actual output must preserve 28 races, 294 runners, 100 collision groups and 172
unbound source rows. No external API request or training call is needed.

## Idempotence and Recovery

All raw inputs are read-only. New output publication uses existing atomic
exclusive-file creation. Retry using a new output path, never overwrite old
artifacts. Preserve all source versions; do not delete or repair captured bytes.
Keep the old reader and feature contract available for comparison.

## Artifacts and Notes

Pro advice is recorded in the PR79 research report; its completed response did
not assess the subsequently discovered 100-group collision evidence. This plan
does not claim a fresh consultation. Paid server preparation remains independent.

## Interfaces and Dependencies

`replay_frozen(root, seed_path, seed_sha256, *, cutoff=None) -> dict` returns
the byte-pinned seed only after reconstructing its selected source data.
`project_partial_history(race, seed) -> dict` returns unchanged legacy projection
plus separate observed partial features. No new third-party dependencies.

Initial plan records implementation scope and the distinction between local
source-cutoff checks and independent future prediction registration.

Revision: completed implementation and actual v2 materialization, 349 tests,
unchanged old features, and preserved all collision evidence. Research report
`docs/research/2026-10-11-frozen-partial-history.md` contains exact reproduction,
source/output pins, cutoff evidence and limitations. Remote publication pending.
