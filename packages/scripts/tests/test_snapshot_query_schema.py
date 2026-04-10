from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.snapshot_query_schema import (  # noqa: E402
    INPUT_FIELD_SPECS,
    INPUT_REQUIRED_FIELD_PATHS,
    LIST_QUERY_PARAM_NAMES,
    LOOKUP_REQUIRED_FIELDS,
    SNAPSHOT_QUERY_SCHEMA_VERSION,
    SNAPSHOT_QUERY_TIME_BASIS,
    normalize_snapshot_list_query_params,
    normalize_snapshot_lookup_payload,
)


def test_snapshot_lookup_payload_normalizes_alias_fields() -> None:
    normalized = normalize_snapshot_lookup_payload(
        {
            "race_id": "race-1",
            "rcDate": "20250719",
            "entry_finalized_at": "2025-07-19T10:35:00+09:00",
        }
    )

    assert normalized == {
        "race_id": "race-1",
        "race_date": "20250719",
        "entry_snapshot_at": "2025-07-19T10:35:00+09:00",
        "source_filter_basis": SNAPSHOT_QUERY_TIME_BASIS,
        "schema_version": SNAPSHOT_QUERY_SCHEMA_VERSION,
    }


def test_snapshot_lookup_payload_requires_all_required_fields() -> None:
    with pytest.raises(ValueError, match="snapshot lookup requires entry_snapshot_at"):
        normalize_snapshot_lookup_payload(
            {
                "race_id": "race-1",
                "race_date": "20250719",
            }
        )


def test_snapshot_list_query_params_validates_positive_integer_limit() -> None:
    assert normalize_snapshot_list_query_params(
        date_filter="20250719",
        limit="5",
    ) == {
        "date_filter": "20250719",
        "limit": 5,
    }

    with pytest.raises(ValueError, match="must be positive"):
        normalize_snapshot_list_query_params(limit=0)


def test_snapshot_query_schema_catalogs_expected_fields() -> None:
    assert LOOKUP_REQUIRED_FIELDS == ("race_id", "race_date", "entry_snapshot_at")
    assert LIST_QUERY_PARAM_NAMES == ("date_filter", "limit")
    assert INPUT_REQUIRED_FIELD_PATHS == (
        "race_info.race_id",
        "race_info.race_date",
        "race_info.entry_snapshot_at",
    )

    entry_snapshot_field = next(
        spec for spec in INPUT_FIELD_SPECS if spec.param_name == "entry_snapshot_at"
    )
    assert "entry_finalized_at" in entry_snapshot_field.aliases
