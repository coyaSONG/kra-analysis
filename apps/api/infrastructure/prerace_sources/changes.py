"""Authless public bulletin connectors for entry changes and cancellations."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from html import unescape
from html.parser import HTMLParser
from typing import Any, Literal

from infrastructure.prerace_sources.base import (
    BasePublicSourceConnector,
    PublicSourceSpec,
    RawSourceResponse,
    SourceRequest,
    validate_meet,
)
from infrastructure.prerace_sources.entry import KRA_RACE_HOST

ENTRY_CHANGE_BULLETIN_SPEC = PublicSourceSpec(
    source_id="entry_change_bulletin",
    name="출전표 변경 공지",
    host=KRA_RACE_HOST,
    path="/raceFastreport/ChulmapyoChange.do",
    method="GET",
    content_kind="html",
    description="말취소, 기수변경 등 출전표 변경 공지를 제공하는 공개 페이지",
    operational_tier="hard_required",
    update_hint="경주 직전 변경 공지 반영",
    default_query={"Act": "03", "Sub": "1"},
)


class EntryChangeConnector(BasePublicSourceConnector):
    spec = ENTRY_CHANGE_BULLETIN_SPEC

    def build_request(self, **kwargs: Any) -> SourceRequest:
        meet = int(kwargs["meet"])
        params = dict(self.spec.default_query)
        params["meet"] = validate_meet(meet)
        return self.spec.method, self.spec.url, params, None


EntryChangeType = Literal["cancelled", "jockey_change"]


@dataclass(frozen=True, slots=True)
class EntryChangeNotice:
    change_type: EntryChangeType
    source_section: str
    race_date: str | None
    race_no: int | None
    chul_no: int | None
    horse_name: str | None
    horse_no: str | None = None
    trainer_name: str | None = None
    trainer_no: str | None = None
    jockey_name: str | None = None
    jockey_no: str | None = None
    old_jockey_name: str | None = None
    old_jockey_no: str | None = None
    new_jockey_name: str | None = None
    new_jockey_no: str | None = None
    reason: str | None = None
    notice_category: str | None = None
    announced_at: str | None = None
    meet: int | None = None
    source_snapshot_at: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class _Cell:
    text: str
    hrefs: tuple[str, ...]


class _EntryChangeBulletinHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.current_section = ""
        self.rows: list[tuple[str, tuple[_Cell, ...]]] = []
        self._in_heading = False
        self._heading_parts: list[str] = []
        self._in_row = False
        self._row_cells: list[_Cell] = []
        self._in_cell = False
        self._cell_parts: list[str] = []
        self._cell_hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key: value or "" for key, value in attrs}
        if tag == "h2":
            self._in_heading = True
            self._heading_parts = []
            return
        if self._in_heading and tag == "img" and attr.get("alt"):
            self._heading_parts.append(attr["alt"])
            return
        if tag == "tr":
            self._in_row = True
            self._row_cells = []
            return
        if self._in_row and tag in {"td", "th"}:
            self._in_cell = True
            self._cell_parts = []
            self._cell_hrefs = []
            return
        if self._in_cell and tag == "a" and attr.get("href"):
            self._cell_hrefs.append(attr["href"])
            return
        if self._in_cell and tag == "br":
            self._cell_parts.append(" ")

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell_parts.append(data)
        elif self._in_heading:
            self._heading_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "h2" and self._in_heading:
            section = _normalize_text(" ".join(self._heading_parts))
            if section:
                self.current_section = section
            self._in_heading = False
            return
        if tag in {"td", "th"} and self._in_cell:
            self._row_cells.append(
                _Cell(
                    text=_normalize_text(" ".join(self._cell_parts)),
                    hrefs=tuple(self._cell_hrefs),
                )
            )
            self._in_cell = False
            return
        if tag == "tr" and self._in_row:
            if any(cell.text for cell in self._row_cells):
                self.rows.append((self.current_section, tuple(self._row_cells)))
            self._in_row = False


_JS_ID_RE = re.compile(
    r"go(?P<kind>Horse|Trainer|Jockey)\('(?P<id>[^']+)'\s*,\s*'(?P<meet>\d+)'\)"
)
_DATE_RE = re.compile(r"(?P<year>\d{4})\D+(?P<month>\d{1,2})\D+(?P<day>\d{1,2})")
_NOTICE_TIME_RE = re.compile(
    r"(?P<month>\d{1,2})/(?P<day>\d{1,2})\s+(?P<hour>\d{1,2}):(?P<minute>\d{2})"
)


def _normalize_text(value: str) -> str:
    return " ".join(unescape(value).split())


def _parse_int(value: str | None) -> int | None:
    if value is None:
        return None
    match = re.search(r"\d+", value)
    return int(match.group(0)) if match else None


def _normalize_race_date(value: str) -> str | None:
    match = _DATE_RE.search(value)
    if not match:
        return None
    year = int(match.group("year"))
    month = int(match.group("month"))
    day = int(match.group("day"))
    return f"{year:04d}{month:02d}{day:02d}"


def _normalize_notice_time(value: str, race_date: str | None) -> str | None:
    if race_date is None:
        return None
    match = _NOTICE_TIME_RE.search(value)
    if not match:
        return None
    year = int(race_date[:4])
    month = int(match.group("month"))
    day = int(match.group("day"))
    hour = int(match.group("hour"))
    minute = int(match.group("minute"))
    return f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:00+09:00"


def _linked_id(cell: _Cell, kind: str) -> str | None:
    for href in cell.hrefs:
        match = _JS_ID_RE.search(href)
        if match and match.group("kind") == kind:
            return match.group("id")
    return None


def _has_no_data(cells: tuple[_Cell, ...]) -> bool:
    return any("자료가 없습니다" in cell.text for cell in cells)


def _parse_cancelled_row(
    section: str,
    cells: tuple[_Cell, ...],
    *,
    meet: int | None,
    source_snapshot_at: str | None,
) -> EntryChangeNotice | None:
    if len(cells) < 9 or _has_no_data(cells):
        return None
    race_date = _normalize_race_date(cells[1].text)
    return EntryChangeNotice(
        change_type="cancelled",
        source_section=section,
        notice_category=cells[0].text or None,
        race_date=race_date,
        race_no=_parse_int(cells[2].text),
        chul_no=_parse_int(cells[3].text),
        horse_name=cells[4].text or None,
        horse_no=_linked_id(cells[4], "Horse"),
        trainer_name=cells[5].text or None,
        trainer_no=_linked_id(cells[5], "Trainer"),
        jockey_name=cells[6].text or None,
        jockey_no=_linked_id(cells[6], "Jockey"),
        reason=cells[7].text or None,
        announced_at=_normalize_notice_time(cells[8].text, race_date),
        meet=meet,
        source_snapshot_at=source_snapshot_at,
    )


def _parse_jockey_change_row(
    section: str,
    cells: tuple[_Cell, ...],
    *,
    meet: int | None,
    source_snapshot_at: str | None,
) -> EntryChangeNotice | None:
    if len(cells) < 10 or _has_no_data(cells):
        return None
    race_date = _normalize_race_date(cells[0].text)
    return EntryChangeNotice(
        change_type="jockey_change",
        source_section=section,
        race_date=race_date,
        race_no=_parse_int(cells[1].text),
        chul_no=_parse_int(cells[2].text),
        horse_name=cells[3].text or None,
        horse_no=_linked_id(cells[3], "Horse"),
        old_jockey_name=cells[4].text or None,
        old_jockey_no=_linked_id(cells[4], "Jockey"),
        new_jockey_name=cells[6].text or None,
        new_jockey_no=_linked_id(cells[6], "Jockey"),
        reason=cells[8].text or None,
        announced_at=_normalize_notice_time(cells[9].text, race_date),
        meet=meet,
        source_snapshot_at=source_snapshot_at,
    )


def parse_entry_change_bulletin_html(
    html: str,
    *,
    meet: int | None = None,
    source_snapshot_at: str | None = None,
) -> tuple[EntryChangeNotice, ...]:
    """Parse KRA entry-change bulletin rows into conservative structured facts."""

    parser = _EntryChangeBulletinHTMLParser()
    parser.feed(html)

    notices: list[EntryChangeNotice] = []
    for section, cells in parser.rows:
        if "말취소" in section:
            notice = _parse_cancelled_row(
                section,
                cells,
                meet=meet,
                source_snapshot_at=source_snapshot_at,
            )
        elif "기수변경" in section:
            notice = _parse_jockey_change_row(
                section,
                cells,
                meet=meet,
                source_snapshot_at=source_snapshot_at,
            )
        else:
            notice = None
        if notice is not None:
            notices.append(notice)
    return tuple(notices)


def parse_entry_change_bulletin_response(
    response: RawSourceResponse,
    *,
    meet: int | None = None,
) -> tuple[EntryChangeNotice, ...]:
    return parse_entry_change_bulletin_html(
        response.text,
        meet=meet,
        source_snapshot_at=response.fetched_at,
    )
