"""Materialize all pinned diagnostic rosters; never fit or approve a model."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from shared.observed_partial_history import CONTRACT, project_partial_history

from autoresearch.frozen_history_view import replay_frozen
from autoresearch.history_identity_audit import audit_replayed_seed
from autoresearch.kra_race_card_pdf_replay import parse_json
from autoresearch.observed_history_seed import (
    ROOT,
    digest,
    exclusive,
    implementation,
    save,
)


def materialize(
    root: Path,
    seed_path: Path,
    seed_sha256: str,
    corpus_path: Path,
    corpus_sha256: str,
    *,
    cutoff: str | None = None,
) -> dict:
    seed = replay_frozen(root, seed_path, seed_sha256, cutoff=cutoff)
    raw = corpus_path.read_bytes()
    if digest(raw) != corpus_sha256:
        raise ValueError("partial_history_corpus_pin_mismatch")
    corpus = parse_json(raw)
    # Labels, eligibility and training-selection fields are deliberately unused.
    races = [{"race_id": r["race_id"], "roster": r["roster"]} for r in corpus["ledger"]]
    if not races or len({r["race_id"] for r in races}) != len(races):
        raise ValueError("partial_history_invalid_race_membership")
    projections = [project_partial_history(r, seed) for r in races]
    modules = (
        "autoresearch/frozen_history_view.py",
        "autoresearch/observed_partial_projection.py",
        "autoresearch/history_identity_audit.py",
        "autoresearch/prerace_hash_witness.py",
        "shared/observed_partial_history.py",
    )
    current = implementation()
    current["sources"].update(
        {name: digest((ROOT / name).read_bytes()) for name in modules}
    )
    return {
        "format_version": "kra-frozen-partial-history-projection-v1",
        "feature_contract": CONTRACT,
        "seed_sha256": seed_sha256,
        "corpus_sha256": corpus_sha256,
        "plan_sha256": seed["plan_sha256"],
        "implementation": current,
        "original_seed_implementation": seed["implementation"],
        "materialized_at": datetime.now(UTC).isoformat(),
        "history_source_cutoff": cutoff,
        "history_source_cutoff_basis": "local_clocks_only" if cutoff else "not_checked",
        "race_count": len(races),
        "runner_count": sum(len(r["roster"]) for r in races),
        "races": projections,
        "quality_audit": audit_replayed_seed(root, seed, seed_sha256),
        "scope": "all_rosters_in_pinned_diagnostic_corpus_not_future_national_universe",
        "target_card_availability_verified": False,
        "prediction_registration_verified": False,
        "independent_timestamp_verified": False,
        "historical_pre_race_availability_verified": False,
        "training_approved": False,
        "counts_as_70_percent_evidence": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument("--seed-sha256", required=True)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--corpus-sha256", required=True)
    parser.add_argument("--history-source-cutoff")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    with exclusive(args.root):
        report = materialize(
            args.root,
            args.seed,
            args.seed_sha256,
            args.corpus,
            args.corpus_sha256,
            cutoff=args.history_source_cutoff,
        )
        sha = save(args.output, report)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "sha256": sha,
                "race_count": report["race_count"],
                "runner_count": report["runner_count"],
                "training_approved": False,
                "counts_as_70_percent_evidence": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
