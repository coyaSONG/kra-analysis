"""Check the new features with direct day arithmetic, without projection helpers."""
import json
from collections import defaultdict
from datetime import datetime
from fractions import Fraction
from pathlib import Path

from autoresearch import condition_delta_diagnostic as delta
from autoresearch.observed_history_seed import digest, save
from autoresearch.official_history_catalog import read_pin

root = Path(".cache/autoresearch/observed-history-extension-20260501-14")
report_sha = "0ff580a8e1ff3123f2f18ffb226ceb7ebf6c759f071697fbde0e9ad67bbb85e3"
r = read_pin(root / "audit-report.json", report_sha)
old = read_pin(
    Path(".cache/autoresearch/history-gap-expansion-20261014/report-v2.json"),
    r["previous_extension_sha256"],
)
base = read_pin(delta.HISTORY / "history.json", r["baseline_history_sha256"])["records"]
contexts = read_pin(delta.HISTORY / "conditions.json", delta.CONDITIONS_SHA)["records"]
public = {k: read_pin(delta.PUBLIC / k, v) for k, v in delta.PINS.items()}
targets, target_context, _ = delta.load_targets(public["m0.json"])
contexts = {**contexts, **old["extension_conditions"], **r["extension_conditions"], **target_context}
history = base + old["extension_history"] + r["extension_history"]
assert len(history) == len({(x["race_id"], x["horse_id"]) for x in history})
assert not any(x["race_id"] == "20260510_1_9" for x in r["extension_history"])
index = defaultdict(list)
for x in history:
    index[x["horse_id"]].append(x)
expected_keys = {(rid, x["horse_id"], x["chul_no"]) for rid, roster in targets.items() for x in roster}
assert expected_keys == {(x["race_id"], x["horse_id"], x["chul_no"]) for x in r["rows"]}
assert len(expected_keys) == len(r["rows"]) == 534


def mean(rows):
    return (1 + sum(Fraction(x["observed_roster_size"] - x["rank"], x["observed_roster_size"] - 1) for x in rows)) / (2 + len(rows))


def similar(target, prior):
    a, b = contexts.get(target, {}), contexts.get(prior, {})
    return (a.get("status") == b.get("status") == "observed"
            and a["meet"] == b["meet"] and a["class_text"] == b["class_text"]
            and abs(a["distance_m"] - b["distance_m"]) <= 200)


for row in r["rows"]:
    rid = row["race_id"]
    day = datetime.strptime(rid[:8], "%Y%m%d")
    candidates = [(x, (day - datetime.strptime(x["race_id"][:8], "%Y%m%d")).days) for x in index[row["horse_id"]]]
    recent = [x for x, age in candidates if 1 <= age <= 90]
    older = [x for x, age in candidates if 91 <= age <= 180]
    matched = [x for x in recent if similar(rid, x["race_id"])]
    old_matched = [x for x in older if similar(rid, x["race_id"])]
    expected = {
        "condition_delta90": str(mean(matched) - mean(recent)) if matched else "0",
        "prior90_count": len(recent), "similar90_count": len(matched),
        "fallback90": None if matched else "no_eligible_prior",
        "older_count": len(older), "older_career_form": str(mean(older)) if older else None,
        "older_same_venue_similar_count": len(old_matched),
        "older_other_venue_count": sum(x["race_id"].split("_")[1] != rid.split("_")[1] for x in older),
        "older_missing_condition_count": sum(contexts.get(x["race_id"], {}).get("status") != "observed" for x in older),
    }
    assert row["features"] == expected, (rid, row["horse_id"])
    for key, values in (("recent_ids", recent), ("similar90_ids", matched), ("older_ids", older), ("older_similar_ids", old_matched)):
        assert sorted(row["provenance"][key]) == sorted(x["race_id"] for x in values)
evidence = {
    "report_sha256": report_sha, "script_sha256": digest(Path(__file__).read_bytes()),
    "checked_rows": len(r["rows"]), "checked_races": len(targets),
    "history_rows": len(history), "all_features_equal": True,
    "unique_history_keys": True, "quarantined_group_absent": True,
    "public_commitments_unchanged": delta.PINS,
    "fit_count": 0, "accuracy": None, "counts_as_70_percent_evidence": False,
}
print(json.dumps({"sha256": save(root / "independent-check.json", evidence), **evidence}))
