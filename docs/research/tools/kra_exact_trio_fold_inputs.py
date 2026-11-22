"""Project verified complete-card evidence into explicit, separate data roles."""

import argparse
from dataclasses import dataclass
from pathlib import Path

import kra_exact_trio_fold_design as design
import kra_walk_forward_fold as fold
from autoresearch import fixed_pair_forward_contract as original_inputs
from autoresearch.kra_entry_scope_intake import now
from autoresearch.kra_race_card_pdf_replay import read_bytes
from autoresearch.observed_history_seed import save
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import (
    API_COLUMNS,
    API_FIELDS,
    encoded,
    horse_id,
    numeric,
    parse_json,
    sha256,
)

TRAINING = "kra-exact-trio-verified-training-rows-v1"
EVALUATION = "kra-exact-trio-verified-evaluation-inputs-v1"
RECEIPT = "kra-exact-trio-fold-input-views-v1"
DIRECTORY = "exact-trio-input-views"
FILES = {
    "training": "training.json",
    "labels": "training-targets.json",
    "evaluation": "evaluation-inputs.json",
}
RECEIPT_NAME = "readback.json"
require = fold.require


@dataclass(frozen=True, slots=True)
class FoldInputs:
    training: dict
    evaluation: dict
    chronology: dict


def _values(row):
    require(
        type(row) is dict and row.keys() == set(API_COLUMNS),
        "trio_fold_unexpected_entry_features",
    )
    for name in API_FIELDS:
        value = row[name]
        missing = row[f"{name}_missing"]
        require(
            type(missing) is bool
            and missing == (value is None)
            and (value is None or type(value) in (int, float)),
            "trio_fold_entry_missingness_or_type_conflict",
        )
        require(numeric(value, name) == value, "trio_fold_invalid_entry_value")
    return {column: row[column] for column in API_COLUMNS}


def _project_field(binding):
    race = binding["race"]
    key = race["race_id"]
    shared = binding["shared_input"]
    require(
        key
        == shared["race_id"]
        == f"{race['race_date']}_{race['meet']}_{race['race_no']}",
        "trio_fold_mismatched_entry_race",
    )
    rows, gates, identities = [], set(), set()
    for item in shared["feature_rows"]:
        require(
            type(item) is dict and set(item) == {"chul_no", "horse_id", "features"},
            "trio_fold_unexpected_declared_row_fields",
        )
        gate, horse = item["chul_no"], item["horse_id"]
        require(
            type(gate) is int
            and gate > 0
            and gate not in gates
            and horse == horse_id(horse)
            and horse not in identities,
            "trio_fold_ambiguous_declared_identity",
        )
        gates.add(gate)
        identities.add(horse)
        rows.append(
            {"chul_no": gate, "horse_id": horse, "features": _values(item["features"])}
        )
    require(len(rows) == race["runners"] >= 3, "trio_fold_incomplete_declared_field")
    return {
        "race_id": key,
        "entry_manifest": binding["entry_manifest"],
        "feature_rows": sorted(rows, key=lambda r: r["chul_no"]),
    }


def _fields(bindings, scope):
    projected = sorted(
        (_project_field(binding) for binding in bindings), key=lambda b: b["race_id"]
    )
    ids = [field["race_id"] for field in projected]
    require(
        len(ids) == len(set(ids)) == scope["race_count"]
        and ids == scope["race_ids"]
        and sha256(encoded(ids)) == scope["population_sha256"],
        "trio_fold_scope_population_conflict",
    )
    rows = [row for field in projected for row in field["feature_rows"]]
    missing = dict.fromkeys(API_FIELDS, 0)
    for row in rows:
        for name in missing:
            missing[name] += row["features"][f"{name}_missing"]
    require(
        len(rows) == scope["declaration_count"]
        and missing == scope["feature_missing_counts"],
        "trio_fold_source_coverage_conflict",
    )
    return projected


def _targets(rows, fields):
    by_race = {r["race_id"]: r for r in rows}
    require(
        len(by_race) == len(rows) == len(fields)
        and by_race.keys() == {field["race_id"] for field in fields},
        "trio_fold_requires_one_target_per_training_race",
    )
    result = []
    for field in fields:
        row = by_race[field["race_id"]]
        target = row["horse_ids"]
        require(
            type(target) is list
            and len(target) == 3
            and target == sorted(set(target), key=int)
            and set(target) <= {r["horse_id"] for r in field["feature_rows"]},
            "trio_fold_target_outside_frozen_roster",
        )
        result.append(
            {
                "race_id": field["race_id"],
                "horse_ids": target,
                "result_observation_id": row["result_observation_id"],
            }
        )
    return result


def _earlier_card(root, scope):
    _, raw = fold._pinned(root, scope["candidate"])
    data = parse_json(raw)
    report = data["report"]
    require(
        report["candidate_ready_for_review"] is True
        and report["source"] == scope["input"]
        and report["result_version"] == scope["result_version"]
        and data["feature_columns"] == list(API_COLUMNS),
        "trio_fold_development_candidate_binding_changed",
    )
    fields = _fields(data["input_races"], scope)
    return {
        "source": scope["input"],
        "result_version": scope["result_version"],
        "candidate": scope["candidate"],
        "population_sha256": scope["population_sha256"],
        "fields": fields,
        "targets": _targets(data["target_races"], fields),
    }


def _future_card(root, spec, scope):
    # This path can only replay original entry data; it has no result inputs.
    verified, bound = original_inputs.source(root, **spec)
    require(
        bound | {"intake_receipt": verified["intake_receipt"]} == scope["input"],
        "trio_fold_evaluation_source_binding_changed",
    )
    return {
        "source": scope["input"],
        "population_sha256": scope["population_sha256"],
        "fields": _fields(verified["bindings"], scope),
    }


def _compile(root, plan_ref, packet_sha256, pull, checked_at):
    root = root.resolve()
    plan, parent = fold._load_plan(root, plan_ref)
    cutoff = timestamp(plan["evaluation"]["first_cutoff"])
    require(checked_at < cutoff, "trio_fold_evidence_not_ready_before_original_cutoff")
    proof = fold.verify(root, plan_ref, packet_sha256=packet_sha256, pull=pull)
    retrieved = timestamp(proof["publication"]["retrieved_at"])
    require(
        proof["before_cutoff"]
        and timestamp(proof["first_block_cutoff"]) == cutoff
        and retrieved <= checked_at,
        "trio_fold_evidence_not_ready_before_original_cutoff",
    )
    packet_path = fold.private_path(
        root, str((parent / fold.PACKET_NAME).relative_to(root))
    )
    packet = parse_json(fold._read_pin(packet_path, packet_sha256))
    common = {
        "fold_packet_sha256": packet_sha256,
        "feature_columns": list(API_COLUMNS),
        "training_approved": False,
    }
    training = {
        "format": TRAINING,
        **common,
        "cards": [_earlier_card(root, c) for c in packet["training"]],
    }
    evaluation = {
        "format": EVALUATION,
        **common,
        "card": _future_card(root, plan["evaluation"], packet["evaluation"]),
    }
    require(
        not {r["race_id"] for c in training["cards"] for r in c["fields"]}
        & {r["race_id"] for r in evaluation["card"]["fields"]},
        "trio_fold_data_role_overlap",
    )
    return FoldInputs(
        training,
        evaluation,
        {
            "fold_publication": proof["publication"],
            "fold_plan": plan_ref,
            "fold_packet_sha256": packet_sha256,
            "first_block_cutoff": proof["first_block_cutoff"],
            "training_races": proof["training_race_count"],
            "evaluation_races": proof["evaluation_race_count"],
            "training_approved": False,
            "model_fit_performed": False,
            "predictions_generated": False,
        },
    )


def read_verified(root: Path, plan_ref: dict, *, packet_sha256: str, pull: int):
    """Prepare complete in-memory operands while the original cutoff is open."""
    checked_at = now()
    result = _compile(root, plan_ref, packet_sha256, pull, checked_at)
    require(
        checked_at <= now() < timestamp(result.chronology["first_block_cutoff"]),
        "trio_fold_readback_finished_after_cutoff",
    )
    return result


def _destination(root, parent, filename=""):
    return fold.private_path(
        root, str((parent / DIRECTORY / filename).relative_to(root))
    )


def _file_refs(root, parent, roles):
    return {
        role: {
            "path": str(_destination(root, parent, name).relative_to(root)),
            "sha256": sha256(encoded(roles[role])),
        }
        for role, name in FILES.items()
    }


def _receipt(views, refs, started, written):
    require(started <= written, "trio_fold_materialization_clock_reversed")
    cutoff = timestamp(views.chronology["first_block_cutoff"])
    return {
        "format": RECEIPT,
        "state": "local_views_prepared" if written < cutoff else "local_views_late",
        "source_roles": refs,
        "local_started_at": started.isoformat(),
        "local_role_files_written_at": written.isoformat(),
        "projection_sha256": sha256(Path(__file__).read_bytes()),
        "design_implementation_sha256": sha256(Path(design.__file__).read_bytes()),
        "recipe": design.RECIPE,
        "materialization_independent_clock_verified": False,
        "counts_as_70_percent_evidence": False,
        **views.chronology,
    }


def _verify_role_file(root, ref, value):
    expected = encoded(value)
    path = fold.private_path(root, ref["path"])
    # Derived whole-season views can be larger than one original manifest.
    require(
        read_bytes(path, limit=len(expected)) == expected
        and sha256(expected) == ref["sha256"],
        "trio_fold_role_does_not_replay",
    )


def stage(root: Path, plan_ref: dict, *, packet_sha256: str, pull: int):
    """Save separate local role views without replacing a prior assembly."""
    root = root.resolve()
    _, parent = fold._load_plan(root, plan_ref)
    directory = _destination(root, parent)
    if directory.exists():
        raise FileExistsError("trio_fold_role_views_already_reserved")
    started = now()
    views = _compile(root, plan_ref, packet_sha256, pull, started)
    roles = design.prepare_roles(root, views.training, views.evaluation)
    require(
        started <= now() < timestamp(views.chronology["first_block_cutoff"]),
        "trio_fold_readback_finished_after_cutoff",
    )
    refs = _file_refs(root, parent, roles)
    directory.mkdir(mode=0o700, exist_ok=False)
    for role, ref in refs.items():
        digest = save(root / ref["path"], roles[role])
        require(digest == ref["sha256"], "trio_fold_role_write_mismatch")
    receipt = _receipt(views, refs, started, now())
    path = _destination(root, parent, RECEIPT_NAME)
    return receipt | {
        "receipt": {"path": str(path.relative_to(root)), "sha256": save(path, receipt)}
    }


def replay(
    root: Path, plan_ref: dict, *, packet_sha256: str, pull: int, receipt_sha256: str
):
    """Check the originally saved role bytes; never make them timely or approved."""
    root = root.resolve()
    _, parent = fold._load_plan(root, plan_ref)
    path = _destination(root, parent, RECEIPT_NAME)
    raw = fold._read_pin(path, receipt_sha256)
    old = parse_json(raw)
    started = timestamp(old["local_started_at"])
    written = timestamp(old["local_role_files_written_at"])
    require(
        started <= written <= now(),
        "trio_fold_invalid_local_materialization_clock",
    )
    views = _compile(root, plan_ref, packet_sha256, pull, started)
    roles = design.prepare_roles(root, views.training, views.evaluation)
    refs = _file_refs(root, parent, roles)
    receipt = _receipt(views, refs, started, written)
    require(encoded(receipt) == raw, "trio_fold_role_receipt_does_not_replay")
    for role, ref in refs.items():
        _verify_role_file(root, ref, roles[role])
    return receipt | {
        "receipt": {"path": str(path.relative_to(root)), "sha256": receipt_sha256}
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="mode", required=True)
    for mode in ("stage", "replay"):
        sub = commands.add_parser(mode)
        sub.add_argument("--plan", required=True)
        sub.add_argument("--plan-sha256", required=True)
        sub.add_argument("--packet-sha256", required=True)
        sub.add_argument("--pull", type=int, required=True)
        if mode == "replay":
            sub.add_argument("--receipt-sha256", required=True)
    args = parser.parse_args(argv)
    plan = {"path": args.plan, "sha256": args.plan_sha256}
    options = {"packet_sha256": args.packet_sha256, "pull": args.pull}
    if args.mode == "stage":
        report = stage(Path.cwd(), plan, **options)
    else:
        report = replay(Path.cwd(), plan, **options, receipt_sha256=args.receipt_sha256)
    print(encoded(report).decode(), end="")
    return 0 if report["state"] == "local_views_prepared" else 2


if __name__ == "__main__":
    raise SystemExit(main())
