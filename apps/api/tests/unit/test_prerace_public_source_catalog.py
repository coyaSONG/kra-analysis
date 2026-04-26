from infrastructure.prerace_sources.catalog import (
    CONNECTOR_REGISTRY,
    FREE_PUBLIC_SOURCE_SPECS,
    list_free_public_sources,
)


def test_free_public_source_catalog_has_expected_core_sources():
    source_ids = {spec.source_id for spec in FREE_PUBLIC_SOURCE_SPECS}

    assert {
        "entry_meeting_list",
        "entry_race_card",
        "entry_change_bulletin",
        "track_status",
    }.issubset(source_ids)
    assert len(source_ids) == len(FREE_PUBLIC_SOURCE_SPECS)


def test_every_source_is_authless_and_has_registered_connector():
    for spec in FREE_PUBLIC_SOURCE_SPECS:
        assert spec.requires_auth is False
        assert spec.source_id in CONNECTOR_REGISTRY


def test_list_free_public_sources_returns_catalog_tuple():
    assert list_free_public_sources() == FREE_PUBLIC_SOURCE_SPECS
