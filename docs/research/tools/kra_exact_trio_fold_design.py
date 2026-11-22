"""Build a review-only complete-field design; never fit or select a trio."""

from collections import Counter
from fractions import Fraction
from itertools import groupby
from math import comb, fsum

import kra_walk_forward_fold as fold
from autoresearch.exact_trio_distribution import (
    partition_trios,
    prepare_exact_trio_distribution,
)
from autoresearch.kra_race_card_pdf_replay import replay_entry_pages
from autoresearch.local_m0_inference import api_features
from autoresearch.restricted_cohort import API_FIELDS, encoded, horse_id, sha256
from kra_trainer_pair_geometry import analyze_trainer_pairs

RECIPE = "api26-field-midranks-and-centered-trainer-v1"
TRAIN = "kra-exact-trio-training-design-v1"
TARGETS = "kra-exact-trio-training-targets-v1"
EVAL = "kra-exact-trio-evaluation-design-v1"
COMMON = (
    *(f"{field}_field_midrank" for field in API_FIELDS),
    *(f"{field}_missing" for field in API_FIELDS),
    "trainer_role_unresolved",
)
ADDITION = "trainer_pair_additive_residual"
RIDGE = 1.0
require = fold.require


def centered_midranks(rows, field):
    rank = dict.fromkeys((row["horse_id"] for row in rows), 0.0)
    observed = sorted(
        (row["features"][field], row["horse_id"])
        for row in rows
        if row["features"][field] is not None
    )
    if len(observed) < 2:
        return rank
    offset = 0
    for _, tied in groupby(observed, key=lambda item: item[0]):
        horses = [horse for _, horse in tied]
        value = float(Fraction(2 * offset + len(horses) - 1, len(observed) - 1) - 1)
        for horse in horses:
            rank[horse] = value
        offset += len(horses)
    return rank


def centered_trainer_counts(counts, roster):
    """Remove the projection onto horse inclusion under uniform trio weights."""
    n = len(roster)
    if n == 3:
        return dict.fromkeys(counts, Fraction(0))
    diagonal = comb(n - 1, 2)
    off_diagonal = n - 2
    row_sum = Counter()
    for trio, value in counts.items():
        for horse in trio:
            row_sum[horse] += value
    sum_node = Fraction(sum(counts.values()), diagonal)
    node = {
        horse: (row_sum[horse] - off_diagonal * sum_node) / (diagonal - off_diagonal)
        for horse in roster
    }
    return {
        trio: (value - sum(node[horse] for horse in trio)) / 3
        for trio, value in counts.items()
    }


def _trainer_rows(root, field, cache):
    day, meet, race_no = field["race_id"].split("_")
    manifest = field["entry_manifest"]
    key = (manifest["path"], manifest["sha256"], day, int(meet))
    if key not in cache:
        rows, _, _ = replay_entry_pages(
            fold.private_path(root, manifest["path"]),
            archive_root=root,
            meet=int(meet),
            race_date=day,
            expected_sha256=manifest["sha256"],
        )
        cache[key] = rows
    selected = [row for row in cache[key] if int(row["rcNo"]) == int(race_no)]
    by_gate = {int(row["chulNo"]): row for row in selected}
    projected = field["feature_rows"]
    require(
        len(by_gate) == len(selected) == len(projected)
        and set(by_gate) == {row["chul_no"] for row in projected},
        "trio_design_trainer_page_roster_conflict",
    )
    result = {}
    for row in projected:
        raw = by_gate[row["chul_no"]]
        horse = row["horse_id"]
        require(
            horse_id(raw["hrNo"]) == horse and api_features(raw) == row["features"],
            "trio_design_not_the_original_entry_row",
        )
        result[horse] = {key: raw.get(key) for key in ("trName", "trNo")}
    return result


def design_field(field, entries):
    rows = field["feature_rows"]
    roster = tuple(row["horse_id"] for row in rows)
    trios, _ = partition_trios(roster, ())
    role = analyze_trainer_pairs(roster, entries)
    ranks = [centered_midranks(rows, key) for key in API_FIELDS]
    additive = {
        r["horse_id"]: (
            *(values[r["horse_id"]] for values in ranks),
            *(int(r["features"][f"{key}_missing"]) for key in API_FIELDS),
            int(role.role_states[r["horse_id"]] != "verified_within_field"),
        )
        for r in rows
    }
    extra = centered_trainer_counts(role.confirmed_pair_counts, roster)
    return {
        "race_id": field["race_id"],
        "entry_manifest": field["entry_manifest"],
        "roster": [[row["chul_no"], row["horse_id"]] for row in rows],
        "trainer_role_states": role.role_states,
        "candidate_horse_ids": [list(trio) for trio in trios],
        "base_logits": [0.0] * len(trios),
        "common_features": [
            [
                fsum(coordinates)
                for coordinates in zip(*(additive[h] for h in trio), strict=True)
            ]
            for trio in trios
        ],
        "extra_feature": [float(extra[trio]) for trio in trios],
    }


def _design_card(root, card, cache):
    fields = [
        design_field(field, _trainer_rows(root, field, cache))
        for field in card["fields"]
    ]
    return {
        "source": card["source"],
        "population_sha256": card["population_sha256"],
        "fields": fields,
    }


def prepare_roles(root, training_rows, evaluation_rows):
    """Make feature bytes without a dependency on labels or their versions."""
    cache = {}
    common = {
        "recipe": RECIPE,
        "common_feature_columns": list(COMMON),
        "added_feature_column": ADDITION,
        "same_positive_ridge_for_both_arms": RIDGE,
        "training_approved": False,
    }
    training = {
        "format": TRAIN,
        **common,
        "cards": [_design_card(root, card, cache) for card in training_rows["cards"]],
    }
    evaluation = {
        "format": EVAL,
        **common,
        "card": _design_card(root, evaluation_rows["card"], cache),
    }
    labels = []
    for card, design in zip(training_rows["cards"], training["cards"], strict=True):
        targets = []
        for target, field in zip(card["targets"], design["fields"], strict=True):
            require(
                target["race_id"] == field["race_id"], "trio_design_wrong_target_role"
            )
            selected = set(target["horse_ids"])
            (index,) = [
                i
                for i, trio in enumerate(field["candidate_horse_ids"])
                if set(trio) == selected
            ]
            targets.append(target | {"candidate_index": index})
        labels.append(
            {
                "candidate": card["candidate"],
                "result_version": card["result_version"],
                "population_sha256": card["population_sha256"],
                "targets": targets,
            }
        )
    return {
        "training": training,
        "labels": {
            "format": TARGETS,
            "recipe": RECIPE,
            "fold_packet_sha256": training_rows["fold_packet_sha256"],
            "training_design_sha256": sha256(encoded(training)),
            "equal_race_weight": [1, sum(len(c["targets"]) for c in labels)],
            "cards": labels,
            "training_approved": False,
        },
        "evaluation": evaluation,
    }


def fit_arguments(training, labels, *, arm):
    """Assemble the existing fitter's arguments without invoking it."""
    require(
        arm in ("A", "B")
        and training.get("format") == TRAIN
        and labels.get("format") == TARGETS
        and training.get("recipe") == labels.get("recipe") == RECIPE
        and training.get("common_feature_columns") == list(COMMON)
        and training.get("added_feature_column") == ADDITION
        and training.get("same_positive_ridge_for_both_arms") == RIDGE
        and training.get("training_approved")
        is labels.get("training_approved")
        is False
        and labels["training_design_sha256"] == sha256(encoded(training)),
        "trio_design_invalid_training_role_or_binding",
    )
    use_pair = arm == "B"
    rosters, distributions, targets = {}, {}, {}
    for card, results in zip(training["cards"], labels["cards"], strict=True):
        require(
            card["population_sha256"] == results["population_sha256"],
            "trio_design_target_population_mismatch",
        )
        for field, target in zip(card["fields"], results["targets"], strict=True):
            rid = field["race_id"]
            roster = tuple(horse for _, horse in field["roster"])
            trios = tuple(tuple(s) for s in field["candidate_horse_ids"])
            expected, _ = partition_trios(roster, ())
            index = target["candidate_index"]
            require(
                rid == target["race_id"]
                and rid not in rosters
                and trios == expected
                and type(index) is int
                and 0 <= index < len(trios)
                and len(target["horse_ids"]) == 3
                and set(trios[index]) == set(target["horse_ids"]),
                "trio_design_fit_population_or_index_mismatch",
            )
            require(
                all(len(row) == len(COMMON) for row in field["common_features"]),
                "trio_design_common_feature_width_mismatch",
            )
            vectors = {
                trio: (*values, extra) if use_pair else tuple(values)
                for trio, values, extra in zip(
                    trios, field["common_features"], field["extra_feature"], strict=True
                )
            }
            rosters[rid] = roster
            distributions[rid] = prepare_exact_trio_distribution(
                roster, dict(zip(trios, field["base_logits"], strict=True)), vectors
            )
            targets[rid] = tuple(target["horse_ids"])
    require(
        rosters and labels["equal_race_weight"] == [1, len(rosters)],
        "trio_design_invalid_equal_race_weight",
    )
    return {
        "expected_rosters": rosters,
        "distributions": distributions,
        "targets": targets,
        "feature_columns": (*COMMON, ADDITION) if use_pair else COMMON,
        "ridge": RIDGE,
    }
