"""Prepare, execute once, and witness the original M0/API27 on a reviewed card."""

import argparse
import sys
from pathlib import Path

import httpx

from autoresearch import condition_forward_publication as publication
from autoresearch import fixed_pair_forward_contract as contract
from autoresearch.condition_training import safe_destination, sync_directory
from autoresearch.condition_training_admission import read
from autoresearch.kra_entry_scope_intake import now
from autoresearch.kra_race_card_pdf_replay import checked_digest
from autoresearch.kra_schedule_snapshot import _write_new
from autoresearch.observed_history_seed import exclusive, save
from autoresearch.prerace_hash_witness import API_ROOT, REPOSITORY, timestamp
from autoresearch.restricted_cohort import encoded, horse_id, parse_json, sha256

PAIR = "kra-fixed-pair-prospective-predictions-v1"
ATTEMPTS = "kra-fixed-pair-forward-attempts-v1"
MAX_OPEN_SLOT_BYTES = 512 * 1024


def deadline(protocol, instant):
    contract.require(
        timestamp(protocol["created_at"])
        <= instant
        < timestamp(protocol["first_block_cutoff"]),
        "fixed_pair_original_deadline",
    )
    return instant


def ledger_for(root, study):
    contract.path_for(study, "protocol")
    common = Path(
        contract.git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
        .decode()
        .strip()
    ).resolve()
    return common / ATTEMPTS / study


def check_attempt_directory(base):
    lock = base / "collector.lock"
    if (
        base.is_symlink()
        or lock.is_symlink()
        or (base.exists() and not base.is_dir())
        or (lock.exists() and not lock.is_file())
    ):
        raise ValueError("fixed_pair_unsafe_attempt_directory")


def unreserved_claim(ledger, race_dates):
    safe_destination(ledger)
    claim = ledger.with_suffix(".reservation.json")
    safe_destination(claim)
    if not ledger.parent.exists():
        return claim
    for previous in ledger.parent.iterdir():
        if not previous.name.endswith(".reservation.json"):
            continue
        if previous.is_symlink():
            raise ValueError("fixed_pair_unsafe_previous_reservation")
        old = contract.canonical(read(previous))
        contract.require(
            not set(old["race_dates"]).intersection(race_dates),
            "fixed_pair_overlapping_consumed_dates",
        )
    return claim


def reserve(ledger, reservation):
    base = ledger.parent
    if not base.exists():
        base.mkdir(exist_ok=True)
        sync_directory(base.parent)
    check_attempt_directory(base)
    with exclusive(base):
        claim = unreserved_claim(ledger, reservation["race_dates"])
        # Publish the complete claim atomically before opening a run directory.
        save(claim, reservation)
        ledger.mkdir(exist_ok=False)
        sync_directory(base)


def inputs_for(root, receipt, protocol):
    details = protocol["source"]
    verified, binding = contract.source(
        root,
        receipt,
        schedule_sha256=details["schedule_sha256"],
        first_cutoff=protocol["first_block_cutoff"],
        packet_sha256=details["input_packet_sha256"],
        input_pr=details["input_publication"]["pull_number"],
    )
    slot = protocol["prediction_slot"]
    expected = contract.protocol_for(
        protocol["study_id"],
        protocol["reviewer"],
        slot["pull_number"],
        protocol["analysis"],
        verified,
        binding,
        timestamp(protocol["created_at"]),
    )
    contract.require(
        encoded(protocol) == encoded(expected), "fixed_pair_protocol_or_runtime_changed"
    )
    return verified


def slot_evidence(ledger, protocol, *, collect):
    number = protocol["prediction_slot"]["pull_number"]
    path = ledger / "prediction-slot-response.json"
    receipt = ledger / "prediction-slot-observation.json"
    if collect:
        url = f"{API_ROOT}/pulls/{number}"
        with (
            httpx.Client(timeout=15, follow_redirects=False, trust_env=False) as client,
            client.stream("GET", url) as response,
        ):
            contract.require(
                str(response.url) == url and response.status_code == 200,
                "fixed_pair_prediction_slot_unavailable",
            )
            raw = bytearray()
            for chunk in response.iter_bytes():
                raw.extend(chunk)
                contract.require(
                    len(raw) <= MAX_OPEN_SLOT_BYTES,
                    "fixed_pair_prediction_slot_too_large",
                )
        _write_new(path, bytes(raw))
        save(
            receipt,
            {
                "raw_sha256": sha256(raw),
                "observed_at": deadline(protocol, now()).isoformat(),
            },
        )
    raw = read(path)
    observed = contract.canonical(read(receipt))
    pull = parse_json(raw)
    base = pull.get("base", {})
    contract.require(
        sha256(raw) == observed["raw_sha256"]
        and pull.get("state") == "open"
        and pull.get("merged") is False
        and type(pull.get("number")) is int
        and pull["number"] == number
        and pull.get("html_url") == f"https://github.com/{REPOSITORY}/pull/{number}"
        and pull.get("user", {}).get("login", "").lower() == contract.OWNER.lower()
        and base.get("ref") == "main"
        and base.get("repo", {}).get("full_name") == REPOSITORY
        and timestamp(pull["created_at"]) <= timestamp(protocol["created_at"])
        and deadline(protocol, timestamp(observed["observed_at"])) <= now(),
        "fixed_pair_prediction_slot_not_open_before_registration",
    )
    return observed


def load_models(directories, started):
    loaded = {}
    for arm, load in (
        ("M0", contract.m0.load_model),
        ("API27", contract.api27.load_model),
    ):
        model, receipt = load(directories[arm])
        contract.require(
            timestamp(receipt["completed_at"]) <= started,
            "fixed_pair_fit_not_before_execution",
        )
        loaded[arm] = model
    return loaded


def score_slot(model, binding):
    projected = binding["shared_input"]
    try:
        scored = contract.m0.score_capture(model, projected)
    except ValueError as exc:
        if str(exc) != "nonfinite_restricted_scores":
            raise
        return {"status": "not_submitted", "reason": str(exc), "horse_ids": None}
    ids = scored["horse_ids"]
    contract.require(
        scored["race_id"] == binding["race"]["race_id"]
        and type(ids) is list
        and len(ids) == 3
        and all(type(h) is str and horse_id(h) == h for h in ids)
        and ids == sorted(set(ids), key=int)
        and set(ids) <= {row["horse_id"] for row in projected["feature_rows"]},
        "fixed_pair_invalid_single_three_selection",
    )
    return {"status": "submitted", "reason": None, "horse_ids": ids}


def pair_rows(protocol, verified, models, check=lambda: None):
    rows = []
    for binding in sorted(verified["bindings"], key=lambda b: b["race"]["race_id"]):
        race = binding["race"]
        arms = {}
        for arm in contract.MODELS:
            check()
            arms[arm] = score_slot(models[arm], binding)
        rows.append(
            {
                "race_id": race["race_id"],
                "race_cutoff": race["feature_cutoff_at"],
                "shared_input_sha256": sha256(encoded(binding)),
                "predictions": arms,
            }
        )
    contract.require(
        [r["race_id"] for r in rows] == protocol["race_ids"],
        "fixed_pair_output_population_changed",
    )
    return rows


def payload(protocol, reservation, rows, started, computed):
    return {
        "format_version": PAIR,
        "study_id": protocol["study_id"],
        "protocol_sha256": reservation["protocol_sha256"],
        "approval_sha256": reservation["approval_sha256"],
        "model_hashes": contract.MODELS,
        "policy": contract.POLICY,
        "input_packet_sha256": protocol["source"]["input_packet_sha256"],
        "first_block_cutoff": protocol["first_block_cutoff"],
        "started_at": started.isoformat(),
        "computed_at": computed.isoformat(),
        "races": rows,
        "actual_fit_count": 0,
    }


def setup_run(root, study, receipt, proof_ids):
    protocol, _, protocol_raw, approval_raw = contract.documents(
        root, study, *proof_ids
    )
    contract.require(
        protocol["study_id"] == study, "fixed_pair_protocol_identity_changed"
    )
    deadline(protocol, now())
    verified = inputs_for(root, receipt, protocol)
    contract.unused_scope(root, protocol)
    contract.git(
        root,
        "--no-optional-locks",
        "diff",
        "--exit-code",
        "refs/remotes/origin/main",
        "--",
        "packages/scripts",
        "pyproject.toml",
        "uv.lock",
    )
    return protocol, protocol_raw, approval_raw, verified


def preflight(root, study, receipt, proof_ids, model_dirs):
    """Verify local prerequisites without obtaining authority or claiming a run."""
    protocol, protocol_raw, approval_raw, _ = setup_run(root, study, receipt, proof_ids)
    _, reviewed_at = contract.local_review(
        study, proof_ids, protocol, protocol_raw, approval_raw
    )
    checked_at = deadline(protocol, now())
    contract.require(
        timestamp(protocol["created_at"]) <= reviewed_at <= checked_at,
        "fixed_pair_local_review_clock_conflict",
    )
    ledger = ledger_for(root, study)
    check_attempt_directory(ledger.parent)
    unreserved_claim(ledger, protocol["race_dates"])
    load_models(model_dirs, checked_at)
    return {
        "status": "local_prerequisites_verified",
        "study_id": study,
        "race_count": len(protocol["race_ids"]),
        "checked_at": deadline(protocol, now()).isoformat(),
        "first_block_cutoff": protocol["first_block_cutoff"],
        "live_authority_verified": False,
        "attempt_reserved": False,
    }


def run(root, study, receipt, proof_ids, model_dirs):
    protocol, protocol_raw, approval_raw, verified = setup_run(
        root, study, receipt, proof_ids
    )
    ledger = ledger_for(root, study)
    reservation = {
        "study_id": study,
        "protocol_sha256": sha256(protocol_raw),
        "approval_sha256": sha256(approval_raw),
        "protocol_and_approval_prs": list(proof_ids),
        "race_dates": protocol["race_dates"],
        "race_ids": protocol["race_ids"],
        "reserved_at": deadline(protocol, now()).isoformat(),
        "retry_allowed": False,
    }
    reserve(ledger, reservation)
    try:
        _write_new(ledger / "protocol.json", protocol_raw)
        _write_new(ledger / "approval.json", approval_raw)
        review = contract.verify_documents(
            ledger, study, proof_ids, protocol_raw, approval_raw, collect=True
        )
        deadline(protocol, now())
        open_slot = slot_evidence(ledger, protocol, collect=True)
        started = deadline(protocol, now())
        contract.require(
            max(timestamp(v["retrieved_at"]) for v in review.values())
            <= timestamp(open_slot["observed_at"])
            <= started,
            "fixed_pair_authority_clock_conflict",
        )
        models = load_models(model_dirs, started)
        rows = pair_rows(protocol, verified, models, lambda: deadline(protocol, now()))
        computed = deadline(protocol, now())
        packet = payload(protocol, reservation, rows, started, computed)
        pair_sha = save(ledger / "paired.json", packet)
        observed = deadline(protocol, now())
        contract.require(
            started <= computed <= observed
            and sha256(read(ledger / "paired.json")) == pair_sha,
            "fixed_pair_persisted_prediction_conflict",
        )
        receipt_info = {
            "status": "locally_complete_not_published",
            "pair_sha256": pair_sha,
            "observed_at": observed.isoformat(),
            "race_count": len(rows),
            "actual_fit_count": 0,
        }
        completion_sha = save(ledger / "receipt.json", receipt_info)
        deadline(protocol, now())
        save(ledger / "complete.json", {"receipt_sha256": completion_sha})
        deadline(protocol, now())
        return receipt_info
    except BaseException as exc:
        save(
            ledger / "failure.json",
            {
                "status": "attempt_consumed_unpublishable",
                "failed_at": now().isoformat(),
                "error_type": type(exc).__name__,
                "race_ids": protocol["race_ids"],
                "retry_allowed": False,
            },
        )
        raise


def verify_local(root, study, receipt, model_dirs):
    ledger = ledger_for(root, study)
    if (ledger / "failure.json").exists():
        raise ValueError("fixed_pair_failed_attempt_is_not_publishable")
    reservation = contract.canonical(read(ledger.with_suffix(".reservation.json")))
    protocol_raw = read(ledger / "protocol.json")
    approval_raw = read(ledger / "approval.json")
    protocol = contract.canonical(protocol_raw)
    contract.require(
        protocol["study_id"] == reservation["study_id"] == study
        and protocol["race_dates"] == reservation["race_dates"]
        and protocol["race_ids"] == reservation["race_ids"]
        and sha256(protocol_raw) == reservation["protocol_sha256"]
        and sha256(approval_raw) == reservation["approval_sha256"]
        and reservation["retry_allowed"] is False,
        "fixed_pair_saved_reservation_conflict",
    )
    completion = contract.canonical(read(ledger / "complete.json"))
    completion_raw = read(ledger / "receipt.json")
    info = contract.canonical(completion_raw)
    packet_raw = read(ledger / "paired.json")
    packet = contract.canonical(packet_raw)
    reserved, started, computed, observed = (
        deadline(protocol, timestamp(value))
        for value in (
            reservation["reserved_at"],
            packet["started_at"],
            packet["computed_at"],
            info["observed_at"],
        )
    )
    contract.require(
        reserved <= started <= computed <= observed <= now()
        and completion == {"receipt_sha256": sha256(completion_raw)}
        and info["status"] == "locally_complete_not_published"
        and info["pair_sha256"] == sha256(packet_raw)
        and info["race_count"] == len(protocol["race_ids"])
        and info["actual_fit_count"] == 0,
        "fixed_pair_saved_completion_conflict",
    )
    review = contract.verify_documents(
        ledger,
        study,
        reservation["protocol_and_approval_prs"],
        protocol_raw,
        approval_raw,
        collect=False,
    )
    slot = slot_evidence(ledger, protocol, collect=False)
    contract.require(
        reserved
        <= min(timestamp(v["retrieved_at"]) for v in review.values())
        <= max(timestamp(v["retrieved_at"]) for v in review.values())
        <= timestamp(slot["observed_at"])
        <= started,
        "fixed_pair_saved_authority_clock_conflict",
    )
    verified = inputs_for(root, receipt, protocol)
    rows = pair_rows(protocol, verified, load_models(model_dirs, started))
    contract.require(
        packet_raw == encoded(payload(protocol, reservation, rows, started, computed)),
        "fixed_pair_numerical_replay_conflict",
    )
    return ledger, protocol, packet_raw, info


def stage(root, study, receipt, model_dirs):
    ledger = ledger_for(root, study)
    saved = contract.canonical(read(ledger / "protocol.json"))
    deadline(saved, now())
    _, protocol, raw, _ = verify_local(root, study, receipt, model_dirs)
    deadline(protocol, now())
    return raw


def witness(root, study, receipt, model_dirs, *, collect):
    ledger, protocol, raw, info = verify_local(root, study, receipt, model_dirs)
    slot = protocol["prediction_slot"]
    operation = publication.capture if collect else publication.replay
    visible, external = operation(
        ledger / "prediction-publication",
        slot["pull_number"],
        slot["document"],
        info["pair_sha256"],
    )
    merged = timestamp(external["merged_at"])
    contract.require(
        visible == raw and merged >= timestamp(info["observed_at"]),
        "fixed_pair_public_prediction_bytes_or_clock_conflict",
    )
    timely = merged < timestamp(protocol["first_block_cutoff"])
    return {
        "status": "published_before_cutoff"
        if timely
        else "published_at_or_after_cutoff",
        "before_cutoff": timely,
        "race_count": info["race_count"],
        "pair_sha256": info["pair_sha256"],
        "prediction_slot": slot,
        "external": external,
        "outcomes_verified": False,
        "model_promoted": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    for name in (
        "prepare",
        "preflight",
        "run",
        "verify",
        "stage",
        "witness",
        "replay-witness",
    ):
        mode = modes.add_parser(name)
        mode.add_argument("--study", required=True)
        mode.add_argument("--receipt", required=True)
        mode.add_argument("--receipt-sha256", required=True)
        if name == "prepare":
            mode.add_argument("--schedule-sha256", required=True)
            mode.add_argument("--packet-sha256", required=True)
            mode.add_argument("--first-cutoff", required=True)
            mode.add_argument("--input-pull", type=int, required=True)
            mode.add_argument("--prediction-pull", type=int, required=True)
            mode.add_argument("--reviewer", required=True)
            mode.add_argument("--analysis", type=Path, required=True)
        else:
            mode.add_argument("--m0-model-dir", type=Path, required=True)
            mode.add_argument("--api27-model-dir", type=Path, required=True)
        if name in ("preflight", "run"):
            mode.add_argument("--protocol-pull", type=int, required=True)
            mode.add_argument("--approval-pull", type=int, required=True)
    args = parser.parse_args(argv)
    root = Path.cwd()
    receipt = {"path": args.receipt, "sha256": checked_digest(args.receipt_sha256)}
    if args.mode == "prepare":
        verified, binding = contract.source(
            root,
            receipt,
            schedule_sha256=args.schedule_sha256,
            first_cutoff=args.first_cutoff,
            packet_sha256=args.packet_sha256,
            input_pr=args.input_pull,
        )
        result = contract.protocol_for(
            args.study,
            args.reviewer,
            args.prediction_pull,
            parse_json(read(args.analysis)),
            verified,
            binding,
            now(),
        )
    else:
        models = {"M0": args.m0_model_dir, "API27": args.api27_model_dir}
        if args.mode in ("preflight", "run"):
            operation = preflight if args.mode == "preflight" else run
            result = operation(
                root,
                args.study,
                receipt,
                (args.protocol_pull, args.approval_pull),
                models,
            )
        elif args.mode == "stage":
            sys.stdout.buffer.write(stage(root, args.study, receipt, models))
            return 0
        elif args.mode == "verify":
            _, _, _, result = verify_local(root, args.study, receipt, models)
        else:
            result = witness(
                root, args.study, receipt, models, collect=args.mode == "witness"
            )
    sys.stdout.buffer.write(encoded(result))
    return 0 if result.get("before_cutoff", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
