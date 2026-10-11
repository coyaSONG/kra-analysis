# Audit the horse-specific meaning of the saved rest feature

This living ExecPlan follows `.agent/PLANS.md`.

## Purpose / Big Picture

The October development audit found that all 116 races had the same saved `rest` value for every runner. Before changing model inputs, reconstruct the gap to each horse's most recent observed earlier entry using stable horse IDs, and compare that diagnostic with the saved values. This is not an accuracy experiment or a replacement production feature. A listed entry does not prove an actual start, and the legacy collection does not prove complete history or historical availability.

## Progress

- [x] (2026-10-11) Verified prior diagnostic PR #69 merged as 2746823f51d8ffc459bd524d87ee144975d1f15b. Started the isolated `codex/horse-rest-interval` branch without editing the owner's dirty checkout.
- [x] (2026-10-11) Traced `compute_features` assigning `ilsu` directly to `rest_days`. Existing field inventory describes a racing-day/session identifier; the official entry API catalog only calls it day count, not rest interval.
- [x] (2026-10-11) Implemented a read-only, pinned-input diagnostic with 36 passing focused regressions. Combined source/identity/paired-audit/training-admission checks: 229 passed, 15 existing joblib/NumPy deprecation warnings. Ruff lint/format and diff whitespace checks passed.
- [x] (2026-10-11) Actual comparison retained all 116 races/1,308 runners: 1,192 prior observations, 116 null gaps, one equality to the saved proxy, 111 races with varying observed gaps. Documented results and uncertainty.
- [ ] Pass tests, push, and merge normally after required CI.

## Surprises & Discoveries

The historical JSON roster has stable `hrNo` values and dates but strips result ranks. The existing past-statistics query has a 90-day window and a positive-odds filter; neither is a complete last-start certificate. A change to `compute_features` would silently change the meaning of existing model and cached inputs, so this increment must not do that.

## Decision Log

Decision (2026-10-11, Codex): Call the calculated value `days_since_prior_observed_entry`, never `rest_days`. Keep null when history or identity is missing. Do not infer debut, zero rest, or actual start from absence. Preserve numeric/string stable IDs without name matching; digit-only IDs normalize leading zeros consistently and normalization collisions within a race fail.

Decision (2026-10-11, Codex): Limit targets to the saved October development state file, require exact target roster equality and saved-rest/raw-ilsu agreement, and exclude all same-day/future entries by strict date. Read no prediction labels and perform no training, feature replacement, or December evaluation. Whole-source hashes identify replay bytes, not historical timing evidence.

## Outcomes & Retrospective

The executable diagnostic and actual 116-race replay are implemented. The observed proxy mismatch is substantial, but actual horse-rest semantics and deployment remain unresolved. This reduces uncertainty without granting historical data production eligibility. The 70% exact unordered single-combination target and complete future universe requirement are unchanged. Full evidence and replay pins are in `docs/research/2026-10-11-horse-entry-interval-audit.md`.

## Context and Orientation

Work in `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf`. `packages/scripts/feature_engineering.py` computes existing features. `packages/scripts/autoresearch/october_paired_error_audit.py` found the race-constant values. The owner's read-only `.cache/autoresearch/full_year_2025_plus_20260613_collector_v2_full_context_training_lookback3_overlay.json` is a list of races with `race_id`, `race_date`, and `horses`. Each horse has `chulNo` (race-local gate number), `hrNo` (stable ID), and `ilsu`. The saved `laya_oof_training_dataset/validation.jsonl` contains states with race ID, runner fields/values and field size. No model, cache, production schema, or DB is changed.

## Plan of Work

Add `autoresearch/horse_entry_interval_audit.py` with pure `build_audit(dataset, validation)` plus a CLI. Validate dates, physical race keys, nonempty unique rosters, stable identity collisions, and exact target membership. Index earlier observations by horse ID and date. Sort dates and use binary search strictly before each target day, independent of source order and including previous observations at other venues. Retain all target runner rows. Report interval coverage, missing identity/history, within-race variability, agreement with `ilsu`, and complete row-level provenance (prior observed race IDs). Add focused pytest cases and required CI coverage. Document the actual bounded experiment in a repo-native research note.

## Milestones

The first milestone is a reproducible command whose synthetic two-horse example returns different observed gaps while saved `rest` stays constant. The second is actual same-universe coverage and differences, with no score or promotion claim. The final milestone publishes code, tests and evidence through normal required checks. Production replacement will require qualified actual-start history, source timing/completeness evidence, a versioned train/serve contract, and a fresh frozen-input experiment; that is not implemented here.

## Concrete Steps

From the isolated root run `.venv/bin/python -m pytest -q packages/scripts/autoresearch/tests/test_horse_entry_interval_audit.py -o addopts=''`. Run `.venv/bin/ruff check` and `.venv/bin/ruff format --check` on the two new Python files, then `git diff --check`.

Run `PYTHONPATH=packages/scripts .venv/bin/python -m autoresearch.horse_entry_interval_audit --dataset /Users/coyasong/Developer/coyasong/kra-analysis/.cache/autoresearch/full_year_2025_plus_20260613_collector_v2_full_context_training_lookback3_overlay.json --validation /Users/coyasong/Developer/coyasong/kra-analysis/.cache/autoresearch/laya_oof_training_dataset/validation.jsonl --output .cache/autoresearch/horse-entry-interval-audit-20261011.json`. The output must retain 116 target races and 1308 runner rows or fail visibly; these counts are verified against the preceding audit, not imposed as a reusable function requirement.

## Validation and Acceptance

Test date boundaries, year/leap-day changes, same-day/future exclusion, reordered source rows, missing history/ID, stable-ID normalization, cross-venue observations, malformed dates/IDs, duplicate race/runner/horse identities, target/source roster mismatches, saved/raw rest disagreements, input hash capture, and refusal to overwrite existing output. Every malformed relevant row fails visibly. Null intervals stay in denominators. Nothing in a passing diagnostic asserts pre-race eligibility or accuracy gain.

## Idempotence and Recovery

Inputs are read once and SHA-256 hashes recorded. Output creation refuses replacement. Reruns use a new output filename. Do not edit originals, owner files, model checkpoints, cached features or database records. CI failures must be investigated without force merging.

## Artifacts and Notes

The official API catalog https://www.data.go.kr/data/15058677/openapi.do?recommendDataYn=Y was read on October 11. It calls the field day count but does not establish horse-specific rest semantics. Repository field inventory `docs/knowledge/discovery-2026-04-10-field-inventory.md` describes `ilsu` as a session/day identifier. Distinguish these source descriptions from the diagnostic's observed distributions.

## Interfaces and Dependencies

Use Python standard library argparse, bisect, collections, datetime, hashlib, JSON and pathlib. Reuse `shared.kra_race_identity.validate_race_identity`; do not add third-party dependencies or modify production feature builders. The CLI writes diagnostic JSON and prints a bounded aggregate summary.

Revision note (2026-10-11): Created before edits. Narrowed this increment to identifying the incorrect proxy's behavior because complete actual-start and pre-race evidence are absent, rather than silently changing existing model semantics.

Revision note (2026-10-11): Implemented and executed the bounded audit. The initial source/target roster and saved-value checks pass on real inputs without filtering target rows. Production replacement and forward registration remain unfinished separate milestones.
