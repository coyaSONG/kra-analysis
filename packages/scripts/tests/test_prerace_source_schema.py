from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.prerace_source_schema import (  # noqa: E402
    DERIVED_SCHEMA_PATHS,
    HARD_REQUIRED_SOURCE_APIS,
    OPTIONAL_SCHEMA_PATHS,
    REQUIRED_SCHEMA_PATHS,
    SCHEMA_VERSION,
    SOFT_REQUIRED_SOURCE_APIS,
    SOURCE_API_REGISTRY,
    SOURCE_FIELD_MAPPINGS,
    mappings_by_schema_path,
    required_mappings,
)


def test_schema_version_is_fixed():
    assert SCHEMA_VERSION == "prerace-source-v1"


def test_required_schema_paths_are_covered_by_mapping_or_derived_fields():
    mapped_paths = set(mappings_by_schema_path())
    uncovered = REQUIRED_SCHEMA_PATHS - mapped_paths - DERIVED_SCHEMA_PATHS
    assert uncovered == set()


def test_optional_extension_paths_are_backed_by_source_mappings():
    mapped_paths = set(mappings_by_schema_path())
    extension_blocks = {
        "horses[].hrDetail",
        "horses[].jkDetail",
        "horses[].trDetail",
        "horses[].jkStats",
        "horses[].owDetail",
        "horses[].training",
    }
    uncovered = extension_blocks - mapped_paths
    assert uncovered == set()
    assert extension_blocks <= OPTIONAL_SCHEMA_PATHS


def test_all_mappings_reference_known_source_apis():
    unknown = {mapping.source_api for mapping in SOURCE_FIELD_MAPPINGS} - set(
        SOURCE_API_REGISTRY
    )
    assert unknown == set()


def test_required_mappings_only_use_declared_hard_required_apis():
    hard_required = set(HARD_REQUIRED_SOURCE_APIS)
    optional_sources = set(SOFT_REQUIRED_SOURCE_APIS)

    required_sources = {mapping.source_api for mapping in required_mappings()}

    assert required_sources <= hard_required | optional_sources
    assert "API214_1" in required_sources
    assert "API72_2" in required_sources
    assert "API189_1" in required_sources
    assert "API9_1" in required_sources
