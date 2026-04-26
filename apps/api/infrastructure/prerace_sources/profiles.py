"""Authless public profile and training connectors."""

from __future__ import annotations

from typing import Any

from infrastructure.prerace_sources.base import (
    BasePublicSourceConnector,
    PublicSourceSpec,
    SourceRequest,
    validate_meet,
)
from infrastructure.prerace_sources.entry import KRA_RACE_HOST

HORSE_PROFILE_SPEC = PublicSourceSpec(
    source_id="horse_profile",
    name="경주마 프로필",
    host=KRA_RACE_HOST,
    path="/racehorse/ProfileHorsenameKinds.do",
    method="GET",
    content_kind="html",
    description="개별 경주마 프로필과 기본 이력을 제공하는 공개 페이지",
    operational_tier="soft_required",
)

HORSE_TRAINING_SPEC = PublicSourceSpec(
    source_id="horse_training_state",
    name="경주마 조교상태",
    host=KRA_RACE_HOST,
    path="/racehorse/profileTrainState.do",
    method="GET",
    content_kind="html",
    description="개별 경주마 조교 상태를 제공하는 공개 페이지",
    operational_tier="soft_required",
)

JOCKEY_ACTIVE_LIST_SPEC = PublicSourceSpec(
    source_id="jockey_active_list",
    name="현역 기수 목록",
    host=KRA_RACE_HOST,
    path="/jockey/ProfileJockeyListActive.do",
    method="GET",
    content_kind="html",
    description="현역 기수 목록과 프로필 진입점을 제공하는 공개 페이지",
    operational_tier="soft_required",
    default_query={"Act": "08", "Sub": "1"},
)

TRAINER_PROFILE_LIST_SPEC = PublicSourceSpec(
    source_id="trainer_profile_list",
    name="조교사 프로필 목록",
    host=KRA_RACE_HOST,
    path="/trainer/profileTrainerList.do",
    method="GET",
    content_kind="html",
    description="조교사 목록과 프로필 진입점을 제공하는 공개 페이지",
    operational_tier="soft_required",
    default_query={"Act": "09", "Sub": "1"},
)

OWNER_PROFILE_LIST_SPEC = PublicSourceSpec(
    source_id="owner_profile_list",
    name="마주 프로필 목록",
    host=KRA_RACE_HOST,
    path="/owner/profileOwnerList.do",
    method="GET",
    content_kind="html",
    description="마주 목록과 프로필 진입점을 제공하는 공개 페이지",
    operational_tier="soft_required",
    default_query={"Act": "11", "Sub": "1"},
)


class HorseProfileConnector(BasePublicSourceConnector):
    spec = HORSE_PROFILE_SPEC

    def build_request(self, **kwargs: Any) -> SourceRequest:
        meet = int(kwargs["meet"])
        horse_no = str(kwargs["horse_no"])
        params = {"meet": validate_meet(meet), "hrNo": horse_no}
        return self.spec.method, self.spec.url, params, None


class HorseTrainingStateConnector(BasePublicSourceConnector):
    spec = HORSE_TRAINING_SPEC

    def build_request(self, **kwargs: Any) -> SourceRequest:
        meet = int(kwargs["meet"])
        horse_no = str(kwargs["horse_no"])
        params = {"meet": validate_meet(meet), "hrNo": horse_no}
        return self.spec.method, self.spec.url, params, None


class JockeyActiveListConnector(BasePublicSourceConnector):
    spec = JOCKEY_ACTIVE_LIST_SPEC

    def build_request(self, **kwargs: Any) -> SourceRequest:
        meet = int(kwargs["meet"])
        params = dict(self.spec.default_query)
        params["meet"] = validate_meet(meet)
        return self.spec.method, self.spec.url, params, None


class TrainerProfileListConnector(BasePublicSourceConnector):
    spec = TRAINER_PROFILE_LIST_SPEC

    def build_request(self, **kwargs: Any) -> SourceRequest:
        meet = int(kwargs["meet"])
        params = dict(self.spec.default_query)
        params["meet"] = validate_meet(meet)
        return self.spec.method, self.spec.url, params, None


class OwnerProfileListConnector(BasePublicSourceConnector):
    spec = OWNER_PROFILE_LIST_SPEC

    def build_request(self, **kwargs: Any) -> SourceRequest:
        meet = int(kwargs["meet"])
        params = dict(self.spec.default_query)
        params["meet"] = validate_meet(meet)
        return self.spec.method, self.spec.url, params, None
