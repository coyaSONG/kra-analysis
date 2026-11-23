"""Read only clock and custody metadata from already selected result sources."""

import sys
from copy import deepcopy
from datetime import timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "docs/research/tools"))

import kra_result_observation_inventory as custody

from autoresearch.observed_history_seed import pin, save
from autoresearch.restricted_cohort import parse_json
from autoresearch.tests import test_kra_walk_forward_fold as cases
from autoresearch.tests import test_kra_whole_card_learning as learning_cases

study = cases.study


def _scope(card):
    return {
        "race_dates": card.protocol["race_dates"],
        "race_ids": sorted(card.races),
        "schedule_sha256": card.input_spec["schedule_sha256"],
    }


def test_complete_clock_inventory_and_later_tail(study, monkeypatch):
    ref = study.plan["training"][0]["result_plan"]
    scope = _scope(study.training[0])
    learning_cases._guard(monkeypatch)
    saved = learning_cases._snapshot(study.root)
    report = custody.inventory(study.root, ref, **scope)
    assert report["result_plan"] == ref
    assert (
        not report["training_approved"]
        and not report["independent_collection_clock_verified"]
    )
    assert report["local_api_requests"]
    assert not report["local_api_request_ordinals_without_selected_pages"]
    assert report["api_pages_without_local_request"] == 0
    assert not report["frozen_races_without_official_detail_request"]
    assert {
        s["key"] for s in report["official_captures"] if s["kind"] == "detail"
    } == set(scope["race_ids"])
    assert b'"observed_top3' not in custody.encoded(report)
    assert b'"horse_id' not in custody.encoded(report)
    assert learning_cases._snapshot(study.root) == saved
    plan = parse_json((study.root / ref["path"]).read_bytes())
    seed = Path(plan["seed_root"])
    next_page = len(report["local_api_requests"]) + 1
    previous = parse_json(
        (seed / "requests" / f"{next_page - 1:06d}.json").read_bytes()
    )
    save(
        seed / "requests" / f"{next_page:06d}.json",
        previous
        | {
            "ordinal": next_page,
            "reserved_at": (
                study.training[0].result_time + timedelta(days=1)
            ).isoformat(),
        },
    )
    assert custody.inventory(study.root, ref, **scope) == report


@pytest.mark.parametrize("key", ["race_dates", "schedule_sha256"])
def test_original_scope_is_checked_before_the_seed_path(study, monkeypatch, key):
    def forbid(*_, **__):
        pytest.fail("different scope must not open the seed")

    monkeypatch.setattr(custody.history, "load_plan", forbid)
    ref = study.plan["training"][0]["result_plan"]
    scope = _scope(study.training[0])
    scope[key] = None
    with pytest.raises(ValueError, match="observation_result_plan_not_original_scope"):
        custody.inventory(study.root, ref, **scope)


def test_missing_api_race_keeps_unattempted_official_detail(study, monkeypatch):
    card = study.training[0]
    loader = cases.results.fake_result_sources
    missing = min(card.races)

    def omit(*args, **kwargs):
        api, web = loader(*args, **kwargs)
        del api[missing], web[missing]
        return api, web

    monkeypatch.setattr(cases.results, "fake_result_sources", omit)
    path, _ = cases.results.seal_results(
        card, "one-missing-api-race", captured_at=card.result_time
    )
    learning_cases._guard(monkeypatch)
    report = custody.inventory(study.root, pin(study.root, path), **_scope(card))
    assert report["frozen_races_without_official_detail_request"] == [missing]
    assert not report["result_version_selection_verified"]


def test_pages_only_match_one_request_in_their_clock_window():
    start = "2099-01-04T11:55:00+00:00"
    end = "2099-01-04T12:00:00+00:00"
    request = {
        "ordinal": 1,
        "day": "20990102",
        "meet": 1,
        "source": "API214",
        "page": 1,
        "reserved_at": "2099-01-04T12:00:01+00:00",
    }
    units = [
        {
            "day": "20990102",
            "meet": 1,
            "captures": [
                {
                    "source": "API214",
                    "pages": [
                        {"page": 1, "started_at": start, "completed_at": end},
                    ],
                }
            ],
        }
    ]
    assert custody._link_pages(deepcopy(units), [request]) == (1, [1])
    request["reserved_at"] = start
    assert custody._link_pages(deepcopy(units), [request]) == (0, [])
    with pytest.raises(ValueError, match="observation_ambiguous_request_binding"):
        custody._link_pages(units, [request, request | {"ordinal": 2}])


def test_recorded_clocks_need_the_whole_fixed_window_not_just_last_observation():
    open_utc = "2099-01-04T12:00:00+00:00"
    close_utc = "2099-01-04T14:00:00+00:00"
    end = "2099-01-04T13:59:59+00:00"
    evidence = {
        "api_units": [{"captures": [{"started_at": open_utc, "completed_at": end}]}],
        "local_api_requests": [{"reserved_at": open_utc}],
        "official_captures": [{"started_at": open_utc, "completed_at": end}],
        "api_pages_without_local_request": 0,
        "local_api_request_ordinals_without_selected_pages": [],
        "frozen_races_without_official_detail_request": [],
    }
    window = {"opens_at": open_utc, "closes_at": "2099-01-04T23:00:00+09:00"}
    assert not custody.window_holds(evidence, **window)
    bad = deepcopy(evidence)
    bad["api_units"][0]["captures"][0]["started_at"] = "2099-01-04T11:59:59Z"
    bad["official_captures"][0]["completed_at"] = close_utc
    bad["api_pages_without_local_request"] = 1
    assert custody.window_holds(bad, **window) == [
        "api_capture_outside_window",
        "official_capture_outside_window",
        "selected_api_page_has_no_window_request",
    ]
