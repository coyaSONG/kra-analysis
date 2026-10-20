"""Narrow claim shapes and pinned source text; no population conclusions."""

from urllib.parse import urlsplit

from shared.kra_race_identity import validate_race_identity

from autoresearch.condition_historical_publication import pin
from autoresearch.condition_population_chain import identifier
from autoresearch.prerace_hash_witness import REPOSITORY, timestamp
from autoresearch.restricted_cohort import encoded, parse_json, sha256

CLAIMS = {
    "no_enrollable_races",
    "same_physical_event",
    "different_replacement_event",
    "postponement",
    "cancellation",
    "exhaustive_scope_listing",
}
OWNER = (66289470, "coyasong")
AUTHORITY_PATH = "data/contracts/condition_semantic_authorities_v1.json"
POLICY = {
    "format_version": "condition-semantic-policy-v1",
    "repository": REPOSITORY,
    "owner_account_id": OWNER[0],
    "owner_login": OWNER[1],
    "claim_types": sorted(CLAIMS),
    "owner_review_of_registry_required": True,
    "reviewer_must_differ_from_pr_author": True,
    "exact_reviewed_bytes_and_body_commitment_required": True,
    "review_snapshot": "one_complete_page_under_100_after_merge",
    "source_hosts": ["race.kra.co.kr", "www.kra.co.kr"],
    "source_semantics": "human_attestation_not_machine_implication",
    "authorizes_population_closure": False,
    "authorizes_training_or_inference": False,
}
POLICY_SHA = sha256(encoded(POLICY))


def race_id(value, scope):
    if type(value) is not str:
        raise ValueError("semantic_race_id")
    day, meet, number = value.split("_")
    validate_race_identity(int(meet), day, int(number))
    if value != f"{day}_{int(meet)}_{int(number)}":
        raise ValueError("semantic_noncanonical_race_id")
    if day not in scope["race_dates"] or int(meet) not in scope["meets"]:
        raise ValueError("semantic_race_outside_claim_scope")


def claim(decision):
    if (
        set(decision)
        != {
            "format_version",
            "decision_id",
            "policy_sha256",
            "authority_sha256",
            "umbrella_sha256",
            "authored_at",
            "claim_type",
            "scope",
            "subjects",
            "claim",
            "justification",
            "sources",
            "supersedes_decision_sha256",
        }
        or decision["format_version"] != "condition-semantic-decision-v1"
    ):
        raise ValueError("semantic_decision_schema")
    identifier(decision["decision_id"])
    kind, scope = decision["claim_type"], decision["scope"]
    if type(kind) is not str or kind not in CLAIMS:
        raise ValueError("semantic_claim_type")
    if type(scope) is not dict or set(scope) != {"race_dates", "meets"}:
        raise ValueError("semantic_scope_schema")
    days, meets = scope["race_dates"], scope["meets"]
    if (
        type(days) is not list
        or not days
        or any(type(d) is not str for d in days)
        or days != sorted(set(days))
        or type(meets) is not list
        or not meets
        or any(type(m) is not int or m <= 0 for m in meets)
        or meets != sorted(set(meets))
    ):
        raise ValueError("semantic_scope_values")
    for day in days:
        for meet in meets:
            validate_race_identity(meet, day, 1)
    subjects, value = decision["subjects"], decision["claim"]
    if type(subjects) is not dict or type(value) is not dict:
        raise ValueError("semantic_claim_schema")
    for subject, rid in subjects.items():
        identifier(subject)
        race_id(rid, scope)
    expected = (
        2
        if kind in {"same_physical_event", "different_replacement_event"}
        else 1
        if kind in {"postponement", "cancellation"}
        else 0
    )
    if len(subjects) != expected:
        raise ValueError("semantic_claim_subjects")
    keys = (
        {"new_race_id", "effective_at"}
        if kind == "postponement"
        else {"effective_at"}
        if kind == "cancellation"
        else {"race_ids"}
        if kind == "exhaustive_scope_listing"
        else set()
    )
    if set(value) != keys:
        raise ValueError("semantic_typed_claim_fields")
    if "effective_at" in value:
        timestamp(value["effective_at"])
    if "new_race_id" in value:
        race_id(value["new_race_id"], scope)
    if "race_ids" in value:
        ids = value["race_ids"]
        if (
            type(ids) is not list
            or not ids
            or any(type(r) is not str for r in ids)
            or ids != sorted(set(ids))
        ):
            raise ValueError("semantic_listing_ids")
        for rid in ids:
            race_id(rid, scope)
    if (
        type(decision["justification"]) is not str
        or not decision["justification"].strip()
    ):
        raise ValueError("semantic_justification_missing")
    # Supersession admission needs the previous decision's own evidence, not a hash alone.
    if decision["supersedes_decision_sha256"] is not None:
        raise ValueError("semantic_correction_requires_versioned_admission")
    return timestamp(decision["authored_at"])


def source(root, reference, excerpt, authored_at):
    receipt = parse_json(pin(root, reference))
    if (
        set(receipt)
        != {
            "format_version",
            "url",
            "status",
            "fetch_started_at",
            "capture_completed_at",
            "content_type",
            "encoding",
            "body",
        }
        or receipt["format_version"] != "condition-official-text-capture-v1"
    ):
        raise ValueError("semantic_source_capture_schema")
    url = urlsplit(receipt["url"])
    if (
        url.scheme != "https"
        or url.hostname not in POLICY["source_hosts"]
        or url.username is not None
        or url.password is not None
        or url.port not in (None, 443)
        or url.fragment
        or type(receipt["status"]) is not int
        or receipt["status"] != 200
        or receipt["content_type"] not in {"text/html", "text/plain"}
        or receipt["encoding"] not in {"utf-8", "euc-kr", "cp949"}
    ):
        raise ValueError("semantic_official_source_identity")
    completed = timestamp(receipt["capture_completed_at"])
    if not timestamp(receipt["fetch_started_at"]) <= completed <= authored_at:
        raise ValueError("semantic_source_clock")
    raw = pin(root, receipt["body"])
    if len(raw) > 5 * 1024 * 1024:
        raise ValueError("semantic_source_too_large")
    if type(excerpt) is not str or not excerpt.strip() or len(excerpt) > 4096:
        raise ValueError("semantic_source_excerpt")
    if excerpt not in raw.decode(receipt["encoding"]):
        raise ValueError("semantic_excerpt_not_in_original")
    return {
        "capture_sha256": reference["sha256"],
        "body_sha256": receipt["body"]["sha256"],
        "url": receipt["url"],
        "captured_at": completed.isoformat(),
        "literal_excerpt_present": True,
        "claim_implication_machine_verified": False,
    }
