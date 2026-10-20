"""Read-only provenance audit, NOT historical inference or outcome evaluation."""

from __future__ import annotations

import argparse
import re
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from shared.kra_race_identity import validate_race_identity

from autoresearch import condition_forward_publication as publication
from autoresearch import prerace_hash_witness as github
from autoresearch.condition_forward_contract import MODEL_HASHES, RECEIPT_SHA, REGISTRY
from autoresearch.kra_race_card_pdf_replay import checked_digest
from autoresearch.restricted_cohort import encoded, parse_json, sha256

VERSION = "condition-historical-publication-v1"
KINDS = ("protocol", "approval", "prediction")
LIMIT = 32 * 1024 * 1024


def relative(value):
    if (
        type(value) is not str
        or not value
        or "\\" in value
        or PurePosixPath(value).is_absolute()
        or any(p in ("", ".", "..") for p in value.split("/"))
    ):
        raise ValueError("historical_invalid_relative_path")
    return value


def read(path):
    if path.is_symlink() or any(p.is_symlink() for p in path.parents):
        raise ValueError("historical_symlink_evidence")
    with path.open("rb") as stream:
        raw = stream.read(LIMIT + 1)
    if len(raw) > LIMIT:
        raise ValueError("historical_oversized_evidence")
    return raw


def pin(root, record):
    if type(record) is not dict or set(record) != {"path", "sha256"}:
        raise ValueError("historical_invalid_file_pin")
    path = root / relative(record["path"])
    digest = checked_digest(record["sha256"])
    raw = read(path)
    if sha256(raw) != digest:
        raise ValueError("historical_file_hash_mismatch")
    return raw


def archive(root, reference):
    if (
        type(reference) is not dict
        or set(reference) != {"pull_number", "document", "sha256", "files"}
        or type(reference["pull_number"]) is not int
        or reference["pull_number"] <= 0
        or type(reference["files"]) is not dict
        or set(reference["files"]) != set(publication.ARCHIVE_FILES)
    ):
        raise ValueError("historical_invalid_archive_reference")
    relative(reference["document"])
    checked_digest(reference["sha256"])
    contents, missing = {}, []
    for name, record in reference["files"].items():
        try:
            contents[name] = pin(root, record)
        except FileNotFoundError:
            missing.append(name)
    if missing:
        return None, {"status": "pending_evidence", "missing_files": sorted(missing)}
    raw, witness = publication.replay_contents(
        contents,
        reference["pull_number"],
        reference["document"],
        reference["sha256"],
    )
    document = parse_json(raw)
    if raw != encoded(document):
        raise ValueError("historical_noncanonical_public_document")
    return document, {"status": "public_bytes_verified", "witness": witness}


def positive_id(value):
    try:
        return (
            type(value) is str
            and value.isascii()
            and value.isdecimal()
            and int(value) > 0
        )
    except ValueError:
        return False


def protocol_population(protocol, study):
    if (
        protocol["format_version"] != "condition-forward-protocol-v1"
        or protocol["study_id"] != study
        or not protocol["races"]
    ):
        raise ValueError("historical_protocol_identity")
    ids, rosters = [], {}
    for race in protocol["races"]:
        rid = race["race_id"]
        day, meet, number = rid.split("_")
        validate_race_identity(int(meet), day, int(number))
        if rid != f"{day}_{int(meet)}_{int(number)}" or day <= "20261018":
            raise ValueError("historical_noncanonical_race_id")
        ids.append(rid)
        horses = [r["horse_id"] for r in race["roster"]]
        numbers = [r["chul_no"] for r in race["roster"]]
        if (
            len(horses) < 3
            or not all(positive_id(h) for h in horses)
            or len({int(h) for h in horses}) != len(horses)
            or any(type(n) is not int or n <= 0 for n in numbers)
            or len(set(numbers)) != len(numbers)
        ):
            raise ValueError("historical_invalid_roster")
        rosters[rid] = horses
    if ids != sorted(set(ids)) or protocol["race_dates"] != sorted(
        {rid[:8] for rid in ids}
    ):
        raise ValueError("historical_protocol_population")
    cutoff = min(github.timestamp(r["feature_cutoff_at"]) for r in protocol["races"])
    if github.timestamp(protocol["created_at"]) >= cutoff:
        raise ValueError("historical_protocol_created_after_cutoff")
    return ids, rosters, cutoff


def approval_record(registry, protocol, reference, study):
    if registry["format_version"] != "condition-forward-reviews-v1":
        raise ValueError("historical_registry_format")
    records = registry["approved_studies"]
    reviews = [r for r in records if r["study_id"] == study]
    dates = [d for r in records for d in r["race_dates"]]
    if len(reviews) != 1 or len(dates) != len(set(dates)):
        raise ValueError("historical_registry_identity_or_overlap")
    review = reviews[0]
    if (
        review["protocol"]
        != {"path": reference["document"], "sha256": reference["sha256"]}
        or review["protocol_publication_pr"] != reference["pull_number"]
        or type(review["protocol_publication_pr"]) is not int
        or review["race_dates"] != protocol["race_dates"]
        or type(review.get("reviewer")) is not str
        or not review["reviewer"].strip()
        or any(
            review.get(name) is not True
            for name in (
                "raw_source_closure_reviewed",
                "label_free_inputs_reviewed",
                "protocol_reviewed",
            )
        )
    ):
        raise ValueError("historical_approval_binding")
    return review


def selections(packet, protocol, rosters):
    ids = list(rosters)
    if (
        packet["format_version"] != "condition-forward-paired-v1"
        or packet["study_id"] != protocol["study_id"]
        or packet["protocol_sha256"] != sha256(encoded(protocol))
        or packet["runtime_sha256"] != sha256(encoded(protocol["runtime"]))
        or packet["model_hashes"] != MODEL_HASHES
        or packet["training_receipt_sha256"] != RECEIPT_SHA
        or protocol["runtime"]["model_hashes"] != packet["model_hashes"]
        or protocol["runtime"]["training_receipt_sha256"] != RECEIPT_SHA
        or type(protocol["runtime"]["fit_count"]) is not int
        or protocol["runtime"]["fit_count"] != 0
        or type(packet["actual_fit_count"]) is not int
        or packet["actual_fit_count"] != 0
        or type(packet["race_count"]) is not int
        or packet["race_count"] != len(ids)
        or type(packet["runner_count"]) is not int
        or packet["runner_count"] != sum(map(len, rosters.values()))
        or [r["race_id"] for r in packet["races"]] != ids
        or [r["feature_cutoff_at"] for r in packet["races"]]
        != [r["feature_cutoff_at"] for r in protocol["races"]]
        or any(
            packet.get(name) is not False
            for name in (
                "external_publication_verified",
                "counts_as_70_percent_evidence",
                "model_promoted",
            )
        )
    ):
        raise ValueError("historical_prediction_envelope")
    checked_digest(packet["matrix_sha256"])
    rows = []
    for row in packet["races"]:
        if set(row["predictions"]) != set(MODEL_HASHES):
            raise ValueError("historical_prediction_arms")
        arms = {}
        for arm, triple in row["predictions"].items():
            valid = (
                type(triple) is list
                and len(triple) == 3
                and all(positive_id(h) for h in triple)
                and len({int(h) for h in triple}) == 3
                and set(triple) <= set(rosters[row["race_id"]])
            )
            arms[arm] = {
                "selection_shape_and_membership_verified": valid,
                "reason": None if valid else "malformed_or_out_of_roster",
                "published_selection": triple,
                "inference_validity": "not_verified",
            }
        rows.append({"race_id": row["race_id"], "arms": arms})
    return rows


def audit(manifest_path, expected_sha):
    path = Path(manifest_path).absolute()
    manifest_raw = read(path)
    if sha256(manifest_raw) != checked_digest(expected_sha):
        raise ValueError("historical_manifest_hash_mismatch")
    manifest = parse_json(manifest_raw)
    if (
        set(manifest) != {"format_version", "study_id", *KINDS}
        or manifest["format_version"] != VERSION
        or type(manifest["study_id"]) is not str
        or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", manifest["study_id"])
    ):
        raise ValueError("historical_manifest_schema")
    study = manifest["study_id"]
    if (
        not relative(manifest["protocol"]["document"]).startswith(
            "docs/research/protocols/"
        )
        or manifest["approval"]["document"] != REGISTRY
        or manifest["prediction"]["document"]
        != f"docs/research/commitments/condition-forward-v1/{study}/paired.json"
        or manifest["approval"]["pull_number"] == manifest["protocol"]["pull_number"]
    ):
        raise ValueError("historical_publication_paths_or_separate_review")
    documents, facts = {}, {}
    for kind in KINDS:
        documents[kind], facts[kind] = archive(path.parent, manifest[kind])
    result = {
        "format_version": VERSION,
        "scope": "archived_publication_chain_only_not_inference_or_outcomes",
        "status": "pending_evidence",
        "manifest_sha256": expected_sha,
        "study_id": study,
        "audited_at": datetime.now(UTC).isoformat(),
        "verifier_sha256": sha256(Path(__file__).read_bytes()),
        "publication_replay_sha256": sha256(Path(publication.__file__).read_bytes()),
        "github_validator_sha256": sha256(Path(github.__file__).read_bytes()),
        "publications": facts,
        "inference_validity": "not_verified",
        "raw_input_provenance": "not_verified",
        "submission_closure": "not_verified",
        "umbrella_population": "not_verified",
        "outcomes_loaded": False,
        "counts_as_70_percent_evidence": False,
        "usable_for_scoring": False,
        "actual_fit_count": 0,
    }
    protocol, registry, packet = (documents[k] for k in KINDS)
    if protocol is None:
        return result
    ids, rosters, cutoff = protocol_population(protocol, study)
    merges = {
        k: github.timestamp(facts[k]["witness"]["merged_at"])
        for k in KINDS
        if documents[k] is not None
    }
    created = github.timestamp(protocol["created_at"])
    if created > merges["protocol"]:
        raise ValueError("historical_publication_clock_conflict")
    if registry is not None:
        review = approval_record(registry, protocol, manifest["protocol"], study)
        if not created <= github.timestamp(review["reviewed_at"]) <= merges["approval"]:
            raise ValueError("historical_publication_clock_conflict")
    for kind in merges:
        facts[kind]["before_whole_block_cutoff"] = merges[kind] < cutoff
    result.update(
        declared_race_ids=ids,
        declared_race_count=len(ids),
        whole_block_cutoff_at=cutoff.isoformat(),
    )
    if packet is not None:
        computed = github.timestamp(packet["computed_at"])
        if (
            not merges["protocol"] <= computed <= merges["prediction"]
            or registry is not None
            and merges["approval"] > computed
        ):
            raise ValueError("historical_publication_clock_conflict")
        result.update(
            original_runtime_sha256=packet["runtime_sha256"],
            matrix_sha256=packet["matrix_sha256"],
            model_hashes=packet["model_hashes"],
            training_receipt_sha256=packet["training_receipt_sha256"],
            selections=selections(packet, protocol, rosters),
        )
    if all(document is not None for document in documents.values()):
        result.update(
            status="public_chain_replayed",
            all_selected_publications_before_cutoff=all(
                merged < cutoff for merged in merges.values()
            ),
        )
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args(argv)
    try:
        result = audit(args.manifest, args.sha256)
    except (ValueError, OSError, KeyError, TypeError, AttributeError) as exc:
        result = {
            "status": "blocked",
            "reason": str(exc),
            "scope": "archived_publication_chain_only_not_inference_or_outcomes",
            "counts_as_70_percent_evidence": False,
            "usable_for_scoring": False,
            "outcomes_loaded": False,
            "actual_fit_count": 0,
        }
    print(encoded(result).decode(), end="")
    return 0 if result["status"] == "public_chain_replayed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
