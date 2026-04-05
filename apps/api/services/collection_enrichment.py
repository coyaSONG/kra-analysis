"""Collection enrichment helpers."""

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import pandas as pd
import structlog
from dateutil.relativedelta import relativedelta
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.kra_response_adapter import KRAResponseAdapter
from adapters.race_projection_adapter import RaceProjectionAdapter
from models.database_models import DataStatus, Race
from services.kra_api_service import KRAAPIService
from utils.field_mapping import convert_api_to_internal

logger = structlog.get_logger()

PastPerformanceFetcher = Callable[
    [str, str, AsyncSession | None], Awaitable[list[dict[str, Any]]]
]
JockeyStatsFetcher = Callable[
    [str, str, AsyncSession | None], Awaitable[dict[str, Any]]
]
TrainerStatsFetcher = Callable[
    [str, str, AsyncSession | None], Awaitable[dict[str, Any]]
]

_DEFAULT_JOCKEY_STATS: dict[str, Any] = {
    "recent_win_rate": 0.15,
    "career_win_rate": 0.12,
    "total_wins": 0,
    "total_races": 0,
    "recent_races": 0,
}

_DEFAULT_TRAINER_STATS: dict[str, Any] = {
    "recent_win_rate": 0.18,
    "career_win_rate": 0.16,
    "total_wins": 0,
    "total_races": 0,
    "recent_races": 0,
    "plc_rate": 0.35,
    "meet": "",
}


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
        race_date = data.get("race_date") or data.get("date")

        # --- Phase 2: prefetch past performances (1 DB query) ---
        perf_map = await prefetch_past_performances(race_date, db)

        for horse in horses:
            horse_no = horse.get("hr_no") or horse.get("horse_no")
            horse_no_str = str(horse_no) if horse_no else None
            # chul_no is race entry number (1-15), used as key in result_data
            chul_no_str = str(horse.get("chul_no", "")) or None

            if perf_map is not None and (chul_no_str or horse_no_str):
                past_performances = (
                    perf_map.get(chul_no_str, [])
                    if chul_no_str
                    else perf_map.get(horse_no_str, [])
                )
                if not past_performances and horse_no_str:
                    past_performances = await get_horse_past_performances(
                        horse_no_str, race_date, db
                    )
                if past_performances:
                    horse["past_stats"] = calculate_performance_stats_fn(
                        past_performances
                    )
                else:
                    horse["past_stats"] = get_default_stats_fn()
            elif horse_no_str:
                past_performances = await get_horse_past_performances(
                    horse_no_str, race_date, db
                )
                if past_performances:
                    horse["past_stats"] = calculate_performance_stats_fn(
                        past_performances
                    )
                else:
                    horse["past_stats"] = get_default_stats_fn()
            else:
                horse["past_stats"] = get_default_stats_fn()

            # --- Extract jockey/trainer stats from embedded detail data ---
            # basic_data already contains jkDetail/trDetail from collection
            jk_detail = horse.get("jkDetail")
            tr_detail = horse.get("trDetail")

            if jk_detail:
                horse["jockey_stats"] = _extract_jockey_stats(jk_detail)
            else:
                jockey_no = horse.get("jk_no") or horse.get("jockey_no")
                if jockey_no:
                    horse["jockey_stats"] = await get_jockey_stats(
                        jockey_no, race_date, db
                    )

            if tr_detail:
                horse["trainer_stats"] = _extract_trainer_stats(tr_detail)
            else:
                trainer_no = horse.get("tr_no") or horse.get("trainer_no")
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
            "enrichment_timestamp": datetime.now(UTC).isoformat(),
        }
    except Exception as exc:
        logger.error("Enrichment logic failed", error=str(exc))
        raise


def _extract_jockey_stats(jk_detail: dict[str, Any]) -> dict[str, Any]:
    """Extract jockey stats from embedded jkDetail in basic_data."""
    rc_cnt_t = jk_detail.get("rc_cnt_t", 0)
    ord1_cnt_t = jk_detail.get("ord1_cnt_t", 0)
    win_rate_t = jk_detail.get("win_rate_t")
    win_rate_y = jk_detail.get("win_rate_y")
    return {
        "recent_win_rate": float(win_rate_y) / 100
        if win_rate_y
        else (float(ord1_cnt_t) / rc_cnt_t if rc_cnt_t else 0),
        "career_win_rate": float(win_rate_t) / 100
        if win_rate_t
        else (float(ord1_cnt_t) / rc_cnt_t if rc_cnt_t else 0),
        "total_wins": ord1_cnt_t,
        "total_races": rc_cnt_t,
        "recent_races": jk_detail.get("rc_cnt_y", 0),
    }


def _extract_trainer_stats(tr_detail: dict[str, Any]) -> dict[str, Any]:
    """Extract trainer stats from embedded trDetail in basic_data."""
    rc_cnt_t = tr_detail.get("rc_cnt_t", 0)
    ord1_cnt_t = tr_detail.get("ord1_cnt_t", 0)
    win_rate_t = tr_detail.get("win_rate_t")
    win_rate_y = tr_detail.get("win_rate_y")
    plc_rate_t = tr_detail.get("plc_rate_t")
    return {
        "recent_win_rate": float(win_rate_y) / 100
        if win_rate_y
        else (float(ord1_cnt_t) / rc_cnt_t if rc_cnt_t else 0),
        "career_win_rate": float(win_rate_t) / 100
        if win_rate_t
        else (float(ord1_cnt_t) / rc_cnt_t if rc_cnt_t else 0),
        "total_wins": ord1_cnt_t,
        "total_races": rc_cnt_t,
        "recent_races": tr_detail.get("rc_cnt_y", 0),
        "plc_rate": float(plc_rate_t) / 100 if plc_rate_t else 0.0,
        "meet": tr_detail.get("meet", ""),
    }


async def prefetch_past_performances(
    race_date: str | None, db: AsyncSession | None
) -> dict[str, list[dict[str, Any]]] | None:
    """Prefetch all past performances for a race date in a single DB query.

    Returns a dict mapping horse_no -> list of performance records,
    or None if prefetch is not possible.
    """
    if not race_date or db is None:
        return None

    try:
        current_date = datetime.strptime(race_date, "%Y%m%d")
        three_months_ago = current_date - relativedelta(months=3)
        three_months_ago_str = three_months_ago.strftime("%Y%m%d")

        result = await db.execute(
            select(Race.date, Race.meet, Race.race_number, Race.result_data)
            .where(
                and_(
                    Race.date >= three_months_ago_str,
                    Race.date < race_date,
                    Race.result_status == DataStatus.COLLECTED,
                )
            )
            .order_by(Race.date.desc())
        )
        rows = result.all()

        perf_map: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            horses = RaceProjectionAdapter.extract_result_horses(row.result_data)
            for horse in horses:
                horse_no = horse.get("hr_no") or str(horse.get("chulNo", ""))
                if not horse_no:
                    continue
                perf_map.setdefault(horse_no, []).append(
                    {
                        "date": row.date,
                        "meet": row.meet,
                        "race_no": row.race_number,
                        "position": horse.get("ord", 0),
                        "win_odds": horse.get("win_odds", 0),
                        "rating": horse.get("rating", 0),
                        "weight": horse.get("weight", 0),
                        "jockey": horse.get("jk_name", horse.get("jkName", "")),
                        "trainer": horse.get("tr_name", horse.get("trName", "")),
                    }
                )
        return perf_map
    except Exception as exc:
        logger.warning(f"Failed to prefetch past performances: {exc}")
        return None


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
            horses = RaceProjectionAdapter.extract_result_horses(race.result_data)
            for horse in horses:
                if (
                    horse.get("hr_no") == horse_no
                    or str(horse.get("chulNo")) == horse_no
                ):
                    performances.append(
                        {
                            "date": race.date,
                            "meet": race.meet,
                            "race_no": race.race_number,
                            "position": horse.get("ord", 0),
                            "win_odds": horse.get("win_odds", 0),
                            "rating": horse.get("rating", 0),
                            "weight": horse.get("weight", 0),
                            "jockey": horse.get("jk_name", horse.get("jkName", "")),
                            "trainer": horse.get("tr_name", horse.get("trName", "")),
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
        jockey_info = await kra_api.get_jockey_info(jockey_no)
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

        return dict(_DEFAULT_JOCKEY_STATS)
    except Exception as exc:
        logger.warning(f"Failed to get jockey stats: {exc}")
        return dict(_DEFAULT_JOCKEY_STATS)


async def get_trainer_stats(
    kra_api: KRAAPIService, trainer_no: str, race_date: str, db: AsyncSession | None
) -> dict[str, Any]:
    """Fetch normalized trainer statistics."""
    _ = race_date, db
    try:
        trainer_info = await kra_api.get_trainer_info(trainer_no)
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

        return dict(_DEFAULT_TRAINER_STATS)
    except Exception as exc:
        logger.warning(f"Failed to get trainer stats: {exc}")
        return dict(_DEFAULT_TRAINER_STATS)


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
