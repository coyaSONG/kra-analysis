"""Offline, fixed-scope companion to the October 20 source feasibility note."""

import argparse
import json
from pathlib import Path

from autoresearch.kra_race_card_pdf_bundle import _feature_projection, _identity
from autoresearch.kra_race_card_pdf_replay import replay_race_card_snapshot, sha256
from autoresearch.prerace_hash_witness import DOCUMENT, timestamp, validate_publication
from shared.kra_entry_sheet import parse_entry_sheet_page
from shared.operational_cutoff import classify_source_snapshot_for_t30

SELECTED = (
    (
        "history-api26-control/20260705_1_1/"
        "entries_20261012T125933.573076Z_0b2e3451f825/entry_capture.json",
        "fbe1cded97445d1e6d371a32f77f4fd2d602f290db557d52ad81730b6fd427b2",
    ),
    (
        "observed-history-20261011/entries/20260824_4_1/"
        "entries_20261011T133612.371028Z_5048d9482f73/entry_capture.json",
        "bb8536dacc870064009810d3ac4ea717ed912532067cd3d81728a05fd781da6a",
    ),
    (
        "observed-history-20261011/entries/20260825_4_1/"
        "entries_20261011T133616.689686Z_10118bd4030d/entry_capture.json",
        "d11bc7488ede5c611615c97650f347676ad3e9a62436351470082859a45e1d09",
    ),
)


def checked(path, digest):
    raw = path.read_bytes()
    if sha256(raw) != digest:
        raise ValueError("source_hash_mismatch")
    return raw


def inspect(research, original):
    cache = research / ".cache/autoresearch"
    observations = []
    for relative, pin in SELECTED:
        path = cache / relative
        manifest = json.loads(checked(path, pin))
        race_id = path.parent.parent.name
        identity = _identity(race_id)
        assert all(manifest[key] == value for key, value in identity.items())
        assert manifest["entry_snapshot"] is None
        pages = []
        for page in manifest["pages"]:
            raw_path = Path(page["raw_path"])
            assert raw_path.resolve().parent == path.resolve().parent
            raw = checked(raw_path, page["sha256"])
            assert len(raw) == page["byte_count"]
            params = page["request_parameters"]
            assert params["rc_date"] == identity["race_date"]
            assert params["meet"] == identity["meet"]
            assert params["rc_no"] == identity["race_no"]
            payload = json.loads(raw)
            rows, total = parse_entry_sheet_page(
                payload, page_no=params["pageNo"], page_size=params["numOfRows"]
            )
            assert rows == [] and total == page["row_count"] == 0
            pages.append({"sha256": page["sha256"], "api_code": "00", "rows": 0})
        observations.append(
            {
                "race_id": race_id,
                "manifest_sha256": pin,
                "fetch_started_at": manifest["fetch_started_at"],
                "collected_at": manifest["collected_at"],
                "recorded_error": manifest["error"],
                "classification": "empty_unconfirmed" if pages else "unknown_response",
                "pages": pages,
            }
        )

    witness_dir = cache / ("prerace-hash-witness/20261011T121531.534487Z_c6c93a9ac319")
    document, witness = validate_publication(
        json.loads((witness_dir / "pull.json").read_bytes()),
        json.loads((witness_dir / "document-response.json").read_bytes()),
        number=61,
        document=DOCUMENT,
    )
    assert document == (witness_dir / "published-document.md").read_bytes()
    bundle_dir = cache / "race_card_pdf_bundles/20261009T165933.854898Z_51a041eda9e6"
    plan_raw = checked(
        bundle_dir / "input_plan.json",
        "0ac4a309d07901d6f4da8c4503c937fee9529fb5e05871cfdcd5252116a52be0",
    )
    bundle_raw = checked(
        bundle_dir / "feature_bundle.json",
        "8061a185401bf72c4bfee2751529acb164b695eb2985dbf4d6a43e187a8ecdd6",
    )
    for raw in (plan_raw, bundle_raw):
        assert ("`" + sha256(raw) + "`").encode() in document
    plan, bundle = json.loads(plan_raw), json.loads(bundle_raw)
    assert bundle["input_plan_sha256"] == sha256(plan_raw)
    record = plan["races"][0]
    assert record["race_id"] == "20261010_1_1"
    identity = _identity(record["race_id"])
    replay = replay_race_card_snapshot(
        record["manifest_path"],
        archive_root=original,
        expected_sha256=record["manifest_sha256"],
        expected_identity=identity,
        expected_pdf_sha256=record["pdf_sha256"],
        expected_entry_manifest_sha256=record["entry_manifest_sha256"],
    )
    assert replay["eligible_for_prerace_features"] and not replay["reasons"]
    assert replay["evidence"].get("pdf") and replay["evidence"].get("entry")
    rows = [_feature_projection(row, replay) for row in replay["feature_rows"]]
    saved = [r for r in bundle["feature_rows"] if r["race_id"] == record["race_id"]]
    assert sorted(rows, key=lambda r: r["chulNo"]) == sorted(
        saved, key=lambda r: r["chulNo"]
    )
    merged = timestamp(witness["merged_at"])
    assert timestamp(replay["features_available_at"]) <= merged
    assert timestamp(plan["pinned_at"]) <= merged
    assert timestamp(bundle["exported_at"]) <= merged
    timing = classify_source_snapshot_for_t30(
        race_date=identity["race_date"],
        scheduled_start_time=replay["scheduled_start_time"],
        source_snapshot_at=merged,
    )
    assert timing.passed
    return {
        "selected_requests": observations,
        "new_usable_packets": 0,
        "positive_control": {
            "race_id": record["race_id"],
            "feature_rows": len(rows),
            "raw_chain_and_projection_verified": True,
            "publication_before_cutoff": True,
            "merged_at": witness["merged_at"],
            "document_sha256": witness["document_sha256"],
            "trust_basis": "offline_replay_of_preserved_github_metadata_not_live_fetch",
        },
        "training_authorized": False,
        "future_registration": False,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--research-root", type=Path, required=True)
    parser.add_argument("--original-root", type=Path, required=True)
    args = parser.parse_args()
    if not __debug__:
        raise RuntimeError("assertions_must_be_enabled")
    print(json.dumps(inspect(args.research_root, args.original_root), indent=2))
