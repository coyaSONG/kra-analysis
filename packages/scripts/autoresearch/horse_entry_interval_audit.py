"""Compare saved rest proxies with prior observed entries, not actual-start rest."""

from __future__ import annotations

import argparse
import hashlib
import json
from bisect import bisect_left
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

from shared.kra_race_identity import MEET_NAMES, validate_race_identity


def _race_date(key: str, value: str) -> date:
    parts = key.split("_")
    if len(parts) != 3 or parts[0] != value:
        raise ValueError("race_date_identity_mismatch")
    meet, race_no = int(parts[1]), int(parts[2])
    validate_race_identity(meet, value, race_no)
    if key != f"{value}_{meet}_{race_no}":
        raise ValueError("noncanonical_race_id")
    return datetime.strptime(value, "%Y%m%d").date()


def _horse_id(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if type(value) is int and value > 0:
        return str(value)
    if (
        isinstance(value, str)
        and value.isascii()
        and value.isdecimal()
        and int(value) > 0
    ):
        return str(int(value))
    raise ValueError("invalid_stable_horse_id")


def _number(value: Any) -> int:
    if type(value) is not int or not 1 <= value <= 20:
        raise ValueError("invalid_runner_number")
    return value


def _rest(value: Any) -> int | None:
    if value is None:
        return None
    if type(value) is not int or value < 0:
        raise ValueError("invalid_rest_proxy")
    return value


def _check_meet(value: Any, expected: int) -> None:
    normalized = value if type(value) is int else MEET_NAMES.get(value)
    if normalized != expected:
        raise ValueError("source_meet_identity_mismatch")


def build_audit(
    dataset: list[dict[str, Any]], validation: list[dict[str, Any]]
) -> dict[str, Any]:
    targets = {}
    for record in validation:
        state = record["state"]
        key = state["race_id"]
        when = _race_date(key, state["date"])
        if not key.startswith("202510") or key in targets:
            raise ValueError("duplicate_or_non_october_target")
        fields, values = state["runner_fields"], state["runner_values"]
        if (
            not values
            or type(state["field_size"]) is not int
            or len(values) != state["field_size"]
            or len(set(fields)) != len(fields)
            or not {"number", "rest"}.issubset(fields)
            or any(len(row) != len(fields) for row in values)
        ):
            raise ValueError("invalid_target_roster_shape")
        roster = {}
        for row in values:
            number = _number(row[fields.index("number")])
            if number in roster:
                raise ValueError("duplicate_target_runner")
            roster[number] = _rest(row[fields.index("rest")])
        targets[key] = (when, roster)
    if not targets:
        raise ValueError("empty_target_universe")

    races = {}
    history: dict[str, dict[date, list[str]]] = defaultdict(lambda: defaultdict(list))
    # Later races cannot influence earlier gaps, even if the input is unsorted.
    for race in dataset:
        key = race["race_id"]
        when = _race_date(key, race["race_date"])
        if key in races:
            raise ValueError("duplicate_source_race")
        meet = int(key.split("_")[1])
        if "meet" in race:
            _check_meet(race["meet"], meet)
        horses, ids = {}, set()
        for horse in race["horses"]:
            number, stable_id = _number(horse["chulNo"]), _horse_id(horse.get("hrNo"))
            if number in horses or (stable_id is not None and stable_id in ids):
                raise ValueError("duplicate_source_runner_or_horse")
            if "meet" in horse:
                _check_meet(horse["meet"], meet)
            for field, expected in (
                ("rcDate", int(race["race_date"])),
                ("rcNo", int(key.split("_")[2])),
            ):
                if field in horse and horse[field] != expected:
                    raise ValueError("horse_race_identity_mismatch")
            ids.add(stable_id)
            horses[number] = (stable_id, _rest(horse.get("ilsu")))
            if stable_id is not None:
                history[stable_id][when].append(key)
        if not horses:
            raise ValueError("empty_source_roster")
        races[key] = horses
    if not set(targets).issubset(races):
        raise ValueError("missing_target_race")

    dates = {horse: sorted(observations) for horse, observations in history.items()}
    ledger, counts = [], Counter()
    for key, (when, saved) in sorted(targets.items()):
        horses = races[key]
        if set(saved) != set(horses):
            raise ValueError("target_roster_mismatch")
        gaps = []
        for number, proxy in sorted(saved.items()):
            stable_id, ilsu = horses[number]
            if proxy != ilsu:
                raise ValueError("saved_rest_source_disagreement")
            observed = dates.get(stable_id, [])
            index = bisect_left(observed, when) - 1
            previous = observed[index] if index >= 0 else None
            gap = (when - previous).days if previous else None
            status = (
                "missing_stable_id"
                if stable_id is None
                else "no_prior_observed_entry"
                if previous is None
                else "prior_entry_observed"
            )
            counts[status] += 1
            if gap is not None:
                gaps.append(gap)
                if proxy is not None:
                    counts["comparable_rows"] += 1
                    counts["proxy_equals_observed_gap"] += int(proxy == gap)
            ledger.append(
                {
                    "race_id": key,
                    "number": number,
                    "horse_id": stable_id,
                    "saved_rest_proxy": proxy,
                    "days_since_prior_observed_entry": gap,
                    "prior_observed_date": previous.strftime("%Y%m%d")
                    if previous
                    else None,
                    "prior_observed_race_ids": sorted(history[stable_id][previous])
                    if previous is not None
                    else [],
                    "status": status,
                }
            )
        counts["races_with_varying_observed_gaps"] += int(len(set(gaps)) > 1)
        counts["races_with_complete_observed_gaps"] += int(len(gaps) == len(saved))
        counts["races_with_constant_complete_proxy"] += int(
            None not in saved.values() and len(set(saved.values())) == 1
        )
    return {
        "format_version": "horse-observed-entry-interval-audit-v1",
        "diagnostic_only": True,
        "counts_as_70_percent_evidence": False,
        "promotion_safe": False,
        "historical_source_availability": "unproven",
        "actual_start_and_history_completeness": "unproven",
        "production_feature_changed": False,
        "target_race_count": len(targets),
        "target_runner_count": len(ledger),
        "source_race_count": len(races),
        "counts": {
            name: counts[name]
            for name in (
                "missing_stable_id",
                "no_prior_observed_entry",
                "prior_entry_observed",
                "comparable_rows",
                "proxy_equals_observed_gap",
                "races_with_varying_observed_gaps",
                "races_with_complete_observed_gaps",
                "races_with_constant_complete_proxy",
            )
        },
        "ledger": ledger,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--validation", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    raw = {name: getattr(args, name).read_bytes() for name in ("dataset", "validation")}
    result = build_audit(
        json.loads(raw["dataset"]),
        [json.loads(line) for line in raw["validation"].splitlines()],
    )
    result["input_pins"] = {
        name: {
            "path": str(getattr(args, name)),
            "sha256": hashlib.sha256(content).hexdigest(),
        }
        for name, content in raw.items()
    }
    serialized = json.dumps(result, indent=2, sort_keys=True) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        stream.write(serialized)
    print(json.dumps({k: v for k, v in result.items() if k != "ledger"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
