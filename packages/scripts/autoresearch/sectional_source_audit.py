"""Compare preserved API time values to labelled original official HTML columns."""

import re
from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from shared.official_result_support import TIME_CAPTION, integer, tables

from autoresearch.frozen_history_view import replay_frozen
from autoresearch.history_time_audit import join_rows
from autoresearch.kra_result_snapshot import replay_result_pages
from autoresearch.observed_history_seed import digest, pinned_path
from autoresearch.official_history_support import replay_archive
from autoresearch.race_conditions import parse_conditions
from autoresearch.restricted_cohort import encoded

ROOT = Path(".cache/autoresearch/observed-history-extension-20260501-14")
SEED_SHA = "561bcfdc6fe2c4733e571b8c77034a2753e88794d5d7d3a6ee5d2ee2f25a5407"
HTML_SHA = "8ca56ba232156beb824e9baab1f4c8c5b301e8d619f81e17d1213e8f6512e1bd"
BOUND = "2026-10-16T01:20:00Z"
FIELDS = {
    "seoul": (
        "seS1fAccTime",
        "se_1cAccTime",
        "se_2cAccTime",
        "se_3cAccTime",
        "seG3fAccTime",
        "se_4cAccTime",
        "seG1fAccTime",
        None,
        None,
        "rcTime",
    ),
    "jeju": (
        "jeS1fTime",
        "je_1cTime",
        "je_2cTime",
        "je_3cTime",
        "je_4cTime",
        "jeG3fTime",
        "jeG1fTime",
        "rcTime",
    ),
    "busan_segment": (
        "buS1fTime",
        "bu_10_8fTime",
        "bu_8_6fTime",
        "bu_6_4fTime",
        "bu_4_2fTime",
        "bu_2fGTime",
        "bu_3fGTime",
        "bu_1fGTime",
        "rcTime",
    ),
    "busan_cumulative": (
        "buS1fAccTime",
        "buG8fAccTime",
        "buG6fAccTime",
        "buG4fAccTime",
        "buG3fAccTime",
        "buG2fAccTime",
        "buG1fAccTime",
        "rcTime",
    ),
}
# Observed HTML layouts, not a general distance-applicability rule.
BUSAN_LAYOUTS = {
    1200: ("- - 200M 400M 600M 800M 1000M", ("G8f", "G6f", "S1f")),
    1300: ("- 100M 200M 500M 700M 900M 1100M", ("G8f", "G6f", "S1f")),
    1400: ("- - 200M 600M 800M 1000M 1200M", ("G8f", "G6f", "S1f")),
    1600: ("- 200M 400M 800M 1000M 1200M 1400M", ("G8f", "S1f", "G6f")),
    1800: ("- 200M 600M 1000M 1200M 1400M 1600M", ("G8f", "S1f", "G6f")),
    2200: ("200M 600M 1000M 1400M 1600M 1800M 2000M", ("S1f", "G8f", "G6f")),
}


def fields(kind, distance):
    if kind == "busan_cumulative":
        if distance not in BUSAN_LAYOUTS:
            raise ValueError("unobserved_busan_distance")
        return (
            tuple(f"bu{part}AccTime" for part in BUSAN_LAYOUTS[distance][1])
            + FIELDS[kind][3:]
        )
    return FIELDS[kind]


def headers(kind, distance):
    cumulative = f"통과 누적기록(경주거리 : {distance}M)"
    if kind == "seoul":
        return [
            ["순위", "마번", "구간별 통과순위", cumulative, "펄롱타임", "경주 기록"],
            [
                "S1F-1C-2C-3C-G3F-4C-G1F",
                "S1F 지점",
                "1코너 지점",
                "2코너 지점",
                "3코너 지점",
                "G3F 지점",
                "4코너 지점",
                "G1F 지점",
                "3F-G",
                "1F-G",
            ],
        ]
    if kind == "jeju":
        return [
            [
                "순위",
                "마번",
                "S1F-1C-2C-3C-4C-G1F",
                "S-1F",
                "1코너",
                "2코너",
                "3코너",
                "4코너",
                "G-3F",
                "G-1F",
                "경주기록",
            ]
        ]
    if kind == "busan_segment":
        return [
            [
                "순위",
                "마번",
                "구간별 통과순위(구간기록의 이해/활용) S1F-G8F-G6F-G4F-G3F-G2F-G1F",
                "S-1F",
                "10-8F",
                "8-6F",
                "6-4F",
                "4-2F",
                "2F-G",
                "3F-G",
                "1F-G",
                "경주 기록",
            ]
        ]
    if kind == "busan_cumulative":
        fields(kind, distance)
        return [
            [
                "순위",
                "마번",
                "구간별 통과순위 S1F-G8F-G6F-G4F-G3F-G2F-G1F",
                cumulative,
                "경주 기록",
            ],
            BUSAN_LAYOUTS[distance][0].split(),
        ]
    raise ValueError("unsupported_timing_kind")


def timing_rows(table, kind, distance, roster):
    if not table.closed or table.invalid:
        raise ValueError("malformed_sectional_table")
    header_rows = [
        [c.text for c in row]
        for row in table.rows
        if row and all(c.tag == "th" for c in row)
    ]
    if header_rows != headers(kind, distance):
        raise ValueError("unknown_sectional_headers")
    result = {}
    for row in table.rows:
        if row and all(c.tag == "th" for c in row):
            continue
        if len(row) != 3 + len(fields(kind, distance)) or any(
            c.tag != "td" or c.span for c in row
        ):
            raise ValueError("malformed_sectional_row")
        gate = integer(row[1].text)
        if gate in result or gate not in roster:
            raise ValueError("sectional_gate_mismatch")
        if row[0].text != roster[gate]["rank_text"]:
            raise ValueError("sectional_rank_mismatch")
        result[gate] = [c.text for c in row[3:]]
    if set(result) != set(roster):
        raise ValueError("sectional_missing_gate")
    return result


def compare(api, text):
    if isinstance(api, bool) or type(api) not in (str, int, float):
        return "invalid_api_value"
    try:
        value = Decimal(str(api))
    except ArithmeticError:
        return "invalid_api_value"
    if not value.is_finite() or value < 0:
        return "invalid_api_value"
    if text == "":
        return "zero_blank" if value == 0 else "nonzero_blank_conflict"
    match = re.fullmatch(r"([0-9]+):([0-5][0-9](?:\.[0-9]+)?)", text)
    if not match:
        return "unparsed_html"
    seconds = Decimal(match[1]) * 60 + Decimal(match[2])
    if value != seconds:
        return "numeric_conflict"
    return "positive_equal" if value > 0 else "zero_numeric_equal"


def audit(root=ROOT):
    root = Path(root)
    seed = replay_frozen(root, root / "seed.json", SEED_SHA, cutoff=BOUND)
    evidence = replay_archive(root / "official", HTML_SHA, seed, SEED_SHA, BOUND)
    by_capture, raw_by_race = defaultdict(list), defaultdict(dict)
    for row in seed["records"]:
        by_capture[row["source_capture_sha256"]].append(row)
    for unit in seed["inventory"]:
        if unit["status"] != "api_reported_rows":
            continue
        replay = replay_result_pages(pinned_path(root, unit["result"]))
        if replay["capture_manifest_sha256"] != unit["result"]["sha256"]:
            raise ValueError("sectional_capture_changed")
        for row in join_rows(
            replay["rows"],
            by_capture[unit["result"]["sha256"]],
            unit["day"],
            unit["meet"],
        ):
            race_id, gate, horse = row["identity"]
            if gate in raw_by_race[race_id]:
                raise ValueError("sectional_duplicate_api_gate")
            raw_by_race[race_id][gate] = (horse, row["raw"])
    if sum(len(rows) for rows in raw_by_race.values()) != len(seed["records"]):
        raise ValueError("sectional_incomplete_api_join")
    counts, groups, exceptions, sources = Counter(), {}, [], []
    for race_id, api_rows in sorted(raw_by_race.items()):
        unit = evidence[race_id]
        parsed, receipt = unit["parsed"], unit["capture"]
        if parsed["event_support"] != "confirmed" or parsed["race_id"] != race_id:
            raise ValueError("sectional_event_mismatch")
        roster = {r["chul_no"]: r for r in parsed["rows"]}
        if {g: r["horse_id"] for g, r in roster.items()} != {
            g: horse for g, (horse, _) in api_rows.items()
        }:
            raise ValueError("sectional_horse_roster_mismatch")
        distances = {int(raw["rcDist"]) for _, raw in api_rows.values()}
        if len(distances) != 1:
            raise ValueError("sectional_distance_conflict")
        distance = distances.pop()
        meet = race_id.split("_")[1]
        kinds = {
            "1": ["seoul"],
            "2": ["jeju"],
            "3": ["busan_segment", "busan_cumulative"],
        }[meet]
        content = pinned_path(root / "official", receipt["raw"]).read_bytes()
        html = content.decode(receipt["encoding"], errors="strict")
        conditions = parse_conditions(html, race_id)
        if conditions["status"] != "observed" or conditions["distance_m"] != distance:
            raise ValueError("sectional_official_distance_mismatch")
        timings = [
            t for t in tables(html) if t.caption.strip().startswith(TIME_CAPTION)
        ]
        if len(timings) != len(kinds):
            raise ValueError("sectional_table_count_mismatch")
        group = groups.setdefault(
            f"{meet}:{distance}",
            {
                "races": 0,
                "rows": 0,
                "fields": {},
                "layouts": {
                    kind: {
                        "headers": headers(kind, distance),
                        "time_columns": fields(kind, distance),
                    }
                    for kind in kinds
                },
            },
        )
        group["races"] += 1
        group["rows"] += len(roster)
        for kind, table in zip(kinds, timings, strict=True):
            rows = timing_rows(table, kind, distance, roster)
            for gate, values in rows.items():
                horse, raw = api_rows[gate]
                for field, text in zip(fields(kind, distance), values, strict=True):
                    if field is None:
                        continue
                    status = compare(raw.get(field), text)
                    counts[status] += 1
                    key = f"{kind}:{field}"
                    tally = group["fields"].setdefault(key, Counter())
                    tally[status] += 1
                    if status not in ("positive_equal", "zero_blank"):
                        exceptions.append(
                            {
                                "race_id": race_id,
                                "chul_no": gate,
                                "horse_id": horse,
                                "table": kind,
                                "field": field,
                                "api": raw.get(field),
                                "html": text,
                                "status": status,
                            }
                        )
        sources.append(
            {
                "race_id": race_id,
                "receipt": unit["receipt"],
                "raw": receipt["raw"],
                "url": receipt["request"]["url"],
                "available_at": receipt["completed_at"],
            }
        )
    return {
        "format_version": "sectional-source-reconciliation-v1",
        "created_at": datetime.now(UTC).isoformat(),
        "implementation_sha256": digest(Path(__file__).read_bytes()),
        "seed_sha256": SEED_SHA,
        "official_archive_sha256": HTML_SHA,
        "source_local_clock_bound": BOUND,
        "races": len(raw_by_race),
        "rows": len(seed["records"]),
        "counts": dict(counts),
        "by_venue_distance": groups,
        "exceptions": exceptions,
        "official_sources": sources,
        "seed_status_counts": seed["status_counts"],
        "interpretation": "empirical_labelled_cell_agreement_not_feature_approval",
        "zero_meaning_verified": False,
        "historical_prerace_verified": False,
        "training_approved": False,
        "existing_exclusions_changed": False,
        "target_outcomes_loaded": False,
        "fits": 0,
        "network_requests": 0,
        "accuracy": None,
        "counts_as_70_percent_evidence": False,
    }


if __name__ == "__main__":
    print(encoded(audit()).decode(), end="")
