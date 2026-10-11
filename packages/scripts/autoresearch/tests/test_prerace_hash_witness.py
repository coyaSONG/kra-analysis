"""A public commitment proves bounded existence, never source authenticity."""

import asyncio
import base64
import copy
import hashlib
import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import kra_race_card_pdf_bundle as bundle
from autoresearch import prerace_hash_witness as audit
from autoresearch.tests.race_card_pdf_capture_fixture import capture_chain
from autoresearch.tests.test_kra_race_card_pdf_bundle import plan_for


def encoded(value):
    return json.dumps(value, sort_keys=True, allow_nan=False).encode()


def publication(document, merged="2026-06-27T01:02:00Z"):
    commit = "a" * 40
    pull = {
        "number": 61,
        "state": "closed",
        "merged": True,
        "merged_at": merged,
        "merge_commit_sha": commit,
        "base": {"repo": {"full_name": audit.REPOSITORY}},
        "html_url": f"https://github.com/{audit.REPOSITORY}/pull/61",
    }
    content = {
        "type": "file",
        "encoding": "base64",
        "path": audit.DOCUMENT,
        "html_url": f"https://github.com/{audit.REPOSITORY}/blob/{commit}/{audit.DOCUMENT}",
        "content": base64.b64encode(document).decode(),
        "size": len(document),
        "sha": hashlib.sha1(
            b"blob " + str(len(document)).encode() + b"\0" + document
        ).hexdigest(),
    }
    return pull, content


def inputs(plan, archive, root, merged="2026-06-27T01:02:00Z"):
    plan_bytes = encoded(plan)
    archive = copy.deepcopy(archive)
    archive.update(
        input_plan_sha256=audit.sha256(plan_bytes),
        exported_at="2026-06-27T01:01:30+00:00",
    )
    archive_bytes = encoded(archive)
    document = f"Plan `{audit.sha256(plan_bytes)}` and bundle `{audit.sha256(archive_bytes)}`".encode()
    pull, content = publication(document, merged)
    raw, witness = audit.validate_publication(
        pull, content, number=61, document=audit.DOCUMENT
    )
    return {
        "plan_bytes": plan_bytes,
        "bundle_bytes": archive_bytes,
        "document_bytes": raw,
        "witness": witness,
        "archive_root": root,
    }


@pytest.fixture
def captured(tmp_path):
    pytest.importorskip("pdfplumber")
    chain = asyncio.run(capture_chain(tmp_path))
    plan = plan_for(chain)
    archive = bundle.build_bundle(plan, archive_root=tmp_path)
    return chain, plan, archive


def test_real_raw_replay_matches_published_projection_without_training_approval(
    captured, tmp_path
):
    _, plan, archive = captured
    report = audit.audit_archive(**inputs(plan, archive, tmp_path))
    assert report["raw_chain_verified_count"] == 1
    assert report["pre_cutoff_content_bound_count"] == 1
    assert report["source_review_candidate_count"] == 1
    assert report["candidate_feature_row_count"] == 2
    assert not report["training_approved"]
    assert not report["official_source_authenticated_by_github"]
    assert not report["prediction_registration_proven"]
    assert not report["counts_as_70_percent_evidence"]


@pytest.mark.parametrize(
    "change",
    [
        "unmerged",
        "wrong_repo",
        "wrong_pr",
        "naive_time",
        "wrong_commit",
        "branch_not_commit",
        "wrong_path",
        "blob_changed",
        "wrong_size",
    ],
)
def test_rejects_invalid_server_document_link(change):
    pull, content = publication(b"published")
    if change == "unmerged":
        pull["merged"] = False
    elif change == "wrong_repo":
        pull["base"]["repo"]["full_name"] = "other/repo"
    elif change == "wrong_pr":
        pull["number"] = 62
    elif change == "naive_time":
        pull["merged_at"] = "2026-06-27T01:00:00"
    elif change == "wrong_commit":
        pull["merge_commit_sha"] = "b" * 40
    elif change == "branch_not_commit":
        content["html_url"] = content["html_url"].replace("a" * 40, "main")
    elif change == "wrong_path":
        content["path"] = "unrelated.md"
    elif change == "blob_changed":
        content["content"] = base64.b64encode(b"different").decode()
    elif change == "wrong_size":
        content["size"] += 1
    with pytest.raises(ValueError):
        audit.validate_publication(pull, content, number=61, document=audit.DOCUMENT)


def test_git_client_dates_and_mutable_pull_body_are_not_evidence():
    pull, content = publication(b"actual document")
    pull.update(body="`" + "f" * 64 + "`", created_at="2000-01-01T00:00:00Z")
    raw, witness = audit.validate_publication(
        pull, content, number=61, document=audit.DOCUMENT
    )
    assert raw == b"actual document"
    assert witness["merged_at"] == "2026-06-27T01:02:00+00:00"


@pytest.mark.parametrize(
    "change",
    [
        "plan_bytes",
        "bundle_bytes",
        "document_bytes",
        "missing_pin",
        "inventory",
        "feature_membership",
    ],
)
def test_changed_or_incomplete_commitments_fail(captured, tmp_path, change):
    _, plan, archive = captured
    if change == "missing_pin":
        plan["races"][0]["entry_manifest_sha256"] = None
    elif change == "inventory":
        archive["races"].append(copy.deepcopy(archive["races"][0]))
    elif change == "feature_membership":
        archive["feature_rows"].append(copy.deepcopy(archive["feature_rows"][0]))
        archive["feature_row_count"] += 1
    kwargs = inputs(plan, archive, tmp_path)
    if change in ("plan_bytes", "bundle_bytes", "document_bytes"):
        kwargs[change] += b" "
    with pytest.raises(ValueError):
        audit.audit_archive(**kwargs)


@pytest.mark.parametrize(
    "change", ["late_merge", "raw_changed", "projection_changed", "original_blocked"]
)
def test_failed_race_remains_in_inventory(captured, tmp_path, change):
    chain, plan, archive = captured
    merged = "2026-06-27T01:02:00Z"
    if change == "late_merge":
        merged = "2026-06-27T01:06:00Z"
    elif change == "raw_changed":
        Path(chain["pdf"]["raw_path"]).write_bytes(b"tampered")
    elif change == "projection_changed":
        archive["feature_rows"][0]["features"]["training_minutes"] += 1
    elif change == "original_blocked":
        archive["races"][0]["eligible_for_prerace_features"] = False
    report = audit.audit_archive(**inputs(plan, archive, tmp_path, merged))
    assert report["race_count"] == len(report["ledger"]) == 1
    assert report["source_review_candidate_count"] == 0
    assert report["candidate_feature_row_count"] == 0
    assert report["ledger"][0]["reasons"]


def test_clock_contradiction_is_not_relabelled_as_earlier_capture(captured, tmp_path):
    _, plan, archive = captured
    with pytest.raises(ValueError, match="clock_after_publication"):
        audit.audit_archive(**inputs(plan, archive, tmp_path, "2026-06-27T01:00:00Z"))


def test_current_replay_drift_is_recorded_without_rewriting_original_plan(
    captured, tmp_path
):
    _, plan, archive = captured
    plan["implementation"]["python_version"] = "old"
    archive["implementation"] = copy.deepcopy(plan["implementation"])
    report = audit.audit_archive(**inputs(plan, archive, tmp_path))
    assert report["implementation_changed"]
    assert report["original_implementation"]["python_version"] == "old"
    assert report["source_review_candidate_count"] == 1
    assert not report["training_approved"]


def test_live_collector_pins_commit_not_main_and_saves_original_responses(tmp_path):
    pull, content = publication(b"evidence")
    requests = []

    def respond(request):
        requests.append(str(request.url))
        return httpx.Response(200, json=pull if len(requests) == 1 else content)

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        raw, witness = audit.collect_publication(
            tmp_path, number=61, document=audit.DOCUMENT, client=client
        )
    assert raw == b"evidence"
    assert requests[1].endswith("?ref=" + "a" * 40)
    assert witness["pull_response_sha256"] == audit.sha256(
        (tmp_path / "pull.json").read_bytes()
    )
    assert (tmp_path / "published-document.md").read_bytes() == raw
    assert audit.timestamp(witness["retrieved_at"]) > audit.timestamp(
        witness["merged_at"]
    )


@pytest.mark.parametrize("status", [301, 403, 404])
def test_failed_network_never_becomes_a_witness(tmp_path, status):
    with httpx.Client(
        transport=httpx.MockTransport(lambda request: httpx.Response(status))
    ) as client:
        with pytest.raises(ValueError, match="fetch_failed"):
            audit.collect_publication(
                tmp_path, number=61, document=audit.DOCUMENT, client=client
            )


def test_cli_runs_real_replay_with_synthetic_github_response(
    captured, tmp_path, monkeypatch, capsys
):
    _, plan, archive = captured
    kwargs = inputs(plan, archive, tmp_path)
    plan_path, archive_path = tmp_path / "plan.json", tmp_path / "bundle.json"
    plan_path.write_bytes(kwargs["plan_bytes"])
    archive_path.write_bytes(kwargs["bundle_bytes"])
    pull, content = publication(kwargs["document_bytes"])
    client_type = httpx.Client
    monkeypatch.setattr(
        audit.httpx,
        "Client",
        lambda **kw: client_type(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200, json=pull if request.url.path.endswith("/61") else content
                )
            )
        ),
    )
    assert (
        audit.main(
            [
                "--plan",
                str(plan_path),
                "--bundle",
                str(archive_path),
                "--archive-root",
                str(tmp_path),
                "--output-dir",
                str(tmp_path / "output"),
            ]
        )
        == 0
    )
    printed = json.loads(capsys.readouterr().out)
    assert printed["source_review_candidate_count"] == 1
    assert not json.loads(Path(printed["report_path"]).read_bytes())[
        "training_approved"
    ]
