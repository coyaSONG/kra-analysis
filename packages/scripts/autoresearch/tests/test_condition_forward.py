"""Future block and publication regressions with fitting entry points trapped."""

import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import numpy as np
import pytest

from autoresearch import condition_forward as forward
from autoresearch import condition_forward_contract as contract
from autoresearch import condition_forward_publication as publication
from autoresearch import condition_training as training
from autoresearch import condition_training_model as numerical
from autoresearch import prerace_hash_witness as github
from autoresearch.restricted_cohort import encoded, parse_json, sha256
from autoresearch.tests.condition_forward_fixture import (
    archive_publication,
    make_block,
    public_payload,
)


@pytest.fixture(autouse=True)
def no_fitting(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("fitting is forbidden in forward inference")

    for cls, names in (
        (numerical.LogisticRegression, ("fit",)),
        (numerical.SimpleImputer, ("fit", "fit_transform")),
        (numerical.StandardScaler, ("fit", "fit_transform")),
    ):
        for name in names:
            monkeypatch.setattr(cls, name, forbidden)
    monkeypatch.setattr(numerical, "fit_once", forbidden)
    monkeypatch.setattr(training, "run", forbidden)


@pytest.fixture
def block(tmp_path, monkeypatch):
    return make_block(tmp_path, monkeypatch)


def test_real_pins_and_stored_statistics_without_fit():
    models, _ = contract.load_models()
    for model in models.values():
        x = np.zeros((4, len(model["columns"])))
        x[0, :] = np.nan
        filled = np.where(np.isnan(x), model["imputer_statistics"], x)
        expected = (
            (filled - model["scaler_mean"]) / model["scaler_scale"]
        ) @ np.asarray(model["coefficients"]) + model["intercept"]
        np.testing.assert_array_equal(numerical.score(model, x), expected)


def test_complete_replay_stage_and_publication(block):
    receipt = forward.run(block.study)
    assert receipt["status"] == "locally_complete_not_public"
    _, raw, _ = forward.verify_local(block.study)
    packet = parse_json(raw)
    assert packet["race_count"] == 4 and packet["runner_count"] == 40
    assert (
        packet["actual_fit_count"] == 0 and not packet["counts_as_70_percent_evidence"]
    )
    assert all(
        len(r["predictions"][a]) == 3 for r in packet["races"] for a in numerical.ARMS
    )
    assert forward.stage(block.study) == forward.stage(block.study)
    assert (block.root / forward.document_path(block.study)).read_bytes() == raw
    result = forward.witness(block.study, 901)
    assert result["status"] == "published_before_cutoff"
    assert result["race_count"] == 4 and not result["model_promoted"]
    assert block.calls == [900, 901]
    with pytest.raises(ValueError, match="reused_or_symlink"):
        forward.run(block.study)


@pytest.mark.parametrize(
    "damage",
    ["runtime_drift", "missing_local_copy", "damaged_local_copy", "failure_marker"],
)
def test_current_replay_failure_does_not_erase_archived_publication(block, damage):
    """A live admission failure is not evidence of historical invalidity."""
    forward.run(block.study)
    forward.stage(block.study)
    _, raw, _ = forward.verify_local(block.study)
    result = forward.witness(block.study, 901)
    assert result["status"] == "published_before_cutoff"
    archive = Path(result["report_path"]).parent
    ledger, output = forward.locations(block.study)
    if damage == "runtime_drift":
        block.runtime["synthetic_environment"] = "changed_after_publication"
    elif damage == "missing_local_copy":
        (output / "paired.json").unlink()
    elif damage == "damaged_local_copy":
        (output / "paired.json").write_bytes(b"synthetic later damage")
    else:
        training.save(ledger / "failure.json", {"synthetic_later_marker": True})
    with pytest.raises((ValueError, OSError)):
        forward.verify_local(block.study)
    published, witness = publication.replay(
        archive, 901, forward.document_path(block.study), sha256(raw)
    )
    assert published == raw
    assert witness == result["witness"]
    assert github.timestamp(witness["merged_at"]) < min(
        github.timestamp(r["feature_cutoff_at"]) for r in block.protocol["races"]
    )
    # This proves archived publication bytes/timing, not full inference validity,
    # population completeness, or a hit. No outcome has been loaded.
    assert not result["counts_as_70_percent_evidence"]


@pytest.mark.parametrize(
    "change",
    [
        "missing_review",
        "overlap",
        "old_date",
        "empty_horizon",
        "policy",
        "environment",
        "code",
        "unmerged",
        "uncommitted",
        "model",
        "numerical_code",
        "registry_empty",
    ],
)
def test_admission_refuses_without_reservation(block, change):
    if change == "missing_review":
        block.review["raw_source_closure_reviewed"] = False
    elif change == "overlap":
        block.records.append({**block.review, "study_id": "other"})
    elif change == "old_date":
        block.protocol["race_dates"] = ["20261018"]
    elif change == "empty_horizon":
        block.protocol["horizon"] = " "
    elif change == "policy":
        block.protocol["policies"]["refitting"] = "allowed"
    elif change == "environment":
        block.runtime["synthetic_environment"] = "changed"
    elif change == "model":
        (block.root / contract.MODELS / "A24-model.json").write_bytes(b"{}")
    elif change == "numerical_code":
        (
            block.root / "packages/scripts/autoresearch/condition_training_model.py"
        ).write_bytes(b"changed")
    elif change == "registry_empty":
        block.records.clear()
    block.persist()
    if change in ("unmerged", "uncommitted"):
        ref = "origin/main" if change == "unmerged" else "HEAD"
        block.committed[f"{ref}:{contract.REGISTRY}"] = b"different"
    elif change == "code":
        block.committed["origin/main:packages/scripts/mock-reviewed-code.py"] = (
            b"different"
        )
    with pytest.raises(ValueError):
        forward.run(block.study)
    ledger, output = forward.locations(block.study)
    assert not ledger.exists() and not output.exists() and not block.calls


@pytest.mark.parametrize(
    "change",
    [
        "population",
        "roster",
        "schedule_bytes",
        "raw_html",
        "source_hash",
        "source_clock",
        "packet_hash",
        "packet_label",
        "packet_clock",
        "memory_clock",
        "memory_label",
        "column",
        "missing_runner",
        "cutoff",
        "duplicate_packet",
        "missing_source",
    ],
)
def test_invalid_inputs_consume_attempt_without_predictions(block, change):
    p = block.protocol
    if change == "population":
        p["races"].pop()
    elif change == "roster":
        p["races"][0]["roster"].pop()
    elif change == "schedule_bytes":
        block.captured.write_bytes(b"{}")
    elif change == "raw_html":
        next(block.captured.parent.glob("*.html")).write_bytes(b"changed")
    elif change == "source_hash":
        (block.root / p["source_receipts"][0]["path"]).write_bytes(b"changed")
    elif change == "source_clock":
        p["source_receipts"][0]["available_at"] = (
            datetime.now(UTC) + timedelta(days=1)
        ).isoformat()
    elif change == "packet_hash":
        (block.root / p["packets"][0]["path"]).write_bytes(b"{}")
    elif change in ("packet_label", "packet_clock", "column", "missing_runner"):
        pin = p["packets"][0]
        packet = contract.read_pin(pin)
        if change == "packet_label":
            packet["target_outcomes_loaded"] = True
        elif change == "packet_clock":
            packet["materialized_at"] = datetime.now(UTC).isoformat()
        elif change == "column":
            packet["feature_rows"][0]["features"]["target_rank"] = 1
        else:
            packet["feature_rows"].pop()
        p["packets"][0] = block.pin(pin["path"], packet)
    elif change in ("memory_clock", "memory_label"):
        memory = contract.read_pin(p["memory"])
        if change == "memory_clock":
            memory["created_at"] = datetime.now(UTC).isoformat()
        else:
            memory["target_outcomes_loaded"] = True
        p["memory"] = block.pin(p["memory"]["path"], memory)
    elif change == "cutoff":
        p["races"][0]["feature_cutoff_at"] = (
            datetime.now(UTC) + timedelta(days=2)
        ).isoformat()
    elif change == "duplicate_packet":
        p["packets"].append(p["packets"][0])
    else:
        p["source_receipts"] = []
    block.persist()
    with pytest.raises(ValueError):
        forward.run(block.study)
    ledger, output = forward.locations(block.study)
    failure = parse_json((ledger / "failure.json").read_bytes())
    assert failure["actual_fit_count"] == 0 and not failure["retry_allowed"]
    assert failure["race_ids"] == [r["race_id"] for r in p["races"]]
    assert not output.exists()
    with pytest.raises(ValueError, match="reused_or_symlink"):
        forward.run(block.study)


@pytest.mark.parametrize("point", ["before_network", "after_score", "after_save"])
def test_deadline_crossings_never_complete(block, monkeypatch, point):
    late = github.timestamp(block.protocol["races"][0]["feature_cutoff_at"])
    if point == "before_network":
        monkeypatch.setattr(forward, "now", lambda: late)
    elif point == "after_score":
        original = forward.score

        def scoring(*args):
            result = original(*args)
            monkeypatch.setattr(forward, "now", lambda: late)
            return result

        monkeypatch.setattr(forward, "score", scoring)
    else:
        original = forward.save

        def saving(path, value):
            result = original(path, value)
            if path.name == "paired.json":
                monkeypatch.setattr(forward, "now", lambda: late)
            return result

        monkeypatch.setattr(forward, "save", saving)
    with pytest.raises(ValueError, match="deadline"):
        forward.run(block.study)
    ledger, _ = forward.locations(block.study)
    assert (ledger / "failure.json").exists() and not (
        ledger / "complete.json"
    ).exists()
    with pytest.raises(ValueError, match="failed_attempt"):
        forward.verify_local(block.study)
    if point == "before_network":
        assert block.calls == []


def test_concurrent_run_has_one_reservation(block):
    def attempt():
        try:
            forward.run(block.study)
            return "completed"
        except FileExistsError:
            return "duplicate"
        except ValueError as exc:
            assert str(exc) == "reused_or_symlink_destination"
            return "duplicate"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: attempt(), range(2))) == [
            "completed",
            "duplicate",
        ]
    assert block.calls == [900]


@pytest.mark.parametrize("target", ["paired.json", "matrix.json", "receipt.json"])
def test_changed_local_bytes_cannot_be_staged(block, target):
    forward.run(block.study)
    _, output = forward.locations(block.study)
    path = output / target
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="receipt_conflict"):
        forward.stage(block.study)


def test_staged_bytes_are_never_replaced(block):
    forward.run(block.study)
    forward.stage(block.study)
    path = block.root / forward.document_path(block.study)
    path.write_bytes(b"preserve existing")
    with pytest.raises(ValueError, match="existing_staged"):
        forward.stage(block.study)
    assert path.read_bytes() == b"preserve existing"


def test_late_stage_is_recorded_and_not_published(block, monkeypatch):
    forward.run(block.study)
    late = github.timestamp(block.protocol["races"][0]["feature_cutoff_at"])
    monkeypatch.setattr(forward, "now", lambda: late)
    with pytest.raises(ValueError, match="deadline"):
        forward.stage(block.study)
    _, output = forward.locations(block.study)
    assert len(list(output.glob("staging-failure-*.json"))) == 1
    assert not (block.root / forward.document_path(block.study)).exists()


def test_new_registration_does_not_break_old_receipt(block):
    forward.run(block.study)
    block.records.append({"study_id": "later", "race_dates": ["20991231"]})
    block.persist()
    forward.verify_local(block.study)


@pytest.mark.parametrize("where", ["output", "source"])
def test_symlinks_fail_closed(block, where):
    if where == "output":
        _, output = forward.locations(block.study)
        output.parent.mkdir(parents=True)
        output.symlink_to(block.root / "elsewhere", target_is_directory=True)
    else:
        pin = block.protocol["packets"][0]
        path = block.root / pin["path"]
        replacement = path.with_suffix(".copy")
        path.rename(replacement)
        path.symlink_to(replacement)
    with pytest.raises((ValueError, FileExistsError)):
        forward.run(block.study)


def test_cli_inspect_and_unregistered_run_create_nothing(block, capsys):
    assert forward.main(["inspect"]) == 0
    assert parse_json(capsys.readouterr().out)["actual_fit_count"] == 0
    assert forward.main(["run", "--study", "not-registered"]) == 2
    assert "exact_registered_study" in capsys.readouterr().out
    assert not (block.root / "common-git").exists() and not block.calls


@pytest.mark.parametrize(
    "change",
    [
        "pending",
        "wrong_bytes",
        "wrong_branch",
        "wrong_blob",
        "future_retrieval",
        "response_hash",
    ],
)
def test_publication_conflicts_fail_closed(tmp_path, change):
    instant = datetime.now(UTC) - timedelta(seconds=2)
    raw, doc = b"published", "docs/research/commitments/test.json"
    directory = tmp_path / "witness"
    archive_publication(directory, raw, 900, doc, instant, instant)
    if change in ("pending", "wrong_branch"):
        path = directory / "pull.json"
        value = parse_json(path.read_bytes())
        if change == "pending":
            value["merged"] = False
        else:
            value["base"]["ref"] = "other"
        path.write_bytes(encoded(value))
    elif change == "wrong_bytes":
        (directory / "published-document.md").write_bytes(b"different")
    elif change == "wrong_blob":
        path = directory / "document-response.json"
        value = parse_json(path.read_bytes())
        value["sha"] = "f" * 40
        path.write_bytes(encoded(value))
    else:
        path = directory / "observed.json"
        value = parse_json(path.read_bytes())
        if change == "future_retrieval":
            value["retrieved_at"] = (instant + timedelta(days=1)).isoformat()
        else:
            value["pull_response_sha256"] = "f" * 64
        path.write_bytes(encoded(value))
    with pytest.raises(ValueError):
        publication.replay(directory, 900, doc, sha256(raw))


@pytest.mark.parametrize("status", [200, 403, 429, 503])
def test_live_capture_bounded_requests_no_retries(tmp_path, monkeypatch, status):
    raw, doc = b"published", "docs/research/commitments/test.json"
    pull, content = public_payload(
        raw, 900, doc, datetime.now(UTC) - timedelta(seconds=2)
    )
    calls = []
    original = httpx.Client

    def respond(request):
        calls.append(str(request.url))
        return httpx.Response(status, json=pull if len(calls) == 1 else content)

    monkeypatch.setattr(
        publication.httpx,
        "Client",
        lambda **kwargs: original(transport=httpx.MockTransport(respond), **kwargs),
    )
    if status == 200:
        assert (
            publication.capture(tmp_path / "witness", 900, doc, sha256(raw))[0] == raw
        )
        assert len(calls) == 2 and calls[1].endswith("?ref=" + "a" * 40)
    else:
        with pytest.raises(ValueError, match="fetch_failed"):
            publication.capture(tmp_path / "witness", 900, doc, sha256(raw))
        assert len(calls) == 1


def test_publication_failure_preserved_without_replacement(block, monkeypatch):
    forward.run(block.study)
    forward.stage(block.study)
    _, before, _ = forward.verify_local(block.study)

    def unavailable(*args):
        raise httpx.ConnectError("synthetic failure")

    monkeypatch.setattr(publication, "capture", unavailable)
    report = forward.witness(block.study, 901)
    assert (
        report["status"] == "publication_unverified" and report["actual_fit_count"] == 0
    )
    assert forward.verify_local(block.study)[1] == before


def test_ties_are_numeric_and_canonical_without_fitting():
    rows = [
        {"race_id": "20990101_1_1", "chul_no": n, "horse_id": str(h)}
        for n, h in ((10, 9), (2, 30), (3, 4), (1, 100))
    ]
    assert numerical.select(rows, np.zeros(4))[0]["horse_ids"] == ["4", "30", "100"]


def test_stage_crossing_deadline_preserves_failed_bytes(block, monkeypatch):
    forward.run(block.study)
    original = forward.save
    late = github.timestamp(block.protocol["races"][0]["feature_cutoff_at"])

    def saving(path, value):
        result = original(path, value)
        if str(path).endswith(forward.document_path(block.study)):
            monkeypatch.setattr(forward, "now", lambda: late)
        return result

    monkeypatch.setattr(forward, "save", saving)
    with pytest.raises(ValueError, match="deadline"):
        forward.stage(block.study)
    _, output = forward.locations(block.study)
    assert (block.root / forward.document_path(block.study)).exists()
    assert len(list(output.glob("staging-failure-*.json"))) == 1


@pytest.mark.parametrize("timely", [True, False])
def test_witness_after_event_uses_server_merge_clock(block, monkeypatch, timely):
    forward.run(block.study)
    forward.stage(block.study)
    _, raw, receipt = forward.verify_local(block.study)
    late = github.timestamp(
        block.protocol["races"][0]["feature_cutoff_at"]
    ) + timedelta(days=1)

    class FutureClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return late

    monkeypatch.setattr(publication, "datetime", FutureClock)
    monkeypatch.setattr(forward, "now", lambda: late)
    merged = (
        github.timestamp(receipt["observed_at"]) + timedelta(seconds=1)
        if timely
        else late
    )

    def capture_later(directory, number, document, digest):
        return archive_publication(directory, raw, number, document, merged, late)

    monkeypatch.setattr(publication, "capture", capture_later)
    result = forward.witness(block.study, 901)
    assert result["status"] == (
        "published_before_cutoff" if timely else "published_after_cutoff"
    )
    assert not result["counts_as_70_percent_evidence"]
    assert forward.verify_local(block.study)[1] == raw


@pytest.mark.parametrize(
    "field",
    [
        "horizon",
        "sample_size_rationale",
        "uncertainty",
        "stopping",
        "prediction_failure_scoring",
        "prior_block_history_policy",
    ],
)
def test_each_statistical_policy_is_required(block, field):
    del block.protocol[field]
    block.persist()
    with pytest.raises(ValueError, match="statistical_protocol"):
        contract.admit(block.study)


def test_modified_protocol_witness_cannot_be_replayed(block):
    forward.run(block.study)
    ledger, _ = forward.locations(block.study)
    (ledger / "protocol-publication/published-document.md").write_bytes(b"different")
    with pytest.raises(ValueError, match="publication_evidence"):
        forward.stage(block.study)


def test_runtime_changed_after_inference_cannot_publish(block):
    forward.run(block.study)
    block.runtime["synthetic_environment"] = "changed"
    with pytest.raises(ValueError, match="runtime_or_policy"):
        forward.stage(block.study)


def test_registry_must_preserve_exact_canonical_bytes(block):
    path = block.root / contract.REGISTRY
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="registry_not_canonical"):
        contract.admit(block.study)


def test_cli_environment_failure_is_blocked_not_success(block, monkeypatch, capsys):
    def unavailable():
        raise subprocess.CalledProcessError(1, "synthetic environment probe")

    monkeypatch.setattr(contract, "runtime", unavailable)
    assert forward.main(["inspect"]) == 2
    assert parse_json(capsys.readouterr().out)["status"] == "blocked"
