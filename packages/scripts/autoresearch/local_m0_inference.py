"""Read-only admission and API26 inference for one frozen research model."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from shared.kra_entry_sheet import build_entry_snapshot

from autoresearch.kra_race_card_pdf_replay import (
    MAX_MANIFEST_BYTES,
    archive_path,
    parse_json,
    read_bytes,
    replay_entry_pages,
    sha256,
)
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_ablation import RECIPE, input_matrix, predict, score_model
from autoresearch.restricted_cohort import (
    API_COLUMNS,
    API_FIELDS,
    ROOT,
    horse_id,
    numeric,
)

SERIES = "local_m0_20261016_18_v1"
DATES = ("20261016", "20261017", "20261018")
MODEL_NAME = "full_M0_model.json"
MODEL_SHA = "0c0078fb513d4acc2695427475b91668f20441bfab1f4ce05e0418277c8bbb74"
RECEIPT_SHA = "70cf1f7de5a51ae68f4706b6349686276c6bf23978d37f116072bcd61a7ef69b"
REVIEW_SHA = "d29499f0b9e409c25e6446ce8d4fe7abcbab71101af0399b72377c3610a5e60f"
REVIEW_PATH = ROOT / "data/contracts/restricted_training_review_v1.json"
INFERENCE_PINS = {
    "autoresearch/restricted_ablation.py": "2dc1f11bef99df0e7ddc16ede039cffa0e1a16ee82bb63736fe16d037529d48a",
    "autoresearch/restricted_cohort.py": "a2ec2dbe30a97624d508a9aa5b40f70010b615e01b4449574a6fff35fd29cf1c",
    "autoresearch/kra_race_card_pdf_replay.py": "2db618a34a77fe7ff03b8ea30e38e00a5d79ca94dbba75ffdb9a616a41ab45e0",
    "shared/kra_entry_sheet.py": "9fbc330976d58f7453e3a8b73721771db768e717e38a7010f6bd18e58f654cc6",
}


def pinned_json(path: Path, expected: str) -> dict:
    raw = read_bytes(path, limit=MAX_MANIFEST_BYTES)
    if sha256(raw) != expected:
        raise ValueError("local_m0_artifact_pin_mismatch")
    return parse_json(raw)


def load_model(directory: Path) -> tuple[dict, dict]:
    model = pinned_json(directory / MODEL_NAME, MODEL_SHA)
    receipt = pinned_json(directory / "receipt.json", RECEIPT_SHA)
    review = pinned_json(REVIEW_PATH, REVIEW_SHA)
    for name, expected in INFERENCE_PINS.items():
        if sha256((ROOT / "packages/scripts" / name).read_bytes()) != expected:
            raise ValueError("local_m0_inference_dependency_changed")
    if (
        receipt["status"] != "completed"
        or receipt["artifacts"][MODEL_NAME] != MODEL_SHA
        or receipt["review_sha256"] != REVIEW_SHA
        or model["arm"] != "M0"
        or model["recipe"] != RECIPE
        or receipt["recipe"] != RECIPE
        or model["columns"] != list(API_COLUMNS)
        or model["training_race_ids"] != review["selected_race_ids"]
        or any(key[:8] >= min(DATES) for key in model["training_race_ids"])
        or any(
            model[key] != receipt[key] or model[key] != review[key]
            for key in ("corpus_sha256", "implementation_sha256")
        )
        or model["source_review_id"] != review["review_id"]
        or receipt["source_review_id"] != review["review_id"]
    ):
        raise ValueError("local_m0_model_provenance_mismatch")
    timestamp(receipt["completed_at"])
    return model, receipt


def api_features(raw: dict) -> dict:
    if not set(API_FIELDS) <= raw.keys():
        raise ValueError("local_m0_missing_feature_key")
    values = {key: numeric(raw[key], key) for key in API_FIELDS}
    counts = [values[k] for k in ("rcCntT", "ord1CntT", "ord2CntT", "ord3CntT")]
    if all(n is not None for n in counts) and sum(counts[1:]) > counts[0]:
        raise ValueError("career_places_exceed_starts")
    return {**values, **{f"{k}_missing": v is None for k, v in values.items()}}


def project_capture(
    race: dict, path: Path, root: Path, *, expected_sha256: str | None = None
) -> dict:
    if race["race_id"] != f"{race['race_date']}_{race['meet']}_{race['race_no']}":
        raise ValueError("local_m0_target_identity_mismatch")
    path = archive_path(path, archive_root=root)
    rows, manifest, evidence = replay_entry_pages(
        path,
        archive_root=root,
        meet=race["meet"],
        race_date=race["race_date"],
        expected_sha256=expected_sha256,
    )
    captured = timestamp(manifest["collected_at"])
    snapshot = build_entry_snapshot(
        rows,
        meet=race["meet"],
        race_date=race["race_date"],
        race_no=race["race_no"],
        collected_at=captured,
    )
    start = timestamp(race["scheduled_start_at"])
    if snapshot["scheduled_start_time"] != start.astimezone(
        ZoneInfo("Asia/Seoul")
    ).strftime("%H%M"):
        raise ValueError("local_m0_schedule_time_conflict")
    if len(snapshot["entries"]) != race["runners"]:
        raise ValueError("local_m0_schedule_roster_count_conflict")
    if len(snapshot["entries"]) < 3:
        raise ValueError("local_m0_short_roster")
    selected = {int(r["chulNo"]): r for r in rows if int(r["rcNo"]) == race["race_no"]}
    features = [
        {
            "chul_no": r["chulNo"],
            "horse_id": horse_id(r["hrNo"]),
            "features": api_features(selected[r["chulNo"]]),
        }
        for r in snapshot["entries"]
    ]
    if len({r["horse_id"] for r in features}) != len(features):
        raise ValueError("local_m0_canonical_identity_collision")
    return {
        "race_id": race["race_id"],
        "feature_rows": features,
        "source": {**evidence, "available_at": captured.isoformat()},
    }


def score_capture(model: dict, projected: dict) -> dict:
    selection = predict(model, [projected])[0]
    values, _, identities = input_matrix([projected], "M0")
    scores = score_model(model, values)
    return {
        **projected,
        "horse_ids": sorted(selection["horse_ids"], key=int),
        "linear_scores": [
            {**row, "score": float(score)}
            for row, score in zip(identities, scores, strict=True)
        ],
        "scores_are_joint_probabilities": False,
    }


def check_prospective_times(race: dict, projected: dict, receipt: dict, now: datetime):
    cutoff = timestamp(race["feature_cutoff_at"])
    if not timestamp(projected["source"]["available_at"]) <= now < cutoff:
        raise ValueError("local_m0_source_or_completion_after_cutoff")
    if timestamp(receipt["completed_at"]) >= cutoff:
        raise ValueError("local_m0_model_not_before_target")
