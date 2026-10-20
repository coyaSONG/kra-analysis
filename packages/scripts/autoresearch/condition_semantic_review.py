"""Read-only attestation audit; never registration, closure, fitting or scoring."""

import argparse
from datetime import UTC, datetime
from pathlib import Path

from autoresearch import condition_review_evidence as review
from autoresearch import condition_semantic_contract as contract
from autoresearch.condition_historical_publication import archive, pin, read
from autoresearch.kra_race_card_pdf_replay import checked_digest
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import encoded, parse_json, sha256

VERSION = "condition-semantic-review-v1"


def commitment(digest, *, authority=None, umbrella=None):
    body = {
        "format_version": "condition-semantic-review-commitment-v1",
        "document_sha256": digest,
        "policy_sha256": contract.POLICY_SHA,
    }
    if authority is not None:
        body.update(authority_sha256=authority, umbrella_sha256=umbrella)
    return body


def authority(registry, owner_review):
    if (
        set(registry) != {"format_version", "policy_sha256", "created_at", "reviewers"}
        or registry["format_version"] != "condition-semantic-authorities-v1"
        or registry["policy_sha256"] != contract.POLICY_SHA
        or type(registry["reviewers"]) is not list
        or (owner_review["reviewer_id"], owner_review["reviewer_login"])
        != contract.OWNER
    ):
        raise ValueError("semantic_authority_owner_or_schema")
    if timestamp(registry["created_at"]) > timestamp(owner_review["reviewed_at"]):
        raise ValueError("semantic_authority_clock")
    actors = {}
    for actor in registry["reviewers"]:
        if set(actor) != {"account", "claim_types", "valid_from", "valid_until"}:
            raise ValueError("semantic_authority_grant_schema")
        identity = review.account(actor["account"])
        claims = actor["claim_types"]
        if (
            identity[0] in actors
            or type(claims) is not list
            or not claims
            or any(type(c) is not str for c in claims)
            or claims != sorted(set(claims))
            or not set(claims) <= contract.CLAIMS
            or timestamp(actor["valid_from"]) >= timestamp(actor["valid_until"])
        ):
            raise ValueError("semantic_authority_grant")
        actors[identity[0]] = actor
    return actors


def audit(manifest_path, expected_sha):
    path = Path(manifest_path).absolute()
    manifest = parse_json(pin(path.parent, {"path": path.name, "sha256": expected_sha}))
    if (
        set(manifest)
        != {
            "format_version",
            "as_of",
            "umbrella_sha256",
            "authority",
            "authority_review",
            "decision",
            "decision_review",
            "sources",
        }
        or manifest["format_version"] != VERSION
        or type(manifest["sources"]) is not dict
        or manifest["authority"]["document"] != contract.AUTHORITY_PATH
        or manifest["authority"]["pull_number"] == manifest["decision"]["pull_number"]
    ):
        raise ValueError("semantic_manifest_schema")
    checked_digest(manifest["umbrella_sha256"])
    as_of = timestamp(manifest["as_of"])
    if as_of > datetime.now(UTC):
        raise ValueError("semantic_as_of_in_future")
    result = {
        "format_version": VERSION,
        "status": "pending_evidence",
        "manifest_sha256": expected_sha,
        "as_of": manifest["as_of"],
        "audited_at": datetime.now(UTC).isoformat(),
        "verifier_sha256": sha256(read(Path(__file__))),
        "review_verifier_sha256": sha256(read(Path(review.__file__))),
        "contract_verifier_sha256": sha256(read(Path(contract.__file__))),
        "policy_sha256": contract.POLICY_SHA,
        "evidence_kind": "unverified_interpretation",
        "source_semantics_fully_machine_verified": False,
        "umbrella_publication_verified": False,
        "full_population_verified": False,
        "denominator": None,
        "usable_for_scoring": False,
        "counts_as_70_percent_evidence": False,
        "actual_fit_count": 0,
        "outcomes_loaded": False,
        "registration_performed": False,
        "latest_remote_state_verified": False,
    }
    registry, reg_fact = archive(path.parent, manifest["authority"])
    decision, dec_fact = archive(path.parent, manifest["decision"])
    result["publications"] = {"authority": reg_fact, "decision": dec_fact}
    if registry is None or decision is None:
        return result
    for fact in (reg_fact, dec_fact):
        if timestamp(fact["witness"]["retrieved_at"]) > as_of:
            raise ValueError("semantic_publication_after_evidence_cutoff")
    authored = contract.claim(decision)
    if (
        decision["policy_sha256"] != contract.POLICY_SHA
        or decision["authority_sha256"] != manifest["authority"]["sha256"]
        or decision["umbrella_sha256"] != manifest["umbrella_sha256"]
        or manifest["decision"]["document"]
        != f"docs/research/semantic-decisions/{decision['decision_id']}.json"
        or timestamp(reg_fact["witness"]["merged_at"]) > authored
    ):
        raise ValueError("semantic_decision_binding")
    try:
        owner = review.verify(
            path.parent,
            manifest["authority_review"],
            manifest["authority"],
            registry,
            reg_fact["witness"],
            commitment(manifest["authority"]["sha256"]),
            as_of,
        )
        actors = authority(registry, owner)
        approved = review.verify(
            path.parent,
            manifest["decision_review"],
            manifest["decision"],
            decision,
            dec_fact["witness"],
            commitment(
                manifest["decision"]["sha256"],
                authority=manifest["authority"]["sha256"],
                umbrella=manifest["umbrella_sha256"],
            ),
            as_of,
        )
        actor = actors.get(approved["reviewer_id"])
        reviewed = timestamp(approved["reviewed_at"])
        if (
            actor is None
            or review.account(actor["account"])[1] != approved["reviewer_login"]
            or decision["claim_type"] not in actor["claim_types"]
            or not timestamp(actor["valid_from"])
            <= reviewed
            < timestamp(actor["valid_until"])
            or authored > reviewed
        ):
            raise ValueError("semantic_reviewer_not_authorized")
        if type(decision["sources"]) is not list or not decision["sources"]:
            raise ValueError("semantic_decision_sources")
        facts, seen = [], set()
        for source in decision["sources"]:
            if set(source) != {"capture_sha256", "excerpt"}:
                raise ValueError("semantic_decision_source_schema")
            digest = checked_digest(source["capture_sha256"])
            if digest in seen or manifest["sources"][digest]["sha256"] != digest:
                raise ValueError("semantic_source_binding")
            seen.add(digest)
            facts.append(
                contract.source(
                    path.parent,
                    manifest["sources"][digest],
                    source["excerpt"],
                    authored,
                )
            )
        if seen != set(manifest["sources"]):
            raise ValueError("semantic_unselected_source_pins")
    except FileNotFoundError as exc:
        result["missing_evidence"] = str(exc)
        return result
    result.update(
        status="attestation_replayed",
        evidence_kind="reviewer_attested_interpretation",
        authority_review=owner,
        decision_review=approved,
        decision_sha256=manifest["decision"]["sha256"],
        decision=decision,
        source_facts=facts,
        trust_basis="cooperative_operator_archived_github_and_official_https",
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
            "evidence_kind": "unverified_interpretation",
            "source_semantics_fully_machine_verified": False,
            "usable_for_scoring": False,
            "full_population_verified": False,
            "denominator": None,
            "counts_as_70_percent_evidence": False,
            "actual_fit_count": 0,
            "outcomes_loaded": False,
            "registration_performed": False,
        }
    print(encoded(result).decode(), end="")
    return 0 if result["status"] == "attestation_replayed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
