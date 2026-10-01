"""Audit whether a row cache can support race-level Laya research."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from hashlib import sha256
from numbers import Real
from pathlib import Path
from typing import Any

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))

from autoresearch.clean_sparse_multichoice_policy_selector_probe import (  # noqa: E402
    DEFAULT_CACHE_DIR,
    DEFAULT_CONFIG,
)
from autoresearch.search_clean_model import (  # noqa: E402
    _load_or_build_row_cache,
)

FORMAT_VERSION = "single-combo-laya-data-capacity-audit-v1"
DEFAULT_OUTPUT = DEFAULT_CACHE_DIR / "single_combo_laya_data_capacity_audit.json"
DEFAULT_PROJECTED_ROW_COUNTS = (100_000, 200_000, 300_000)
DEFAULT_TARGET_UNIQUE_RACES = 20_000
IDENTIFIER_FIELDS = frozenset({"race_id", "race_date", "chulNo", "target"})


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, Real):
        try:
            return math.isnan(float(value))
        except (TypeError, ValueError):
            return False
    return False


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _answer_tuple(value: Any) -> tuple[int, int, int] | None:
    if not isinstance(value, list | tuple) or len(value) != 3:
        return None
    converted = tuple(_safe_int(item) for item in value)
    if any(item is None for item in converted):
        return None
    answer = tuple(int(item) for item in converted if item is not None)
    if len(set(answer)) != 3:
        return None
    return answer


def _race_date(row: dict[str, Any], race_id: str) -> str:
    explicit = str(row.get("race_date") or "").strip()
    if len(explicit) == 8 and explicit.isdigit():
        return explicit
    prefix = race_id[:8]
    return prefix if len(prefix) == 8 and prefix.isdigit() else ""


def _project_capacity(
    *,
    projected_row_counts: tuple[int, ...],
    mean_rows_per_race: float | None,
    target_unique_races: int,
) -> list[dict[str, Any]]:
    projections: list[dict[str, Any]] = []
    for raw_count in sorted(set(projected_row_counts)):
        if raw_count <= 0:
            continue
        projected_races = (
            int(raw_count / mean_rows_per_race)
            if mean_rows_per_race and mean_rows_per_race > 0
            else None
        )
        projections.append(
            {
                "raw_row_count": raw_count,
                "projected_unique_race_count": projected_races,
                "projected_target_coverage_rate": round(
                    projected_races / target_unique_races,
                    6,
                )
                if projected_races is not None and target_unique_races > 0
                else None,
                "meets_target_unique_races": (
                    projected_races >= target_unique_races
                    if projected_races is not None
                    else None
                ),
            }
        )
    return projections


def audit_row_cache(
    row_cache: dict[str, Any],
    *,
    projected_row_counts: tuple[int, ...] = DEFAULT_PROJECTED_ROW_COUNTS,
    target_unique_races: int = DEFAULT_TARGET_UNIQUE_RACES,
) -> dict[str, Any]:
    """Return a deterministic quality and capacity profile for one row cache."""

    raw_rows = row_cache.get("rows")
    raw_answers = row_cache.get("answers")
    if not isinstance(raw_rows, list):
        raise ValueError("row cache rows must be a list")
    if not isinstance(raw_answers, dict):
        raise ValueError("row cache answers must be a dictionary")
    if target_unique_races <= 0:
        raise ValueError("target_unique_races must be positive")

    rows = [row for row in raw_rows if isinstance(row, dict)]
    invalid_row_count = len(raw_rows) - len(rows)
    race_entries: dict[str, set[int]] = defaultdict(set)
    race_dates: dict[str, str] = {}
    entry_key_counts: Counter[tuple[str, int]] = Counter()
    missing_race_id_count = 0
    missing_chul_no_count = 0
    inconsistent_race_dates: set[str] = set()

    for row in rows:
        race_id = str(row.get("race_id") or "").strip()
        chul_no = _safe_int(row.get("chulNo"))
        if not race_id:
            missing_race_id_count += 1
            continue
        if chul_no is None:
            missing_chul_no_count += 1
            continue
        race_entries[race_id].add(chul_no)
        entry_key_counts[(race_id, chul_no)] += 1
        date = _race_date(row, race_id)
        previous = race_dates.setdefault(race_id, date)
        if date and previous and date != previous:
            inconsistent_race_dates.add(race_id)

    race_ids = sorted(race_entries)
    row_count = len(rows)
    race_count = len(race_ids)
    field_sizes = [len(race_entries[race_id]) for race_id in race_ids]
    mean_rows_per_race = row_count / race_count if race_count else None
    duplicate_keys = sorted(
        (race_id, chul_no, count)
        for (race_id, chul_no), count in entry_key_counts.items()
        if count > 1
    )

    feature_names = sorted(
        {str(key) for row in rows for key in row if str(key) not in IDENTIFIER_FIELDS}
    )
    missing_by_feature = {
        feature: sum(_is_missing(row.get(feature)) for row in rows)
        for feature in feature_names
    }
    feature_cell_count = row_count * len(feature_names)
    missing_feature_cell_count = sum(missing_by_feature.values())
    missing_rate_by_feature = {
        feature: round(count / row_count, 6) if row_count else None
        for feature, count in missing_by_feature.items()
    }
    fully_missing_features = sorted(
        feature
        for feature, count in missing_by_feature.items()
        if row_count > 0 and count == row_count
    )
    high_missing_features = [
        {"feature": feature, "missing_rate": rate}
        for feature, rate in sorted(
            missing_rate_by_feature.items(),
            key=lambda item: (
                -(item[1] if item[1] is not None else -1.0),
                item[0],
            ),
        )
        if rate is not None and rate >= 0.20
    ]

    answer_ids = {str(race_id) for race_id in raw_answers}
    missing_answer_race_ids: list[str] = []
    invalid_answer_race_ids: list[str] = []
    answer_not_in_field_race_ids: list[str] = []
    complete_answer_race_ids: list[str] = []
    for race_id in race_ids:
        if race_id not in raw_answers:
            missing_answer_race_ids.append(race_id)
            continue
        answer = _answer_tuple(raw_answers[race_id])
        if answer is None:
            invalid_answer_race_ids.append(race_id)
            continue
        if not set(answer).issubset(race_entries[race_id]):
            answer_not_in_field_race_ids.append(race_id)
            continue
        complete_answer_race_ids.append(race_id)

    orphan_answer_race_ids = sorted(answer_ids - set(race_ids))
    usable_race_count = len(complete_answer_race_ids)
    quality_failures = {
        "invalid_row_objects": invalid_row_count,
        "missing_race_id_rows": missing_race_id_count,
        "missing_chul_no_rows": missing_chul_no_count,
        "duplicate_entry_keys": len(duplicate_keys),
        "inconsistent_race_dates": len(inconsistent_race_dates),
        "missing_answers": len(missing_answer_race_ids),
        "invalid_answers": len(invalid_answer_race_ids),
        "answers_outside_active_field": len(answer_not_in_field_race_ids),
    }
    passed = (
        row_count > 0
        and race_count > 0
        and bool(feature_names)
        and all(count == 0 for count in quality_failures.values())
        and usable_race_count == race_count
    )
    known_dates = sorted(date for date in race_dates.values() if date)

    return {
        "format_version": FORMAT_VERSION,
        "status": "passed" if passed else "failed",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "diagnostic_only": True,
        "counts_as_70_percent_evidence": False,
        "dataset": row_cache.get("dataset"),
        "grain": {
            "intended_row_grain": "one_active_runner_per_race",
            "independent_supervised_grain": "one_race_choice",
            "row_count": row_count,
            "unique_race_count": race_count,
            "usable_unique_race_count": usable_race_count,
            "mean_rows_per_race": round(mean_rows_per_race, 6)
            if mean_rows_per_race is not None
            else None,
            "min_field_size": min(field_sizes) if field_sizes else None,
            "max_field_size": max(field_sizes) if field_sizes else None,
        },
        "date_coverage": {
            "min_race_date": min(known_dates) if known_dates else None,
            "max_race_date": max(known_dates) if known_dates else None,
            "race_with_known_date_count": len(known_dates),
            "race_with_unknown_date_count": race_count - len(known_dates),
            "inconsistent_race_date_count": len(inconsistent_race_dates),
            "inconsistent_race_date_ids_preview": sorted(inconsistent_race_dates)[:10],
        },
        "label_quality": {
            "answer_key_count": len(raw_answers),
            "complete_valid_top3_race_count": usable_race_count,
            "complete_valid_top3_rate": round(usable_race_count / race_count, 6)
            if race_count
            else None,
            "missing_answer_count": len(missing_answer_race_ids),
            "invalid_answer_count": len(invalid_answer_race_ids),
            "answer_not_in_active_field_count": len(answer_not_in_field_race_ids),
            "orphan_answer_count": len(orphan_answer_race_ids),
            "missing_answer_ids_preview": missing_answer_race_ids[:10],
            "invalid_answer_ids_preview": invalid_answer_race_ids[:10],
            "answer_not_in_active_field_ids_preview": answer_not_in_field_race_ids[:10],
            "orphan_answer_ids_preview": orphan_answer_race_ids[:10],
        },
        "duplicate_quality": {
            "entry_key": ["race_id", "chulNo"],
            "duplicate_entry_key_count": len(duplicate_keys),
            "duplicate_row_excess_count": sum(
                count - 1 for _, _, count in duplicate_keys
            ),
            "duplicate_entry_keys_preview": [
                {"race_id": race_id, "chulNo": chul_no, "count": count}
                for race_id, chul_no, count in duplicate_keys[:10]
            ],
        },
        "missingness": {
            "feature_count": len(feature_names),
            "feature_cell_count": feature_cell_count,
            "missing_feature_cell_count": missing_feature_cell_count,
            "missing_feature_cell_rate": round(
                missing_feature_cell_count / feature_cell_count,
                6,
            )
            if feature_cell_count
            else None,
            "fully_missing_feature_count": len(fully_missing_features),
            "fully_missing_features": fully_missing_features,
            "features_at_or_above_20pct_missing": high_missing_features,
        },
        "quality_failures": quality_failures,
        "capacity_target": {
            "target_unique_races": target_unique_races,
            "current_gap_races": max(target_unique_races - usable_race_count, 0),
            "current_target_coverage_rate": round(
                usable_race_count / target_unique_races,
                6,
            ),
            "note": (
                "The target is a research-capacity planning threshold, not a "
                "guarantee of model accuracy or a 70 percent result."
            ),
        },
        "projections": _project_capacity(
            projected_row_counts=projected_row_counts,
            mean_rows_per_race=mean_rows_per_race,
            target_unique_races=target_unique_races,
        ),
        "recommended_next_action": (
            "build_strict_prior_date_laya_candidate_surface"
            if passed
            else "repair_row_cache_quality_failures_before_laya_export"
        ),
    }


def _load_explicit_row_cache(path: Path) -> dict[str, Any]:
    import joblib

    payload = joblib.load(path)
    if not isinstance(payload, dict):
        raise ValueError(f"row cache must contain a dictionary: {path}")
    return payload


def _sha256_path(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--row-cache", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--projected-row-count",
        action="append",
        type=int,
        dest="projected_row_counts",
    )
    parser.add_argument(
        "--target-unique-races",
        type=int,
        default=DEFAULT_TARGET_UNIQUE_RACES,
    )
    parser.add_argument("--require-pass", action="store_true")
    args = parser.parse_args()

    if args.row_cache:
        row_cache = _load_explicit_row_cache(args.row_cache)
        source = {
            "kind": "explicit_joblib_row_cache",
            "path": str(args.row_cache),
            "sha256": _sha256_path(args.row_cache),
        }
    else:
        row_cache = _load_or_build_row_cache(
            config_path=args.config,
            cache_dir=args.cache_dir,
            refresh_cache=False,
        )
        source = {
            "kind": "configured_row_cache",
            "config_path": str(args.config),
            "cache_dir": str(args.cache_dir),
        }

    payload = audit_row_cache(
        row_cache,
        projected_row_counts=tuple(
            args.projected_row_counts or DEFAULT_PROJECTED_ROW_COUNTS
        ),
        target_unique_races=args.target_unique_races,
    )
    payload["source"] = source
    payload["output_path"] = str(args.output)
    _write_json(args.output, payload)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "status": payload["status"],
                "row_count": payload["grain"]["row_count"],
                "unique_race_count": payload["grain"]["unique_race_count"],
                "usable_unique_race_count": payload["grain"][
                    "usable_unique_race_count"
                ],
                "missing_feature_cell_rate": payload["missingness"][
                    "missing_feature_cell_rate"
                ],
                "counts_as_70_percent_evidence": False,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    if args.require_pass and payload["status"] != "passed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
