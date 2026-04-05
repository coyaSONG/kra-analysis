"""Data loading helpers for prompt evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from feature_engineering import compute_race_features
from shared.data_adapter import convert_basic_data_to_enriched_format

FEATURE_SCHEMA_VERSION = "race-eval-v1"


@dataclass(slots=True)
class RaceEvaluationDataLoader:
    """Load and normalize race data for evaluation runs."""

    db_client: Any
    with_past_stats: bool = False

    def find_test_races(self, limit: int | None = None) -> list[dict[str, Any]]:
        races = self.db_client.find_races(limit=limit)
        print(f"테스트할 경주: {len(races)}개 (DB 데이터)")
        return races

    def build_dataset_metadata(
        self, races: list[dict[str, Any]], *, limit: int | None = None
    ) -> dict[str, Any]:
        race_ids = [str(race.get("race_id")) for race in races if race.get("race_id")]
        return {
            "source": "RaceDBClient.find_races",
            "requested_limit": limit,
            "race_count": len(races),
            "race_ids": race_ids,
            "feature_schema_version": FEATURE_SCHEMA_VERSION,
            "with_past_stats": self.with_past_stats,
        }

    def load_race_data(self, race_info: dict[str, Any]) -> dict[str, Any] | None:
        try:
            basic_data = self.db_client.load_race_basic_data(race_info["race_id"])
            if not basic_data:
                return None

            data = convert_basic_data_to_enriched_format(basic_data)
            if not data:
                return None

            items = data["response"]["body"]["items"]["item"]
            if not isinstance(items, list):
                items = [items]
            if not items:
                return None

            horses = self._build_horses(items)
            if self.with_past_stats and horses:
                self._inject_past_stats(horses, items)

            horses = compute_race_features(horses)
            first_item = items[0]

            return {
                "raceInfo": {
                    "rcDate": first_item["rcDate"],
                    "rcNo": first_item["rcNo"],
                    "rcName": first_item.get("rcName", ""),
                    "rcDist": first_item["rcDist"],
                    "track": first_item.get("track", ""),
                    "weather": first_item.get("weather", ""),
                    "meet": first_item["meet"],
                },
                "horses": horses,
            }
        except Exception as exc:
            print(f"데이터 로드 오류: {exc}")
            return None

    def build_v5_race_data(self, race_data: dict[str, Any]) -> dict[str, Any]:
        entries = []
        for horse in race_data.get("horses", []):
            entries.append(
                {
                    "horse_no": horse.get("chulNo"),
                    "win_odds": horse.get("winOdds", 0),
                    "jockey_name": horse.get("jkName", ""),
                    "jockey_winrate": horse.get("jkDetail", {}).get("winRate", 0),
                    "horse_name": horse.get("hrName", ""),
                    "horse_record": horse.get("hrDetail", {}),
                }
            )

        return {"entries": entries, "race_info": race_data.get("raceInfo", {})}

    def _build_horses(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        horses: list[dict[str, Any]] = []
        for item in items:
            if item.get("winOdds", 999) == 0:
                continue

            horse = {
                "chulNo": item["chulNo"],
                "hrName": item["hrName"],
                "hrNo": item["hrNo"],
                "jkName": item["jkName"],
                "jkNo": item["jkNo"],
                "trName": item["trName"],
                "trNo": item["trNo"],
                "wgBudam": item.get("wgBudam", 0),
                "winOdds": item["winOdds"],
                "plcOdds": item.get("plcOdds", 0),
                "rating": item.get("rating", 0),
                "rank": item.get("rank", ""),
                "age": item.get("age", 0),
                "sex": item.get("sex", ""),
                "hrDetail": item.get("hrDetail", {}),
                "jkDetail": item.get("jkDetail", {}),
                "trDetail": item.get("trDetail", {}),
            }
            horses.append(horse)

        return horses

    def _inject_past_stats(
        self, horses: list[dict[str, Any]], items: list[dict[str, Any]]
    ) -> None:
        hr_nos = [horse["hrNo"] for horse in horses if horse.get("hrNo")]
        race_date = items[0]["rcDate"]
        past_stats = self.db_client.get_past_top3_stats_for_race(
            hr_nos=hr_nos,
            race_date=race_date,
            lookback_days=90,
        )
        for horse in horses:
            hr_no = horse.get("hrNo", "")
            if hr_no in past_stats:
                horse["past_stats"] = past_stats[hr_no]
