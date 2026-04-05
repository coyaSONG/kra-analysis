from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from research_clean import SAFE_FEATURES

# Current frontier is already a strong early baseline. Keep it stable and only
# explore a small set of additive, non-market features around it.
TUNABLE_FEATURES = [
    "horse_place_rate",
    "jockey_form",
    "burden_ratio",
    "is_route",
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
        params["max_depth"] = rng.choice([5, 6, 7])
        notes.append(f"max_depth={params['max_depth']}")
    if rng.random() < 0.6:
        params["learning_rate"] = rng.choice([0.04, 0.05, 0.06])
        notes.append(f"learning_rate={params['learning_rate']}")
    if rng.random() < 0.6:
        params["max_iter"] = rng.choice([500, 600, 700])
        notes.append(f"max_iter={params['max_iter']}")
    if rng.random() < 0.6:
        params["min_samples_leaf"] = rng.choice([25, 30, 35])
        notes.append(f"min_samples_leaf={params['min_samples_leaf']}")
    if rng.random() < 0.4:
        params["l2_regularization"] = rng.choice([0.2, 0.3, 0.4, 0.6])
        notes.append(f"l2={params['l2_regularization']}")
    return notes


def _mutate_features(
    features: list[str], rng: random.Random
) -> tuple[list[str], list[str]]:
    selected = set(features)
    mutation_notes: list[str] = []

    candidates = TUNABLE_FEATURES[:]
    rng.shuffle(candidates)
    for candidate in candidates[: rng.randint(1, 2)]:
        if candidate in selected:
            selected.remove(candidate)
            mutation_notes.append(f"drop:{candidate}")
        else:
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
    config["model"]["kind"] = "hgb"
    params = config["model"].setdefault("params", {})
    params.setdefault("max_depth", 6)
    params.setdefault("learning_rate", 0.05)
    params.setdefault("max_iter", 600)
    params.setdefault("min_samples_leaf", 30)
    params.setdefault("l2_regularization", 0.3)
    notes.extend(_mutate_hgb(params, rng))

    if rng.random() < 0.7:
        config["model"]["positive_class_weight"] = rng.choice([0.95, 1.0, 1.05, 1.1])
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
