"""Join synthetic original inputs and official results without prediction approval."""

import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import condition_forward_publication as publication
from autoresearch import fixed_pair_forward as forward
from autoresearch import kra_entry_scope_witness as witness
from autoresearch import kra_whole_card_learning as learning
from autoresearch import prerace_hash_witness as github
from autoresearch.restricted_cohort import API_COLUMNS, encoded, parse_json, sha256
from autoresearch.tests import test_fixed_pair_evaluation as result_fixture
from autoresearch.tests import test_fixed_pair_forward as source_fixture

AFTER = result_fixture.AFTER
PULL = source_fixture.PULLS[0]


def _clock(monkeypatch):
    clock = [AFTER]

    class Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            value = clock[0]
            return (
                value.astimezone(tz) if tz is not None else value.replace(tzinfo=None)
            )

    for module in (witness, learning):
        monkeypatch.setattr(module, "now", lambda: clock[0])
    for module in (
        publication,
        github,
        result_fixture.result_source,
        result_fixture.seed,
        result_fixture.official,
    ):
        monkeypatch.setattr(module, "datetime", Frozen)
    return clock


def _request(tmp_path):
    subprocess.run(
        ["git", "init", "-q", "--template="], cwd=tmp_path, check=True, timeout=15
    )
    receipt, schedule, digest = source_fixture.mock_source(tmp_path)
    return (
        receipt,
        {
            "schedule_sha256": schedule["sha256"],
            "first_cutoff": source_fixture.DUE.isoformat(),
            "packet_sha256": digest,
            "input_pr": PULL,
        },
        tmp_path / schedule["path"],
    )


@pytest.fixture
def card(tmp_path, monkeypatch):
    clock = _clock(monkeypatch)
    receipt, selected, schedule = _request(tmp_path)
    verified, source = learning.inputs.source(tmp_path, receipt, **selected)
    races = {b["race"]["race_id"]: b for b in verified["bindings"]}
    # Only the existing result fixture uses these two lists to vary a rank.
    slots = {}
    for rid, binding in races.items():
        horses = [row["horse_id"] for row in binding["shared_input"]["feature_rows"]]
        slots[rid] = {
            "M0": {"horse_ids": horses[:3]},
            "API27": {"horse_ids": horses[-3:]},
        }
    return SimpleNamespace(
        root=tmp_path,
        receipt=receipt,
        selected=selected,
        clock=clock,
        calls=[],
        races=races,
        slots=slots,
        schedule=schedule,
        protocol={"race_dates": verified["race_dates"], "source": source},
    )


def _snapshot(root):
    return {p: sha256(p.read_bytes()) for p in root.rglob("*") if p.is_file()}


def _guard(monkeypatch):
    def forbid(*_, **__):
        pytest.fail("learning evidence replay cannot use live or scoring paths")

    for module, name in (
        (httpx, "Client"),
        (httpx, "AsyncClient"),
        (forward, "run"),
        (forward, "load_models"),
        (learning.evidence, "score_slot"),
    ):
        monkeypatch.setattr(module, name, forbid)


def call(operation, card, plan=None):
    return operation(card.root, card.receipt, result_plan=plan, **card.selected)


def test_exact_whole_card_seals_without_any_prediction_or_review(card, monkeypatch):
    plan = result_fixture.seal_results(card, "official-result-v1")
    saved = _snapshot(card.root)
    assert not (card.root / "docs").exists()
    _guard(monkeypatch)
    report, candidate = call(learning.replay, card, plan)
    assert saved == _snapshot(card.root)
    assert report["race_count"] == len(card.races) == 14
    assert report["declaration_count"] == sum(
        b["race"]["runners"] for b in card.races.values()
    )
    assert report["api26_feature_missing_counts"]["rating"] == 14
    assert report["candidate_ready_for_review"] and not report["training_approved"]
    assert not report["counts_as_70_percent_evidence"]
    assert report["join_counts"] == {"joined": 14}
    assert report["result_version"]["plan_sha256"] == plan[1]
    assert report["ledger"][0]["official_result_evidence"]["capture"]["raw"]["sha256"]
    assert candidate["feature_columns"] == list(API_COLUMNS)
    assert [r["race"]["race_id"] for r in candidate["input_races"]] == sorted(
        card.races
    )
    assert [r["race_id"] for r in candidate["target_races"]] == sorted(card.races)
    for group, target in zip(
        candidate["input_races"], candidate["target_races"], strict=True
    ):
        assert "observed_top3_horse_ids" not in group
        rows = group["shared_input"]["feature_rows"]
        assert all(set(row["features"]) == set(API_COLUMNS) for row in rows)
        assert set(target["horse_ids"]) <= {row["horse_id"] for row in rows}
        assert len(target["horse_ids"]) == 3
    _, ref = call(learning.seal, card, plan)
    path = card.root / ref["path"]
    assert path.parent == (card.root / card.receipt["path"]).parent
    assert sha256(path.read_bytes()) == ref["sha256"]
    assert parse_json(path.read_bytes()) == candidate | {
        "materialized_at": AFTER.isoformat()
    }
    with pytest.raises(FileExistsError):
        call(learning.seal, card, plan)
    assert {k: v for k, v in _snapshot(card.root).items() if k != path} == saved


def test_missing_unresolved_and_omitted_declarations_withhold_entire_candidate(card):
    plan = result_fixture.seal_results(card, "incomplete-results", exceptions=True)
    saved = _snapshot(card.root)
    report, ref = call(learning.seal, card, plan)
    assert ref is None and _snapshot(card.root) == saved
    assert len(report["ledger"]) == report["race_count"] == 14
    assert not report["candidate_ready_for_review"]
    assert [r["join_state"] for r in report["ledger"][:7]] == [
        "joined",
        "top3_unresolved",
        "void_reported_no_top3",
        "source_missing",
        "source_conflict",
        "input_result_identity_conflict",
        "incomplete_result_roster",
    ]
    withdrawn = report["ledger"][6]
    assert withdrawn["result_status"] == "unique_top3_observed"
    assert withdrawn["roster_comparison"]["declared_not_in_api_result"] == 1
    assert withdrawn["result_exception_notes"] == {result_fixture.EXCLUDED: 1}


def test_explicit_result_correction_gets_a_separate_candidate(card):
    first = result_fixture.seal_results(card, "first")
    before_report, before = call(learning.seal, card, first)
    old = (card.root / before["path"]).read_bytes()
    latest = AFTER + timedelta(minutes=5)
    second = result_fixture.seal_results(card, "second", "API27", captured_at=latest)
    after_report, after = call(learning.seal, card, second)
    updated = parse_json((card.root / after["path"]).read_bytes())
    initial = parse_json(old)
    assert before_report["population_sha256"] == after_report["population_sha256"]
    assert initial["input_races"] == updated["input_races"]
    assert (
        initial["target_races"][0]["horse_ids"]
        != updated["target_races"][0]["horse_ids"]
    )
    assert [r["horse_ids"] for r in initial["target_races"][1:]] == [
        r["horse_ids"] for r in updated["target_races"][1:]
    ]
    assert updated["materialized_at"] == latest.isoformat()
    assert before["path"] != after["path"] and before["sha256"] != after["sha256"]
    assert (card.root / before["path"]).read_bytes() == old


def test_extra_results_block_seal_and_wrong_plan_does_not_redefine_scope(card):
    plan = result_fixture.seal_results(card, "extra", extra=True)
    report, candidate = call(learning.replay, card, plan)
    assert len(report["ledger"]) == 14 and candidate is None
    assert report["extra_api_result_ids"] == report["extra_official_result_ids"]
    assert len(report["extra_api_result_ids"]) == 1
    assert "selected_result_version_has_out_of_scope_races" in report["hold_reasons"]
    wrong = plan[0].with_name("wrong.json")
    wrong.write_bytes(
        encoded(parse_json(plan[0].read_bytes()) | {"schedule_sha256": "a" * 64})
    )
    with pytest.raises(ValueError, match="result_plan_not_original_scope"):
        call(learning.replay, card, (wrong, sha256(wrong.read_bytes())))


def test_result_observed_after_readback_clock_cannot_seal(card, monkeypatch):
    plan = result_fixture.seal_results(card, "future-result")
    card.clock[0] = AFTER - timedelta(days=1)
    saved = _snapshot(card.root)
    _guard(monkeypatch)
    with pytest.raises(ValueError, match="result_identity_or_clock_conflict"):
        call(learning.seal, card, plan)
    assert _snapshot(card.root) == saved


def test_unselected_result_version_prints_only_coverage(card, monkeypatch, capsys):
    original = _snapshot(card.root)
    monkeypatch.chdir(card.root)
    args = [
        "--receipt",
        card.receipt["path"],
        "--receipt-sha256",
        card.receipt["sha256"],
        "--schedule-sha256",
        card.selected["schedule_sha256"],
        "--first-cutoff",
        card.selected["first_cutoff"],
        "--packet-sha256",
        card.selected["packet_sha256"],
        "--input-pr",
        str(PULL),
        "--seal",
    ]
    assert learning.main(args) == 2
    printed = capsys.readouterr().out
    result = json.loads(printed)
    assert result["join_counts"] == {"result_version_not_selected": 14}
    assert result["sealed_candidate"] is result["result_version"] is None
    assert "feature_rows" not in printed and "horse_ids" not in printed
    assert original == _snapshot(card.root)


@pytest.mark.parametrize("late", [False, True])
def test_absent_or_cutoff_time_witness_cannot_admit_inputs(tmp_path, monkeypatch, late):
    _clock(monkeypatch)
    archived = source_fixture.archive_publication

    def replace(directory, raw, number, document, merged, retrieved):
        if late:
            return archived(directory, raw, number, document, source_fixture.DUE, AFTER)
        return None

    monkeypatch.setattr(source_fixture, "archive_publication", replace)
    receipt, selected, _ = _request(tmp_path)
    _guard(monkeypatch)
    reason = (
        "fixed_pair_input_publication_late" if late else "missing_or_oversized_evidence"
    )
    with pytest.raises(ValueError, match=reason):
        learning.replay(tmp_path, receipt, **selected)
