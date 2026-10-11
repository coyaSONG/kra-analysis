"""Prepare a source-replayed PDF/API26 cohort, never a future evaluation universe."""

from __future__ import annotations

import argparse
import math
import platform
import re
from collections import defaultdict
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from shared.kra_entry_sheet import build_entry_snapshot
from shared.kra_race_card_pdf import NUMERIC_FIELDS

from autoresearch.kra_race_card_pdf_bundle import implementation_fingerprint
from autoresearch.kra_race_card_pdf_replay import (
    MAX_MANIFEST_BYTES,
    archive_path,
    parse_json,
    read_bytes,
    replay_entry_pages,
    sha256,
)
from autoresearch.kra_result_population_audit import inspect_top3
from autoresearch.kra_result_snapshot import replay_result_snapshot
from autoresearch.prerace_hash_witness import (
    DOCUMENT,
    audit_archive,
    collect_publication,
    timestamp,
)

ROOT = Path(__file__).resolve().parents[3]
CONTRACT = "pdf_api26_restricted_v1"
POLICY = "ordinary_versioned_results_full_observed_roster_v1"
API_FIELDS = ("age", "wgBudam", "rating", "rcCntT", "ord1CntT", "ord2CntT", "ord3CntT")
PDF_FIELDS = (
    *NUMERIC_FIELDS,
    *(f"{k}_missing" for k in NUMERIC_FIELDS),
    "training_summary_truncated",
)
API_COLUMNS = (*API_FIELDS, *(f"{k}_missing" for k in API_FIELDS))
EXTRA_IMPLEMENTATION = (
    "autoresearch/prerace_hash_witness.py",
    "autoresearch/restricted_cohort.py",
    "autoresearch/restricted_ablation.py",
    "autoresearch/kra_result_snapshot.py",
    "autoresearch/kra_result_population_audit.py",
    "shared/kra_result_history.py",
)


def encoded(value: Any) -> bytes:
    import json

    return (
        json.dumps(value, sort_keys=True, allow_nan=False, indent=2) + "\n"
    ).encode()


def implementation() -> dict[str, Any]:
    result = implementation_fingerprint()
    for name in EXTRA_IMPLEMENTATION:
        result["source_sha256"][name] = sha256(
            (ROOT / "packages/scripts" / name).read_bytes()
        )
    result["source_sha256"]["uv.lock"] = sha256((ROOT / "uv.lock").read_bytes())
    for name in ("numpy", "scipy", "scikit-learn", "joblib"):
        try:
            result["dependency_versions"][name] = version(name)
        except PackageNotFoundError:
            result["dependency_versions"][name] = "not_installed"
    result["python_version"] = platform.python_version()
    return result


def horse_id(value: Any) -> str:
    if type(value) is int and 0 < value < 100_000_000:
        return str(value)
    if isinstance(value, str) and re.fullmatch(r"[0-9]{1,8}", value) and int(value) > 0:
        return str(int(value))
    raise ValueError("invalid_restricted_horse_identity")


def numeric(value: Any, field: str) -> float | None:
    if value is None or (isinstance(value, str) and value.strip() in ("", "-")):
        return None
    if type(value) not in (str, int, float):
        raise ValueError(f"invalid_numeric_type:{field}")
    try:
        number = float(value)
    except ValueError as exc:
        raise ValueError(f"invalid_numeric_value:{field}") from exc
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"invalid_numeric_range:{field}")
    if field not in ("wgBudam", "trainer_win_rate") and not number.is_integer():
        raise ValueError(f"nonintegral_count:{field}")
    if field in ("age", "wgBudam") and number <= 0:
        raise ValueError(f"nonpositive_value:{field}")
    if field == "trainer_win_rate" and number > 1:
        raise ValueError("trainer_rate_not_fraction")
    return number


def project_features(raw: dict[str, Any], pdf: dict[str, Any]) -> dict[str, Any]:
    """Only explicitly named pre-race fields enter the matrix, never labels."""
    if not set(API_FIELDS) <= raw.keys() or set(pdf) != set(PDF_FIELDS):
        raise ValueError("restricted_feature_keys_mismatch")
    output = {}
    for field in API_FIELDS:
        output[field] = numeric(raw[field], field)
        output[f"{field}_missing"] = output[field] is None
    counts = [output[k] for k in ("rcCntT", "ord1CntT", "ord2CntT", "ord3CntT")]
    if all(n is not None for n in counts) and sum(counts[1:]) > counts[0]:
        raise ValueError("career_places_exceed_starts")
    for field in NUMERIC_FIELDS:
        output[field] = numeric(pdf[field], field)
        flag = pdf[f"{field}_missing"]
        if type(flag) is not bool or flag != (output[field] is None):
            raise ValueError("pdf_missing_flag_mismatch")
        output[f"{field}_missing"] = flag
    if type(pdf["training_summary_truncated"]) is not bool:
        raise ValueError("invalid_truncation_flag")
    output["training_summary_truncated"] = pdf["training_summary_truncated"]
    return output


def source_rows(
    plan: dict, bundle: dict, witness: dict, archive_root: Path
) -> list[dict]:
    archived = {r["race_id"]: r for r in bundle["races"]}
    evidence = {r["race_id"]: r for r in witness["ledger"]}
    pdf_rows = defaultdict(dict)
    for row in bundle["feature_rows"]:
        pdf_rows[row["race_id"]][row["chulNo"]] = row
    ledger = []
    for record in sorted(plan["races"], key=lambda r: r["race_id"]):
        key = record["race_id"]
        audit = evidence[key]
        features, roster = [], []
        reasons = list(audit["reasons"])
        if audit["raw_chain_verified"]:
            entry = audit["evidence"]["entry"]
            rows, manifest, _ = replay_entry_pages(
                archive_path(entry["manifest_path"], archive_root=archive_root),
                archive_root=archive_root,
                meet=record["meet"],
                race_date=record["race_date"],
                expected_sha256=record["entry_manifest_sha256"],
            )
            identity = {k: record[k] for k in ("meet", "race_date", "race_no")}
            snapshot = build_entry_snapshot(
                rows, **identity, collected_at=timestamp(manifest["collected_at"])
            )
            roster = [
                {
                    "chul_no": r["chulNo"],
                    "horse_id": horse_id(r["hrNo"]),
                    "raw_horse_id": r["hrNo"],
                }
                for r in snapshot["entries"]
            ]
            if len({r["horse_id"] for r in roster}) != len(roster):
                raise ValueError("canonical_entry_identity_collision")
            if len(roster) != archived[key]["entry_horse_count"]:
                raise ValueError("published_roster_count_drift")
            if audit["source_review_candidate"]:
                selected = {
                    int(r["chulNo"]): r
                    for r in rows
                    if int(r["rcNo"]) == record["race_no"]
                }
                if set(selected) != set(pdf_rows[key]):
                    raise ValueError("pdf_api_runner_set_mismatch")
                for runner in roster:
                    pdf = pdf_rows[key][runner["chul_no"]]
                    if horse_id(pdf["hrNo"]) != runner["horse_id"]:
                        raise ValueError("pdf_api_horse_id_mismatch")
                    features.append(
                        {
                            **runner,
                            "features": project_features(
                                selected[runner["chul_no"]], pdf["features"]
                            ),
                        }
                    )
        ledger.append(
            {
                "race_id": key,
                "source_eligible": audit["source_review_candidate"],
                "source_reasons": reasons,
                "roster": roster,
                "feature_rows": features,
                "expected_roster_count": archived[key]["entry_horse_count"],
            }
        )
    return ledger


def result_rows(plan: dict) -> tuple[list[dict], list[dict]]:
    if plan["format_version"] != "kra-result-population-plan-v1":
        raise ValueError("unsupported_result_plan")
    records, pins, seen = [], [], set()
    for source in plan["result_captures"]:
        report = replay_result_snapshot(
            Path(source["path"]),
            entry_capture=Path(source["entry_capture"])
            if source.get("entry_capture")
            else None,
            archive_root=Path(plan["archive_root"]),
        )
        if report["capture_manifest_sha256"] != source["sha256"]:
            raise ValueError("result_manifest_pin_mismatch")
        if (
            source.get("entry_capture")
            and report["entry_binding_pins"][0]["manifest_sha256"]
            != source["entry_sha256"]
        ):
            raise ValueError("result_entry_pin_mismatch")
        for row in report["records"]:
            key = (row["race_id"], row["chul_no"])
            if key in seen:
                raise ValueError("duplicate_result_capture_membership")
            seen.add(key)
        records.extend(report["records"])
        pins.append(
            {
                k: report[k]
                for k in (
                    "capture_manifest_sha256",
                    "page_pins",
                    "capture_completed_at",
                    "entry_binding_pins",
                )
            }
        )
    return records, pins


def join_labels(sources: list[dict], results: list[dict]) -> list[dict]:
    grouped = defaultdict(list)
    for row in results:
        grouped[row["race_id"]].append(row)
    ledger = []
    for source in sources:
        rows = grouped[source["race_id"]]
        status = inspect_top3(rows, source["expected_roster_count"])
        reasons = list(status["blockers"])
        expected = {(r["chul_no"], r["horse_id"]) for r in source["roster"]}
        actual = {(r["chul_no"], r["horse_id"]) for r in rows}
        if not expected or expected != actual or len(actual) != len(rows):
            reasons.append("full_result_roster_identity_mismatch")
        if any(horse_id(r["raw_horse_id"]) != r["horse_id"] for r in rows):
            reasons.append("raw_result_identity_mismatch")
        eligible = not reasons and status["status"] == "ordinary_rank_observation"
        ledger.append(
            {
                **source,
                "results": rows,
                "label_eligible": eligible,
                "label_reasons": sorted(set(reasons)),
                "label_top3": status["candidate_top3_horse_ids"] if eligible else None,
                "training_selected": source["source_eligible"] and eligible,
            }
        )
    return ledger


def validate_corpus(corpus: dict) -> list[dict]:
    if (
        corpus.get("format_version") != "kra-restricted-corpus-v1"
        or corpus.get("feature_contract") != CONTRACT
        or corpus.get("selection_policy") != POLICY
        or corpus.get("counts_as_70_percent_evidence") is not False
    ):
        raise ValueError("unsupported_restricted_corpus")
    ledger = corpus["ledger"]
    if not ledger or len({r["race_id"] for r in ledger}) != len(ledger):
        raise ValueError("invalid_corpus_inventory")
    selected = []
    for race in ledger:
        expected = race["source_eligible"] is True and race["label_eligible"] is True
        if (
            type(race["training_selected"]) is not bool
            or race["training_selected"] != expected
        ):
            raise ValueError("training_selection_policy_mismatch")
        if not expected:
            continue
        rows = race["feature_rows"]
        if not 3 <= len(rows) <= 20 or len(rows) != race["expected_roster_count"]:
            raise ValueError("incomplete_training_field")
        roster = {(r["chul_no"], r["horse_id"]) for r in race["roster"]}
        if len(roster) != len(rows) or roster != {
            (r["chul_no"], r["horse_id"]) for r in rows
        }:
            raise ValueError("training_roster_mismatch")
        if len({r["chul_no"] for r in rows}) != len(rows) or len(
            {r["horse_id"] for r in rows}
        ) != len(rows):
            raise ValueError("duplicate_training_identity")
        checked = join_labels(
            [
                {
                    k: v
                    for k, v in race.items()
                    if k
                    not in (
                        "results",
                        "label_eligible",
                        "label_reasons",
                        "label_top3",
                        "training_selected",
                    )
                }
            ],
            race["results"],
        )[0]
        if (
            not checked["training_selected"]
            or checked["label_top3"] != race["label_top3"]
        ):
            raise ValueError("training_label_mismatch")
        for row in rows:
            if (
                horse_id(row["horse_id"]) != row["horse_id"]
                or horse_id(row["raw_horse_id"]) != row["horse_id"]
            ):
                raise ValueError("noncanonical_training_identity")
            values = row["features"]
            rebuilt = project_features(
                {k: values[k] for k in API_FIELDS}, {k: values[k] for k in PDF_FIELDS}
            )
            if values != rebuilt:
                raise ValueError("training_feature_contract_mismatch")
        selected.append(race)
    if not selected:
        raise ValueError("empty_restricted_training_cohort")
    return selected


def write_new(path: Path, value: Any) -> str:
    raw = encoded(value)
    with path.open("xb") as stream:
        stream.write(raw)
    return sha256(raw)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("plan", "bundle", "archive-root", "result-plan", "output-dir"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args(argv)
    before = implementation()
    plan_raw = read_bytes(args.plan, limit=MAX_MANIFEST_BYTES)
    bundle_raw = read_bytes(args.bundle, limit=MAX_MANIFEST_BYTES)
    results_raw = read_bytes(args.result_plan, limit=MAX_MANIFEST_BYTES)
    directory = args.output_dir / (
        datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ") + "_" + uuid4().hex[:12]
    )
    directory.mkdir(parents=True)
    with httpx.Client(timeout=30, follow_redirects=False, trust_env=False) as client:
        document, witness = collect_publication(
            directory, number=61, document=DOCUMENT, client=client
        )
    audit = audit_archive(
        plan_bytes=plan_raw,
        bundle_bytes=bundle_raw,
        document_bytes=document,
        witness=witness,
        archive_root=args.archive_root,
    )
    sources = source_rows(
        parse_json(plan_raw), parse_json(bundle_raw), audit, args.archive_root
    )
    records, pins = result_rows(parse_json(results_raw))
    corpus = {
        "format_version": "kra-restricted-corpus-v1",
        "feature_contract": CONTRACT,
        "selection_policy": POLICY,
        "counts_as_70_percent_evidence": False,
        "materialized_at": datetime.now(UTC).isoformat(),
        "implementation": before,
        "input_plan_sha256": sha256(plan_raw),
        "feature_bundle_sha256": sha256(bundle_raw),
        "result_plan_sha256": sha256(results_raw),
        "source_witness": audit,
        "result_version_pins": pins,
        "official_finality_verified": False,
        "ledger": join_labels(sources, records),
    }
    selected = validate_corpus(corpus)
    if before != implementation():
        raise ValueError("implementation_changed_during_preparation")
    digest = write_new(directory / "corpus.json", corpus)
    print(
        encoded(
            {
                "corpus": str(directory / "corpus.json"),
                "sha256": digest,
                "inventory_races": len(sources),
                "selected_races": len(selected),
                "selected_rows": sum(len(r["feature_rows"]) for r in selected),
                "training_approved": False,
            }
        ).decode()
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
