"""Read-only endpoint arithmetic of the original May sectional observations."""

import json
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from shared.official_result_support import TIME_CAPTION, reconcile_group, tables

from autoresearch import sectional_source_audit as source
from autoresearch.frozen_history_view import replay_frozen
from autoresearch.observed_history_seed import digest, pinned_path
from autoresearch.official_history_support import replay_archive
from autoresearch.race_conditions import parse_conditions
from autoresearch.restricted_cohort import encoded

GUIDE_ROOT = Path(".cache/autoresearch/sectional-arithmetic/guide-20261020T175117Z")
GUIDE_RECEIPT_SHA = "4fc08a08e789ebfe94b2adea99bd9fc6d15c925614472fe72c67849488711549"
GUIDE_RAW_SHA = "4ad717274decab45d501f1a8884935544117beeb65c866ee000063e884a80ab7"
GUIDE_URL = "https://race.kra.co.kr/raceScore/cornerRecordDesc.do"


def replay_guide(root=GUIDE_ROOT):
    root = Path(root)
    receipt = json.loads(
        pinned_path(
            root, {"path": "capture.json", "sha256": GUIDE_RECEIPT_SHA}
        ).read_bytes()
    )
    if receipt["url"] != GUIDE_URL or receipt["sha256"] != GUIDE_RAW_SHA:
        raise ValueError("wrong_sectional_guide")
    content = pinned_path(
        root, {"path": receipt["raw_file"], "sha256": GUIDE_RAW_SHA}
    ).read_bytes()
    guide_tables = tables(content.decode(receipt["encoding"], errors="strict"))
    rows = [
        [c.text for c in row]
        for table in guide_tables
        for row in table.rows
        if row and row[0].text == "1300"
    ]
    if rows != [["1300", "200", "", "100", "400", "400", "400", "600", "200"]]:
        raise ValueError("unverified_1300_segment_definition")
    return {**receipt, "receipt_sha256": GUIDE_RECEIPT_SHA}


def seconds(text):
    if text == "":
        return None
    match = re.fullmatch(r"([0-9]+):([0-5][0-9](?:\.[0-9]+)?)", text)
    if not match:
        raise ValueError("unparsed_arithmetic_time")
    return Decimal(match[1]) * 60 + Decimal(match[2])


def check_relation(start, end, printed, *, origin=False):
    if printed is None or start is None or end is None:
        return {"status": "missing_value", "residual_seconds": None}
    if printed <= 0 or end <= 0 or start < 0 or (start == 0 and not origin):
        return {"status": "nonpositive_value", "residual_seconds": None}
    if end <= start:
        return {"status": "nonincreasing_clock", "residual_seconds": None}
    residual = printed - (end - start)
    return {
        "status": "exact" if residual == 0 else "arithmetic_conflict",
        "residual_seconds": str(residual),
    }


def relations(kind, distance, values):
    """Return named endpoints and exact raw operands; never add overlapping spans."""
    if kind == "seoul":
        if len(values["seoul"]) != 10:
            raise ValueError("invalid_arithmetic_row_width")
        v = values["seoul"]
        return [
            ("final_600", distance - 600, distance, v[4], v[9], v[7]),
            ("final_200", distance - 200, distance, v[6], v[9], v[8]),
        ]
    if kind == "jeju":
        return []
    if kind != "busan":
        raise ValueError("unknown_arithmetic_venue")
    header = source.headers("busan_cumulative", distance)[1]
    cumulative = values["busan_cumulative"]
    segments = values["busan_segment"]
    if len(cumulative) != 8 or len(segments) != 9:
        raise ValueError("invalid_arithmetic_row_width")
    checkpoints = {0: "0:00.0", distance: cumulative[-1]}
    for label, text in zip(header, cumulative[:-1], strict=True):
        if label == "-":
            if text != "":
                raise ValueError("value_at_unlabelled_checkpoint")
            continue
        position = int(label.removesuffix("M"))
        if position in checkpoints or not 0 < position < distance:
            raise ValueError("invalid_checkpoint_position")
        checkpoints[position] = text
    spans = [
        ("initial_200", 0, 200),
        ("10f_8f", distance - 2000, distance - 1600),
        ("8f_6f", distance - 1600, distance - 1200),
        ("6f_4f", distance - 1200, distance - 800),
        ("4f_2f", distance - 800, distance - 400),
        ("final_400", distance - 400, distance),
        ("final_600", distance - 600, distance),
        ("final_200", distance - 200, distance),
    ]
    # The official guide defines this generic column as the initial 100m at 1300m.
    if distance == 1300:
        spans[2] = ("8f_6f_initial_100", 0, 100)
    return [
        (
            name,
            start,
            end,
            checkpoints.get(start, ""),
            checkpoints.get(end, ""),
            segments[i],
        )
        for i, (name, start, end) in enumerate(spans)
    ]


def evaluate(kind, distance, values):
    checks = []
    for name, start, end, a, b, printed in relations(kind, distance, values):
        valid_positions = 0 <= start < end <= distance
        if not valid_positions:
            result = {
                "status": (
                    "unsupported_endpoint_with_value"
                    if printed != ""
                    else "unsupported_endpoint"
                ),
                "residual_seconds": None,
            }
        else:
            result = check_relation(
                seconds(a), seconds(b), seconds(printed), origin=start == 0
            )
        checks.append(
            {
                "relation": name,
                "start_m": start,
                "end_m": end,
                "raw_start": a,
                "raw_end": b,
                "raw_printed_segment": printed,
                **result,
            }
        )
    return checks


def audit(root=source.ROOT, guide_root=GUIDE_ROOT):
    root = Path(root)
    guide = replay_guide(guide_root)
    # Replay the API/HTML identity and numerical mapping before deriving anything.
    baseline = source.audit(root)
    if baseline["exceptions"]:
        raise ValueError("unresolved_source_cell_conflicts")
    seed = replay_frozen(root, root / "seed.json", source.SEED_SHA, cutoff=source.BOUND)
    evidence = replay_archive(
        root / "official", source.HTML_SHA, seed, source.SEED_SHA, source.BOUND
    )
    members = defaultdict(list)
    for row in seed["records"]:
        members[row["race_id"]].append(row)
    counts, eligibility, groups = Counter(), Counter(), {}
    by_relation, by_eligibility = defaultdict(Counter), defaultdict(Counter)
    observations, exceptions = [], []
    for race_id, records in sorted(members.items()):
        unit = evidence[race_id]
        comparison = reconcile_group(records, unit["parsed"])
        if comparison["roster_support"] != "exact":
            raise ValueError("arithmetic_roster_not_exact")
        conflict = any(
            r["rank_support"] == "conflict" or r["time_support"] == "conflict"
            for r in comparison["rows"]
        )
        support = {
            (r["chul_no"], r["horse_id"]): (
                "whole_race_conflict"
                if conflict
                else "supported"
                if r["ranked_feature_supported"]
                else "unsupported_start"
            )
            for r in comparison["rows"]
        }
        receipt = unit["capture"]
        html = (
            pinned_path(root / "official", receipt["raw"])
            .read_bytes()
            .decode(receipt["encoding"], errors="strict")
        )
        condition = parse_conditions(html, race_id)
        if condition["status"] != "observed":
            raise ValueError("arithmetic_condition_not_observed")
        distance = condition["distance_m"]
        meet = race_id.split("_")[1]
        kind = {"1": "seoul", "2": "jeju", "3": "busan"}[meet]
        kinds = ["busan_segment", "busan_cumulative"] if kind == "busan" else [kind]
        roster = {r["chul_no"]: r for r in unit["parsed"]["rows"]}
        timing = [t for t in tables(html) if t.caption.strip().startswith(TIME_CAPTION)]
        parsed = {
            k: source.timing_rows(t, k, distance, roster)
            for k, t in zip(kinds, timing, strict=True)
        }
        group = groups.setdefault(
            f"{meet}:{distance}",
            {"rows": 0, "races": 0, "eligibility": Counter(), "checks": Counter()},
        )
        group["races"] += 1
        for gate, row in sorted(roster.items()):
            state = support[(gate, row["horse_id"])]
            checks = evaluate(kind, distance, {k: parsed[k][gate] for k in kinds})
            tally = Counter(r["status"] for r in checks)
            eligibility[state] += 1
            counts.update(tally)
            by_eligibility[state].update(tally)
            for check in checks:
                by_relation[f"{kind}:{check['relation']}"][check["status"]] += 1
            group["rows"] += 1
            group["eligibility"][state] += 1
            group["checks"].update(tally)
            identity = {
                "race_id": race_id,
                "chul_no": gate,
                "horse_id": row["horse_id"],
                "history_eligibility": state,
            }
            observations.append(
                {
                    **identity,
                    "check_counts": dict(tally),
                    "arithmetic_scope": (
                        "labelled_endpoint_checks"
                        if checks
                        else "no_independent_cumulative_counterpart"
                    ),
                }
            )
            for check in checks:
                if check["status"] not in (
                    "exact",
                    "missing_value",
                    "unsupported_endpoint",
                ):
                    exceptions.append({**identity, **check})
    if len(observations) != baseline["rows"] or len(members) != baseline["races"]:
        raise ValueError("incomplete_arithmetic_population")
    return {
        "format_version": "sectional-arithmetic-audit-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "implementation_sha256": digest(Path(__file__).read_bytes()),
        "source_mapper_sha256": digest(Path(source.__file__).read_bytes()),
        "sectional_definition_source": guide,
        "seed_sha256": source.SEED_SHA,
        "official_archive_sha256": source.HTML_SHA,
        "source_local_clock_bound": source.BOUND,
        "races": len(members),
        "rows": len(observations),
        "eligibility": dict(eligibility),
        "checks": dict(counts),
        "by_relation": dict(by_relation),
        "checks_by_history_eligibility": dict(by_eligibility),
        "by_venue_distance": groups,
        "observations": observations,
        "exceptions": exceptions,
        "official_sources": baseline["official_sources"],
        "seed_status_counts": seed["status_counts"],
        "target_outcomes_loaded": False,
        "training_approved": False,
        "existing_exclusions_changed": False,
        "historical_prerace_verified": False,
        "fits": 0,
        "network_requests": 0,
        "accuracy": None,
        "counts_as_70_percent_evidence": False,
    }


if __name__ == "__main__":
    print(encoded(audit()).decode(), end="")
