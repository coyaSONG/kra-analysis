from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from shared.prerace_entry_preprocessing_schema import (  # noqa: E402
    ALL_COLUMNS,
    CANONICAL_STORAGE_ENCODING,
    CANONICAL_STORAGE_RELATIVE_PATH,
    FIELD_GROUPS,
    PRIORITY_GRADES,
    REQUIRED_COLUMNS,
    RULE_SCHEMA_VERSION,
    csv_header,
)


def test_rule_schema_version_is_fixed():
    assert RULE_SCHEMA_VERSION == "prerace-entry-preprocessing-rules-v1"


def test_required_columns_cover_sub_ac_contract():
    required = set(REQUIRED_COLUMNS)
    assert "field_path" in required
    assert "allowed_range" in required
    assert "correction_priority" in required
    assert "replacement_priority" in required
    assert "exclusion_priority" in required
    assert "generated_flags" in required


def test_enum_sets_remain_explicit():
    assert FIELD_GROUPS == ("core_card", "optional_card", "derived", "detail_block")
    assert PRIORITY_GRADES == ("P0", "P1", "P2")


def test_csv_template_header_matches_declared_column_order():
    template_path = (
        Path(__file__).resolve().parents[3] / CANONICAL_STORAGE_RELATIVE_PATH
    )
    with template_path.open(encoding=CANONICAL_STORAGE_ENCODING, newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)

    assert tuple(header) == ALL_COLUMNS
    assert ",".join(header) == csv_header()


def test_rule_table_covers_core_and_soft_fail_fields():
    template_path = (
        Path(__file__).resolve().parents[3] / CANONICAL_STORAGE_RELATIVE_PATH
    )
    with template_path.open(encoding=CANONICAL_STORAGE_ENCODING, newline="") as handle:
        rows = list(csv.DictReader(handle))

    field_paths = {row["field_path"] for row in rows}
    assert {
        "horses[].chul_no",
        "horses[].hr_no",
        "horses[].wg_budam",
        "horses[].win_odds",
        "horses[].plc_odds",
        "horses[].weight_delta",
        "horses[].training",
    } <= field_paths
    assert rows
    assert all(row["rule_schema_version"] == RULE_SCHEMA_VERSION for row in rows)
