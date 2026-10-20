"""Synthetic historical archives only; no registered study or inference."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import httpx
import pytest
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from autoresearch import condition_forward as forward
from autoresearch import condition_forward_contract as contract
from autoresearch import condition_forward_publication as publication
from autoresearch import condition_historical_publication as historical
from autoresearch import condition_training as training
from autoresearch import condition_training_model as model
from autoresearch.restricted_cohort import encoded, parse_json, sha256
from autoresearch.tests.condition_forward_fixture import archive_publication


@pytest.fixture(autouse=True)
def no_live_operations(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("historical audit called a live operation")

    for owner, names in (
        (contract, ("admit", "runtime", "load_models")),
        (contract.training, ("git", "environment", "implementation")),
        (forward, ("run", "verify_local", "stage", "witness")),
        (training, ("run",)),
        (model, ("fit_once", "score")),
        (publication, ("capture",)),
        (httpx, ("Client",)),
        (LogisticRegression, ("fit",)),
        (StandardScaler, ("fit", "fit_transform")),
        (SimpleImputer, ("fit", "fit_transform")),
    ):
        for name in names:
            monkeypatch.setattr(owner, name, forbidden)


@pytest.fixture
def bundle(tmp_path):
    instant = datetime.now(UTC) - timedelta(seconds=1)

    def stamp(minutes):
        return (instant + timedelta(minutes=minutes)).isoformat()

    day = instant.strftime("%Y%m%d")
    study = "synthetic-history-only"
    protocol = {
        "format_version": "condition-forward-protocol-v1",
        "study_id": study,
        "created_at": stamp(-50),
        "race_dates": [day],
        "runtime": {
            "model_hashes": contract.MODEL_HASHES,
            "training_receipt_sha256": contract.RECEIPT_SHA,
            "fit_count": 0,
            "implementation": {"synthetic-original.py": "1" * 64},
            "environment": {"synthetic_only": True},
        },
        "races": [
            {
                "race_id": f"{day}_1_{n}",
                "feature_cutoff_at": stamp(-5 + (n - 1) * 60),
                "roster": [
                    {"horse_id": str(100 + h), "chul_no": h} for h in range(1, 5)
                ],
            }
            for n in (1, 2)
        ],
    }
    protocol_path = f"docs/research/protocols/{study}.json"
    review = {
        "study_id": study,
        "race_dates": [day],
        "reviewer": "synthetic archived review",
        "reviewed_at": stamp(-35),
        "protocol_publication_pr": 800,
        "protocol": {"path": protocol_path, "sha256": sha256(encoded(protocol))},
        "raw_source_closure_reviewed": True,
        "label_free_inputs_reviewed": True,
        "protocol_reviewed": True,
    }
    registry = {
        "format_version": "condition-forward-reviews-v1",
        "approved_studies": [review],
    }
    packet = {
        "format_version": "condition-forward-paired-v1",
        "study_id": study,
        "protocol_sha256": sha256(encoded(protocol)),
        "runtime_sha256": sha256(encoded(protocol["runtime"])),
        "model_hashes": contract.MODEL_HASHES,
        "training_receipt_sha256": contract.RECEIPT_SHA,
        "matrix_sha256": "2" * 64,
        "computed_at": stamp(-20),
        "actual_fit_count": 0,
        "race_count": 2,
        "runner_count": 8,
        "external_publication_verified": False,
        "counts_as_70_percent_evidence": False,
        "model_promoted": False,
        "races": [
            {
                "race_id": row["race_id"],
                "feature_cutoff_at": row["feature_cutoff_at"],
                "predictions": {
                    "A24": ["101", "102", "103"],
                    "B34": ["104", "102", "101"],
                },
            }
            for row in protocol["races"]
        ],
    }
    documents = {"protocol": protocol, "approval": registry, "prediction": packet}
    paths = {
        "protocol": protocol_path,
        "approval": contract.REGISTRY,
        "prediction": forward.document_path(study),
    }
    merges = dict(zip(historical.KINDS, (-40, -30, -10), strict=True))
    state = SimpleNamespace(
        root=tmp_path,
        protocol=protocol,
        review=review,
        registry=registry,
        packet=packet,
        documents=documents,
        paths=paths,
        merges=merges,
        instant=instant,
        stamp=stamp,
        revision=0,
    )

    def write():
        state.revision += 1
        root = tmp_path / str(state.revision)
        manifest = {"format_version": historical.VERSION, "study_id": study}
        for number, kind in enumerate(historical.KINDS, 800):
            raw = encoded(documents[kind])
            archive_publication(
                root / kind,
                raw,
                number,
                paths[kind],
                instant + timedelta(minutes=merges[kind]),
                instant,
            )
            manifest[kind] = {
                "pull_number": number,
                "document": paths[kind],
                "sha256": sha256(raw),
                "files": {
                    name: {
                        "path": f"{kind}/{name}",
                        "sha256": sha256((root / kind / name).read_bytes()),
                    }
                    for name in publication.ARCHIVE_FILES
                },
            }
        state.manifest = manifest
        state.path = root / "manifest.json"
        state.digest = training.save(state.path, manifest)
        return state.path, state.digest

    state.write = write
    write()
    return state


def snapshot(root):
    return {
        str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()
    }


def test_public_chain_readonly_and_never_scoring(bundle):
    before = snapshot(bundle.root)
    result = historical.audit(bundle.path, bundle.digest)
    assert result["status"] == "public_chain_replayed"
    assert result["declared_publication_slot"] is None
    assert result["selected_archive_matches_declared_slot"] is None
    assert result["all_selected_publications_before_declared_cutoff"]
    assert result["declared_race_count"] == 2
    assert all(
        item["status"] == "public_bytes_verified"
        for item in result["publications"].values()
    )
    for dimension in (
        "inference_validity",
        "raw_input_provenance",
        "submission_closure",
        "umbrella_population",
    ):
        assert result[dimension] == "not_verified"
    assert not result["usable_for_scoring"]
    assert not result["counts_as_70_percent_evidence"]
    assert not result["outcomes_loaded"]
    assert result["actual_fit_count"] == 0
    assert "accuracy" not in result and "denominator" not in result
    assert snapshot(bundle.root) == before


def with_v2_slot(bundle):
    bundle.protocol["format_version"] = "condition-forward-protocol-v2"
    bundle.protocol["publication_slot"] = {
        "repository": "coyaSONG/kra-analysis",
        "pull_number": 802,
        "document": bundle.paths["prediction"],
    }
    bundle.review["prediction_publication_pr"] = 802


def bind_changed_protocol(bundle):
    digest = sha256(encoded(bundle.protocol))
    bundle.review["protocol"]["sha256"] = digest
    bundle.packet["protocol_sha256"] = digest
    bundle.write()


def test_v2_original_slot_attribution_is_not_submission_closure(bundle, monkeypatch):
    with_v2_slot(bundle)
    bind_changed_protocol(bundle)
    monkeypatch.setattr(contract, "PROTOCOL_VERSION", "some-later-live-version")
    before = snapshot(bundle.root)
    result = historical.audit(bundle.path, bundle.digest)
    assert result["status"] == "public_chain_replayed"
    assert result["selected_archive_matches_declared_slot"] is True
    assert result["declared_publication_slot"] == bundle.protocol["publication_slot"]
    assert result["submission_closure"] == "not_verified"
    assert not result["usable_for_scoring"]
    assert snapshot(bundle.root) == before


@pytest.mark.parametrize(
    "change", ["other_pr", "approval_pr", "review", "missing", "repo", "path"]
)
def test_v2_historical_slot_conflicts_are_not_scores(bundle, change):
    with_v2_slot(bundle)
    slot = bundle.protocol["publication_slot"]
    if change == "other_pr":
        slot["pull_number"] = 803
    elif change == "approval_pr":
        slot["pull_number"] = 801
    elif change == "review":
        bundle.review["prediction_publication_pr"] = 803
    elif change == "missing":
        del bundle.protocol["publication_slot"]
    elif change == "repo":
        slot["repository"] = "other/repository"
    else:
        slot["document"] = "docs/research/other.json"
    bind_changed_protocol(bundle)
    with pytest.raises(ValueError, match="slot"):
        historical.audit(bundle.path, bundle.digest)


def test_v2_missing_prediction_is_pending_not_absence(bundle):
    with_v2_slot(bundle)
    bind_changed_protocol(bundle)
    (bundle.path.parent / "prediction/pull.json").unlink()
    result = historical.audit(bundle.path, bundle.digest)
    assert result["status"] == "pending_evidence"
    assert result["selected_archive_matches_declared_slot"] is True
    assert result["submission_closure"] == "not_verified"
    assert "proven_absent" not in encoded(result).decode()
    assert not result["usable_for_scoring"]


def test_current_files_and_failure_markers_do_not_change_history(bundle, monkeypatch):
    before = historical.audit(bundle.path, bundle.digest)
    current = bundle.root / "current-checkout"
    current.mkdir()
    monkeypatch.setattr(contract, "ROOT", current)
    (current / "registry.json").write_text('{"approved_studies": []}')
    (current / "failure.json").write_text('{"error": "later failure"}')
    (current / "unrelated-new-code.py").write_text("raise RuntimeError('changed')")
    after = historical.audit(bundle.path, bundle.digest)
    before.pop("audited_at")
    after.pop("audited_at")
    assert before == after


@pytest.mark.parametrize("kind", historical.KINDS)
@pytest.mark.parametrize("name", publication.ARCHIVE_FILES)
def test_missing_evidence_never_creates_failure(bundle, kind, name):
    (bundle.path.parent / kind / name).unlink()
    result = historical.audit(bundle.path, bundle.digest)
    assert result["status"] == "pending_evidence"
    assert result["publications"][kind] == {
        "status": "pending_evidence",
        "missing_files": [name],
    }
    assert all(
        result["publications"][other]["status"] == "public_bytes_verified"
        for other in historical.KINDS
        if other != kind
    )
    assert "proven_absent" not in encoded(result).decode()
    assert "proven_invalid" not in encoded(result).decode()
    assert not result["usable_for_scoring"]


@pytest.mark.parametrize("kind", historical.KINDS)
def test_corrupt_copy_blocks_not_original_invalid(bundle, kind):
    (bundle.path.parent / kind / "published-document.md").write_bytes(
        b"later corruption"
    )
    with pytest.raises(ValueError, match="historical_file_hash_mismatch"):
        historical.audit(bundle.path, bundle.digest)


def test_known_structural_conflict_not_hidden_by_other_missing_evidence(bundle):
    bundle.review["protocol"]["sha256"] = "3" * 64
    bundle.write()
    (bundle.path.parent / "prediction/pull.json").unlink()
    with pytest.raises(ValueError, match="historical_approval_binding"):
        historical.audit(bundle.path, bundle.digest)


@pytest.mark.parametrize("minutes,timely", [(-10, True), (-5, False), (-4, False)])
def test_whole_block_cutoff_and_late_retrieval(bundle, minutes, timely):
    bundle.merges["prediction"] = minutes
    bundle.write()
    result = historical.audit(bundle.path, bundle.digest)
    assert result["all_selected_publications_before_declared_cutoff"] is timely
    assert (
        result["publications"]["prediction"]["before_declared_whole_block_cutoff"]
        is timely
    )
    assert (
        result["publications"]["prediction"]["witness"]["retrieved_at"]
        > result["declared_whole_block_cutoff_at"]
    )
    assert "proven_late" not in encoded(result).decode()


@pytest.mark.parametrize(
    "triple",
    [
        ["101", "101", "102"],
        ["101", "0101", "102"],
        ["101", "102"],
        ["101", "102", "999"],
        [101, 102, 103],
        ["00101", "102", "103"],
        ["1" * 5000, "102", "103"],
        None,
    ],
)
def test_bad_arm_does_not_erase_other_arm_or_claim_inference(bundle, triple):
    bundle.packet["races"][0]["predictions"]["B34"] = triple
    bundle.write()
    result = historical.audit(bundle.path, bundle.digest)
    arms = result["selections"][0]["arms"]
    assert arms["A24"]["selection_shape_and_membership_verified"]
    assert not arms["B34"]["selection_shape_and_membership_verified"]
    assert arms["B34"]["published_selection"] == triple
    assert arms["A24"]["inference_validity"] == "not_verified"
    assert not result["usable_for_scoring"]


@pytest.mark.parametrize(
    "change",
    [
        "wrong_protocol_hash",
        "wrong_runtime",
        "wrong_model",
        "wrong_receipt",
        "extra_race",
        "missing_race",
        "duplicate_race",
        "changed_cutoff",
        "wrong_count",
        "wrong_runner_count",
        "fit_claim",
        "evidence_claim",
        "missing_arm",
    ],
)
def test_shared_prediction_conflicts_block(bundle, change):
    packet = bundle.packet
    if change == "wrong_protocol_hash":
        packet["protocol_sha256"] = "f" * 64
    elif change == "wrong_runtime":
        packet["runtime_sha256"] = "f" * 64
    elif change == "wrong_model":
        packet["model_hashes"] = {"A24": "f" * 64, "B34": "f" * 64}
    elif change == "wrong_receipt":
        packet["training_receipt_sha256"] = "f" * 64
    elif change == "extra_race":
        packet["races"].append(deepcopy(packet["races"][0]))
        packet["races"][-1]["race_id"] = packet["races"][-1]["race_id"][:-1] + "3"
    elif change == "missing_race":
        packet["races"].pop()
    elif change == "duplicate_race":
        packet["races"][1] = deepcopy(packet["races"][0])
    elif change == "changed_cutoff":
        packet["races"][0]["feature_cutoff_at"] = bundle.stamp(-1)
    elif change == "wrong_count":
        packet["race_count"] = 3
    elif change == "wrong_runner_count":
        packet["runner_count"] = 9
    elif change == "fit_claim":
        packet["actual_fit_count"] = True
    elif change == "evidence_claim":
        packet["counts_as_70_percent_evidence"] = True
    else:
        del packet["races"][0]["predictions"]["B34"]
    bundle.write()
    with pytest.raises(ValueError, match="historical_prediction"):
        historical.audit(bundle.path, bundle.digest)


@pytest.mark.parametrize(
    "change",
    [
        "duplicate_review",
        "wrong_protocol_pr",
        "wrong_protocol_path",
        "missing_flag",
        "empty_reviewer",
        "review_after_merge",
        "compute_before_approval",
        "compute_after_merge",
        "protocol_after_merge",
    ],
)
def test_approval_and_clocks_are_original_not_current(bundle, change):
    if change == "duplicate_review":
        bundle.registry["approved_studies"].append(deepcopy(bundle.review))
    elif change == "wrong_protocol_pr":
        bundle.review["protocol_publication_pr"] = 999
    elif change == "wrong_protocol_path":
        bundle.review["protocol"]["path"] = "docs/research/protocols/other.json"
    elif change == "missing_flag":
        bundle.review["raw_source_closure_reviewed"] = False
    elif change == "empty_reviewer":
        bundle.review["reviewer"] = ""
    elif change == "review_after_merge":
        bundle.review["reviewed_at"] = bundle.stamp(-29)
    elif change == "compute_before_approval":
        bundle.packet["computed_at"] = bundle.stamp(-31)
    elif change == "compute_after_merge":
        bundle.packet["computed_at"] = bundle.stamp(-9)
    else:
        bundle.protocol["created_at"] = bundle.stamp(-39)
    bundle.write()
    with pytest.raises(ValueError, match="historical_"):
        historical.audit(bundle.path, bundle.digest)


def test_review_before_protocol_merge_keeps_original_contract(bundle):
    bundle.review["reviewed_at"] = bundle.stamp(-45)
    bundle.write()
    assert (
        historical.audit(bundle.path, bundle.digest)["status"]
        == "public_chain_replayed"
    )


@pytest.mark.parametrize(
    "change",
    ["duplicate_race", "noncanonical_id", "duplicate_horse", "bad_date", "roster"],
)
def test_protocol_identity_rejected(bundle, change):
    protocol = bundle.protocol
    if change == "duplicate_race":
        protocol["races"][1] = deepcopy(protocol["races"][0])
    elif change == "noncanonical_id":
        protocol["races"][0]["race_id"] += "0"
        protocol["races"][0]["race_id"] = protocol["races"][0]["race_id"].replace(
            "_1_", "_01_"
        )
    elif change == "duplicate_horse":
        protocol["races"][0]["roster"][1]["horse_id"] = "0101"
    elif change == "bad_date":
        protocol["race_dates"] = []
    else:
        protocol["races"][0]["roster"] = protocol["races"][0]["roster"][:2]
    bundle.write()
    with pytest.raises(ValueError, match="historical_"):
        historical.audit(bundle.path, bundle.digest)


@pytest.mark.parametrize("path", ["../outside", "/tmp/outside", "a//b", "./a", "a\\b"])
def test_paths_cannot_escape_manifest(bundle, path):
    bundle.manifest["protocol"]["files"]["pull.json"]["path"] = path
    digest = training.save(bundle.path.parent / "bad-path.json", bundle.manifest)
    with pytest.raises(ValueError, match="historical_invalid_relative_path"):
        historical.audit(bundle.path.parent / "bad-path.json", digest)


def test_symlink_and_missing_manifest_are_blocked(bundle):
    source = bundle.path.parent / "protocol/pull.json"
    backup = source.with_name("backup.json")
    source.rename(backup)
    source.symlink_to(backup)
    with pytest.raises(ValueError, match="historical_symlink_evidence"):
        historical.audit(bundle.path, bundle.digest)
    with pytest.raises(FileNotFoundError):
        historical.audit(bundle.root / "missing-manifest.json", bundle.digest)


def test_manifest_hash_and_extra_authority_flags_rejected(bundle):
    with pytest.raises(ValueError, match="historical_manifest_hash_mismatch"):
        historical.audit(bundle.path, "0" * 64)
    bundle.manifest["population_verified"] = True
    path = bundle.path.parent / "extra-flag.json"
    digest = training.save(path, bundle.manifest)
    with pytest.raises(ValueError, match="historical_manifest_schema"):
        historical.audit(path, digest)


@pytest.mark.parametrize(
    "change", ["same_review_pr", "wrong_approval_path", "wrong_prediction_path"]
)
def test_manifest_cannot_redirect_publication_authority(bundle, change):
    manifest = bundle.manifest
    if change == "same_review_pr":
        manifest["approval"]["pull_number"] = manifest["protocol"]["pull_number"]
    elif change == "wrong_approval_path":
        manifest["approval"]["document"] = "docs/arbitrary-approval.json"
    else:
        manifest["prediction"]["document"] = forward.document_path("other-study")
    path = bundle.path.parent / "bad-authority.json"
    digest = training.save(path, manifest)
    with pytest.raises(ValueError, match="historical_publication_paths"):
        historical.audit(path, digest)


@pytest.mark.parametrize("change", ["repository", "base", "pull", "observed", "blob"])
def test_consistent_file_pins_do_not_bypass_github_evidence(bundle, change):
    directory = bundle.path.parent / "prediction"
    if change == "observed":
        name = "observed.json"
        value = parse_json((directory / name).read_bytes())
        value["retrieved_at"] = bundle.stamp(-11)
    elif change == "blob":
        name = "document-response.json"
        value = parse_json((directory / name).read_bytes())
        value["html_url"] = value["html_url"].replace("a" * 40, "b" * 40)
    else:
        name = "pull.json"
        value = parse_json((directory / name).read_bytes())
        if change == "repository":
            value["base"]["repo"]["full_name"] = "untrusted/repository"
        elif change == "base":
            value["base"]["ref"] = "another-branch"
        else:
            value["number"] = 999
    (directory / name).write_bytes(encoded(value))
    bundle.manifest["prediction"]["files"][name]["sha256"] = sha256(encoded(value))
    path = bundle.path.parent / "bad-github.json"
    digest = training.save(path, bundle.manifest)
    with pytest.raises(ValueError):
        historical.audit(path, digest)


def test_missing_plus_corrupt_archive_is_blocked_not_pending(bundle):
    (bundle.path.parent / "protocol/pull.json").unlink()
    (bundle.path.parent / "protocol/observed.json").write_bytes(b"damaged")
    with pytest.raises(ValueError, match="historical_file_hash_mismatch"):
        historical.audit(bundle.path, bundle.digest)


def test_cli_readonly_pending_and_blocked(bundle, capsys):
    args = ["--manifest", str(bundle.path), "--sha256", bundle.digest]
    before = snapshot(bundle.root)
    assert historical.main(args) == 0
    assert (
        parse_json(capsys.readouterr().out.encode())["status"]
        == "public_chain_replayed"
    )
    assert snapshot(bundle.root) == before
    (bundle.path.parent / "approval/pull.json").unlink()
    assert historical.main(args) == 2
    assert parse_json(capsys.readouterr().out.encode())["status"] == "pending_evidence"
    assert historical.main(args[:-1] + ["0" * 64]) == 2
    report = parse_json(capsys.readouterr().out.encode())
    assert report["status"] == "blocked"
    assert not report["usable_for_scoring"]
