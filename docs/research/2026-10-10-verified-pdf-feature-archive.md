# Verified pre-race PDF feature archive

The original 28-race capture inventory now has a reproducible feature-consumption boundary. All PDF bytes, entry-sheet pages, capture ordering, complete joins, saved projections, and cutoff decisions are replayed before any features are exported. The export retains 28 race records, authorizes 27 sources and 282 horse rows, blocks the known Seoul name mismatch, and preserves the unresolved Busan meeting/date scope. This is source verification, not a new prediction model or evidence of 70% success.

## Scope and Grain

The horse-row key is `(race_id, chulNo)`; `hrNo` and the full official horse name are join metadata, not numeric features. The race inventory is distinct from the exported horse rows. A blocked race remains in the inventory with `fallback_required: true` and no PDF feature rows. Future model evaluation must supply a preregistered baseline fallback for that race, not evaluate only the 27 eligible races.

The scope is explicitly `capture_inventory_not_evaluation_universe`. API26 captures used a race-number request filter that was ignored in the observed responses. Those pages support verifying every target horse field they actually contain, but do not independently prove the full unfiltered day's race universe. The Busan October 11 response had no entries; its actual race universe is still unknown. No nationwide or complete evaluation denominator is claimed here.

The [earlier source contract](2026-10-10-race-card-pdf-source.md) contains acquisition timing, official source URLs, original coverage, missingness, and the full-name mismatch finding. No current-race outcome was fetched or loaded during this increment.

## Consumption Checks

`packages/scripts/autoresearch/kra_race_card_pdf_replay.py` reads only bounded local files under an explicit archive root. It rejects escaping paths and symlinks, wrong source URLs/identities/versions, altered byte counts or SHA-256 checksums, ambiguous JSON, missing provenance, incomplete or inconsistent API pages, and invalid timezone-aware capture ordering. It recomputes PDF parsing and the existing T30 audit and requires those results to match the archived output. A saved eligibility Boolean cannot authorize data by itself.

Some races share a same-meeting/same-date API capture originally requested for race 1. Replay validates that source capture's original canonical entry projection and every page, then derives the target race from the verified raw rows. It does not rewrite the source race identity, invent a timestamp, or allow cross-meeting/date reuse. The target must still pass declared field size, horse-ID uniqueness, schedule agreement, and a complete runner-number/full-name PDF join.

The bundle's input plan pins the PDF and entry manifest bytes and records implementation checksums and PDF dependency versions. Reusing it after implementation drift is rejected. Source availability after the plan's pin time is blocked, and future or naive pin timestamps are rejected. Pinning files now is distinct from the original acquisition time, and all timing evidence remains local observation rather than third-party attestation.

## Feature Interface

The fixed numeric projection contains `training_count`, `training_minutes`, `training_window_days`, `training_gu_count`, `training_seup_count`, `swimming_count`, `swimming_laps`, `trainer_wins`, and `trainer_win_rate`. Each field has a corresponding Boolean `*_missing` flag; null stays null and explicit zero stays zero. `training_summary_truncated` is a separate Boolean. Invalid nonfinite, negative, Boolean-as-number, or greater-than-100 trainer win-rate values block the whole race's projection.

Unprinted Jeju swimming/trainer statistics are not imputed as zero. Unknown Seoul/Busan training windows remain null and are not equated with Jeju's explicit two-week window. Raw panel text, historical tables, treatment descriptions, unrelated API fields, and outcomes are not part of this feature interface. There has been no feature weighting, hyperparameter selection, training, or accuracy comparison on this archive.

## Reproduction

Run from the clean worktree `/Users/coyasong/Developer/coyasong/kra-analysis-race-card-pdf`, with the existing PDF extra installed:

```sh
.venv/bin/python packages/scripts/autoresearch/kra_race_card_pdf_bundle.py \
  --cohort /Users/coyasong/Developer/coyasong/kra-analysis/.cache/autoresearch/race_card_pdf_snapshots/cohort_20261010_11_capture.json \
  --archive-root /Users/coyasong/Developer/coyasong/kra-analysis \
  --require-complete
```

The CLI writes `input_plan.json`, `feature_bundle.json`, and `export_summary.json` to a unique ignored `.cache/autoresearch/race_card_pdf_bundles/` directory. Reuse `--plan path/to/input_plan.json` instead of `--cohort` to enforce the existing pins. Export timestamps differ, but the race/feature content and input-plan checksum are reproducible. Previous observations and exports are never overwritten.

Exit 0 means a successful export (not a prediction or proof of a full evaluation universe). With `--require-complete`, an exported partial archive returns 2. Invalid planning input or output failure returns 1. The actual archive appropriately returns 2 because it includes one blocked race and an unresolved scope.

## Evidence

The focused offline suite passes 179 tests: 110 prior capture/parser/audit tests and 69 new replay/bundle tests. Dedicated PDF CI now exercises both new modules and their fixtures without API credentials or external requests. Ruff lint and formatting pass for all 15 source/test files, `uv lock --check` passes without dependency changes, and `git diff --check` passes.

Implementation is pushed and normally merged into main through [PR #61](https://github.com/coyaSONG/kra-analysis/pull/61), merge commit `f794ffc`, at 2026-10-09 17:08:16Z. [Required Python CI](https://github.com/coyaSONG/kra-analysis/actions/runs/37963820526) and the [dedicated PDF workflow](https://github.com/coyaSONG/kra-analysis/actions/runs/37963820598) pass, including all 179 PDF source tests. Scripts, Docker, and Gitleaks also pass. The broader security job still fails at its existing Python dependency audit; no new dependency, secret-scan exception, or protection override was introduced here.

The final cohort replay produced `.cache/autoresearch/race_card_pdf_bundles/20261009T165933.854898Z_51a041eda9e6/feature_bundle.json`, with SHA-256 `8061a185401bf72c4bfee2751529acb164b695eb2985dbf4d6a43e187a8ecdd6`. Its pinned input-plan SHA-256 is `0ac4a309d07901d6f4da8c4503c937fee9529fb5e05871cfdcd5252116a52be0`. Reusing that exact plan produced `20261009T170031.529322Z_69881123d72c/feature_bundle.json`, SHA-256 `bb75f109f1565c7b8239ba0cc42755eab85636353df8e912b5698fe7c0d541c6`. A sorted JSON comparison excluding only `exported_at` has no differences, including all raw evidence, identities, features, and blocker codes. Both exports preserve all 28 records, authorize 27 races/282 rows, and retain the unresolved Busan scope.

An earlier development run incorrectly required an entry manifest inside each target race directory and blocked 25 races, yielding only 3 eligible sources. That failed export is retained locally. The same-date shared-capture regression test and actual raw replay exposed and corrected the invalid folder assumption without relaxing any source identity or complete-join checks. It is not used as an evaluation subset.

## Remaining Research Gate

The next experiment needs a confirmed full future race universe, cutoff entry updates/scratches, one hashed baseline model with a reproducible inference path, and a limited predeclared training-feature ablation. Historical PDFs downloaded after racing are not strict pre-race training evidence solely because they have old server headers. Do not select again on the spent December 2025 holdout. Outcome-independent input registration and timestamped single-combination predictions must precede evaluation; uncertainty must be evaluated at the race/date level, not by treating horse rows as independent trials.

ChatGPT Pro advice remains pending the owner's login; no consultation occurred and no response was interrupted. The Goal tool reports `paused`; this increment is manually authorized work, not a claim that automatic Goal execution resumed. Existing broad-workspace dependency-audit failures remain outside this increment, with no protection override or broad secret-scan suppression.
