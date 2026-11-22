"""Measure prior-source coverage on a preserved preliminary nomination census."""

from collections import Counter, defaultdict
from datetime import date
from zoneinfo import ZoneInfo

from shared.kra_race_identity import validate_race_identity

from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import horse_id

KST = ZoneInfo("Asia/Seoul")
REFERENCE = "reference"
OVERLAY = "unreconciled_overlay"
SCOPE_DAY_WINDOW = 90
DISTANCE_BAND = 200


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def race_parts(race_id):
    day, meet, number = race_id.split("_")
    venue, race = int(meet), int(number)
    validate_race_identity(venue, day, race)
    require(race_id == f"{day}_{venue}_{race}", "noncanonical_coverage_race")
    return date.fromisoformat(day), venue


def flags(records, scope):
    numeric = [r for r in records if r["numeric_prior"] is True]
    nearby = [
        r
        for r in numeric
        if r["venue"] == scope["meet"]
        and r["grade"] == scope["grade"]
        and type(r["distance_m"]) is int
        and abs(r["distance_m"] - scope["distance_m"]) <= DISTANCE_BAND
    ]
    exact = [r for r in nearby if r["distance_m"] == scope["distance_m"]]
    return {
        "any_numeric_prior": bool(numeric),
        "similar_venue_grade_distance": bool(nearby),
        "exact_venue_grade_distance": bool(exact),
        "two_exact_prior_days": len({r["race_id"][:8] for r in exact}) >= 2,
    }


def index_sources(archives, boundary):
    """Keep receipt time, independently witnessed time, and event day separate."""
    by_horse, owners, summary, seen = defaultdict(list), {}, {}, set()
    for label, archive in archives.items():
        kind = archive["kind"]
        known_at = timestamp(archive["public_existence_by"])
        require(
            kind in (REFERENCE, OVERLAY) and known_at < boundary,
            "archive_not_witnessed_before_coverage_anchor",
        )
        rows, events = archive["rows"], set()
        for row in rows:
            rid, hid = row["race_id"], horse_id(row["horse_id"])
            day, venue = race_parts(rid)
            observed = timestamp(row["observed_at"])
            distance, grade = row["distance_m"], row["grade"]
            require(
                owners.setdefault(rid, label) == label and (rid, hid) not in seen,
                "overlapping_or_duplicate_archived_prior_record",
            )
            require(
                type(row["numeric_prior"]) is bool
                and (grade is None or isinstance(grade, str) and bool(grade.strip()))
                and (distance is None or type(distance) is int and distance > 0)
                and day <= observed.astimezone(KST).date()
                and observed <= known_at,
                "invalid_prior_record_or_clock",
            )
            seen.add((rid, hid))
            events.add(rid)
            by_horse[hid].append({**row, "venue": venue, "day": day, "source": label})
        summary[label] = {
            "kind": kind,
            "public_existence_by": archive["public_existence_by"],
            "row_count": len(rows),
            "represented_races": len(events),
        }
    return by_horse, summary


def report(observed_fields, linked_fields, archives, *, source_anchor):
    """Retain every seen key; only dated, identified nomination rows get diagnostics.

    Sources already have bound receipt and publication evidence at this boundary.
    A reference may be single-source: this comparison does not admit features,
    certify a result label, or select an evaluation population.
    """
    boundary = timestamp(source_anchor)
    require(
        len(set(observed_fields)) == len(observed_fields)
        and linked_fields.keys() <= set(observed_fields),
        "nomination_census_key_changed",
    )
    by_horse, source_summary = index_sources(archives, boundary)
    fields, total = {}, Counter()
    for key in sorted(observed_fields):
        day, meet = race_parts(key)
        require(boundary.astimezone(KST).date() < day, "nomination_anchor_on_race_day")
        if key not in linked_fields:
            fields[key] = {
                "state": "profile_detail_unobserved",
                "known_nomination_rows": None,
                "slots": None,
            }
            continue
        scope = linked_fields[key]
        ids = {horse_id(h) for h in scope["horse_ids"]}
        require(
            len(ids) == len(scope["horse_ids"])
            and bool(ids)
            and scope["meet"] == meet
            and isinstance(scope["grade"], str)
            and bool(scope["grade"].strip())
            and type(scope["distance_m"]) is int
            and scope["distance_m"] > 0,
            "nomination_identity_or_context_changed",
        )
        slots = {}
        counts = Counter()
        for hid in sorted(ids, key=int):
            past = [
                row
                for row in by_horse.get(hid, ())
                if 0 < (day - row["day"]).days <= SCOPE_DAY_WINDOW
            ]
            baseline = [r for r in past if archives[r["source"]]["kind"] == REFERENCE]
            reference, with_overlay = flags(baseline, scope), flags(past, scope)
            proofs = defaultdict(list)
            for row in sorted(past, key=lambda r: (r["source"], r["race_id"])):
                proofs[row["source"]].append(row["race_id"])
            slots[hid] = {
                "reference": reference,
                "if_unreconciled_overlay_were_eligible": with_overlay,
                "observed_prior_race_ids_by_source": dict(proofs),
            }
            for name in reference:
                counts[f"reference_{name}"] += reference[name]
                counts[f"with_overlay_{name}"] += with_overlay[name]
        counts["known_nomination_rows"] = len(ids)
        total.update(counts)
        fields[key] = {
            "state": "preliminary_profile_ids_only",
            "context": {key: scope[key] for key in ("meet", "grade", "distance_m")},
            "known_nomination_rows": len(ids),
            "counts": dict(counts),
            "slots": slots,
        }
    return {
        "fields": fields,
        "source_summary": source_summary,
        "race_keys_seen": len(observed_fields),
        "races_with_identity_detail": len(linked_fields),
        "races_without_identity_detail": len(observed_fields) - len(linked_fields),
        "observed_slot_totals": dict(total),
        "final_population_or_cutoff_known": False,
        "training_or_evaluation_admitted": False,
    }
