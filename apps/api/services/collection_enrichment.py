"""Collection enrichment helpers."""

from datetime import datetime
from typing import Any, Awaitable, Callable

import pandas as pd
import structlog
from dateutil.relativedelta import relativedelta
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.kra_response_adapter import KRAResponseAdapter
from models.database_models import DataStatus, Race
from services.kra_api_service import KRAAPIService
from utils.field_mapping import convert_api_to_internal

logger = structlog.get_logger()

PastPerformanceFetcher = Callable[
    [str, str, AsyncSession | None], Awaitable[list[dict[str, Any]]]
]
JockeyStatsFetcher = Callable[[str, str, AsyncSession | None], Awaitable[dict[str, Any]]]
TrainerStatsFetcher = Callable[[str, str, AsyncSession | None], Awaitable[dict[str, Any]]]


async def enrich_data(
    data: dict[str, Any],
    db: AsyncSession | None,
    *,
    get_horse_past_performances: PastPerformanceFetcher,
    calculate_performance_stats_fn: Callable[[list[dict[str, Any]]], dict[str, Any]],
    get_default_stats_fn: Callable[[], dict[str, Any]],
    get_jockey_stats: JockeyStatsFetcher,
    get_trainer_stats: TrainerStatsFetcher,
    analyze_weather_impact_fn: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    """Apply enrichment to race data using injected fetch/calculation functions."""
    try:
        horses = data.get("horses", [])
        race_date = data.get("race_date")

        for horse in horses:
            horse_no = horse.get("hr_no") or horse.get("horse_no")

            past_performances = await get_horse_past_performances(
                horse_no, race_date, db
            )
            if past_performances:
                horse["past_stats"] = calculate_performance_stats_fn(past_performances)
            else:
                horse["past_stats"] = get_default_stats_fn()

            jockey_no = horse.get("jk_no") or horse.get("jockey_no")
            trainer_no = horse.get("tr_no") or horse.get("trainer_no")

            if jockey_no:
                horse["jockey_stats"] = await get_jockey_stats(jockey_no, race_date, db)

            if trainer_no:
                horse["trainer_stats"] = await get_trainer_stats(
                    trainer_no, race_date, db
                )

        weather = data.get("weather", {})
        weather_impact = analyze_weather_impact_fn(weather)

        return {
            **data,
            "horses": horses,
            "weather_impact": weather_impact,
            "enrichment_timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as exc:
        logger.error("Enrichment logic failed", error=str(exc))
        raise


async def get_horse_past_performances(
    horse_no: str, race_date: str, db: AsyncSession | None
) -> list[dict[str, Any]]:
    """Fetch horse performances in the 3 months leading up to a race date."""
    try:
        current_date = datetime.strptime(race_date, "%Y%m%d")
        three_months_ago = current_date - relativedelta(months=3)
        three_months_ago_str = three_months_ago.strftime("%Y%m%d")

        if db is None:
            return []

        result = await db.execute(
            select(Race)
            .where(
                and_(
                    Race.date >= three_months_ago_str,
                    Race.date < race_date,
                    Race.result_status == DataStatus.COLLECTED,
                )
            )
            .order_by(Race.date.desc())
        )
        races = result.scalars().all()

        performances = []
        for race in races:
            if not race.result_data:
                continue
            horses = race.result_data.get("horses", [])
            for horse in horses:
                if horse.get("hr_no") == horse_no:
                    performances.append(
                        {
                            "date": race.date,
                            "meet": race.meet,
                            "race_no": race.race_number,
                            "position": horse.get("ord", 0),
                            "win_odds": horse.get("win_odds", 0),
                            "rating": horse.get("rating", 0),
                            "weight": horse.get("weight", 0),
                            "jockey": horse.get("jk_name", ""),
                            "trainer": horse.get("tr_name", ""),
                        }
                    )
                    break

        return performances
    except Exception as exc:
        logger.warning(f"Failed to get past performances: {exc}")
        return []


def calculate_performance_stats(performances: list[dict[str, Any]]) -> dict[str, Any]:
    """Calculate aggregate horse performance statistics."""
    df = pd.DataFrame(performances)
    return {
        "total_races": len(performances),
        "wins": len(df[df["position"] == 1]),
        "win_rate": len(df[df["position"] == 1]) / len(df) if len(df) > 0 else 0,
        "avg_position": df["position"].mean() if "position" in df else 0,
        "recent_form": calculate_recent_form(df),
    }


def get_default_stats() -> dict[str, Any]:
    """Default performance statistics."""
    return {
        "total_races": 0,
        "wins": 0,
        "win_rate": 0,
        "avg_position": 0,
        "recent_form": 0,
    }


def calculate_recent_form(df: pd.DataFrame) -> float:
    """Calculate weighted recent-form score."""
    if len(df) == 0:
        return 0

    recent = df.head(5)
    weights = [5, 4, 3, 2, 1][: len(recent)]

    form_score = 0
    for i, (_, race) in enumerate(recent.iterrows()):
        position = race.get("position", 10)
        score = max(0, 11 - position) * weights[i]
        form_score += score

    max_score = sum(weights) * 10
    return form_score / max_score if max_score > 0 else 0


async def get_jockey_stats(
    kra_api: KRAAPIService, jockey_no: str, race_date: str, db: AsyncSession | None
) -> dict[str, Any]:
    """Fetch normalized jockey statistics."""
    _ = race_date, db
    try:
        jockey_info = await kra_api.get_jockey_info(jockey_no, use_cache=False)
        normalized_jockey = KRAResponseAdapter.normalize_jockey_info(jockey_info)
        if normalized_jockey:
            jk_data = convert_api_to_internal(normalized_jockey["raw_data"])
            return {
                "recent_win_rate": float(jk_data.get("win_rate_y", 0)) / 100,
                "career_win_rate": float(jk_data.get("win_rate_t", 0)) / 100,
                "total_wins": jk_data.get("ord1_cnt_t", 0),
                "total_races": jk_data.get("rc_cnt_t", 0),
                "recent_races": jk_data.get("rc_cnt_y", 0),
            }

        return {
            "recent_win_rate": 0.15,
            "career_win_rate": 0.12,
            "total_wins": 0,
            "total_races": 0,
            "recent_races": 0,
        }
    except Exception as exc:
        logger.warning(f"Failed to get jockey stats: {exc}")
        return {
            "recent_win_rate": 0.15,
            "career_win_rate": 0.12,
            "total_wins": 0,
            "total_races": 0,
            "recent_races": 0,
        }


async def get_trainer_stats(
    kra_api: KRAAPIService, trainer_no: str, race_date: str, db: AsyncSession | None
) -> dict[str, Any]:
    """Fetch normalized trainer statistics."""
    _ = race_date, db
    try:
        trainer_info = await kra_api.get_trainer_info(trainer_no, use_cache=False)
        normalized_trainer = KRAResponseAdapter.normalize_trainer_info(trainer_info)
        if normalized_trainer:
            tr_data = convert_api_to_internal(normalized_trainer["raw_data"])
            return {
                "recent_win_rate": float(tr_data.get("win_rate_y", 0)) / 100,
                "career_win_rate": float(tr_data.get("win_rate_t", 0)) / 100,
                "total_wins": tr_data.get("ord1_cnt_t", 0),
                "total_races": tr_data.get("rc_cnt_t", 0),
                "recent_races": tr_data.get("rc_cnt_y", 0),
                "plc_rate": float(tr_data.get("plc_rate_t", 0)) / 100,
                "meet": tr_data.get("meet", ""),
            }

        return {
            "recent_win_rate": 0.18,
            "career_win_rate": 0.16,
            "total_wins": 0,
            "total_races": 0,
            "recent_races": 0,
            "plc_rate": 0.35,
            "meet": "",
        }
    except Exception as exc:
        logger.warning(f"Failed to get trainer stats: {exc}")
        return {
            "recent_win_rate": 0.18,
            "career_win_rate": 0.16,
            "total_wins": 0,
            "total_races": 0,
            "recent_races": 0,
            "plc_rate": 0.35,
            "meet": "",
        }


def analyze_weather_impact(weather: dict[str, Any]) -> dict[str, Any]:
    """Compute simple weather impact multipliers."""
    track_condition = weather.get("track_condition", "good")
    impact = {
        "track_speed_factor": 1.0,
        "stamina_importance": 1.0,
        "weight_impact": 1.0,
    }

    if track_condition in ["heavy", "soft"]:
        impact["track_speed_factor"] = 0.95
        impact["stamina_importance"] = 1.2
        impact["weight_impact"] = 1.1
    elif track_condition == "firm":
        impact["track_speed_factor"] = 1.05
        impact["stamina_importance"] = 0.9

    return impact
