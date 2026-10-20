"""Entirely synthetic review evidence; creates no remote approval or authority."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from autoresearch import condition_review_evidence as review
from autoresearch import condition_semantic_contract as contract
from autoresearch import condition_semantic_review as audit
from autoresearch.condition_forward_publication import ARCHIVE_FILES
from autoresearch.prerace_hash_witness import API_ROOT, REPOSITORY
from autoresearch.restricted_cohort import encoded, parse_json, sha256
from autoresearch.tests.condition_forward_fixture import (
    archive_publication,
    public_payload,
)

NOW = datetime(2026, 10, 20, 15, tzinfo=UTC)


def stamp(hours):
    return (NOW + timedelta(hours=hours)).isoformat()


def actor(uid, login):
    return {"id": uid, "login": login, "type": "User"}


def bundle(root, modify=lambda value: None):
    def save(name, value):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = value if isinstance(value, bytes) else encoded(value)
        path.write_bytes(raw)
        return {"path": name, "sha256": sha256(raw)}

    body = save("source/body.txt", b"SYNTHETIC: the entire named race is cancelled.")
    capture = {
        "format_version": "condition-official-text-capture-v1",
        "url": "https://race.kra.co.kr/synthetic-notice",
        "status": 200,
        "fetch_started_at": stamp(-3),
        "capture_completed_at": stamp(-3),
        "content_type": "text/plain",
        "encoding": "utf-8",
        "body": body,
    }
    registry = {
        "format_version": "condition-semantic-authorities-v1",
        "policy_sha256": contract.POLICY_SHA,
        "created_at": stamp(-5),
        "reviewers": [
            {
                "account": actor(2002, "synthetic-reviewer"),
                "claim_types": sorted(contract.CLAIMS),
                "valid_from": stamp(-20),
                "valid_until": stamp(20),
            }
        ],
    }
    decision = {
        "format_version": "condition-semantic-decision-v1",
        "decision_id": "synthetic-only",
        "policy_sha256": contract.POLICY_SHA,
        "authority_sha256": None,
        "umbrella_sha256": "a" * 64,
        "authored_at": stamp(-2),
        "claim_type": "cancellation",
        "scope": {"race_dates": ["20261023"], "meets": [1]},
        "subjects": {"enrollment-one": "20261023_1_1"},
        "claim": {"effective_at": stamp(24)},
        "justification": "Synthetic fixture only; not a real official decision.",
        "sources": [
            {"capture_sha256": None, "excerpt": "the entire named race is cancelled."}
        ],
        "supersedes_decision_sha256": None,
    }

    def opinion(number, uid, login, submitted):
        return {
            "id": number + 100,
            "user": actor(uid, login),
            "state": "APPROVED",
            "submitted_at": submitted,
            "commit_id": "b" * 40,
            "pull_request_url": f"{API_ROOT}/pulls/{number}",
            "html_url": f"https://github.com/{REPOSITORY}/pull/{number}#pullrequestreview-{number + 100}",
            "body": None,
        }

    value = SimpleNamespace(
        registry=registry,
        decision=decision,
        capture=capture,
        owner=opinion(900, contract.OWNER[0], "coyaSONG", stamp(-4)),
        delegate=opinion(901, 2002, "synthetic-reviewer", stamp(-1.5)),
        authority_author=actor(3001, "synthetic-registry-author"),
        decision_author=actor(2001, "synthetic-author"),
        extra_reviews=[],
        reviewed_decision=None,
    )
    modify(value)
    capture_ref = save("source/capture.json", capture)
    decision["sources"][0]["capture_sha256"] = capture_ref["sha256"]

    def publication(kind, document, content, number, merged, author):
        directory = root / kind
        archive_publication(directory, encoded(content), number, document, merged, NOW)
        pull = parse_json((directory / "pull.json").read_bytes())
        pull["user"] = author
        pull_pin = save(f"{kind}/pull.json", pull)
        observed = parse_json((directory / "observed.json").read_bytes())
        observed["pull_response_sha256"] = pull_pin["sha256"]
        save(f"{kind}/observed.json", observed)
        return {
            "pull_number": number,
            "document": document,
            "sha256": sha256(encoded(content)),
            "files": {
                n: {
                    "path": f"{kind}/{n}",
                    "sha256": sha256((directory / n).read_bytes()),
                }
                for n in ARCHIVE_FILES
            },
        }

    authority = publication(
        "authority",
        contract.AUTHORITY_PATH,
        registry,
        900,
        NOW - timedelta(hours=3.5),
        value.authority_author,
    )
    decision["authority_sha256"] = authority["sha256"]
    published = publication(
        "decision",
        "docs/research/semantic-decisions/synthetic-only.json",
        decision,
        901,
        NOW - timedelta(hours=1),
        value.decision_author,
    )

    def approval(name, ref, opinion, document, commitment, extra=()):
        if opinion["body"] is None:
            opinion["body"] = encoded(commitment).decode()
        _, content = public_payload(
            encoded(document), ref["pull_number"], ref["document"], NOW
        )
        content["html_url"] = (
            f"https://github.com/{REPOSITORY}/blob/{opinion['commit_id']}/{ref['document']}"
        )
        listing = save(f"{name}/reviews.json", [opinion, *extra])
        original = save(f"{name}/content.json", content)
        return save(
            f"{name}/capture.json",
            {
                "format_version": review.VERSION,
                "repository": REPOSITORY,
                "pull_number": ref["pull_number"],
                "review_id": opinion["id"],
                "observed_at": stamp(0),
                "reviews": {
                    "url": f"{API_ROOT}/pulls/{ref['pull_number']}/reviews?per_page=100&page=1",
                    "status": 200,
                    "response": listing,
                },
                "reviewed_content": {
                    "url": f"{API_ROOT}/contents/{ref['document']}?ref={opinion['commit_id']}",
                    "status": 200,
                    "response": original,
                },
            },
        )

    owner_ref = approval(
        "owner-review",
        authority,
        value.owner,
        registry,
        audit.commitment(authority["sha256"]),
    )
    delegate_ref = approval(
        "delegate-review",
        published,
        value.delegate,
        value.reviewed_decision if value.reviewed_decision is not None else decision,
        audit.commitment(
            published["sha256"], authority=authority["sha256"], umbrella="a" * 64
        ),
        value.extra_reviews,
    )
    manifest = {
        "format_version": audit.VERSION,
        "as_of": stamp(0.1),
        "umbrella_sha256": "a" * 64,
        "authority": authority,
        "authority_review": owner_ref,
        "decision": published,
        "decision_review": delegate_ref,
        "sources": {capture_ref["sha256"]: capture_ref},
    }
    return SimpleNamespace(
        root=root,
        path=root / "manifest.json",
        pin=save("manifest.json", manifest),
        manifest=manifest,
        values=value,
        save=save,
    )


def later_review(value, state):
    later = deepcopy(value.delegate)
    later.update(id=1002, state=state, submitted_at=stamp(-0.5))
    later["html_url"] = (
        f"https://github.com/{REPOSITORY}/pull/901#pullrequestreview-1002"
    )
    value.extra_reviews.append(later)
