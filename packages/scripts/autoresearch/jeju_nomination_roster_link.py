"""Compare one Jeju weekly roster with its ID-bearing web nomination detail."""

from collections import Counter, defaultdict

from shared.kra_race_card_pdf import normalize_horse_name
from shared.kra_race_identity import validate_race_identity

from autoresearch.restricted_cohort import horse_id

CONTEXT = ("race_date", "meet", "race_no", "grade", "distance_m", "weight_type")
DEMOGRAPHICS = ("sex", "age", "trainer", "owner")


def _context(source):
    day, venue, race_no, grade, distance, rule = (source[key] for key in CONTEXT)
    validate_race_identity(venue, day, race_no)
    if (
        venue != 2
        or type(distance) is not int
        or distance <= 0
        or not all(isinstance(x, str) and x.strip() for x in (grade, rule))
    ):
        raise ValueError("invalid_jeju_nomination_context")
    return day, venue, race_no, grade, distance, rule


def _name(value):
    if value is not None and not isinstance(value, str):
        raise ValueError("invalid_nomination_text")
    return normalize_horse_name(value or "") or None


def _number(value, minimum):
    if value is not None and (type(value) is not int or value < minimum):
        raise ValueError("invalid_nomination_number")
    return value


def _group(rows, *, position, is_web):
    groups = defaultdict(list)
    positions, identifiers = set(), set()
    for row in rows:
        name, order = _name(row["name"]), _number(row[position], 1)
        stable = horse_id(row["profile_id"]) if is_web else None
        if not name or order is None or order in positions or stable in identifiers:
            raise ValueError("duplicate_or_unidentified_nomination_row")
        positions.add(order)
        if is_web:
            identifiers.add(stable)
        groups[name].append(
            {
                "position": order,
                "profile_id": stable,
                "sex": _name(row["sex"]),
                "age": _number(row["age"], 1),
                "trainer": _name(row["trainer"]),
                "owner": _name(row["owner"]),
                "rating": _number(row["rating"], 0),
            }
        )
    if not positions:
        raise ValueError("empty_nomination_source_unconfirmed")
    return groups


def _state(left, right):
    if left is None or right is None:
        return "missing"
    return "match" if left == right else "conflict"


def audit_rosters(weekly, web):
    """Return all name groups and comparisons, never final starter or feature links.

    Both source objects must already be parsed from their original receipt-bound
    bytes. They supply the literal race context and a 'rows' list. The two source
    positions are not keys. A stable ID exists only on the web-detail side.
    """
    context = _context(weekly)
    if _context(web) != context:
        raise ValueError("nomination_race_context_mismatch")
    report = _group(
        weekly["rows"], position="registration_number_not_gate", is_web=False
    )
    detail = _group(web["rows"], position="nomination_position_not_gate", is_web=True)
    groups, report_counts, web_counts = [], Counter(), Counter()
    for name in sorted(report.keys() | detail.keys()):
        left, right = report.get(name, []), detail.get(name, [])
        checks, same_position = {}, None
        if not left:
            state = "web_only"
        elif not right:
            state = "weekly_only"
        elif len(left) != 1 or len(right) != 1:
            state = "ambiguous_name"
        else:
            checks = {
                field: _state(left[0][field], right[0][field])
                for field in (*DEMOGRAPHICS, "rating")
            }
            identity = {checks[key] for key in DEMOGRAPHICS}
            state = (
                "identity_disagreement"
                if "conflict" in identity
                else "identity_fields_missing"
                if "missing" in identity
                else "corroborated_nomination_only"
            )
            same_position = left[0]["position"] == right[0]["position"]
        report_counts[state] += len(left)
        web_counts[state] += len(right)
        groups.append(
            {
                "name": name,
                "state": state,
                "weekly_registration_numbers_not_gates": [r["position"] for r in left],
                "detail_positions_not_gates": [r["position"] for r in right],
                "detail_only_profile_ids": [r["profile_id"] for r in right],
                "checks": checks,
                "numeric_positions_equal_diagnostic_only": same_position,
            }
        )
    day, venue, race_no, *_ = context
    return {
        "race_id": f"{day}_{venue}_{race_no}",
        "groups": groups,
        "weekly_rows_by_state": dict(report_counts),
        "web_rows_by_state": dict(web_counts),
        "direct_id_matches_in_both_sources": 0,
        "establishes_final_declaration_or_gate": False,
        "allows_training_or_predictions": False,
    }
