"""Validate the complete frozen candidate population without fitting anything."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from fractions import Fraction

import numpy as np

from autoresearch.condition_candidate_inputs import (
    BASE_COLUMNS,
    COLUMNS,
    COUNTS,
    base_features,
    key,
)
from autoresearch.restricted_cohort import encoded, sha256

LABEL_POLICY = "frozen_roster_observed_unique_top3_membership_v1"


def index(rows):
    result = {}
    for row in rows:
        rid = row["race_id"]
        if rid in result:
            raise ValueError("duplicate_race")
        result[rid] = row
    return result


def canonical(ids):
    if not isinstance(ids, list) or len(ids) != 3 or len(set(ids)) != 3:
        raise ValueError("target_requires_three_distinct_ids")
    for horse in ids:
        key("identity", {"chul_no": 1, "horse_id": horse})
    return sorted(ids, key=int)


def feature_values(features):
    if set(features) != set(COLUMNS):
        raise ValueError("feature_columns_mismatch")
    base_features({k: features[k] for k in BASE_COLUMNS})
    counts = {c: features[f"memory_{c}"] for c in COUNTS}
    if any(type(v) is not int or v < 0 for v in counts.values()):
        raise ValueError("invalid_memory_count")
    if counts["similar90_count"] > counts["prior90_count"] or any(
        counts[c] > counts["older_count"] for c in COUNTS[3:]
    ):
        raise ValueError("inconsistent_memory_count")
    delta = features["memory_condition_delta90"]
    form = features["memory_older_career_form"]
    if (
        type(delta) not in (int, float)
        or not -1 <= delta <= 1
        or features["memory_fallback90"] != (counts["similar90_count"] == 0)
        or (features["memory_fallback90"] and delta != 0)
        or (form is None) != (counts["older_count"] == 0)
        or (form is not None and (type(form) not in (int, float) or not 0 <= form <= 1))
    ):
        raise ValueError("invalid_memory_values")
    for name, value in features.items():
        boolean = name.endswith("_missing") or name in (
            "memory_fallback90",
            "has_linked_api_unresolved_after_last_supported_ranked_date",
        )
        if boolean:
            if type(value) is not bool and not (
                name == "has_linked_api_unresolved_after_last_supported_ranked_date"
                and value is None
            ):
                raise ValueError("invalid_feature_boolean")
        elif value is not None and (
            type(value) not in (int, float) or not np.isfinite(value)
        ):
            raise ValueError("invalid_feature_number")
        if name.endswith("_missing") and value != (features[name[:-8]] is None):
            raise ValueError("invalid_missing_flag")
    return [np.nan if features[c] is None else float(features[c]) for c in COLUMNS]


def prepare(cohort, matrix, outcomes, packets, public_ids):
    """Return arrays only after all joins and rowwise label evidence agree."""
    if (
        cohort["format_version"] != "development-cohort-link-v1"
        or matrix["format_version"] != "condition-candidate-inputs-v1"
        or cohort["columns"] != list(COLUMNS)
        or matrix["columns"] != list(COLUMNS)
        or cohort["training_approved"] is not False
        or cohort["training_label_policy_approved"] is not False
        or cohort["fit_count"] != 0
        or matrix["training_approved"] is not False
        or matrix["target_outcomes_loaded"] is not False
    ):
        raise ValueError("invalid_original_contract")
    if encoded(cohort["feature_rows"]) != encoded(matrix["rows"]):
        raise ValueError("original_feature_matrix_changed")
    targets = index(cohort["race_targets"])
    results = index(outcomes["ledger"])
    cutoffs = index(cohort["race_cutoffs"])
    packet_map = index(packets)
    ids = set(public_ids)
    if len(ids) != len(public_ids) or not all(
        set(x) == ids for x in (targets, results, cutoffs, packet_map)
    ):
        raise ValueError("whole_population_mismatch")
    if encoded(cohort["race_cutoffs"]) != encoded(matrix["races"]):
        raise ValueError("original_cutoffs_changed")
    observations = [r for rid in sorted(ids) for r in results[rid]["api_records"]]

    def sort_key(r):
        return key(r["race_id"], r)

    if encoded(sorted(observations, key=sort_key)) != encoded(
        sorted(cohort["result_observations_not_features"], key=sort_key)
    ):
        raise ValueError("original_observations_changed")
    rows = sorted(cohort["feature_rows"], key=sort_key)
    if len({sort_key(r) for r in rows}) != len(rows):
        raise ValueError("duplicate_identity")
    if {r["race_id"] for r in rows} != ids or len(rows) != matrix["runner_count"]:
        raise ValueError("feature_population_mismatch")
    if matrix["race_count"] != len(ids):
        raise ValueError("race_count_mismatch")
    identities, values, labels, weights, exceptions = [], [], [], [], []
    for rid in sorted(ids):
        roster = [r for r in rows if r["race_id"] == rid]
        if not 3 <= len(roster) <= 20 or any(
            len({r[k] for r in roster}) != len(roster) for k in ("horse_id", "chul_no")
        ):
            raise ValueError("invalid_frozen_roster")
        result, target, packet = results[rid], targets[rid], packet_map[rid]
        top3 = canonical(result["observed_top3_horse_ids"])
        if (
            result["status"] != "unique_top3_observed"
            or top3 != canonical(target["unordered_top3_horse_ids"])
            or not set(top3) <= {r["horse_id"] for r in roster}
            or result["exception_notes"] != target["exception_notes"]
            or result["observed_runner_count"] != len(roster)
        ):
            raise ValueError("unresolved_or_mismatched_target")
        observed_keys = [sort_key(r) for r in result["api_records"]]
        if Counter(observed_keys) != Counter(sort_key(r) for r in roster):
            raise ValueError("result_roster_mismatch")
        old = sorted(packet["feature_rows"], key=lambda r: r["chul_no"])
        if len(old) != len(roster):
            raise ValueError("packet_roster_mismatch")
        cutoff = datetime.fromisoformat(cutoffs[rid]["feature_cutoff_at"])
        created = datetime.fromisoformat(matrix["created_at"])
        if (
            cutoff.utcoffset() is None
            or created.utcoffset() is None
            or not created < cutoff
            or packet["feature_cutoff_at"] != cutoffs[rid]["feature_cutoff_at"]
        ):
            raise ValueError("invalid_prerace_clock")
        if sum((Fraction(1, len(roster)) for _ in roster), Fraction()) != 1:
            raise ValueError("invalid_rational_weights")
        for row, original in zip(roster, old, strict=True):
            if key(rid, row) != key(rid, original) or encoded(
                {k: row["features"][k] for k in BASE_COLUMNS}
            ) != encoded(original["features"]):
                raise ValueError("original_base24_changed")
            identities.append({k: row[k] for k in ("race_id", "chul_no", "horse_id")})
            values.append(feature_values(row["features"]))
            labels.append(int(row["horse_id"] in top3))
            weights.append(1.0 / len(roster))
        exceptions.extend(
            r
            for r in result["api_records"]
            if r["evidence"] != "ranked_finish_observed"
        )
    x = np.asarray(values, dtype=np.float64)
    y = np.asarray(labels, dtype=np.int64)
    w = np.asarray(weights, dtype=np.float64)
    if int(y.sum()) != 3 * len(ids) or not np.isclose(w.sum(), len(ids)):
        raise ValueError("invalid_labels_or_weights")
    return (
        x,
        y,
        w,
        identities,
        {
            "race_count": len(ids),
            "row_count": len(rows),
            "positive": int(y.sum()),
            "negative": int((y == 0).sum()),
            "weight_sum": float(w.sum()),
            "exceptions": exceptions,
            "null_counts": {
                c: int(np.isnan(x[:, n]).sum()) for n, c in enumerate(COLUMNS)
            },
            "identities_sha256": sha256(encoded(identities)),
            "labels_sha256": sha256(encoded(labels)),
            "weights_sha256": sha256(encoded(weights)),
            "raw_features_sha256": sha256(encoded(cohort["feature_rows"])),
        },
    )
