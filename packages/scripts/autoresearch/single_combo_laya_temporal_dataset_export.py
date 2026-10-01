"""Export strict temporal KRA candidate rows as Laya choice JSONL."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import joblib

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from autoresearch.clean_sparse_multichoice_policy_selector_probe import (  # noqa: E402
    DEFAULT_CACHE_DIR,
    DEFAULT_CONFIG,
)
from autoresearch.search_clean_model import (  # noqa: E402
    _load_or_build_row_cache,
    _read_json,
)

FORMAT_VERSION = "single-combo-laya-temporal-dataset-v1"
SOURCE_FORMAT_VERSION = "single-combo-primary-route-candidate-row-cache-v1"
SOURCE_SELECTION_CONTRACT = "primary_row_feature_support_union_candidate_row_cache"
SOURCE_TIMING_CONTRACT = "pre_race_candidate_features_with_completed_race_labels"
RENDERING_VERSION = "kra-laya-choice-rendering-v5"
QUESTION_ID = "top3_combo"
DEFAULT_SEED = "kra-laya-v1"
DEFAULT_CANDIDATE_CACHE = (
    DEFAULT_CACHE_DIR / "single_combo_primary_route_candidate_rows.joblib"
)
DEFAULT_OUTPUT_DIR = DEFAULT_CACHE_DIR / "laya_temporal_dataset"
SPLIT_WINDOWS = {
    "train": "fold_a",
    "validation": "fold_b",
    "test": "fold_c",
}
MAX_COMBO_OPTIONS = 19
NONE_OPTION = "NONE"
OPTION_LABELS = tuple("ABCDEFGHIJKLMNOPQRST")

RUNNER_FEATURES = (
    ("age", "age", 1),
    ("sex", "sex_code", 1),
    ("rating", "rating", 1),
    ("carried_x10", "wgBudam", 10),
    ("weight_delta", "weight_delta", 1),
    ("horse_place_x10", "horse_place_rate", 10),
    ("recent_top3_x1000", "recent_top3_rate", 1000),
    ("jockey_top3_x1000", "jockey_hist_top3_rate", 1000),
    ("trainer_top3_x1000", "trainer_hist_top3_rate", 1000),
    ("rest", "rest_days", 1),
)

FORBIDDEN_RENDERED_KEYS = {
    "answer",
    "answers",
    "exact_label",
    "match_label",
    "target",
}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _json_number(value: Any) -> int | float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    if number.is_integer():
        return int(number)
    return round(number, 8)


def _render_state_number(value: Any, scale: int) -> int | float | None:
    number = _json_number(value)
    if number is None:
        return number
    if scale != 1:
        return int(round(float(number) * scale))
    if isinstance(number, int):
        return number
    return round(number, 3)


def _format_integer(value: Any) -> str:
    number = _json_number(value)
    return "NA" if number is None else str(int(round(float(number))))


def _format_milli(value: Any) -> str:
    number = _json_number(value)
    return "NA" if number is None else str(int(round(float(number) * 1000)))


def _normalise_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _normalise_json(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, list | tuple):
        return [_normalise_json(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _sha256_json(value: Any) -> str:
    encoded = json.dumps(
        _normalise_json(value),
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return _sha256_bytes(encoded)


def _answer(value: Any) -> tuple[int, int, int] | None:
    if not isinstance(value, list | tuple) or len(value) < 3:
        return None
    try:
        answer = tuple(sorted(int(item) for item in value[:3]))
    except (TypeError, ValueError):
        return None
    return answer if len(set(answer)) == 3 else None


def _combo(value: Any) -> tuple[int, int, int] | None:
    return _answer(value)


def _race_date(race_id: str) -> str:
    prefix = str(race_id)[:8]
    return prefix if len(prefix) == 8 and prefix.isdigit() else ""


def _rows_by_race(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        race_id = str(row.get("race_id") or "")
        if race_id:
            grouped[race_id].append(row)
    return {
        race_id: sorted(race_rows, key=lambda row: int(row.get("chulNo", 0)))
        for race_id, race_rows in grouped.items()
    }


def _rolling_windows(config: dict[str, Any]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for raw in config.get("rolling_windows", []):
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or "")
        if not name:
            continue
        result[name] = {
            "train_end": str(raw.get("train_end") or ""),
            "eval_start": str(raw.get("eval_start") or ""),
            "eval_end": str(raw.get("eval_end") or ""),
        }
    return result


def _race_state(race_id: str, race_rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not race_rows:
        raise ValueError(f"missing clean rows for race {race_id}")
    first = race_rows[0]
    parts = race_id.split("_")
    meeting_code = int(parts[-2]) if len(parts) >= 3 and parts[-2].isdigit() else None
    race_number = int(parts[-1]) if parts and parts[-1].isdigit() else None
    runner_fields = ["number", *(name for name, _source, _scale in RUNNER_FEATURES)]
    runners: list[list[int | float | None]] = []
    for row in race_rows:
        runners.append(
            [
                int(row["chulNo"]),
                *[
                    _render_state_number(row.get(source_name), scale)
                    for _name, source_name, scale in RUNNER_FEATURES
                ],
            ]
        )
    return {
        "race_id": race_id,
        "date": _race_date(race_id),
        "meet": meeting_code,
        "race_no": race_number,
        "distance": _json_number(first.get("dist")),
        "field_size": len(race_rows),
        "class": _json_number(first.get("class_code")),
        "weather": _json_number(first.get("weather_code")),
        "track_pct": _json_number(first.get("track_pct")),
        "wet": _json_number(first.get("wet_track")),
        "handicap": _json_number(first.get("is_handicap")),
        "runner_fields": runner_fields,
        "runner_values": runners,
    }


def _candidate_priority(row: dict[str, Any]) -> tuple[Any, ...]:
    combo = _combo(row.get("combo")) or (999, 999, 999)
    model_rank = _json_number(row.get("model_rank"))
    return (
        float(_json_number(row.get("is_default")) or 0.0),
        float(_json_number(row.get("support_count")) or 0.0),
        float(_json_number(row.get("probability")) or 0.0),
        float(_json_number(row.get("ensemble_score")) or 0.0),
        float(_json_number(row.get("source_score")) or 0.0),
        float(_json_number(row.get("member_mean")) or 0.0),
        -float(model_rank if model_rank is not None else 999.0),
        tuple(-item for item in combo),
    )


def _retained_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: dict[tuple[int, int, int], dict[str, Any]] = {}
    for row in rows:
        combo = _combo(row.get("combo"))
        if combo is None:
            raise ValueError(
                "candidate combo must contain three distinct horse numbers"
            )
        current = unique.get(combo)
        if current is None or _candidate_priority(row) > _candidate_priority(current):
            unique[combo] = row
    return sorted(unique.values(), key=_candidate_priority, reverse=True)[
        :MAX_COMBO_OPTIONS
    ]


def _candidate_description(row: dict[str, Any]) -> str:
    combo = _combo(row.get("combo"))
    if combo is None:
        raise ValueError("candidate combo is invalid")
    features = (
        _format_integer(row.get("is_default")),
        _format_integer(row.get("default_overlap")),
        _format_milli(row.get("source_score")),
        _format_milli(row.get("ensemble_score")),
        _format_integer(row.get("model_rank")),
        _format_milli(row.get("member_mean")),
        _format_milli(row.get("probability")),
    )
    horses = ",".join(str(item) for item in combo)
    return f"{horses}|{','.join(features)}"


def _option_order_key(seed: str, race_id: str, option_id: str) -> str:
    return _sha256_bytes(f"{seed}|{race_id}|{option_id}".encode())


def _render_example(
    *,
    race_id: str,
    split_name: str,
    source_window: str,
    race_rows: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    answer: tuple[int, int, int],
    seed: str,
) -> tuple[dict[str, Any], bool]:
    retained = _retained_candidates(candidates)
    option_rows: list[tuple[str, str, tuple[int, int, int] | None]] = []
    for candidate in retained:
        combo = _combo(candidate["combo"])
        if combo is None:
            raise ValueError(f"invalid candidate in {race_id}")
        option_rows.append(
            (
                ",".join(str(item) for item in combo),
                _candidate_description(candidate),
                combo,
            )
        )
    option_rows.append(
        (
            NONE_OPTION,
            NONE_OPTION,
            None,
        )
    )
    option_rows.sort(key=lambda row: _option_order_key(seed, race_id, row[0]))

    criteria: dict[str, str] = {}
    expected_label = ""
    candidate_hit = False
    for index, (_option_id, description, combo) in enumerate(option_rows):
        label = OPTION_LABELS[index]
        criteria[label] = description
        if combo == answer:
            expected_label = label
            candidate_hit = True
        elif combo is None and not expected_label:
            expected_label = label
    if not candidate_hit:
        expected_label = next(
            label
            for label, description in criteria.items()
            if description == NONE_OPTION
        )

    example = {
        "state": _race_state(race_id, race_rows),
        "questions": {
            QUESTION_ID: {
                "type": "choice",
                "instructions": (
                    "Choose the correct unordered top three. Format: "
                    "horses|default,overlap,source,ensemble,rank,member,probability. "
                    "Source, ensemble, member, and probability use x1000. "
                    "Choose NONE only if no listed combination is correct."
                ),
                "criteria": criteria,
            }
        },
        "expected": {QUESTION_ID: expected_label},
        "tags": [f"split:{split_name}", f"source_window:{source_window}"],
        "language": "en",
    }
    return example, candidate_hit


def _rendered_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            keys.add(str(key))
            keys.update(_rendered_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.update(_rendered_keys(item))
    return keys


def _validate_source_candidate_labels(
    race_id: str,
    candidates: list[dict[str, Any]],
    answer: tuple[int, int, int],
) -> list[str]:
    violations: list[str] = []
    answer_set = set(answer)
    for index, candidate in enumerate(candidates):
        combo = _combo(candidate.get("combo"))
        if combo is None:
            violations.append(f"{race_id}:{index}:invalid_combo")
            continue
        expected_exact = float(combo == answer)
        expected_match = len(set(combo) & answer_set) / 3.0
        if "exact_label" in candidate and not math.isclose(
            float(candidate["exact_label"]), expected_exact, abs_tol=1e-9
        ):
            violations.append(f"{race_id}:{index}:exact_label")
        if "match_label" in candidate and not math.isclose(
            float(candidate["match_label"]), expected_match, abs_tol=1e-9
        ):
            violations.append(f"{race_id}:{index}:match_label")
    return violations


def build_laya_dataset(
    *,
    candidate_cache: dict[str, Any],
    row_cache: dict[str, Any],
    config: dict[str, Any],
    seed: str = DEFAULT_SEED,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    """Build deterministic split rows and an audit manifest."""

    if candidate_cache.get("format_version") != SOURCE_FORMAT_VERSION:
        raise ValueError("candidate cache format version is not supported")
    if candidate_cache.get("selection_contract") != SOURCE_SELECTION_CONTRACT:
        raise ValueError("candidate cache selection contract is not supported")
    if candidate_cache.get("timing_contract") != SOURCE_TIMING_CONTRACT:
        raise ValueError("candidate cache timing contract is not supported")
    if candidate_cache.get("is_partial_window_cache") is not False:
        raise ValueError("candidate cache must contain every canonical window")

    raw_candidate_windows = candidate_cache.get("candidate_rows_by_window")
    raw_rows = row_cache.get("rows")
    raw_answers = row_cache.get("answers")
    if not isinstance(raw_candidate_windows, dict):
        raise ValueError("candidate cache is missing candidate_rows_by_window")
    if not isinstance(raw_rows, list) or not all(
        isinstance(row, dict) for row in raw_rows
    ):
        raise ValueError("row cache rows are invalid")
    if not isinstance(raw_answers, dict):
        raise ValueError("row cache answers are invalid")

    rows_by_race = _rows_by_race(raw_rows)
    answers = {
        str(race_id): answer
        for race_id, value in raw_answers.items()
        if (answer := _answer(value)) is not None
    }
    windows = _rolling_windows(config)
    datasets: dict[str, list[dict[str, Any]]] = {}
    split_summaries: dict[str, dict[str, Any]] = {}
    all_race_ids: set[str] = set()
    overlap_race_ids: set[str] = set()
    timing_violations: list[str] = []
    source_label_violations: list[str] = []
    missing_row_race_ids: list[str] = []
    missing_answer_race_ids: list[str] = []
    rendered_leakage_violations: list[str] = []

    for split_name, source_window in SPLIT_WINDOWS.items():
        raw_window = raw_candidate_windows.get(source_window)
        window = windows.get(source_window)
        if not isinstance(raw_window, dict):
            raise ValueError(f"candidate cache is missing {source_window}")
        if not window or not all(window.values()):
            raise ValueError(f"config is missing complete window {source_window}")

        race_ids = sorted(str(race_id) for race_id in raw_window)
        overlap_race_ids.update(all_race_ids & set(race_ids))
        all_race_ids.update(race_ids)
        examples: list[dict[str, Any]] = []
        raw_candidate_counts: list[int] = []
        option_counts: list[int] = []
        expected_labels: list[str] = []
        state_char_counts: list[int] = []
        criterion_char_counts: list[int] = []
        max_rendered_decision_chars = 0
        original_hits = 0
        retained_hits = 0
        dropped_candidate_count = 0

        for race_id in race_ids:
            date = _race_date(race_id)
            if not (
                window["train_end"] < date
                and window["eval_start"] <= date <= window["eval_end"]
            ):
                timing_violations.append(race_id)
            race_rows = rows_by_race.get(race_id)
            if not race_rows:
                missing_row_race_ids.append(race_id)
                continue
            answer = answers.get(race_id)
            if answer is None:
                missing_answer_race_ids.append(race_id)
                continue
            candidates = raw_window[race_id]
            if not isinstance(candidates, list) or not all(
                isinstance(row, dict) for row in candidates
            ):
                raise ValueError(f"candidate rows are invalid for {race_id}")
            source_label_violations.extend(
                _validate_source_candidate_labels(race_id, candidates, answer)
            )
            original_combos = {
                combo
                for row in candidates
                if (combo := _combo(row.get("combo"))) is not None
            }
            original_hits += int(answer in original_combos)
            retained = _retained_candidates(candidates)
            retained_combos = {
                combo
                for row in retained
                if (combo := _combo(row.get("combo"))) is not None
            }
            retained_hits += int(answer in retained_combos)
            dropped_candidate_count += len(original_combos) - len(retained_combos)
            example, candidate_hit = _render_example(
                race_id=race_id,
                split_name=split_name,
                source_window=source_window,
                race_rows=race_rows,
                candidates=candidates,
                answer=answer,
                seed=seed,
            )
            if candidate_hit != (answer in retained_combos):
                raise AssertionError(f"candidate hit mismatch for {race_id}")
            rendered_keys = _rendered_keys(
                {"state": example["state"], "questions": example["questions"]}
            )
            if rendered_keys & FORBIDDEN_RENDERED_KEYS:
                rendered_leakage_violations.append(race_id)
            expected = example["expected"][QUESTION_ID]
            criteria = example["questions"][QUESTION_ID]["criteria"]
            if expected not in criteria:
                raise AssertionError(f"expected label is missing for {race_id}")
            raw_candidate_counts.append(len(original_combos))
            option_counts.append(len(criteria))
            expected_labels.append(expected)
            state_chars = len(
                json.dumps(
                    example["state"],
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                )
            )
            instruction_chars = len(
                str(example["questions"][QUESTION_ID]["instructions"])
            )
            state_char_counts.append(state_chars)
            for description in criteria.values():
                criterion_chars = len(description)
                criterion_char_counts.append(criterion_chars)
                max_rendered_decision_chars = max(
                    max_rendered_decision_chars,
                    state_chars + instruction_chars + criterion_chars,
                )
            examples.append(example)

        datasets[split_name] = examples
        race_count = len(examples)
        split_summaries[split_name] = {
            "source_window": source_window,
            "train_end": window["train_end"],
            "eval_start": window["eval_start"],
            "eval_end": window["eval_end"],
            "race_count": race_count,
            "date_min": min(
                (_race_date(race_id) for race_id in race_ids), default=None
            ),
            "date_max": max(
                (_race_date(race_id) for race_id in race_ids), default=None
            ),
            "raw_candidate_count_distribution": dict(
                sorted(Counter(raw_candidate_counts).items())
            ),
            "laya_option_count_distribution": dict(
                sorted(Counter(option_counts).items())
            ),
            "expected_label_distribution": dict(
                sorted(Counter(expected_labels).items())
            ),
            "rendering_size_chars": {
                "state_mean": round(sum(state_char_counts) / race_count, 2)
                if race_count
                else None,
                "state_max": max(state_char_counts, default=None),
                "criterion_mean": round(
                    sum(criterion_char_counts) / len(criterion_char_counts),
                    2,
                )
                if criterion_char_counts
                else None,
                "criterion_max": max(criterion_char_counts, default=None),
                "state_plus_instruction_plus_criterion_max": (
                    max_rendered_decision_chars
                ),
            },
            "dropped_candidate_count": dropped_candidate_count,
            "original_candidate_oracle_exact_rate": round(original_hits / race_count, 6)
            if race_count
            else None,
            "retained_candidate_oracle_exact_rate": round(retained_hits / race_count, 6)
            if race_count
            else None,
            "none_target_count": race_count - retained_hits,
        }

    all_examples = [example for rows in datasets.values() for example in rows]
    all_option_counts = [
        len(example["questions"][QUESTION_ID]["criteria"]) for example in all_examples
    ]
    passed = (
        bool(all_examples)
        and not overlap_race_ids
        and not timing_violations
        and not source_label_violations
        and not missing_row_race_ids
        and not missing_answer_race_ids
        and not rendered_leakage_violations
        and max(all_option_counts, default=0) <= 20
        and all(len(rows) > 0 for rows in datasets.values())
    )
    manifest = {
        "format_version": FORMAT_VERSION,
        "status": "passed" if passed else "failed",
        "diagnostic_only": True,
        "counts_as_70_percent_evidence": False,
        "rendering_version": RENDERING_VERSION,
        "seed": seed,
        "question_id": QUESTION_ID,
        "split_mapping": SPLIT_WINDOWS,
        "source_format_version": SOURCE_FORMAT_VERSION,
        "source_selection_contract": SOURCE_SELECTION_CONTRACT,
        "source_timing_contract": SOURCE_TIMING_CONTRACT,
        "timing_contract": (
            "complete_date_disjoint_fold_a_train_fold_b_validation_fold_c_test"
        ),
        "label_visibility_rule": "completed_prior_race_dates_only",
        "option_contract": {
            "max_combo_options": MAX_COMBO_OPTIONS,
            "always_include_none_option": True,
            "max_total_options": 20,
            "opaque_labels": True,
            "deterministic_per_race_permutation": True,
        },
        "coverage": {
            "race_count": len(all_examples),
            "split_overlap_race_ids": sorted(overlap_race_ids),
            "missing_row_race_ids": sorted(set(missing_row_race_ids)),
            "missing_answer_race_ids": sorted(set(missing_answer_race_ids)),
        },
        "timing_audit": {
            "passed": not timing_violations,
            "violation_race_ids": sorted(set(timing_violations)),
        },
        "leakage_audit": {
            "passed": not source_label_violations and not rendered_leakage_violations,
            "source_label_consistency_violations": source_label_violations,
            "rendered_input_forbidden_key_race_ids": sorted(
                set(rendered_leakage_violations)
            ),
            "candidate_label_fields_rendered": False,
            "row_target_rendered": False,
        },
        "split_summaries": split_summaries,
        "dataset_digest": _sha256_json(datasets),
        "selected_row_source_digest": _sha256_json(
            {
                race_id: rows_by_race[race_id]
                for race_id in sorted(all_race_ids)
                if race_id in rows_by_race
            }
        ),
        "recommended_next_action": (
            "validate_with_official_laya_evals"
            if passed
            else "repair_laya_dataset_contract"
        ),
    }
    return datasets, manifest


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                + "\n"
            )


def export_laya_dataset(
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
    config = _read_json(config_path)
    row_cache = _load_or_build_row_cache(
        config_path=config_path,
        cache_dir=cache_dir,
        refresh_cache=False,
    )
    datasets, manifest = build_laya_dataset(
        candidate_cache=candidate_cache,
        row_cache=row_cache,
        config=config,
        seed=seed,
    )
    files: dict[str, dict[str, Any]] = {}
    for split_name, rows in datasets.items():
        path = output_dir / f"{split_name}.jsonl"
        _write_jsonl(path, rows)
        files[split_name] = {
            "path": str(path),
            "sha256": _sha256_file(path),
            "row_count": len(rows),
        }
    manifest.update(
        {
            "candidate_cache_path": str(candidate_cache_path),
            "candidate_cache_sha256": _sha256_file(candidate_cache_path),
            "config_path": str(config_path),
            "config_sha256": _sha256_file(config_path),
            "files": files,
        }
    )
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-cache", type=Path, default=DEFAULT_CANDIDATE_CACHE)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--seed", default=DEFAULT_SEED)
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()
    manifest = export_laya_dataset(
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
                "race_count": manifest["coverage"]["race_count"],
                "split_summaries": manifest["split_summaries"],
                "output_dir": str(args.output_dir),
                "counts_as_70_percent_evidence": False,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return int(args.require_pass and manifest["status"] != "passed")


if __name__ == "__main__":
    raise SystemExit(main())
