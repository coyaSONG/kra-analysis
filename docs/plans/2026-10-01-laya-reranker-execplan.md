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
- [ ] Export deterministic Laya train, validation, and test JSONL files grouped by complete race dates.
- [ ] Run a zero-shot baseline, a lightweight specialization probe, calibration, and the existing strict walk-forward comparison.
- [ ] Promote, commit, push, and integrate only a result that improves the existing strict single-combination baseline without weakening any leakage or coverage gate.

## Surprises & Discoveries

- Observation: Raw public-data row count is not the independent sample count.
  Evidence: The current cache has 18,742 rows but only 1,758 race decisions, or 10.661 runner rows per race. At that density, 100,000 rows project to roughly 9,380 independent races and 300,000 rows to roughly 28,140 races.

- Observation: The current live candidate path already produces exactly 19 options for every covered race.
  Evidence: `.cache/autoresearch/single_combo_live_probability_current_miss_candidate_features.json` reports 17 covered races and 19 merged candidates for each race, matching Laya's practical option-count guidance.

- Observation: Candidate availability is not the present bottleneck, but candidate selection is.
  Evidence: `.cache/autoresearch/clean_release_current_best_full_combo_delta_switch_after_broad_rank_segment_reanchor_rerun_repro_diagnostic.json` reports a 0.551020 robust selected exact rate and at least a 0.913793 robust candidate-pool oracle rate. The oracle uses labels and is only an upper-bound diagnostic, not valid performance evidence.

- Observation: Existing historical candidate helpers may fit their base horse models on the same rows they later expose as training candidates.
  Evidence: `_build_window_member_probabilities` uses `dates <= train_end` for fitting, while the synthetic train window can also evaluate dates through `train_end`. The Laya dataset must therefore use a new strict prior-date replay surface rather than treating those in-sample candidate features as deployment-equivalent evidence.

- Observation: A single ensemble rank ordering does not provide a robust enough 19-option ceiling.
  Evidence: The strict replay covered all 1,254 eligible races without timing violations, but its candidate oracle was 71.6906% overall and ranged from 61.7486% to 81.8898% by refit block. Because a reranker cannot select an answer absent from its options, this surface cannot support the 70% rolling-floor goal.

- Observation: The existing support-union surface is a much stronger match for Laya's bounded choice head.
  Evidence: `.cache/autoresearch/single_combo_primary_route_candidate_rows_summary.json` reports 11 to 20 candidates per race and pool-oracle rates of 93.1034% on `fold_a`, 96.5909% on `fold_b`, and 96.5986% on `fold_c`. The cache builder uses answer keys only to attach completed-race labels and calculate diagnostics; candidate combinations and their feature fields are formed without the active answer.

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

## Outcomes & Retrospective

The Laya route is approved for implementation but has not yet produced promotion evidence. The capacity audit passes, and the first strict 19-pattern replay has now ruled out a weak candidate representation without claiming model progress. The stronger support-union surface supplies 439 non-overlapping October-through-December races and a robust candidate ceiling above 93%, but this is still a small first probe compared with the planning target of 20,000 independent races. No selected-model metric changed in these milestones.

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

Later milestones will add exact commands for candidate replay, JSONL validation with `laya-evals validate`, zero-shot evaluation, specialization, and strict comparison. Record actual command transcripts here as those interfaces become real.

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

The official Laya evaluation row shape used by this plan is equivalent to:

    {"state": {...}, "questions": {"top3_combo": {"type": "choice", "instructions": "Select the most likely unordered top-three combination.", "criteria": {"C01": "...", "C02": "..."}}}, "expected": {"top3_combo": "C02"}, "tags": ["split:train"], "language": "en"}

Use English field names and terse option descriptions for the first probe because the English and typed-decisions checkpoints use a constrained option-token budget. Korean display names are not required for numerical KRA features.

## Interfaces and Dependencies

`packages/scripts/autoresearch/single_combo_laya_data_capacity_audit.py` must expose:

    def audit_row_cache(row_cache: dict[str, Any], *, projected_row_counts: tuple[int, ...], target_unique_races: int) -> dict[str, Any]

The function must use only the standard library and the already-installed row-cache dependencies. Joblib loading belongs only in the CLI/source-loading boundary. Tests call the pure function with small dictionaries.

The later candidate surface must expose a format version and a per-race timing record containing `race_id`, `race_date`, `fit_through_date`, `selection_uses_active_date_labels`, and `selection_uses_future_labels`. The Laya exporter must reject a row unless the fit date is strictly earlier than the race date and both label-use flags are false.

Revision note, 2026-10-01 / Codex: Created the dedicated Laya reranker ExecPlan after confirming public-data scale and identifying that the existing historical train-candidate helper is not a strict prior-date replay surface.

Revision note, 2026-10-01 / Codex: Recorded the completed capacity-audit milestone and its real-cache evidence. The next implementation milestone is the strict prior-date candidate surface.

Revision note, 2026-10-01 / Codex: Recorded the completed strict rank-pattern replay, rejected it because of its 61.75% weakest-block oracle, and selected the existing support-union rolling surface for the first leakage-safe Laya dataset.
