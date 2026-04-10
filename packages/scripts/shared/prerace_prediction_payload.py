"""공통 prerace prediction payload 빌더."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from evaluation.leakage_checks import FORBIDDEN_POST_RACE_FIELDS
from feature_engineering import compute_race_features

from shared.prediction_input_schema import validate_alternative_ranking_race_payload
from shared.prerace_field_policy import filter_prerace_payload
from shared.runner_status import select_prediction_candidates

HorseListPreprocessor = Callable[[list[dict[str, Any]]], list[dict[str, Any]] | None]
HorseFeatureBuilder = Callable[[list[dict[str, Any]]], list[dict[str, Any]]]


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


def build_prerace_race_payload_from_enriched(
    enriched: dict[str, Any],
    *,
    race_id: str,
    race_date: str,
    meet: str | int | None = None,
    cancelled_horses: list[dict[str, Any]] | None = None,
    removed_paths: list[str] | None = None,
    horse_preprocessor: HorseListPreprocessor | None = None,
    feature_builder: HorseFeatureBuilder | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
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
    return filtered_payload, race_payload["candidate_filter"], field_policy
