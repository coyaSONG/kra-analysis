"""Read the official Seoul all-date workout HTML without making requests."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser

from shared.official_result_support import Table, tables

KST = timezone(timedelta(hours=9))
INDEX = "/trainer/dailyDayTrainList.do?Act=09&Sub=3&meet=1"
GROUPS = "/trainer/dailyGroupTrainList.do"
DETAIL = "/trainer/dailyAllTrainDetail.do"
DATE_LABEL = "\uc870\uad50\uc77c\uc790"
COUNT_LABEL = "\uc870\uad50\ub450\uc218"
TRAINER_LABEL = "\uc870\uad50\uc0ac"
ORDER = "\uc21c"
INDEX_CAPTION = "\uc77c\uc77c\uc870\uad50 \ubaa9\ub85d\uc744"
GROUP_CAPTION = "\uc870\ubcc4 \uc870\uad50\ud604\ud669\uc744"
DATE_CAPTION = "\uc870\uad50\uc77c\uc790\ub97c \uc81c\uacf5\ud558\ub294"
DETAIL_CAPTION = "\uc804\uccb4\uc77c\ubcc4\uc0c1\uc138\uc870\uad50\ud604\ud669\uc744"
DETAIL_COLUMNS = (
    ORDER,
    "\uc870",
    "\uc870\ubc88",
    "\ub9c8\uba85",
    "\ub4f1\uae09",
    "\uae30\uc2b9\uc790",
    "\ube44\uace0",
    "\uc785\uc7a5\uc2dc\uac01",
    "\ud1f4\uc7a5\uc2dc\uac01",
    "\uc870\uad50\uc2dc\uac04",
    "\uc804\uccb4\uac70\ub9ac",
    "\uad6c\ubcf4",
    "\uc2b5\ubcf4",
)
WEEKDAYS = "\uc6d4\ud654\uc218\ubaa9\uae08\ud1a0\uc77c"
FULL_DATE = re.compile(r"(20[0-9]{2}/[0-9]{2}/[0-9]{2})\(([^()]+)\)")
HOUR_MINUTE = re.compile(r"([01][0-9]|2[0-3]):([0-5][0-9])")
PROFILE_LINK = re.compile(r"javascript:goPage4\('([0-9]{1,8})'\);?")
PROFILE_ACTION = 'form.action = "/racehorse/profileHorseItem.do";'


@dataclass(frozen=True)
class Workout:
    ordinal: int
    group: int
    stall: int
    horse_id: str
    horse_name: str
    start_minute: int
    end_minute: int
    minutes: int
    distance_literal: str | None
    gait_counts: tuple[int | None, int | None]


class _ScopeForm(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.attrs = []
        self.active = False
        self.fields = {}
        self.duplicates = False

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "form":
            self.active = values.get("name") == "form1"
            if self.active:
                self.attrs.append(values)
        if self.active and tag == "input" and values.get("type") == "hidden":
            field = values.get("name")
            self.duplicates |= field in self.fields
            self.fields[field] = values.get("value")

    def handle_endtag(self, tag):
        if tag == "form":
            self.active = False


def _scope(html: str, path: str, day: date | None = None) -> dict:
    form = _ScopeForm()
    form.feed(html)
    form.close()
    if (
        len(form.attrs) != 1
        or form.duplicates
        or form.attrs[0].get("action") != path
        or form.attrs[0].get("method") != "post"
        or any(
            form.fields.get(k) != v
            for k, v in {"meet": "1", "Act": "09", "Sub": "3"}.items()
        )
    ):
        raise ValueError("unverified_seoul_workout_scope")
    if day is not None and form.fields.get("trDate") != day.strftime("%Y/%m/%d"):
        raise ValueError("workout_form_date_mismatch")
    return form.fields


def _table(html: str, prefix: str) -> Table:
    found = [
        table for table in tables(html) if table.caption.strip().startswith(prefix)
    ]
    if len(found) != 1 or found[0].invalid or not found[0].closed or not found[0].rows:
        raise ValueError("unverified_workout_table")
    return found[0]


def _body(table: Table, columns: tuple[str, ...]):
    header, *rows = table.rows
    if tuple("".join(cell.text.split()) for cell in header) != columns or any(
        cell.tag != "th" or cell.span for cell in header
    ):
        raise ValueError("workout_heading_changed")
    if any(
        len(row) != len(columns) or any(cell.tag != "td" or cell.span for cell in row)
        for row in rows
    ):
        raise ValueError("workout_row_shape_changed")
    return rows


def _uint(text: str, suffix: str = "", *, positive: bool = False) -> int:
    match = re.fullmatch(r"([0-9]{1,6})" + re.escape(suffix), text)
    if match is None or (positive and int(match[1]) <= 0):
        raise ValueError("invalid_workout_count_or_key")
    return int(match[1])


def _date_value(text: str, *, allow_placeholder: bool) -> tuple[date, str]:
    match = FULL_DATE.fullmatch(text)
    if match is None:
        raise ValueError("workout_date_not_literal")
    value = date.fromisoformat(match[1].replace("/", "-"))
    week = match[2]
    if week != WEEKDAYS[value.weekday()] and not (allow_placeholder and week == "??"):
        raise ValueError("workout_weekday_disagrees")
    return value, week


def index_count(html: str, day: date) -> int:
    """Read one displayed date count; a missing date does not imply no activity."""
    _scope(html, INDEX)
    rows = _body(_table(html, INDEX_CAPTION), (ORDER, DATE_LABEL, COUNT_LABEL))
    counts = {}
    for expected, row in enumerate(rows, 1):
        if _uint(row[0].text, positive=True) != expected:
            raise ValueError("workout_index_sequence_changed")
        event, _ = _date_value(row[1].text, allow_placeholder=False)
        if event in counts:
            raise ValueError("duplicate_workout_index_day")
        counts[event] = _uint(row[2].text, "\ub450")
    if day not in counts:
        raise ValueError("workout_date_not_listed_unconfirmed")
    return counts[day]


def group_counts(html: str, day: date) -> dict[int, int]:
    form = _scope(html, GROUPS, day)
    if form.get("trDateReplace") != day.strftime("%Y%m%d"):
        raise ValueError("workout_group_date_mismatch")
    rows = _body(_table(html, GROUP_CAPTION), (TRAINER_LABEL, COUNT_LABEL) * 2)
    counts = {}
    for pos, row in enumerate(rows, 1):
        for offset in (0, 2):
            trainer, count = (cell.text for cell in row[offset : offset + 2])
            if not trainer and not count and pos == len(rows) and offset == 2:
                continue
            match = re.fullmatch(r"([0-9]{1,3})\uc870\([^)]+\)", trainer)
            if match is None:
                raise ValueError("unverified_workout_group")
            number = _uint(match[1], positive=True)
            if number in counts:
                raise ValueError("duplicate_workout_group")
            counts[number] = _uint(count, "\ub450")
    if not counts:
        raise ValueError("workout_groups_empty_unconfirmed")
    return counts


def _minute(text: str) -> int:
    match = HOUR_MINUTE.fullmatch(text)
    if match is None:
        raise ValueError("invalid_workout_wall_clock")
    return 60 * int(match[1]) + int(match[2])


def daily_workouts(
    html: str,
    day: date,
    observed_at: datetime,
    *,
    expected_groups: dict[int, int],
    expected_count: int,
) -> tuple[str, tuple[Workout, ...]]:
    """Return the literal weekday and identity-bearing rows of the checked edition."""
    fields = _scope(html, DETAIL, day)
    if fields.get("hrNo") != "" or html.count(PROFILE_ACTION) != 1:
        raise ValueError("unverified_workout_profile_links")
    (header,) = _table(html, DATE_CAPTION).rows
    if (
        len(header) != 2
        or header[0].text != DATE_LABEL
        or [c.tag for c in header] != ["th", "td"]
        or any(c.span for c in header)
    ):
        raise ValueError("workout_detail_date_row_changed")
    event, weekday = _date_value(header[1].text, allow_placeholder=True)
    if event != day or weekday != fields.get("trYo"):
        raise ValueError("workout_detail_date_mismatch")
    if observed_at.utcoffset() is None:
        raise ValueError("workout_observation_requires_timezone")
    local = observed_at.astimezone(KST)
    if local.date() < day:
        raise ValueError("workout_after_observation")

    rows = _body(_table(html, DETAIL_CAPTION), DETAIL_COLUMNS)
    if not rows:
        raise ValueError("workout_body_empty_unconfirmed")
    horses, stalls, counts, result = set(), set(), Counter(), []
    for ordinal, row in enumerate(rows, 1):
        text = [cell.text for cell in row]
        name = row[3]
        if (
            _uint(text[0], positive=True) != ordinal
            or not name.text
            or len(name.links) != 1
            or [" ".join(x.split()) for x in name.link_labels] != [name.text]
        ):
            raise ValueError("workout_sequence_or_horse_link_missing")
        link = PROFILE_LINK.fullmatch(name.links[0])
        if link is None or int(link[1]) == 0:
            raise ValueError("unverified_workout_horse_id")
        hid, group, stall = (
            str(int(link[1])),
            _uint(text[1], "\uc870", positive=True),
            _uint(text[2], positive=True),
        )
        if hid in horses or (group, stall) in stalls:
            raise ValueError("duplicate_workout_horse_or_stall")
        start, end = map(_minute, text[7:9])
        duration = _uint(text[9], "\ubd84", positive=True)
        if duration != end - start:
            raise ValueError("workout_duration_does_not_match_clocks")
        if local.date() == day and end > 60 * local.hour + local.minute:
            raise ValueError("workout_after_observation")
        easy, fast = (_uint(raw, "\ud68c") if raw else None for raw in text[11:13])
        gait = easy, fast
        result.append(
            Workout(
                ordinal,
                group,
                stall,
                hid,
                name.text,
                start,
                end,
                duration,
                text[10] or None,
                gait,
            )
        )
        horses.add(hid)
        stalls.add((group, stall))
        counts[group] += 1
    if len(result) != expected_count or dict(counts) != expected_groups:
        raise ValueError("workout_detail_does_not_match_scope_counts")
    return weekday, tuple(result)
