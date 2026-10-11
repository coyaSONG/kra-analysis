import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import kra_result_population_audit as audit
from autoresearch.kra_result_population_audit import reconcile_observations
from autoresearch.kra_result_snapshot import collect_result_snapshot


def finish(rank, horse=None, evidence="ranked_finish_observed"):
    return {
        "race_id": "20261010_1_1",
        "chul_no": int(rank),
        "horse_id": horse or str(100 + int(rank)),
        "raw_ord": rank,
        "raw_ord_bigo": None,
        "evidence": evidence,
    }


def test_unique_top3_candidate_is_unordered_and_not_final_truth():
    rows = [finish("2", "20"), finish(3, "3"), finish(1, "100"), finish(4)]
    result = audit.inspect_top3(rows, 4)
    assert result["candidate_top3_horse_ids"] == ["3", "20", "100"]
    assert result["status"] == "ordinary_rank_observation"
    assert result["blockers"] == []
    assert not result["official_finality_verified"]
    assert not result["counts_as_70_percent_evidence"]
    assert audit.inspect_top3(list(reversed(rows)), 4) == result


@pytest.mark.parametrize(
    "ranks,candidate,blocker",
    [
        ([1, 1, 3, 4], None, "duplicate_finish_rank_requires_policy"),
        ([1, 2, 3, 3], None, "missing_or_ambiguous_top3"),
        ([1, 2, 4], None, "missing_or_ambiguous_top3"),
        ([1, 2, 3, 5], ["100", "101", "102"], "nonconsecutive_finish_ranks"),
        (
            [1, 2, 3, 4, 4],
            ["100", "101", "102"],
            "duplicate_finish_rank_requires_policy",
        ),
    ],
)
def test_ties_and_rank_gaps_require_review(ranks, candidate, blocker):
    rows = [finish(rank, str(100 + index)) for index, rank in enumerate(ranks)]
    result = audit.inspect_top3(rows, len(rows))
    assert result["status"] == "requires_review"
    assert result["candidate_top3_horse_ids"] == candidate
    assert blocker in result["blockers"]


@pytest.mark.parametrize("horse", [None, "", "0001", "0", "-1", "a", 1, "123456789"])
def test_invalid_normalized_identity_never_yields_candidate(horse):
    rows = [finish(i) for i in (1, 2, 3)]
    rows[0]["horse_id"] = horse
    result = audit.inspect_top3(rows, 3)
    assert "invalid_horse_identity" in result["blockers"]
    assert result["candidate_top3_horse_ids"] is None


def test_duplicate_horse_never_yields_candidate():
    rows = [finish(i, "123") for i in (1, 2, 3)]
    result = audit.inspect_top3(rows, 3)
    assert "duplicate_horse_identity" in result["blockers"]
    assert result["candidate_top3_horse_ids"] is None


@pytest.mark.parametrize("rank", [True, 1.0, "1.0", None, 0, 21])
def test_invalid_normalized_rank_requires_review(rank):
    rows = [finish(i) for i in (1, 2, 3)]
    rows[0]["raw_ord"] = rank
    result = audit.inspect_top3(rows, 3)
    assert "invalid_finish_rank" in result["blockers"]
    assert result["candidate_top3_horse_ids"] is None


def test_exceptional_runner_is_not_dropped_to_approve_top3():
    rows = [finish(i) for i in (1, 2, 3)] + [finish(94, evidence="unresolved")]
    result = audit.inspect_top3(rows, 3)
    assert result["candidate_top3_horse_ids"] == ["101", "102", "103"]
    assert "runner_count_mismatch" in result["blockers"]
    assert "unresolved_runner_status" in result["blockers"]
    assert result["status"] == "requires_review"


def test_unresolved_duplicate_top_rank_cannot_leave_an_unambiguous_candidate():
    rows = [finish(i) for i in (1, 2, 3)] + [finish(3, "999", "unresolved")]
    result = audit.inspect_top3(rows, 4)
    assert result["candidate_top3_horse_ids"] is None
    assert "duplicate_finish_rank_requires_policy" in result["blockers"]


def test_top3_totals_keep_void_and_missing_races():
    result = reconcile_observations(
        {"20261010_1_1": 3, "20261010_1_2": 1, "20261010_1_3": 3},
        [finish(i) for i in (1, 2, 3)] + [record("20261010_1_2")],
    )
    assert result["top3_observation_counts"] == {
        "ordinary_rank_observation": 1,
        "requires_review": 2,
    }
    assert sum(result["top3_observation_counts"].values()) == 3
    assert len(result["ledger"]) == result["scheduled_race_count"] == 3
    assert result["top3_blocker_counts"]["missing_results"] == 1
    assert not result["counts_as_70_percent_evidence"]


def record(race="20261010_1_1", gate=1, note="경주불성립"):
    return {
        "race_id": race,
        "chul_no": gate,
        "raw_ord_bigo": note,
        "evidence": "unresolved",
    }


def test_void_unknown_rows_stay_in_whole_population_without_scoring():
    result = reconcile_observations(
        {"20261010_1_1": 2, "20261010_1_2": 2}, [record(), record(gate=2)]
    )
    assert result["scheduled_race_count"] == len(result["ledger"]) == 2
    assert result["ledger"][0]["exception_notes"] == {"경주불성립": 2}
    assert result["ledger"][1]["status"] == "missing_results"
    assert not result["reconciled_observation_population"]
    assert not result["counts_as_70_percent_evidence"]


def test_matching_rosters_do_not_approve_actual_starts():
    result = reconcile_observations({"20261010_1_1": 1}, [record()])
    assert result["reconciled_observation_population"]
    assert not result["complete_actual_start_history_verified"]


def test_extra_races_and_count_mismatch_are_reported_not_discarded():
    result = reconcile_observations(
        {"20261010_1_1": 2}, [record(), record("20261010_1_2")]
    )
    assert result["extra_result_races"] == ["20261010_1_2"]
    assert result["ledger"][0]["status"] == "runner_count_mismatch"
    assert result["observed_runner_count"] == 2


def test_duplicate_observations_and_empty_population_fail():
    with pytest.raises(ValueError, match="duplicate"):
        reconcile_observations({"20261010_1_1": 2}, [record(), record()])
    with pytest.raises(ValueError, match="empty"):
        reconcile_observations({}, [])


@pytest.fixture
def schedule(monkeypatch):
    def replay(path, *, race_date):
        return {
            "capture_manifest_sha256": "a" * 64,
            "status": "reconciled",
            "source_failures": [],
            "races": [
                {
                    "race_id": f"{race_date}_1_1",
                    "source_observations": {"national": {"runners": 1}},
                }
            ],
        }

    monkeypatch.setattr(audit, "replay_schedule_snapshot", replay)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change", [None, "missing", "result_pin", "entry_pin", "schedule_pin"]
)
async def test_plan_replays_pinned_originals_and_retains_failed_population(
    tmp_path, schedule, monkeypatch, change
):
    raw = {
        "response": {
            "header": {"resultCode": "00"},
            "body": {
                "pageNo": 1,
                "numOfRows": 100,
                "totalCount": 1,
                "items": {
                    "item": [
                        {
                            "meet": 1,
                            "rcDate": 20261010,
                            "rcNo": 1,
                            "chulNo": 1,
                            "hrNo": "0000123",
                            "ord": 98,
                            "ordBigo": "경주불성립",
                            "rcTime": 0,
                        }
                    ]
                },
            },
        }
    }
    credentials = {"api_key": "synthetic+fixture/token="}
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=raw))
    ) as client:
        capture = await collect_result_snapshot(
            meet=1,
            race_date="20261010",
            output_dir=tmp_path,
            client=client,
            clock=lambda: datetime(2026, 10, 11, tzinfo=UTC),
            **credentials,
        )
    source = {
        "path": str(capture),
        "sha256": hashlib.sha256(capture.read_bytes()).hexdigest(),
    }
    plan = {
        "format_version": "kra-result-population-plan-v1",
        "race_dates": ["20261010"],
        "schedule_capture": "synthetic-schedule",
        "schedule_sha256": "a" * 64,
        "archive_root": str(tmp_path),
        "result_captures": [source],
    }
    if change == "missing":
        source["path"] = str(tmp_path / "missing.json")
    elif change == "result_pin":
        source["sha256"] = "0" * 64
    elif change == "schedule_pin":
        plan["schedule_sha256"] = "0" * 64
    elif change == "entry_pin":
        replayed = audit.replay_result_snapshot(capture)
        replayed["entry_binding_pins"] = [{"manifest_sha256": "b" * 64}]
        monkeypatch.setattr(audit, "replay_result_snapshot", lambda *a, **k: replayed)
        source.update(entry_capture="synthetic-entry", entry_sha256="0" * 64)
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    if change == "schedule_pin":
        with pytest.raises(ValueError, match="schedule_pin_mismatch"):
            audit.audit_plan(path)
        return
    result = audit.audit_plan(path)
    assert len(result["ledger"]) == result["scheduled_race_count"] == 1
    assert not result["counts_as_70_percent_evidence"]
    if change:
        assert result["source_failures"]
        assert result["missing_result_races"] == ["20261010_1_1"]
        assert not result["reconciled_observation_population"]
    else:
        assert result["reconciled_observation_population"]
        assert result["ledger"][0]["exception_notes"] == {"경주불성립": 1}
        output = tmp_path / "audit.json"
        assert audit.main(["--plan", str(path), "--output", str(output)]) == 0
        assert json.loads(output.read_bytes()) == result
        with pytest.raises(FileExistsError):
            audit.main(["--plan", str(path), "--output", str(output)])
