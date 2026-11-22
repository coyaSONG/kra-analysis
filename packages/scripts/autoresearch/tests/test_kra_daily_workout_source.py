from datetime import date, datetime
from html import escape

import pytest

from autoresearch import kra_daily_workout_source as source

DAY = date(2026, 11, 18)
OBSERVED = datetime.fromisoformat("2026-11-18T09:00:00+00:00")
DATE = "2026/11/18"
WED = "\uc218"
GROUP = "\uc870"
HEADS = "\ub450"
MIN = "\ubd84"
TIMES = "\ud68c"


def _form(lane, action, body, **special):
    fields = {"meet": str(lane), "Act": "10", "Sub": "3"} | special
    hiddens = "".join(
        f'<input type="hidden" name="{name}" value="{value}">'
        for name, value in fields.items()
    )
    return f'<form name="form1" method="post" action="{escape(action)}">{hiddens}{body}</form>'


def _row(*values):
    return "<tr>" + "".join(f"<td>{v}</td>" for v in values) + "</tr>"


def _table(caption, columns, rows):
    header = "<tr>" + "".join(f"<th>{c}</th>" for c in columns) + "</tr>"
    return f"<table><caption>{caption}</caption>{header}{rows}</table>"


def _index(lane, count):
    return _form(
        lane,
        source.index_path(lane),
        _table(
            source.INDEX_CAPTION,
            (source.ORDER, source.DATE_LABEL, source.COUNT_LABEL),
            _row(1, f"{DATE}({WED})", f"{count}{HEADS}"),
        ),
    )


def _groups(lane, count):
    return _form(
        lane,
        source.GROUPS,
        _table(
            source.GROUP_CAPTION,
            (source.TRAINER_LABEL, source.COUNT_LABEL) * 2,
            _row(f"2{GROUP}(Trainer)", f"{count}{HEADS}", "", ""),
        ),
        trDate=DATE,
        trDateReplace="20261118",
    )


def _session(lane, order, horse, *, minutes="9", start="06:55", end="07:04"):
    prefix = (
        order,
        f"2{GROUP}",
        order,
        f"<a href=\"javascript:goPage4('{horse}')\">R</a>",
    )
    times = ("Rider", "", start, end, f"{minutes}{MIN}")
    if lane == 2:
        return _row(*prefix, *times)
    return _row(*prefix, "Grade", *times, "", f"2{TIMES}", f"0{TIMES}")


def _detail(lane, *rows, profile=source.PROFILE_ACTION):
    day = f"<table><caption>{source.DATE_CAPTION}</caption><tr><th>{source.DATE_LABEL}</th><td>{DATE}(??)</td></tr></table>"
    detail = _table(
        source.DETAIL_CAPTION,
        source.JEJU_DETAIL_COLUMNS if lane == 2 else source.DETAIL_COLUMNS,
        "".join(rows),
    )
    return _form(
        lane,
        source.DETAIL,
        f"<script>{profile}</script>" + day + detail,
        trDate=DATE,
        hrNo="",
        trYo="??",
    )


def _read(lane, detail, count=1, clock=OBSERVED):
    return source.read_scoped_workouts(
        detail,
        DAY,
        clock,
        lane=lane,
        expected_count=count,
        expected_groups={2: count},
    )


@pytest.mark.parametrize("lane", [2, 3])
def test_uses_verified_forms_and_counts_for_each_lane(lane):
    assert source.index_path(lane).endswith(f"?Act=10&Sub=3&meet={lane}")
    count = source.index_count(_index(lane, 1), DAY, lane=lane)
    groups = source.group_counts(_groups(lane, 1), DAY, lane=lane)
    week, records = source.read_scoped_workouts(
        _detail(lane, _session(lane, 1, "0000123")),
        DAY,
        OBSERVED,
        lane=lane,
        expected_count=count,
        expected_groups=groups,
    )
    (row,) = records
    assert week == "??" and row.workout.horse_id == "123"
    assert row.workout.distance_literal is None
    assert row.workout.gait_counts == ((None, None) if lane == 2 else (2, 0))
    assert row.usable_minutes == 9


def test_regional_clock_disagreement_keeps_reported_values_and_ids_without_imputing():
    _, rows = _read(
        3,
        _detail(3, _session(3, 1, "123", minutes="8"), _session(3, 2, "124")),
        count=2,
    )
    held, accepted = rows
    assert held.workout.horse_id == "123" and held.workout.minutes == 8
    assert held.clock_issue == "workout_duration_does_not_match_clocks"
    assert held.usable_minutes is None
    assert accepted.usable_minutes == 9


def test_regional_same_day_clock_after_observation_does_not_yield_minutes():
    _, (held,) = _read(
        2,
        _detail(2, _session(2, 1, "123")),
        clock=datetime.fromisoformat("2026-11-18T07:03:00+09:00"),
    )
    assert held.clock_issue == "workout_after_observation"
    assert held.usable_minutes is None


def test_youngnam_menu_is_not_a_fourth_physical_track_route():
    with pytest.raises(ValueError, match="unregistered_workout_menu_lane"):
        source.index_path(4)
    with pytest.raises(ValueError, match="unverified_regional_workout_scope"):
        _read(2, _detail(3, _session(3, 1, "123")))


def test_rejects_scope_substitution_without_using_its_counts():
    with pytest.raises(ValueError, match="unverified_regional_workout_scope"):
        source.index_count(_index(3, 5), DAY, lane=2)
    with pytest.raises(ValueError, match="unverified_regional_workout_scope"):
        source.group_counts(_groups(2, 1), DAY, lane=3)


def test_jeju_column_shape_cannot_be_padded_to_match_other_lanes():
    with pytest.raises(ValueError, match="workout_row_shape_changed"):
        _read(2, _detail(2, _session(3, 1, "123")))
    with pytest.raises(ValueError, match="workout_heading_changed"):
        body = _detail(2, _session(2, 1, "123")).replace(
            "<th>" + source.JEJU_DETAIL_COLUMNS[-1] + "</th>", "<th>Other</th>"
        )
        _read(2, body)


def test_missing_dated_row_and_invalid_record_do_not_become_zero():
    with pytest.raises(ValueError, match="workout_detail_does_not_match_scope_counts"):
        _read(3, _detail(3, _session(3, 1, "123")), count=2)
    with pytest.raises(ValueError, match="invalid_workout_wall_clock"):
        _read(2, _detail(2, _session(2, 1, "123", start="26:40")))


def test_official_profile_control_and_distinct_ids_are_required():
    with pytest.raises(ValueError, match="unverified_workout_profile_links"):
        _read(2, _detail(2, _session(2, 1, "123"), profile=""))
    with pytest.raises(ValueError, match="duplicate_workout_horse_or_stall"):
        _read(3, _detail(3, _session(3, 1, "123"), _session(3, 2, "0000123")), count=2)
