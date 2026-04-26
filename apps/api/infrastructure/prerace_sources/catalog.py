"""Catalog and registry for authless public prerace sources."""

from __future__ import annotations

from infrastructure.prerace_sources.base import PublicSourceSpec
from infrastructure.prerace_sources.changes import (
    ENTRY_CHANGE_BULLETIN_SPEC,
    EntryChangeConnector,
)
from infrastructure.prerace_sources.entry import (
    ENTRY_MEETING_LIST_SPEC,
    ENTRY_RACE_CARD_SPEC,
    EntryMeetingListConnector,
    EntryRaceCardConnector,
)
from infrastructure.prerace_sources.profiles import (
    HORSE_PROFILE_SPEC,
    HORSE_TRAINING_SPEC,
    JOCKEY_ACTIVE_LIST_SPEC,
    OWNER_PROFILE_LIST_SPEC,
    TRAINER_PROFILE_LIST_SPEC,
    HorseProfileConnector,
    HorseTrainingStateConnector,
    JockeyActiveListConnector,
    OwnerProfileListConnector,
    TrainerProfileListConnector,
)
from infrastructure.prerace_sources.track import TRACK_STATUS_SPEC, TrackStatusConnector

FREE_PUBLIC_SOURCE_SPECS: tuple[PublicSourceSpec, ...] = (
    ENTRY_MEETING_LIST_SPEC,
    ENTRY_RACE_CARD_SPEC,
    ENTRY_CHANGE_BULLETIN_SPEC,
    TRACK_STATUS_SPEC,
    HORSE_PROFILE_SPEC,
    HORSE_TRAINING_SPEC,
    JOCKEY_ACTIVE_LIST_SPEC,
    TRAINER_PROFILE_LIST_SPEC,
    OWNER_PROFILE_LIST_SPEC,
)

CONNECTOR_REGISTRY = {
    ENTRY_MEETING_LIST_SPEC.source_id: EntryMeetingListConnector,
    ENTRY_RACE_CARD_SPEC.source_id: EntryRaceCardConnector,
    ENTRY_CHANGE_BULLETIN_SPEC.source_id: EntryChangeConnector,
    TRACK_STATUS_SPEC.source_id: TrackStatusConnector,
    HORSE_PROFILE_SPEC.source_id: HorseProfileConnector,
    HORSE_TRAINING_SPEC.source_id: HorseTrainingStateConnector,
    JOCKEY_ACTIVE_LIST_SPEC.source_id: JockeyActiveListConnector,
    TRAINER_PROFILE_LIST_SPEC.source_id: TrainerProfileListConnector,
    OWNER_PROFILE_LIST_SPEC.source_id: OwnerProfileListConnector,
}


def list_free_public_sources() -> tuple[PublicSourceSpec, ...]:
    return FREE_PUBLIC_SOURCE_SPECS
