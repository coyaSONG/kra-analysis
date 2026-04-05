from __future__ import annotations

import argparse
import importlib
import json
import re
import sys
from collections import defaultdict
from copy import deepcopy
from pathlib import Path

import numpy as np
from sklearn.ensemble import (
    ExtraTreesClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

SNAPSHOT_DIR = Path(__file__).resolve().parent / "snapshots"
SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.append(str(SCRIPT_ROOT))

SAFE_FEATURES = [
    "rating",
    "wgBudam",
    "wgHr_value",
    "winOdds",
    "plcOdds",
    "age",
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
    "jockey_form",
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
    "burden_ratio",
    "hr_starts_y",
    "hr_starts_t",
    "horse_top3_skill",
    "horse_starts_y",
    "horse_low_sample",
    "jk_skill",
    "tr_skill",
    "horse_skill_rank",
    "jk_skill_rank",
    "tr_skill_rank",
    "wg_budam_rank",
    "gap_3rd_4th",
    "field_size_live",
    "wet_track",
    "cancelled_count",
    "training_score",
    "days_since_training",
    "recent_training",
    "owner_win_rate",
    "owner_skill",
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

MARKET_FEATURES = {
    "winOdds",
    "plcOdds",
    "odds_rank",
    "winOdds_rr",
    "plcOdds_rr",
}


def _compute_race_features(horses: list[dict]) -> list[dict]:
    module = importlib.import_module("feature_engineering")
    return module.compute_race_features(horses)


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


def _parse_leading_number(value, default=np.nan) -> float:
    if value in ("", None):
        return default
    text = str(value)
    match = re.match(r"^-?\d+(?:\.\d+)?", text)
    if not match:
        return default
    return _safe_float(match.group(0), default)


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


def _sex_code(value) -> float:
    mapping = {"수": 0.0, "암": 1.0, "거": 2.0}
    return mapping.get(value, np.nan)


def _weather_code(value) -> float:
    mapping = {"맑음": 0.0, "흐림": 1.0, "비": 2.0, "눈": 3.0}
    return mapping.get(value, np.nan)


def _budam_code(value) -> float:
    mapping = {"마령": 0.0, "별정A": 1.0, "별정B": 2.0, "핸디캡": 3.0}
    return mapping.get(value, np.nan)


def _rest_risk_code(value) -> float:
    mapping = {"low": 0.0, "medium": 1.0, "high": 2.0}
    return mapping.get(value, np.nan)


def _class_code(value) -> float:
    mapping = {
        "국6등급": 1.0,
        "국5등급": 2.0,
        "국4등급": 3.0,
        "혼4등급": 3.0,
        "국3등급": 4.0,
        "혼3등급": 4.0,
        "2등급": 5.0,
        "1등급": 6.0,
        "국OPEN": 7.0,
        "혼OPEN": 7.0,
    }
    return mapping.get(str(value or ""), np.nan)


def _track_pct(value) -> float:
    if value in ("", None):
        return np.nan
    match = re.search(r"\((\d+)%\)", str(value))
    if not match:
        return np.nan
    return _safe_float(match.group(1), np.nan)


def _pre_race_horse_order(horses: list[dict]) -> list[dict]:
    return sorted(
        horses,
        key=lambda horse: (
            _safe_int(horse.get("chulNo"), 999),
            str(horse.get("hrNo") or ""),
        ),
    )


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


def _validate_features(features: list[str]) -> None:
    unknown = sorted(set(features) - set(SAFE_FEATURES))
    if unknown:
        raise ValueError(f"Unknown or forbidden features requested: {unknown}")


def _build_feature_rows(races: list[dict], answers: dict[str, list[int]]) -> list[dict]:
    rows: list[dict] = []
    for race in races:
        info = race.get("race_info") or {}
        horses = deepcopy(_pre_race_horse_order(race["horses"]))
        refreshed = _compute_race_features(deepcopy(horses))
        for horse, fresh in zip(horses, refreshed, strict=False):
            existing_features = horse.get("computed_features") or {}
            fresh_features = fresh.get("computed_features") or {}
            horse["computed_features"] = {**fresh_features, **existing_features}
        actual = set(answers.get(race["race_id"], [])[:3])
        local_rows: list[dict] = []

        for horse in horses:
            features = horse.get("computed_features") or {}
            jockey = horse.get("jkDetail") or {}
            trainer = horse.get("trDetail") or {}
            horse_detail = horse.get("hrDetail") or {}
            dist = _safe_int(info.get("rcDist"), 0)
            local_rows.append(
                {
                    "rating": _safe_float(horse.get("rating")),
                    "wgBudam": _safe_float(horse.get("wgBudam")),
                    "wgHr_value": _parse_leading_number(horse.get("wgHr")),
                    "winOdds": _safe_float(horse.get("winOdds")),
                    "plcOdds": _safe_float(horse.get("plcOdds")),
                    "age": _safe_float(horse.get("age")),
                    "draw_no": _safe_float(horse.get("chulNo")),
                    "sex_code": _sex_code(horse.get("sex")),
                    "weather_code": _weather_code(info.get("weather")),
                    "track_pct": _track_pct(info.get("track")),
                    "class_code": _class_code(horse.get("class_rank")),
                    "budam_code": _budam_code(info.get("budam")),
                    "rest_risk_code": _rest_risk_code(features.get("rest_risk")),
                    "allowance_flag": 1.0
                    if str(horse.get("wgBudamBigo")) == "*"
                    else 0.0,
                    "horse_win_rate": _safe_float(features.get("horse_win_rate")),
                    "horse_place_rate": _safe_float(features.get("horse_place_rate")),
                    "jockey_win_rate": _safe_float(features.get("jockey_win_rate")),
                    "jockey_place_rate": _safe_float(features.get("jockey_place_rate")),
                    "trainer_win_rate": _safe_float(features.get("trainer_win_rate")),
                    "trainer_place_rate": _safe_float(
                        features.get("trainer_place_rate")
                    ),
                    "jockey_form": _safe_float(features.get("jockey_form")),
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
                    "burden_ratio": _safe_float(features.get("burden_ratio")),
                    "hr_starts_y": _safe_float(horse_detail.get("rcCntY")),
                    "hr_starts_t": _safe_float(horse_detail.get("rcCntT")),
                    "horse_top3_skill": _safe_float(features.get("horse_top3_skill")),
                    "horse_starts_y": _safe_float(features.get("horse_starts_y")),
                    "horse_low_sample": 1.0
                    if features.get("horse_low_sample") is True
                    else 0.0
                    if features.get("horse_low_sample") is False
                    else np.nan,
                    "jk_skill": _safe_float(features.get("jk_skill")),
                    "tr_skill": _safe_float(features.get("tr_skill")),
                    "horse_skill_rank": _safe_float(features.get("horse_skill_rank")),
                    "jk_skill_rank": _safe_float(features.get("jk_skill_rank")),
                    "tr_skill_rank": _safe_float(features.get("tr_skill_rank")),
                    "wg_budam_rank": _safe_float(features.get("wg_budam_rank")),
                    "gap_3rd_4th": _safe_float(features.get("gap_3rd_4th")),
                    "field_size_live": _safe_float(features.get("field_size_live")),
                    "wet_track": 1.0
                    if features.get("wet_track") is True
                    else 0.0
                    if features.get("wet_track") is False
                    else np.nan,
                    "cancelled_count": _safe_float(features.get("cancelled_count")),
                    "training_score": _safe_float(features.get("training_score")),
                    "days_since_training": _safe_float(
                        features.get("days_since_training")
                    ),
                    "recent_training": 1.0
                    if features.get("recent_training") is True
                    else 0.0
                    if features.get("recent_training") is False
                    else np.nan,
                    "owner_win_rate": _safe_float(features.get("owner_win_rate")),
                    "owner_skill": _safe_float(features.get("owner_skill")),
                    "jk_place_rate_y": _place_rate(
                        jockey.get("ord1CntY"),
                        jockey.get("ord2CntY"),
                        jockey.get("ord3CntY"),
                        jockey.get("rcCntY"),
                    ),
                    "tr_place_rate_y": _place_rate(
                        trainer.get("ord1CntY"),
                        trainer.get("ord2CntY"),
                        trainer.get("ord3CntY"),
                        trainer.get("rcCntY"),
                    ),
                    "race_id": race["race_id"],
                    "race_date": race["race_date"],
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
            "draw_rr": [row["draw_no"] for row in local_rows],
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

    return rows


def _snapshot_order_alignment(
    races: list[dict], answers: dict[str, list[int]]
) -> dict[str, float]:
    checked = 0
    raw_match = 0
    normalized_match = 0

    for race in races:
        actual = answers.get(race["race_id"], [])[:3]
        if not actual:
            continue
        checked += 1
        raw_top3 = [horse.get("chulNo") for horse in race["horses"][:3]]
        normalized_top3 = [
            horse.get("chulNo") for horse in _pre_race_horse_order(race["horses"])[:3]
        ]
        if raw_top3 == actual:
            raw_match += 1
        if normalized_top3 == actual:
            normalized_match += 1

    return {
        "checked_races": checked,
        "raw_first3_match_rate": round(raw_match / checked, 6) if checked else 0.0,
        "normalized_first3_match_rate": round(normalized_match / checked, 6)
        if checked
        else 0.0,
    }


def _load_dataset(dataset_name: str) -> tuple[list[dict], dict[str, list[int]]]:
    data = json.loads((SNAPSHOT_DIR / f"{dataset_name}.json").read_text())
    answer_path = SNAPSHOT_DIR / f"{dataset_name}_answer_key.json"
    answers = json.loads(answer_path.read_text())
    if "meta" in answers:
        answers = {k: v for k, v in answers.items() if k != "meta"}
    return data, answers


def _build_arrays(
    rows: list[dict], features: list[str]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[int]]:
    X = np.array(
        [[row.get(name, np.nan) for name in features] for row in rows], dtype=float
    )
    y = np.array([row["target"] for row in rows], dtype=int)
    groups = np.array([row["race_id"] for row in rows])
    dates = np.array([row["race_date"] for row in rows])
    chuls = [row["chulNo"] for row in rows]
    return X, y, groups, dates, chuls


def _all_missing_features(X: np.ndarray, features: list[str]) -> list[str]:
    missing: list[str] = []
    for idx, feature in enumerate(features):
        column = X[:, idx]
        if np.isnan(column).all():
            missing.append(feature)
    return missing


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
        if not actual:
            continue
        hits.append(len(set(predicted) & set(actual)))

    exact = sum(1 for value in hits if value == 3)
    return {
        "races": len(hits),
        "exact_3of3": exact,
        "exact_3of3_rate": round(exact / len(hits), 6) if hits else 0.0,
        "hit_2of3": sum(1 for value in hits if value == 2),
        "hit_1of3": sum(1 for value in hits if value == 1),
        "miss_0of3": sum(1 for value in hits if value == 0),
        "avg_set_match": round(sum(value / 3 for value in hits) / len(hits), 6)
        if hits
        else 0.0,
    }


def _evaluate_window(
    *,
    X: np.ndarray,
    y: np.ndarray,
    groups: np.ndarray,
    dates: np.ndarray,
    chuls: list[int],
    answers: dict[str, list[int]],
    config: dict,
    train_end: str,
    eval_start: str | None,
    eval_end: str | None = None,
) -> dict[str, float | int]:
    train_mask = dates <= train_end
    eval_mask = dates > train_end if eval_start is None else dates >= eval_start
    if eval_end:
        eval_mask = eval_mask & (dates <= eval_end)

    if not train_mask.any() or not eval_mask.any():
        raise ValueError(
            f"Window produced empty partition: train_end={train_end}, eval_start={eval_start}, eval_end={eval_end}"
        )

    model = _make_model(config)
    sample_weight = np.where(
        y[train_mask] == 1, config["model"].get("positive_class_weight", 1.0), 1.0
    )
    model.fit(X[train_mask], y[train_mask], clf__sample_weight=sample_weight)
    probs = model.predict_proba(X[eval_mask])[:, 1]

    eval_answers = {}
    for rid, ans in answers.items():
        date = rid[:8]
        if eval_start is None:
            if date <= train_end:
                continue
        elif date < eval_start:
            continue
        if eval_end and date > eval_end:
            continue
        eval_answers[rid] = ans

    return _summarize(
        groups[eval_mask],
        [chuls[idx] for idx, flag in enumerate(eval_mask) if flag],
        probs,
        eval_answers,
    )


def _make_model(config: dict) -> Pipeline:
    model = config["model"]
    kind = model["kind"]
    params = model["params"]

    if kind == "hgb":
        clf = HistGradientBoostingClassifier(
            max_depth=params["max_depth"],
            learning_rate=params["learning_rate"],
            max_iter=params["max_iter"],
            min_samples_leaf=params["min_samples_leaf"],
            l2_regularization=params["l2_regularization"],
            random_state=42,
        )
    elif kind == "rf":
        clf = RandomForestClassifier(
            n_estimators=params["n_estimators"],
            max_depth=params["max_depth"],
            min_samples_leaf=params["min_samples_leaf"],
            random_state=42,
            n_jobs=-1,
        )
    elif kind == "et":
        clf = ExtraTreesClassifier(
            n_estimators=params["n_estimators"],
            max_depth=params["max_depth"],
            min_samples_leaf=params["min_samples_leaf"],
            random_state=42,
            n_jobs=-1,
        )
    elif kind == "logreg":
        clf = LogisticRegression(
            max_iter=params["max_iter"],
            C=params["C"],
            class_weight="balanced",
        )
    else:
        raise ValueError(f"Unsupported model kind: {kind}")

    return Pipeline([("imp", SimpleImputer(strategy="median")), ("clf", clf)])


def evaluate(config_path: Path) -> dict:
    config = json.loads(config_path.read_text())
    features = config["features"]
    _validate_features(features)

    races, answers = _load_dataset(config["dataset"])
    rows = _build_feature_rows(races, answers)
    X, y, groups, dates, chuls = _build_arrays(rows, features)

    split = config["split"]
    train_mask = dates <= split["train_end"]
    dev_mask = (dates > split["train_end"]) & (dates <= split["dev_end"])
    test_mask = dates >= split["test_start"]

    if not train_mask.any() or not dev_mask.any() or not test_mask.any():
        raise ValueError("Split produced an empty partition")

    dev_summary = _evaluate_window(
        X=X,
        y=y,
        groups=groups,
        dates=dates,
        chuls=chuls,
        answers=answers,
        config=config,
        train_end=split["train_end"],
        eval_start=None,
        eval_end=split["dev_end"],
    )
    test_summary = _evaluate_window(
        X=X,
        y=y,
        groups=groups,
        dates=dates,
        chuls=chuls,
        answers=answers,
        config=config,
        train_end=split["train_end"],
        eval_start=split["test_start"],
        eval_end=None,
    )
    robust_exact_rate = round(
        min(dev_summary["exact_3of3_rate"], test_summary["exact_3of3_rate"]), 6
    )
    blended_exact_rate = round(
        (dev_summary["exact_3of3_rate"] + test_summary["exact_3of3_rate"]) / 2, 6
    )
    rolling_windows = config.get("rolling_windows") or []
    rolling_results = []
    for window in rolling_windows:
        summary = _evaluate_window(
            X=X,
            y=y,
            groups=groups,
            dates=dates,
            chuls=chuls,
            answers=answers,
            config=config,
            train_end=window["train_end"],
            eval_start=window["eval_start"],
            eval_end=window.get("eval_end"),
        )
        rolling_results.append({"name": window["name"], "summary": summary})

    rolling_min_exact_rate = round(
        min(
            (item["summary"]["exact_3of3_rate"] for item in rolling_results),
            default=robust_exact_rate,
        ),
        6,
    )
    rolling_mean_exact_rate = (
        round(
            (
                sum(item["summary"]["exact_3of3_rate"] for item in rolling_results)
                / len(rolling_results)
            ),
            6,
        )
        if rolling_results
        else robust_exact_rate
    )
    overfit_safe_exact_rate = round(min(robust_exact_rate, rolling_min_exact_rate), 6)

    return {
        "config_path": str(config_path),
        "config": config,
        "feature_count": len(features),
        "market_feature_count": len([f for f in features if f in MARKET_FEATURES]),
        "split": split,
        "model": config["model"],
        "integrity": {
            **_snapshot_order_alignment(races, answers),
            "all_missing_features": _all_missing_features(X, features),
        },
        "summary": {
            "robust_exact_rate": robust_exact_rate,
            "blended_exact_rate": blended_exact_rate,
            "early_primary_exact_rate": robust_exact_rate,
            "rolling_min_exact_rate": rolling_min_exact_rate,
            "rolling_mean_exact_rate": rolling_mean_exact_rate,
            "overfit_safe_exact_rate": overfit_safe_exact_rate,
            "dev_test_gap": round(
                abs(dev_summary["exact_3of3_rate"] - test_summary["exact_3of3_rate"]),
                6,
            ),
        },
        "dev": dev_summary,
        "test": test_summary,
        "rolling": rolling_results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()

    result = evaluate(Path(args.config))
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload)
    print(payload)


if __name__ == "__main__":
    main()
