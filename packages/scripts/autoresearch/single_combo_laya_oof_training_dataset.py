"""Build a larger Laya training set from date-ordered OOF candidate rows."""

# ruff: noqa: E402

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import joblib

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from autoresearch import (  # noqa: E402
    clean_release_row_feature_full_policy_horse_membership_frontier_support_union_train_seeded_online_pairwise_current_best_repro_diagnostic as focused,
)
from autoresearch import (  # noqa: E402
    clean_release_row_feature_full_policy_horse_membership_probe as horse_membership,
)
from autoresearch import (  # noqa: E402
    clean_release_row_feature_full_policy_horse_membership_wide_online_repair_diagnostic as membership_repair,
)
from autoresearch import (  # noqa: E402
    single_combo_frontier_support_union_pairwise_inner_oof_train_surface as inner_oof,
)
from autoresearch import (  # noqa: E402
    single_combo_laya_temporal_dataset_export as laya_export,
)
from autoresearch.clean_release_current_horse_top20_probability_ranker_probe import (  # noqa: E501
    DEFAULT_POLICY_SOURCE,
)
from autoresearch.clean_release_row_feature_full_policy_classifier_probe import (  # noqa: E501
    DEFAULT_CACHE_DIR,
    DEFAULT_CONFIG,
)
from autoresearch.search_clean_model import (  # noqa: E402
    _load_or_build_row_cache,
    _read_json,
)
from autoresearch.single_combo_broad_component_train_surface_inventory import (  # noqa: E501
    TRAIN_PREDICTION_CONTRACT,
)

FORMAT_VERSION = "single-combo-laya-oof-training-dataset-v1"
CANDIDATE_CACHE_FORMAT_VERSION = "single-combo-laya-oof-candidate-cache-v1"
DEFAULT_SOURCE_CANDIDATE_CACHE = (
    DEFAULT_CACHE_DIR / "single_combo_primary_route_candidate_rows.joblib"
)
DEFAULT_OUTPUT_DIR = DEFAULT_CACHE_DIR / "laya_oof_training_dataset"
DEFAULT_CANDIDATE_CACHE = DEFAULT_OUTPUT_DIR / "candidate_rows.joblib"
DEFAULT_TRAIN_WINDOW = "fold_a"
DEFAULT_VALIDATION_WINDOW = "fold_a"
DEFAULT_SEED = "kra-laya-oof-training-v1"


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _normal_answer(value: Any) -> tuple[int, int, int]:
    answer = laya_export._answer(value)
    if answer is None:
        raise ValueError(f"invalid unordered top-three answer: {value!r}")
    return answer


def _candidate_count(rows_by_race: dict[str, list[dict[str, Any]]]) -> int:
    return sum(len(rows) for rows in rows_by_race.values())


def _candidate_summary(
    rows_by_race: dict[str, list[dict[str, Any]]],
    answers: dict[str, list[int]],
) -> dict[str, Any]:
    raw_counts: list[int] = []
    retained_counts: list[int] = []
    raw_hits = 0
    retained_hits = 0
    for race_id, rows in sorted(rows_by_race.items()):
        answer = _normal_answer(answers[race_id])
        raw_combos = {
            combo
            for row in rows
            if (combo := laya_export._combo(row.get("combo"))) is not None
        }
        retained = laya_export._retained_candidates(rows)
        retained_combos = {
            _normal_answer(row["combo"])
            for row in retained
        }
        raw_counts.append(len(raw_combos))
        retained_counts.append(len(retained_combos))
        raw_hits += int(answer in raw_combos)
        retained_hits += int(answer in retained_combos)
    race_count = len(rows_by_race)
    return {
        "race_count": race_count,
        "candidate_row_count": _candidate_count(rows_by_race),
        "raw_candidate_count_distribution": dict(sorted(Counter(raw_counts).items())),
        "retained_candidate_count_distribution": dict(
            sorted(Counter(retained_counts).items())
        ),
        "raw_candidate_oracle_exact_rate": round(
            raw_hits / max(race_count, 1), 6
        ),
        "retained_candidate_oracle_exact_rate": round(
            retained_hits / max(race_count, 1), 6
        ),
    }


def _validate_source_eval_cache(payload: dict[str, Any], window_name: str) -> None:
    if payload.get("format_version") != laya_export.SOURCE_FORMAT_VERSION:
        raise ValueError("source evaluation cache format is not supported")
    if payload.get("selection_contract") != laya_export.SOURCE_SELECTION_CONTRACT:
        raise ValueError("source evaluation cache selection contract is not supported")
    if payload.get("timing_contract") != laya_export.SOURCE_TIMING_CONTRACT:
        raise ValueError("source evaluation cache timing contract is not supported")
    if payload.get("is_partial_window_cache") is not False:
        raise ValueError("source evaluation cache must contain every canonical window")
    rows_by_window = payload.get("candidate_rows_by_window")
    answers_by_window = payload.get("answers_by_window")
    if not isinstance(rows_by_window, dict) or window_name not in rows_by_window:
        raise ValueError(f"source evaluation cache is missing {window_name} rows")
    if not isinstance(answers_by_window, dict) or window_name not in answers_by_window:
        raise ValueError(f"source evaluation cache is missing {window_name} answers")


def materialize_candidate_cache(
    *,
    config_path: Path = DEFAULT_CONFIG,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    policy_source: Path = DEFAULT_POLICY_SOURCE,
    source_candidate_cache_path: Path = DEFAULT_SOURCE_CANDIDATE_CACHE,
    output_path: Path = DEFAULT_CANDIDATE_CACHE,
    train_window: str = DEFAULT_TRAIN_WINDOW,
    validation_window: str = DEFAULT_VALIDATION_WINDOW,
    max_rank: int = 10,
    candidate_preset: str = "cached-best",
    max_date_groups: int | None = None,
    progress_every: int = 10,
) -> dict[str, Any]:
    """Materialize reusable train OOF and strict validation candidate rows."""

    started = time.time()
    focused._apply_candidate_preset(candidate_preset)
    windows, prepared_by_prefix = inner_oof._prepare_support_inputs(
        config_path=config_path,
        cache_dir=cache_dir,
        max_rank=max_rank,
        window_names=(train_window,),
    )
    horse_windows, horse_prepared = inner_oof._prepare_horse_inputs(
        config_path=config_path,
        cache_dir=cache_dir,
        max_rank=membership_repair.HORSE_MAX_RANK,
        window_names=(train_window,),
    )
    if len(windows) != 1 or len(horse_windows) != 1:
        raise ValueError("exactly one train window must be selected")
    if windows[0].name != horse_windows[0].name:
        raise ValueError("support and horse-membership windows do not align")

    horse_payload = horse_prepared[
        (train_window, horse_membership.MAX_FEATURE_DIRECTIONS)
    ]
    train_rows, _warmup_rows, train_answers, seed_diagnostics = (
        inner_oof._build_inner_oof_seed_rows_by_race(
            prepared_by_prefix=prepared_by_prefix,
            horse_payload=horse_payload,
            surface=focused.SURFACE,
            union_spec=focused.UNION_SPEC,
            window_name=train_window,
            max_date_groups=max_date_groups,
            progress_started=started,
            progress_every=progress_every,
        )
    )

    source_eval_cache = joblib.load(source_candidate_cache_path)
    if not isinstance(source_eval_cache, dict):
        raise ValueError("source evaluation cache must be a dictionary")
    _validate_source_eval_cache(source_eval_cache, validation_window)
    validation_rows = source_eval_cache["candidate_rows_by_window"][validation_window]
    validation_answers = source_eval_cache["answers_by_window"][validation_window]

    payload = {
        "format_version": CANDIDATE_CACHE_FORMAT_VERSION,
        "diagnostic_only": True,
        "counts_as_70_percent_evidence": False,
        "train_prediction_contract": TRAIN_PREDICTION_CONTRACT,
        "train_window": train_window,
        "validation_window": validation_window,
        "is_partial_date_group_surface": max_date_groups is not None,
        "candidate_preset": candidate_preset,
        "max_rank": max_rank,
        "surface_spec": focused.SURFACE.name,
        "support_union_spec": focused.UNION_SPEC.name,
        "candidate_rows_by_split": {
            "train": train_rows,
            "validation": validation_rows,
        },
        "answers_by_split": {
            "train": train_answers,
            "validation": validation_answers,
        },
        "source_contracts": {
            "train_dynamic_fit": "completed_prior_target_train_dates_only",
            "train_upstream_selection_scope": "target_window_training_period",
            "validation_timing": laya_export.SOURCE_TIMING_CONTRACT,
            "label_usage": "labels_attached_after_candidate_generation",
        },
        "seed_diagnostics": seed_diagnostics,
        "source_eval_cache_path": str(source_candidate_cache_path),
        "source_eval_cache_sha256": _sha256_file(source_candidate_cache_path),
        "config_path": str(config_path),
        "config_sha256": _sha256_file(config_path),
        "split_summaries": {
            "train": _candidate_summary(train_rows, train_answers),
            "validation": _candidate_summary(validation_rows, validation_answers),
        },
        "elapsed_seconds": round(time.time() - started, 2),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(payload, output_path, compress=0)
    return payload


def _window(config: dict[str, Any], name: str) -> dict[str, str]:
    windows = laya_export._rolling_windows(config)
    if name not in windows:
        raise ValueError(f"config is missing rolling window {name}")
    return windows[name]


def build_laya_oof_dataset(
    *,
    candidate_cache: dict[str, Any],
    row_cache: dict[str, Any],
    config: dict[str, Any],
    seed: str = DEFAULT_SEED,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Render train and validation JSONL rows from a materialized candidate cache."""

    if candidate_cache.get("format_version") != CANDIDATE_CACHE_FORMAT_VERSION:
        raise ValueError("candidate cache format is not supported")
    if candidate_cache.get("train_prediction_contract") != TRAIN_PREDICTION_CONTRACT:
        raise ValueError("candidate cache is missing the date-ordered OOF contract")
    if candidate_cache.get("is_partial_date_group_surface") is not False:
        raise ValueError("candidate cache must cover every target train date group")
    raw_rows_by_split = candidate_cache.get("candidate_rows_by_split")
    raw_answers_by_split = candidate_cache.get("answers_by_split")
    if not isinstance(raw_rows_by_split, dict) or not isinstance(
        raw_answers_by_split, dict
    ):
        raise ValueError("candidate cache is missing split rows or answers")

    train_window_name = str(candidate_cache.get("train_window") or "")
    validation_window_name = str(candidate_cache.get("validation_window") or "")
    train_window = _window(config, train_window_name)
    validation_window = _window(config, validation_window_name)
    clean_rows = row_cache.get("rows")
    master_answers = row_cache.get("answers")
    if not isinstance(clean_rows, list) or not isinstance(master_answers, dict):
        raise ValueError("row cache is missing clean rows or answers")
    clean_rows_by_race = laya_export._rows_by_race(clean_rows)

    datasets: dict[str, list[dict[str, Any]]] = {}
    split_summaries: dict[str, Any] = {}
    rendered_race_ids: dict[str, set[str]] = {}
    source_label_violations: list[str] = []
    answer_mismatches: list[str] = []
    missing_clean_rows: list[str] = []
    timing_violations: list[str] = []

    for split_name in ("train", "validation"):
        rows_by_race = raw_rows_by_split.get(split_name)
        answers = raw_answers_by_split.get(split_name)
        if not isinstance(rows_by_race, dict) or not isinstance(answers, dict):
            raise ValueError(f"candidate cache is missing {split_name} data")
        if set(rows_by_race) != set(answers):
            raise ValueError(f"{split_name} candidate and answer race IDs differ")

        examples: list[dict[str, Any]] = []
        candidate_hits = 0
        none_targets = 0
        raw_candidate_counts: list[int] = []
        retained_candidate_counts: list[int] = []
        for race_id in sorted(rows_by_race):
            race_date = laya_export._race_date(race_id)
            if split_name == "train":
                if not race_date or race_date > train_window["train_end"]:
                    timing_violations.append(f"train:{race_id}")
            elif not (
                validation_window["train_end"] < race_date
                and validation_window["eval_start"]
                <= race_date
                <= validation_window["eval_end"]
            ):
                timing_violations.append(f"validation:{race_id}")

            answer = _normal_answer(answers[race_id])
            master_answer = master_answers.get(race_id)
            if master_answer is None or _normal_answer(master_answer) != answer:
                answer_mismatches.append(race_id)
            race_rows = clean_rows_by_race.get(race_id)
            if not race_rows:
                missing_clean_rows.append(race_id)
                continue
            candidates = rows_by_race[race_id]
            if not isinstance(candidates, list) or not all(
                isinstance(row, dict) for row in candidates
            ):
                raise ValueError(f"invalid candidate rows for {race_id}")
            source_label_violations.extend(
                laya_export._validate_source_candidate_labels(
                    race_id,
                    candidates,
                    answer,
                )
            )
            retained = laya_export._retained_candidates(candidates)
            example, candidate_hit = laya_export._render_example(
                race_id=race_id,
                split_name=split_name,
                source_window=(
                    f"{train_window_name}:inner_oof"
                    if split_name == "train"
                    else validation_window_name
                ),
                race_rows=race_rows,
                candidates=candidates,
                answer=answer,
                seed=seed,
            )
            examples.append(example)
            candidate_hits += int(candidate_hit)
            none_targets += int(not candidate_hit)
            raw_candidate_counts.append(len(candidates))
            retained_candidate_counts.append(len(retained))

        datasets[split_name] = examples
        rendered_race_ids[split_name] = {
            str(row["state"]["race_id"]) for row in examples
        }
        split_summaries[split_name] = {
            "race_count": len(examples),
            "date_min": min(
                (laya_export._race_date(race_id) for race_id in rendered_race_ids[split_name]),
                default=None,
            ),
            "date_max": max(
                (laya_export._race_date(race_id) for race_id in rendered_race_ids[split_name]),
                default=None,
            ),
            "candidate_hit_count": candidate_hits,
            "none_target_count": none_targets,
            "retained_candidate_oracle_exact_rate": round(
                candidate_hits / max(len(examples), 1), 6
            ),
            "raw_candidate_count_distribution": dict(
                sorted(Counter(raw_candidate_counts).items())
            ),
            "retained_candidate_count_distribution": dict(
                sorted(Counter(retained_candidate_counts).items())
            ),
        }

    overlap = sorted(rendered_race_ids["train"] & rendered_race_ids["validation"])
    train_dates = [
        laya_export._race_date(race_id) for race_id in rendered_race_ids["train"]
    ]
    validation_dates = [
        laya_export._race_date(race_id)
        for race_id in rendered_race_ids["validation"]
    ]
    chronological = bool(
        train_dates
        and validation_dates
        and max(train_dates) < min(validation_dates)
    )
    rendered_keys = laya_export._rendered_keys(datasets)
    forbidden_rendered_keys = sorted(
        rendered_keys & laya_export.FORBIDDEN_RENDERED_KEYS
    )
    passed = not any(
        (
            overlap,
            source_label_violations,
            answer_mismatches,
            missing_clean_rows,
            timing_violations,
            forbidden_rendered_keys,
        )
    ) and chronological
    manifest = {
        "format_version": FORMAT_VERSION,
        "rendering_version": laya_export.RENDERING_VERSION,
        "status": "passed" if passed else "failed",
        "diagnostic_only": True,
        "counts_as_70_percent_evidence": False,
        "seed": seed,
        "split_contract": "fold_a_inner_oof_train_then_fold_a_october_validation",
        "holdout_policy": "no_test_split_exported_december_2025_is_spent",
        "train_prediction_contract": TRAIN_PREDICTION_CONTRACT,
        "source_contracts": candidate_cache.get("source_contracts", {}),
        "split_summaries": split_summaries,
        "coverage": {
            "race_count": sum(len(rows) for rows in datasets.values()),
            "split_overlap_race_ids": overlap,
            "missing_clean_row_race_ids": sorted(missing_clean_rows),
        },
        "timing_audit": {
            "passed": not timing_violations and chronological,
            "chronological_split_order": chronological,
            "violations": sorted(timing_violations),
            "train_window": train_window_name,
            "validation_window": validation_window_name,
        },
        "leakage_audit": {
            "passed": not any(
                (
                    source_label_violations,
                    answer_mismatches,
                    forbidden_rendered_keys,
                )
            ),
            "source_label_consistency_violations": sorted(
                source_label_violations
            ),
            "master_answer_mismatches": sorted(answer_mismatches),
            "forbidden_rendered_keys": forbidden_rendered_keys,
            "candidate_label_fields_rendered": False,
        },
        "recommended_next_action": (
            "run_expanded_train_to_october_validation_control"
            if passed
            else "repair_oof_training_dataset_contract"
        ),
    }
    return datasets, manifest


def export_laya_oof_dataset(
    *,
    candidate_cache_path: Path = DEFAULT_CANDIDATE_CACHE,
    config_path: Path = DEFAULT_CONFIG,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    seed: str = DEFAULT_SEED,
) -> dict[str, Any]:
    candidate_cache = joblib.load(candidate_cache_path)
    if not isinstance(candidate_cache, dict):
        raise ValueError("candidate cache payload must be a dictionary")
    row_cache = _load_or_build_row_cache(
        config_path=config_path,
        cache_dir=cache_dir,
        refresh_cache=False,
    )
    config = _read_json(config_path)
    datasets, manifest = build_laya_oof_dataset(
        candidate_cache=candidate_cache,
        row_cache=row_cache,
        config=config,
        seed=seed,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    dataset_hashes: dict[str, str] = {}
    for split_name, rows in datasets.items():
        path = output_dir / f"{split_name}.jsonl"
        laya_export._write_jsonl(path, rows)
        dataset_hashes[split_name] = _sha256_file(path)
    manifest.update(
        {
            "candidate_cache_path": str(candidate_cache_path),
            "candidate_cache_sha256": _sha256_file(candidate_cache_path),
            "config_path": str(config_path),
            "config_sha256": _sha256_file(config_path),
            "dataset_sha256": dataset_hashes,
        }
    )
    _write_json(output_dir / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--policy-source", type=Path, default=DEFAULT_POLICY_SOURCE)
    parser.add_argument(
        "--source-candidate-cache",
        type=Path,
        default=DEFAULT_SOURCE_CANDIDATE_CACHE,
    )
    parser.add_argument("--candidate-cache", type=Path, default=DEFAULT_CANDIDATE_CACHE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--train-window", default=DEFAULT_TRAIN_WINDOW)
    parser.add_argument("--validation-window", default=DEFAULT_VALIDATION_WINDOW)
    parser.add_argument("--max-rank", type=int, default=10)
    parser.add_argument("--candidate-preset", default="cached-best")
    parser.add_argument("--max-date-groups", type=int)
    parser.add_argument("--progress-every", type=int, default=10)
    parser.add_argument("--refresh-candidate-cache", action="store_true")
    parser.add_argument("--materialize-only", action="store_true")
    parser.add_argument("--seed", default=DEFAULT_SEED)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()

    if args.refresh_candidate_cache or not args.candidate_cache.exists():
        candidate_cache = materialize_candidate_cache(
            config_path=args.config,
            cache_dir=args.cache_dir,
            policy_source=args.policy_source,
            source_candidate_cache_path=args.source_candidate_cache,
            output_path=args.candidate_cache,
            train_window=args.train_window,
            validation_window=args.validation_window,
            max_rank=args.max_rank,
            candidate_preset=args.candidate_preset,
            max_date_groups=args.max_date_groups,
            progress_every=args.progress_every,
        )
        print(
            json.dumps(
                {
                    "stage": "candidate_cache_materialized",
                    "candidate_cache": str(args.candidate_cache),
                    "train_races": candidate_cache["split_summaries"]["train"][
                        "race_count"
                    ],
                    "validation_races": candidate_cache["split_summaries"][
                        "validation"
                    ]["race_count"],
                    "elapsed_seconds": candidate_cache["elapsed_seconds"],
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            flush=True,
        )
    if args.materialize_only:
        return 0

    manifest = export_laya_oof_dataset(
        candidate_cache_path=args.candidate_cache,
        config_path=args.config,
        cache_dir=args.cache_dir,
        output_dir=args.output_dir,
        seed=args.seed,
    )
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "output_dir": str(args.output_dir),
                "race_count": manifest["coverage"]["race_count"],
                "split_summaries": manifest["split_summaries"],
                "dataset_sha256": manifest["dataset_sha256"],
                "recommended_next_action": manifest["recommended_next_action"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return int(args.require_pass and manifest["status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
