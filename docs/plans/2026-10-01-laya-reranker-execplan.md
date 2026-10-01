# Build and validate a Laya race-candidate reranker

This ExecPlan is a living document. The sections `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` must be kept up to date as work proceeds. Maintain this document in accordance with `.agent/PLANS.md` from the repository root.

## Purpose / Big Picture

The project currently emits one unordered three-horse combination per KRA race, but the strict temporal exact-hit rate remains below the 70% goal even though larger candidate pools often contain the correct combination. This work adds a reproducible research path that specializes the open-source Laya typed-decision model as a second-stage reranker. After the work, a researcher can audit how many independent, leakage-safe races are available, materialize one Laya `choice` example per race from at most 19 pre-race candidate combinations, fine-tune or evaluate Laya outside the API application's dependency environment, and compare its single-combination predictions with the existing model on the same walk-forward race universe.

The first observable result is a data-capacity JSON artifact. Running the capacity-audit command must report raw runner rows, unique races, complete labels, duplicate entry keys, missing-feature rates, date coverage, and projected unique-race counts for larger public-data collections. Later milestones add the labelled JSONL dataset, a strict prior-date candidate surface, Laya inference, and promotion-gate evaluation.

## Progress

- [x] (2026-10-01 Asia/Seoul) Confirmed the official Laya contract: `choice` questions use a state plus a map of option labels to descriptions, the evaluation dataset is JSONL with `state`, `questions`, and `expected`, and high-cardinality choice questions should stay near 20 options.
- [x] (2026-10-01 Asia/Seoul) Profiled the current 2025 row cache: 18,742 runner rows, 1,758 unique races, 10.661 runners per race, complete three-horse answers for all races, and 10.5% missing feature cells across 86 features.
- [x] (2026-10-01 Asia/Seoul) Implemented and verified `single_combo_laya_data_capacity_audit.py`. Focused pytest passed `4 passed`; the real cache audit passed with 18,742 rows, 1,758 usable races, no duplicate entry keys, complete labels, 10.4968% missing feature cells, and the expected 20250103 through 20251228 coverage.
- [x] (2026-10-01 Asia/Seoul) Materialized a strict prior-date historical rank-pattern candidate surface over 1,254 post-warm-up races. All races passed the timing and coverage gates, but the 19-option diagnostic oracle was 71.6906% overall and only 61.7486% in the weakest block, so this surface is not suitable for Laya training.
- [x] (2026-10-01 Asia/Seoul) Audited the existing primary-route support-union cache as the replacement Laya surface. Its canonical non-overlapping `fold_a`, `fold_b`, and `fold_c` windows contain 116, 176, and 147 races, at most 20 candidates per race, and candidate-pool oracle rates of 93.1034%, 96.5909%, and 96.5986% respectively.
- [x] (2026-10-01 Asia/Seoul) Exported deterministic Laya JSONL from the support-union cache: 116 train races, 176 validation races, and 147 untouched test races. The official Laya 0.3.22 validator at commit `6d942c92081fbc139e736bbd9ac0023223c29b7f` accepted all three files, and a second export reproduced every dataset and manifest SHA-256 exactly.
- [x] (2026-10-01 Asia/Seoul) Reworked the rendering to `kra-laya-choice-rendering-v5`. At `max_len=1024` and `head_max_len=512`, all 439 examples retain every candidate token and every state token, with zero collapsed option spans.
- [x] (2026-10-01 Asia/Seoul) Built 928 deterministic option-order training rows from 116 independent train races, while scheduling exactly one variant of each race per epoch. Focused tests pass `16 passed`, and the official Laya validator still accepts all train, validation, and sealed-test JSONL files.
- [x] (2026-10-01 Asia/Seoul) Ran the pinned Laya zero-shot and eight-epoch head-only specialization on validation only. Zero-shot and the selected epoch 5 checkpoint both scored 11/176 = 6.25%; specialization reduced NLL from 2.72475 to 2.71863 but did not change exact selections, so it is rejected for promotion.
- [x] (2026-10-01 Asia/Seoul) Measured a frozen candidate-feature baseline. A nine-spec train-to-validation XGBoost ranker search selected depth 4 with 100 estimators at 106/176 = 60.2273%, versus 88/176 = 50.0% for the default-candidate heuristic and 11/176 = 6.25% for Laya.
- [x] (2026-10-01 Asia/Seoul) Refit only the selected XGBoost specification on the 292 train-plus-validation races and froze model SHA-256 `f4770458fc121db3d30a2c070420c28f1cd6361a37eb13ed2af73a29130cbb56`. Repeated selection reproduced the manifest, predictions, and model byte for byte; final-test inference was false at freeze time.
- [x] (2026-10-01 Asia/Seoul) Evaluated the precommitted frozen feature ranker exactly once on the December `fold_c` test. It scored 79/147 = 53.7415%, versus 80/147 = 54.4218% for the existing strict current-best fallback on the identical race IDs. The model is rejected for promotion and this holdout is now spent.
- [x] (2026-10-01 Asia/Seoul) Added `single_combo_laya_oof_training_dataset.py`, which caches the date-ordered `fold_a` train candidate rows and exports only train plus October validation JSONL. Focused tests pass `11 passed`; a real one-date smoke materialized 9 races and 176 candidate rows in 130 seconds, and the exporter correctly refused that partial cache.
- [x] (2026-10-02 Asia/Seoul) Materialized all 112 `fold_a` train date groups in 946 seconds. The resulting 1,319-race train and 116-race October validation files passed timing, leakage, byte-reproducibility, token-loss, and official Laya parser checks. Retained candidate oracle rates are 85.5951% and 93.1034%; train and validation SHA-256 values are `f9437f845c190f61b6c132bf325c080db39a74bc55b5593469fca7f774f3500b` and `8151aa4bddc49a01b4bd2631d1cbcb600a9a031389fe787dc5ad390144b7c6c6`.
- [x] (2026-10-02 Asia/Seoul) Corrected both Laya and XGBoost evaluation so a correct `NONE` classification does not count as a top-three prediction hit. The expanded XGBoost control then scored 57/116 = 49.1379%, below the strict fallback's 63/116 = 54.3103% on the same October races.
- [x] (2026-10-02 Asia/Seoul) Ran a two-epoch expanded head-only Laya probe. Its best checkpoint scored 12/116 = 10.3448%, so frozen-encoder specialization remains rejected.
- [x] (2026-10-02 Asia/Seoul) Matched the official Laya fine-tuning recipe by enabling ModernBERT encoder adaptation at `2.5e-5` with head learning rate `1e-4` and gradient checkpointing. A 16-race MPS smoke passed, and the full 1,319-race first epoch improved zero-shot 4/116 = 3.4483% to 35/116 = 30.1724% in 1,388 seconds. This is meaningful adaptation but remains below both controls and is not promoted.
- [ ] Backfill multiple prior years and designate a new untouched 2026 forward window before making another promotion decision. The current environment has no `KRA_API_KEY`, and December 2025 remains spent.
- [x] (2026-10-01 Asia/Seoul) Closed validation order-sensitivity and calibration without running them because the Laya checkpoint did not improve validation exact accuracy.
- [x] (2026-10-01 Asia/Seoul) Applied the promotion gate: neither candidate improved the existing strict baseline on final evidence, so no model was merged.

## Surprises & Discoveries

- Observation: Raw public-data row count is not the independent sample count.
  Evidence: The current cache has 18,742 rows but only 1,758 race decisions, or 10.661 runner rows per race. At that density, 100,000 rows project to roughly 9,380 independent races and 300,000 rows to roughly 28,140 races.

- Observation: The current live candidate path already produces exactly 19 options for every covered race.
  Evidence: `.cache/autoresearch/single_combo_live_probability_current_miss_candidate_features.json` reports 17 covered races and 19 merged candidates for each race, matching Laya's practical option-count guidance.

- Observation: Candidate availability is not the present bottleneck, but candidate selection is.
  Evidence: `.cache/autoresearch/clean_release_current_best_full_combo_delta_switch_after_broad_rank_segment_reanchor_rerun_repro_diagnostic.json` reports a 0.551020 selected test exact rate and at least a 0.913793 robust candidate-pool oracle rate. The oracle uses labels and is only an upper-bound diagnostic, not valid performance evidence.

- Observation: Existing historical candidate helpers may fit their base horse models on the same rows they later expose as training candidates.
  Evidence: `_build_window_member_probabilities` uses `dates <= train_end` for fitting, while the synthetic train window can also evaluate dates through `train_end`. The Laya dataset must therefore use a new strict prior-date replay surface rather than treating those in-sample candidate features as deployment-equivalent evidence.

- Observation: A single ensemble rank ordering does not provide a robust enough 19-option ceiling.
  Evidence: The strict replay covered all 1,254 eligible races without timing violations, but its candidate oracle was 71.6906% overall and ranged from 61.7486% to 81.8898% by refit block. Because a reranker cannot select an answer absent from its options, this surface cannot support the 70% rolling-floor goal.

- Observation: The existing support-union surface is a much stronger match for Laya's bounded choice head.
  Evidence: `.cache/autoresearch/single_combo_primary_route_candidate_rows_summary.json` reports 11 to 20 candidates per race and pool-oracle rates of 93.1034% on `fold_a`, 96.5909% on `fold_b`, and 96.5986% on `fold_c`. The cache builder uses answer keys only to attach completed-race labels and calculate diagnostics; candidate combinations and their feature fields are formed without the active answer.

- Observation: Reserving one `NONE` choice does not reduce candidate coverage on the current rolling surface.
  Evidence: Only one 20-combination race in each of train and validation needed pruning to 19 combinations. The removed combination was not the answer, so retained oracle rates remain 93.1034%, 96.5909%, and 96.5986% for train, validation, and test.

- Observation: A compact tabular runner state materially reduces truncation risk without dropping the selected features.
  Evidence: Replacing repeated per-runner keys with one `runner_fields` schema plus scaled `runner_values` arrays reduced the maximum state size from 4,196 to 936 characters. The maximum state plus instruction plus one criterion is now 1,184 characters.

- Observation: Character-size checks substantially understated Laya's option-head truncation.
  Evidence: Under the shipped 256-token head budget, the initial compact rendering retained only 12 to 20 tokens per option and cut off most candidate scores. The v5 integer-vector rendering plus a 512-token head budget retains all options without re-capping and all states without truncation across train, validation, and test.

- Observation: The unmodified typed-decisions checkpoint does not transfer zero-shot to KRA ranking, and head-only tuning is insufficient at the current sample size.
  Evidence: The pinned checkpoint scored 11/176 = 6.25% on validation, predicted position 1 or 3 on 135/176 races, and missed all six `NONE` targets. Eight head-only epochs covered all eight option-order variants once, but the selected epoch 5 checkpoint still scored 11/176; only NLL improved from 2.72475 to 2.71863.

- Observation: The same compact candidate fields do contain a generalizable validation signal that Laya failed to learn.
  Evidence: A fixed nine-spec XGBoost pairwise-ranker search trained only on October races selected depth 4 and 100 estimators at 106/176 = 60.2273% on November. It improved the default-candidate heuristic by 18 races and the specialized Laya checkpoint by 95 races on the identical validation universe. Runner-state aggregates and CatBoost probes did not improve this result.

- Observation: The validation-selected feature ranker did not transfer enough to the sealed month to beat the existing strict selector.
  Evidence: After refitting the frozen specification on 292 October-plus-November races, the one-time December result was 79/147 = 53.7415%. The existing strict current-best fallback scored 80/147 = 54.4218% on the exact same `fold_c` race IDs, while its project-wide current-best report remains 81/147 = 55.1020% on the canonical `test` alias and 53.8462% at the robust floor.

- Observation: The already-materialized broad 67-component OOF prediction cache cannot replace the support-union candidate surface.
  Evidence: Its 1,319-race `fold_a` train surface has at most 41.6224% answer coverage across every unique component output, and October validation has only 50.8621% coverage. The support-union October surface retains 93.1034%, so the more expensive candidate-row replay is necessary.

- Observation: The repository's public-data client can discover races monthly, but the current wrapper only exposes a day-and-meeting call and the collection routes require callers to know race numbers already.
  Evidence: The official `API72_2` contract accepts `rc_year`, `rc_month`, and optional `meet`, while `KRAAPIService.get_race_plan` currently fixes `rc_date`, `meet`, `numOfRows=50`, and `pageNo=1`. No KRA credential is available in the current environment, so live backfill remains blocked until configuration is supplied.

- Observation: The official Laya fine-tuning result depends on adapting the encoder, not only the typed-decision head.
  Evidence: The pinned notebook trains the full encoder at `2.5e-5` and the decision head at `1e-4` over 1,200 cases. On the expanded KRA data, head-only training peaked at 10.3448%, while one full-encoder epoch reached 30.1724% and reduced validation NLL from 2.80764 to 2.44217.

- Observation: Choice accuracy and top-three prediction accuracy diverge when the expected option is `NONE`.
  Evidence: A model may correctly detect that its candidate pool missed the answer without producing the required three-horse combination. The v2/v3 evaluators therefore report `top3_exact_accuracy` separately and use it as the primary checkpoint-selection metric.

## Decision Log

- Decision: Use Laya as a second-stage candidate reranker, not as a replacement for public-data collection or the first-stage horse models.
  Rationale: The repository already has a high-coverage candidate pool and a large gap between pool oracle and selected exact rate. Laya's typed `choice` primitive directly matches the remaining decision.
  Date/Author: 2026-10-01 / Codex

- Decision: Keep Laya and Torch dependencies out of `apps/api` during research.
  Rationale: The API targets Python 3.13 and currently has no Torch or Transformers dependency. An isolated research environment keeps production installs and tests stable until the approach earns promotion.
  Date/Author: 2026-10-01 / Codex

- Decision: Treat one race as one independent supervised example even when option-order permutations or auxiliary questions are generated.
  Rationale: Augmentations from the same race share the same outcome and must never inflate sample counts or cross a temporal split boundary.
  Date/Author: 2026-10-01 / Codex

- Decision: Audit capacity before building or downloading the model.
  Rationale: The costliest failure mode is training on duplicated, incomplete, temporally unsafe, or much smaller-than-assumed race data. The audit is fast, dependency-light, and reusable for every backfill.
  Date/Author: 2026-10-01 / Codex

- Decision: Replace the new single-ensemble rank-pattern options with the repository's strict prior-date support-union candidate rows for the first Laya probe.
  Rationale: The former has a 61.75% weakest-block ceiling, while the latter stays above 93% across the canonical rolling windows and already fits within Laya's approximately 20-choice operating range.
  Date/Author: 2026-10-01 / Codex

- Decision: Use `fold_a`, `fold_b`, and `fold_c` as train, validation, and final test for the first specialization probe, and ignore the overlapping `dev` and `test` aliases.
  Rationale: The three rolling windows are date-disjoint and preserve an untouched December test period. The aliases overlap `fold_b` and `fold_c` and would duplicate races across splits.
  Date/Author: 2026-10-01 / Codex

- Decision: Keep every race by adding a deterministically permuted `NONE` option and cap ordinary combinations at 19.
  Rationale: Silently dropping the 19 races whose answers are outside the retained candidate pool would inflate accuracy. The explicit choice preserves full coverage while keeping the total option count at 20 or less.
  Date/Author: 2026-10-01 / Codex

- Decision: Use compact integer-vector criteria, labels `A` through `T`, and `head_max_len=512`.
  Rationale: Candidate score fields were invisible under the shipped 256-token budget. Source, ensemble, member, and probability values retain thousandth precision, runner rates retain documented integer scales, and the resulting 512-token sequence audit has zero candidate or state loss.
  Date/Author: 2026-10-01 / Codex

- Decision: Reject the first head-only Laya checkpoint and keep the December test split sealed.
  Rationale: Validation exact accuracy did not improve over zero-shot. A lower validation NLL alone cannot justify touching the final test or integrating the model.
  Date/Author: 2026-10-01 / Codex

- Decision: Freeze the XGBoost depth-4, 100-estimator feature ranker before final-test inference.
  Rationale: It is the best validation-only model in the declared grid, has full race coverage, uses only fields already proven pre-race-safe in the Laya surface, and reproduces byte for byte after refitting on train plus validation. Freezing its specification and model hash prevents post-test tuning.
  Date/Author: 2026-10-01 / Codex

- Decision: Do not promote either the Laya checkpoint or its XGBoost control, and retire the current December holdout from future model selection.
  Rationale: Laya failed validation outright, and the frozen control lost one exact hit to the existing strict fallback on the same final-test universe. Further tuning against December would convert the holdout into validation data. The next credible experiment needs more prior races and a newly designated forward window.
  Date/Author: 2026-10-01 / Codex

- Decision: Expand Laya training from the `fold_a` target-train surface, but export no test split.
  Rationale: The repository already has audited date-ordered OOF coverage for all 1,319 races through September and a strict October validation surface. Training-time upstream policy selection still uses the complete target training period, so these rows are valid training material rather than deployment-equivalent performance evidence. Omitting a test file prevents accidental reuse of the spent December outcomes.
  Date/Author: 2026-10-01 / Codex

- Decision: Continue Laya only through staged full-encoder validation probes; do not extend the failed head-only route or touch December again.
  Rationale: Full encoder adaptation produced a large first-epoch gain, while head-only training and the expanded feature control both failed their same-window baselines. Further compute is justified only while October top-three accuracy improves materially, and promotion still requires a newly collected forward holdout.
  Date/Author: 2026-10-02 / Codex

## Outcomes & Retrospective

The Laya route now has a deterministic 1,319-race OOF training corpus and a lossless 116-race October validation corpus, with candidate ceilings of 85.60% and 93.10%. Expanded head-only Laya remains ineffective at 10.34%, while official-style full-encoder adaptation reaches 30.17% after one epoch. That gain proves domain adaptation is functioning, but it remains below the expanded feature control at 49.14% and the strict fallback at 54.31% on identical October races. No model is promoted. A staged continuation may test whether full-encoder validation keeps improving, but any promotion claim still requires new public-data backfill and a forward holdout because December 2025 is spent.

## Context and Orientation

The repository is a pnpm monorepo. Research scripts live in `packages/scripts/autoresearch/`, while API collection code lives in `apps/api/`. The cached clean training rows are built by `packages/scripts/autoresearch/search_clean_model.py` and contain one row per race entry, an `answers` mapping from `race_id` to the actual unordered top three, and a `race_lookup` mapping to the source race payload. A `race_id` begins with an eight-digit race date, followed by meeting and race number.

A candidate is one unordered tuple of three distinct `chulNo` runner numbers. A candidate surface is the complete set of candidate rows available to the second-stage selector for each race. A strict prior-date candidate surface means every learned value used to create or score candidates for a race was fitted only on dates earlier than that race date. Same-day outcomes are unavailable, even for later races on the same card.

Laya is a non-generative typed-decision model. For this project, every race becomes one `choice` question. The state contains compact pre-race race and runner context. Each criterion describes one candidate combination and compact first-stage scores. The expected value is the opaque label assigned to the candidate equal to the official unordered top three. The option labels must be opaque and deterministically permuted so the model cannot learn that the first option is preferred. Candidate descriptions, not labels, carry meaning.

The existing live 19-option builder is `packages/scripts/autoresearch/single_combo_live_probability_current_miss_candidate_features.py`. The current historical probability candidate helper is `packages/scripts/autoresearch/clean_release_horse_rank_pattern_top20_probability_selector_probe.py`, but its train-candidate path is not sufficient for strict prior-date Laya evidence. The existing split and target rules are in `packages/scripts/autoresearch/clean_model_config.json`.

## Plan of Work

First, add `packages/scripts/autoresearch/single_combo_laya_data_capacity_audit.py`. It must accept either an explicit joblib row cache or the repository's configured row cache. It will profile the intended race-entry grain, validate the composite key `(race_id, chulNo)`, check that every usable race has exactly three distinct answer horses present among its runners, measure feature missingness, and project unique-race capacity from requested raw row counts. Its JSON result is diagnostic and never counts toward the 70% goal.

Second, add a strict prior-date candidate replay module. It will group races by complete race date, fit first-stage models only on earlier dates, predict all races on the active date without using active labels, produce no more than 19 unique candidates per race, and attach a timing manifest proving the fit cutoff for every race. A configurable warm-up period may omit early races from model fitting, but evaluation metrics must report those omissions and the main 70% gate may not silently skip them.

Third, add the Laya dataset exporter. It will join the candidate surface to the clean row cache and answer key, reject any timing-contract violation, keep all examples from one race in one date-based split, and write canonical JSONL plus a manifest containing source hashes, race counts, candidate-oracle coverage, option-count distributions, split boundaries, and feature rendering version. It will use exactly one primary `choice` target per race. Auxiliary examples, if added, remain tagged as augmentations and are excluded from independent-race counts.

Fourth, create an isolated Laya environment and run three evaluations on identical race IDs: the existing fallback selector, the unmodified Laya checkpoint, and the specialized checkpoint. Report exact 3-of-3 rate, per-window minimum, confidence calibration, candidate oracle, missing-race count, and option-order sensitivity. Fit calibration temperatures only on the validation period. The final test and rolling windows remain untouched by model or prompt selection.

Finally, promote only if the new selector improves the strict robust exact rate, covers the full required race universe, passes leakage tests, and remains reproducible from frozen artifacts. Commit and push each validated checkpoint on the active research branch. Do not merge a model merely because it improves a diagnostic oracle, in-sample score, top-k portfolio score, or a subset with skipped races.

## Concrete Steps

From the repository root, run the focused capacity tests:

    .venv/bin/python -m pytest -q packages/scripts/autoresearch/tests/test_single_combo_laya_data_capacity_audit.py

Generate the current capacity artifact:

    .venv/bin/python packages/scripts/autoresearch/single_combo_laya_data_capacity_audit.py --output .cache/autoresearch/single_combo_laya_data_capacity_audit.json --require-pass

Inspect the concise fields:

    jq '{status, grain, date_coverage, label_quality, duplicate_quality, missingness, projections}' .cache/autoresearch/single_combo_laya_data_capacity_audit.json

Later milestones will add exact commands for zero-shot evaluation, specialization, calibration, and strict comparison. Record actual command transcripts here as those interfaces become real.

Generate the temporal Laya dataset:

    .venv/bin/python packages/scripts/autoresearch/single_combo_laya_temporal_dataset_export.py --output-dir .cache/autoresearch/laya_temporal_dataset --require-pass

Validate all splits against the pinned official Laya source:

    for split in train validation test; do PYTHONPATH=.cache/vendor/laya .venv/bin/python -m laya.evals_cli validate ".cache/autoresearch/laya_temporal_dataset/${split}.jsonl"; done

The pinned source revision for this validation is `6d942c92081fbc139e736bbd9ac0023223c29b7f`, which reports Laya version 0.3.22.

Generate the option-order specialization data and run the head-only validation probe:

    .venv/bin/python packages/scripts/autoresearch/single_combo_laya_specialization_dataset.py --require-pass
    PYTORCH_ENABLE_MPS_FALLBACK=1 .cache/laya-venv/bin/python packages/scripts/autoresearch/single_combo_laya_mps_specialize.py --epochs 8 --micro-batch 1 --eval-batch 4 --grad-accum 8

The probe uses the pinned model bundle revision `55cf4c4ebb4ebe31b2550e8bdf3bd21b99753851`, selects epochs on validation exact accuracy with NLL as a tie-breaker, and writes only diagnostic artifacts under `.cache/autoresearch/laya_specialization/head_only_best`.

Select and freeze the candidate-feature control without opening the test split:

    .venv/bin/python packages/scripts/autoresearch/single_combo_laya_feature_ranker.py --require-pass

Only after the selection manifest and frozen-model hash are recorded, run the one-time sealed evaluation:

    .venv/bin/python packages/scripts/autoresearch/single_combo_laya_feature_ranker.py --evaluate-test --require-pass

Materialize the expanded OOF training candidates and export train plus October validation only:

    .venv/bin/python packages/scripts/autoresearch/single_combo_laya_oof_training_dataset.py --refresh-candidate-cache --progress-every 10 --require-pass

Validate both expanded splits with the pinned official parser:

    for split in train validation; do PYTHONPATH=.cache/vendor/laya .cache/laya-venv/bin/python -m laya.evals_cli validate ".cache/autoresearch/laya_oof_training_dataset/${split}.jsonl"; done

Run the feature control without opening any test file:

    .venv/bin/python packages/scripts/autoresearch/single_combo_laya_feature_ranker.py --train .cache/autoresearch/laya_oof_training_dataset/train.jsonl --validation .cache/autoresearch/laya_oof_training_dataset/validation.jsonl --output-dir .cache/autoresearch/laya_oof_feature_ranker --require-pass

## Validation and Acceptance

The capacity milestone is accepted when its focused tests pass and the current row cache reports 18,742 rows, 1,758 unique races, zero duplicate `(race_id, chulNo)` keys, 1,758 complete valid top-three labels, a date range from 20250103 through 20251228, and approximately 10.5% missing feature cells. The artifact must explicitly set `counts_as_70_percent_evidence` to false.

The dataset milestone is accepted when every JSONL line validates under Laya's official evaluation parser, every race appears in exactly one temporal split, every expected choice maps to exactly one candidate, all options are distinct unordered three-horse combinations, and changing answer keys without rebuilding candidates does not change state or criteria fields.

The model milestone is accepted only when predictions cover the full configured evaluation universe and the strict walk-forward report compares the same race IDs against the existing baseline. A 70% claim requires at least 0.70 exact 3-of-3 on the designated test window and every required rolling robustness gate, with no skipped-race, post-race, in-sample, or candidate-oracle substitution.

## Idempotence and Recovery

Every artifact command writes to an explicit output path and may be rerun safely. Source hashes and format versions make stale outputs detectable. Interrupted model downloads and training runs must stay outside tracked source directories. If a backfill changes row counts, regenerate the capacity audit and candidate manifest before reusing any Laya dataset. Never repair a temporal violation by deleting the offending evaluation races; fix the source or mark the experiment diagnostic-only.

## Artifacts and Notes

The initial measured cache profile is:

    rows=18742
    races=1758
    mean_runner_rows_per_race=10.661
    complete_top3_labels=1758
    feature_count=86
    missing_feature_cell_rate=0.105
    date_min=20250103
    date_max=20251228

The current lossless v5 temporal dataset hashes are:

    train.jsonl      0b0413419fedd520e8ea20051f9ea61273cdb99f02f76edc3807c00dd7524933
    validation.jsonl d141fa1fa04c58c46684aa098fffbac8cbd0447e89a5578f20b16d3697fb68a7
    test.jsonl       1b288dac4d45ffbef785dfc8cc21cc84c120a7c158fb1f4ceaafbdaca5286e4b
    manifest.json    4a061e2ca6f877739a474fbf8673ff7cdf05323f01f43c83b25792256c8483ed
    augmented train  9e975275564d1264b0754ddc40d7074f73dd663fed7ec39fa649d06fe9ad1e49

The selected head-only checkpoint is diagnostic only:

    base model SHA-256  4fa56de72383a9d3efa9cfa78955733c81b9fc8067a587ca4beb82c78107a24e
    checkpoint SHA-256  03d75b14470b5b190e171078a641973c741384bb7f2604c5c5eecae463730f0a
    zero-shot validation 11/176 = 0.0625
    selected validation  11/176 = 0.0625
    selected epoch        5
    final test inference  not run

The frozen feature-ranker selection is:

    selected specification  xgb_pairwise_d4_e100
    default validation      88/176 = 0.500000
    selected validation    106/176 = 0.602273
    frozen fit races       292
    frozen model SHA-256   f4770458fc121db3d30a2c070420c28f1cd6361a37eb13ed2af73a29130cbb56
    selection manifest     8f2c94153a94bac7818421bda717d87efa808ee280093c0474d788d22bf7d7fb
    frozen test            79/147 = 0.537415
    strict fold_c baseline 80/147 = 0.544218
    test delta             -1 race / -0.006803
    goal met               false

The official Laya evaluation row shape used by this plan is equivalent to:

    {"state": {...}, "questions": {"top3_combo": {"type": "choice", "instructions": "Select the most likely unordered top-three combination.", "criteria": {"A": "...", "B": "..."}}}, "expected": {"top3_combo": "B"}, "tags": ["split:train"], "language": "en"}

Use English field names and terse option descriptions for the first probe because the English and typed-decisions checkpoints use a constrained option-token budget. Korean display names are not required for numerical KRA features.

## Interfaces and Dependencies

`packages/scripts/autoresearch/single_combo_laya_data_capacity_audit.py` must expose:

    def audit_row_cache(row_cache: dict[str, Any], *, projected_row_counts: tuple[int, ...], target_unique_races: int) -> dict[str, Any]

The function must use only the standard library and the already-installed row-cache dependencies. Joblib loading belongs only in the CLI/source-loading boundary. Tests call the pure function with small dictionaries.

The later candidate surface must expose a format version and a per-race timing record containing `race_id`, `race_date`, `fit_through_date`, `selection_uses_active_date_labels`, and `selection_uses_future_labels`. The Laya exporter must reject a row unless the fit date is strictly earlier than the race date and both label-use flags are false.

Revision note, 2026-10-01 / Codex: Created the dedicated Laya reranker ExecPlan after confirming public-data scale and identifying that the existing historical train-candidate helper is not a strict prior-date replay surface.

Revision note, 2026-10-01 / Codex: Recorded the completed capacity-audit milestone and its real-cache evidence. The next implementation milestone is the strict prior-date candidate surface.

Revision note, 2026-10-01 / Codex: Recorded the completed strict rank-pattern replay, rejected it because of its 61.75% weakest-block oracle, and selected the existing support-union rolling surface for the first leakage-safe Laya dataset.

Revision note, 2026-10-01 / Codex: Completed the deterministic temporal dataset exporter, official Laya parser validation, label-leakage audit, bounded-input rendering, and byte reproducibility check. The next milestone is a pinned zero-shot baseline followed by train-only specialization and validation-only selection.

Revision note, 2026-10-01 / Codex: Completed lossless v5 token rendering and the first pinned head-only specialization. The checkpoint failed to improve validation exact accuracy, so the test split remains sealed and the next step is a simple feature-baseline diagnosis before expanding trainable Laya layers.

Revision note, 2026-10-01 / Codex: Froze the validation-selected candidate-feature control at 60.23%. This establishes that the current fields generalize materially better than Laya and creates a precommitted model for one sealed-test evaluation.

Revision note, 2026-10-01 / Codex: Completed the one-time frozen test. The feature ranker fell to 53.74% and lost one race to the strict current-best fallback on identical IDs, so no promotion or merge is allowed. The December holdout is now spent; further Laya work requires a larger prior-date corpus and a new forward window.

Revision note, 2026-10-01 / Codex: Added the reusable `fold_a` inner-OOF candidate cache and train-plus-October exporter after rejecting the low-ceiling 67-component shortcut. The code and one-date CLI smoke are complete; full 112-date materialization and validation remain in progress, and no test split is emitted.

Revision note, 2026-10-02 / Codex: Completed the 1,319-race OOF dataset, corrected `NONE`-inflated scoring, rejected the expanded head-only and feature controls, and validated official-style full-encoder Laya adaptation at 30.17% after one epoch. No model is promoted; staged October-only continuation and a new forward holdout remain.
