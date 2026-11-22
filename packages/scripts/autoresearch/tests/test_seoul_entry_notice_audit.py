from datetime import date, datetime
from html import escape

import pytest

from autoresearch.seoul_entry_notice_audit import (
    CAPTIONS,
    EMPTY,
    HEADERS,
    HORSE_STATUS,
    RIDER_CHANGE,
    SEOUL,
    check_notice,
    parse_seoul_bulletin,
)

FIRST, LAST = date(2026, 11, 21), date(2026, 11, 22)
CUTOFF = datetime.fromisoformat("2026-11-20T01:15:00+00:00")
LATER = datetime.fromisoformat("2026-11-22T19:05:34+00:00")
MARKER = "\ucd9c\uc804\uc81c\uc678"
HORSE = "<a href=\"javascript:goHorse('0000123','1')\">Runner</a>"
OLD = "<a href=\"javascript:goBefJockey('00031','3')\">Old</a>"
NEW = "<a href=\"javascript:goAftJockey('00042','1')\">New</a>"


def _table(kind, body):
    heads = [
        f"<th colspan='2'>{name}</th>"
        if kind == RIDER_CHANGE and i in (5, 6)
        else f"<th>{name}</th>"
        for i, name in enumerate(HEADERS[kind])
    ]
    return (
        f"<table><caption>{CAPTIONS[kind]} material</caption>"
        f"<tr>{''.join(heads)}</tr>{body}</table>"
    )


def _row(*cells):
    return "<tr>" + "".join(f"<td>{cell}</td>" for cell in cells) + "</tr>"


def _bulletin(horse, rider, first=FIRST, last=LAST):
    heading = f"<h3>{first:%Y/%m/%d} - {last:%Y/%m/%d}</h3>"
    return heading * 3 + _table(HORSE_STATUS, horse) + _table(RIDER_CHANGE, rider)


def _horse(venue=SEOUL, clock="11/21 14:31"):
    return _row(
        MARKER, venue, "2026/11/21", "7", "5", HORSE, "Trainer", "Rider", "", clock
    )


def _rider():
    return _row(
        SEOUL,
        "2026/11/22",
        "10",
        "4",
        HORSE,
        OLD,
        "52.5",
        NEW,
        "52.5",
        "",
        "11/22 13:40",
    )


def test_preserves_horse_and_grouped_rider_change_in_real_column_order():
    source = _bulletin(_horse(), _rider()).replace(f"{SEOUL}</td>", SEOUL)
    bulletin = parse_seoul_bulletin(source, FIRST, LAST)
    cancelled, changed = bulletin.notices
    assert bulletin.implicit_venue_closures == 2
    assert bulletin.table_states == {
        HORSE_STATUS: "rows_observed",
        RIDER_CHANGE: "rows_observed",
    }
    assert (cancelled.race_id, cancelled.gate, cancelled.horse_id) == (
        "20261121_1_7",
        5,
        "123",
    )
    assert cancelled.cells[0] == MARKER
    assert cancelled.reported_minute.isoformat() == "2026-11-21T14:31:00+09:00"
    assert changed.riders == ("31", "42")
    assert changed.cells[6] == changed.cells[8] == "52.5"


def test_empty_is_not_inferred_from_absent_rows():
    explicit = f"<tr><td colspan='10'>{escape(EMPTY[HORSE_STATUS])}</td></tr>"
    bulletin = parse_seoul_bulletin(_bulletin(explicit, ""), FIRST, LAST)
    assert bulletin.table_states == {
        HORSE_STATUS: "explicit_empty_at_observation",
        RIDER_CHANGE: "empty_unconfirmed",
    }
    assert not bulletin.notices


def test_empty_sentinel_must_cover_its_entire_table():
    wrong_width = f"<tr><td colspan='9'>{escape(EMPTY[HORSE_STATUS])}</td></tr>"
    with pytest.raises(ValueError, match="unverified_empty_notice_row"):
        parse_seoul_bulletin(_bulletin(wrong_width, ""), FIRST, LAST)


@pytest.mark.parametrize(
    ("before", "after", "error"),
    [
        ("<td>7</td>", "<td>7", "unverified_bulletin_structure"),
        (" colspan='2'", " colspan='3'", "unknown_notice_column_groups"),
        ("<td>52.5</td>", "", "incorrect_notice_row_layout"),
        ("'0000123','1'", "'0000123','4'", "notice_link_identity_unrecognized"),
        ("Runner</a>", "Runner</a> different", "notice_link_identity_missing"),
        ("11/21 14:31", "11/23 14:31", "notice_minute_outside_event_window"),
        ("<td>2026/11/21</td>", "<td>2026/11/20</td>", "notice_outside_display_scope"),
        (f"<td>{SEOUL}</td>", "<td>Wrong</td>", "notice_not_dated_seoul"),
    ],
)
def test_rejects_other_layouts_and_unbound_rows(before, after, error):
    html = _bulletin(_horse(), _rider()).replace(before, after, 1)
    with pytest.raises(ValueError, match=error):
        parse_seoul_bulletin(html, FIRST, LAST)


def test_original_display_dates_are_required():
    html = _bulletin(_horse(), _rider()).replace("2026/11/22", "2026/11/23", 1)
    with pytest.raises(ValueError, match="unexpected_notice_date_scope"):
        parse_seoul_bulletin(html, FIRST, LAST)


def test_notice_can_cross_year_only_inside_the_event_window():
    first = last = date(2027, 1, 2)
    old = _horse(clock="12/31 21:30").replace("2026/11/21", "2027/01/02")
    result = parse_seoul_bulletin(_bulletin(old, "", first, last), first, last)
    assert result.notices[0].reported_minute.isoformat() == "2026-12-31T21:30:00+09:00"


@pytest.mark.parametrize(
    ("captured", "cutoff", "timing"),
    [
        (LATER, CUTOFF, "publisher_minute_at_or_after_cutoff"),
        (
            LATER,
            datetime.fromisoformat("2026-11-21T05:31:00+00:00"),
            "publisher_minute_at_or_after_cutoff",
        ),
        (
            LATER,
            datetime.fromisoformat("2026-11-21T05:31:01+00:00"),
            "observed_after_cutoff_only",
        ),
        (
            datetime.fromisoformat("2026-11-21T05:30:00+00:00"),
            LATER,
            "publisher_minute_after_observation",
        ),
        (
            datetime.fromisoformat("2026-11-21T05:32:00+00:00"),
            LATER,
            "locally_observed_before_cutoff",
        ),
    ],
)
def test_two_clock_states_are_distinct(captured, cutoff, timing):
    (notice,) = parse_seoul_bulletin(_bulletin(_horse(), ""), FIRST, LAST).notices
    verified = check_notice(
        notice,
        {("20261121_1_7", 5): ("123", "Runner")},
        observed_at=captured,
        cutoff=cutoff,
    )
    assert verified["identity"] == "exact_original_declaration"
    assert verified["timing"] == timing
    assert not verified["may_modify_original"]


def test_identity_conflicts_do_not_disappear_or_drop_original_entries():
    (notice,) = parse_seoul_bulletin(_bulletin(_horse(), ""), FIRST, LAST).notices
    key = ("20261121_1_7", 5)
    roster = {key: ("120", "Runner")}
    assert check_notice(notice, roster, observed_at=LATER, cutoff=CUTOFF)[
        "identity"
    ] == ("original_declaration_identity_conflict")
    assert roster == {key: ("120", "Runner")}
    assert check_notice(notice, {}, observed_at=LATER, cutoff=CUTOFF)["identity"] == (
        "no_matching_declared_gate"
    )


def test_repeated_gate_notices_are_preserved_as_separate_rows():
    repeated = _horse() + _horse(clock="11/21 14:33")
    bulletin = parse_seoul_bulletin(_bulletin(repeated, ""), FIRST, LAST)
    assert [notice.row_index for notice in bulletin.notices] == [1, 2]
    assert [notice.reported_minute.minute for notice in bulletin.notices] == [31, 33]
