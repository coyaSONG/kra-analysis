from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline

SNAPSHOT_DIR = Path(__file__).resolve().parent / "snapshots"

FEATURES = [
    "rating",
    "wgBudam",
    "winOdds",
    "plcOdds",
    "age",
    "seG1fAccTime",
    "sjG1fOrd",
    "seG3fAccTime",
    "sjG3fOrd",
    "seS1fAccTime",
    "sjS1fOrd",
    "horse_win_rate",
    "horse_place_rate",
    "jockey_win_rate",
    "jockey_place_rate",
    "trainer_win_rate",
    "trainer_place_rate",
    "rest_days",
    "jockey_recent_win_rate",
    "rating_rank",
    "odds_rank",
    "age_prime",
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
    "rating_rr",
    "wgBudam_rr",
    "winOdds_rr",
    "plcOdds_rr",
    "horse_place_rate_rr",
    "jockey_place_rate_rr",
    "trainer_place_rate_rr",
    "year_place_rate_rr",
    "total_place_rate_rr",
    "seG1fAccTime_rr",
    "sjG1fOrd_rr",
    "seG3fAccTime_rr",
    "sjG3fOrd_rr",
    "seS1fAccTime_rr",
    "sjS1fOrd_rr",
]

CONFIGS = {
    "hgb_a": {
        "max_depth": 3,
        "learning_rate": 0.03,
        "max_iter": 250,
        "min_samples_leaf": 20,
        "l2_regularization": 0.0,
    },
    "hgb_b": {
        "max_depth": 4,
        "learning_rate": 0.03,
        "max_iter": 350,
        "min_samples_leaf": 20,
        "l2_regularization": 0.0,
    },
    "hgb_c": {
        "max_depth": 4,
        "learning_rate": 0.05,
        "max_iter": 250,
        "min_samples_leaf": 30,
        "l2_regularization": 0.0,
    },
    "hgb_d": {
        "max_depth": 5,
        "learning_rate": 0.03,
        "max_iter": 350,
        "min_samples_leaf": 25,
        "l2_regularization": 0.1,
    },
    "hgb_e": {
        "max_depth": None,
        "learning_rate": 0.03,
        "max_iter": 300,
        "min_samples_leaf": 20,
        "l2_regularization": 0.0,
    },
}


def _safe_float(value, default=np.nan) -> float:
    try:
        if value in ("", None):
            return default
        return float(value)
    except Exception:
        return default


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _place_rate(ord1, ord2, ord3, total) -> float:
    total_count = _safe_float(total, 0.0)
    if not total_count or total_count <= 0:
        return 0.0
    return (
        _safe_float(ord1, 0.0) + _safe_float(ord2, 0.0) + _safe_float(ord3, 0.0)
    ) / total_count


def _year_place_rate(horse: dict) -> float:
    detail = horse.get("hrDetail") or {}
    starts_y = _safe_int(detail.get("rcCntY"))
    places_y = (
        _safe_int(detail.get("ord1CntY"))
        + _safe_int(detail.get("ord2CntY"))
        + _safe_int(detail.get("ord3CntY"))
    )
    if starts_y > 0:
        return places_y / (starts_y + 2)
    return _total_place_rate(horse)


def _total_place_rate(horse: dict) -> float:
    detail = horse.get("hrDetail") or {}
    starts_t = _safe_int(detail.get("rcCntT"))
    places_t = (
        _safe_int(detail.get("ord1CntT"))
        + _safe_int(detail.get("ord2CntT"))
        + _safe_int(detail.get("ord3CntT"))
    )
    return places_t / (starts_t + 15) if starts_t >= 0 else 0.0


def _percentile_rank(values: list[float], reverse: bool = False) -> list[float]:
    arr = np.asarray(values, dtype=float)
    fill = -999999.0 if reverse else 999999.0
    arr = np.where(np.isnan(arr), fill, arr)
    order = np.argsort(arr, kind="stable")
    if reverse:
        order = order[::-1]
    ranks = np.empty(len(arr), dtype=float)
    if len(arr) == 1:
        ranks[0] = 1.0
        return ranks.tolist()
    for idx, pos in enumerate(order):
        ranks[pos] = idx / (len(arr) - 1)
    return ranks.tolist()


def _build_rows(
    races: list[dict], answers: dict[str, list[int]]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[int]]:
    rows: list[dict] = []
    for race in races:
        info = race.get("race_info") or {}
        horses = race["horses"]
        actual = set(answers.get(race["race_id"], [])[:3])
        local_rows: list[dict] = []

        for horse in horses:
            features = horse.get("computed_features") or {}
            jockey = horse.get("jkDetail") or {}
            trainer = horse.get("trDetail") or {}
            dist = _safe_int(info.get("rcDist"), 0)
            local_rows.append(
                {
                    "rating": _safe_float(horse.get("rating")),
                    "wgBudam": _safe_float(horse.get("wgBudam")),
                    "winOdds": _safe_float(horse.get("winOdds")),
                    "plcOdds": _safe_float(horse.get("plcOdds")),
                    "age": _safe_float(horse.get("age")),
                    "seG1fAccTime": _safe_float(horse.get("seG1fAccTime")),
                    "sjG1fOrd": _safe_float(horse.get("sjG1fOrd")),
                    "seG3fAccTime": _safe_float(horse.get("seG3fAccTime")),
                    "sjG3fOrd": _safe_float(horse.get("sjG3fOrd")),
                    "seS1fAccTime": _safe_float(horse.get("seS1fAccTime")),
                    "sjS1fOrd": _safe_float(horse.get("sjS1fOrd")),
                    "horse_win_rate": _safe_float(features.get("horse_win_rate")),
                    "horse_place_rate": _safe_float(features.get("horse_place_rate")),
                    "jockey_win_rate": _safe_float(features.get("jockey_win_rate")),
                    "jockey_place_rate": _safe_float(features.get("jockey_place_rate")),
                    "trainer_win_rate": _safe_float(features.get("trainer_win_rate")),
                    "trainer_place_rate": _safe_float(
                        features.get("trainer_place_rate")
                    ),
                    "rest_days": _safe_float(features.get("rest_days")),
                    "jockey_recent_win_rate": _safe_float(
                        features.get("jockey_recent_win_rate")
                    ),
                    "rating_rank": _safe_float(features.get("rating_rank")),
                    "odds_rank": _safe_float(features.get("odds_rank")),
                    "age_prime": 1.0 if features.get("age_prime") else 0.0,
                    "year_place_rate": _year_place_rate(horse),
                    "total_place_rate": _total_place_rate(horse),
                    "jockey_total_place_rate": _place_rate(
                        jockey.get("ord1CntT"),
                        jockey.get("ord2CntT"),
                        jockey.get("ord3CntT"),
                        jockey.get("rcCntT"),
                    ),
                    "trainer_total_place_rate": _place_rate(
                        trainer.get("ord1CntT"),
                        trainer.get("ord2CntT"),
                        trainer.get("ord3CntT"),
                        trainer.get("rcCntT"),
                    ),
                    "field_size": float(len(horses)),
                    "is_handicap": 1.0
                    if "핸디캡" in str(info.get("budam", ""))
                    else 0.0,
                    "dist": float(dist),
                    "is_sprint": 1.0 if dist <= 1200 else 0.0,
                    "is_mile": 1.0 if 1200 < dist <= 1600 else 0.0,
                    "is_route": 1.0 if dist > 1600 else 0.0,
                    "is_large": 1.0 if len(horses) >= 12 else 0.0,
                    "race_id": race["race_id"],
                    "chulNo": horse.get("chulNo"),
                    "target": 1 if horse.get("chulNo") in actual else 0,
                }
            )

        rank_sources = {
            "rating_rr": [row["rating"] for row in local_rows],
            "wgBudam_rr": [row["wgBudam"] for row in local_rows],
            "winOdds_rr": [row["winOdds"] for row in local_rows],
            "plcOdds_rr": [row["plcOdds"] for row in local_rows],
            "horse_place_rate_rr": [row["horse_place_rate"] for row in local_rows],
            "jockey_place_rate_rr": [row["jockey_place_rate"] for row in local_rows],
            "trainer_place_rate_rr": [row["trainer_place_rate"] for row in local_rows],
            "year_place_rate_rr": [row["year_place_rate"] for row in local_rows],
            "total_place_rate_rr": [row["total_place_rate"] for row in local_rows],
            "seG1fAccTime_rr": [row["seG1fAccTime"] for row in local_rows],
            "sjG1fOrd_rr": [row["sjG1fOrd"] for row in local_rows],
            "seG3fAccTime_rr": [row["seG3fAccTime"] for row in local_rows],
            "sjG3fOrd_rr": [row["sjG3fOrd"] for row in local_rows],
            "seS1fAccTime_rr": [row["seS1fAccTime"] for row in local_rows],
            "sjS1fOrd_rr": [row["sjS1fOrd"] for row in local_rows],
        }
        reverse_features = {
            "rating_rr",
            "horse_place_rate_rr",
            "jockey_place_rate_rr",
            "trainer_place_rate_rr",
            "year_place_rate_rr",
            "total_place_rate_rr",
        }
        for feature_name, values in rank_sources.items():
            ranks = _percentile_rank(values, reverse=feature_name in reverse_features)
            for row, rank in zip(local_rows, ranks, strict=False):
                row[feature_name] = rank

        rows.extend(local_rows)

    X = np.array(
        [[row.get(name, np.nan) for name in FEATURES] for row in rows], dtype=float
    )
    y = np.array([row["target"] for row in rows])
    groups = np.array([row["race_id"] for row in rows])
    chuls = [row["chulNo"] for row in rows]
    return X, y, groups, chuls


def _summarize(
    groups: np.ndarray,
    chuls: list[int],
    probs: np.ndarray,
    answers: dict[str, list[int]],
) -> dict[str, float | int]:
    bucket: dict[str, list[tuple[float, int]]] = defaultdict(list)
    for race_id, chul_no, prob in zip(groups, chuls, probs, strict=False):
        bucket[str(race_id)].append((float(prob), chul_no))

    hits: list[int] = []
    for race_id, values in bucket.items():
        predicted = [
            chul_no
            for prob, chul_no in sorted(values, key=lambda item: item[0], reverse=True)[
                :3
            ]
        ]
        actual = answers.get(race_id, [])[:3]
        hits.append(len(set(predicted) & set(actual)))

    return {
        "exact_3of3": sum(1 for value in hits if value == 3),
        "hit_2of3": sum(1 for value in hits if value == 2),
        "hit_1of3": sum(1 for value in hits if value == 1),
        "miss_0of3": sum(1 for value in hits if value == 0),
        "avg_set_match": round(sum(value / 3 for value in hits) / len(hits), 6),
    }


def _make_model(config: dict) -> Pipeline:
    return Pipeline(
        [
            ("imp", SimpleImputer(strategy="median")),
            (
                "clf",
                HistGradientBoostingClassifier(
                    max_depth=config["max_depth"],
                    learning_rate=config["learning_rate"],
                    max_iter=config["max_iter"],
                    min_samples_leaf=config["min_samples_leaf"],
                    l2_regularization=config["l2_regularization"],
                    random_state=42,
                ),
            ),
        ]
    )


def run(config_name: str) -> dict:
    mini = json.loads((SNAPSHOT_DIR / "mini_val.json").read_text())
    holdout = json.loads((SNAPSHOT_DIR / "holdout.json").read_text())
    answers = json.loads((SNAPSHOT_DIR / "answer_key.json").read_text())
    config = CONFIGS[config_name]

    X_train, y_train, groups_train, chuls_train = _build_rows(mini, answers["mini_val"])
    X_test, y_test, groups_test, chuls_test = _build_rows(holdout, answers["holdout"])
    model = _make_model(config)

    cv_rows = []
    for train_idx, valid_idx in GroupKFold(n_splits=5).split(
        X_train, y_train, groups_train
    ):
        model.fit(X_train[train_idx], y_train[train_idx])
        valid_probs = model.predict_proba(X_train[valid_idx])[:, 1]
        cv_rows.append(
            _summarize(
                groups_train[valid_idx],
                [chuls_train[idx] for idx in valid_idx],
                valid_probs,
                answers["mini_val"],
            )
        )

    model.fit(X_train, y_train)
    train_probs = model.predict_proba(X_train)[:, 1]
    holdout_probs = model.predict_proba(X_test)[:, 1]

    return {
        "config": {"name": config_name, **config},
        "cv": {
            "exact_3of3_mean": round(
                sum(row["exact_3of3"] for row in cv_rows) / len(cv_rows), 3
            ),
            "avg_set_match_mean": round(
                sum(row["avg_set_match"] for row in cv_rows) / len(cv_rows), 6
            ),
        },
        "mini_train": _summarize(
            groups_train, chuls_train, train_probs, answers["mini_val"]
        ),
        "holdout": _summarize(
            groups_test, chuls_test, holdout_probs, answers["holdout"]
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", choices=sorted(CONFIGS), default="hgb_c")
    args = parser.parse_args()
    print(json.dumps(run(args.config), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
