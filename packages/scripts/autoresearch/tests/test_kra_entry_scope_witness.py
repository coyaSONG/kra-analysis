"""Full input marker, merge-clock and preserved-provider regression tests."""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import kra_entry_scope_witness as witness
from autoresearch import prerace_hash_witness as github
from autoresearch.observed_history_seed import pin
from autoresearch.restricted_cohort import encoded, sha256
from autoresearch.tests.condition_forward_fixture import (
    archive_publication,
    public_payload,
)
from autoresearch.tests.test_kra_entry_scope_intake import (
    DUE,
    TEST_KEY,
    common_error,
    model_gateway,
    run,
)
from autoresearch.tests.test_kra_schedule import DATE, NOW, capture

PULL = 906
AFTER = DUE + timedelta(days=1)


class ProviderClock(datetime):
    @classmethod
    def now(cls, tz=None):
        return AFTER.astimezone(tz) if tz is not None else AFTER.replace(tzinfo=None)


@pytest.fixture
def intake(tmp_path, monkeypatch):
    monkeypatch.setattr(witness, "now", lambda: AFTER)
    monkeypatch.setattr(witness.publication, "datetime", ProviderClock)
    monkeypatch.setattr(github, "datetime", ProviderClock)
    scope = tmp_path, pin(tmp_path, capture(tmp_path / "schedule"))
    (path, result), calls = run(scope, provide=model_gateway)
    assert result["status"] == "captured_locally"
    assert len(calls) == 4
    original = {
        "schedule_sha256": scope[1]["sha256"],
        "first_cutoff": DUE.isoformat(),
    }
    return tmp_path, pin(tmp_path, path), original, path


def stage(intake, *, clock=lambda: NOW):
    root, receipt, original, path = intake
    marker = witness.stage(root, receipt, **original, clock=clock)
    return marker, path.with_name(witness.PACKET_NAME)


def readback(intake, digest, **kwargs):
    root, receipt, original, _ = intake
    return witness.verify(
        root,
        receipt,
        **original,
        packet_sha256=digest,
        **({"pull": PULL} | kwargs),
    )


def provider_archive(intake, marker, digest, merged):
    archive = intake[-1].with_name(witness.ARCHIVE_NAME)
    archive_publication(
        archive, marker, PULL, witness.publication_document(digest), merged, AFTER
    )
    return archive


def test_mock_provider_reads_exact_merge_and_replay_never_calls_again(
    intake, monkeypatch
):
    root, receipt, original, _ = intake
    marker, private = stage(intake)
    raw = private.read_bytes()
    digest = sha256(raw)
    assert marker == encoded({"format": witness.MARKER_FORMAT, "packet_sha256": digest})
    assert TEST_KEY.encode() not in raw
    assert str(root).encode() not in raw
    assert b"horse_id" not in raw and b"feature_rows" not in raw
    packet = json.loads(raw)
    assert packet["intake_receipt"] == receipt
    assert packet["schedule"]["sha256"] == original["schedule_sha256"]
    assert packet["first_block_cutoff"] == original["first_cutoff"]
    assert packet["race_count"] == 4 and packet["declaration_count"] == 40
    assert packet["feature_missing_counts"]["rating"] == 4
    assert {row["race_id"] for row in packet["races"]} == {
        f"{DATE}_{meet}_1" for meet in range(1, 5)
    }
    assert len({row["binding_sha256"] for row in packet["races"]}) == 4

    document = witness.publication_document(digest)
    merged = NOW + timedelta(hours=1)
    pull, content = public_payload(marker, PULL, document, merged)
    routes = {
        f"{github.API_ROOT}/pulls/{PULL}": pull,
        f"{github.API_ROOT}/contents/{document}?ref={pull['merge_commit_sha']}": content,
    }
    calls = []

    def respond(request):
        url = str(request.url)
        assert request.method == "GET" and "authorization" not in request.headers
        calls.append(url)
        return httpx.Response(200, json=routes[url])

    client = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kwargs: client(transport=httpx.MockTransport(respond), **kwargs),
    )
    result = readback(intake, digest, capture=True)
    assert calls == list(routes)
    assert result["state"] == "content_bound_before_cutoff"
    assert result["publication"]["merged_at"] == merged.isoformat()
    assert result["publication"]["retrieved_at"] == AFTER.isoformat()
    assert result["before_cutoff"] is True
    assert result["official_source_authenticated_by_publication"] is False
    assert result["training_or_study_approved"] is False
    assert result["prediction_publication_verified"] is False
    archives = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert result == readback(intake, digest)
    with pytest.raises(FileExistsError):
        readback(intake, digest, capture=True)
    with pytest.raises(FileExistsError):
        stage(intake)
    assert calls == list(routes)
    assert {p: p.read_bytes() for p in root.rglob("*") if p.is_file()} == archives


@pytest.mark.parametrize("offset", (0, 1))
def test_equal_or_later_merge_preserved_without_admission(intake, offset):
    marker, path = stage(intake)
    digest = sha256(path.read_bytes())
    provider_archive(intake, marker, digest, DUE + timedelta(seconds=offset))
    result = readback(intake, digest)
    assert result["state"] == "published_at_or_after_cutoff"
    assert result["before_cutoff"] is False
    assert result["race_count"] == 4


def test_impossible_pre_readback_merge_is_conflict(intake):
    marker, path = stage(intake)
    digest = sha256(path.read_bytes())
    provider_archive(intake, marker, digest, NOW - timedelta(seconds=1))
    with pytest.raises(ValueError, match="merge_before_readback"):
        readback(intake, digest)


def test_matching_path_with_changed_bytes_and_wrong_pull_are_rejected(intake):
    marker, path = stage(intake)
    digest = sha256(path.read_bytes())
    provider_archive(intake, marker + b" ", digest, NOW)
    with pytest.raises(ValueError, match="invalid_publication_pull"):
        readback(intake, digest, pull=PULL + 1)
    with pytest.raises(ValueError, match="forward_publication_evidence_conflict"):
        readback(intake, digest)


def test_changed_original_and_repinned_packet_fail_before_network(intake, monkeypatch):
    root, receipt, original, path = intake
    _, private = stage(intake)
    digest = sha256(private.read_bytes())
    monkeypatch.setattr(
        witness.publication,
        "capture",
        lambda *a: pytest.fail("unexpected provider read"),
    )
    wrong_original = original | {"schedule_sha256": "a" * 64}
    with pytest.raises(ValueError, match="original_schedule_conflict"):
        witness.verify(
            root,
            receipt,
            **wrong_original,
            packet_sha256=digest,
            pull=PULL,
            capture=True,
        )
    value = json.loads(private.read_bytes())
    private.write_bytes(encoded(value | {"race_count": 3}))
    with pytest.raises(ValueError, match="packet_does_not_replay"):
        readback(intake, sha256(private.read_bytes()), capture=True)
    assert not path.with_name(witness.ARCHIVE_NAME).exists()


def test_changed_raw_page_fails_before_network(intake):
    root, _, _, path = intake
    _, private = stage(intake)
    receipt = json.loads(path.read_bytes())
    page = root / receipt["scopes"][0]["evidence"]["pages"][0]["path"]
    page.write_bytes(page.read_bytes() + b" ")
    with pytest.raises(ValueError, match="sha256_mismatch"):
        readback(intake, sha256(private.read_bytes()), capture=True)
    assert not path.with_name(witness.ARCHIVE_NAME).exists()


def test_partial_collection_has_no_marker(tmp_path):
    scope = tmp_path, pin(tmp_path, capture(tmp_path / "schedule"))
    (path, report), calls = run(scope, provide=lambda _: common_error(200, "22"))
    assert len(calls) == 1
    assert report["stop_reason"] == "rate_limited"
    with pytest.raises(ValueError, match="requires_complete_local_receipt"):
        witness.stage(
            tmp_path,
            pin(tmp_path, path),
            schedule_sha256=scope[1]["sha256"],
            first_cutoff=DUE.isoformat(),
            clock=lambda: NOW,
        )
    assert not path.with_name(witness.PACKET_NAME).exists()


def test_stage_after_deadline_or_save_at_deadline_yields_no_marker(intake):
    with pytest.raises(ValueError, match="readback_outside_deadline"):
        stage(intake, clock=lambda: DUE)
    path = intake[-1].with_name(witness.PACKET_NAME)
    assert not path.exists()
    phases = iter((NOW, NOW, NOW, DUE))
    with pytest.raises(ValueError, match="stage_outside_original_cutoff"):
        stage(intake, clock=lambda: next(phases))
    assert path.is_file()


def test_replay_rejects_linked_provider_original(intake):
    marker, path = stage(intake)
    digest = sha256(path.read_bytes())
    archive = provider_archive(intake, marker, digest, NOW)
    observed = archive / "observed.json"
    alternate = observed.rename(archive / "alternate.json")
    observed.symlink_to(alternate)
    with pytest.raises(ValueError, match="archive_path_conflict"):
        readback(intake, digest)
