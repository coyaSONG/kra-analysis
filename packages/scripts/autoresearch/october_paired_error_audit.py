"""Audit stored October development predictions without inference or selection."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from collections import Counter
from pathlib import Path
from typing import Any

FILES = {
    "baseline": ".cache/autoresearch/clean_release_current_best_cross_surface_union_prior_date_selector_rerun_repro_diagnostic.json",
    "predictions": ".cache/autoresearch/structured_candidate_ranker/october_predictions.jsonl",
    "ranker_report": ".cache/autoresearch/structured_candidate_ranker/report.json",
    "validation": ".cache/autoresearch/laya_oof_training_dataset/validation.jsonl",
    "manifest": ".cache/autoresearch/laya_oof_training_dataset/manifest.json",
    "candidate_cache": ".cache/autoresearch/laya_oof_training_dataset/candidate_rows.joblib",
}


def _combo(value: Any) -> tuple[int, ...]:
    if (
        not isinstance(value, list)
        or len(value) != 3
        or any(type(n) is not int or not 1 <= n <= 20 for n in value)
        or len(set(value)) != 3
    ):
        raise ValueError("invalid_three_horse_selection")
    return tuple(sorted(value))


def _description(value: str) -> tuple[int, ...]:
    if value == "NONE":
        return ()
    if not isinstance(value, str) or "|" not in value:
        raise ValueError("invalid_saved_prediction_description")
    return _combo([int(n) for n in value.split("|", 1)[0].split(",")])


def _index(rows: list[dict[str, Any]], *, state: bool = False) -> dict[str, Any]:
    result = {}
    for row in rows:
        value = row["state"] if state else row
        key = value["race_id"]
        if key in result:
            raise ValueError("duplicate_race")
        result[key] = value
    return result


def build_ledger(
    baseline: dict[str, list[int]],
    predictions: list[dict[str, Any]],
    answers: dict[str, list[int]],
    validation: list[dict[str, Any]],
) -> dict[str, Any]:
    ranker, states = _index(predictions), _index(validation, state=True)
    keys = set(baseline)
    if not keys or keys != set(ranker) or keys != set(answers) or keys != set(states):
        raise ValueError("paired_universe_mismatch")
    counts = Counter(
        dict.fromkeys(("both_hit", "baseline_only", "ranker_only", "both_miss"), 0)
    )
    ledger = []
    values: dict[str, list[Any]] = {}
    constant_races: Counter[str] = Counter()
    dates: Counter[str] = Counter()
    for race_id in sorted(keys):
        state = states[race_id]
        if not race_id.startswith("202510") or state["date"] != race_id.split("_")[0]:
            raise ValueError("only_october_development_is_allowed")
        fields, runners = state["runner_fields"], state["runner_values"]
        if (
            not runners
            or len(set(fields)) != len(fields)
            or "number" not in fields
            or any(len(row) != len(fields) for row in runners)
            or len(runners) != state["field_size"]
        ):
            raise ValueError("invalid_saved_roster_shape")
        numbers = [row[fields.index("number")] for row in runners]
        if len(set(numbers)) != len(numbers) or any(
            type(n) is not int for n in numbers
        ):
            raise ValueError("invalid_saved_roster_identity")
        actual, left = _combo(answers[race_id]), _combo(baseline[race_id])
        right = _description(ranker[race_id]["predicted_description"])
        expected = _description(ranker[race_id]["expected_description"])
        if expected and expected != actual:
            raise ValueError("saved_answer_disagreement")
        if not (set(actual) | set(left) | set(right)).issubset(numbers):
            raise ValueError("selection_outside_saved_roster")
        left_hit, right_hit = left == actual, right == actual
        if (
            type(ranker[race_id]["top3_correct"]) is not bool
            or ranker[race_id]["top3_correct"] != right_hit
        ):
            raise ValueError("saved_hit_disagreement")
        category = (
            "both_hit"
            if left_hit and right_hit
            else "baseline_only"
            if left_hit
            else "ranker_only"
            if right_hit
            else "both_miss"
        )
        counts[category] += 1
        dates[state["date"]] += 1
        missing = {}
        for i, name in enumerate(fields):
            column = [row[i] for row in runners]
            values.setdefault(name, []).extend(column)
            missing[name] = sum(value is None for value in column)
            observed = {value for value in column if value is not None}
            constant_races[name] += int(len(observed) == 1)
        ledger.append(
            {
                "race_id": race_id,
                "category": category,
                "answer": actual,
                "baseline": left,
                "ranker": right,
                "ranker_abstained": not right,
                "baseline_omitted": sorted(set(actual) - set(left)),
                "baseline_extra": sorted(set(left) - set(actual)),
                "ranker_omitted": sorted(set(actual) - set(right)),
                "ranker_extra": sorted(set(right) - set(actual)),
                "missing_by_field": missing,
                "historical_source_availability": "unproven",
            }
        )
    return {
        "format_version": "october-stored-paired-error-audit-v1",
        "diagnostic_only": True,
        "counts_as_70_percent_evidence": False,
        "new_inference_or_training": False,
        "race_count": len(keys),
        "date_count": len(dates),
        "races_by_date": dict(sorted(dates.items())),
        "paired_counts": dict(counts),
        "baseline_exact": counts["both_hit"] + counts["baseline_only"],
        "ranker_exact": counts["both_hit"] + counts["ranker_only"],
        "ranker_abstentions": sum(row["ranker_abstained"] for row in ledger),
        "feature_profile": {
            name: {
                "runner_rows": len(column),
                "null_rows": sum(value is None for value in column),
                "observed_distinct_count": len({v for v in column if v is not None}),
                "constant_nonmissing_races": constant_races[name],
            }
            for name, column in values.items()
        },
        "ledger": ledger,
    }


def audit_stored_files(root: Path) -> dict[str, Any]:
    # This cache is an existing trusted local research artifact, never a download.
    import joblib

    raw = {name: (root / path).read_bytes() for name, path in FILES.items()}
    hashes = {
        name: hashlib.sha256(content).hexdigest() for name, content in raw.items()
    }
    manifest, report = json.loads(raw["manifest"]), json.loads(raw["ranker_report"])
    if hashes["candidate_cache"] != manifest["candidate_cache_sha256"]:
        raise ValueError("candidate_cache_pin_mismatch")
    if (
        hashes["validation"] != manifest["dataset_sha256"]["validation"]
        or hashes["validation"] != report["validation_sha256"]
    ):
        raise ValueError("validation_pin_mismatch")
    cache = joblib.load(io.BytesIO(raw["candidate_cache"]))
    if cache["validation_window"] != "fold_a":
        raise ValueError("not_october_cache")
    baseline = json.loads(raw["baseline"])
    result = build_ledger(
        baseline["predictions_by_window"]["fold_a"],
        [json.loads(line) for line in raw["predictions"].splitlines()],
        cache["answers_by_split"]["validation"],
        [json.loads(line) for line in raw["validation"].splitlines()],
    )
    if (
        result["race_count"] != 116
        or result["baseline_exact"] != report["strict_baseline"]["correct_count"]
        or result["ranker_exact"]
        != report["validation_by_family"]["structured"]["october_validation"][
            "top3_correct_count"
        ]
    ):
        raise ValueError("stored_summary_disagreement")
    result["input_pins"] = {
        name: {"path": FILES[name], "sha256": digest} for name, digest in hashes.items()
    }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = audit_stored_files(args.research_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write("\n")
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in ("ledger", "input_pins")},
            sort_keys=True,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
