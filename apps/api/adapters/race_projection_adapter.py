"""
Race projection adapter.

Normalize heterogeneous `result_data` shapes into a single internal contract.
"""

from __future__ import annotations

from typing import Any


class RaceProjectionAdapter:
    """Canonical adapter for race result projections."""

    @staticmethod
    def build_result_projection(
        top3: list[int],
        *,
        result_items: list[dict[str, Any]] | None = None,
        source: str = "result_collection_service",
    ) -> dict[str, Any]:
        horses = []
        for position, horse_no in enumerate(top3, start=1):
            source_item = RaceProjectionAdapter._find_source_item(
                result_items or [], horse_no
            )
            horses.append(
                {
                    "ord": position,
                    "chulNo": horse_no,
                    "hr_no": RaceProjectionAdapter._normalize_horse_no(horse_no),
                    "hr_name": source_item.get("hrName") or source_item.get("hr_name"),
                    "win_odds": RaceProjectionAdapter._safe_float(
                        source_item.get("win_odds")
                        or source_item.get("winOdds")
                        or source_item.get("odds")
                    ),
                    "rating": RaceProjectionAdapter._safe_int(source_item.get("rating")),
                    "weight": RaceProjectionAdapter._safe_float(source_item.get("weight")),
                }
            )

        return {
            "schema_version": 1,
            "source": source,
            "top3": list(top3),
            "horses": horses,
        }

    @staticmethod
    def extract_top3(result_data: Any) -> list[int]:
        projection = RaceProjectionAdapter.normalize_result_projection(result_data)
        return [int(horse["chulNo"]) for horse in projection["horses"]]

    @staticmethod
    def extract_result_horses(result_data: Any) -> list[dict[str, Any]]:
        projection = RaceProjectionAdapter.normalize_result_projection(result_data)
        return list(projection["horses"])

    @staticmethod
    def normalize_result_projection(result_data: Any) -> dict[str, Any]:
        if not result_data:
            return {"schema_version": 1, "top3": [], "horses": []}

        if isinstance(result_data, list):
            top3 = [int(item) for item in result_data if str(item).strip()]
            return RaceProjectionAdapter.build_result_projection(top3, result_items=[])

        if not isinstance(result_data, dict):
            return {"schema_version": 1, "top3": [], "horses": []}

        if "top3" in result_data or "horses" in result_data:
            top3 = RaceProjectionAdapter._extract_top3_from_horses(
                result_data.get("top3"), result_data.get("horses")
            )
            horses = RaceProjectionAdapter._normalize_horses(
                result_data.get("horses"), top3
            )
            return {
                "schema_version": result_data.get("schema_version", 1),
                "source": result_data.get("source", "legacy"),
                "top3": top3,
                "horses": horses,
            }

        if "result" in result_data:
            return RaceProjectionAdapter.normalize_result_projection(
                result_data.get("result")
            )

        return {"schema_version": 1, "top3": [], "horses": []}

    @staticmethod
    def _normalize_horses(
        horses: Any, top3: list[int] | None = None
    ) -> list[dict[str, Any]]:
        if not isinstance(horses, list):
            horses = []

        normalized: list[dict[str, Any]] = []
        for index, horse in enumerate(horses, start=1):
            if not isinstance(horse, dict):
                continue
            horse_no = horse.get("hr_no") or horse.get("hrNo") or horse.get("chulNo")
            ord_value = RaceProjectionAdapter._safe_int(
                horse.get("ord") or horse.get("position") or index
            )
            normalized.append(
                {
                    "ord": ord_value,
                    "chulNo": RaceProjectionAdapter._safe_int(horse_no),
                    "hr_no": RaceProjectionAdapter._normalize_horse_no(horse_no),
                    "hr_name": horse.get("hrName") or horse.get("hr_name"),
                    "win_odds": RaceProjectionAdapter._safe_float(
                        horse.get("win_odds")
                        or horse.get("winOdds")
                        or horse.get("odds")
                    ),
                    "rating": RaceProjectionAdapter._safe_int(horse.get("rating")),
                    "weight": RaceProjectionAdapter._safe_float(horse.get("weight")),
                }
            )

        if top3:
            top3_positions = {horse_no: idx + 1 for idx, horse_no in enumerate(top3)}
            for horse in normalized:
                if horse["chulNo"] in top3_positions and not horse["ord"]:
                    horse["ord"] = top3_positions[horse["chulNo"]]

        return normalized

    @staticmethod
    def _extract_top3_from_horses(
        top3: Any, horses: Any
    ) -> list[int]:
        if isinstance(top3, list) and top3:
            return [int(item) for item in top3 if str(item).strip()]

        normalized_horses = RaceProjectionAdapter._normalize_horses(horses)
        if not normalized_horses:
            return []

        top3_values: list[int] = []
        for horse in normalized_horses:
            if horse["ord"] > 0:
                top3_values.append(horse["ord"])
            elif horse["chulNo"] > 0:
                top3_values.append(horse["chulNo"])
        return top3_values

    @staticmethod
    def _find_source_item(
        items: list[dict[str, Any]], horse_no: int
    ) -> dict[str, Any]:
        for item in items:
            if not isinstance(item, dict):
                continue
            raw_no = item.get("chulNo") or item.get("hrNo") or item.get("hr_no")
            if RaceProjectionAdapter._safe_int(raw_no) == horse_no:
                return item
        return {}

    @staticmethod
    def _normalize_horse_no(value: Any) -> str | None:
        if value is None:
            return None
        value_str = str(value).strip()
        return value_str or None

    @staticmethod
    def _safe_int(value: Any) -> int:
        if value is None or value == "":
            return 0
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _safe_float(value: Any) -> float:
        if value is None or value == "":
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0
