"""Local full-population inference, immutable retries and timing boundaries."""

import asyncio
import copy
import sys
from datetime import timedelta
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import local_m0_forward as m
from autoresearch import local_m0_inference as i
from autoresearch.kra_entry_sheet_snapshot import collect_entry_sheet_snapshot
from autoresearch.kra_schedule_snapshot import (
    collect_schedule_snapshot,
    freeze_universe_candidate,
)
from autoresearch.restricted_cohort import API_COLUMNS, PDF_FIELDS, project_features
from autoresearch.tests.test_kra_schedule import DATE, NOW, SOURCE_URLS, page


def raw_entry(gate, venue=1):
    return {
        "meet": venue,
        "rcDate": int(DATE),
        "rcNo": 1,
        "chulNo": gate,
        "hrName": "Horse",
        "hrNo": f"00{venue * 100 + gate}",
        "stTime": "1200",
        "dusu": 10,
        "age": 3,
        "wgBudam": 54,
        "rating": None,
        "rcCntT": 5,
        "ord1CntT": 1,
        "ord2CntT": 1,
        "ord3CntT": 1,
    }


def model():
    return {
        "format_version": "kra-restricted-logistic-v1",
        "arm": "M0",
        "columns": list(API_COLUMNS),
        "imputer_statistics": [0] * 14,
        "scaler_mean": [0] * 14,
        "scaler_scale": [1] * 14,
        "coefficients": [0] * 14,
        "intercept": 0,
    }


@pytest.fixture
def environment(tmp_path, monkeypatch):
    counters = {"schedule": 0, "entry": 0}
    state = {"time": NOW, "fail_venue": None, "unpublished": False}
    fixture_model = model()
    receipt = {"completed_at": (NOW - timedelta(days=2)).isoformat()}
    key = tmp_path / "test-key"
    key.write_text("synthetic-not-a-credential")

    async def schedule(*, output_dir):
        counters["schedule"] += 1

        def respond(request):
            source = next(k for k, v in SOURCE_URLS.items() if v == str(request.url))
            dates = (
                dict.fromkeys((1, 2, 3, 4), "2026/10/09(금)")
                if state["unpublished"]
                else None
            )
            return httpx.Response(
                200,
                content=page(source, dates=dates),
                headers={"content-type": "text/html; charset=utf-8"},
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await collect_schedule_snapshot(
                output_dir=output_dir, client=client, clock=lambda: state["time"]
            )

    async def entries(**kwargs):
        counters["entry"] += 1
        if kwargs["meet"] == state["fail_venue"]:
            raise TimeoutError()
        rows = [raw_entry(gate, kwargs["meet"]) for gate in range(1, 11)]
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200,
                    json={
                        "response": {
                            "header": {"resultCode": "00"},
                            "body": {
                                "pageNo": 1,
                                "numOfRows": 100,
                                "totalCount": 10,
                                "items": {"item": rows},
                            },
                        },
                    },
                )
            )
        ) as client:
            return await collect_entry_sheet_snapshot(
                **kwargs, client=client, clock=lambda: state["time"]
            )

    monkeypatch.setattr(m, "collect_schedule_snapshot", schedule)
    monkeypatch.setattr(m, "collect_entry_sheet_snapshot", entries)
    monkeypatch.setattr(
        m,
        "freeze_universe_candidate",
        lambda *a, **kw: freeze_universe_candidate(
            *a, **kw, clock=lambda: state["time"]
        ),
    )
    monkeypatch.setattr(m, "now", lambda: state["time"])
    monkeypatch.setattr(i, "DATES", (DATE,))
    monkeypatch.setattr(i, "load_model", lambda path: (fixture_model, receipt))
    root = tmp_path / "archive"

    def run():
        return asyncio.run(m.run(root, tmp_path, key))

    return {
        "run": run,
        "root": root / i.SERIES,
        "state": state,
        "counters": counters,
        "model": fixture_model,
        "receipt": receipt,
    }


def test_api_only_projection_matches_reviewed_semantics_without_pdf_or_labels():
    raw = raw_entry(1)
    pdf = {
        key: True
        if key.endswith("_missing")
        else False
        if key == "training_summary_truncated"
        else None
        for key in PDF_FIELDS
    }
    expected = project_features(raw, pdf)
    assert i.api_features(raw) == {k: expected[k] for k in API_COLUMNS}
    changed = {**raw, "ord": 1, "label_top3": ["1", "2", "3"], "ilsu": 999, "odds": 999}
    assert i.api_features(changed) == i.api_features(raw)


@pytest.mark.parametrize(
    "field,value",
    [
        ("age", 0),
        ("rating", float("nan")),
        ("rcCntT", 1),
        ("ord1CntT", 1.5),
        ("wgBudam", -1),
    ],
)
def test_invalid_api_features_fail(field, value):
    with pytest.raises(ValueError):
        i.api_features({**raw_entry(1), field: value})


def test_missing_key_is_not_ordinary_null():
    raw = raw_entry(1)
    del raw["rating"]
    with pytest.raises(ValueError, match="missing_feature_key"):
        i.api_features(raw)


def test_full_population_and_identical_resume_after_deadline(environment):
    e = environment
    first = e["run"]()
    day = first["days"][0]
    assert day["status"] == "locally_complete" and day["race_count"] == 4
    assert [r["horse_ids"] for r in day["ledger"]] == [
        [str(v * 100 + n) for n in (1, 2, 3)] for v in (1, 2, 3, 4)
    ]
    assert not first["counts_as_70_percent_evidence"]
    pins = {p: p.read_bytes() for p in (e["root"] / DATE).glob("prediction_*.json")}
    assert e["counters"] == {"schedule": 1, "entry": 4}
    e["state"]["time"] += timedelta(days=4)
    assert e["run"]()["days"] == first["days"]
    assert e["counters"] == {"schedule": 1, "entry": 4}
    assert all(p.read_bytes() == raw for p, raw in pins.items())


def test_unpublished_date_is_unknown_not_empty_complete(environment):
    e = environment
    e["state"]["unpublished"] = True
    day = e["run"]()["days"][0]
    assert day["status"] == "awaiting_card" and day["race_count"] is None
    assert e["counters"]["entry"] == 0
    assert not (e["root"] / DATE / "study.json").exists()


def test_failed_race_retained_and_retry_does_not_repredict_others(environment):
    e = environment
    e["state"]["fail_venue"] = 4
    day = e["run"]()["days"][0]
    assert (
        day["race_count"] == len(day["ledger"]) == 4 and day["status"] == "incomplete"
    )
    assert day["ledger"][-1]["status"] == "missing_prediction"
    e["state"]["time"] += timedelta(seconds=1)
    e["state"]["fail_venue"] = None
    assert e["run"]()["days"][0]["status"] == "locally_complete"
    assert e["counters"] == {"schedule": 1, "entry": 5}


def test_contract_change_rejected_without_new_capture(environment, monkeypatch):
    e = environment
    e["run"]()
    monkeypatch.setattr(i, "MODEL_SHA", "f" * 64)
    with pytest.raises(ValueError, match="series_contract_changed"):
        e["run"]()
    assert e["counters"]["entry"] == 4


def test_corrupt_existing_prediction_not_replaced(environment):
    e = environment
    e["run"]()
    path = next((e["root"] / DATE).glob("prediction_*.json"))
    original = m.read(path)
    original["prediction"]["horse_ids"] = ["9", "8", "7"]
    path.write_bytes(m.encoded(original))
    e["state"]["time"] += timedelta(seconds=1)
    day = e["run"]()["days"][0]
    assert sum(r["status"] == "missing_prediction" for r in day["ledger"]) == 1
    assert m.read(path) == original and e["counters"]["entry"] == 4


def test_pending_input_reused_after_score_failure(environment, monkeypatch):
    e = environment
    original = m.packet_for
    monkeypatch.setattr(
        m, "packet_for", lambda *a: (_ for _ in ()).throw(OSError("fixture"))
    )
    assert e["run"]()["days"][0]["status"] == "incomplete"
    assert len(list((e["root"] / DATE).glob("input_*.json"))) == 4
    monkeypatch.setattr(m, "packet_for", original)
    e["state"]["time"] += timedelta(seconds=1)
    assert e["run"]()["days"][0]["status"] == "locally_complete"
    assert e["counters"]["entry"] == 4


def test_lost_readback_then_late_retry_does_not_backdate(environment, monkeypatch):
    e = environment
    original = m.observe_packet

    def fail_prediction(path, *args, **kwargs):
        if path.name.startswith("prediction_"):
            raise OSError("lost acknowledgement")
        return original(path, *args, **kwargs)

    monkeypatch.setattr(m, "observe_packet", fail_prediction)
    e["run"]()
    assert len(list((e["root"] / DATE).glob("prediction_*.json"))) == 4
    monkeypatch.setattr(m, "observe_packet", original)
    e["state"]["time"] += timedelta(days=4)
    day = e["run"]()["days"][0]
    assert all(
        r["status"] == "local_persistence_timeliness_unproven" for r in day["ledger"]
    )
    assert e["counters"]["entry"] == 4


def test_score_crossing_deadline_writes_no_prediction(environment, monkeypatch):
    e = environment
    original = m.packet_for

    def delayed(*args):
        packet = original(*args)
        e["state"]["time"] += timedelta(days=4)
        return packet

    monkeypatch.setattr(m, "packet_for", delayed)
    day = e["run"]()["days"][0]
    assert len(day["ledger"]) == 4 and all(
        r["status"] == "missing_prediction" for r in day["ledger"]
    )
    assert not list((e["root"] / DATE).glob("prediction_*.json"))


def test_corrupt_frozen_population_is_not_recollected(environment):
    e = environment
    e["run"]()
    path = e["root"] / DATE / "study.json"
    study = m.read(path)
    study["universe"]["races"].pop()
    path.write_bytes(m.encoded(study))
    e["state"]["time"] += timedelta(seconds=1)
    assert e["run"]()["days"][0]["status"] == "failed"
    assert e["counters"] == {"schedule": 1, "entry": 4}


def test_pinned_file_rejects_changed_bytes(tmp_path):
    path = tmp_path / "artifact.json"
    path.write_text("{}")
    with pytest.raises(ValueError, match="artifact_pin_mismatch"):
        i.pinned_json(path, "0" * 64)


def test_missing_source_date_stays_in_rehearsal_population(environment, tmp_path):
    e = environment
    e["run"]()
    study = m.read(e["root"] / DATE / "study.json")
    capture = Path(study["schedule_capture"])
    packet = m.read(e["root"] / DATE / f"prediction_{DATE}_1_1.json")
    source = packet["prediction"]["source"]
    plan = {
        "entry_archive_root": str(e["root"]),
        "schedule_captures": [
            {
                "race_date": DATE,
                "path": str(capture),
                "sha256": i.sha256(capture.read_bytes()),
            }
        ],
        "entry_captures": [
            {
                "race_date": DATE,
                "meet": 1,
                "path": source["manifest_path"],
                "sha256": source["manifest_sha256"],
            }
        ],
    }
    path = tmp_path / "plan.json"
    pin = m.save(path, plan)
    report = m.rehearse(path, pin, tmp_path)
    day = report["days"][0]
    assert day["race_count"] == len(day["ledger"]) == 4
    assert [r["status"] for r in day["ledger"]] == [
        "rehearsed",
        "missing_input",
        "missing_input",
        "missing_input",
    ]
    assert not report["counts_as_70_percent_evidence"]


def test_projection_rejects_schedule_conflict_and_raw_mutation(environment):
    e = environment
    e["run"]()
    study = m.read(e["root"] / DATE / "study.json")
    race = study["universe"]["races"][0]
    packet = m.read(e["root"] / DATE / f"prediction_{race['race_id']}.json")
    source = packet["prediction"]["source"]
    path = Path(source["manifest_path"])
    changed = copy.deepcopy(race)
    changed["runners"] -= 1
    with pytest.raises(ValueError, match="roster_count_conflict"):
        i.project_capture(changed, path, e["root"])
    manifest = m.read(path)
    raw = Path(manifest["pages"][0]["raw_path"])
    raw.write_bytes(raw.read_bytes() + b" ")
    with pytest.raises(ValueError):
        i.project_capture(race, path, e["root"])


def test_missing_population_observation_after_cutoff_blocks_all_predictions(
    environment, monkeypatch
):
    e = environment
    original = m.observe_packet
    monkeypatch.setattr(
        m,
        "observe_packet",
        lambda *a, **kw: (_ for _ in ()).throw(OSError("lost population readback")),
    )
    assert e["run"]()["days"][0]["status"] == "failed"
    assert e["counters"]["entry"] == 0
    monkeypatch.setattr(m, "observe_packet", original)
    e["state"]["time"] += timedelta(days=4)
    day = e["run"]()["days"][0]
    assert day["race_count"] == 4
    assert all(
        r["reason"] == "local_m0_population_persistence_unproven" for r in day["ledger"]
    )
    assert e["counters"]["entry"] == 0


def test_observation_byte_mismatch_rejected(environment):
    e = environment
    e["run"]()
    path = next((e["root"] / DATE).glob("observation_*.json"))
    observation = m.read(path)
    observation["packet_sha256"] = "0" * 64
    path.write_bytes(m.encoded(observation))
    e["state"]["time"] += timedelta(seconds=1)
    day = e["run"]()["days"][0]
    assert sum(r["status"] == "missing_prediction" for r in day["ledger"]) == 1
    assert e["counters"]["entry"] == 4


def test_source_capture_in_future_or_model_fit_after_cutoff_rejected():
    race = {"feature_cutoff_at": (NOW + timedelta(hours=1)).isoformat()}
    projected = {"source": {"available_at": (NOW + timedelta(seconds=1)).isoformat()}}
    receipt = {"completed_at": (NOW - timedelta(days=1)).isoformat()}
    with pytest.raises(ValueError, match="source_or_completion"):
        i.check_prospective_times(race, projected, receipt, NOW)
    projected["source"]["available_at"] = NOW.isoformat()
    receipt["completed_at"] = race["feature_cutoff_at"]
    with pytest.raises(ValueError, match="model_not_before"):
        i.check_prospective_times(race, projected, receipt, NOW)


def test_equal_scores_have_one_deterministic_combination_and_all_scores():
    projected = {
        "race_id": "20261016_1_1",
        "feature_rows": [
            {
                "chul_no": gate,
                "horse_id": str(gate),
                "features": i.api_features(raw_entry(gate)),
            }
            for gate in (4, 2, 1, 3)
        ],
    }
    result = i.score_capture(model(), projected)
    assert result["horse_ids"] == ["1", "2", "3"]
    assert len(result["linear_scores"]) == 4
    assert all(r["score"] == 0 for r in result["linear_scores"])
    assert not result["scores_are_joint_probabilities"]


def test_model_admission_checks_original_review_and_dependencies(tmp_path, monkeypatch):
    fixture_model = {
        **model(),
        "recipe": i.RECIPE,
        "training_race_ids": ["20261010_1_1"],
        "source_review_id": "test-review",
        "corpus_sha256": "c",
        "implementation_sha256": "impl",
    }
    review = {
        "selected_race_ids": ["20261010_1_1"],
        "review_id": "test-review",
        "corpus_sha256": "c",
        "implementation_sha256": "impl",
    }
    receipt = {
        "status": "completed",
        "artifacts": {i.MODEL_NAME: "placeholder"},
        "review_sha256": "placeholder",
        "recipe": i.RECIPE,
        "source_review_id": "test-review",
        "corpus_sha256": "c",
        "implementation_sha256": "impl",
        "completed_at": "2026-10-11T00:00:00Z",
    }
    model_pin = m.save(tmp_path / i.MODEL_NAME, fixture_model)
    review_path = tmp_path / "review.json"
    review_pin = m.save(review_path, review)
    receipt["artifacts"][i.MODEL_NAME] = model_pin
    receipt["review_sha256"] = review_pin
    receipt_pin = m.save(tmp_path / "receipt.json", receipt)
    monkeypatch.setattr(i, "MODEL_SHA", model_pin)
    monkeypatch.setattr(i, "REVIEW_PATH", review_path)
    monkeypatch.setattr(i, "REVIEW_SHA", review_pin)
    monkeypatch.setattr(i, "RECEIPT_SHA", receipt_pin)
    assert i.load_model(tmp_path) == (fixture_model, receipt)
    monkeypatch.setattr(
        i, "INFERENCE_PINS", {"autoresearch/restricted_ablation.py": "0" * 64}
    )
    with pytest.raises(ValueError, match="inference_dependency_changed"):
        i.load_model(tmp_path)


def test_local_output_cannot_overwrite_existing_file(tmp_path):
    path = tmp_path / "packet.json"
    m.save(path, {"a": 1})
    with pytest.raises(FileExistsError):
        m.save(path, {"a": 2})
    assert m.read(path) == {"a": 1}


def test_partial_date_block_is_not_a_complete_study(environment, monkeypatch):
    e = environment
    monkeypatch.setattr(i, "DATES", (DATE, "20261017", "20261018"))
    result = e["run"]()
    assert result["block_membership_status"] == "complete_block_freeze_not_proven"
    commitment = m.read(Path(result["commitment_path"]))
    assert [d["race_date"] for d in commitment["days"]] == list(i.DATES)
    assert len(commitment["days"][0]["races"]) == 4
    assert all("packet_sha256" in r for r in commitment["days"][0]["races"])
    assert not commitment["external_publication_verified"]


def test_two_runners_cannot_own_same_series(environment):
    e = environment
    e["root"].mkdir(parents=True)
    with m.exclusive(e["root"]):
        with pytest.raises(BlockingIOError):
            e["run"]()
    assert e["counters"] == {"schedule": 0, "entry": 0}


def test_failure_before_atomic_publication_leaves_no_partial_packet(
    tmp_path, monkeypatch
):
    import os

    monkeypatch.setattr(
        os,
        "link",
        lambda *a: (_ for _ in ()).throw(OSError("fixture publication failure")),
    )
    with pytest.raises(OSError):
        m.save(tmp_path / "packet.json", {"complete": True})
    assert list(tmp_path.iterdir()) == []


def test_canonical_duplicate_and_wrong_race_id_fail_before_scoring(environment):
    e = environment
    e["run"]()
    study = m.read(e["root"] / DATE / "study.json")
    race = study["universe"]["races"][0]
    packet = m.read(e["root"] / DATE / f"prediction_{race['race_id']}.json")
    source = packet["prediction"]["source"]
    path = Path(source["manifest_path"])
    wrong = {**race, "race_id": "20261016_4_1"}
    with pytest.raises(ValueError, match="target_identity_mismatch"):
        i.project_capture(wrong, path, e["root"])
    manifest = m.read(path)
    raw_path = Path(manifest["pages"][0]["raw_path"])
    raw = m.read(raw_path)
    rows = raw["response"]["body"]["items"]["item"]
    rows[1]["hrNo"] = str(int(rows[0]["hrNo"]))
    raw_bytes = m.encoded(raw)
    raw_path.write_bytes(raw_bytes)
    manifest["pages"][0]["sha256"] = i.sha256(raw_bytes)
    manifest["pages"][0]["byte_count"] = len(raw_bytes)
    path.write_bytes(m.encoded(manifest))
    with pytest.raises(ValueError, match="canonical_identity_collision"):
        i.project_capture(race, path, e["root"])
