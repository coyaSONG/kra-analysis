"""Exercise pinned publication, schedule, and result bytes with fictional races."""

from datetime import datetime, timedelta
from types import SimpleNamespace

import httpx
import pytest

from autoresearch import condition_forward as forward
from autoresearch import condition_target_observations as target
from autoresearch import condition_training as training
from autoresearch import condition_training_model as model
from autoresearch import local_m0_evaluation as legacy
from autoresearch.restricted_cohort import encoded, parse_json, sha256
from autoresearch.tests import test_fixed_pair_evaluation as results
from autoresearch.tests.condition_forward_fixture import archive_publication
from autoresearch.tests.test_kra_schedule import SOURCE_URLS, capture, page

CONTRACT = target.contract
FIXTURE = results.fixture
STUDY = "fictional-condition-outcomes"
PROTOCOL = f"docs/research/protocols/{STUDY}.json"


@pytest.fixture
def case(tmp_path, monkeypatch):
    card = results.reviewed.__wrapped__(tmp_path, monkeypatch)
    card.publish(FIXTURE.at(44))
    sched = {
        "path": str(card.schedule.relative_to(tmp_path)),
        "sha256": sha256(card.schedule.read_bytes()),
    }
    days = card.protocol["race_dates"]
    protocol = {
        "format_version": CONTRACT.PROTOCOL_VERSION,
        "study_id": STUDY,
        "created_at": FIXTURE.at(10).isoformat(),
        "race_dates": days,
        "runtime": {
            "model_hashes": CONTRACT.MODEL_HASHES,
            "training_receipt_sha256": CONTRACT.RECEIPT_SHA,
            "fit_count": 0,
        },
        "schedules": [dict(sched, race_date=day) for day in days],
        "races": [
            {
                "race_id": rid,
                "feature_cutoff_at": b["race"]["feature_cutoff_at"],
                "roster": [
                    {"horse_id": f"{int(r['horse_id']):08}", "chul_no": r["chul_no"]}
                    for r in b["shared_input"]["feature_rows"]
                ],
            }
            for rid, b in sorted(card.races.items())
        ],
        "publication_slot": {
            "repository": CONTRACT.REPOSITORY,
            "pull_number": 803,
            "document": CONTRACT.prediction_document(STUDY),
        },
    }
    state = SimpleNamespace(
        root=tmp_path,
        card=card,
        protocol=protocol,
        schedule=sched,
        revision=0,
        first_cutoff=min(r["feature_cutoff_at"] for r in protocol["races"]),
    )

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return (results.AFTER + timedelta(days=2)).astimezone(tz)

    monkeypatch.setattr(target, "datetime", Clock)
    return state


def pin(root, path):
    return {
        "path": path.relative_to(root).as_posix(),
        "sha256": sha256(path.read_bytes()),
    }


def manifest_for(case, *, result=None, approval=None, cutoff=None, changes=None):
    case.revision += 1
    folder = case.root / f"authority-{case.revision}"
    review = {
        "study_id": STUDY,
        "race_dates": case.protocol["race_dates"],
        "reviewer": "fictional-independent-reviewer",
        "reviewed_at": FIXTURE.at(17).isoformat(),
        "protocol_publication_pr": 801,
        "prediction_publication_pr": 803,
        "protocol": {"path": PROTOCOL, "sha256": sha256(encoded(case.protocol))},
        "raw_source_closure_reviewed": True,
        "label_free_inputs_reviewed": True,
        "protocol_reviewed": True,
    }
    docs = (
        ("protocol", case.protocol, 801, PROTOCOL, FIXTURE.at(14)),
        (
            "approval",
            {
                "format_version": "condition-forward-reviews-v1",
                "approved_studies": [review],
            },
            802,
            CONTRACT.REGISTRY,
            approval or FIXTURE.at(20),
        ),
    )
    manifest = {
        "format_version": target.VERSION,
        "study_id": STUDY,
        "observation_cutoff_at": (cutoff or results.AFTER).isoformat(),
        "schedule_sources": {case.schedule["sha256"]: case.schedule},
        "result_plans": {case.schedule["sha256"]: pin(case.root, result[0])}
        if result
        else {},
    }
    for role, value, number, document, merge in docs:
        archive = folder / role
        raw = encoded(value)
        archive_publication(archive, raw, number, document, merge, results.AFTER)
        manifest[role] = {
            "pull_number": number,
            "document": document,
            "sha256": sha256(raw),
            "files": {
                name: pin(case.root, archive / name)
                for name in target.historical.publication.ARCHIVE_FILES
            },
        }
    manifest.update(changes or {})
    path = case.root / f"target-manifest-{case.revision}.json"
    return path, training.save(path, manifest)


def forbidden(*args, **kwargs):
    pytest.fail("read-only outcome verification did not stay offline")


def no_live_operations(monkeypatch):
    for mod, names in (
        (httpx, ("Client", "AsyncClient")),
        (CONTRACT, ("admit", "runtime", "load_models")),
        (CONTRACT.training, ("git", "implementation", "environment")),
        (forward, ("run", "verify_local")),
        (model, ("score", "fit_once")),
        (legacy, ("classify", "evaluate")),
    ):
        for name in names:
            monkeypatch.setattr(mod, name, forbidden)


def snapshot(root):
    return {p: sha256(p.read_bytes()) for p in root.rglob("*") if p.is_file()}


def test_replays_only_unique_targets_on_original_roster(case, monkeypatch):
    archive = results.seal_results(case.card, "original", exceptions=True, extra=True)
    authority = manifest_for(case, result=archive)
    before = snapshot(case.root)
    no_live_operations(monkeypatch)
    report = target.audit(*authority)
    assert snapshot(case.root) == before
    assert report["status"] == "original_week_targets_replayed"
    assert report["target_policy_sha256"] == target.POLICY_SHA
    assert report["full_population_verified"] is False
    assert report["denominator"] is None
    assert report["usable_for_scoring"] is False
    assert report["counts_as_70_percent_evidence"] is False
    assert "accuracy" not in report
    assert [r["race_id"] for r in report["ledger"]] == report["declared_race_ids"]
    assert len(report["ledger"]) == len(case.card.races) == 14
    first, *unresolved = report["ledger"][:7]
    assert first["status"] == "unique_target"
    assert first["triple"] == [
        f"{int(horse):08}"
        for horse in sorted(
            case.card.slots[first["race_id"]]["M0"]["horse_ids"], key=int
        )
    ]
    assert first["official_capture"]["raw"]["sha256"]
    assert first["official_receipt"]["sha256"]
    assert first["api_captures"][0]["manifest"]["sha256"]
    assert first["plan_sha256"] == archive[1]
    assert first["result_observation_id"]
    assert all(
        r["status"] == "pending_evidence" and r["triple"] is None for r in unresolved
    )
    assert [r["reason"] for r in unresolved] == [
        "top3_unresolved",
        "void_report_without_whole_race_verification",
        "source_missing",
        "source_conflict",
        "official_results_not_exact_original_roster",
        "official_results_not_exact_original_roster",
    ]
    (version,) = report["selected_result_versions"]
    extra = first["race_id"].rsplit("_", 1)[0] + "_19"
    assert version["extra_api_races"] == version["extra_official_races"] == [extra]


def test_corrections_are_new_observations_not_replacements(case, monkeypatch):
    original = results.seal_results(case.card, "version-one", "M0")
    corrected = results.seal_results(case.card, "version-two", "API27")
    first_ref = manifest_for(case, result=original)
    second_ref = manifest_for(case, result=corrected)
    no_live_operations(monkeypatch)
    before = snapshot(case.root)
    old = target.audit(*first_ref)
    new = target.audit(*second_ref)
    assert old["declared_race_ids"] == new["declared_race_ids"]
    assert old["target_policy_sha256"] == new["target_policy_sha256"]
    a, b = old["ledger"][0], new["ledger"][0]
    assert a["status"] == b["status"] == "unique_target"
    assert a["plan_sha256"] != b["plan_sha256"]
    assert a["result_observation_id"] != b["result_observation_id"]
    assert a["triple"] != b["triple"]
    assert target.audit(*first_ref) == old
    assert snapshot(case.root) == before


def test_bad_or_missing_observation_plan_is_not_a_race_loss(case, monkeypatch):
    path, _ = results.seal_results(case.card, "selected")
    selected = manifest_for(case, result=(path, "unused"))
    omitted = manifest_for(case)
    wrong = parse_json(path.read_bytes())
    wrong["race_dates"] = wrong["race_dates"][:1]
    wrong_path = case.root / "subset-plan.json"
    training.save(wrong_path, wrong)
    subset = manifest_for(case, result=(wrong_path, "unused"))
    no_live_operations(monkeypatch)
    with pytest.raises(ValueError, match="result_plan_not_original_schedule_group"):
        target.audit(*subset)
    content = path.read_bytes()
    path.write_bytes(content + b" ")
    with pytest.raises(ValueError, match="file_hash_mismatch"):
        target.audit(*selected)
    path.unlink()
    for ref, reason in (
        (selected, "missing_original_result_evidence"),
        (omitted, "no_selected_observation_plan"),
    ):
        report = target.audit(*ref)
        assert [r["race_id"] for r in report["ledger"]] == report["declared_race_ids"]
        assert all(
            (r["status"], r["reason"]) == ("pending_evidence", reason)
            for r in report["ledger"]
        )


@pytest.mark.parametrize("early", [True, False])
def test_capture_outside_result_clock_does_not_supply_target(case, monkeypatch, early):
    captured = FIXTURE.at(50) if early else results.AFTER
    cutoff = results.AFTER if early else captured - timedelta(seconds=1)
    archive = results.seal_results(case.card, "out-of-range", captured_at=captured)
    case.card.clock[0] = results.AFTER
    authority = manifest_for(case, result=archive, cutoff=cutoff)
    no_live_operations(monkeypatch)
    report = target.audit(*authority)
    assert {r["status"] for r in report["ledger"]} == {"pending_evidence"}
    assert {r["reason"] for r in report["ledger"]} == {
        "result_clock_outside_selected_window"
    }


def test_one_schedule_group_does_not_close_another(case, monkeypatch):
    archive = results.seal_results(case.card, "multi-day")
    names = "\uc6d4\ud654\uc218\ubaa9\uae08\ud1a0\uc77c"
    dates = {
        meet: f"{d:%Y/%m/%d}({names[d.weekday()]})" for meet, d in FIXTURE.DATES.items()
    }
    pages = {key: page(key, dates=dates, fields=FIXTURE.FIELDS) for key in SOURCE_URLS}
    second = pin(
        case.root,
        capture(case.root / "second-card", pages=pages, clock=lambda: FIXTURE.at(1)),
    )
    case.protocol["schedules"][1].update(second)
    first_plan = parse_json(archive[0].read_bytes())
    first_plan["race_dates"] = first_plan["race_dates"][:1]
    first_file = case.root / "first-day-version.json"
    training.save(first_file, first_plan)
    first_day = first_plan["race_dates"][0]
    authority = manifest_for(
        case,
        result=(first_file, "unused"),
        changes={
            "schedule_sources": {ref["sha256"]: ref for ref in (case.schedule, second)}
        },
    )
    no_live_operations(monkeypatch)
    report = target.audit(*authority)
    assert len(report["selected_result_versions"]) == 2
    for row in report["ledger"]:
        if row["race_id"].startswith(first_day):
            assert row["status"] == "unique_target"
        else:
            assert row["status"] == "pending_evidence"
            assert row["reason"] == "no_selected_observation_plan"
    assert report["denominator"] is None


@pytest.mark.parametrize(
    "change", ["late", "drop_race", "count", "cutoff", "wrong_model", "duplicate_id"]
)
def test_original_authority_and_schedule_must_agree(case, monkeypatch, change):
    approval = datetime.fromisoformat(case.first_cutoff) if change == "late" else None
    if change == "drop_race":
        case.protocol["races"].pop(1)
    elif change == "count":
        case.protocol["races"][0]["roster"].pop()
    elif change == "cutoff":
        case.protocol["races"][0]["feature_cutoff_at"] = FIXTURE.at(40).isoformat()
    elif change == "wrong_model":
        case.protocol["runtime"]["model_hashes"] = {}
    elif change == "duplicate_id":
        roster = case.protocol["races"][0]["roster"]
        roster[1]["horse_id"] = str(int(roster[0]["horse_id"]))
    authority = manifest_for(case, approval=approval)
    no_live_operations(monkeypatch)
    with pytest.raises(ValueError, match="target_original|historical_invalid_roster"):
        target.audit(*authority)


def test_missing_approval_does_not_authorize_result_replay(case, monkeypatch):
    ref = manifest_for(case)
    manifest = parse_json(ref[0].read_bytes())
    (case.root / manifest["approval"]["files"]["pull.json"]["path"]).unlink()
    monkeypatch.setattr(target.observations, "replay_plan", forbidden)
    report = target.audit(*ref)
    assert report["status"] == "pending_original_publication"
    assert report["declared_race_ids"]
    assert "ledger" not in report
