"""Data loading helpers for prompt evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from shared.prediction_input_schema import build_alternative_ranking_dataset_metadata
from shared.prerace_standard_loader import load_standardized_prerace_payload
from shared.read_contract import RaceSourceLookup


class RaceSourceQueryPort(Protocol):
    """Common query interface for source lookups anchored to a race snapshot."""

    def find_races_with_results(
        self,
        date_filter: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]: ...

    def load_race_basic_data(
        self,
        race_id: str,
        *,
        lookup: RaceSourceLookup,
    ) -> dict[str, Any] | None: ...

    def get_past_top3_stats_for_race(
        self,
        hr_nos: list[str],
        *,
        lookup: RaceSourceLookup,
        lookback_days: int = 90,
    ) -> dict[str, dict[str, Any]]: ...


@dataclass(slots=True)
class RaceEvaluationDataLoader:
    """Load and normalize race data for evaluation runs."""

    db_client: RaceSourceQueryPort
    with_past_stats: bool = False

    def find_test_races(self, limit: int | None = None) -> list[dict[str, Any]]:
        races = self.db_client.find_races_with_results(limit=limit)
        print(f"테스트할 경주: {len(races)}개 (DB 데이터)")
        return races

    def build_dataset_metadata(
        self, races: list[dict[str, Any]], *, limit: int | None = None
    ) -> dict[str, Any]:
        race_ids = [str(race.get("race_id")) for race in races if race.get("race_id")]
        return build_alternative_ranking_dataset_metadata(
            source="RaceDBClient.find_races_with_results",
            dataset_name="live_db_evaluation",
            requested_limit=limit,
            race_ids=race_ids,
            with_past_stats=self.with_past_stats,
        )

    def load_race_data(self, race_info: dict[str, Any]) -> dict[str, Any] | None:
        standardized = self.load_standardized_race_data(race_info)
        return standardized.standard_payload if standardized is not None else None

    def load_standardized_race_data(
        self,
        race_info: dict[str, Any],
    ) -> Any | None:
        try:
            lookup = RaceSourceLookup.from_race_info(race_info)
            standardized = load_standardized_prerace_payload(
                race_info,
                query_port=self.db_client,
                horse_preprocessor=(
                    lambda horses: self._prepare_horses_with_optional_stats(
                        horses,
                        lookup=lookup,
                    )
                ),
            )
            return standardized
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

        return {
            "entries": entries,
            "race_info": race_data.get("race_info") or race_data.get("raceInfo", {}),
        }

    def _inject_past_stats(
        self,
        horses: list[dict[str, Any]],
        *,
        lookup: RaceSourceLookup,
    ) -> None:
        hr_nos = [horse["hrNo"] for horse in horses if horse.get("hrNo")]
        past_stats = self.db_client.get_past_top3_stats_for_race(
            hr_nos=hr_nos,
            lookup=lookup,
            lookback_days=90,
        )
        for horse in horses:
            hr_no = horse.get("hrNo", "")
            if hr_no in past_stats:
                horse["past_stats"] = past_stats[hr_no]

    def _prepare_horses_with_optional_stats(
        self,
        horses: list[dict[str, Any]],
        *,
        lookup: RaceSourceLookup,
    ) -> list[dict[str, Any]]:
        if self.with_past_stats and horses:
            self._inject_past_stats(horses, lookup=lookup)
        return horses
