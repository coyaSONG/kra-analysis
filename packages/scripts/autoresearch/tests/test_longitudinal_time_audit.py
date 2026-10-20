import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from autoresearch import longitudinal_time_audit as audit


def seoul():
    return {
        "seoul": [
            "0:13.6",
            "",
            "",
            "",
            "0:37.4",
            "",
            "1:02.2",
            "0:38.2",
            "0:13.4",
            "1:15.6",
        ]
    }


def busan():
    return {
        "busan_cumulative": [
            "",
            "",
            "0:13.0",
            "0:25.0",
            "0:37.0",
            "0:49.0",
            "1:01.0",
            "1:13.0",
        ],
        "busan_segment": [
            "0:13.0",
            "",
            "",
            "",
            "0:24.0",
            "0:24.0",
            "0:36.0",
            "0:12.0",
            "1:13.0",
        ],
    }


@pytest.mark.parametrize(
    "text,status,seconds",
    [
        ("", "blank", None),
        ("0:00.0", "zero", "0.0"),
        ("1:13.0", "positive", "73.0"),
        ("1:60.0", "malformed", None),
        ("-1", "malformed", None),
        ("NaN", "malformed", None),
        ("73", "malformed", None),
        (None, "malformed", None),
    ],
)
def test_operand_states(text, status, seconds):
    assert audit.operand(text) == {"status": status, "seconds": seconds}


def test_seoul_final_exact_but_initial_is_label_only_and_no_mutation():
    values = seoul()
    before = deepcopy(values)
    result = audit.measure("seoul", 1200, values)
    assert values == before
    assert result["issues"] == []
    assert result["check_counts"] == {"exact": 2}
    assert result["measurements"]["total"] == {
        "status": "positive_total",
        "seconds": "75.6",
    }
    assert result["measurements"]["final_600"] == {
        "status": "exact_endpoint",
        "seconds": "38.2",
    }
    assert (
        result["measurements"]["initial_200"]["status"]
        == "label_only_no_independent_counterpart"
    )


def test_busan_endpoints_not_overlapping_sum():
    result = audit.measure("busan", 1200, busan())
    assert result["issues"] == []
    assert result["check_counts"] == {
        "exact": 5,
        "unsupported_endpoint": 2,
        "missing_value": 1,
    }
    assert result["measurements"]["initial_200"] == {
        "status": "exact_endpoint",
        "seconds": "13.0",
    }
    assert result["measurements"]["final_600"] == {
        "status": "exact_endpoint",
        "seconds": "36.0",
    }


@pytest.mark.parametrize(
    "index,text,reason",
    [
        (7, "0:38.3", "arithmetic_conflict"),
        (4, "0:00.0", "nonpositive_value"),
        (4, "1:20.0", "nonincreasing_clock"),
        (1, "bad", "malformed_operand"),
        (9, "", "invalid_total"),
    ],
)
def test_conflicts_withhold_all_measurements_without_discarding_raw(
    index, text, reason
):
    values = seoul()
    values["seoul"][index] = text
    result = audit.measure("seoul", 1200, values)
    assert reason in result["issues"]
    assert result["raw_time_columns"] == values
    assert all(
        m == {"status": "withheld_conflict", "seconds": None}
        for m in result["measurements"].values()
    )


@pytest.mark.parametrize("index", [4, 7])
def test_missing_endpoint_is_not_zero_or_conflict(index):
    values = seoul()
    values["seoul"][index] = ""
    result = audit.measure("seoul", 1200, values)
    assert result["issues"] == []
    assert result["check_counts"]["missing_value"] == 1
    assert result["measurements"]["final_600"]["seconds"] is None
    assert result["measurements"]["total"]["status"] == "positive_total"


def test_busan_total_conflict_and_unlabelled_span():
    values = busan()
    values["busan_cumulative"][-1] = "1:14.0"
    assert "timing_total_disagreement" in audit.measure("busan", 1200, values)["issues"]
    values = busan()
    values["busan_segment"][1] = "0:10.0"
    assert (
        "unsupported_endpoint_with_value"
        in audit.measure("busan", 1200, values)["issues"]
    )


def test_jeju_never_inherits_pace_semantics():
    result = audit.measure("jeju", 1000, {"jeju": ["0:13.0"] * 7 + ["1:15.0"]})
    assert result["measurements"]["total"]["status"] == "positive_total"
    assert result["check_counts"] == {}
    assert all(
        result["measurements"][m]["status"] == "unverified_jeju_endpoints"
        for m in audit.METRICS[1:]
    )


def test_missing_segment_cannot_hide_reversed_cumulative_clock():
    values = {
        "busan_cumulative": [
            "",
            "0:14.7",
            "0:39.2",
            "1:34.0",
            "1:16.8",
            "1:30.6",
            "1:44.2",
            "1:58.3",
        ],
        "busan_segment": [
            "0:14.7",
            "",
            "0:24.5",
            "0:54.8",
            "",
            "0:27.7",
            "0:41.5",
            "0:14.1",
            "1:58.3",
        ],
    }
    result = audit.measure("busan", 1800, values)
    assert result["check_counts"] == {
        "exact": 6,
        "missing_value": 1,
        "unsupported_endpoint": 1,
    }
    assert result["issues"] == ["cumulative_clock_order_conflict"]
    assert result["exceptions"] == [
        {
            "relation": "cumulative_order",
            "start_m": 1000,
            "end_m": 1200,
            "raw_start": "1:34.0",
            "raw_end": "1:16.8",
            "status": "cumulative_clock_order_conflict",
        }
    ]
    assert all(m["seconds"] is None for m in result["measurements"].values())


@pytest.mark.parametrize("initial", ["0:37.4", "0:40.0"])
def test_equal_or_reversed_known_seoul_clocks_withheld(initial):
    values = seoul()
    values["seoul"][0] = initial
    assert (
        "cumulative_clock_order_conflict"
        in audit.measure("seoul", 1200, values)["issues"]
    )


@pytest.mark.parametrize(
    "kind,values",
    [
        ("other", seoul()),
        ("seoul", {}),
        ("seoul", {"seoul": []}),
        ("busan", {"busan_segment": [""] * 9}),
        ("jeju", seoul()),
    ],
)
def test_invalid_shape_fails_closed(kind, values):
    with pytest.raises(ValueError, match="invalid_measurement_shape"):
        audit.measure(kind, 1200, values)


def row(day, horse="h", meet="1", distance=1200, race=1):
    return {
        "race_id": f"{day}_{meet}_{race}",
        "horse_id": horse,
        "meet": meet,
        "distance_m": distance,
        "tier": "html_only",
        **audit.measure("seoul", distance, seoul()),
    }


def test_full_denominator_pair_rules_and_no_input_mutation():
    rows = [
        row("20260501"),
        row("20260502"),
        row("20260502", race=2),
        row("20260502", "other"),
        row("20260502", meet="3"),
        row("20260502", distance=1400, race=3),
    ]
    before = deepcopy(rows)
    report = audit.summarize(rows)
    assert rows == before
    assert report["rows"] == 6
    assert report["structural_rows_with_verified_measurement_prior"] == {
        "total": 2,
        "initial_200": 0,
        "final_600": 2,
    }
    assert audit.summarize(list(reversed(rows))) == report


@pytest.mark.parametrize("day,count", [("20261028", 1), ("20261029", 0)])
def test_180_inclusive_and_181_excluded(day, count):
    report = audit.summarize([row("20260501"), row(day)])
    assert (
        report["structural_rows_with_verified_measurement_prior"]["final_600"] == count
    )


def test_unknown_layout_row_remains_and_current_must_be_ready():
    rows = [row("20260501"), row("20260502")]
    for value in rows[1]["measurements"].values():
        value.update(status="unsupported_physical_venue", seconds=None)
    report = audit.summarize(rows)
    assert report["rows"] == 2
    assert report["statuses"]["total"]["unsupported_physical_venue"] == 1
    assert report["structural_rows_with_verified_measurement_prior"]["total"] == 0


@pytest.mark.parametrize("horse", ["h", ""])
def test_duplicate_or_missing_identity_rejected(horse):
    with pytest.raises(ValueError, match="duplicate_or_missing"):
        audit.summarize([row("20260501"), row("20260501", horse)])


def test_pinned_inventory_mismatch_stops_before_any_measurements(tmp_path, monkeypatch):
    data = {k: {} for k in ("source_pins", "race_ledger", "sources", "counts", "tiers")}
    content = audit.encoded(data)
    (tmp_path / "report.json").write_bytes(content)
    monkeypatch.setattr(
        audit,
        "REPORT",
        {"path": "report.json", "sha256": audit.inventory.digest(content)},
    )
    changed = deepcopy(data)
    changed["counts"] = {"rows": 1}
    monkeypatch.setattr(audit.inventory, "audit", lambda root: changed)
    with pytest.raises(ValueError, match="inventory_evidence_changed"):
        audit.audit(tmp_path)


def test_no_network_fit_or_scoring_imports():
    import ast

    tree = ast.parse(Path(audit.__file__).read_text())
    names = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    assert names == [
        "collections",
        "datetime",
        "pathlib",
        "autoresearch",
        "autoresearch",
        "autoresearch.restricted_cohort",
    ]


def test_audit_keeps_unknown_layout_and_horse_identity(tmp_path, monkeypatch):
    records = [
        {
            "race_id": "20260501_1_1",
            "horse_id": "h",
            "tier": "html_only",
            "rank": 1,
            "observed_roster_size": 2,
        },
        {
            "race_id": "20260501_4_1",
            "horse_id": "v",
            "tier": "html_only",
            "rank": 2,
            "observed_roster_size": 2,
        },
    ]
    raw = b"original fixture"
    (tmp_path / "raw.html").write_bytes(raw)
    raw_ref = {"path": "raw.html", "sha256": audit.inventory.digest(raw)}
    receipt = audit.encoded({"encoding": "utf-8", "raw": raw_ref})
    (tmp_path / "capture.json").write_bytes(receipt)
    receipt_ref = {"path": "capture.json", "sha256": audit.inventory.digest(receipt)}
    sources = {
        r["race_id"]: {
            "directory": ".",
            "receipt": receipt_ref,
            "raw": raw_ref,
            "layout": {
                "status": "recognized_literal_layout"
                if r["horse_id"] == "h"
                else "unsupported_physical_venue"
            },
        }
        for r in records
    }
    baseline = {
        "source_pins": [],
        "race_ledger": {"histogram": {2: 1, 10: 2}},
        "sources": sources,
        "counts": {},
        "tiers": {"html_only": 2},
        "rows": 2,
        "races": 2,
    }
    content = audit.encoded(baseline)
    (tmp_path / "report.json").write_bytes(content)
    monkeypatch.setattr(
        audit,
        "REPORT",
        {"path": "report.json", "sha256": audit.inventory.digest(content)},
    )
    monkeypatch.setattr(audit.inventory, "audit", lambda root: baseline)
    monkeypatch.setattr(
        audit.inventory,
        "load",
        lambda root: (
            records,
            {r["race_id"]: {"distance_m": 1200} for r in records},
            {},
        ),
    )
    monkeypatch.setattr(audit.arithmetic, "replay_guide", lambda root: {})
    monkeypatch.setattr(
        audit.inventory,
        "parse_detail",
        lambda html: {
            "rows": [
                {"horse_id": "h", "chul_no": 7, "rank_text": "1"},
                {"horse_id": "excluded", "chul_no": 3, "rank_text": "2"},
            ]
        },
    )
    monkeypatch.setattr(
        audit.inventory,
        "tables",
        lambda html: [SimpleNamespace(caption=audit.inventory.TIME_CAPTION)],
    )
    monkeypatch.setattr(
        audit.arithmetic.source,
        "timing_rows",
        lambda *args: {7: seoul()["seoul"], 3: seoul()["seoul"]},
    )
    result = audit.audit(tmp_path)
    assert result["rows"] == 2
    assert [r["horse_id"] for r in result["observations"]] == ["h", "v"]
    assert result["statuses"]["total"] == {
        "positive_total": 1,
        "unsupported_physical_venue": 1,
    }
    assert result["fits"] == result["network_requests"] == 0
    assert result["historical_prerace_verified"] is False
    assert result["training_approved"] is False
    assert result["accuracy"] is None


def test_published_report_retains_population_and_the_anomaly():
    root = Path(__file__).resolve().parents[4]
    raw = (
        root / "docs/research/experiments/2026-10-20-longitudinal-time/report.json"
    ).read_bytes()
    assert (
        audit.inventory.digest(raw)
        == "2ff4ef525c33a6f83e5aa2ecc9f14c9d5942f103386b34d2e4007f4fda1e6f7a"
    )
    report = json.loads(raw)
    assert report["implementation_sha256"] == audit.inventory.digest(
        Path(audit.__file__).read_bytes()
    )
    assert report["rows"] == len(report["observations"]) == 11523
    assert (
        report["races"] == len({r["race_id"] for r in report["observations"]}) == 1156
    )
    assert report["tiers"] == {"dual_supported": 9184, "html_only": 2339}
    for metric in audit.METRICS:
        assert sum(report["statuses"][metric].values()) == 11523
    assert report["issues"] == {"cumulative_clock_order_conflict": 1}
    conflicts = [r for r in report["observations"] if r["issues"]]
    assert [(r["race_id"], r["horse_id"]) for r in conflicts] == [
        ("20260703_3_6", "51248")
    ]
    assert report["structural_rows_with_verified_measurement_prior"] == {
        "total": 5122,
        "initial_200": 1227,
        "final_600": 3179,
    }
    assert report["fits"] == report["network_requests"] == 0
    for flag in (
        "training_approved",
        "historical_prerace_verified",
        "october_16_18_outcomes_loaded",
        "existing_exclusions_changed",
        "counts_as_70_percent_evidence",
    ):
        assert report[flag] is False
