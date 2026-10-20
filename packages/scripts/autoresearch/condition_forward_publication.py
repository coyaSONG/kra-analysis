"""Bounded live GitHub witnesses and replay of their preserved responses."""

from datetime import UTC, datetime

import httpx

from autoresearch import condition_forward_contract as contract
from autoresearch.condition_training import save
from autoresearch.prerace_hash_witness import (
    collect_publication,
    timestamp,
    validate_publication,
)
from autoresearch.restricted_cohort import parse_json, sha256

ARCHIVE_FILES = (
    "pull.json",
    "document-response.json",
    "observed.json",
    "published-document.md",
)


def replay(directory, number, document, expected_sha):
    return replay_contents(
        {name: contract.training.read(directory / name) for name in ARCHIVE_FILES},
        number,
        document,
        expected_sha,
    )


def replay_contents(contents, number, document, expected_sha):
    """Verify one already-read archive without mutable file rereads."""
    pull_raw = contents["pull.json"]
    content_raw = contents["document-response.json"]
    pull = parse_json(pull_raw)
    raw, witness = validate_publication(
        pull, parse_json(content_raw), number=number, document=document
    )
    observed = parse_json(contents["observed.json"])
    if (
        pull.get("base", {}).get("ref") != "main"
        or sha256(raw) != expected_sha
        or any(observed.get(k) != v for k, v in witness.items())
        or observed["pull_response_sha256"] != sha256(pull_raw)
        or observed["document_response_sha256"] != sha256(content_raw)
        or contents["published-document.md"] != raw
        or not timestamp(witness["merged_at"])
        <= timestamp(observed["retrieved_at"])
        <= datetime.now(UTC)
    ):
        raise ValueError("forward_publication_evidence_conflict")
    return raw, observed


def capture(directory, number, document, expected_sha):
    directory.mkdir(parents=True, exist_ok=False)
    with httpx.Client(timeout=30, follow_redirects=False, trust_env=False) as client:
        _, observed = collect_publication(
            directory, number=number, document=document, client=client
        )
    save(directory / "observed.json", observed)
    return replay(directory, number, document, expected_sha)
