"""Synthetic future source chain; never a registered research population."""

import base64
import hashlib
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from shared.kra_schedule import WEEKDAYS

from autoresearch import condition_candidate_inputs as candidate
from autoresearch import condition_forward as forward
from autoresearch import condition_forward_contract as contract
from autoresearch import condition_forward_publication as publication
from autoresearch import condition_training as training
from autoresearch import prerace_hash_witness as github
from autoresearch.kra_schedule_snapshot import replay_schedule_snapshot
from autoresearch.local_m0_forward import scheduled_races
from autoresearch.restricted_cohort import encoded, sha256
from autoresearch.tests.test_kra_schedule import SOURCE_URLS, capture, page


def public_payload(raw, number, document, merged):
    commit = "a" * 40
    pull = {
        "number": number,
        "state": "closed",
        "merged": True,
        "merged_at": merged.isoformat(),
        "merge_commit_sha": commit,
        "base": {"ref": "main", "repo": {"full_name": github.REPOSITORY}},
        "html_url": f"https://github.com/{github.REPOSITORY}/pull/{number}",
    }
    content = {
        "type": "file",
        "encoding": "base64",
        "path": document,
        "html_url": f"https://github.com/{github.REPOSITORY}/blob/{commit}/{document}",
        "content": base64.b64encode(raw).decode(),
        "size": len(raw),
        "sha": hashlib.sha1(
            b"blob " + str(len(raw)).encode() + b"\0" + raw
        ).hexdigest(),
    }
    return pull, content


def archive_publication(directory, raw, number, document, merged, retrieved):
    directory.mkdir(parents=True)
    pull, content = public_payload(raw, number, document, merged)
    _, observed = github.validate_publication(
        pull, content, number=number, document=document
    )
    observed.update(
        retrieved_at=retrieved.isoformat(),
        pull_response_sha256=training.save(directory / "pull.json", pull),
        document_response_sha256=training.save(
            directory / "document-response.json", content
        ),
    )
    (directory / "published-document.md").write_bytes(raw)
    training.save(directory / "observed.json", observed)
    return publication.replay(directory, number, document, sha256(raw))


def make_block(tmp_path, monkeypatch):
    real_root = contract.ROOT
    for name in ("receipt.json", "A24-model.json", "B34-model.json"):
        path = tmp_path / contract.MODELS / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((real_root / contract.MODELS / name).read_bytes())
    for name in (
        "condition_training_model.py",
        "condition_training_data.py",
        "condition_candidate_inputs.py",
    ):
        path = tmp_path / "packages/scripts/autoresearch" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(
            (real_root / "packages/scripts/autoresearch" / name).read_bytes()
        )
    monkeypatch.setattr(contract, "ROOT", tmp_path)
    instant = datetime.now(UTC)
    date = (instant + timedelta(days=7)).strftime("%Y%m%d")
    old, protocol_at = instant - timedelta(minutes=3), instant - timedelta(minutes=2)
    date_value = datetime.strptime(date, "%Y%m%d")
    date_text = date_value.strftime("%Y/%m/%d") + f"({WEEKDAYS[date_value.weekday()]})"
    pages = {
        s: page(s, dates=dict.fromkeys(range(1, 5), date_text)) for s in SOURCE_URLS
    }
    captured = capture(tmp_path / "raw", pages=pages, clock=lambda: old)
    scheduled = scheduled_races(replay_schedule_snapshot(captured, race_date=date))

    def pin(path, value=None):
        path = tmp_path / path
        path.parent.mkdir(parents=True, exist_ok=True)
        if value is not None:
            path.write_bytes(encoded(value))
        return {
            "path": str(path.relative_to(tmp_path)),
            "sha256": sha256(path.read_bytes()),
        }

    features = {
        k: False if k.endswith("_missing") or k == candidate.recency.FIELDS[-1] else 0
        for k in candidate.BASE_COLUMNS
    }
    memory_features = {
        **dict.fromkeys(candidate.COUNTS, 0),
        "condition_delta90": "0",
        "fallback90": "no_eligible_prior",
        "older_career_form": None,
    }
    races, packets, memory_rows = [], [], []
    for race in scheduled:
        rid = race["race_id"]
        roster = [{"horse_id": str(100 + n), "chul_no": n} for n in range(1, 11)]
        races.append(
            {
                "race_id": rid,
                "feature_cutoff_at": race["feature_cutoff_at"],
                "roster": roster,
            }
        )
        packets.append(
            pin(
                f"inputs/{rid}.json",
                {
                    "race_id": rid,
                    "feature_cutoff_at": race["feature_cutoff_at"],
                    "target_outcomes_loaded": False,
                    "materialized_at": old.isoformat(),
                    "api_source": {"available_at": old.isoformat()},
                    "history_source": {
                        "available_at": old.isoformat(),
                        "public_existence_bound_at": old.isoformat(),
                    },
                    "feature_rows": [
                        {**r, "features": {**features, "age": n + 2}}
                        for n, r in enumerate(roster)
                    ],
                },
            )
        )
        memory_rows.extend(
            {"race_id": rid, **r, "features": deepcopy(memory_features)} for r in roster
        )
    memory = pin(
        "inputs/memory.json",
        {
            "created_at": old.isoformat(),
            "training_approved": False,
            "target_outcomes_loaded": False,
            "rows": memory_rows,
        },
    )
    code_path = "packages/scripts/mock-reviewed-code.py"
    pin(code_path, {"synthetic": True})
    runtime = {
        "implementation": {code_path: sha256((tmp_path / code_path).read_bytes())},
        "synthetic_environment": "test-only",
    }
    monkeypatch.setattr(contract, "runtime", lambda: deepcopy(runtime))
    protocol = {
        "format_version": "condition-forward-protocol-v1",
        "study_id": "synthetic-only",
        "race_dates": [date],
        "created_at": protocol_at.isoformat(),
        "policies": deepcopy(contract.POLICIES),
        "runtime": deepcopy(runtime),
        "horizon": "one synthetic block",
        "sample_size_rationale": "fixture only",
        "uncertainty": "fixture only",
        "stopping": "fixed block no tuning",
        "prediction_failure_scoring": "retain failures and withhold whole accuracy",
        "prior_block_history_policy": "only reviewed histories available before freeze",
        "races": sorted(races, key=lambda r: r["race_id"]),
        "packets": packets,
        "memory": memory,
        "schedules": [{**pin(captured), "race_date": date}],
        "source_receipts": [
            {
                **pin("inputs/raw-receipt.json", {"synthetic": True}),
                "available_at": old.isoformat(),
            }
        ],
    }
    review = {
        "study_id": protocol["study_id"],
        "race_dates": [date],
        "reviewer": "synthetic fixture",
        "reviewed_at": (protocol_at + timedelta(seconds=10)).isoformat(),
        "protocol_publication_pr": 900,
        "raw_source_closure_reviewed": True,
        "label_free_inputs_reviewed": True,
        "protocol_reviewed": True,
    }
    records, committed, calls = [review], {}, []

    def persist():
        review["protocol"] = pin(
            "docs/research/protocols/synthetic-only.json", protocol
        )
        pin(
            contract.REGISTRY,
            {
                "format_version": "condition-forward-reviews-v1",
                "approved_studies": records,
            },
        )
        for p in (review["protocol"]["path"], contract.REGISTRY, code_path):
            for ref in ("HEAD", "origin/main"):
                committed[f"{ref}:{p}"] = (tmp_path / p).read_bytes()

    def git(*args):
        if args == ("rev-parse", "--git-common-dir"):
            return str(tmp_path / "common-git").encode()
        assert args[0] == "show"
        return committed[args[1]]

    def capture_public(directory, number, document, digest):
        calls.append(number)
        if number == 900:
            raw = encoded(protocol)
            merged, retrieved = (
                protocol_at + timedelta(seconds=20),
                instant - timedelta(seconds=10),
            )
        else:
            raw = (tmp_path / forward.document_path(protocol["study_id"])).read_bytes()
            merged = retrieved = datetime.now(UTC)
        return archive_publication(directory, raw, number, document, merged, retrieved)

    monkeypatch.setattr(contract.training, "git", git)
    monkeypatch.setattr(publication, "capture", capture_public)
    persist()
    return SimpleNamespace(
        root=tmp_path,
        protocol=protocol,
        review=review,
        records=records,
        persist=persist,
        pin=pin,
        committed=committed,
        runtime=runtime,
        calls=calls,
        study=protocol["study_id"],
        captured=captured,
    )
