from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from research_clean import SAFE_FEATURES

OPTIONAL_FEATURES = [
    "draw_no",
    "sex_code",
    "weather_code",
    "track_pct",
    "class_code",
    "budam_code",
    "rest_risk_code",
    "allowance_flag",
    "horse_win_rate",
    "horse_place_rate",
    "jockey_win_rate",
    "jockey_place_rate",
    "trainer_win_rate",
    "trainer_place_rate",
    "rest_days",
    "jockey_recent_win_rate",
    "year_place_rate",
    "total_place_rate",
    "jockey_total_place_rate",
    "trainer_total_place_rate",
    "field_size",
    "is_handicap",
    "dist",
    "is_sprint",
    "is_mile",
    "is_route",
    "is_large",
    "hr_starts_y",
    "hr_starts_t",
    "jk_place_rate_y",
    "tr_place_rate_y",
    "rating_rr",
    "wgBudam_rr",
    "winOdds_rr",
    "plcOdds_rr",
    "horse_place_rate_rr",
    "jockey_place_rate_rr",
    "trainer_place_rate_rr",
    "year_place_rate_rr",
    "total_place_rate_rr",
    "draw_rr",
]

CORE_FEATURES = [
    "rating",
    "wgBudam",
    "wgHr_value",
    "winOdds",
    "plcOdds",
    "age",
    "draw_no",
    "class_code",
    "track_pct",
    "budam_code",
    "rest_risk_code",
    "allowance_flag",
    "year_place_rate",
    "total_place_rate",
    "jk_place_rate_y",
    "tr_place_rate_y",
    "draw_rr",
    "rating_rank",
    "odds_rank",
    "age_prime",
]


def _find_runs_dir(start: Path) -> Path | None:
    current = start.resolve()
    for candidate in (current, *current.parents):
        runs_dir = candidate / ".ralph" / "runs"
        if runs_dir.exists():
            return runs_dir
    return None


def _has_accepted_run(start: Path) -> bool:
    runs_dir = _find_runs_dir(start)
    if runs_dir is None:
        return False
    for run_file in sorted(runs_dir.glob("run-*.json")):
        try:
            payload = json.loads(run_file.read_text())
        except Exception:
            continue
        if payload.get("status") == "accepted":
            return True
    return False


def _mutate_hgb(params: dict, rng: random.Random) -> list[str]:
    notes: list[str] = []
    if rng.random() < 0.6:
        params["max_depth"] = rng.choice([3, 4, 5, 6])
        notes.append(f"max_depth={params['max_depth']}")
    if rng.random() < 0.6:
        params["learning_rate"] = rng.choice([0.02, 0.03, 0.05, 0.07])
        notes.append(f"learning_rate={params['learning_rate']}")
    if rng.random() < 0.6:
        params["max_iter"] = rng.choice([400, 500, 600, 700, 900])
        notes.append(f"max_iter={params['max_iter']}")
    if rng.random() < 0.6:
        params["min_samples_leaf"] = rng.choice([10, 15, 20, 25, 30])
        notes.append(f"min_samples_leaf={params['min_samples_leaf']}")
    if rng.random() < 0.4:
        params["l2_regularization"] = rng.choice([0.0, 0.1, 0.3, 0.6, 1.0])
        notes.append(f"l2={params['l2_regularization']}")
    return notes


def _mutate_forest(params: dict, rng: random.Random) -> list[str]:
    params["n_estimators"] = rng.choice([300, 400, 500, 700])
    params["max_depth"] = rng.choice([8, 10, 12, 14, None])
    params["min_samples_leaf"] = rng.choice([1, 2, 3, 5, 8])
    return [
        f"n_estimators={params['n_estimators']}",
        f"max_depth={params['max_depth']}",
        f"min_samples_leaf={params['min_samples_leaf']}",
    ]


def _mutate_logreg(params: dict, rng: random.Random) -> list[str]:
    params["max_iter"] = rng.choice([1000, 1500, 2000, 3000])
    params["C"] = rng.choice([0.05, 0.1, 0.2, 0.5, 1.0, 2.0])
    return [f"max_iter={params['max_iter']}", f"C={params['C']}"]


def _mutate_features(
    features: list[str], rng: random.Random
) -> tuple[list[str], list[str]]:
    selected = set(features)
    mutation_notes: list[str] = []
    touched: set[str] = set()

    candidates = OPTIONAL_FEATURES[:]
    rng.shuffle(candidates)
    for candidate in candidates[: rng.randint(1, 4)]:
        if candidate in touched:
            continue
        touched.add(candidate)
        must_keep = candidate in CORE_FEATURES
        if (
            candidate in selected
            and not must_keep
            and len(selected) > len(CORE_FEATURES)
        ):
            selected.remove(candidate)
            mutation_notes.append(f"drop:{candidate}")
        elif candidate not in selected:
            selected.add(candidate)
            mutation_notes.append(f"add:{candidate}")

    ordered = [feature for feature in SAFE_FEATURES if feature in selected]
    return ordered, mutation_notes


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()

    config_path = Path(args.config)
    config = json.loads(config_path.read_text())
    rng = random.Random(args.seed)

    if not _has_accepted_run(Path.cwd()):
        baseline_note = "baseline-seed"
        if config.get("notes", {}).get("last_mutation") == baseline_note:
            baseline_note = "baseline-seed-reset"
        config["notes"]["last_mutation"] = baseline_note
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n")
        print(
            json.dumps(
                {"config": str(config_path), "mutation": [baseline_note]},
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    notes: list[str] = []
    if rng.random() < 0.25:
        config["model"]["kind"] = rng.choice(["hgb", "rf", "et"])
        notes.append(f"kind={config['model']['kind']}")

    kind = config["model"]["kind"]
    if kind == "hgb":
        params = config["model"].setdefault("params", {})
        params.setdefault("max_depth", 4)
        params.setdefault("learning_rate", 0.03)
        params.setdefault("max_iter", 300)
        params.setdefault("min_samples_leaf", 20)
        params.setdefault("l2_regularization", 0.0)
        notes.extend(_mutate_hgb(params, rng))
    elif kind in {"rf", "et"}:
        params = config["model"].setdefault("params", {})
        notes.extend(_mutate_forest(params, rng))
    else:
        params = config["model"].setdefault("params", {})
        notes.extend(_mutate_logreg(params, rng))

    if rng.random() < 0.7:
        config["model"]["positive_class_weight"] = rng.choice(
            [0.9, 1.0, 1.1, 1.25, 1.5]
        )
        notes.append(f"positive_weight={config['model']['positive_class_weight']}")

    features, feature_notes = _mutate_features(config["features"], rng)
    config["features"] = features
    notes.extend(feature_notes)
    config["notes"]["last_mutation"] = ", ".join(notes)

    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {"config": str(config_path), "mutation": notes},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
