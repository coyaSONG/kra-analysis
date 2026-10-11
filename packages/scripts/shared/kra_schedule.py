"""Parse and reconcile the complete dated official KRA race cards."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from html.parser import HTMLParser
from typing import Any
from zoneinfo import ZoneInfo

from shared.kra_race_identity import MEET_NAMES, validate_race_identity

KST = ZoneInfo("Asia/Seoul")
SOURCE_URLS = {
    "national": "https://race.kra.co.kr/thisweekrace/ThisWeekDetailInfoList.do",
    **{
        f"region_{menu}": (
            "https://race.kra.co.kr/chulmainfo/ChulmaDetailInfoList.do"
            f"?Act=02&Sub=1&meet={menu}"
        )
        for menu in (1, 2, 3)
    },
}
REGION_VENUES = {"region_1": {1}, "region_2": {2}, "region_3": {3, 4}}
REGIONAL_HEADERS = (
    "\uc21c",
    "\uacbd\uc8fc\uc77c\uc790",
    "\uacbd\uc8fc",
    "\ub4f1\uae09",
    "\uac70\ub9ac",
    "\ud3b8\uc131",
    "\ucd9c\uc804",
    "\uacbd\uc8fc\uba85",
    "\ucd9c\ubc1c\uc2dc\uac01",
    "\uac1c\ucd5c\uc9c0",
    "\ube44\uace0",
    "PDF",
)
NATIONAL_HEADERS = (
    "\uc21c",
    "\uc9c0\uc5ed",
    "\uacbd\uc8fc\uc77c\uc790",
    "\uacbd\uc8fc",
    "\ub4f1\uae09",
    "\uac70\ub9ac",
    "\ucd9c\uc804",
    "\uacbd\uc8fc\uad6c\ubd84",
    "\ucd9c\ubc1c\uc2dc\uac01",
    "\uc624\ub298\uc758\uacbd\uc8fc",
    "\ud310\ub9e4\uacbd\ub9c8\uacf5\uc6d0",
)
SELLING_HEADERS = ("\uc11c\uc6b8", "\ubd80\uacbd", "\uc601\ucc9c", "\uc81c\uc8fc")
WEEKDAYS = "\uc6d4\ud654\uc218\ubaa9\uae08\ud1a0\uc77c"
_DATE = re.compile(r"(20[0-9]{2})/([0-9]{2})/([0-9]{2})\(([\uac00-\ud7a3])\)")
_TIME = re.compile(r"([0-9]{2}):([0-9]{2})")


def _compact(value: str) -> str:
    return "".join(value.split())


@dataclass
class _Table:
    caption: str = ""
    headers: list[tuple[str, ...]] = field(default_factory=list)
    rows: list[tuple[str, ...]] = field(default_factory=list)
    closed: bool = False
    invalid: bool = False
    body_seen: bool = False


class _Tables(HTMLParser):
    """Retain table boundaries and reject body spans instead of shifting cells."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[_Table] = []
        self.stack: list[_Table] = []
        self.section = ""
        self.caption = False
        self.row: list[str] | None = None
        self.cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            if self.stack:
                self.stack[-1].invalid = True
            table = _Table()
            self.tables.append(table)
            self.stack.append(table)
            self.section, self.row, self.cell = "", None, None
        elif self.stack:
            table = self.stack[-1]
            if tag in ("thead", "tbody"):
                self.section = tag
                table.body_seen |= tag == "tbody"
            elif tag == "caption":
                self.caption = True
            elif tag == "tr":
                table.invalid |= self.row is not None
                self.row = []
            elif tag in ("td", "th"):
                table.invalid |= self.row is None or self.cell is not None
                if self.section == "tbody":
                    table.invalid |= any(
                        key in ("rowspan", "colspan") and value != "1"
                        for key, value in attrs
                    )
                self.cell = []
            elif tag == "br" and self.cell is not None:
                self.cell.append(" ")

    def handle_data(self, data: str) -> None:
        if self.stack:
            if self.caption:
                self.stack[-1].caption += data
            if self.cell is not None:
                self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if not self.stack:
            return
        table = self.stack[-1]
        if tag in ("td", "th"):
            if self.cell is None or self.row is None:
                table.invalid = True
            else:
                self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr":
            if self.row is None or self.cell is not None:
                table.invalid = True
            elif self.section == "thead":
                table.headers.append(tuple(_compact(c) for c in self.row))
            elif self.section == "tbody":
                table.rows.append(tuple(self.row))
            else:
                table.invalid = True
            self.row, self.cell = None, None
        elif tag == "caption":
            self.caption = False
        elif tag in ("thead", "tbody"):
            table.invalid |= self.row is not None
            self.section = ""
        elif tag == "table":
            table.invalid |= self.row is not None or self.cell is not None
            table.closed = True
            self.stack.pop()
            self.section, self.row, self.cell, self.caption = "", None, None, False


@dataclass(frozen=True, slots=True)
class ScheduledRace:
    meet: int
    race_date: str
    race_no: int
    scheduled_start_at: str
    runners: int
    declared_runners: int | None
    notes: str

    @property
    def race_id(self) -> str:
        return f"{self.race_date}_{self.meet}_{self.race_no}"

    def record(self) -> dict[str, Any]:
        return {"race_id": self.race_id, **asdict(self)}


def _number(value: str, *, maximum: int, suffix: str = "") -> int:
    raw = _compact(value)
    if suffix:
        if not raw.endswith(suffix):
            raise ValueError("invalid_schedule_number")
        raw = raw.removesuffix(suffix)
    if not re.fullmatch(r"[0-9]+", raw) or not 0 <= int(raw) <= maximum:
        raise ValueError("invalid_schedule_number")
    return int(raw)


def _race(cells: tuple[str, ...], *, national: bool) -> ScheduledRace:
    if len(cells) != (14 if national else 12):
        raise ValueError("unexpected_schedule_body_columns")
    date_cell, number_cell, venue_cell = (2, 3, 1) if national else (1, 2, 9)
    date_match = _DATE.fullmatch(_compact(cells[date_cell]))
    time_match = _TIME.fullmatch(_compact(cells[8]))
    if date_match is None or time_match is None:
        raise ValueError("invalid_schedule_date_or_time")
    year, month, day, weekday = date_match.groups()
    hour, minute = time_match.groups()
    start = datetime(
        int(year), int(month), int(day), int(hour), int(minute), tzinfo=KST
    )
    if weekday != WEEKDAYS[start.weekday()]:
        raise ValueError("schedule_weekday_mismatch")
    meet = MEET_NAMES.get(_compact(cells[venue_cell]))
    race_date = start.strftime("%Y%m%d")
    race_no = _number(cells[number_cell], maximum=20)
    validate_race_identity(meet, race_date, race_no)
    runners = _number(cells[6], maximum=20, suffix="" if national else "\ub450")
    declared = None if national else _number(cells[5], maximum=20, suffix="\ub450")
    if declared is not None and runners > declared:
        raise ValueError("schedule_runners_exceed_declared")
    return ScheduledRace(
        meet=meet,
        race_date=race_date,
        race_no=race_no,
        scheduled_start_at=start.isoformat(),
        runners=runners,
        declared_runners=declared,
        notes="" if national else cells[10],
    )


def parse_schedule_html(
    content: bytes, *, source_id: str, encoding: str = "euc-kr"
) -> tuple[ScheduledRace, ...]:
    if source_id not in SOURCE_URLS:
        raise ValueError("unsupported_schedule_source")
    parser = _Tables()
    parser.feed(content.decode(encoding, errors="strict"))
    parser.close()
    national = source_id == "national"
    headers = NATIONAL_HEADERS if national else REGIONAL_HEADERS
    candidates = [t for t in parser.tables if t.headers and t.headers[0] == headers]
    if len(candidates) != 1:
        raise ValueError("missing_or_duplicate_schedule_table")
    table = candidates[0]
    expected_headers = [headers, SELLING_HEADERS] if national else [headers]
    if (
        not table.closed
        or table.invalid
        or not table.body_seen
        or table.headers != expected_headers
        or not table.caption
        or not table.rows
    ):
        raise ValueError("incomplete_schedule_table")
    rows: list[ScheduledRace] = []
    for ordinal, cells in enumerate(table.rows, 1):
        if not cells or _number(cells[0], maximum=1000) != ordinal:
            raise ValueError("schedule_ordinal_gap_or_duplicate")
        row = _race(cells, national=national)
        if not national and row.meet not in REGION_VENUES[source_id]:
            raise ValueError("schedule_region_venue_mismatch")
        rows.append(row)
    if len({row.race_id for row in rows}) != len(rows):
        raise ValueError("duplicate_scheduled_race")
    for key in {(r.race_date, r.meet) for r in rows}:
        numbers = sorted(r.race_no for r in rows if (r.race_date, r.meet) == key)
        if numbers != list(range(1, len(numbers) + 1)):
            raise ValueError("schedule_race_number_gap")
    return tuple(sorted(rows, key=lambda r: (r.race_date, r.meet, r.race_no)))


def reconcile_schedule_cards(
    cards: dict[str, tuple[ScheduledRace, ...]], *, race_date: str
) -> dict[str, Any]:
    """Compare the whole published card before selecting one complete date."""
    validate_race_identity(1, race_date, 1)
    if set(cards) - SOURCE_URLS.keys():
        raise ValueError("unsupported_schedule_source")
    issues: list[dict[str, Any]] = []
    for source in SOURCE_URLS:
        if not cards.get(source):
            issues.append({"code": "missing_schedule_source", "source_id": source})
    national = {r.race_id: r for r in cards.get("national", ())}
    regional: dict[str, ScheduledRace] = {}
    for source in REGION_VENUES:
        for row in cards.get(source, ()):
            if row.race_id in regional:
                issues.append(
                    {"code": "duplicate_regional_race", "race_id": row.race_id}
                )
            regional[row.race_id] = row
    for race_id in sorted(national.keys() | regional.keys()):
        left, right = national.get(race_id), regional.get(race_id)
        if left is None or right is None:
            issues.append({"code": "schedule_membership_conflict", "race_id": race_id})
        elif (
            left.scheduled_start_at != right.scheduled_start_at
            or left.runners != right.runners
        ):
            issues.append(
                {
                    "code": "schedule_value_conflict",
                    "race_id": race_id,
                    "national": left.record(),
                    "regional": right.record(),
                }
            )
    observed_dates = sorted({r.race_date for rows in cards.values() for r in rows})
    weeks = {
        (
            datetime.strptime(d, "%Y%m%d")
            - timedelta(days=datetime.strptime(d, "%Y%m%d").weekday())
        ).date()
        for d in observed_dates
    }
    if len(weeks) != 1:
        issues.append({"code": "mixed_or_missing_card_week"})
    if race_date not in {r.race_date for r in national.values()}:
        issues.append({"code": "requested_date_not_published", "race_date": race_date})
    target_ids = sorted(
        {
            r.race_id
            for rows in cards.values()
            for r in rows
            if r.race_date == race_date
        },
        key=lambda key: tuple(int(value) for value in key.split("_")),
    )
    races = []
    for race_id in target_ids:
        observations = {
            source: row.record()
            for source, rows in cards.items()
            for row in rows
            if row.race_id == race_id
        }
        races.append({"race_id": race_id, "source_observations": observations})
    conflict = any(
        "conflict" in item["code"] or "duplicate" in item["code"] for item in issues
    )
    return {
        "format_version": "kra-schedule-reconciliation-v1",
        "race_date": race_date,
        "status": "conflict" if conflict else "unknown" if issues else "reconciled",
        "scope": "national_dated_card_crosschecked_with_all_regional_cards",
        "observed_dates": observed_dates,
        "source_race_counts": {key: len(rows) for key, rows in sorted(cards.items())},
        "race_count": len(races),
        "races": races,
        "issues": issues,
        "independent_time_verified": False,
        "target_accuracy_verified": False,
    }
