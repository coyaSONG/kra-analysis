"""Synthetic raw-backed paired operations, never evidence of model quality."""

import copy
import sys
from datetime import timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import api27_evaluation as e
from autoresearch import api27_forward as f
from autoresearch.observed_history_seed import digest, save
from autoresearch.restricted_cohort import encoded
from autoresearch.tests.test_kra_schedule import DATE, NOW
from autoresearch.tests.test_local_m0_evaluation import (
    files,
    publication,
)
from autoresearch.tests.test_local_m0_evaluation import (
    forward_case as forward_case,
)
from autoresearch.tests.test_local_m0_forward import environment as environment


@pytest.fixture
def paired(forward_case, tmp_path, monkeypatch):
    c = forward_case
    monkeypatch.setattr(f, "load_model", lambda path: (c["model"], c["receipt"]))
    c["m0_dir"] = tmp_path / "m0-model"
    c["api27_dir"] = tmp_path / "api27-model"
    c["output"] = tmp_path / "companion"

    def run():
        return f.run(
            c["output"],
            c["root"],
            c["m0_dir"],
            c["api27_dir"],
            c["commitment"],
            c["commitment_sha"],
        )

    c["companion_run"] = run
    c["companion"] = run()
    c["companion_root"] = c["output"] / f.SERIES
    return c


def evaluate(c, **kwargs):
    return e.evaluate(
        c["companion_root"],
        c["root"],
        c["m0_dir"],
        c["api27_dir"],
        c["commitment"],
        c["commitment_sha"],
        Path(c["companion"]["commitment_path"]),
        c["companion"]["commitment_sha256"],
        outcome_plan=c["outcome_plan"],
        outcome_sha=c["outcome_sha"],
        evaluated_at=c["evaluated"],
        **kwargs,
    )


def proofs(c, tmp_path, **kwargs):
    a, b = tmp_path / "proof-m0", tmp_path / "proof-api27"
    a.mkdir()
    b.mkdir()
    other = {**c, "commitment": Path(c["companion"]["commitment_path"])}
    return {
        "m0_publication": publication(c, a),
        "publication": publication(other, b, **kwargs),
    }


def recommit(c, tmp_path, mutate):
    value = f.parent.read(Path(c["companion"]["commitment_path"]))
    mutate(value)
    path = tmp_path / "changed-commitment.json"
    sha = save(path, value)
    c["companion"] = {"commitment_path": str(path), "commitment_sha256": sha}


def test_raw_backed_pair_full_population_and_read_only_evaluation(paired, tmp_path):
    c = paired
    before = files(c["root"]), files(c["companion_root"])
    result = evaluate(c, **proofs(c, tmp_path))
    assert result["full_paired_population_verified"]
    for arm in result["metrics"]["arms"].values():
        assert arm["denominator"] == 4
        assert arm["exact_hit_rate"] == 1
    assert result["metrics"]["paired_counts"] == {
        "both": 4,
        "M0_only": 0,
        "API27_only": 0,
        "neither": 0,
    }
    assert result["metrics"]["api27_minus_m0_exact_rate"] == 0
    assert not result["model_promoted"]
    assert before == (files(c["root"]), files(c["companion_root"]))


def test_missing_companion_publication_preserves_original_m0_result(paired, tmp_path):
    result = evaluate(paired, m0_publication=publication(paired, tmp_path))
    assert result["original_m0_report"]["metrics"]["exact_hit_rate"] == 1
    assert result["full_paired_population_verified"]
    assert result["metrics"]["paired_counts"] is None
    assert all(a["denominator"] == 4 for a in result["metrics"]["arms"].values())
    assert result["metrics"]["arms"]["M0"]["exact_hit_rate"] == 1
    assert result["metrics"]["arms"][f.ARM]["exact_hit_rate"] is None


def test_resume_after_deadline_does_not_collect_or_overwrite(paired):
    c = paired
    before = files(c["root"])
    packets = {p: p.read_bytes() for p in c["companion_root"].rglob("prediction_*")}
    counters = copy.copy(c["counters"])
    c["state"]["time"] += timedelta(days=4)
    assert c["companion_run"]()["days"] == c["companion"]["days"]
    assert counters == c["counters"]
    assert before == files(c["root"])
    assert all(p.read_bytes() == raw for p, raw in packets.items())


@pytest.mark.parametrize("kind", ["packet", "observation", "source"])
def test_tampering_or_missing_readback_keeps_full_denominator(paired, tmp_path, kind):
    c = paired
    proof = proofs(c, tmp_path)
    directory = c["companion_root"] / DATE
    if kind == "observation":
        path = next(directory.glob("observation_*.json"))
        path.unlink()
    elif kind == "packet":
        path = next(directory.glob("prediction_*.json"))
        path.write_bytes(path.read_bytes() + b" ")
    else:
        path = next((c["root"] / DATE).glob("input_*.json"))
        obj = f.parent.read(path)
        obj["manifest_sha256"] = "0" * 64
        path.write_bytes(encoded(obj))
    before = files(c["root"]), files(c["companion_root"])
    result = evaluate(c, **proof)
    arm = result["metrics"]["arms"][f.ARM]
    assert arm["denominator"] == 4
    assert arm["counts"] == {"verified_hit": 3, "pending_evidence": 1}
    assert arm["exact_hit_rate"] is None
    assert result["metrics"]["paired_counts"] is None
    assert before == (files(c["root"]), files(c["companion_root"]))


@pytest.mark.parametrize("mutation", ["drop", "duplicate", "parent", "count"])
def test_commitment_cannot_select_subset_or_different_parent(
    paired, tmp_path, mutation
):
    def mutate(v):
        if mutation == "drop":
            v["days"][0]["races"].pop()
        elif mutation == "duplicate":
            v["days"][0]["races"].append(v["days"][0]["races"][0])
        elif mutation == "parent":
            v["parent_commitment_sha256"] = "0" * 64
        else:
            v["days"][0]["race_count"] -= 1

    recommit(paired, tmp_path, mutate)
    with pytest.raises(ValueError, match="conflict"):
        evaluate(paired)


def test_unrelated_public_document_rejected(paired, tmp_path):
    with pytest.raises(ValueError, match="not_selected_commitment"):
        evaluate(paired, **proofs(paired, tmp_path, raw=b"public source code"))


def test_publication_at_first_cutoff_is_too_late(paired, tmp_path):
    study = f.parent.read(paired["root"] / DATE / "study.json")
    cutoff = f.timestamp(study["universe"]["races"][0]["feature_cutoff_at"])
    result = evaluate(paired, **proofs(paired, tmp_path, merged=cutoff))
    assert result["full_paired_population_verified"]
    assert not result["companion_commitment_published_before_block_cutoff"]
    assert result["metrics"]["paired_counts"] is None


def test_original_scoring_failure_does_not_block_companion(
    environment, tmp_path, monkeypatch
):
    c = environment
    original = f.parent.packet_for

    def fail(*args, **kwargs):
        raise ValueError("synthetic_original_scoring_failure")

    monkeypatch.setattr(f.parent, "packet_for", fail)
    run = c["run"]()
    monkeypatch.setattr(f.parent, "packet_for", original)
    monkeypatch.setattr(f.base, "CONTRACT_SHA", run["contract_sha256"])
    monkeypatch.setattr(f, "load_model", lambda path: (c["model"], c["receipt"]))
    assert len(list(c["root"].rglob("input_*.json"))) == 4
    assert not list(c["root"].rglob("prediction_*.json"))
    before = files(c["root"])
    result = f.run(
        tmp_path / "pair",
        c["root"],
        tmp_path / "m0",
        tmp_path / "api27",
        Path(run["commitment_path"]),
        run["commitment_sha256"],
    )
    assert result["days"][0]["status"] == "locally_complete"
    assert before == files(c["root"])


def test_missing_intake_keeps_four_slots(environment, tmp_path, monkeypatch):
    c = environment
    c["state"]["fail_venue"] = 1
    run = c["run"]()
    monkeypatch.setattr(f.base, "CONTRACT_SHA", run["contract_sha256"])
    monkeypatch.setattr(f, "load_model", lambda path: (c["model"], c["receipt"]))
    result = f.run(
        tmp_path / "pair",
        c["root"],
        tmp_path / "m0",
        tmp_path / "api27",
        Path(run["commitment_path"]),
        run["commitment_sha256"],
    )
    day = result["days"][0]
    assert day["race_count"] == 4 and len(day["races"]) == 4
    assert day["races"][0]["reason"] == "api27_shared_source_missing"


@pytest.mark.parametrize("fit,compute,observe", [(1, 0, 0), (-1, 1, 0)])
def test_fit_compute_readback_chronology(fit, compute, observe):
    race = {"feature_cutoff_at": (NOW + timedelta(days=2)).isoformat()}
    projected = {"source": {"available_at": (NOW - timedelta(days=2)).isoformat()}}
    receipt = {"completed_at": (NOW + timedelta(hours=fit)).isoformat()}
    with pytest.raises(ValueError, match="clock_conflict"):
        f.check_times(
            race,
            projected,
            receipt,
            NOW + timedelta(hours=compute),
            NOW + timedelta(hours=observe),
        )


def test_outputs_cannot_overlap_original(paired):
    c = paired
    with pytest.raises(ValueError, match="overlaps_source"):
        f.run(
            c["root"],
            c["root"],
            c["m0_dir"],
            c["api27_dir"],
            c["commitment"],
            c["commitment_sha"],
        )


def test_empty_comparison_has_no_rate():
    metrics = e.paired_metrics([], False)
    assert not metrics["fully_paired"] and metrics["paired_counts"] is None
    assert all(a["exact_hit_rate"] is None for a in metrics["arms"].values())


def test_parent_unverified_universe_cannot_be_reapproved(paired, tmp_path):
    proof = proofs(paired, tmp_path)
    result = evaluate(paired, publication=proof["publication"])
    assert not result["full_paired_population_verified"]
    assert all(a["denominator"] is None for a in result["metrics"]["arms"].values())


def test_unbound_parent_and_missing_companion_remain_q_and_f(paired, tmp_path):
    c = paired
    parent = f.parent.read(c["commitment"])
    slot = parent["days"][0]["races"][0]
    slot.pop("packet_sha256")
    slot.pop("observation_sha256")
    c["commitment"] = tmp_path / "parent-unbound.json"
    c["commitment_sha"] = save(c["commitment"], parent)
    race_id = slot["race_id"]
    directory = c["companion_root"] / DATE
    (directory / f"prediction_{race_id}.json").unlink()
    (directory / f"observation_{race_id}.json").unlink()

    def mutate(value):
        value["parent_commitment_sha256"] = c["commitment_sha"]
        child = next(r for r in value["days"][0]["races"] if r["race_id"] == race_id)
        child.pop("packet_sha256")
        child.pop("observation_sha256")

    recommit(c, tmp_path, mutate)
    result = evaluate(c, **proofs(c, tmp_path))
    row = next(r for r in result["ledger"] if r["race_id"] == race_id)
    assert row["M0"]["evaluation_status"] == "pending_evidence"
    assert row[f.ARM]["evaluation_status"] == "verified_miss"
    assert result["metrics"]["paired_counts"] is None
    assert all(a["denominator"] == 4 for a in result["metrics"]["arms"].values())


def test_paired_counts_are_not_portfolio_or_rate():
    statuses = [(True, True), (True, False), (False, True), (False, False)]
    ledger = [
        {
            "target_defined": True,
            "M0": {"evaluation_status": "verified_hit" if a else "verified_miss"},
            f.ARM: {"evaluation_status": "verified_hit" if b else "verified_miss"},
        }
        for a, b in statuses
    ]
    result = e.paired_metrics(ledger, True)
    assert result["paired_counts"] == {
        "both": 1,
        "M0_only": 1,
        "API27_only": 1,
        "neither": 1,
    }
    assert result["api27_minus_m0_exact_rate"] == 0
    assert all(a["exact_hit_rate"] == 0.5 for a in result["arms"].values())


def test_fixed_model_loader_checks_exact_receipt(tmp_path):
    save(tmp_path / "model.json", {})
    with pytest.raises(ValueError):
        f.load_model(tmp_path)
    assert digest((tmp_path / "model.json").read_bytes()) != f.MODEL_SHA


def test_published_protocol_matches_frozen_source_and_model_pins():
    value = f.base.pinned(
        f.ROOT / "data/contracts/api27_forward_contract_v1.json",
        "649cfe45d3ef17ea936c79e8400b44fc45474bcee12e9f94327a57a5cd856585",
    )
    assert value["model_sha256"] == f.MODEL_SHA
    assert value["fit_receipt_sha256"] == f.RECEIPT_SHA
    assert value["parent_contract_sha256"] == f.base.CONTRACT_SHA
    for name, sha in value["sources"].items():
        assert (
            digest((f.ROOT / "packages/scripts/autoresearch" / name).read_bytes())
            == sha
        )


def test_missing_companion_prediction_is_failure_not_excluded(paired, tmp_path):
    c = paired
    slot = c["companion"]["days"][0]["races"][0]
    directory = c["companion_root"] / DATE
    (directory / f"prediction_{slot['race_id']}.json").unlink()
    (directory / f"observation_{slot['race_id']}.json").unlink()

    def mutate(v):
        first = v["days"][0]["races"][0]
        first.pop("packet_sha256")
        first.pop("observation_sha256")
        first["status"] = "missing_prediction"

    recommit(c, tmp_path, mutate)
    result = evaluate(c, **proofs(c, tmp_path))
    arm = result["metrics"]["arms"][f.ARM]
    assert arm["denominator"] == 4
    assert arm["counts"] == {"verified_hit": 3, "verified_miss": 1}
    assert arm["exact_hit_rate"] == 0.75
    assert result["metrics"]["paired_counts"]["M0_only"] == 1


def test_late_recovery_cannot_backdate_missing_readback(paired):
    c = paired
    path = next((c["companion_root"] / DATE).glob("observation_*.json"))
    path.unlink()
    c["state"]["time"] += timedelta(days=4)
    result = c["companion_run"]()
    assert result["days"][0]["status"] == "incomplete"
    assert f.parent.read(path)["observed_at"] == c["state"]["time"].isoformat()
    assert any(
        r["status"] == "local_persistence_timeliness_unproven"
        for r in result["days"][0]["races"]
    )


@pytest.mark.parametrize(
    "status,defined", [("undefined_target", False), ("pending_evidence", None)]
)
def test_undefined_or_unknown_target_prevents_paired_rate(status, defined):
    ledger = [
        {
            "target_defined": defined,
            "M0": {"evaluation_status": status},
            f.ARM: {"evaluation_status": status},
        }
    ]
    metrics = e.paired_metrics(ledger, True)
    assert not metrics["fully_paired"]
    assert metrics["paired_counts"] is None
    assert all(
        a["denominator"] == 1 and a["exact_hit_rate"] is None
        for a in metrics["arms"].values()
    )


def test_changed_contract_prevents_resume(paired, monkeypatch):
    original = f.contract
    monkeypatch.setattr(f, "contract", lambda: {**original(), "selection": "changed"})
    with pytest.raises(ValueError, match="contract_changed"):
        paired["companion_run"]()


@pytest.mark.parametrize(
    "mutation", ["receipt", "columns", "recipe", "training_date", "provenance"]
)
def test_loader_rejects_conflicting_model_metadata(tmp_path, monkeypatch, mutation):
    recipe = {"fixed": True}
    model = {
        "format_version": "kra-api27-research-model-v1",
        "arm": f.ARM,
        "estimator": {
            "recipe": recipe,
            "columns": list(f.inference.API_COLUMNS),
            "training_race_ids": ["20261010_1_1"],
        },
    }
    artifacts = {}
    for name in ("corpus", "review", "implementation"):
        sha = save(tmp_path / f"{name}.json", {"kind": name})
        model[f"{name}_sha256"] = sha
        artifacts[f"{name}.json"] = sha
    receipt = {
        "status": "completed",
        "arm": f.ARM,
        "recipe": recipe,
        "artifacts": artifacts,
        "completed_at": NOW.isoformat(),
    }
    if mutation == "receipt":
        receipt["status"] = "started"
    elif mutation == "columns":
        model["estimator"]["columns"] = []
    elif mutation == "recipe":
        model["estimator"]["recipe"] = {"tuned": True}
    elif mutation == "training_date":
        model["estimator"]["training_race_ids"] = ["20990101_1_1"]
    else:
        model["corpus_sha256"] = "0" * 64
    sha = save(tmp_path / "model.json", model)
    artifacts["model.json"] = sha
    rs = save(tmp_path / "receipt.json", receipt)
    monkeypatch.setattr(f, "MODEL_SHA", sha)
    monkeypatch.setattr(f, "RECEIPT_SHA", rs)
    with pytest.raises(ValueError, match="conflict"):
        f.load_model(tmp_path)
