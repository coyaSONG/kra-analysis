"""Dated official HTML evidence, separate from API identity and training approval."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser

from shared.kra_race_identity import MEET_NAMES, validate_race_identity

DETAIL_CAPTION = "\uacbd\uc8fc\uc0c1\uc138\uc131\uc801\uc744"
TIME_CAPTION = "\uacbd\uc8fc\uc131\uc801\uc744"
LIST_CAPTION = "\uacbd\uc8fc\uc131\uc801\ud45c \ub9ac\uc2a4\ud2b8\ub97c"
HEADER = re.compile(
    r"(20[0-9]{2})\uB144\s*([0-9]{2})\uC6D4\s*([0-9]{2})\uC77C"
    r"\s*\([^)]*\)\s*\uC81C\s*([0-9]+)\uACBD\uC8FC\s*(\S+)"
)
HORSE = re.compile(r"javascript:goHorse\('([0-9]+)','([0-9]+)'\);?")


@dataclass
class Cell:
    text: str = ""
    links: list[str] = field(default_factory=list)
    link_labels: list[str] = field(default_factory=list)
    tag: str = "td"
    span: bool = False


@dataclass
class Table:
    caption: str = ""
    rows: list[list[Cell]] = field(default_factory=list)
    closed: bool = False
    invalid: bool = False


class Tables(HTMLParser):
    """Preserve all table rows, including blank ranks and unlinked horses."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = []
        self.table = self.row = self.cell = None
        self.caption = False
        self.ignored = 0
        self.link_index = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "style"):
            self.ignored += 1
        if tag == "table":
            if self.table is not None:
                raise ValueError("nested_official_table")
            self.table = Table()
            self.tables.append(self.table)
        elif self.table is not None:
            if tag == "caption":
                self.caption = True
            elif tag == "tr":
                self.table.invalid |= self.row is not None
                self.row = []
            elif tag in ("td", "th"):
                self.table.invalid |= self.row is None or self.cell is not None
                self.cell = Cell(
                    tag=tag,
                    span=any(attrs.get(k, "1") != "1" for k in ("rowspan", "colspan")),
                )
            elif tag == "a" and self.cell is not None:
                self.cell.links.append(attrs.get("href", ""))
                self.cell.link_labels.append("")
                self.link_index = len(self.cell.link_labels) - 1
            elif tag == "br" and self.cell is not None:
                self.cell.text += " "

    def handle_data(self, data):
        if self.ignored:
            return
        if self.table is not None:
            if self.caption:
                self.table.caption += data
            if self.cell is not None:
                self.cell.text += data
                if self.link_index is not None:
                    self.cell.link_labels[self.link_index] += data

    def handle_endtag(self, tag):
        if tag == "a":
            self.link_index = None
        if tag in ("script", "style"):
            self.ignored = max(0, self.ignored - 1)
        if self.table is None:
            return
        if tag in ("td", "th"):
            if self.cell is None or self.row is None:
                self.table.invalid = True
            else:
                self.cell.text = " ".join(self.cell.text.split())
                self.row.append(self.cell)
            self.cell = None
            self.link_index = None
        elif tag == "tr":
            if self.row is None or self.cell is not None:
                self.table.invalid = True
            else:
                self.table.rows.append(self.row)
            self.row = self.cell = None
        elif tag == "caption":
            self.caption = False
        elif tag == "table":
            self.table.invalid |= self.row is not None or self.cell is not None
            self.table.closed = True
            self.table = None


def tables(html):
    parser = Tables()
    parser.feed(html)
    parser.close()
    return parser.tables


def selected(items, caption):
    matches = [t for t in items if t.caption.strip().startswith(caption)]
    if len(matches) != 1 or not matches[0].closed or matches[0].invalid:
        raise ValueError("missing_or_malformed_official_table")
    return matches[0]


def integer(value, maximum=20):
    if not re.fullmatch(r"[0-9]+", str(value)) or not 1 <= int(value) <= maximum:
        raise ValueError("invalid_official_identifier")
    return int(value)


def parse_detail(html: str) -> dict:
    items = tables(html)
    headers = [
        HEADER.fullmatch(c.text)
        for t in items
        if t.closed and not t.invalid
        for row in t.rows
        for c in row
    ]
    headers = [h for h in headers if h]
    if not headers:
        return {"event_support": "unknown", "reason": "missing_dated_body", "rows": []}
    if len(headers) != 1:
        raise ValueError("ambiguous_official_event")
    year, month, day, number, venue = headers[0].groups()
    meet = MEET_NAMES.get(venue)
    if meet is None:
        raise ValueError("unknown_official_physical_venue")
    date, number = year + month + day, integer(number)
    validate_race_identity(meet, date, number)
    detail = selected(items, DETAIL_CAPTION)
    timings = [t for t in items if t.caption.strip().startswith(TIME_CAPTION)]
    if not timings or any(not t.closed or t.invalid for t in timings):
        raise ValueError("missing_or_malformed_official_timing_table")
    rows, gates, horses = [], set(), set()
    for index, row in enumerate(detail.rows):
        if row and all(c.tag == "th" for c in row):
            continue
        if len(row) < 3 or any(c.span for c in row):
            raise ValueError("incomplete_official_roster_row")
        gate = integer(row[1].text)
        links = [HORSE.fullmatch(link) for link in row[2].links]
        if len(links) != 1 or links[0] is None:
            raise ValueError("missing_official_horse_id")
        horse = str(integer(links[0][1], 99_999_999))
        if gate in gates or horse in horses:
            raise ValueError("duplicate_official_roster_member")
        gates.add(gate)
        horses.add(horse)
        rows.append(
            {
                "chul_no": gate,
                "horse_id": horse,
                "rank_text": row[0].text,
                "row_index": index,
                "time_text": None,
            }
        )
    if not rows:
        raise ValueError("empty_official_roster")
    for table_index, timing in enumerate(timings):
        times = {}
        for index, row in enumerate(timing.rows):
            if row and all(c.tag == "th" for c in row):
                continue
            if len(row) < 3 or any(c.span for c in row):
                raise ValueError("incomplete_official_timing_row")
            gate = integer(row[1].text)
            if gate in times:
                raise ValueError("duplicate_official_timing_gate")
            times[gate] = (row[0].text, row[-1].text, index)
        if set(times) != gates:
            raise ValueError("official_timing_roster_mismatch")
        for row in rows:
            rank, time, index = times[row["chul_no"]]
            if row["rank_text"] != rank:
                raise ValueError("official_tables_rank_disagreement")
            if row["time_text"] is not None and row["time_text"] != time:
                raise ValueError("official_tables_time_disagreement")
            row["time_text"] = time
            row.setdefault("timing_locations", []).append(
                {"table_index": table_index, "row_index": index}
            )
    return {
        "event_support": "confirmed",
        "race_id": f"{date}_{meet}_{number}",
        "event_kind": "regular_race_result_page",
        "rows": rows,
    }


def parse_list(html: str) -> list[dict]:
    table = selected(tables(html), LIST_CAPTION)
    result = []
    for row in table.rows:
        if row and all(c.tag == "th" for c in row):
            continue
        if len(row) != 4 or any(c.span for c in row):
            raise ValueError("malformed_official_list_row")
        date = re.match(r"(20[0-9]{2})/([0-9]{2})/([0-9]{2})", row[2].text)
        meet = MEET_NAMES.get(row[1].text)
        if date is None or meet is None:
            raise ValueError("missing_official_list_identity")
        day = "".join(date.groups())
        # Include void-race links too: they may use #open instead of detail URLs.
        numbers = []
        for label in row[3].link_labels:
            match = re.match(r"^\s*([0-9]+)(?:\s|$)", label)
            if match:
                numbers.append(match[1])
        if not numbers or len(set(numbers)) != len(numbers):
            raise ValueError("ambiguous_official_list_numbers")
        for n in numbers:
            number = integer(n)
            validate_race_identity(meet, day, number)
            result.append(
                {
                    "race_id": f"{day}_{meet}_{number}",
                    "list_order": integer(row[0].text, 100000),
                }
            )
    return result


def seconds(text):
    match = re.fullmatch(r"([0-9]+):([0-5][0-9]\.[0-9])", text or "")
    if not match:
        return None
    return Decimal(match[1]) * 60 + Decimal(match[2])


def reconcile_group(records: list[dict], official: dict) -> dict:
    if not records or len({r["race_id"] for r in records}) != 1:
        raise ValueError("invalid_official_comparison_group")
    race_id = records[0]["race_id"]
    output = {
        "race_id": race_id,
        "official_event_support": "unknown",
        "roster_support": "incomplete",
        "rows": [],
        "reason_codes": [],
    }
    if official["event_support"] != "confirmed":
        output["reason_codes"] = [official["reason"]]
        return output
    if official["race_id"] != race_id:
        output.update(
            official_event_support="conflict",
            reason_codes=["official_body_identity_mismatch"],
        )
        return output
    output["official_event_support"] = "confirmed"
    api = {(r["chul_no"], r["horse_id"]): r for r in records}
    web = {(r["chul_no"], r["horse_id"]): r for r in official["rows"]}
    if len(api) != len(records) or len(web) != len(official["rows"]):
        raise ValueError("duplicate_official_comparison_member")
    if api.keys() != web.keys():
        output.update(roster_support="mismatch", reason_codes=["whole_roster_mismatch"])
        output["api_only"] = sorted(api.keys() - web.keys())
        output["official_only"] = sorted(web.keys() - api.keys())
        return output
    output["roster_support"] = "exact"
    for key, record in sorted(api.items()):
        row = web[key]
        ranked = record["evidence"] == "ranked_finish_observed"
        rank_support = time_support = "not_checked"
        if ranked:
            rank_support = (
                "supported"
                if str(record["raw_ord"]) == row["rank_text"]
                else "conflict"
            )
            try:
                api_time = Decimal(str(record["raw_rc_time"]))
            except InvalidOperation:
                api_time = None
            time_support = (
                "supported" if api_time == seconds(row["time_text"]) else "conflict"
            )
        output["rows"].append(
            {
                "horse_id": key[1],
                "chul_no": key[0],
                "rank_support": rank_support,
                "time_support": time_support,
                "status_support": "not_checked",
                "ranked_feature_supported": ranked
                and rank_support == time_support == "supported",
                "event_linked_api_unresolved": not ranked,
                "official_row": row,
            }
        )
    return output
