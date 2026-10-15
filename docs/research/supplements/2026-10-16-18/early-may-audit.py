"""Offline early-May acquisition audit; no model fitting or target outcomes."""

import argparse
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

from autoresearch import condition_delta_diagnostic as delta
from autoresearch import condition_memory_research as memory
from autoresearch import history_gap_expansion as expansion
from autoresearch import official_history_support as support
from autoresearch import race_conditions
from autoresearch.frozen_history_view import replay_frozen
from autoresearch.observed_history_seed import digest, save
from autoresearch.official_history_catalog import read_pin

ROOT = Path(".cache/autoresearch/observed-history-extension-20260501-14")
SEED_SHA = "561bcfdc6fe2c4733e571b8c77034a2753e88794d5d7d3a6ee5d2ee2f25a5407"
ARCHIVE_SHA = "8ca56ba232156beb824e9baab1f4c8c5b301e8d619f81e17d1213e8f6512e1bd"
MEMORY_PATH = Path(".cache/autoresearch/condition-memory-20261015/run-1/report.json")
MEMORY_SHA = "1d28fe6df8a41bfa15f3342f08dc25fd507ba37461471eb5bbe32f0531daceef"


def run(output):
    started = datetime.now(UTC)
    previous = read_pin(MEMORY_PATH, MEMORY_SHA)
    cutoff = datetime.fromisoformat(previous["first_cutoff"])
    memory.check_time(started, cutoff)
    commitments = {k: read_pin(delta.PUBLIC / k, v) for k, v in delta.PINS.items()}
    seed = replay_frozen(ROOT, ROOT / "seed.json", SEED_SHA, cutoff=cutoff.isoformat())
    evidence = support.replay_archive(
        ROOT / "official", ARCHIVE_SHA, seed, SEED_SHA, cutoff.isoformat()
    )
    added, groups = expansion.supported_extension(seed["records"], evidence)
    contexts = {}
    for identity in sorted({r["race_id"] for r in seed["records"]}):
        assert "20260501" <= identity[:8] <= "20260514"
        item = evidence[identity]
        contexts[identity] = race_conditions.from_capture(
            ROOT / "official", identity, item["capture"],
            {"archive_sha256": ARCHIVE_SHA, "receipt": item["receipt"]},
        )
    old = read_pin(expansion.ROOT / "report-v2.json", memory.EXPANSION_SHA)
    base = read_pin(delta.HISTORY / "history.json", delta.HISTORY_SHA)["records"]
    old_contexts = read_pin(delta.HISTORY / "conditions.json", delta.CONDITIONS_SHA)["records"]
    targets, target_contexts, target_evidence = delta.load_targets(commitments["m0.json"])
    assert len(targets) == 50 and sum(map(len, targets.values())) == 534
    assert not (old_contexts.keys() & old["extension_conditions"].keys())
    historical_contexts = {**old_contexts, **old["extension_conditions"]}
    assert not (historical_contexts.keys() & contexts.keys())
    baseline = base + old["extension_history"]
    all_contexts = {**historical_contexts, **contexts, **target_contexts}
    assert all(
        datetime.fromisoformat(c["captured_at"]) <= started
        for c in all_contexts.values() if "captured_at" in c
    )
    before = memory.project(targets, base, old["extension_history"], all_contexts)
    assert before["rows"] == previous["rows"]
    assert before["recent_ledger"] == previous["recent_ledger"]
    projected = memory.project(targets, baseline, added, all_contexts)
    assert projected["recent_ledger"] == previous["recent_ledger"]
    coverage = expansion.coverage(targets, baseline, added, all_contexts)
    segments = defaultdict(list)
    for row in projected["rows"]:
        segments[row["race_id"].split("_")[1]].append(row)
    for name, sha in delta.PINS.items():
        read_pin(delta.PUBLIC / name, sha)
    report = {
        "format_version": "early-may-history-audit-v1",
        "created_at": started.isoformat(),
        "first_cutoff": cutoff.isoformat(),
        "seed_sha256": SEED_SHA,
        "official_archive_sha256": ARCHIVE_SHA,
        "previous_memory_sha256": MEMORY_SHA,
        "baseline_history_sha256": delta.HISTORY_SHA,
        "previous_extension_sha256": memory.EXPANSION_SHA,
        "public_commitments_unchanged": delta.PINS,
        "script_sha256": digest(Path(__file__).read_bytes()),
        "implementation": {
            p.name: digest(p.read_bytes()) for p in (
                Path(memory.__file__), Path(expansion.__file__),
                Path(support.__file__), Path(race_conditions.__file__),
            )
        },
        "api_requests": seed["request_reservations"],
        "api_units": seed["status_counts"],
        "raw_rows": len(seed["records"]),
        "race_count": len(groups),
        "admitted_rows": len(added),
        "unresolved_rows": len(seed["records"]) - len(added),
        "group_conflicts": sum(g["group_conflict_withheld"] for g in groups),
        "event_support": dict(Counter(g["official_event_support"] for g in groups)),
        "roster_support": dict(Counter(g["roster_support"] for g in groups)),
        "condition_status": dict(Counter(c["status"] for c in contexts.values())),
        "extension_history": added,
        "extension_conditions": contexts,
        "groups": groups,
        "coverage": coverage,
        "summary": memory.summarize(projected["rows"]),
        "by_meet": {k: memory.summarize(v) for k, v in sorted(segments.items())},
        "rows": projected["rows"],
        "recent_ledger": projected["recent_ledger"],
        "input_evidence": target_evidence,
        "fit_count": 0,
        "target_outcomes_loaded": False,
        "training_approved": False,
        "historical_prerace_availability_verified": False,
        "complete_actual_start_history_verified": False,
        "model_promoted": False,
        "accuracy": None,
        "counts_as_70_percent_evidence": False,
    }
    memory.check_time(datetime.now(UTC), cutoff)
    sha = save(output, report)
    print({"report_sha256": sha, **{k: report[k] for k in (
        "race_count", "raw_rows", "admitted_rows", "unresolved_rows",
        "group_conflicts", "event_support", "roster_support", "condition_status",
        "summary", "by_meet",
    )}, "coverage": coverage["strata"]})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args().output)
