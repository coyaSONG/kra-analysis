"""Read-only public journal/source replay; does not activate or score a study."""

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path

from shared import kra_schedule

from autoresearch import condition_population_chain as chain
from autoresearch import condition_population_sources as sources
from autoresearch.condition_historical_publication import archive, pin, read
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import encoded, parse_json, sha256

VERSION = "condition-population-replay-v1"
SCOPE_VERSION = "condition-population-scope-draft-v1"


def expected_scopes(scope):
    if (
        set(scope) != {"format_version", "weeks"}
        or scope["format_version"] != SCOPE_VERSION
    ):
        raise ValueError("population_scope_schema")
    if type(scope["weeks"]) is not list or not scope["weeks"]:
        raise ValueError("population_scope_empty")
    scopes, weeks, prior_end = [], set(), None
    for week in scope["weeks"]:
        if set(week) != {"week_id", "start_date", "end_date", "venues"}:
            raise ValueError("population_week_schema")
        wid = chain.identifier(week["week_id"])
        start = datetime.strptime(week["start_date"], "%Y%m%d")
        end = datetime.strptime(week["end_date"], "%Y%m%d")
        venues = week["venues"]
        if (
            wid in weeks
            or start.strftime("%Y%m%d") != week["start_date"]
            or end.strftime("%Y%m%d") != week["end_date"]
            or start.weekday() != 0
            or end - start != timedelta(days=6)
            or prior_end is not None
            and start != prior_end + timedelta(days=1)
            or type(venues) is not list
            or any(type(v) is not int or v < 1 for v in venues)
            or venues != sorted(set(venues))
            or not {1, 2, 3, 4} <= set(venues)
        ):
            raise ValueError("population_week_scope")
        weeks.add(wid)
        prior_end = end
        scopes.extend(
            {
                "week_id": wid,
                "race_date": (start + timedelta(days=n)).strftime("%Y%m%d"),
                "meet": meet,
                "observed_race_ids": [],
                "closure": "not_verified",
            }
            for n in range(7)
            for meet in venues
        )
    return weeks, scopes


def audit(manifest_path, expected_sha):
    path = Path(manifest_path).absolute()
    manifest = parse_json(pin(path.parent, {"path": path.name, "sha256": expected_sha}))
    if (
        set(manifest) != {"format_version", "umbrella", "journal", "snapshots"}
        or manifest["format_version"] != VERSION
        or type(manifest["snapshots"]) is not dict
    ):
        raise ValueError("population_manifest_schema")
    scope, scope_fact = archive(path.parent, manifest["umbrella"])
    journal, journal_fact = archive(path.parent, manifest["journal"])
    result = {
        "format_version": VERSION,
        "status": "pending_publication",
        "scope": "selected_public_journal_and_snapshot_membership_only",
        "manifest_sha256": expected_sha,
        "audited_at": datetime.now(UTC).isoformat(),
        "verifier_sha256": sha256(read(Path(__file__))),
        "chain_verifier_sha256": sha256(read(Path(chain.__file__))),
        "source_verifier_sha256": sha256(read(Path(sources.__file__))),
        "schedule_parser_sha256": sha256(read(Path(kra_schedule.__file__))),
        "publications": {"umbrella": scope_fact, "journal": journal_fact},
        "full_population_verified": False,
        "denominator": None,
        "usable_for_scoring": False,
        "counts_as_70_percent_evidence": False,
        "actual_fit_count": 0,
        "outcomes_loaded": False,
        "registration_performed": False,
    }
    if scope is None:
        return result
    weeks, scopes = expected_scopes(scope)
    result["expected_scopes"] = scopes
    if journal is None:
        return result
    scope_at = timestamp(scope_fact["witness"]["merged_at"])
    journal_at = timestamp(journal_fact["witness"]["merged_at"])
    if scope_at > journal_at:
        raise ValueError("population_publication_order")
    structure = chain.validate(
        journal, manifest["umbrella"]["sha256"], weeks, journal_at
    )
    result.update(
        status="observations_replayed",
        chain=structure,
        latest_journal_or_history_completeness="not_verified",
        semantic_events=[],
        inventories=[],
        outside_declared_scope=[],
    )
    lookup = {(s["race_date"], s["meet"]): s for s in scopes}
    used, all_ids = set(), set()
    for wrapped in structure["events"]:
        event, digest = wrapped["event"], wrapped["event_sha256"]
        if timestamp(event["recorded_at"]) < scope_at:
            raise ValueError("population_event_before_scope_publication")
        if event["event_type"] != "week_inventory":
            result["semantic_events"].append(
                {
                    "event_sha256": digest,
                    "status": "unverified_assertion",
                    "event": event,
                }
            )
            continue
        if set(event["payload"]) != {"capture_sha256"}:
            raise ValueError("population_inventory_schema")
        capture_sha = event["payload"]["capture_sha256"]
        if (
            capture_sha not in event["evidence_refs"]
            or capture_sha not in manifest["snapshots"]
            or manifest["snapshots"][capture_sha]["sha256"] != capture_sha
        ):
            raise ValueError("population_inventory_source_binding")
        used.add(capture_sha)
        try:
            frame = sources.snapshot(
                path.parent,
                manifest["snapshots"][capture_sha],
                timestamp(event["recorded_at"]),
            )
        except FileNotFoundError:
            frame = {"status": "pending_local_capture", "dates": []}
        frame["event_sha256"] = digest
        result["inventories"].append(frame)
        for report in frame["dates"]:
            for race in report["races"]:
                rid = race["race_id"]
                day, meet, _ = rid.split("_")
                all_ids.add(rid)
                target = lookup.get((day, int(meet)))
                if target is None:
                    result["outside_declared_scope"].append(
                        {"event_sha256": digest, "race_id": rid}
                    )
                else:
                    target["observed_race_ids"].append(rid)
    if used != set(manifest["snapshots"]):
        raise ValueError("population_unused_snapshot_pins")
    for scope in scopes:
        scope["observed_race_ids"] = sorted(set(scope["observed_race_ids"]))
    result["observed_canonical_ids"] = sorted(all_ids)
    result["observed_identifier_count_not_physical_n"] = len(all_ids)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args(argv)
    try:
        result = audit(args.manifest, args.sha256)
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        result = {
            "status": "blocked",
            "reason": str(exc),
            "denominator": None,
            "full_population_verified": False,
            "usable_for_scoring": False,
            "counts_as_70_percent_evidence": False,
            "actual_fit_count": 0,
            "outcomes_loaded": False,
            "registration_performed": False,
        }
    print(encoded(result).decode(), end="")
    return 0 if result["status"] == "observations_replayed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
