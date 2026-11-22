"""Offline inspection of the official Seoul entry change board."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from shared.kra_race_identity import validate_race_identity
from shared.official_result_support import Cell, Tables, integer

SEOUL = "\uc11c\uc6b8"
KST = timezone(timedelta(hours=9))
HORSE_STATUS = "horse_status"
RIDER_CHANGE = "rider_change"
CAPTIONS = {
    HORSE_STATUS: "\ub9d0\ucde8\uc18c\ub0b4\uc6a9\uc744",
    RIDER_CHANGE: "\uae30\uc218\ubcc0\uacbd\ub0b4\uc6a9\uc744",
}
VENUE = "\uac1c\ucd5c\uc9c0"
SCOPE = (
    VENUE,
    "\uacbd\uc8fc\uc77c\uc790",
    "\uacbd\uc8fc\ubc88\ud638",
    "\ucd9c\uc804\ubc88\ud638",
    "\ub9c8\uba85",
)
TAIL = ("\uc0ac\uc720", "\uacf5\uc9c0\uc2dc\uac01")
HEADERS = {
    HORSE_STATUS: (
        "\uad6c\ubd84",
        *SCOPE,
        "\uc870\uad50\uc0ac",
        "\uae30\uc218\uba85",
        *TAIL,
    ),
    RIDER_CHANGE: (*SCOPE, "\ubcc0\uacbd\uc804", "\ubcc0\uacbd\ud6c4", *TAIL),
}
EMPTY = {
    HORSE_STATUS: "\ub9d0 \ucde8\uc18c \uc790\ub8cc\uac00 \uc5c6\uc2b5\ub2c8\ub2e4.",
    RIDER_CHANGE: "\uae30\uc218 \ubcc0\uacbd \uc790\ub8cc\uac00 \uc5c6\uc2b5\ub2c8\ub2e4.",
}
STATUS_VALUES = {
    "\ucd9c\uc804\ucde8\uc18c",
    "\ucd9c\uc804\uc81c\uc678",
    "\ubc1c\uc8fc\uc81c\uc678",
    "\ucd9c\ubc1c\uc81c\uc678",
    "\uacbd\uc8fc\uc81c\uc678",
}
DATE_CELL = re.compile(r"(20[0-9]{2}/[0-9]{2}/[0-9]{2})(?: \([^()]{1,4}\))?")
BOARD_DATE = re.compile(r"20[0-9]{2}/[0-9]{2}/[0-9]{2}")
MINUTE = re.compile(r"([0-9]{1,2})/([0-9]{1,2}) ([0-9]{1,2}):([0-9]{2})")
WEIGHT = re.compile(r"[1-9][0-9](?:\.[0-9])?")


@dataclass(frozen=True)
class Notice:
    table: str
    row_index: int
    race_id: str
    gate: int
    horse_id: str
    horse_name: str
    reported_minute: datetime
    cells: tuple[str, ...]
    riders: tuple[str, ...]


@dataclass(frozen=True)
class Bulletin:
    table_states: dict[str, str]
    notices: tuple[Notice, ...]
    implicit_venue_closures: int


def _kind(caption):
    compact = "".join(caption.split())
    return next(
        (kind for kind, prefix in CAPTIONS.items() if compact.startswith(prefix)), None
    )


class _SeoulTables(Tables):
    def __init__(self):
        super().__init__()
        self.heading = None
        self.ranges = []
        self.spans = {}
        self.implicit_venue_closures = 0

    def handle_starttag(self, tag, attrs):
        kind = _kind(self.table.caption) if self.table else None
        if tag == "h3" and self.table is None:
            self.heading = []
        if (
            kind is not None
            and tag == "td"
            and self.row is not None
            and len(self.row) == (1 if kind == HORSE_STATUS else 0)
            and self.cell is not None
            and self.cell.tag == "td"
            and not self.cell.links
            and not self.cell.span
            and self.cell.text.strip() == SEOUL
        ):
            # These two tables omit only the optional venue cell end tag.
            super().handle_endtag("td")
            self.implicit_venue_closures += 1
        super().handle_starttag(tag, attrs)
        if tag in ("td", "th") and kind and self.cell is not None:
            values = dict(attrs)
            self.spans[id(self.cell)] = (
                values.get("colspan", "1"),
                values.get("rowspan", "1"),
            )

    def handle_data(self, data):
        super().handle_data(data)
        if self.heading is not None:
            self.heading.append(data)

    def handle_endtag(self, tag):
        if tag == "h3" and self.heading is not None:
            dates = BOARD_DATE.findall("".join(self.heading))
            if dates:
                self.ranges.append(
                    tuple(date.fromisoformat(x.replace("/", "-")) for x in dates)
                )
            self.heading = None
        super().handle_endtag(tag)


def _linked_id(cell: Cell, action: str, *, seoul_only=False) -> str:
    venue = "1" if seoul_only else "[1-4]"
    pattern = rf"javascript:{action}\('([0-9]{{1,8}})','{venue}'\);?"
    if len(cell.links) != 1 or cell.link_labels != [cell.text] or not cell.text:
        raise ValueError("notice_link_identity_missing")
    match = re.fullmatch(pattern, cell.links[0])
    if match is None:
        raise ValueError("notice_link_identity_unrecognized")
    return str(integer(match[1], 99_999_999))


def _reported_minute(text: str, event: date) -> datetime:
    match = MINUTE.fullmatch(text)
    if match is None:
        raise ValueError("notice_minute_missing")
    month, day, hour, minute = map(int, match.groups())
    for offset in range(8):
        value = event - timedelta(days=offset)
        if (value.month, value.day) == (month, day):
            return datetime(value.year, month, day, hour, minute, tzinfo=KST)
    raise ValueError("notice_minute_outside_event_window")


def _row(kind, cells, index, first, last) -> Notice:
    horse_status = kind == HORSE_STATUS
    if len(cells) != (10 if horse_status else 11) or any(
        c.tag != "td" or c.span for c in cells
    ):
        raise ValueError("incorrect_notice_row_layout")
    raw = tuple(c.text for c in cells)
    if horse_status and raw[0] not in STATUS_VALUES:
        raise ValueError("unrecognized_horse_status_literal")
    n = int(horse_status)
    day = DATE_CELL.fullmatch(raw[n + 1])
    if raw[n] != SEOUL or day is None:
        raise ValueError("notice_not_dated_seoul")
    event = date.fromisoformat(day[1].replace("/", "-"))
    if not first <= event <= last:
        raise ValueError("notice_outside_display_scope")
    race_day = event.strftime("%Y%m%d")
    race, gate = integer(raw[n + 2]), integer(raw[n + 3])
    validate_race_identity(1, race_day, race)
    horse = cells[n + 4]
    riders = ()
    if not horse_status:
        if not WEIGHT.fullmatch(raw[6]) or not WEIGHT.fullmatch(raw[8]):
            raise ValueError("unknown_notice_weight_layout")
        riders = (
            _linked_id(cells[5], "goBefJockey"),
            _linked_id(cells[7], "goAftJockey"),
        )
    return Notice(
        kind,
        index,
        f"{race_day}_1_{race}",
        gate,
        _linked_id(horse, "goHorse", seoul_only=True),
        horse.text,
        _reported_minute(raw[-1], event),
        raw,
        riders,
    )


def parse_seoul_bulletin(html: str, first: date, last: date) -> Bulletin:
    """Check the exact displayed scope, not the currently active roster."""
    parser = _SeoulTables()
    parser.feed(html)
    parser.close()
    if first > last or parser.ranges != [(first, last)] * 3:
        raise ValueError("unexpected_notice_date_scope")
    states, rows = {}, []
    for kind, header in HEADERS.items():
        matches = [table for table in parser.tables if _kind(table.caption) == kind]
        if len(matches) != 1 or not matches[0].closed or matches[0].invalid:
            raise ValueError("unverified_bulletin_structure")
        cells, *body = matches[0].rows if matches[0].rows else ([],)
        if tuple("".join(c.text.split()) for c in cells) != header or any(
            c.tag != "th"
            or parser.spans.get(id(c))
            != ("2" if kind == RIDER_CHANGE and i in (5, 6) else "1", "1")
            for i, c in enumerate(cells)
        ):
            raise ValueError("unknown_notice_column_groups")
        state = "rows_observed" if body else "empty_unconfirmed"
        if len(body) == 1 and len(body[0]) == 1 and body[0][0].text == EMPTY[kind]:
            singleton = body[0][0]
            width = "10" if kind == HORSE_STATUS else "11"
            if (
                singleton.tag != "td"
                or parser.spans.get(id(singleton)) != (width, "1")
                or singleton.links
            ):
                raise ValueError("unverified_empty_notice_row")
            state = "explicit_empty_at_observation"
        elif body:
            rows.extend(
                _row(kind, row, i, first, last) for i, row in enumerate(body, 1)
            )
        states[kind] = state
    return Bulletin(states, tuple(rows), parser.implicit_venue_closures)


def check_notice(
    notice: Notice,
    roster: dict[tuple[str, int], tuple[str, str]],
    *,
    observed_at: datetime,
    cutoff: datetime,
) -> dict:
    """Report identity and clock states independently; neither revises entries."""
    if observed_at.utcoffset() is None or cutoff.utcoffset() is None:
        raise ValueError("notice_readback_requires_zoned_clocks")
    declared = roster.get((notice.race_id, notice.gate))
    if declared is None:
        state = "no_matching_declared_gate"
    elif declared != (notice.horse_id, notice.horse_name):
        state = "original_declaration_identity_conflict"
    else:
        state = "exact_original_declaration"
    if notice.reported_minute > observed_at:
        timing = "publisher_minute_after_observation"
    elif notice.reported_minute >= cutoff:
        timing = "publisher_minute_at_or_after_cutoff"
    elif observed_at >= cutoff:
        timing = "observed_after_cutoff_only"
    else:
        timing = "locally_observed_before_cutoff"
    return {
        "identity": state,
        "timing": timing,
        "publisher_reported_minute": notice.reported_minute.isoformat(),
        "observed_at": observed_at.isoformat(),
        "may_modify_original": False,
    }
