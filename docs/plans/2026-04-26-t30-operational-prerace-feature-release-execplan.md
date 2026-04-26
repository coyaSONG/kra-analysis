# T-30 Operational Prerace Feature Release

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds.

This document follows [.agent/PLANS.md](/Users/chsong/Developer/Personal/kra-analysis/.agent/PLANS.md) and must be maintained in accordance with that file.

## Purpose / Big Picture

After this change, the project can produce KRA unordered top-3 predictions from a frozen T-30-minute prerace input snapshot that excludes odds and other timing-unsafe data. The user-visible outcome is an evaluation and prediction path that says, for every race, whether the input was safe for actual pre-race operation, what fields were used, and whether the model regressed or improved against the pinned holdout baseline. The first release prioritizes operational safety over speculative feature breadth: a release may ship if leakage, freshness, coverage, and no-regression gates pass, while metric improvement is tracked as the success target.

## Progress

- [x] (2026-04-26 08:40Z) User decisions were finalized: operational prediction first, T-30 cutoff, no same-day history, odds audit-only, existing per-horse classifier, release gate separated from success target.
- [x] (2026-04-26 08:50Z) Repository context was inspected: timing policy docs, prediction registry, feature engineering, standardized loader, past-stats DB lookup, leakage checks, and public change bulletin connector.
- [x] (2026-04-26 09:00Z) This implementation ExecPlan was created to make the decisions self-contained and executable.
- [x] (2026-04-26 09:22Z) Milestone 1 was implemented by adding `data/contracts/t30_operational_release_features_v1.csv`, `packages/scripts/shared/t30_release_contract.py`, registry documentation, and contract tests.
- [x] (2026-04-26 09:28Z) Milestone 1 validation passed with 25 targeted pytest tests and ruff checks on the new contract module and tests.
- [x] (2026-04-26 09:40Z) Milestone 2 foundation was added as a pure T-30 cutoff helper with unit tests.
- [x] (2026-04-26 09:50Z) Standardized prerace loading now carries `operational_cutoff_status` without changing the validated alternative-ranking payload shape.
- [x] (2026-04-26 10:10Z) Milestone 3 first slice promoted strict `past_stats` and `weight_delta` into the prediction input registry, source timing contract, row builder, and tests.
- [x] (2026-04-26 10:25Z) Changed-jockey source parsing was added for the public `entry_change_bulletin`; `changed_jockey_flag` remains `planned_nullable` until T-30 snapshot wiring is validated.
- [x] (2026-04-27 09:20Z) Parsed changed-jockey notices are now wired into standardized horse payloads as nullable non-model state with entry-change coverage audit.
- [x] (2026-04-27 09:35Z) Milestone 2 gate reporting was added: snapshot bundles now emit per-dataset T-30 release gate reports for freshness, odds exclusion, and changed-jockey source coverage.
- [x] (2026-04-27 10:05Z) Milestone 4 evaluation tooling was added and validated. The resulting release readiness verdict is `BLOCKED`, not release-pass, because current stored artifacts cannot prove strict T-30 freshness and DB replay produced zero usable strict rows for the fixed mini_val/holdout manifests.
- [x] (2026-04-27 10:42Z) Added `apps/api/scripts/capture_entry_change_bulletin.py` to persist raw KRA entry-change HTML and parsed notice manifests with a shared `source_snapshot_at`. A live capture for meets 1/2/3 wrote ignored local artifacts under `data/source_snapshots/entry_change_bulletin/`.
- [x] (2026-04-27 10:55Z) Wired captured `entry_change_bulletin` manifests into offline replay through `packages/scripts/shared/entry_change_snapshot_manifest.py` and `--entry-change-snapshot-dir`. Replay selects only the latest manifest whose `source_snapshot_at` is at or before the race `entry_snapshot_at`; late-only manifests keep changed-jockey state as `source_missing`.

## Surprises & Discoveries

- Observation: `packages/scripts/shared/db_client.py` already implements the most important past-stats guard by querying historical rows with `r.date < race_date` and `COALESCE(r.result_collected_at, r.updated_at, r.created_at) <= cutoff_at`.
  Evidence: `RaceDBClient.get_past_top3_stats_for_race()` uses `r.date >= %s AND r.date < %s` and receives `lookup.entry_snapshot_at` as the cutoff anchor.

- Observation: `horses[].weight_delta` is already present in `data/contracts/prerace_field_metadata_v1.csv`, but `data/contracts/prediction_input_field_registry_v1.csv` does not expose a `weight_delta` model input row.
  Evidence: the metadata row describes `parse_weight_delta_from_wg_hr(wgHr)` as `ALLOW`, while the prediction registry currently exposes `wgHr_value` but no explicit `weight_delta`.

- Observation: a public source connector for entry changes already exists, but it is only the fetch layer.
  Evidence: `apps/api/infrastructure/prerace_sources/changes.py` defines `entry_change_bulletin` for `/raceFastreport/ChulmapyoChange.do`, described as 말취소 and 기수변경 notices.

- Observation: `past_stats` can be promoted without a new source table because `feature_engineering.compute_features()` already consumes `horses[].past_stats`; the missing part was exposing count fields and registering the prediction inputs.
  Evidence: `recent_race_count`, `recent_top3_count`, `recent_top3_rate`, `recent_win_count`, and `recent_win_rate` now validate through `historical_result_lookback_block`.

- Observation: the live KRA `ChulmapyoChange.do` page exposes 말취소 and 기수변경 as separate HTML tables with row-level notice timestamps, but 기수변경 can legitimately be an empty table.
  Evidence: `parse_entry_change_bulletin_html()` now extracts cancellation and jockey-change rows while ignoring "자료가 없습니다." rows.

- Observation: T-30 safety can be checked before model execution because standardized payloads now carry `operational_cutoff_status`, `entry_change_audit`, and odds-filtered horse records.
  Evidence: `build_t30_release_gate_report()` fails late snapshots or any audit-only odds key and reports changed-jockey null/source coverage.

- Observation: current fixed mini_val/holdout manifests cannot be replayed into strict T-30 rows from the DB as stored today.
  Evidence: the replay into `.ralph/outputs/t30_release_snapshots/` requested 200 mini_val and 500 holdout races but wrote 0 rows; mini_val failures were all `late_snapshot_unusable`, while holdout failures were 375 `late_snapshot_unusable` and 125 `partial_snapshot`.

- Observation: existing static snapshot artifacts are useful as a weakness probe but are not release-valid.
  Evidence: `.ralph/outputs/t30_release_evaluation_current_snapshots.json` reports `gate.passed=false` because freshness metadata is missing; release-feature coverage is 0% for `recent_*`, `cancelled_count`, and `field_size_live`, while `weight_delta` coverage is 93.5%.

- Observation: the live entry-change bulletin contains table header rows that look structurally similar to data rows.
  Evidence: the first live capture initially produced bogus notices with `horse_name="마명"` and `reason="사유"`. `_is_header_row()` now filters those rows, and the corrected live capture produced meet1=6 notices, meet2=2 notices, meet3=0 notices.

- Observation: entry-change manifests must be selected by capture timestamp, not simply by race date.
  Evidence: `select_entry_change_snapshot_for_replay()` ignores manifests whose `source_snapshot_at` is after the race `entry_snapshot_at`, so replay cannot use a later public bulletin to backfill a historical pre-race snapshot.

## Decision Log

- Decision: The first release target is operational prediction, not maximum offline score.
  Rationale: The current data contains mixed pre-race and post-race fields, stale detail snapshots, and timestamp-unverified odds. A high offline score is not meaningful until the input boundary is proven safe.
  Date/Author: 2026-04-26 / User and Codex

- Decision: The official prediction cutoff is T-30 minutes before scheduled start.
  Rationale: T-30 is recent enough to include race-day card state while leaving time for collection retry and avoiding the higher timing risk of T-10 odds and late changes.
  Date/Author: 2026-04-26 / User and Codex

- Decision: Historical rolling features must use only races with `history.race_date < target.race_date`; same-day earlier results are excluded.
  Rationale: Same-day results create result publication and start-delay ambiguity. Excluding them makes the first operational contract auditable and deterministic.
  Date/Author: 2026-04-26 / User and Codex

- Decision: Odds fields are audit-only for this release.
  Rationale: `winOdds`, `plcOdds`, odds ranks, and odds race-relative features are currently `HOLD` because their true pre-race publication and replay semantics are unverified.
  Date/Author: 2026-04-26 / User and Codex

- Decision: Release features are limited to `past_stats`, `body_weight_delta`, and `cancelled_changed_jockey`; `training`, `jkStats`, `ownerStats`, and `sectional_speed` are backfill-only.
  Rationale: The release features either already have a strict historical lookup path or come from the core T-30 card/change snapshot. The backfill-only features currently have 0% coverage or stale-snapshot risk and should not block the first safe release.
  Date/Author: 2026-04-26 / User, ChatGPT Pro consultation, and Codex

- Decision: Keep the existing per-horse classifier for two weeks and select top3 by within-race score sorting.
  Rationale: Replacing the model structure while fixing data timing would confound the release. A triplet reranker can be evaluated after safe inputs are proven.
  Date/Author: 2026-04-26 / ChatGPT Pro consultation and Codex

- Decision: The release gate and success target are separate.
  Rationale: The release gate is leakage/freshness/coverage plus holdout no-regression. Metric improvement remains the success target, but it is not the only shipping condition for an operational safety release.
  Date/Author: 2026-04-26 / User and Codex

- Decision: The T-30 release contract is an overlay, not a replacement for the full prediction input registry.
  Rationale: The first release still uses safe core-card features governed by the existing registry. The new contract only classifies debated enhancement groups so audit-only odds and backfill-only sources cannot silently enter the release feature set.
  Date/Author: 2026-04-26 / Codex

- Decision: Keep the new T-30 cutoff helper pure and independent from database or network access.
  Rationale: Freshness classification must be easy to unit test and reusable by evaluation, reporting, and future API collection paths. Integration code should call the helper rather than duplicate timestamp math.
  Date/Author: 2026-04-26 / Codex

## Outcomes & Retrospective

The implementation now captures the T-30 release contract in both prose and machine-readable form, wires the current release feature groups into the row schema, adds changed-jockey parsing and nullable audit state, emits release gate reports from offline snapshot bundles, and provides a reproducible T-30 release evaluation script.

The current data is not ready for release. The readiness report is `BLOCKED` because strict pre-cutoff snapshots are absent or late for the fixed evaluation manifests. This is a data collection/replay weakness, not just a model score issue: the existing snapshots cannot prove T-30 freshness and lack coverage for the newly promoted release features.

## Context and Orientation

This repository predicts unordered top-3 horse sets for KRA races. The API app in `apps/api` collects and stores race snapshots. The script package in `packages/scripts` builds feature rows, trains and evaluates models, and runs offline research jobs.

The phrase "T-30" means "thirty minutes before the scheduled race start time." A source is fresh for this release only if its snapshot timestamp is at or before `scheduled_start_at - 30 minutes`. The phrase "same-day history" means a race that occurred earlier on the same calendar day as the target race. Same-day history is not allowed in release features even if it would have been known before a later race.

The main policy documents are `docs/prerace-standard-field-catalog.md`, `docs/kra-race-lifecycle-timing-matrix.md`, `docs/prerace-data-whitelist-blacklist-policy.md`, and `docs/prediction-input-field-registry.md`. The machine-readable contracts live under `data/contracts/`.

The main implementation files are:

- `packages/scripts/shared/db_client.py`, where `RaceDBClient.get_past_top3_stats_for_race()` computes horse rolling top-3 history.
- `packages/scripts/evaluation/data_loading.py`, where `RaceEvaluationDataLoader` can inject past stats during evaluation.
- `packages/scripts/feature_engineering.py`, where `compute_features()` and `compute_race_features()` derive per-horse and same-race features.
- `packages/scripts/shared/prediction_input_schema.py`, where the final model row contract and row validation live.
- `packages/scripts/evaluation/leakage_checks.py`, where post-race field leakage is scanned.
- `apps/api/infrastructure/prerace_sources/changes.py`, where the public entry-change bulletin connector is declared.

Current known data weaknesses are part of this plan, not assumptions outside it. In local snapshots, core race-card fields are strong, but `past_stats`, `training`, `jkStats`, and `ownerStats` were observed at 0% in the full-year analysis snapshot. Enriched `hrDetail` has coverage but may be stale because historical re-query can return current cumulative totals. Raw `API214_1` payloads can include post-race result and sectional fields. Odds are stored in some paths but remain timing-unverified and must not enter the release model.

## Plan of Work

Milestone 1 freezes the release contract before feature implementation. Update `docs/prediction-input-field-registry.md` with a short "T-30 operational release overlay" section that states the release buckets: release, backfill-only, audit-only, and excluded. Then update machine-readable contracts so the row validator can distinguish release-allowed features from generally operationally allowed features. If the existing registry schema should remain stable, add a separate file such as `data/contracts/t30_operational_release_features_v1.csv` with columns `feature_name`, `release_bucket`, `cutoff_rule`, `notes`. Add tests in `packages/scripts/tests/test_prediction_input_field_registry.py` or a new `test_t30_operational_release_contract.py` that assert odds are audit-only, `training` and `jkStats` are not release features, and `past_stats`, `weight_delta`, `cancelled_count`, `field_size_live`, and changed-jockey indicators are the release surface.

Milestone 2 makes freshness auditable. Add a small shared module under `packages/scripts/shared/`, for example `operational_cutoff.py`, that computes `t30_cutoff_at` from `race_plan.sch_st_time` and the race date. It must return a structured result with `scheduled_start_at`, `cutoff_at`, `source_snapshot_at`, and a pass/fail reason. If a historical row lacks a scheduled start time, it may be included in backfill statistics but must not count as a freshness-pass release row. Wire this check into the standardized loader or evaluation dataset builder so each race payload carries `operational_cutoff_status`. The release gate requires 100% of included release rows to pass freshness.

Milestone 3 promotes only the three release feature groups. For `past_stats`, keep the existing strict query rule in `RaceDBClient.get_past_top3_stats_for_race()` and add tests that prove same-day rows are excluded. The MVP fields are `recent_race_count`, `recent_win_count`, `recent_top3_count`, `recent_win_rate`, and `recent_top3_rate`. For `body_weight_delta`, add `weight_delta` to `data/contracts/prediction_input_field_registry_v1.csv`, expose it in `packages/scripts/shared/prediction_input_schema.py`, and use the existing `wgHr` parsing policy from `data/contracts/prerace_entry_preprocessing_rules_v1.csv`; parsing failures should produce null plus a normalization flag, not drop the horse. For `cancelled_changed_jockey`, keep `cancelled_count` and `field_size_live`, then add a T-30-snapshot-derived changed-jockey flag only after parsing the public `entry_change_bulletin` source; until the parser exists, the changed-jockey field must default to null with a coverage reason rather than fabricated zero.

Milestone 4 keeps backfill-only data out of the model while preserving research value. Collect or backfill `training`, `jkStats`, `ownerStats`, and `sectional_speed` into source snapshots and QA reports, but do not add them to the release model feature set. `sectional_speed` may only be built from historical races strictly before the target date, never from the current race's sectional fields. Odds collection may run as an audit job with T-60, T-30, T-10, and T-5 snapshots, but all odds-derived columns remain absent from the release feature matrix.

Milestone 5 runs the two-level acceptance process. The release gate passes if leakage is zero, freshness is 100% for included release rows, coverage meets thresholds, and holdout primary metrics do not regress beyond tolerance. The success target is metric improvement over the pinned baseline. If the gate passes but metrics do not improve, label the result "operational safety release" rather than "success release" and keep the backfill-only features as next candidates.

## Concrete Steps

Work from `/Users/chsong/Developer/Personal/kra-analysis`.

1. Create or update the release contract.

    Edit `docs/prediction-input-field-registry.md` and add the T-30 overlay. Add `data/contracts/t30_operational_release_features_v1.csv` if extending the main registry would blur existing meanings. Include at minimum these rows:

    - `recent_race_count`, `recent_win_count`, `recent_top3_count`, `recent_win_rate`, `recent_top3_rate`: release, strict past only.
    - `weight_delta`: release, direct T-30 core card.
    - `cancelled_count`, `field_size_live`: release, pre-cutoff snapshot only.
    - `changed_jockey_flag`: release once parsed from `entry_change_bulletin`; null until parsed.
    - `winOdds`, `plcOdds`, `odds_rank`, `winOdds_rr`, `plcOdds_rr`: audit-only.
    - `training_score`, `recent_training`, `days_since_training`, `jk_skill`, `owner_skill`, and sectional-speed fields: backfill-only for this release.

2. Add tests for the contract.

    Add tests under `packages/scripts/tests/`. They should fail if an odds field is release-allowed, if a backfill-only field appears in the release feature set, or if `weight_delta` is missing from the prediction input registry once Milestone 3 is implemented.

3. Implement freshness helpers.

    Add `packages/scripts/shared/operational_cutoff.py` with a pure function that accepts race date, scheduled start time, and snapshot timestamps. The function should not access the database; it should only calculate and classify. Add unit tests that cover valid T-30 pass, snapshot after cutoff fail, missing scheduled start fail for release, and timezone-safe parsing.

4. Implement release feature wiring.

    Update `packages/scripts/evaluation/data_loading.py` and the standardized payload path so `with_past_stats=True` is used for release evaluations. Update `packages/scripts/shared/prediction_input_schema.py` so `weight_delta` is normalized into rows. Update `feature_engineering.py` only if `weight_delta` needs a computed feature wrapper; direct registry mapping is preferable because `wgHr` is already a core card field.

5. Add changed-jockey parser work as an independently verifiable slice.

    Use `apps/api/infrastructure/prerace_sources/changes.py` as the fetch connector. Add a parser module near the source connector or in a shared parser location already used by `apps/api/infrastructure/prerace_sources/`. It should return structured rows with race date, meet, race number when available, horse identifier/name, change type, old jockey if available, new jockey if available, and `source_snapshot_at`. If the bulletin does not expose enough structure reliably, record that in the release report and keep `changed_jockey_flag` null rather than guessing.

6. Run targeted tests while building.

    Use the existing Python test style:

        UV_CACHE_DIR=.uv-cache uv run pytest -q packages/scripts/tests/test_past_top3_stats.py packages/scripts/tests/test_prediction_input_field_registry.py packages/scripts/tests/test_prediction_input_schema.py packages/scripts/tests/test_feature_engineering_timing_validation.py packages/scripts/evaluation/tests/test_data_loading.py

    Add the new test file to this command once created.

7. Run the release evaluation and write the report.

    Use the existing autoresearch/evaluation entry points rather than inventing a new one unless the current commands cannot express the T-30 contract. The report should be written under `packages/scripts/autoresearch/` or `.ralph/outputs/` following existing output conventions, and should include gate status, metric deltas, feature coverage, freshness pass rate, leakage result, and the backfill-only feature backlog.

## Validation and Acceptance

Leakage acceptance: `check_detailed_results_for_leakage()` must pass with zero issues on the final detailed evaluation records, and the final model row validator must contain zero `HOLD`, `BLOCK`, `LABEL_ONLY`, or `META_ONLY` feature columns. Odds fields must be absent from the release feature matrix.

Freshness acceptance: 100% of races included in the release evaluation must have a valid `scheduled_start_at`, a computed `t30_cutoff_at`, and every release feature source snapshot at or before `t30_cutoff_at`. Races missing the data needed to prove freshness may be reported separately but cannot count as release-pass rows.

Coverage acceptance: `past_stats` coverage must be at least 90% among non-debut horses; `weight_delta` parse coverage must be at least 95% of active entries or all failures must have explicit normalization flags; `cancelled_count` and `field_size_live` must be present for at least 95% of included races; changed-jockey coverage may be null until the parser is validated, but its null rate and source failure rate must be reported.

Holdout acceptance: the release model must not regress the pinned baseline by more than 0.5 percentage points on the primary top-3 hit/overlap metric and exact 3-of-3 must not show a material drop. A "success release" requires at least 1.0 percentage point improvement in the primary top-3 metric or a statistically defensible improvement note. If safety gates pass but improvement does not, the outcome is "operational safety release."

Backfill acceptance: `training`, `jkStats`, `ownerStats`, `sectional_speed`, and odds audit outputs may exist as QA artifacts, but none may appear in release model rows. If any of these appear in the final row feature set, the release fails.

## Idempotence and Recovery

The implementation should be additive until all tests pass. New contract files, helper modules, parsers, and tests can be re-run safely. Do not overwrite stored T-30 snapshots with later snapshots; if a re-collection occurs after T-30, store it as a later audit revision and keep the release snapshot immutable. If a parser cannot confidently extract changed-jockey state, preserve the raw bulletin and mark the derived field null. Do not backfill missing fields by querying current profile/detail APIs for historical races unless the stored-as-of timestamp proves the data existed at or before the target cutoff.

## Artifacts and Notes

The final two-week release should leave at most these user-facing artifacts:

- `data/contracts/t30_operational_release_features_v1.csv` or an equivalent registry update.
- A T-30 freshness report with race-level pass/fail reasons.
- A leakage report proving zero forbidden post-race fields in release rows.
- A feature coverage report for release and backfill-only groups.
- A holdout evaluation report comparing baseline, operational safety release, and any audit-only odds baselines.
- An odds audit report, if live polling was run, with T-60/T-30/T-10/T-5 snapshot coverage and discard reasons.

Current known baseline context to preserve in the final report: previous holdout summaries observed roughly `overall_holdout_hit_rate` around 0.38 and exact 3-of-3 around 0.43 in local `.ralph` outputs. Treat these as orientation only; the release report must compare against the actual pinned baseline artifact selected at run time.

Milestone 1 validation transcript:

    $ UV_CACHE_DIR=.uv-cache uv run pytest -q packages/scripts/tests/test_t30_release_contract.py packages/scripts/tests/test_prediction_input_field_registry.py packages/scripts/tests/test_prediction_input_schema.py
    .........................                                                [100%]
    25 passed in 0.03s

    $ UV_CACHE_DIR=.uv-cache uv run ruff check packages/scripts/shared/t30_release_contract.py packages/scripts/tests/test_t30_release_contract.py
    All checks passed!

Milestone 2 foundation validation transcript:

    $ UV_CACHE_DIR=.uv-cache uv run pytest -q packages/scripts/tests/test_operational_cutoff.py
    ......                                                                   [100%]
    6 passed

Milestone 2 loader integration validation transcript:

    $ UV_CACHE_DIR=.uv-cache uv run pytest -q packages/scripts/tests/test_prerace_standard_loader.py packages/scripts/tests/test_operational_cutoff.py packages/scripts/tests/test_t30_release_contract.py packages/scripts/tests/test_prediction_input_field_registry.py packages/scripts/tests/test_prediction_input_schema.py
    ...................................                                      [100%]
    35 passed in 0.08s

    $ UV_CACHE_DIR=.uv-cache uv run ruff check packages/scripts/shared/t30_release_contract.py packages/scripts/shared/operational_cutoff.py packages/scripts/shared/prerace_standard_loader.py packages/scripts/tests/test_t30_release_contract.py packages/scripts/tests/test_operational_cutoff.py packages/scripts/tests/test_prerace_standard_loader.py
    All checks passed!

Milestone 3 past-stats and weight-delta validation transcript:

    $ UV_CACHE_DIR=.uv-cache uv run pytest -q packages/scripts/tests/test_past_top3_stats.py packages/scripts/tests/test_prediction_input_schema.py packages/scripts/tests/test_t30_release_contract.py packages/scripts/tests/test_prediction_input_field_registry.py packages/scripts/tests/test_feature_source_timing_contract.py packages/scripts/tests/test_prerace_standard_loader.py packages/scripts/tests/test_operational_cutoff.py
    ..................................................                       [100%]
    50 passed in 0.10s

    $ UV_CACHE_DIR=.uv-cache uv run ruff check packages/scripts/feature_engineering.py packages/scripts/shared/prediction_input_schema.py packages/scripts/shared/feature_source_timing_contract.py packages/scripts/tests/test_past_top3_stats.py packages/scripts/tests/test_prediction_input_schema.py packages/scripts/tests/test_t30_release_contract.py
    All checks passed!

Milestone 3 changed-jockey parser validation transcript:

    $ cd apps/api && UV_CACHE_DIR=../../.uv-cache uv run pytest -q --no-cov tests/unit/test_prerace_public_source_connectors.py
    tests/unit/test_prerace_public_source_connectors.py .........            [100%]
    9 passed in 2.04s

    $ cd apps/api && UV_CACHE_DIR=../../.uv-cache uv run ruff check infrastructure/prerace_sources/changes.py tests/unit/test_prerace_public_source_connectors.py
    All checks passed!

Milestone 2/3 gate wiring validation transcript:

    $ UV_CACHE_DIR=.uv-cache uv run pytest -q packages/scripts/tests/test_t30_release_gate.py packages/scripts/autoresearch/tests/test_offline_evaluation_dataset_job.py packages/scripts/evaluation/tests/test_data_loading.py packages/scripts/tests/test_prerace_prediction_payload.py packages/scripts/tests/test_prerace_standard_loader.py
    ....................                                                     [100%]
    20 passed in 0.47s

    $ UV_CACHE_DIR=.uv-cache uv run ruff check packages/scripts/shared/t30_release_gate.py packages/scripts/autoresearch/offline_evaluation_dataset_job.py packages/scripts/autoresearch/tests/test_offline_evaluation_dataset_job.py packages/scripts/evaluation/data_loading.py packages/scripts/evaluation/tests/test_data_loading.py packages/scripts/shared/prerace_prediction_payload.py packages/scripts/shared/prerace_standard_loader.py packages/scripts/tests/test_t30_release_gate.py packages/scripts/tests/test_prerace_prediction_payload.py packages/scripts/tests/test_prerace_standard_loader.py
    All checks passed!

Milestone 4 evaluation and readiness artifacts:

- `.ralph/outputs/t30_release_evaluation_current_snapshots.json`: static snapshot probe; not release-valid because freshness metadata is missing. Baseline exact 3-of-3 was `0.386`, release-feature exact 3-of-3 was `0.382`, exact delta was `-0.004`, and average set-match delta was `-0.0013333333333332975`.
- `.ralph/outputs/t30_release_snapshots/`: attempted strict DB replay output. The build wrote zero strict rows for both splits because stored snapshots were late or partial.
- `.ralph/outputs/t30_release_readiness_report.json` and `.ralph/outputs/t30_release_readiness_report.md`: final readiness report with verdict `BLOCKED`.
- `data/source_snapshots/entry_change_bulletin/`: ignored local raw HTML and JSON manifest captures for `entry_change_bulletin`; each manifest records `source_snapshot_at`, raw HTML path, content hash, and parsed notices.

Milestone 4 validation transcript:

    $ UV_CACHE_DIR=.uv-cache uv run pytest -q packages/scripts/autoresearch/tests/test_t30_release_evaluation.py
    .                                                                        [100%]
    1 passed in 1.54s

    $ UV_CACHE_DIR=.uv-cache uv run pytest -q packages/scripts/tests/test_past_top3_stats.py packages/scripts/tests/test_prediction_input_schema.py packages/scripts/tests/test_t30_release_contract.py packages/scripts/tests/test_t30_release_gate.py packages/scripts/tests/test_prediction_input_field_registry.py packages/scripts/tests/test_feature_source_timing_contract.py packages/scripts/tests/test_prerace_prediction_payload.py packages/scripts/tests/test_prerace_standard_loader.py packages/scripts/tests/test_operational_cutoff.py packages/scripts/evaluation/tests/test_data_loading.py packages/scripts/autoresearch/tests/test_offline_evaluation_dataset_job.py packages/scripts/autoresearch/tests/test_t30_release_evaluation.py packages/scripts/evaluation/tests/test_predict_only_test.py
    ........................................................................ [100%]
    72 passed in 1.98s

    $ UV_CACHE_DIR=.uv-cache uv run ruff check packages/scripts/autoresearch/t30_release_evaluation.py packages/scripts/autoresearch/offline_evaluation_dataset_job.py packages/scripts/autoresearch/tests/test_t30_release_evaluation.py packages/scripts/autoresearch/tests/test_offline_evaluation_dataset_job.py packages/scripts/shared/t30_release_contract.py packages/scripts/shared/t30_release_gate.py packages/scripts/shared/operational_cutoff.py packages/scripts/shared/prediction_input_schema.py packages/scripts/shared/prerace_prediction_payload.py packages/scripts/shared/prerace_standard_loader.py packages/scripts/shared/feature_source_timing_contract.py packages/scripts/feature_engineering.py packages/scripts/evaluation/data_loading.py
    All checks passed!

    $ cd apps/api && UV_CACHE_DIR=../../.uv-cache uv run pytest -q --no-cov tests/unit/test_prerace_public_source_connectors.py
    tests/unit/test_prerace_public_source_connectors.py .........            [100%]
    9 passed in 2.04s

Entry-change capture and replay linkage validation transcript:

    $ cd apps/api && UV_CACHE_DIR=../../.uv-cache uv run python scripts/capture_entry_change_bulletin.py --meet 1 --meet 2 --meet 3
    [
      {"notice_count": 6, "source_snapshot_at": "2026-04-26T15:42:12.780181+00:00", ...},
      {"notice_count": 2, "source_snapshot_at": "2026-04-26T15:42:12.914764+00:00", ...},
      {"notice_count": 0, "source_snapshot_at": "2026-04-26T15:42:13.032425+00:00", ...}
    ]

    $ UV_CACHE_DIR=.uv-cache uv run pytest -q packages/scripts/tests/test_entry_change_snapshot_manifest.py packages/scripts/autoresearch/tests/test_offline_evaluation_dataset_job.py packages/scripts/tests/test_prerace_prediction_payload.py packages/scripts/tests/test_t30_release_gate.py
    ...............                                                          [100%]
    15 passed in 0.53s

    $ UV_CACHE_DIR=.uv-cache uv run ruff check packages/scripts/shared/entry_change_snapshot_manifest.py packages/scripts/autoresearch/offline_evaluation_dataset_job.py packages/scripts/tests/test_entry_change_snapshot_manifest.py packages/scripts/autoresearch/tests/test_offline_evaluation_dataset_job.py
    All checks passed!

    $ UV_CACHE_DIR=.uv-cache uv run mypy packages/scripts/shared/entry_change_snapshot_manifest.py
    Success: no issues found in 1 source file

## Interfaces and Dependencies

At the end of the implementation, the following interfaces or artifacts should exist.

- A release feature contract loader, either in a new module such as `packages/scripts/shared/t30_release_contract.py` or as an extension of `packages/scripts/shared/prediction_input_schema.py`.
- `packages/scripts/shared/operational_cutoff.py` with a pure function that can be unit tested without network or database access.
- `RaceDBClient.get_past_top3_stats_for_race()` still using `r.date < target race_date` and source cutoff checks.
- `packages/scripts/shared/prediction_input_schema.py` exposing `weight_delta` as a numeric model feature if the registry contains it.
- A parser for `entry_change_bulletin` or an explicit release report finding that changed-jockey parsing is not yet reliable.
- Evaluation output that records release gate status separately from success target status.

Revision note: 2026-04-26에 운영 예측 우선, T-30 cutoff, odds audit-only, strict past history, 제한된 release feature scope, 기존 per-horse classifier 유지, 그리고 릴리스 게이트/성공 목표 분리 결정을 반영해 신규 ExecPlan을 작성했다.

Revision note: 2026-04-26에 Milestone 1 구현 결과를 반영했다. T-30 운영 릴리스 overlay 계약 CSV, shared loader, 테스트, registry 문서 링크가 추가되어 이후 구현 단계에서 backfill-only/audit-only feature를 코드로 차단할 수 있게 됐다.

Revision note: 2026-04-26에 Milestone 1 검증 결과를 Artifacts and Notes에 추가했다. 이유는 다음 구현자가 현재 계약 레이어가 테스트와 lint를 통과한 지점에서 Milestone 2를 시작할 수 있게 하기 위해서다.

Revision note: 2026-04-26에 Milestone 2의 cutoff helper와 표준 로더 통합 검증 결과를 반영했다. 이유는 T-30 freshness 상태가 이제 표준 prerace 적재 결과에 포함되므로 다음 작업이 report/gate 연결부터 시작될 수 있기 때문이다.

Revision note: 2026-04-26에 Milestone 3의 첫 구현 조각을 반영했다. `past_stats` 기반 recent feature 5개와 `weight_delta`가 레지스트리, source timing contract, row schema, 릴리스 overlay에서 현재 모델 입력으로 검증된다.

Revision note: 2026-04-26에 `entry_change_bulletin` HTML 파서와 테스트를 반영했다. 기수변경이 실제 row로 파싱 가능해졌지만, 모델 입력 `changed_jockey_flag`는 스냅샷 wiring 전까지 계속 nullable planned 상태로 둔다.

Revision note: 2026-04-27에 changed-jockey nullable wiring과 T-30 release gate report writer를 반영했다. 이제 snapshot bundle 생성 시 freshness/odds exclusion/change-source coverage를 모델 평가 전 단계에서 확인할 수 있다.
