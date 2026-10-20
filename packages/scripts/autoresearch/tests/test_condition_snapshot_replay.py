"""Synthetic original-code subprocess replay, not a live prediction attempt."""

import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from autoresearch import condition_forward as forward
from autoresearch import condition_forward_contract as contract
from autoresearch import condition_forward_inputs as inputs
from autoresearch import condition_historical_publication as history
from autoresearch import condition_snapshot_replay as replay
from autoresearch import condition_snapshot_worker as worker
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import encoded, parse_json, sha256
from autoresearch.tests.condition_forward_fixture import (
    archive_publication,
    make_block,
)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded(value))
    return {"path": path.name, "sha256": sha256(path.read_bytes())}


@pytest.fixture
def bundle(tmp_path, monkeypatch):
    original = contract.ROOT
    root = tmp_path / "snapshot"
    root.mkdir()
    block = make_block(root, monkeypatch)
    implementation = contract.training.implementation()
    for name in implementation:
        dest = root / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((original / name).read_bytes())
    # Capture the same clean import sequence as the worker, rather than pytest's
    # larger in-process set of already loaded numerical libraries.
    environment = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            "import sys; sys.path.insert(0, sys.argv[1]); "
            "from autoresearch import condition_forward, condition_forward_contract, "
            "condition_forward_inputs, condition_training, condition_training_model; "
            "from autoresearch.restricted_cohort import encoded; "
            "print(encoded(condition_forward_contract.training.environment()).decode())",
            str(root / "packages/scripts"),
        ],
        check=True,
        capture_output=True,
        env=dict(os.environ),
    )
    block.protocol["runtime"] = {
        "model_hashes": contract.MODEL_HASHES,
        "training_receipt_sha256": contract.RECEIPT_SHA,
        "implementation": implementation,
        "environment": parse_json(environment.stdout),
        "policies": contract.POLICIES,
        "fit_count": 0,
    }
    # This archive uses separate PRs 900 (protocol), 901 (approval), 902 (pair).
    block.protocol["publication_slot"]["pull_number"] = 902
    block.review["prediction_publication_pr"] = 902
    block.persist()
    (root / "packages/scripts/mock-reviewed-code.py").unlink()
    created = timestamp(block.protocol["created_at"])
    matrix, x, identities = inputs.matrix_for(
        block.protocol, created + timedelta(seconds=40)
    )
    models, _ = contract.load_models()
    packet = forward.paired(
        block.protocol, matrix, x, identities, models, created + timedelta(seconds=50)
    )
    matrix_path = "inputs/matrix.json"
    save(root / matrix_path, matrix)
    packet_path = forward.document_path(block.study)
    save(root / packet_path, packet)
    references = {
        "protocol": block.review["protocol"]["path"],
        "approval": contract.REGISTRY,
        "prediction": packet_path,
    }
    pub_manifest = {"format_version": history.VERSION, "study_id": block.study}
    for index, (kind, document) in enumerate(references.items()):
        number = (900, 901, 902)[index]
        archive = tmp_path / kind
        archive_publication(
            archive,
            (root / document).read_bytes(),
            number,
            document,
            created + timedelta(seconds=(20, 30, 60)[index]),
            datetime.now(UTC),
        )
        pub_manifest[kind] = {
            "pull_number": number,
            "document": document,
            "sha256": sha256((root / document).read_bytes()),
            "files": {
                p.name: {
                    "path": p.relative_to(tmp_path).as_posix(),
                    "sha256": sha256(p.read_bytes()),
                }
                for p in archive.iterdir()
            },
        }
    pub_path = tmp_path / "publication.json"
    pub_pin = save(pub_path, pub_manifest)
    files = {
        p.relative_to(root).as_posix(): sha256(p.read_bytes())
        for p in root.rglob("*")
        if p.is_file()
    }
    manifest = {
        "format_version": replay.VERSION,
        "publication": pub_pin,
        "snapshot": {"path": "snapshot", "files": files},
        "matrix": matrix_path,
    }
    path = tmp_path / "replay.json"
    pin = save(path, manifest)
    return SimpleNamespace(
        path=path,
        pin=pin,
        root=root,
        manifest=manifest,
        files=files,
        pub_manifest=pub_manifest,
        pub_path=pub_path,
        block=block,
        packet=packet,
        matrix=matrix,
    )


def audit(bundle):
    return replay.audit(bundle.path, bundle.pin["sha256"])


def repin(bundle):
    bundle.pin = save(bundle.path, bundle.manifest)


def republish(bundle):
    """Change synthetic original evidence, never repair real public artifacts."""
    parent = bundle.path.parent
    protocol_ref = bundle.pub_manifest["protocol"]
    protocol = parse_json((bundle.root / protocol_ref["document"]).read_bytes())
    registry_path = bundle.root / bundle.pub_manifest["approval"]["document"]
    registry = parse_json(registry_path.read_bytes())
    registry["approved_studies"][0]["protocol"]["sha256"] = sha256(encoded(protocol))
    save(registry_path, registry)
    packet_path = bundle.root / bundle.pub_manifest["prediction"]["document"]
    packet = parse_json(packet_path.read_bytes())
    packet["protocol_sha256"] = sha256(encoded(protocol))
    packet["runtime_sha256"] = sha256(encoded(protocol["runtime"]))
    save(packet_path, packet)
    for kind in history.KINDS:
        ref = bundle.pub_manifest[kind]
        raw = (bundle.root / ref["document"]).read_bytes()
        old_pull = parse_json((parent / kind / "pull.json").read_bytes())
        directory = parent / f"{kind}-revision"
        archive_publication(
            directory,
            raw,
            ref["pull_number"],
            ref["document"],
            timestamp(old_pull["merged_at"]),
            datetime.now(UTC),
        )
        ref["sha256"] = bundle.files[ref["document"]] = sha256(raw)
        ref["files"] = {
            p.name: {
                "path": p.relative_to(parent).as_posix(),
                "sha256": sha256(p.read_bytes()),
            }
            for p in directory.iterdir()
        }
    bundle.manifest["publication"] = save(bundle.pub_path, bundle.pub_manifest)
    repin(bundle)


def test_original_environment_unavailable_is_pending(bundle):
    path = bundle.root / bundle.pub_manifest["protocol"]["document"]
    protocol = parse_json(path.read_bytes())
    protocol["runtime"]["environment"]["cpu"] = "unavailable-original-cpu"
    save(path, protocol)
    republish(bundle)
    result = audit(bundle)
    assert result["status"] == "pending_environment", result
    assert "matrix_bytes_match" not in result["replay"]
    assert result["usable_for_scoring"] is False


def test_original_prediction_disagreement_is_not_a_race_miss(bundle):
    path = bundle.root / bundle.pub_manifest["prediction"]["document"]
    packet = parse_json(path.read_bytes())
    triple = packet["races"][0]["predictions"]["A24"]
    alternate = next(
        r["horse_id"]
        for r in bundle.block.protocol["races"][0]["roster"]
        if r["horse_id"] not in triple
    )
    triple[0] = alternate
    save(path, packet)
    republish(bundle)
    result = audit(bundle)
    assert result["status"] == "replay_conflict", result
    assert result["replay"]["matrix_bytes_match"] is True
    assert result["replay"]["prediction_bytes_match"] is False
    assert result["usable_for_scoring"] is False
    assert "misses" not in result


def test_fit_and_live_entry_points_blocked_in_child():
    script = """
import sys
sys.path.insert(0, sys.argv[1])
from autoresearch import condition_forward as forward
from autoresearch import condition_forward_contract as contract
from autoresearch import condition_training as fitting
from autoresearch import condition_training_model as model
from autoresearch.condition_snapshot_worker import guard_execution
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
guard_execution(forward, contract, fitting, model)
calls = [forward.run, forward.stage, forward.witness, forward.verify_local,
         forward.locations, contract.admit, contract.training.git,
         fitting.run, fitting.save, fitting.locations, fitting.fit_once,
         model.fit_once, SimpleImputer().fit, SimpleImputer().fit_transform,
         StandardScaler().fit, StandardScaler().partial_fit,
         StandardScaler().fit_transform, LogisticRegression().fit]
for call in calls:
    try:
        call()
    except ValueError as exc:
        assert str(exc) == "snapshot_forbidden_side_effect"
    else:
        raise AssertionError("unguarded execution")
print(len(calls))
"""
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            script,
            str(Path(worker.__file__).parents[1]),
        ],
        check=True,
        capture_output=True,
    )
    assert result.stdout.strip() == b"18"


def test_missing_publication_does_not_execute_worker(bundle, monkeypatch):
    ref = bundle.pub_manifest["approval"]["files"]["pull.json"]["path"]
    (bundle.path.parent / ref).unlink()
    monkeypatch.setattr(replay, "invoke", lambda *a: pytest.fail("must not execute"))
    result = audit(bundle)
    assert result["status"] == "pending_evidence"
    assert "replay" not in result


def test_matrix_after_computation_not_verified(bundle):
    path = bundle.root / bundle.manifest["matrix"]
    matrix = parse_json(path.read_bytes())
    matrix["created_at"] = (
        timestamp(bundle.packet["computed_at"]) + timedelta(seconds=1)
    ).isoformat()
    save(path, matrix)
    digest = bundle.files[bundle.manifest["matrix"]] = sha256(encoded(matrix))
    path = bundle.root / bundle.pub_manifest["prediction"]["document"]
    packet = parse_json(path.read_bytes())
    packet["matrix_sha256"] = digest
    save(path, packet)
    republish(bundle)
    result = audit(bundle)
    assert result["status"] == "replay_unverified", result
    assert result["replay"]["reason"] == "snapshot_matrix_after_computation"


@pytest.mark.parametrize(
    "expression",
    [
        "Path(sys.argv[2], 'new.txt').write_text('x')",
        "Path(sys.argv[2], 'new-dir').mkdir()",
        "subprocess.run(['git', '--version'])",
        "socket.socket()",
        "Path(sys.argv[3]).read_bytes()",
    ],
)
def test_read_only_guard_in_separate_process(tmp_path, expression):
    root = tmp_path / "snapshot"
    root.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text("{}")
    run = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            "-c",
            "import sys, subprocess, socket; from pathlib import Path; "
            "sys.path.insert(0, sys.argv[1]); "
            "from autoresearch.condition_snapshot_worker import guard_io; "
            "guard_io(Path(sys.argv[2])); " + expression,
            str(Path(worker.__file__).parents[1]),
            str(root),
            str(outside),
        ],
        capture_output=True,
        check=False,
    )
    assert run.returncode != 0
    assert b"snapshot_forbidden_side_effect" in run.stderr or (
        b"snapshot_read_outside_evidence" in run.stderr
    )
    assert list(root.iterdir()) == []


def test_original_functions_replay_in_real_subprocess(bundle, monkeypatch):
    # The parent cannot rescue replay by substituting today's scorer or runtime.
    def forbidden(*args, **kwargs):
        pytest.fail("current implementation must not execute")

    monkeypatch.setattr(contract, "load_models", forbidden)
    monkeypatch.setattr(contract, "runtime", forbidden)
    monkeypatch.setattr(inputs, "matrix_for", forbidden)
    monkeypatch.setattr(forward, "paired", forbidden)
    monkeypatch.setattr(contract.training, "git", forbidden)
    result = audit(bundle)
    assert result["status"] == "numerically_replayed", result
    assert result["replay"]["matrix_bytes_match"] is True
    assert result["replay"]["prediction_bytes_match"] is True
    assert (
        result["original_environment_sha256"]
        == (result["replay"]["observed_environment_sha256"])
    )
    assert result["usable_for_scoring"] is False
    assert result["counts_as_70_percent_evidence"] is False
    assert result["actual_fit_count"] == 0
    assert result["outcomes_loaded"] is False
    assert result["raw_input_provenance"] == "not_verified"
    worker.inventory(bundle.root, bundle.files)


@pytest.mark.parametrize("kind", ["source", "input", "model"])
def test_corruption_before_worker(bundle, monkeypatch, kind):
    names = {
        "source": "packages/scripts/autoresearch/condition_training_model.py",
        "input": bundle.manifest["matrix"],
        "model": f"{contract.MODELS}/A24-model.json",
    }
    (bundle.root / names[kind]).write_bytes(b"damaged")
    monkeypatch.setattr(replay, "invoke", lambda *a: pytest.fail("must not execute"))
    with pytest.raises(ValueError, match="hash_mismatch"):
        audit(bundle)


@pytest.mark.parametrize("name", ["extra.py", "hidden.pyc", "data.txt"])
def test_unlisted_files_rejected(bundle, name):
    (bundle.root / name).write_bytes(b"extra")
    with pytest.raises(ValueError, match="unlisted_file"):
        audit(bundle)


@pytest.mark.parametrize("name", ["extra.py", "extra.pyc", "extra.so", "extra.pth"])
def test_listed_extra_executable_rejected(bundle, name):
    (bundle.root / name).write_bytes(b"extra")
    bundle.files[name] = sha256(b"extra")
    repin(bundle)
    with pytest.raises(ValueError, match="inventory_mismatch|unexpected_executable"):
        audit(bundle)


def test_missing_matrix_is_pending(bundle, monkeypatch):
    (bundle.root / bundle.manifest["matrix"]).unlink()
    monkeypatch.setattr(replay, "invoke", lambda *a: pytest.fail("must not execute"))
    result = audit(bundle)
    assert result["status"] == "pending_evidence"
    assert result["usable_for_scoring"] is False


def test_symlink_rejected(bundle):
    (bundle.root / "linked").symlink_to(bundle.root / bundle.manifest["matrix"])
    with pytest.raises(ValueError, match="symlink"):
        audit(bundle)


def test_changed_snapshot_after_worker_rejected(bundle, monkeypatch):
    def mutate(*args):
        (bundle.root / bundle.manifest["matrix"]).write_bytes(b"changed")
        return {"status": "numerically_replayed"}

    monkeypatch.setattr(replay, "invoke", mutate)
    with pytest.raises(ValueError, match="hash_mismatch"):
        audit(bundle)


def test_timeout_is_pending_without_retry(bundle, monkeypatch):
    calls = []

    def unavailable(*args):
        calls.append(1)
        raise subprocess.TimeoutExpired("worker", 120)

    monkeypatch.setattr(replay, "invoke", unavailable)
    result = audit(bundle)
    assert result["status"] == "pending_worker"
    assert calls == [1]


@pytest.mark.parametrize("value", ["../snapshot", "/tmp/snapshot", "./snapshot"])
def test_snapshot_path_validation(bundle, value):
    bundle.manifest["snapshot"]["path"] = value
    repin(bundle)
    with pytest.raises(ValueError, match="relative_path"):
        audit(bundle)


@pytest.mark.parametrize(
    "payload",
    [
        b"invalid",
        b"{}",
        b'{"status":"success"}',
        b'{"status":"numerically_replayed","matrix_bytes_match":true,'
        b'"prediction_bytes_match":false}',
        b'{"status":"numerically_replayed","matrix_bytes_match":1,'
        b'"prediction_bytes_match":true}',
    ],
)
def test_worker_reports_validated(monkeypatch, tmp_path, payload):
    monkeypatch.setattr(
        replay.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(returncode=0, stdout=payload),
    )
    with pytest.raises(ValueError):
        replay.invoke({"root": str(tmp_path)}, {})


def test_only_recorded_thread_settings_are_restored(monkeypatch):
    original = dict.fromkeys(worker.THREAD_VARIABLES)
    monkeypatch.setenv("OMP_NUM_THREADS", "8")
    original["BLIS_NUM_THREADS"] = "1"
    env = replay.child_environment(original)
    assert "OMP_NUM_THREADS" not in env
    assert env["BLIS_NUM_THREADS"] == "1"
    original["PYTHONPATH"] = "/untrusted"
    with pytest.raises(ValueError, match="schema"):
        replay.child_environment(original)


@pytest.mark.parametrize("value", [True, 2, "", "-1", "0", "1025", "1;echo", "１２"])
def test_invalid_thread_settings(value):
    original = dict.fromkeys(worker.THREAD_VARIABLES)
    original["OMP_NUM_THREADS"] = value
    with pytest.raises(ValueError, match="setting_invalid"):
        replay.child_environment(original)


def test_cli_missing_manifest_pending(tmp_path, capsys):
    assert (
        replay.main(
            [
                "--manifest",
                str(tmp_path / "missing.json"),
                "--sha256",
                "a" * 64,
            ]
        )
        == 2
    )
    result = parse_json(capsys.readouterr().out)
    assert result["status"] == "pending_evidence"
    assert result["usable_for_scoring"] is False
