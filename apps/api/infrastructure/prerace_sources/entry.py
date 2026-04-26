"""Authless entry-related public KRA source connectors."""

from __future__ import annotations

from typing import Any

from infrastructure.prerace_sources.base import (
    BasePublicSourceConnector,
    PublicSourceSpec,
    SourceRequest,
    validate_meet,
)

KRA_RACE_HOST = "https://race.kra.co.kr"

ENTRY_MEETING_LIST_SPEC = PublicSourceSpec(
    source_id="entry_meeting_list",
    name="출전상세정보 목록",
    host=KRA_RACE_HOST,
    path="/chulmainfo/ChulmaDetailInfoList.do",
    method="GET",
    content_kind="html",
    description="주간 출전정보 목록과 오늘의경주 PDF 링크를 제공하는 공개 페이지",
    operational_tier="hard_required",
    update_hint="출전정보 및 PDF 공개시각: 매주 수 17:00",
    default_query={"Act": "02", "Sub": "1"},
)

ENTRY_RACE_CARD_SPEC = PublicSourceSpec(
    source_id="entry_race_card",
    name="출전표 상세 카드",
    host=KRA_RACE_HOST,
    path="/chulmainfo/chulmaDetailInfoChulmapyo.do",
    method="POST",
    content_kind="html",
    description="경주일/경주번호 기준 상세 출전표를 반환하는 공개 폼 엔드포인트",
    operational_tier="hard_required",
)


class EntryMeetingListConnector(BasePublicSourceConnector):
    spec = ENTRY_MEETING_LIST_SPEC

    def build_request(self, **kwargs: Any) -> SourceRequest:
        meet = int(kwargs["meet"])
        params = dict(self.spec.default_query)
        params["meet"] = validate_meet(meet)
        return self.spec.method, self.spec.url, params, None


class EntryRaceCardConnector(BasePublicSourceConnector):
    spec = ENTRY_RACE_CARD_SPEC

    def build_request(self, **kwargs: Any) -> SourceRequest:
        meet = int(kwargs["meet"])
        race_date = str(kwargs["race_date"])
        race_no = int(kwargs["race_no"])
        data = {
            "Act": "02",
            "Sub": "1",
            "meet": validate_meet(meet),
            "rcDate": race_date,
            "rcNo": str(race_no),
        }
        return self.spec.method, self.spec.url, None, data
