"""Read only fictional cards with preserved, independently dated fixture receipts."""

import importlib.util
import subprocess
import sys
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import kra_whole_card_learning as learning
from autoresearch.observed_history_seed import make_plan, pin, save
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import API_COLUMNS, encoded, parse_json, sha256
from autoresearch.tests import test_fixed_pair_evaluation as results
from autoresearch.tests import test_fixed_pair_forward as source
from autoresearch.tests import test_kra_whole_card_learning as fixtures

SPEC = importlib.util.spec_from_file_location(
    "kra_walk_forward_fold",
    Path(__file__).resolve().parents[4]
    / "docs/research/tools/kra_walk_forward_fold.py",
)
fold = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fold)
FOLD_PR = 1001


def _card(root, change, clock, weeks, pull):
    delta = timedelta(weeks=weeks)
    cutoff = source.DUE + delta
    started = source.NOW + delta
    clock[0] = started + timedelta(minutes=3)
    with change.context() as patch:
        patch.setattr(source, "NOW", started)
        patch.setattr(source, "DUE", cutoff)
        patch.setattr(
            source, "DATES", {m: day + delta for m, day in source.DATES.items()}
        )
        patch.setattr(source, "PULLS", (pull,))
        receipt, schedule, digest = source.mock_source(root)
    input_spec = {
        "receipt": receipt,
        "schedule_sha256": schedule["sha256"],
        "first_cutoff": cutoff.isoformat(),
        "packet_sha256": digest,
        "input_pr": pull,
    }
    verified, bound = learning.inputs.source(root, **input_spec)
    races, slots = {}, {}
    for binding in verified["bindings"]:
        key = binding["race"]["race_id"]
        horses = [r["horse_id"] for r in binding["shared_input"]["feature_rows"]]
        races[key] = binding
        slots[key] = {
            "M0": {"horse_ids": horses[:3]},
            "API27": {"horse_ids": horses[-3:]},
        }
    return SimpleNamespace(
        root=root,
        calls=[],
        clock=clock,
        cutoff=cutoff,
        result_time=results.AFTER + delta,
        input_spec=input_spec,
        schedule=root / schedule["path"],
        protocol={"race_dates": verified["race_dates"], "source": bound},
        races=races,
        slots=slots,
    )


def _candidate(card, name, recorded_at, choice="M0"):
    selected = results.seal_results(card, name, choice, captured_at=recorded_at)
    _, ref = learning.seal(card.root, **card.input_spec, result_plan=selected)
    return {
        "input": card.input_spec,
        "result_plan": pin(card.root, selected[0]),
        "candidate": ref,
    }


def _plan(case, data=None, name="fold-plan.json"):
    path = case.root / name
    return {"path": name, "sha256": save(path, case.plan if data is None else data)}


@pytest.fixture
def study(tmp_path, monkeypatch):
    clock = fixtures._clock(monkeypatch)
    monkeypatch.setattr(fold, "now", lambda: clock[0])
    subprocess.run(
        ["git", "init", "-q", "--template="], cwd=tmp_path, check=True, timeout=15
    )
    earlier = _card(tmp_path, monkeypatch, clock, 0, 906)
    a = _candidate(earlier, "result-version-a", earlier.result_time)
    next_card = _card(tmp_path, monkeypatch, clock, 1, 916)
    b = _candidate(next_card, "result-version-b", next_card.result_time)
    candidate_eval = _card(tmp_path, monkeypatch, clock, 2, 926)
    parent = (tmp_path / candidate_eval.input_spec["receipt"]["path"]).parent
    return SimpleNamespace(
        root=tmp_path,
        parent=parent,
        plan={
            "format": fold.PLAN,
            "training": [a, b],
            "evaluation": candidate_eval.input_spec,
        },
        clock=clock,
        initial=clock[0],
        training=[earlier, next_card],
        evaluation=candidate_eval,
    )


def _publication(study, marker, merged):
    sha = parse_json(marker)["packet_sha256"]
    retrieved = merged + timedelta(seconds=2)
    study.clock[0] = retrieved
    source.archive_publication(
        study.parent / fold.ARCHIVE_NAME,
        marker,
        FOLD_PR,
        fold.publication_document(sha),
        merged,
        retrieved,
    )
    return sha


def test_replay_freezes_all_races_and_only_old_labels(study, monkeypatch, capsys):
    ref = _plan(study)
    checks = []
    replay = learning.replay

    def past_only(root, **selected):
        assert selected["receipt"] != study.evaluation.input_spec["receipt"]
        checks.append(selected["result_plan"][0])
        return replay(root, **selected)

    monkeypatch.setattr(learning, "replay", past_only)
    fixtures._guard(monkeypatch)
    monkeypatch.chdir(study.root)
    assert (
        fold.main(["stage", "--plan", ref["path"], "--plan-sha256", ref["sha256"]]) == 0
    )
    raw_marker = capsys.readouterr().out.encode()
    assert set(parse_json(raw_marker)) == {"format", "packet_sha256"}
    raw = (study.parent / fold.PACKET_NAME).read_bytes()
    assert b"target_races" not in raw and b"feature_rows" not in raw
    data = parse_json(raw)
    assert data["training_race_count"] == 28
    assert data["evaluation"]["race_ids"] == sorted(study.evaluation.races)
    assert data["evaluation"]["race_count"] == 14
    assert data["evaluation"]["declaration_count"] == sum(
        b["race"]["runners"] for b in study.evaluation.races.values()
    )
    assert all(
        item["race_ids"] == sorted(card.races)
        for item, card in zip(data["training"], study.training, strict=True)
    )
    assert data["training_feature_missing_counts"]["rating"] == 28
    assert data["feature_columns"] == list(API_COLUMNS)
    assert len(checks) == 2
    with pytest.raises(FileExistsError, match="already_present"):
        fold.stage(study.root, ref)
    sha = _publication(study, raw_marker, study.initial + timedelta(seconds=4))
    assert sha == sha256(raw)
    study.clock[0] = study.evaluation.cutoff + timedelta(days=4)
    saved = fixtures._snapshot(study.root)
    proof = fold.verify(study.root, ref, packet_sha256=sha, pull=FOLD_PR)
    assert proof["before_cutoff"] and not proof["training_approved"]
    assert not proof["cross_fold_selection_rule_verified"]
    assert not proof["local_receipt_timestamps_independently_verified"]
    assert proof["evaluation_race_count"] == 14
    assert proof["training_card_count"] == 2
    assert fixtures._snapshot(study.root) == saved
    assert len(checks) == 4


@pytest.mark.parametrize("mode", ["duplicate", "reverse", "evaluation_as_training"])
def test_scope_conflict_fails_before_opening_results(study, monkeypatch, mode):
    items = study.plan["training"]
    if mode == "duplicate":
        selected = [items[0], items[0]]
    elif mode == "reverse":
        selected = items[::-1]
    else:
        selected = [items[0] | {"input": study.evaluation.input_spec}]

    def forbid(*_, **__):
        pytest.fail("must verify temporal role separation before reading labels")

    monkeypatch.setattr(learning, "replay", forbid)
    ref = _plan(study, study.plan | {"training": selected})
    with pytest.raises(ValueError, match="fold_card_order_or_population_overlap"):
        fold.stage(study.root, ref)
    assert not (study.parent / fold.PACKET_NAME).exists()


def _edit_candidate(study, change):
    item = study.plan["training"][0]
    path = study.root / item["candidate"]["path"]
    data = parse_json(path.read_bytes())
    change(data)
    path.write_bytes(encoded(data))
    item["candidate"] = pin(study.root, path)
    return _plan(study)


def test_rehashed_changed_target_is_not_raw_source_replay(study):
    def change(data):
        data["target_races"][0]["horse_ids"].reverse()

    ref = _edit_candidate(study, change)
    with pytest.raises(ValueError, match="fold_candidate_does_not_replay"):
        fold.stage(study.root, ref)


def test_backdated_candidate_readback_is_not_proof_of_result_availability(study):
    recorded_at = (study.training[0].result_time - timedelta(seconds=1)).isoformat()

    def change(data):
        data["report"]["readback_started_at"] = recorded_at

    ref = _edit_candidate(study, change)
    with pytest.raises(
        ValueError, match="fold_result_evidence_after_candidate_readback"
    ):
        fold.stage(study.root, ref)
    assert not (study.parent / fold.PACKET_NAME).exists()


def test_actual_later_correction_is_not_eligible_at_original_assembly(study):
    a = study.plan["training"][0]
    old = (study.root / a["candidate"]["path"]).read_bytes()
    late = _candidate(
        study.training[0], "correction-after-fold", study.evaluation.cutoff, "API27"
    )
    ref = _plan(study, study.plan | {"training": [late, study.plan["training"][1]]})
    study.clock[0] = study.initial
    with pytest.raises(ValueError, match="fold_candidate_unavailable_at_assembly"):
        fold.stage(study.root, ref)
    assert (study.root / a["candidate"]["path"]).read_bytes() == old
    assert not (study.parent / fold.PACKET_NAME).exists()


def test_late_stage_and_cutoff_time_publication_are_not_timely(study):
    ref = _plan(study)
    study.clock[0] = study.evaluation.cutoff
    with pytest.raises(ValueError, match="fold_stage_not_before_original_cutoff"):
        fold.stage(study.root, ref)
    assert not (study.parent / fold.PACKET_NAME).exists()
    study.clock[0] = study.initial
    marker = fold.stage(study.root, ref)
    sha = _publication(study, marker, study.evaluation.cutoff)
    report = fold.verify(study.root, ref, packet_sha256=sha, pull=FOLD_PR)
    assert report["state"] == "fold_published_late"
    assert report["before_cutoff"] is False


def test_cannot_substitute_plan_after_staging(study):
    ref = _plan(study)
    marker = fold.stage(study.root, ref)
    sha = _publication(study, marker, study.initial + timedelta(seconds=4))
    replacement = _plan(study, study.plan, name="different-selection.json")
    with pytest.raises(ValueError, match="fold_packet_does_not_replay"):
        fold.verify(study.root, replacement, packet_sha256=sha, pull=FOLD_PR)


@pytest.mark.parametrize("delay", [0, 30])
def test_korean_clock_representation_does_not_move_original_cutoff(study, delay):
    alternate = (study.evaluation.cutoff + timedelta(minutes=delay)).astimezone(
        ZoneInfo("Asia/Seoul")
    )
    spec = study.plan["evaluation"] | {"first_cutoff": alternate.isoformat()}
    ref = _plan(study, study.plan | {"evaluation": spec})
    if delay:
        with pytest.raises(ValueError, match="original_cutoff_conflict"):
            fold.stage(study.root, ref)
        assert not (study.parent / fold.PACKET_NAME).exists()
    else:
        fold.stage(study.root, ref)
        payload = parse_json((study.parent / fold.PACKET_NAME).read_bytes())
        assert (
            payload["evaluation"]["first_block_cutoff"]
            == study.evaluation.cutoff.isoformat()
        )


def test_earlier_pr_does_not_witness_replaced_marker_bytes(study):
    ref = _plan(study)
    original = parse_json(fold.stage(study.root, ref))["packet_sha256"]
    merged = study.initial + timedelta(seconds=4)
    study.clock[0] = merged + timedelta(seconds=2)
    source.archive_publication(
        study.parent / fold.ARCHIVE_NAME,
        fold.marker("8" * 64),
        FOLD_PR,
        fold.publication_document(original),
        merged,
        study.clock[0],
    )
    with pytest.raises(ValueError, match="forward_publication_evidence_conflict"):
        fold.verify(study.root, ref, packet_sha256=original, pull=FOLD_PR)


def test_stage_loads_no_outcome_reference_in_evaluation_spec(study):
    evaluation = study.plan["evaluation"] | {
        "result_plan": study.plan["training"][0]["result_plan"]
    }
    ref = _plan(study, study.plan | {"evaluation": evaluation})
    with pytest.raises(ValueError, match="fold_invalid_input"):
        fold.stage(study.root, ref)
    assert not (study.parent / fold.PACKET_NAME).exists()


def test_wide_old_result_archive_does_not_open_evaluation_labels(study, monkeypatch):
    item = study.plan["training"][0]
    original = parse_json((study.root / item["result_plan"]["path"]).read_bytes())
    seed_root = study.root / "archive-with-future-dates"
    seed_root.mkdir()
    save(
        seed_root / "plan.json",
        make_plan(
            original["race_dates"][0],
            study.evaluation.protocol["race_dates"][0],
        ),
    )
    plan_path = study.root / "wrong-result-scope.json"
    save(plan_path, original | {"seed_root": str(seed_root)})
    revised = item | {"result_plan": pin(study.root, plan_path)}

    def forbid(*_, **__):
        pytest.fail("must reject a too-wide archive before result replay")

    monkeypatch.setattr(learning, "replay", forbid)
    ref = _plan(study, study.plan | {"training": [revised]})
    with pytest.raises(ValueError, match="fold_result_archive_reaches_evaluation"):
        fold.stage(study.root, ref)
    assert not (study.parent / fold.PACKET_NAME).exists()


@pytest.mark.parametrize("before_merge", [False, True])
def test_packet_cannot_predate_its_evaluation_input_witness(study, before_merge):
    ref = _plan(study)
    fold.stage(study.root, ref)
    path = study.parent / fold.PACKET_NAME
    packet = parse_json(path.read_bytes())
    evaluation_merged = timestamp(
        packet["evaluation"]["input"]["input_publication"]["merged_at"]
    )
    packet["eligibility_checked_as_of"] = (
        evaluation_merged - timedelta(seconds=int(before_merge))
    ).isoformat()
    raw = encoded(packet)
    path.write_bytes(raw)
    sha = _publication(study, fold.marker(sha256(raw)), study.initial)
    with pytest.raises(ValueError, match="fold_input_unavailable_at_assembly"):
        fold.verify(study.root, ref, packet_sha256=sha, pull=FOLD_PR)


def test_capture_reads_only_the_bound_public_marker(study, monkeypatch):
    ref = _plan(study)
    marker = fold.stage(study.root, ref)
    sha = parse_json(marker)["packet_sha256"]
    document = fold.publication_document(sha)
    merged = study.initial + timedelta(seconds=5)
    pr, content = source.public_payload(marker, FOLD_PR, document, merged)
    base = source.github.API_ROOT
    calls = []
    urls = [
        f"{base}/pulls/{FOLD_PR}",
        f"{base}/contents/{document}?ref={pr['merge_commit_sha']}",
    ]
    routes = dict(zip(urls, (pr, content), strict=True))

    def fixture_response(request):
        key = str(request.url)
        calls.append(key)
        return httpx.Response(200, json=routes[key])

    client = httpx.Client
    monkeypatch.setattr(
        fold.publication.httpx,
        "Client",
        lambda **kw: client(transport=httpx.MockTransport(fixture_response), **kw),
    )
    study.clock[0] = merged + timedelta(seconds=2)
    report = fold.verify(study.root, ref, packet_sha256=sha, pull=FOLD_PR, capture=True)
    assert report["before_cutoff"] and not report["counts_as_70_percent_evidence"]
    assert calls == urls
    assert sorted(
        p.name for p in (study.parent / fold.ARCHIVE_NAME).iterdir()
    ) == sorted(fold.publication.ARCHIVE_FILES)


def test_original_fold_replays_after_a_later_result_correction(study):
    ref = _plan(study)
    marker = fold.stage(study.root, ref)
    sha = _publication(study, marker, study.initial + timedelta(seconds=4))
    immutable = (study.parent / fold.PACKET_NAME).read_bytes()
    correction = _candidate(
        study.training[0],
        "late-result-version",
        study.evaluation.cutoff + timedelta(days=4),
        "API27",
    )
    assert correction["result_plan"] != study.plan["training"][0]["result_plan"]
    assert correction["candidate"] != study.plan["training"][0]["candidate"]
    before = fixtures._snapshot(study.root)
    proof = fold.verify(study.root, ref, packet_sha256=sha, pull=FOLD_PR)
    assert proof["before_cutoff"]
    assert fixtures._snapshot(study.root) == before
    assert (study.parent / fold.PACKET_NAME).read_bytes() == immutable


@pytest.mark.parametrize("exported_before_combined", [False, True])
def test_combined_result_clock_can_be_later_than_api_response(exported_before_combined):
    api = "2099-01-04T01:00:00+00:00"
    official = "2099-01-04T02:00:00+00:00"
    combined = "2099-01-04T03:00:00+00:00"
    exported = "2099-01-04T04:00:00+00:00"
    record = {"race_id": "fixture-race", "source_available_at": combined}
    seed = {
        "materialized_at": api if exported_before_combined else exported,
        "records": [record],
    }
    report = {
        "ledger": [
            {
                "race_id": "fixture-race",
                "api_result_captures": [{"capture_completed_at": api}],
                "official_result_evidence": {"capture": {"completed_at": official}},
            }
        ]
    }
    if exported_before_combined:
        with pytest.raises(ValueError, match="fold_result_seed_clock_conflict"):
            fold._result_clocks(seed, report)
    else:
        assert fold._result_clocks(seed, report) == {
            "latest_api_capture_completed_at": api,
            "latest_combined_result_available_at": combined,
            "result_seed_materialized_at": exported,
            "latest_official_capture_completed_at": official,
            "result_evidence_available_at": exported,
        }
