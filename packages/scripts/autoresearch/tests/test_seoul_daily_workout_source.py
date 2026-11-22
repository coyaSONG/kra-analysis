from datetime import date, datetime
from html import escape

import pytest

from autoresearch import seoul_daily_workout_source as source

DAY = date(2026, 11, 18)
OBSERVED = datetime.fromisoformat("2026-11-18T09:00:00+00:00")
DATE = "2026/11/18"
WED = "\uc218"
GROUP_SUFFIX = "\uc870"
HEADS = "\ub450"
MIN = "\ubd84"
COUNT = "\ud68c"


def _form(path, body, **additional):
    fields = {"meet": "1", "Act": "09", "Sub": "3"} | additional
    inputs = "".join(
        f'<input type="hidden" name="{name}" value="{value}">'
        for name, value in fields.items()
    )
    return f'<form name="form1" method="post" action="{escape(path)}">{inputs}{body}</form>'


def _row(*payload):
    return "<tr>" + "".join(f"<td>{x}</td>" for x in payload) + "</tr>"


def _table(caption, headings, payload):
    cols = "".join(f"<th>{name}</th>" for name in headings)
    return f"<table><caption>{caption}</caption><tr>{cols}</tr>{payload}</table>"


def _index(text=f"{DATE}({WED})"):
    return _form(
        source.INDEX,
        _table(
            source.INDEX_CAPTION,
            (source.ORDER, source.DATE_LABEL, source.COUNT_LABEL),
            _row(1, text, f"2{HEADS}"),
        ),
    )


def _group(rows=None):
    if rows is None:
        rows = _row(f"2{GROUP_SUFFIX}(Trainer)", f"2{HEADS}", "", "")
    return _form(
        source.GROUPS,
        _table(
            source.GROUP_CAPTION, (source.TRAINER_LABEL, source.COUNT_LABEL) * 2, rows
        ),
        trDate=DATE,
        trDateReplace="20261118",
    )


def _workout(
    seq=1, stall=6, horse="0000123", extra="", distance="", sprint=f"0{COUNT}"
):
    return _row(
        seq,
        f"2{GROUP_SUFFIX}",
        stall,
        f"<a href=\"javascript:goPage4('{horse}')\">\n Runner \n</a>{extra}",
        "Class",
        "Rider",
        "",
        "06:55",
        "07:04",
        f"9{MIN}",
        distance,
        f"1{COUNT}",
        sprint,
    )


def _detail(rows=None, weekday="??"):
    if rows is None:
        rows = _workout()
    date_header = (
        f"<table><caption>{source.DATE_CAPTION}</caption>"
        f"<tr><th>{source.DATE_LABEL}</th><td>{DATE}({weekday})</td></tr></table>"
    )
    return _form(
        source.DETAIL,
        f"<script>function goPage4(hrno){{{source.PROFILE_ACTION}}}</script>"
        + date_header
        + _table(source.DETAIL_CAPTION, source.DETAIL_COLUMNS, rows),
        trDate=DATE,
        trYo=weekday,
        hrNo="",
    )


def _read(body, clock=OBSERVED, *, groups=None, count=1):
    return source.daily_workouts(
        body,
        DAY,
        clock,
        expected_groups={2: 1} if groups is None else groups,
        expected_count=count,
    )


def test_reconciles_all_three_public_views_and_native_horse_keys():
    qty = source.index_count(_index(), DAY)
    groups = source.group_counts(_group(), DAY)
    previous, now = _workout(), _workout(seq=2, stall=7, horse="0000124", sprint="")
    weekday, rows = _read(_detail(previous + now), groups=groups, count=qty)
    assert weekday == "??"
    assert len(rows) == qty == 2 and groups == {2: 2}
    assert [row.horse_id for row in rows] == ["123", "124"]
    assert [row.distance_literal for row in rows] == [None, None]
    assert [row.gait_counts for row in rows] == [(1, 0), (1, None)]
    assert rows[0].horse_name == "Runner" and rows[0].minutes == 9


def test_unlisted_date_and_group_padding_are_not_source_counts():
    with pytest.raises(ValueError, match="workout_date_not_listed_unconfirmed"):
        source.index_count(_index(), date(2026, 11, 19))
    row = _row(f"2{GROUP_SUFFIX}(Trainer)", f"2{HEADS}", "", "")
    with pytest.raises(ValueError, match="unverified_workout_group"):
        source.group_counts(_group(row + row), DAY)


def test_duplicate_group_is_not_silently_merged():
    row = _row(
        f"2{GROUP_SUFFIX}(Trainer)", f"2{HEADS}", f"2{GROUP_SUFFIX}(Same)", f"1{HEADS}"
    )
    with pytest.raises(ValueError, match="duplicate_workout_group"):
        source.group_counts(_group(row), DAY)


def test_untrusted_date_or_weekday_is_not_a_date_match():
    with pytest.raises(ValueError, match="workout_weekday_disagrees"):
        source.index_count(_index(f"{DATE}(??)"), DAY)
    with pytest.raises(ValueError, match="workout_weekday_disagrees"):
        _read(_detail(weekday="\ubaa9"))
    with pytest.raises(ValueError, match="workout_detail_date_mismatch"):
        _read(_detail().replace(f"{DATE}(??)", "2026/11/17(??)"))


@pytest.mark.parametrize(
    ("before", "after", "error"),
    [
        (
            'name="meet" value="1"',
            'name="meet" value="3"',
            "unverified_seoul_workout_scope",
        ),
        (
            'name="hrNo" value=""',
            'name="hrNo" value="123"',
            "unverified_workout_profile_links",
        ),
        ("goPage4('0000123')", "goPage5('0000123')", "unverified_workout_horse_id"),
        ("<td>1</td>", "<td>2</td>", "workout_sequence_or_horse_link_missing"),
        ("06:55", "06:75", "invalid_workout_wall_clock"),
        ("07:04", "07:05", "workout_duration_does_not_match_clocks"),
        (f"9{MIN}", f"0{MIN}", "invalid_workout_count_or_key"),
        ("<td>Class</td>", "<td colspan='2'>Class</td>", "workout_row_shape_changed"),
    ],
)
def test_fails_closed_on_layout_and_identity_or_time_drift(before, after, error):
    with pytest.raises(ValueError, match=error):
        _read(_detail().replace(before, after, 1))


def test_link_label_only_and_duplicate_horses_are_required():
    with pytest.raises(ValueError, match="workout_sequence_or_horse_link_missing"):
        _read(_detail(_workout(extra="other")))
    with pytest.raises(ValueError, match="duplicate_workout_horse_or_stall"):
        _read(_detail(_workout() + _workout(seq=2, stall=7)))
    with pytest.raises(ValueError, match="duplicate_workout_horse_or_stall"):
        _read(_detail(_workout() + _workout(seq=2, horse="0000124")))


def test_empty_partial_and_competing_group_counts_are_distinct_errors():
    with pytest.raises(ValueError, match="workout_body_empty_unconfirmed"):
        _read(_detail(""))
    with pytest.raises(ValueError, match="workout_detail_does_not_match_scope_counts"):
        _read(_detail(), count=2)
    with pytest.raises(ValueError, match="workout_detail_does_not_match_scope_counts"):
        _read(_detail(), groups={3: 1})


def test_requires_observation_at_or_after_printed_clocks():
    with pytest.raises(ValueError, match="workout_observation_requires_timezone"):
        _read(_detail(), datetime(2026, 11, 18, 10, 0))
    with pytest.raises(ValueError, match="workout_after_observation"):
        _read(_detail(), datetime.fromisoformat("2026-11-18T07:03:00+09:00"))
    assert _read(_detail(), datetime.fromisoformat("2026-11-18T07:04:00+09:00"))[1]
