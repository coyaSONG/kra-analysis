import pytest

from autoresearch.nomination_prior_coverage import OVERLAY, REFERENCE, report

FIELD = "20261128_2_5"
WITHOUT_DETAIL = "20261128_2_6"
ANCHOR = "2026-11-22T18:28:05Z"
KNOWN = "2026-11-22T15:11:40Z"
SCOPES = {
    FIELD: {"meet": 2, "grade": "OPEN", "distance_m": 1610, "horse_ids": ["1", "2"]}
}


def row(rid, hid="1", **change):
    return {
        "race_id": rid,
        "horse_id": hid,
        "observed_at": "2026-11-22T09:00:00Z",
        "numeric_prior": True,
        "grade": "OPEN",
        "distance_m": 1610,
    } | change


def source(rows, kind=REFERENCE, when=KNOWN):
    return {"kind": kind, "rows": rows, "public_existence_by": when}


def run(reference, extra, scopes=SCOPES, seen=(FIELD, WITHOUT_DETAIL)):
    return report(
        seen,
        scopes,
        {"a": source(reference), "b": source(extra, OVERLAY)},
        source_anchor=ANCHOR,
    )


def test_unknown_detail_is_never_counted_as_zero_coverage():
    got = run([row("20261003_2_1")], [row("20261121_2_7", "2")])
    assert set(got["fields"]) == {FIELD, WITHOUT_DETAIL}
    assert got["fields"][WITHOUT_DETAIL]["known_nomination_rows"] is None
    assert got["fields"][WITHOUT_DETAIL]["slots"] is None
    totals = got["observed_slot_totals"]
    assert totals["known_nomination_rows"] == 2
    assert totals["reference_exact_venue_grade_distance"] == 1
    assert totals["with_overlay_exact_venue_grade_distance"] == 2
    assert got["training_or_evaluation_admitted"] is False


def test_keep_venue_literal_grade_200m_and_distinct_days():
    got = run(
        [
            row("20260830_2_1", distance_m=1410),
            row("20260829_2_2"),
            row("20261002_2_2"),
            row("20261002_2_3"),
            row("20261001_3_3", "2"),
            row("20261001_2_3", "2", grade="OPEN OTHER"),
            row("20261001_2_4", "2", distance_m=1409),
        ],
        [row("20261121_2_5", numeric_prior=False), row("20261120_2_5", "2")],
    )["fields"][FIELD]["slots"]
    assert got["1"]["reference"] == {
        "any_numeric_prior": True,
        "similar_venue_grade_distance": True,
        "exact_venue_grade_distance": True,
        "two_exact_prior_days": False,
    }
    assert not got["1"]["if_unreconciled_overlay_were_eligible"]["two_exact_prior_days"]
    assert "20260829_2_2" not in got["1"]["observed_prior_race_ids_by_source"]["a"]
    assert not got["2"]["reference"]["similar_venue_grade_distance"]
    assert got["2"]["if_unreconciled_overlay_were_eligible"][
        "exact_venue_grade_distance"
    ]


def test_late_archive_and_receipt_fail_closed():
    with pytest.raises(ValueError, match="before_coverage_anchor"):
        report((FIELD,), SCOPES, {"a": source([], when=ANCHOR)}, source_anchor=ANCHOR)
    with pytest.raises(ValueError, match="record_or_clock"):
        run([row("20261003_2_1", observed_at=ANCHOR)], [])
    with pytest.raises(ValueError, match="record_or_clock"):
        run([row("20261128_2_3")], [])


def test_no_duplicate_archive_or_canonical_identity():
    with pytest.raises(ValueError, match="overlapping_or_duplicate"):
        run([row("20261003_2_1")], [row("20261003_2_1", "2")])
    with pytest.raises(ValueError, match="identity_or_context"):
        run([], [], {FIELD: SCOPES[FIELD] | {"horse_ids": ["1", "001"]}})
    with pytest.raises(ValueError, match="census_key"):
        run([], [], seen=(FIELD, FIELD))
