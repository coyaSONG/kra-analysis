"""공통 prerace prediction payload 빌더."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from evaluation.leakage_checks import FORBIDDEN_POST_RACE_FIELDS
from feature_engineering import compute_race_features

from shared.prediction_input_schema import validate_alternative_ranking_race_payload
from shared.prerace_field_policy import filter_prerace_payload
from shared.runner_status import select_prediction_candidates

HorseListPreprocessor = Callable[[list[dict[str, Any]]], list[dict[str, Any]] | None]
HorseFeatureBuilder = Callable[[list[dict[str, Any]]], list[dict[str, Any]]]
EntryChangeNotices = Sequence[Mapping[str, Any]]


def strip_forbidden_fields(
    data: dict[str, Any],
    *,
    path: str = "",
    removed_paths: list[str] | None = None,
) -> dict[str, Any]:
    """사후 결과 필드를 제거하고 `rank`를 `class_rank`로 정규화한다."""

    cleaned: dict[str, Any] = {}
    for key, value in data.items():
        current_path = f"{path}.{key}" if path else key
        if key == "rank":
            cleaned["class_rank"] = value
            continue
        if key in FORBIDDEN_POST_RACE_FIELDS:
            if removed_paths is not None:
                removed_paths.append(current_path)
            continue
        if isinstance(value, dict):
            cleaned[key] = strip_forbidden_fields(
                value,
                path=current_path,
                removed_paths=removed_paths,
            )
            continue
        if isinstance(value, list):
            cleaned[key] = [
                strip_forbidden_fields(
                    item,
                    path=f"{current_path}[{idx}]",
                    removed_paths=removed_paths,
                )
                if isinstance(item, dict)
                else item
                for idx, item in enumerate(value)
            ]
            continue
        cleaned[key] = value
    return cleaned


def _normalize_items(enriched: dict[str, Any]) -> list[dict[str, Any]]:
    items = enriched["response"]["body"]["items"]["item"]
    if not isinstance(items, list):
        items = [items]
    if not items:
        raise ValueError("enriched payload has no race items")
    return items


def _build_race_info(
    first_item: dict[str, Any],
    *,
    fallback_meet: str | int | None = None,
) -> dict[str, Any]:
    return {
        "rcDate": first_item.get("rcDate", ""),
        "rcNo": first_item.get("rcNo", ""),
        "rcName": first_item.get("rcName", ""),
        "rcDist": first_item.get("rcDist", ""),
        "track": first_item.get("track", ""),
        "weather": first_item.get("weather", ""),
        "meet": first_item.get("meet", fallback_meet or ""),
        "budam": first_item.get("budam", ""),
        "ageCond": first_item.get("ageCond", ""),
    }


def _safe_int(value: object) -> int | None:
    if value in ("", None):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_race_date(value: object) -> str | None:
    if value in ("", None):
        return None
    text = str(value)
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits[:8] if len(digits) >= 8 else None


def _jockey_change_notice_matches_race(
    notice: Mapping[str, Any],
    *,
    race_date: str,
    race_no: int | None,
) -> bool:
    if notice.get("change_type") != "jockey_change":
        return False
    if _normalize_race_date(notice.get("race_date")) != _normalize_race_date(race_date):
        return False
    notice_race_no = _safe_int(notice.get("race_no") or notice.get("rcNo"))
    return race_no is not None and notice_race_no == race_no


def _annotate_changed_jockey_state(
    horses: list[dict[str, Any]],
    *,
    race_date: str,
    race_no: int | None,
    entry_change_notices: EntryChangeNotices | None,
) -> dict[str, Any]:
    source_present = entry_change_notices is not None
    relevant: list[Mapping[str, Any]] = []
    if entry_change_notices is not None:
        relevant = [
            notice
            for notice in entry_change_notices
            if _jockey_change_notice_matches_race(
                notice,
                race_date=race_date,
                race_no=race_no,
            )
        ]

    by_chul_no = {
        chul_no: notice
        for notice in relevant
        if (chul_no := _safe_int(notice.get("chul_no") or notice.get("chulNo")))
        is not None
    }

    for horse in horses:
        chul_no = _safe_int(horse.get("chulNo"))
        notice = by_chul_no.get(chul_no)
        if not source_present:
            horse["changed_jockey_flag"] = None
            horse["changed_jockey_status"] = "source_missing"
            continue

        horse["changed_jockey_flag"] = 1.0 if notice is not None else 0.0
        horse["changed_jockey_status"] = (
            "changed" if notice is not None else "unchanged"
        )
        if notice is not None:
            horse["changed_jockey_notice"] = {
                "old_jockey_name": notice.get("old_jockey_name"),
                "old_jockey_no": notice.get("old_jockey_no"),
                "new_jockey_name": notice.get("new_jockey_name"),
                "new_jockey_no": notice.get("new_jockey_no"),
                "reason": notice.get("reason"),
                "announced_at": notice.get("announced_at"),
                "source_snapshot_at": notice.get("source_snapshot_at"),
            }

    return {
        "source_present": source_present,
        "notice_count": len(entry_change_notices or ()),
        "race_jockey_change_count": len(relevant),
        "matched_chul_nos": sorted(by_chul_no),
    }


def build_prerace_race_payload_from_enriched(
    enriched: dict[str, Any],
    *,
    race_id: str,
    race_date: str,
    meet: str | int | None = None,
    cancelled_horses: list[dict[str, Any]] | None = None,
    entry_change_notices: EntryChangeNotices | None = None,
    removed_paths: list[str] | None = None,
    horse_preprocessor: HorseListPreprocessor | None = None,
    feature_builder: HorseFeatureBuilder | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """enriched race payload를 공통 prerace/schema 계약으로 정규화한다."""

    items = _normalize_items(enriched)
    candidate_selection = select_prediction_candidates(
        items,
        cancelled_horses=cancelled_horses,
    )
    horses = [
        strip_forbidden_fields(
            item,
            path=f"horses[{idx}]",
            removed_paths=removed_paths,
        )
        for idx, item in enumerate(candidate_selection.eligible_runners)
    ]
    if horse_preprocessor is not None:
        processed = horse_preprocessor(horses)
        if processed is not None:
            horses = processed
    horses = (feature_builder or compute_race_features)(horses)
    entry_change_audit = _annotate_changed_jockey_state(
        horses,
        race_date=race_date,
        race_no=_safe_int(items[0].get("rcNo")),
        entry_change_notices=entry_change_notices,
    )

    race_payload: dict[str, Any] = {
        "race_id": race_id,
        "race_date": race_date,
        "race_info": _build_race_info(items[0], fallback_meet=meet),
        "horses": horses,
        "candidate_filter": candidate_selection.to_audit_dict(),
    }
    if meet is not None:
        race_payload["meet"] = meet

    filtered_payload, field_policy = filter_prerace_payload(race_payload)
    filtered_payload["input_schema"] = validate_alternative_ranking_race_payload(
        filtered_payload
    )
    return (
        filtered_payload,
        race_payload["candidate_filter"],
        field_policy,
        entry_change_audit,
    )
