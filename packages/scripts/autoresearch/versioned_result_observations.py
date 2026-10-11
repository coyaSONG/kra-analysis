"""Replay versioned result observations, not settlement or model performance."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from shared.kra_race_identity import validate_race_identity
from shared.official_result_support import reconcile_group

from autoresearch.frozen_history_view import replay_frozen
from autoresearch.kra_race_card_pdf_replay import parse_json
from autoresearch.kra_result_population_audit import inspect_top3
from autoresearch.kra_schedule_snapshot import replay_schedule_snapshot
from autoresearch.observed_history_seed import digest, save
from autoresearch.official_history_support import replay_archive

FORMAT = "kra-versioned-result-observations-v1"
POLICY = "unique-ranks-1-2-3-whole-roster-v1"
VOID_NOTE = "\uacbd\uc8fc\ubd88\uc131\ub9bd"
POLICY_RULES = {
    "version": POLICY,
    "membership": "complete_dated_national_schedule",
    "identity": "dated_physical_event_and_complete_api_html_roster_equality",
    "top3": "one_each_1_2_3_same_ids_and_all_ranked_rows_agree",
    "lower_blank_rows": "preserved_not_automatically_excluded",
    "void": "explicit_api_text_observation_not_settlement_or_binary_score",
    "ties": "unsupported_top3_mapping_preserved_without_tiebreak",
    "performance": "not_computed",
}


def value_hash(value):
    return digest(json.dumps(value, sort_keys=True, allow_nan=False).encode())


def source_hashes():
    root = Path(__file__).resolve().parents[1]
    names = (
        "autoresearch/versioned_result_observations.py",
        "autoresearch/frozen_history_view.py",
        "autoresearch/observed_history_seed.py",
        "autoresearch/official_history_support.py",
        "autoresearch/kra_schedule_snapshot.py",
        "autoresearch/kra_result_snapshot.py",
        "autoresearch/kra_result_population_audit.py",
        "autoresearch/kra_race_card_pdf_replay.py",
        "shared/official_result_support.py",
        "shared/kra_result_history.py",
        "shared/kra_race_identity.py",
    )
    return {name: digest((root / name).read_bytes()) for name in names}


def _identity(value):
    day, meet, number = value.split("_")
    validate_race_identity(int(meet), day, int(number))
    if value != f"{day}_{int(meet)}_{int(number)}":
        raise ValueError("noncanonical_result_race_id")


def observe_race(race_id, count, records, official):
    """Inputs are normalized source replays; all rows remain visible."""
    _identity(race_id)
    if type(count) is not int or not 1 <= count <= 20:
        raise ValueError("invalid_scheduled_runner_count")
    if any(row["race_id"] != race_id for row in records):
        raise ValueError("mixed_result_race_ids")
    diagnostic = inspect_top3(records, count)
    output = {
        "race_id": race_id,
        "scheduled_runner_count": count,
        "observed_runner_count": len(records),
        "schedule_count_agrees": count == len(records),
        "status": "source_missing",
        "observed_top3_horse_ids": None,
        "api_diagnostic": diagnostic,
        "exception_notes": dict(
            sorted(
                Counter(
                    r.get("raw_ord_bigo")
                    for r in records
                    if r.get("raw_ord_bigo") not in (None, "", "-")
                ).items()
            )
        ),
        "api_records": sorted(records, key=lambda row: row["chul_no"]),
        "official_observation": official,
        "reasons": [],
        "official_finality_verified": False,
        "settlement_policy_verified": False,
    }
    if not records or official is None:
        output["reasons"] = ["missing_api" if not records else "missing_official"]
        return output
    comparison = reconcile_group(records, official)
    output["comparison"] = comparison
    if comparison["official_event_support"] == "unknown":
        output["reasons"] = comparison["reason_codes"]
        return output
    if (
        comparison["official_event_support"] != "confirmed"
        or comparison["roster_support"] != "exact"
    ):
        output.update(status="source_conflict", reasons=comparison["reason_codes"])
        return output

    void_notes = [r.get("raw_ord_bigo") == VOID_NOTE for r in records]
    blank = all(not r["rank_text"] and not r["time_text"] for r in official["rows"])
    output.update(
        api_all_rows_void_text_observed=all(void_notes), html_all_rank_time_blank=blank
    )
    if any(void_notes) and (
        not blank
        or any(str(r["raw_ord"]) in {str(n) for n in range(1, 21)} for r in records)
    ):
        output.update(
            status="source_conflict", reasons=["void_note_with_finish_observation"]
        )
        return output

    # Even an unresolved API row can contradict the proposed top-three set.
    conflicts = []
    for row in comparison["rows"]:
        if "conflict" in (row["rank_support"], row["time_support"]):
            conflicts.append("rank_or_time_conflict")
        if row["event_linked_api_unresolved"] and (
            row["official_row"]["rank_text"] or row["official_row"]["time_text"]
        ):
            conflicts.append("unresolved_api_has_official_finish")
    if conflicts:
        output.update(status="source_conflict", reasons=sorted(set(conflicts)))
        return output
    if blank:
        output.update(
            status="void_reported_no_top3"
            if all(void_notes)
            else "no_top3_reason_unknown",
            reasons=["api_void_text_not_independent_html_status"]
            if all(void_notes)
            else ["blank_ranks_do_not_establish_void"],
        )
        return output
    web_ranks = Counter(row["rank_text"] for row in official["rows"])
    candidate = diagnostic["candidate_top3_horse_ids"]
    if candidate is None or any(web_ranks[str(rank)] != 1 for rank in (1, 2, 3)):
        output.update(status="top3_unresolved", reasons=["no_unique_1_2_3"])
        return output
    web_top3 = sorted(
        (r["horse_id"] for r in official["rows"] if r["rank_text"] in ("1", "2", "3")),
        key=int,
    )
    if web_top3 != candidate:
        output.update(status="source_conflict", reasons=["top3_identity_conflict"])
        return output
    output.update(status="unique_top3_observed", observed_top3_horse_ids=candidate)
    return output


def project_population(scheduled, records, official):
    """Left join, never use observed/ordinary races as a replacement population."""
    if not scheduled:
        raise ValueError("empty_result_population")
    groups = defaultdict(list)
    keys = set()
    for record in records:
        key = record["race_id"], record["chul_no"]
        if key in keys:
            raise ValueError("duplicate_result_population_runner")
        keys.add(key)
        groups[record["race_id"]].append(record)
    ledger = [
        observe_race(race_id, count, groups[race_id], official.get(race_id))
        for race_id, count in sorted(scheduled.items())
    ]
    return {
        "format_version": FORMAT,
        "observation_policy": POLICY,
        "observation_policy_rules": POLICY_RULES.copy(),
        "observation_policy_sha256": value_hash(POLICY_RULES),
        "scheduled_race_count": len(scheduled),
        "status_counts": dict(sorted(Counter(r["status"] for r in ledger).items())),
        "schedule_count_difference_count": sum(
            not r["schedule_count_agrees"] for r in ledger
        ),
        "extra_api_races": sorted(set(groups) - set(scheduled)),
        "extra_official_races": sorted(set(official) - set(scheduled)),
        "ledger": ledger,
        "prediction_evaluation": "not_performed_outcome_observations_only",
        "counts_as_70_percent_evidence": False,
    }


def replay_plan(path, sha256):
    raw = path.read_bytes()
    if digest(raw) != sha256:
        raise ValueError("result_observation_plan_pin_mismatch")
    plan = parse_json(raw)
    if plan["format_version"] != FORMAT:
        raise ValueError("unsupported_result_observation_plan")
    dates = plan["race_dates"]
    if not dates or len(set(dates)) != len(dates):
        raise ValueError("invalid_result_observation_dates")
    scheduled = {}
    for day in dates:
        validate_race_identity(1, day, 1)
        schedule = replay_schedule_snapshot(
            Path(plan["schedule_capture"]), race_date=day
        )
        if schedule["capture_manifest_sha256"] != plan["schedule_sha256"]:
            raise ValueError("result_observation_schedule_pin_mismatch")
        if schedule["status"] != "reconciled" or schedule["source_failures"]:
            raise ValueError("result_observation_schedule_unreconciled")
        for race in schedule["races"]:
            key = race["race_id"]
            if key in scheduled:
                raise ValueError("duplicate_result_scheduled_race")
            scheduled[key] = race["source_observations"]["national"]["runners"]
    seed = replay_frozen(
        Path(plan["seed_root"]), Path(plan["seed_path"]), plan["seed_sha256"]
    )
    evidence = replay_archive(
        Path(plan["official_directory"]),
        plan["official_archive_sha256"],
        seed,
        plan["seed_sha256"],
    )
    selected = [r for r in seed["records"] if r["race_id"].split("_")[0] in dates]
    official = {
        key: value for key, value in evidence.items() if key.split("_")[0] in dates
    }
    result = project_population(
        scheduled, selected, {k: v["parsed"] for k, v in official.items()}
    )
    implementation = source_hashes()
    for row in result["ledger"]:
        row["official_source"] = official.get(row["race_id"])
        row["publisher_revision_id"] = None
        row["result_observation_id"] = value_hash(
            {
                "race_id": row["race_id"],
                "api_records": row["api_records"],
                "official_source": row["official_source"],
                "policy_sha256": result["observation_policy_sha256"],
                "implementation": implementation,
            }
        )
    result.update(
        plan_sha256=sha256,
        source_plan=plan,
        seed_total_rows=len(seed["records"]),
        selected_date_rows=len(selected),
        source_scope="selected_dates_from_frozen_seed_not_global_history",
        implementation_sha256=digest(Path(__file__).read_bytes()),
        observation_source_sha256=implementation,
    )
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = replay_plan(args.plan, args.plan_sha256)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report_sha = save(args.output, result)
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in ("ledger", "source_plan")}
            | {"report_sha256": report_sha},
            sort_keys=True,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
