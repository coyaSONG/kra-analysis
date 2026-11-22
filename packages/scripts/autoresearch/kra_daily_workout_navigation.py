"""Read displayed KRA workout form controls without running publisher scripts."""

from __future__ import annotations

import re
from datetime import date
from html.parser import HTMLParser

from autoresearch.kra_daily_workout_source import (
    GROUPS,
    WEEKDAYS,
    _scope,
    group_counts,
    index_count,
    index_path,
)

ALL_LABEL = "\uc804\uccb4\uc120\ud0dd"


class _Control(HTMLParser):
    def __init__(self, html: str, tag: str, invocation: str):
        super().__init__(convert_charrefs=True)
        self.tag = tag
        self.invocation = invocation
        self.in_form = False
        self.in_script = False
        self.scripts = []
        self.labels = []
        self.active = None
        self.feed(html)
        self.close()
        if self.active is not None:
            raise ValueError("unclosed_workout_control")

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "script":
            self.in_script = True
        if tag == "form":
            self.in_form = values.get("name") == "form1"
        if (
            self.in_form
            and tag == self.tag
            and values.get("onclick") == self.invocation
        ):
            if (
                self.active is not None
                or len(attrs) != len(values)
                or "disabled" in values
                or (tag == "a" and values.get("href") != "#KRA")
                or (tag == "button" and values.get("type") != "button")
            ):
                raise ValueError("unverified_workout_control")
            self.active = []

    def handle_data(self, data):
        if self.in_script:
            self.scripts.append(data)
        elif self.active is not None:
            self.active.append(data)

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_script = False
        if tag == "form":
            if self.active is not None:
                raise ValueError("unclosed_workout_control")
            self.in_form = False
        if tag == self.tag and self.active is not None:
            self.labels.append(" ".join("".join(self.active).split()))
            self.active = None

    def require(
        self, label: str, function: str, parameters: str, *statements: str
    ) -> None:
        code = "\n".join(self.scripts)
        declaration = rf"\bfunction\s+{re.escape(function)}\s*\("
        matches = re.findall(declaration + r"([^()]*)\)\s*\{([^{}]*)\}", code)
        if (
            self.labels != [label]
            or len(re.findall(declaration, code)) != 1
            or len(matches) != 1
        ):
            raise ValueError("unverified_workout_control")
        args, body = matches[0]
        lines = (line.strip() for line in body.splitlines())
        actual = tuple(line for line in lines if line and not line.startswith("//"))
        if "".join(args.split()) != parameters or actual != statements:
            raise ValueError("unverified_workout_submit_action")


def dated_group_request(
    html: str, day: date, *, lane: int
) -> tuple[dict[str, str], int]:
    """Accept only the requested date displayed on this saved first page."""
    count = index_count(html, day, lane=lane)
    fields = _scope(html, index_path(lane), lane)
    event, weekday = day.strftime("%Y/%m/%d"), WEEKDAYS[day.weekday()]
    if (
        set(fields)
        != {"Act", "Sub", "meet", "nTotPageRest", "trDate", "trYo", "pageIndex"}
        or not fields["trDate"] == fields["trYo"] == ""
        or fields["pageIndex"] != "1"
        or not (fields["nTotPageRest"] or "").isascii()
        or not fields["nTotPageRest"].isdecimal()
        or not 0 < len(fields["nTotPageRest"]) <= 3
        or int(fields["nTotPageRest"]) < 1
    ):
        raise ValueError("unverified_workout_date_fields")
    control = _Control(html, "a", f"javascript:goPage1('{event}', '{weekday}')")
    control.require(
        f"{event}({weekday})",
        "goPage1",
        "trDate,trYo",
        "var form = document.form1;",
        "form.trDate.value = trDate;",
        "form.trYo.value = trYo;",
        'form.action = "dailyGroupTrainList.do";',
        "form.submit();",
    )
    return {**fields, "trDate": event, "trYo": weekday}, count


def all_detail_request(
    html: str, day: date, *, lane: int, expected_count: int
) -> tuple[dict[str, str], dict[int, int]]:
    """Accept the enabled all-selection control, not a trainer or profile."""
    groups = group_counts(html, day, lane=lane)
    if expected_count < 1 or sum(groups.values()) != expected_count:
        raise ValueError("workout_group_count_changed_since_index")
    fields = _scope(html, GROUPS, lane, day)
    if (
        set(fields)
        != {"Act", "Sub", "meet", "trDate", "trDateReplace", "trName", "trNo", "trYo"}
        or fields["trName"] != ""
        or fields["trNo"] != ""
        or fields["trYo"] not in {"??", WEEKDAYS[day.weekday()]}
    ):
        raise ValueError("unverified_workout_all_detail_fields")
    control = _Control(html, "button", "javascript:goPage2();")
    control.require(
        ALL_LABEL,
        "goPage2",
        "",
        'document.form1.action = "dailyAllTrainDetail.do";',
        "document.form1.submit();",
    )
    return fields, groups
