"""Collision evidence never becomes an automatic event-identity correction."""

import asyncio
import copy
import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import history_identity_audit as audit
from autoresearch import observed_history_seed as seed
from autoresearch.kra_result_snapshot import replay_result_pages, replay_result_snapshot
from autoresearch.tests.test_kra_result_snapshot import envelope, row
from autoresearch.tests.test_observed_history_seed import execute, response


def source(tmp_path, *, ambiguous=False, no_match=False):
    root = tmp_path / "source"
    root.mkdir()
    seed.save(root / "plan.json", seed.make_plan("20261010", "20261011"))

    def handler(request):
        day, meet = request.url.params["rc_date"], int(request.url.params["meet"])
        entry = str(request.url.copy_with(query=None)) == seed.ENTRY_URL
        known = day == "20261010" and meet in ((1, 3) if ambiguous else (3,))
        unknown = day == "20261011" and meet == 4
        rows = []
        if (known or unknown) and not entry:
            rows = [row(n, rank=n) for n in (1, 2, 3)]
            for item in rows:
                item["rcDate"] = int(day)
                item["meet"] = meet
                if unknown:
                    item.pop("meet")
                    item["rcNo"] = 2
                    item["rcTime"] = 0
                    if no_match:
                        item["chulNo"] += 1
        return httpx.Response(200, json=envelope(rows))

    asyncio.run(execute(root, handler))
    path = root / "frozen.json"
    sha = seed.save(path, seed.replay(root))
    return root, path, sha


def test_full_raw_replay_without_venue_does_not_admit_identity(tmp_path):
    root, path, sha = source(tmp_path)
    before = {p: p.read_bytes() for p in root.rglob("*.json")}
    result = audit.audit_history(root, path, sha)
    assert len(result["inventory"]) == 8
    assert result["observed_race_count"] == 1
    assert result["observed_row_count"] == 3
    assert result["unbound_row_count"] == 3
    assert result["unbound_groups_with_matches"] == 1
    group = result["unbound_groups"][0]
    assert "race_id" not in group
    assert group["requested_meet"] == 4 and group["returned_race_no"] == 2
    assert group["matches"][0]["race_id"] == "20261010_3_1"
    assert group["matches"][0]["changed_field_row_counts"] == {
        "meet": 3,
        "rcDate": 3,
        "rcNo": 3,
        "rcTime": 3,
    }
    assert not result["automatic_identity_resolution_allowed"]
    assert not result["training_approved"]
    assert not result["counts_as_70_percent_evidence"]
    assert all(p.read_bytes() == raw for p, raw in before.items())
    unknown = next(
        r for r in result["inventory"] if r["status"] == "identity_unresolved"
    )
    capture = root / unknown["result"]["path"]
    raw = replay_result_pages(capture)
    assert len(raw["rows"]) == 3 and not raw["event_identity_verified"]
    with pytest.raises(ValueError, match="missing_result_venue"):
        replay_result_snapshot(capture)


def test_multiple_candidates_and_observed_collisions_remain_ambiguous(tmp_path):
    args = source(tmp_path, ambiguous=True)
    report = audit.audit_history(*args)
    assert report["unbound_groups_with_multiple_matches"] == 1
    assert len(report["unbound_groups"][0]["matches"]) == 2
    assert len(report["observed_collision_groups"]) == 2
    assert report["observed_collision_group_count"] == 2
    assert report["observed_collision_pair_count"] == 1
    assert report["observed_collision_row_count"] == 6
    assert report["source_review_required"]
    assert report["observed_row_count"] == 6
    assert all("race_id" not in g for g in report["unbound_groups"])


def test_changed_gates_do_not_count_as_full_roster_match(tmp_path):
    report = audit.audit_history(*source(tmp_path, no_match=True))
    assert report["unbound_group_count"] == 1
    assert report["unbound_groups_with_matches"] == 0
    assert report["unbound_groups"][0]["matches"] == []


def test_row_order_and_leading_zero_ids_have_same_membership():
    rows = [row(n) for n in (1, 2, 3)]
    other = copy.deepcopy(list(reversed(rows)))
    for r in other:
        r["hrNo"] = int(r["hrNo"])
    a = audit.group_rows(rows, "20261011")[1]
    b = audit.group_rows(other, "20261011")[1]
    assert audit.compare_fields(a, b)["changed_field_row_counts"] == {"hrNo": 3}
    with pytest.raises(ValueError, match="exact_roster"):
        audit.compare_fields(a, {k: v for k, v in b.items() if k[0] != 1})


def test_field_comparison_retains_absent_null_and_type_differences():
    key = (1, "101")
    a = {key: {"equal": 4, "absent": None, "kind": 1, "bool": True, "ord": 1}}
    b = {key: {"equal": 4, "kind": 1.0, "bool": 1, "ord": 2, "added": None}}
    result = audit.compare_fields(a, b)
    assert result["identical_fields_across_all_pairs"] == ["equal"]
    assert result["changed_field_row_counts"] == {
        "absent": 1,
        "added": 1,
        "bool": 1,
        "kind": 1,
        "ord": 1,
    }


@pytest.mark.parametrize(
    "field,value",
    [("rcDate", 20261010), ("rcNo", 0), ("hrNo", True), ("chulNo", 1.0)],
)
def test_invalid_within_capture_identity_rejected(field, value):
    item = row()
    item[field] = value
    with pytest.raises(ValueError):
        audit.group_rows([item], "20261011")


@pytest.mark.parametrize("duplicate", ["row", "gate", "horse"])
def test_duplicate_unbound_membership_is_not_silently_collapsed(duplicate):
    first, second = row(), row(2)
    if duplicate == "row":
        second = copy.deepcopy(first)
    elif duplicate == "gate":
        second["chulNo"] = first["chulNo"]
    else:
        second["hrNo"] = first["hrNo"]
    with pytest.raises(ValueError, match="duplicate_collision_runner"):
        audit.group_rows([first, second], "20261011")


@pytest.mark.parametrize("change", ["pin", "seed", "raw", "manifest", "new_receipt"])
def test_original_source_and_frozen_view_must_both_match(tmp_path, change):
    root, path, sha = source(tmp_path)
    frozen = json.loads(path.read_bytes())
    unit = next(r for r in frozen["inventory"] if r["status"] == "identity_unresolved")
    capture = root / unit["result"]["path"]
    manifest = json.loads(capture.read_bytes())
    if change == "pin":
        sha = "0" * 64
    elif change == "seed":
        frozen["records"].pop()
        path = root / "altered.json"
        sha = seed.save(path, frozen)
    elif change == "raw":
        (capture.parent / manifest["pages"][0]["raw_file"]).write_bytes(b"changed")
    elif change == "manifest":
        capture.write_bytes(capture.read_bytes() + b" ")
    else:
        receipt_path = root / "receipts/20261011_4/0001.json"
        receipt = json.loads(receipt_path.read_bytes())
        manifest["capture_completed_at"] = manifest["fetch_started_at"]
        replacement = capture.parent / "later.json"
        seed.save(replacement, manifest)
        receipt["result"] = seed.pin(root, replacement)
        seed.save(receipt_path.with_name("0002.json"), receipt)
    with pytest.raises(ValueError):
        audit.audit_history(root, path, sha)


def test_cli_is_deterministic_exclusive_and_never_rewrites_seed(tmp_path):
    root, path, sha = source(tmp_path)
    before = path.read_bytes()
    output = root / "audit.json"
    args = [
        "--root",
        str(root),
        "--seed",
        str(path),
        "--seed-sha256",
        sha,
        "--output",
        str(output),
    ]
    assert audit.main(args) == 0
    raw = output.read_bytes()
    assert json.loads(raw) == audit.audit_history(root, path, sha)
    with pytest.raises(FileExistsError):
        audit.main(args)
    assert output.read_bytes() == raw and path.read_bytes() == before


def test_relative_root_keeps_independent_entry_binding_valid(tmp_path, monkeypatch):
    root = tmp_path / "source"
    root.mkdir()
    seed.save(root / "plan.json", seed.make_plan("20261011", "20261011"))
    asyncio.run(execute(root, lambda r: response(r, missing_venue=True)))
    frozen = root / "frozen.json"
    sha = seed.save(frozen, seed.replay(root))
    monkeypatch.chdir(tmp_path)
    report = audit.audit_history(Path("source"), Path("source/frozen.json"), sha)
    assert report["observed_race_count"] == 4
    assert report["unbound_row_count"] == 0
    assert all(r["entry"] for r in report["source_pins"])


def test_failed_and_unattempted_units_are_retained_and_require_review(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    seed.save(root / "plan.json", seed.make_plan("20261011", "20261011"))
    asyncio.run(execute(root, lambda r: httpx.Response(503)))
    frozen = root / "frozen.json"
    sha = seed.save(frozen, seed.replay(root))
    report = audit.audit_history(root, frozen, sha)
    assert [r["status"] for r in report["inventory"]] == [
        "failed",
        "failed",
        "failed",
        "not_attempted",
    ]
    assert report["source_review_required"]
    assert report["observed_collision_group_count"] == 0
    assert report["unbound_group_count"] == 0
    assert not report["complete_actual_start_history_verified"]
