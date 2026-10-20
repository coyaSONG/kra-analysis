"""Verify archived account approval of exact published bytes, not their truth."""

import base64
import hashlib
import json
import re
from datetime import UTC, datetime

from autoresearch.condition_historical_publication import pin
from autoresearch.kra_race_card_pdf_replay import _invalid_constant, _unique_object
from autoresearch.prerace_hash_witness import API_ROOT, REPOSITORY, timestamp
from autoresearch.restricted_cohort import encoded, parse_json, sha256

VERSION = "condition-review-archive-v1"
OPINIONS = {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}


def account(value):
    if (
        type(value) is not dict
        or type(value.get("id")) is not int
        or value["id"] <= 0
        or type(value.get("login")) is not str
        or not re.fullmatch(r"[A-Za-z0-9-]{1,39}", value["login"])
        or value.get("type") != "User"
    ):
        raise ValueError("semantic_invalid_account")
    return value["id"], value["login"].lower()


def response(root, record, expected_url):
    if (
        type(record) is not dict
        or set(record) != {"url", "status", "response"}
        or record["url"] != expected_url
        or type(record["status"]) is not int
        or record["status"] != 200
    ):
        raise ValueError("semantic_review_response_identity")
    return json.loads(
        pin(root, record["response"]),
        object_pairs_hook=_unique_object,
        parse_constant=_invalid_constant,
    )


def reviewed_bytes(content, document, commit):
    if (
        content.get("type") != "file"
        or content.get("encoding") != "base64"
        or content.get("path") != document
        or content.get("html_url")
        != f"https://github.com/{REPOSITORY}/blob/{commit}/{document}"
    ):
        raise ValueError("semantic_reviewed_content_identity")
    raw = base64.b64decode("".join(content["content"].split()), validate=True)
    blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
    if (
        type(content["size"]) is not int
        or content["size"] != len(raw)
        or content["sha"] != blob
    ):
        raise ValueError("semantic_reviewed_content_blob")
    return raw


def verify(root, reference, publication, published, witness, commitment, as_of):
    """Missing files propagate to the audit; invalid evidence never becomes approval."""
    record = parse_json(pin(root, reference))
    if (
        set(record)
        != {
            "format_version",
            "repository",
            "pull_number",
            "review_id",
            "observed_at",
            "reviews",
            "reviewed_content",
        }
        or record["format_version"] != VERSION
        or record["repository"] != REPOSITORY
        or type(record["pull_number"]) is not int
        or record["pull_number"] != publication["pull_number"]
        or type(record["review_id"]) is not int
        or record["review_id"] <= 0
    ):
        raise ValueError("semantic_review_archive_schema")
    number = record["pull_number"]
    observed = timestamp(record["observed_at"])
    merged = timestamp(witness["merged_at"])
    if not merged <= observed <= as_of <= datetime.now(UTC):
        raise ValueError("semantic_review_observation_clock")
    reviews = response(
        root,
        record["reviews"],
        f"{API_ROOT}/pulls/{number}/reviews?per_page=100&page=1",
    )
    if type(reviews) is not list or len(reviews) >= 100:
        raise ValueError("semantic_review_page_not_complete")
    by_id, latest, previous = {}, {}, None
    for review in reviews:
        rid = review["id"]
        actor = account(review["user"])
        if type(rid) is not int or rid <= 0 or rid in by_id:
            raise ValueError("semantic_review_identity")
        if (
            review["pull_request_url"] != f"{API_ROOT}/pulls/{number}"
            or review["html_url"]
            != f"https://github.com/{REPOSITORY}/pull/{number}#pullrequestreview-{rid}"
        ):
            raise ValueError("semantic_review_url")
        state = review["state"]
        if state not in OPINIONS | {"COMMENTED", "PENDING"}:
            raise ValueError("semantic_review_state")
        if state == "PENDING":
            raise ValueError("semantic_unsubmitted_review_in_snapshot")
        submitted = timestamp(review["submitted_at"])
        if submitted > observed or previous is not None and submitted < previous:
            raise ValueError("semantic_review_list_clock")
        previous = submitted
        by_id[rid] = review
        if state in OPINIONS:
            latest[actor[0]] = review
    selected = by_id.get(record["review_id"])
    if selected is None:
        raise ValueError("semantic_selected_review_missing")
    actor = account(selected["user"])
    if (
        selected["state"] != "APPROVED"
        or latest.get(actor[0]) != selected
        or any(r["state"] == "CHANGES_REQUESTED" for r in latest.values())
        or timestamp(selected["submitted_at"]) > merged
    ):
        raise ValueError("semantic_review_not_current_approval")
    pull = parse_json(pin(root, publication["files"]["pull.json"]))
    if account(pull["user"])[0] == actor[0]:
        raise ValueError("semantic_reviewer_not_separate")
    if parse_json(selected["body"].encode("utf-8")) != commitment:
        raise ValueError("semantic_review_commitment")
    commit = selected["commit_id"]
    if type(commit) is not str or not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("semantic_review_commit")
    document = publication["document"]
    if not re.fullmatch(r"[A-Za-z0-9_./-]+", document):
        raise ValueError("semantic_document_path")
    content = response(
        root,
        record["reviewed_content"],
        f"{API_ROOT}/contents/{document}?ref={commit}",
    )
    if reviewed_bytes(content, document, commit) != encoded(published):
        raise ValueError("semantic_reviewed_bytes_changed")
    return {
        "reviewer_id": actor[0],
        "reviewer_login": actor[1],
        "review_id": selected["id"],
        "review_commit": commit,
        "reviewed_at": selected["submitted_at"],
        "observed_at": record["observed_at"],
        "document_sha256": sha256(encoded(published)),
        "review_archive_sha256": reference["sha256"],
        "evidence_kind": "archived_account_approval",
        "source_meaning_verified": False,
        "latest_remote_state_verified": False,
    }
