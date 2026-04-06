from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from research_clean import SAFE_FEATURES

# Early-prediction search must stay non-market, but the previous proposer was
# too narrow to justify long plateau runs. Expand around the current frontier
# with only validated, non-leaking feature bundles that actually exist in the
# snapshot.
OPTIONAL_FEATURES = [
    "horse_win_rate",
    "jockey_win_rate",
    "trainer_win_rate",
    "jockey_recent_win_rate",
    "jockey_total_place_rate",
    "trainer_total_place_rate",
    "hr_starts_y",
    "hr_starts_t",
    "horse_low_sample",
    "horse_skill_rank",
    "jk_skill_rank",
    "tr_skill_rank",
    "wg_budam_rank",
    "gap_3rd_4th",
    "field_size_live",
]

FEATURE_BUNDLES = {
    "speed_shape": ["gap_3rd_4th", "wg_budam_rank", "field_size_live"],
    "skill_ranks": ["horse_skill_rank", "jk_skill_rank", "tr_skill_rank"],
    "career_depth": ["hr_starts_y", "hr_starts_t", "horse_low_sample"],
    "win_signals": [
        "horse_win_rate",
        "jockey_win_rate",
        "trainer_win_rate",
        "jockey_recent_win_rate",
    ],
    "legacy_totals": ["jockey_total_place_rate", "trainer_total_place_rate"],
}


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
        params["max_depth"] = rng.choice([4, 5, 6, 7, 8, None])
        notes.append(f"max_depth={params['max_depth']}")
    if rng.random() < 0.6:
        params["learning_rate"] = rng.choice([0.03, 0.04, 0.05, 0.06, 0.08])
        notes.append(f"learning_rate={params['learning_rate']}")
    if rng.random() < 0.6:
        params["max_iter"] = rng.choice([400, 500, 600, 700, 800])
        notes.append(f"max_iter={params['max_iter']}")
    if rng.random() < 0.6:
        params["min_samples_leaf"] = rng.choice([15, 20, 25, 30, 35, 40])
        notes.append(f"min_samples_leaf={params['min_samples_leaf']}")
    if rng.random() < 0.4:
        params["l2_regularization"] = rng.choice([0.2, 0.3, 0.4, 0.5, 0.6, 0.8])
        notes.append(f"l2={params['l2_regularization']}")
    return notes


def _set_feature_state(
    selected: set[str], feature: str, enable: bool, notes: list[str]
) -> None:
    if enable and feature not in selected:
        selected.add(feature)
        notes.append(f"add:{feature}")
    elif not enable and feature in selected:
        selected.remove(feature)
        notes.append(f"drop:{feature}")


def _apply_bundle(
    selected: set[str], bundle_name: str, enable: bool, notes: list[str]
) -> None:
    changed = False
    for feature in FEATURE_BUNDLES[bundle_name]:
        before = feature in selected
        _set_feature_state(selected, feature, enable, notes)
        changed = changed or (before != (feature in selected))
    if changed:
        notes.append(f"bundle:{'add' if enable else 'drop'}:{bundle_name}")


def _mutate_features(
    features: list[str], rng: random.Random
) -> tuple[list[str], list[str]]:
    selected = set(features)
    mutation_notes: list[str] = []

    bundle_names = list(FEATURE_BUNDLES)
    for _ in range(rng.randint(2, 4)):
        if rng.random() < 0.6:
            bundle_name = rng.choice(bundle_names)
            bundle = FEATURE_BUNDLES[bundle_name]
            enable = not all(feature in selected for feature in bundle)
            if not enable and rng.random() < 0.7:
                enable = True
            _apply_bundle(selected, bundle_name, enable, mutation_notes)
            continue

        candidate = rng.choice(OPTIONAL_FEATURES)
        enable = candidate not in selected
        if not enable and rng.random() < 0.7:
            enable = True
        _set_feature_state(selected, candidate, enable, mutation_notes)

    if not any(feature in selected for feature in OPTIONAL_FEATURES):
        _apply_bundle(selected, "skill_ranks", True, mutation_notes)

    deduped_notes = list(dict.fromkeys(mutation_notes))

    ordered = [feature for feature in SAFE_FEATURES if feature in selected]
    return ordered, deduped_notes


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
        config["model"]["positive_class_weight"] = rng.choice(
            [0.9, 0.95, 1.0, 1.05, 1.1, 1.15]
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
