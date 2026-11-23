"""Operate one approved whole-card result slot without retry or fitting."""

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx
import kra_result_slot_witness as witness
from autoresearch import condition_forward_publication as publication
from autoresearch import frozen_history_view
from autoresearch import observed_history_seed as history
from autoresearch import official_history_support as official
from autoresearch.fixed_pair_forward import check_attempt_directory
from autoresearch.fixed_pair_forward_contract import git
from autoresearch.kra_entry_scope_intake import KST
from autoresearch.kra_result_snapshot import PAGE_SIZE
from autoresearch.versioned_result_observations import FORMAT as OUTCOME_FORMAT
from kra_result_slot_collectors import Stop, capture_api, capture_official

fold, enrollment, custody = witness.fold, witness.enrollment, witness.custody
encoded, parse, require = fold.encoded, fold.parse_json, fold.require
sha256, timestamp = fold.sha256, witness.timestamp
INPUTS = "kra-result-slot-input-prefix-v1"
CLAIMS = "kra-result-slot-claims-v1"
FINISH = "kra-result-slot-capture-finish-v1"


def rule_publication(root, rules_ref, pull):
    path, _ = fold._pinned(root.resolve(), rules_ref)
    require(type(pull) is int and pull > 0, "result_slot_invalid_rules_pull")
    digest = rules_ref["sha256"]
    folder = path.with_name(f"result-slot-rules-publication-{digest}")
    raw = witness.rule_marker(digest)
    _, proof = publication.capture(
        folder, pull, witness.rule_document(digest), sha256(raw)
    )
    return proof


@dataclass(frozen=True)
class Appointment:
    root: Path
    folder: Path
    claims: Path
    rule_sha: str
    prefix_sha: str
    slot: dict
    scope: dict
    schedule: Path
    expected: dict

    @property
    def claim(self):
        return self.claims / f"{self.slot['week']}.json"

    @property
    def binding(self):
        return {
            "week": self.slot["week"],
            "policy_sha256": self.rule_sha,
            "schedule_sha256": self.scope["input"]["schedule_sha256"],
            "population_sha256": self.scope["population_sha256"],
        }

    def clock(self):
        instant = fold.now()
        if (
            not timestamp(self.slot["opens_at"])
            <= instant
            < timestamp(self.slot["closes_at"])
        ):
            raise Stop("outside_designated_observation_window")
        return instant


def appointment(
    root, rules_ref, enrollment_ref, inputs_ref, *, week, rules_pull, enrollment_pull
):
    root = root.resolve()
    checked = fold.now()
    policy_path, policy = enrollment._load_policy(root, enrollment_ref)
    weeks = policy["training_weeks"]
    require(week in weeks, "result_slot_not_enrolled_training_week")
    n = weeks.index(week) + 1
    _, raw = fold._pinned(root, inputs_ref)
    inputs = parse(raw)
    require(
        set(inputs) == {"format", "training"}
        and inputs["format"] == INPUTS
        and type(inputs["training"]) is list
        and len(inputs["training"]) == n
        and all(
            type(row) is dict and set(row) == fold.INPUT_KEYS
            for row in inputs["training"]
        ),
        "result_slot_invalid_training_prefix",
    )
    cutoffs = []
    for spec, planned_week in zip(inputs["training"], weeks[:n], strict=True):
        scope = fold._scope(root, spec, checked)
        require(
            enrollment._week_for(scope["race_dates"]) == planned_week,
            "result_slot_prefix_week_conflict",
        )
        cutoffs.append(timestamp(scope["first_block_cutoff"]))
    proof = enrollment._witness(
        root, policy_path, enrollment_ref["sha256"], enrollment_pull
    )
    require(
        timestamp(proof["merged_at"]) < min(cutoffs)
        and timestamp(proof["retrieved_at"]) <= checked,
        "result_slot_enrollment_not_timely",
    )
    path, raw = fold._pinned(root, rules_ref)
    require(
        path.is_relative_to(root / ".cache/autoresearch"),
        "result_slot_private_archive_required",
    )
    rule_sha = rules_ref["sha256"]
    rules = parse(raw)
    witness._rules(
        root,
        path,
        rule_sha,
        rules,
        enrollment_ref["sha256"],
        {"training_weeks": weeks, "first_enrolled_cutoff": min(cutoffs).isoformat()},
        rules_pull,
        checked,
    )
    pulls = [
        rules_pull,
        enrollment_pull,
        *(s["receipt_pull"] for s in rules["slots"]),
        *(s["input_pr"] for s in inputs["training"]),
    ]
    require(len(set(pulls)) == len(pulls), "result_slot_publication_roles_overlap")
    slot = rules["slots"][n - 1]
    opens = timestamp(slot["opens_at"])
    last = timestamp(scope["last_scheduled_start_at"])
    require(
        last.astimezone(KST).date() < opens.astimezone(KST).date()
        and opens < timestamp(slot["closes_at"]),
        "result_slot_window_not_after_original_race_dates",
    )

    _, raw = fold._pinned(root, scope["input"]["intake_receipt"])
    _, raw = fold._pinned(root, parse(raw)["reservation"])
    reserved = parse(raw)
    schedule, _ = fold._pinned(root, reserved["schedule"])
    expected = {
        (s["race_date"], s["meet"]): {
            "ids": sorted(r["race_id"] for r in s["races"]),
            "pages": (s["runner_count"] + PAGE_SIZE - 1) // PAGE_SIZE,
            "anchor": s["anchor_race_no"],
            "runners": s["runner_count"],
        }
        for s in reserved["scopes"]
    }
    require(
        reserved["schedule"]["sha256"] == scope["input"]["schedule_sha256"]
        and sorted(r for s in expected.values() for r in s["ids"]) == scope["race_ids"],
        "result_slot_original_scope_changed",
    )
    parent = path.with_name(f"result-observation-slots-{rule_sha}")
    folder = custody._path(root, week, parent=parent)
    common = Path(
        git(root, "rev-parse", "--path-format=absolute", "--git-common-dir")
        .decode()
        .strip()
    ).resolve()
    return Appointment(
        root,
        folder,
        common / CLAIMS,
        rule_sha,
        inputs_ref["sha256"],
        slot,
        scope,
        schedule,
        expected,
    )


def _inventory(card, ref):
    report = custody.inventory(
        card.root,
        ref,
        race_dates=card.scope["race_dates"],
        race_ids=card.scope["race_ids"],
        schedule_sha256=card.binding["schedule_sha256"],
    )
    holds = [
        *custody.window_holds(
            report, opens_at=card.slot["opens_at"], closes_at=card.slot["closes_at"]
        ),
        *witness._required_source_holds(report, card.scope["race_ids"]),
        *witness._run_holds(
            card.root, card.folder / "history", report, card.slot["api_request_budget"]
        ),
    ]
    if not holds:
        # Replay the raw source hashes, not just the observation clocks.
        _, raw = fold._pinned(card.root, ref)
        plan = parse(raw)
        directory = custody._path(card.root, plan["seed_root"])
        seed_path = custody._path(card.root, plan["seed_path"])
        seed = frozen_history_view.replay_frozen(
            directory, seed_path, plan["seed_sha256"]
        )
        official.replay_archive(
            custody._path(card.root, plan["official_directory"]),
            plan["official_archive_sha256"],
            seed,
            plan["seed_sha256"],
        )
    return sha256(encoded(report)), holds


def _claim(card, *, started):
    return {
        "format": CLAIMS,
        **card.binding,
        "archive": str(card.folder),
        "training_prefix_sha256": card.prefix_sha,
        "started_at": started,
    }


async def collect(
    card, credential, *, api_transport=None, official_transport=None, delays=(1, 0.25)
):
    if not credential.strip():
        raise ValueError("result_slot_missing_credential")
    card.clock()
    card.claims.mkdir(exist_ok=True)
    check_attempt_directory(card.claims)
    with history.exclusive(card.claims):
        require(
            not card.claim.exists() and not card.claim.is_symlink(),
            "result_slot_week_consumed",
        )
        require(
            not card.folder.exists() and not card.folder.is_symlink(),
            "result_slot_archive_already_exists",
        )
        started = card.clock()
        history.save(card.claim, _claim(card, started=started.isoformat()))
        card.folder.mkdir(parents=True, exist_ok=False)
        history.save(
            card.folder / "claim.json", _claim(card, started=started.isoformat())
        )
        seed_root, directory = card.folder / "history", card.folder / "official"
        plan_sha, inventory_sha = None, None
        reason = None
        try:
            remaining = (
                timestamp(card.slot["closes_at"]) - card.clock()
            ).total_seconds()
            async with asyncio.timeout(remaining):
                seed, seed_path, seed_sha = await capture_api(
                    card, seed_root, credential, api_transport, delays[0]
                )
                archive = await capture_official(
                    card, directory, seed, seed_sha, official_transport, delays[1]
                )
                card.clock()
                path = card.folder / "outcome-plan.json"
                plan_sha = history.save(
                    path,
                    {
                        "format_version": OUTCOME_FORMAT,
                        "race_dates": card.scope["race_dates"],
                        "schedule_capture": str(card.schedule),
                        "schedule_sha256": card.binding["schedule_sha256"],
                        "seed_root": str(seed_root),
                        "seed_path": str(seed_path),
                        "seed_sha256": seed_sha,
                        "official_directory": str(directory),
                        "official_archive_sha256": archive["sha256"],
                    },
                )
                inventory_sha, holds = _inventory(card, history.pin(card.root, path))
                if holds:
                    raise Stop(holds[0])
                card.clock()
        except Stop as exc:
            reason = str(exc)
        except TimeoutError:
            reason = "observation_window_timeout"
        except (ValueError, OSError, KeyError, httpx.HTTPError):
            reason = "observation_collection_or_replay_failed"
        finish = {
            "format": FINISH,
            **card.binding,
            "completed_at": fold.now().isoformat(),
            "state": "failed" if reason else "captured",
            "reason": reason,
            "result_plan_sha256": None if reason else plan_sha,
            "inventory_sha256": None if reason else inventory_sha,
        }
        history.save(card.folder / "finish.json", finish)
        return {"state": finish["state"], "reason": reason, "week": card.slot["week"]}


def _close_record(card, instant):
    claimed = card.claim.exists()
    claim = parse(card.claim.read_bytes()) if claimed else _claim(card, started=None)
    require(
        claim == _claim(card, started=claim["started_at"]),
        "result_slot_other_week_claim",
    )
    if not claimed:
        require(not card.folder.exists(), "result_slot_archive_without_claim")
        history.save(card.claim, claim)
    card.folder.mkdir(parents=True, exist_ok=True)
    finish_path = custody._path(card.root, "finish.json", parent=card.folder)
    state = "not_run" if claim["started_at"] is None else "failed"
    digest, inventory = None, None
    if finish_path.exists() and state == "failed":
        try:
            finish = parse(finish_path.read_bytes())
            if (
                finish["format"] == FINISH
                and all(finish[k] == v for k, v in card.binding.items())
                and finish["state"] == "captured"
                and finish["reason"] is None
                and timestamp(card.slot["opens_at"])
                <= timestamp(claim["started_at"])
                <= timestamp(finish["completed_at"])
                < timestamp(card.slot["closes_at"])
            ):
                ref = history.pin(
                    card.root,
                    custody._path(card.root, "outcome-plan.json", parent=card.folder),
                )
                expected, holds = _inventory(card, ref)
                if not holds and (ref["sha256"], expected) == (
                    finish["result_plan_sha256"],
                    finish["inventory_sha256"],
                ):
                    state, digest, inventory = "observed", ref["sha256"], expected
        except (ValueError, TypeError, KeyError, OSError):
            # Keep the original attempt and make no substitute digest available.
            pass
    return {
        "format": witness.TERMINAL,
        **card.binding,
        "closed_at": instant.isoformat(),
        "state": state,
        "result_plan_sha256": digest,
        "inventory_sha256": inventory,
    }


def seal(card):
    instant = fold.now()
    require(timestamp(card.slot["closes_at"]) <= instant, "result_slot_not_closed")
    card.claims.mkdir(exist_ok=True)
    check_attempt_directory(card.claims)
    with history.exclusive(card.claims):
        require(not card.claim.is_symlink(), "result_slot_unsafe_week_claim")
        path = custody._path(card.root, "terminal.json", parent=card.folder)
        if path.exists():
            require(card.claim.exists(), "result_slot_terminal_without_claim")
            record = parse(path.read_bytes())
            closed = timestamp(record["closed_at"])
            require(
                timestamp(card.slot["closes_at"]) <= closed <= instant,
                "result_slot_terminal_clock_conflict",
            )
            original = _close_record(card, closed)
            require(record == original, "result_slot_sealed_evidence_changed")
            digest = sha256(path.read_bytes())
        else:
            digest = history.save(path, _close_record(card, instant))
    return witness.terminal_marker(card.rule_sha, card.slot["week"], digest)


def terminal_publication(card):
    path = custody._path(card.root, "terminal.json", parent=card.folder)
    require(path.is_file(), "result_slot_terminal_not_sealed")
    raw = seal(card)
    _, proof = publication.capture(
        card.folder / "terminal-publication",
        card.slot["receipt_pull"],
        witness.slot_document(card.rule_sha, card.slot["week"]),
        sha256(raw),
    )
    return proof


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=("rules-marker", "capture-rules", "collect", "seal", "witness"),
    )
    for name in ("rules", "enrollment", "inputs"):
        parser.add_argument(f"--{name}", required=name == "rules")
        parser.add_argument(f"--{name}-sha256", required=name == "rules")
    parser.add_argument("--rules-pull", type=int)
    parser.add_argument("--enrollment-pull", type=int)
    parser.add_argument("--week")
    parser.add_argument("--api-key-file", type=Path)
    args = parser.parse_args(argv)
    rules = {"path": args.rules, "sha256": args.rules_sha256}
    root = Path.cwd()
    if args.action == "rules-marker":
        fold._pinned(root, rules)
        sys.stdout.buffer.write(witness.rule_marker(args.rules_sha256))
        return 0
    if args.action == "capture-rules":
        print(json.dumps(rule_publication(root, rules, args.rules_pull), indent=2))
        return 0

    def reference(name):
        value, digest = getattr(args, name), getattr(args, f"{name}_sha256")
        if not value or not digest:
            parser.error(f"--{name} and --{name}-sha256 are required")
        return {"path": value, "sha256": digest}

    card = appointment(
        root,
        rules,
        reference("enrollment"),
        reference("inputs"),
        week=args.week,
        rules_pull=args.rules_pull,
        enrollment_pull=args.enrollment_pull,
    )
    if args.action == "seal":
        sys.stdout.buffer.write(seal(card))
        return 0
    if args.action == "witness":
        print(json.dumps(terminal_publication(card), indent=2))
        return 0
    if args.api_key_file is None:
        parser.error("collect requires --api-key-file")
    report = asyncio.run(collect(card, args.api_key_file.read_text()))
    print(json.dumps(report, indent=2))
    return 0 if report["state"] == "captured" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Stop as exc:
        print(json.dumps({"state": "blocked", "reason": str(exc)}), file=sys.stderr)
        raise SystemExit(2) from None
