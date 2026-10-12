"""HTML observations remain separate from dual-format support and PIT approval."""

import asyncio
import copy
import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.official_result_support import LIST_CAPTION

from autoresearch import official_history_catalog as c
from autoresearch import official_history_support as support
from autoresearch.tests.test_official_history_support import html, records


def capture(tmp_path, *, wrong_date=False, fail=False, notice=False, repeat=False):
    discovery, directory = tmp_path / "discovery", tmp_path / "catalog"

    def handler(request):
        params = request.url.params
        meet = params["meet"]
        venue = {"1": "\uc11c\uc6b8", "2": "\uc81c\uc8fc", "3": "\ubd80\uacbd"}[meet]
        if "pageIndex" in params:
            page = "1" if repeat else params["pageIndex"]
            warning = "\uacbd\uc8fc\ubd88\uc131\ub9bd" if notice else ""
            text = f'<table><caption>{LIST_CAPTION}</caption><tr><td>{page}</td><td>{venue}</td><td>2026/06/0{page}</td><td><a href="#open">1 detail</a>{warning}</td></tr></table>'
        else:
            if fail:
                return httpx.Response(503)
            day = "20260609" if wrong_date else params["realRcDate"]
            text = html(records(), date=day, venue=venue)
        return httpx.Response(
            200, text=text, headers={"content-type": "text/html; charset=utf-8"}
        )

    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            found = await support.collect(
                discovery, {"records": []}, "a" * 64, client=client, delay=0
            )
            detail = await c.collect(
                directory,
                discovery,
                found["sha256"],
                "20260601",
                "20260604",
                client=client,
                delay=0,
            )
        return found, detail

    found, detail = asyncio.run(go())
    return directory, detail["index_sha256"], detail["sha256"], discovery


def test_real_capture_replay_and_no_approval(tmp_path):
    args = capture(tmp_path)
    result = c.replay(*args)
    assert result["status_counts"] == {"confirmed": 12}
    assert len(result["records"]) == result["numeric_rank_time_rows"] == 36
    for flag in (
        "api_corroboration_verified",
        "training_approved",
        "historical_pre_race_availability_verified",
        "counts_as_70_percent_evidence",
    ):
        assert result[flag] is False
    assert result["source_tier"] == "official_html_only"
    assert all(r["receipt"]["sha256"] for r in result["records"])
    assert all(r["timing_locations"] and r["row_index"] >= 0 for r in result["records"])
    assert all(g["listing"]["receipt"]["sha256"] for g in result["groups"])


def test_list_void_notice_preserves_rows_but_withholds_numeric_history(tmp_path):
    result = c.replay(*capture(tmp_path, notice=True))
    assert result["status_counts"] == {"list_notice_requires_review": 12}
    assert len(result["records"]) == 36
    assert result["numeric_rank_time_rows"] == 0
    assert all(
        g["reason"] == "list_void_notice_scope_unresolved" for g in result["groups"]
    )


def test_repeated_list_pages_rejected(tmp_path):
    with pytest.raises(ValueError, match="duplicate_listing"):
        capture(tmp_path, repeat=True)


@pytest.mark.parametrize("which", ["index", "detail", "discovery"])
def test_tampered_bytes_fail(tmp_path, which):
    args = capture(tmp_path)
    directory, _, _, discovery = args
    path = (
        directory / "index.json"
        if which == "index"
        else next(
            (directory / "details" if which == "detail" else discovery).glob("*.html")
        )
    )
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="pin_mismatch"):
        c.replay(*args)


@pytest.mark.parametrize(
    "kwargs,status",
    [({"wrong_date": True}, "identity_conflict"), ({"fail": True}, "unknown")],
)
def test_bad_details_keep_all_requested_slots(tmp_path, kwargs, status):
    result = c.replay(*capture(tmp_path, **kwargs))
    assert result["status_counts"] == {status: 12}
    assert len(result["groups"]) == 12
    assert result["records"] == []


def baseline():
    return {
        "format_version": "history-coverage-study-v1",
        "strata": {"all": {"runner_rows": 2}},
        "rows": [
            {
                "race_id": "20260901_1_1",
                "horse_id": str(h),
                "chul_no": gate,
                "prior_supported_race_ids": ["20260701_1_1"] if h == 101 else [],
                "prior_supported_ranked_count_90d": int(h == 101),
            }
            for gate, h in enumerate((101, 102), 1)
        ],
    }


def test_prior_day_and_lower_bound_full_roster_no_mutation():
    base = baseline()
    catalog = {
        "records": [
            {
                "race_id": f"{day}_1_1",
                "horse_id": "102",
                "numeric_rank_time_observed": True,
            }
            for day in ("20260602", "20260603", "20260831", "20260901", "20260902")
        ]
    }
    before = copy.deepcopy((base, catalog))
    result = c.compare(base, catalog)
    assert len(result["rows"]) == 2
    assert result["rows"][1]["html_only_prior_race_ids"] == [
        "20260603_1_1",
        "20260831_1_1",
    ]
    assert result["strata"]["all"]["api_with_prior"] == 1
    assert result["strata"]["all"]["combined_with_prior"] == 2
    assert result["strata"]["all"]["html_only_with_prior"] == 1
    assert result["strata"]["all"]["newly_covered_by_html_only"] == 1
    assert (base, catalog) == before


def test_june_extension_cannot_enter_october_forward_90_day_window():
    base = baseline()
    for row in base["rows"]:
        row.update(
            race_id="20261016_1_1",
            prior_supported_race_ids=[],
            prior_supported_ranked_count_90d=0,
        )
    catalog = {
        "records": [
            {
                "race_id": f"{day}_1_1",
                "horse_id": "102",
                "numeric_rank_time_observed": True,
            }
            for day in ("20260601", "20260630", "20260704")
        ]
    }
    result = c.compare(base, catalog)
    assert result["strata"]["all"]["combined_with_prior"] == 0
    assert [(r["race_id"], r["horse_id"], r["chul_no"]) for r in result["rows"]] == [
        (r["race_id"], r["horse_id"], r["chul_no"]) for r in base["rows"]
    ]


def test_unresolved_rank_time_not_used():
    result = c.compare(
        baseline(),
        {
            "records": [
                {
                    "race_id": "20260603_1_1",
                    "horse_id": "102",
                    "numeric_rank_time_observed": False,
                },
            ]
        },
    )
    assert result["strata"]["all"]["newly_covered_by_html_only"] == 0


@pytest.mark.parametrize(
    "change", ["duplicate_history", "duplicate_target", "overlap", "count", "future"]
)
def test_invalid_comparisons_fail(change):
    base = baseline()
    catalog = {
        "records": [
            {
                "race_id": "20260603_1_1",
                "horse_id": "101",
                "numeric_rank_time_observed": True,
            }
        ]
    }
    if change == "duplicate_history":
        catalog["records"].append(catalog["records"][0])
    elif change == "duplicate_target":
        base["rows"].append(base["rows"][0])
    elif change == "overlap":
        catalog["records"][0]["race_id"] = "20260701_1_1"
    elif change == "count":
        base["rows"][0]["prior_supported_ranked_count_90d"] = 2
    else:
        base["rows"][0]["prior_supported_race_ids"] = ["20260901_1_1"]
    with pytest.raises(ValueError):
        c.compare(base, catalog)


def test_changed_index_membership_cannot_pass_replay(tmp_path):
    directory, _, archive_sha, discovery = capture(tmp_path)
    path = directory / "index.json"
    index = json.loads(path.read_bytes())
    index["records"].pop()
    path.write_text(json.dumps(index))
    with pytest.raises(ValueError, match="index_replay_mismatch"):
        c.replay(directory, c.digest(path.read_bytes()), archive_sha, discovery)
