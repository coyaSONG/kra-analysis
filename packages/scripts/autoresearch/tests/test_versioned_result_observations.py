"""An observed combination never erases exceptions or implies future accuracy."""

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.official_result_support import parse_detail

from autoresearch import versioned_result_observations as observations
from autoresearch.observed_history_seed import digest, save
from autoresearch.tests.test_official_history_support import captured, html, records

RACE = "20261010_3_1"


def pair():
    api = [{**r, "raw_ord_bigo": "-"} for r in records()]
    return api, parse_detail(html(api))


def test_unique_observation_is_numeric_unordered_not_final_or_accuracy():
    api, web = pair()
    result = observations.observe_race(RACE, 3, api, web)
    assert result["status"] == "unique_top3_observed"
    assert result["observed_top3_horse_ids"] == ["101", "102", "103"]
    assert not result["official_finality_verified"]
    assert not result["settlement_policy_verified"]
    assert "accuracy" not in result
    assert result == observations.observe_race(RACE, 3, list(reversed(api)), web)


def test_lower_blank_row_and_schedule_difference_are_preserved():
    api, web = pair()
    api.append(
        {
            **api[0],
            "chul_no": 4,
            "horse_id": "104",
            "raw_ord": 94,
            "raw_ord_bigo": "excluded",
            "raw_rc_time": 0,
            "evidence": "unresolved",
        }
    )
    web["rows"].append(
        {"chul_no": 4, "horse_id": "104", "rank_text": "", "time_text": ""}
    )
    result = observations.observe_race(RACE, 5, api, web)
    assert result["status"] == "unique_top3_observed"
    assert not result["schedule_count_agrees"]
    assert len(result["api_records"]) == len(result["comparison"]["rows"]) == 4
    assert result["exception_notes"] == {"excluded": 1}
    assert "unresolved_runner_status" in result["api_diagnostic"]["blockers"]


@pytest.mark.parametrize("change", ["rank", "time", "date", "roster", "unresolved"])
def test_any_whole_source_conflict_blocks_observed_combination(change):
    api, web = pair()
    if change == "rank":
        web["rows"][2]["rank_text"] = "4"
    elif change == "time":
        web["rows"][0]["time_text"] = "1:00.9"
    elif change == "date":
        web["race_id"] = "20261011_3_1"
    elif change == "roster":
        web["rows"].pop()
    else:
        api[0]["evidence"] = "unresolved"
    result = observations.observe_race(RACE, 3, api, web)
    assert result["status"] == "source_conflict"
    assert result["observed_top3_horse_ids"] is None


@pytest.mark.parametrize("ranks", [[1, 1, 3], [1, 2, 2], [1, 2, 4], [1, 2, 3, 3]])
def test_ties_are_unresolved_even_when_an_unordered_set_might_be_possible(ranks):
    api = [
        {**records()[0], "chul_no": i, "horse_id": str(100 + i), "raw_ord": rank}
        for i, rank in enumerate(ranks, 1)
    ]
    result = observations.observe_race(RACE, len(api), api, parse_detail(html(api)))
    assert result["status"] == "top3_unresolved"
    assert result["observed_top3_horse_ids"] is None


def test_api_void_notes_and_blank_official_ranks_are_not_automatic_settlement():
    api, web = pair()
    for row in api:
        row.update(
            raw_ord=98,
            raw_ord_bigo="\uacbd\uc8fc\ubd88\uc131\ub9bd",
            evidence="unresolved",
        )
    for row in web["rows"]:
        row.update(rank_text="", time_text="")
    result = observations.observe_race(RACE, 3, api, web)
    assert result["status"] == "void_reported_no_top3"
    assert result["api_all_rows_void_text_observed"]
    assert result["html_all_rank_time_blank"]
    assert result["exception_notes"] == {"\uacbd\uc8fc\ubd88\uc131\ub9bd": 3}
    assert result["comparison"]["roster_support"] == "exact"
    assert result["official_finality_verified"] is False
    assert result["settlement_policy_verified"] is False


def test_unresolved_api_top_rank_is_not_ignored_behind_blank_official_row():
    api, web = pair()
    api.append(
        {
            **api[0],
            "chul_no": 4,
            "horse_id": "104",
            "raw_ord": 3,
            "raw_rc_time": 0,
            "evidence": "unresolved",
        }
    )
    web["rows"].append(
        {"chul_no": 4, "horse_id": "104", "rank_text": "", "time_text": ""}
    )
    result = observations.observe_race(RACE, 4, api, web)
    assert result["status"] == "top3_unresolved"
    assert result["observed_top3_horse_ids"] is None


def test_blank_ranks_without_void_note_do_not_invent_void():
    api, web = pair()
    for row in api:
        row.update(raw_ord=98, evidence="unresolved")
    for row in web["rows"]:
        row.update(rank_text="", time_text="")
    result = observations.observe_race(RACE, 3, api, web)
    assert result["status"] == "no_top3_reason_unknown"
    assert not result["api_all_rows_void_text_observed"]


def test_explicit_void_and_normal_finish_never_approve_top3():
    api, web = pair()
    api[0]["raw_ord_bigo"] = observations.VOID_NOTE
    result = observations.observe_race(RACE, 3, api, web)
    assert result["status"] == "source_conflict"
    assert result["reasons"] == ["void_note_with_finish_observation"]
    assert result["observed_top3_horse_ids"] is None


def test_lower_rank_conflict_is_not_hidden_by_a_top3_only_join():
    api, web = pair()
    api.append({**api[0], "chul_no": 4, "horse_id": "104", "raw_ord": 4})
    web["rows"].append(
        {"chul_no": 4, "horse_id": "104", "rank_text": "5", "time_text": "1:00.1"}
    )
    result = observations.observe_race(RACE, 4, api, web)
    assert result["status"] == "source_conflict"
    assert result["observed_top3_horse_ids"] is None


def test_missing_sources_and_extras_never_change_population():
    api, web = pair()
    extra = "20261010_3_4"
    result = observations.project_population(
        {RACE: 3, "20261010_3_2": 4, "20261010_3_3": 5},
        api + [{**r, "race_id": extra} for r in api],
        {RACE: web, extra: {**web, "race_id": extra}},
    )
    assert len(result["ledger"]) == result["scheduled_race_count"] == 3
    assert result["status_counts"] == {"source_missing": 2, "unique_top3_observed": 1}
    assert result["extra_api_races"] == result["extra_official_races"] == [extra]
    assert not result["counts_as_70_percent_evidence"]
    assert result["prediction_evaluation"].startswith("not_performed")


def test_changed_result_is_a_separate_observation_not_overwritten_truth():
    api, web = pair()
    before = observations.observe_race(RACE, 3, api, web)
    changed_api, changed_web = copy.deepcopy(api), copy.deepcopy(web)
    changed_api[0]["horse_id"] = changed_web["rows"][0]["horse_id"] = "999"
    after = observations.observe_race(RACE, 3, changed_api, changed_web)
    assert before["observed_top3_horse_ids"] == ["101", "102", "103"]
    assert after["observed_top3_horse_ids"] == ["102", "103", "999"]


def test_duplicates_invalid_population_and_missing_event_fail_closed():
    api, web = pair()
    with pytest.raises(ValueError, match="duplicate_result_population_runner"):
        observations.project_population({RACE: 3}, api + [api[0]], {RACE: web})
    with pytest.raises(ValueError, match="empty_result_population"):
        observations.project_population({}, api, {})
    with pytest.raises(ValueError, match="invalid_scheduled_runner_count"):
        observations.observe_race(RACE, True, api, web)
    result = observations.observe_race(
        RACE, 3, api, {"event_support": "unknown", "reason": "blank", "rows": []}
    )
    assert result["status"] == "source_missing"
    assert result["reasons"] == ["blank"]


def replay_fixture(tmp_path, monkeypatch):
    root, path, sha, _, directory, receipt = captured(tmp_path)
    plan = {
        "format_version": observations.FORMAT,
        "race_dates": ["20261010"],
        "schedule_capture": str(tmp_path / "schedule.json"),
        "schedule_sha256": "a" * 64,
        "seed_root": str(root),
        "seed_path": str(path),
        "seed_sha256": sha,
        "official_directory": str(directory),
        "official_archive_sha256": receipt["sha256"],
    }
    monkeypatch.setattr(
        observations,
        "replay_schedule_snapshot",
        lambda *a, **k: {
            "capture_manifest_sha256": "a" * 64,
            "status": "reconciled",
            "source_failures": [],
            "races": [
                {"race_id": RACE, "source_observations": {"national": {"runners": 3}}}
            ],
        },
    )
    pp = tmp_path / "observation-plan.json"
    ps = save(pp, plan)
    return pp, ps, directory


def test_cli_replays_original_sources_and_refuses_overwrite(
    tmp_path, monkeypatch, capsys
):
    path, sha, _ = replay_fixture(tmp_path, monkeypatch)
    result = observations.replay_plan(path, sha)
    assert result["status_counts"] == {"unique_top3_observed": 1}
    assert result["ledger"][0]["official_source"]["capture"]["raw"]["sha256"]
    assert len(result["ledger"][0]["result_observation_id"]) == 64
    assert result["ledger"][0]["publisher_revision_id"] is None
    assert result["observation_policy_sha256"] == observations.value_hash(
        observations.POLICY_RULES
    )
    output = tmp_path / "report.json"
    args = ["--plan", str(path), "--plan-sha256", sha, "--output", str(output)]
    capsys.readouterr()
    assert observations.main(args) == 0
    assert json.loads(output.read_bytes()) == result
    assert json.loads(capsys.readouterr().out)["report_sha256"] == digest(
        output.read_bytes()
    )
    with pytest.raises(FileExistsError):
        observations.main(args)


def test_plan_and_raw_pins_are_enforced(tmp_path, monkeypatch):
    path, sha, directory = replay_fixture(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match="plan_pin_mismatch"):
        observations.replay_plan(path, "0" * 64)
    raw = next(directory.glob("*.html"))
    raw.write_bytes(raw.read_bytes() + b" ")
    with pytest.raises(ValueError, match="pin_mismatch"):
        observations.replay_plan(path, sha)


def test_schedule_pin_precedes_source_replay(tmp_path, monkeypatch):
    path, _, _ = replay_fixture(tmp_path, monkeypatch)
    plan = json.loads(path.read_bytes())
    plan["schedule_sha256"] = "b" * 64
    other = tmp_path / "wrong-plan.json"
    sha = save(other, plan)
    with pytest.raises(ValueError, match="schedule_pin_mismatch"):
        observations.replay_plan(other, sha)
