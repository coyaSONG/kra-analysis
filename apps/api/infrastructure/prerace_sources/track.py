"""Authless public track-status source connectors."""

from __future__ import annotations

from typing import Any

from infrastructure.prerace_sources.base import (
    BasePublicSourceConnector,
    PublicSourceSpec,
    SourceRequest,
    validate_meet,
)
from infrastructure.prerace_sources.entry import KRA_RACE_HOST

TRACK_STATUS_SPEC = PublicSourceSpec(
    source_id="track_status",
    name="경주로 현황",
    host=KRA_RACE_HOST,
    path="/chulmainfo/trackView.do",
    method="GET",
    content_kind="html",
    description="경주로 상태, 함수율 등 당일 트랙 현황을 제공하는 공개 페이지",
    operational_tier="hard_required",
    update_hint="경주 당일 수시 갱신",
    default_query={"Act": "02", "Sub": "4"},
)


class TrackStatusConnector(BasePublicSourceConnector):
    spec = TRACK_STATUS_SPEC

    def build_request(self, **kwargs: Any) -> SourceRequest:
        meet = int(kwargs["meet"])
        params = dict(self.spec.default_query)
        params["meet"] = validate_meet(meet)
        return self.spec.method, self.spec.url, params, None
