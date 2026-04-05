"""Workflow boundary for single-race collection and materialization."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, Protocol

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from adapters.kra_response_adapter import KRAResponseAdapter
from models.database_models import DataStatus, Race, RaceOdds
from services.collection_enrichment import (
    analyze_weather_impact as analyze_weather_impact_helper,
)
from services.collection_enrichment import (
    calculate_performance_stats as calculate_performance_stats_helper,
)
from services.collection_enrichment import (
    enrich_data as enrich_data_helper,
)
from services.collection_enrichment import (
    get_default_stats as get_default_stats_helper,
)
from services.collection_enrichment import (
    get_horse_past_performances as get_horse_past_performances_helper,
)
from services.collection_enrichment import (
    get_jockey_stats as get_jockey_stats_helper,
)
from services.collection_enrichment import (
    get_trainer_stats as get_trainer_stats_helper,
)
from services.collection_enrichment import (
    prefetch_past_performances as prefetch_past_performances_helper,
)
from services.collection_preprocessing import preprocess_data as preprocess_data_helper
from utils.field_mapping import POOL_NAME_MAP, VALID_POOLS, convert_api_to_internal

logger = structlog.get_logger()


def _utcnow() -> datetime:
    """Return current UTC time as naive datetime for database writes."""
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass(frozen=True, slots=True)
class RaceKey:
    race_date: str
    meet: int
    race_number: int

    @property
    def race_id(self) -> str:
        return f"{self.race_date}_{self.meet}_{self.race_number}"


@dataclass(frozen=True, slots=True)
class CollectRaceCommand:
    key: RaceKey
    horse_failure_threshold: float = 0.5


@dataclass(frozen=True, slots=True)
class MaterializeRaceCommand:
    race_id: str
    target: Literal["preprocessed", "enriched"] = "enriched"


@dataclass(frozen=True, slots=True)
class CollectOddsCommand:
    key: RaceKey
    source: Literal["API160_1", "API301"] = "API160_1"


@dataclass(frozen=True, slots=True)
class HorseFailure:
    horse_no: str | None
    horse_name: str | None
    error: str


@dataclass(frozen=True, slots=True)
class CollectedRace:
    race_id: str
    key: RaceKey
    payload: dict[str, Any]
    status: Literal["success", "partial_failure"]
    failed_horses: tuple[HorseFailure, ...] = ()


@dataclass(frozen=True, slots=True)
class MaterializedRace:
    race_id: str
    target: Literal["preprocessed", "enriched"]
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class OddsCollectionResult:
    race_id: str
    inserted_count: int
    source: str
    error: str | None = None


@dataclass(frozen=True, slots=True)
class RaceSnapshot:
    race_id: str
    date: str
    meet: int
    race_number: int
    basic_data: dict[str, Any] | None
    raw_data: dict[str, Any] | None
    enriched_data: dict[str, Any] | None
    result_data: dict[str, Any] | None
    collection_status: str | None
    enrichment_status: str | None
    result_status: str | None


class KraRaceSourcePort(Protocol):
    async def fetch_race_card(self, key: RaceKey) -> dict[str, Any]: ...

    async def fetch_race_plan(self, key: RaceKey) -> dict[str, Any]: ...

    async def fetch_track(self, key: RaceKey) -> dict[str, Any]: ...

    async def fetch_cancelled_horses(self, key: RaceKey) -> list[dict[str, Any]]: ...

    async def fetch_training_map(self, race_date: str) -> dict[str, dict[str, Any]]: ...

    async def fetch_horse_bundle(
        self, horse_basic: dict[str, Any], *, meet: int
    ) -> dict[str, Any]: ...

    async def fetch_final_odds(
        self, key: RaceKey, *, source: str
    ) -> dict[str, Any]: ...


class RaceRepositoryPort(Protocol):
    async def load(self, race_id: str) -> RaceSnapshot | None: ...

    async def save_collection(self, collected: CollectedRace) -> None: ...

    async def save_collection_failure(
        self,
        key: RaceKey,
        *,
        race_info: dict[str, Any] | None,
        reason: str,
    ) -> None: ...

    async def save_materialized(
        self,
        race_id: str,
        *,
        target: Literal["preprocessed", "enriched"],
        payload: dict[str, Any],
    ) -> None: ...

    async def upsert_odds(
        self,
        result: OddsCollectionResult,
        *,
        rows: list[dict[str, Any]],
    ) -> None: ...


class RaceHistoryPort(Protocol):
    async def list_horse_performances(
        self, *, horse_no: str, race_date: str
    ) -> list[dict[str, Any]]: ...

    async def prefetch_horse_performances(
        self, *, race_date: str
    ) -> dict[str, list[dict[str, Any]]] | None: ...


HorseBundleCollector = Callable[[dict[str, Any], int], Awaitable[dict[str, Any]]]
PayloadTransformer = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
CollectionPayloadSaver = Callable[[dict[str, Any]], Awaitable[None]]
CollectionFailureSaver = Callable[
    [RaceKey, dict[str, Any] | None, str], Awaitable[None]
]


class SQLAlchemyRaceRepository:
    """Default repository adapter backed by an AsyncSession."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def load(self, race_id: str) -> RaceSnapshot | None:
        result = await self.db.execute(select(Race).where(Race.race_id == race_id))
        race = result.scalar_one_or_none()
        if race is None:
            return None
        return RaceSnapshot(
            race_id=race.race_id,
            date=race.date,
            meet=race.meet,
            race_number=race.race_number,
            basic_data=race.basic_data,
            raw_data=race.raw_data,
            enriched_data=race.enriched_data,
            result_data=race.result_data,
            collection_status=(
                race.collection_status.value
                if hasattr(race.collection_status, "value")
                else race.collection_status
            ),
            enrichment_status=(
                race.enrichment_status.value
                if hasattr(race.enrichment_status, "value")
                else race.enrichment_status
            ),
            result_status=(
                race.result_status.value
                if hasattr(race.result_status, "value")
                else race.result_status
            ),
        )

    async def save_collection(self, collected: CollectedRace) -> None:
        data = collected.payload
        existing = await self.db.execute(
            select(Race).where(
                and_(
                    Race.date == data["date"],
                    Race.meet == data["meet"],
                    Race.race_number == data["race_number"],
                )
            )
        )
        race = existing.scalar_one_or_none()

        if race:
            race.basic_data = data
            race.updated_at = _utcnow()
            race.collection_status = DataStatus.COLLECTED
            race.collected_at = _utcnow()
            race.status = DataStatus.COLLECTED
            race.race_date = data["date"]
            race.race_no = data["race_number"]
        else:
            race = Race(
                race_id=collected.race_id,
                date=data["date"],
                race_date=data["date"],
                meet=data["meet"],
                race_number=data["race_number"],
                race_no=data["race_number"],
                basic_data=data,
                status=DataStatus.COLLECTED,
                collection_status=DataStatus.COLLECTED,
                collected_at=_utcnow(),
            )
            self.db.add(race)

        await self.db.commit()

    async def save_collection_failure(
        self,
        key: RaceKey,
        *,
        race_info: dict[str, Any] | None,
        reason: str,
    ) -> None:
        existing = await self.db.execute(
            select(Race).where(Race.race_id == key.race_id)
        )
        race = existing.scalar_one_or_none()

        if race and race.collection_status in (
            DataStatus.COLLECTED,
            DataStatus.ENRICHED,
        ):
            race.updated_at = _utcnow()
            await self.db.commit()
            return

        failure_payload = {
            "race_info": race_info,
            "failure_reason": reason,
            "failed_at": datetime.now(UTC).isoformat(),
        }

        if race:
            race.raw_data = failure_payload
            race.collection_status = DataStatus.FAILED
            race.updated_at = _utcnow()
        else:
            race = Race(
                race_id=key.race_id,
                date=key.race_date,
                race_date=key.race_date,
                meet=key.meet,
                race_number=key.race_number,
                race_no=key.race_number,
                raw_data=failure_payload,
                status=DataStatus.FAILED,
                collection_status=DataStatus.FAILED,
                updated_at=_utcnow(),
            )
            self.db.add(race)

        await self.db.commit()

    async def save_materialized(
        self,
        race_id: str,
        *,
        target: Literal["preprocessed", "enriched"],
        payload: dict[str, Any],
    ) -> None:
        result = await self.db.execute(select(Race).where(Race.race_id == race_id))
        race = result.scalar_one_or_none()
        if race is None:
            raise ValueError(f"Race not found: {race_id}")

        race.enriched_data = payload
        race.enrichment_status = DataStatus.ENRICHED
        race.enriched_at = _utcnow()
        race.updated_at = _utcnow()
        await self.db.commit()

    async def upsert_odds(
        self,
        result: OddsCollectionResult,
        *,
        rows: list[dict[str, Any]],
    ) -> None:
        if not rows:
            return

        try:
            stmt = pg_insert(RaceOdds).values(rows)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_race_odds_entry",
                set_={"odds": stmt.excluded.odds, "collected_at": func.now()},
            )
            await self.db.execute(stmt)
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise


class SQLAlchemyRaceHistory:
    """Thin history adapter around existing enrichment helpers."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_horse_performances(
        self, *, horse_no: str, race_date: str
    ) -> list[dict[str, Any]]:
        return await get_horse_past_performances_helper(horse_no, race_date, self.db)

    async def prefetch_horse_performances(
        self, *, race_date: str
    ) -> dict[str, list[dict[str, Any]]] | None:
        return await prefetch_past_performances_helper(race_date, self.db)


class KraRaceSourceAdapter:
    """Default source adapter backed by KRAAPIService."""

    def __init__(self, kra_api):
        self.kra_api = kra_api

    async def fetch_race_card(self, key: RaceKey) -> dict[str, Any]:
        return await self.kra_api.get_race_info(
            key.race_date, str(key.meet), key.race_number
        )

    async def fetch_race_plan(self, key: RaceKey) -> dict[str, Any]:
        response = await self.kra_api.get_race_plan(key.race_date, str(key.meet))
        if not KRAResponseAdapter.is_successful_response(response):
            return {}
        for plan in KRAResponseAdapter.extract_items(response):
            if plan.get("rcNo") == key.race_number:
                return convert_api_to_internal(plan)
        return {}

    async def fetch_track(self, key: RaceKey) -> dict[str, Any]:
        response = await self.kra_api.get_track_info(key.race_date, str(key.meet))
        if not KRAResponseAdapter.is_successful_response(response):
            return {}
        for track in KRAResponseAdapter.extract_items(response):
            if track.get("rcNo") == key.race_number:
                return convert_api_to_internal(track)
        return {}

    async def fetch_cancelled_horses(self, key: RaceKey) -> list[dict[str, Any]]:
        response = await self.kra_api.get_cancelled_horses(key.race_date, str(key.meet))
        if not KRAResponseAdapter.is_successful_response(response):
            return []
        return [
            convert_api_to_internal(cancel)
            for cancel in KRAResponseAdapter.extract_items(response)
            if cancel.get("rcNo") == key.race_number
        ]

    async def fetch_training_map(self, race_date: str) -> dict[str, dict[str, Any]]:
        response = await self.kra_api.get_training_status(race_date)
        if not KRAResponseAdapter.is_successful_response(response):
            return {}

        training_map: dict[str, dict[str, Any]] = {}
        for training in KRAResponseAdapter.extract_items(response):
            hr_name = training.get("hrnm", "")
            if hr_name:
                training_map[hr_name] = convert_api_to_internal(training)
        return training_map

    async def fetch_horse_bundle(
        self, horse_basic: dict[str, Any], *, meet: int
    ) -> dict[str, Any]:
        horse_no = horse_basic.get("hr_no")
        jockey_no = horse_basic.get("jk_no")
        trainer_no = horse_basic.get("tr_no")

        horse_info = (
            await self.kra_api.get_horse_info(horse_no, use_cache=False)
            if horse_no
            else None
        )
        jockey_info = (
            await self.kra_api.get_jockey_info(jockey_no, use_cache=False)
            if jockey_no
            else None
        )
        trainer_info = (
            await self.kra_api.get_trainer_info(trainer_no, use_cache=False)
            if trainer_no
            else None
        )

        result = {**horse_basic}

        if horse_info:
            normalized_horse = KRAResponseAdapter.normalize_horse_info(horse_info)
            if normalized_horse:
                result["hrDetail"] = convert_api_to_internal(
                    normalized_horse["raw_data"]
                )

        if jockey_info:
            normalized_jockey = KRAResponseAdapter.normalize_jockey_info(jockey_info)
            if normalized_jockey:
                result["jkDetail"] = convert_api_to_internal(
                    normalized_jockey["raw_data"]
                )

        if trainer_info:
            normalized_trainer = KRAResponseAdapter.normalize_trainer_info(trainer_info)
            if normalized_trainer:
                result["trDetail"] = convert_api_to_internal(
                    normalized_trainer["raw_data"]
                )

        if jockey_no:
            try:
                jk_stats_response = await self.kra_api.get_jockey_stats(
                    str(jockey_no), meet=str(meet)
                )
                if jk_stats_response and KRAResponseAdapter.is_successful_response(
                    jk_stats_response
                ):
                    jk_stats_item = KRAResponseAdapter.extract_single_item(
                        jk_stats_response
                    )
                    if jk_stats_item:
                        result["jkStats"] = convert_api_to_internal(jk_stats_item)
            except Exception as exc:
                logger.warning(
                    "Failed to get jockey stats",
                    jockey_no=jockey_no,
                    error=str(exc),
                )

        owner_no = horse_basic.get("ow_no")
        if not owner_no and "hrDetail" in result:
            owner_no = result["hrDetail"].get("ow_no")
        if owner_no:
            try:
                owner_response = await self.kra_api.get_owner_info(
                    str(owner_no), meet=str(meet)
                )
                if owner_response and KRAResponseAdapter.is_successful_response(
                    owner_response
                ):
                    owner_item = KRAResponseAdapter.extract_single_item(owner_response)
                    if owner_item:
                        result["owDetail"] = convert_api_to_internal(owner_item)
            except Exception as exc:
                logger.warning(
                    "Failed to get owner info",
                    owner_no=owner_no,
                    error=str(exc),
                )

        return result

    async def fetch_final_odds(self, key: RaceKey, *, source: str) -> dict[str, Any]:
        if source == "API160_1":
            return await self.kra_api.get_final_odds(
                key.race_date, str(key.meet), race_no=key.race_number
            )
        return await self.kra_api.get_final_odds_total(
            key.race_date, str(key.meet), race_no=key.race_number
        )


class RaceProcessingWorkflow:
    """Deep module that owns the single-race processing lifecycle."""

    def __init__(
        self,
        *,
        source: KraRaceSourcePort,
        races: RaceRepositoryPort,
        history: RaceHistoryPort | None = None,
        preprocess_payload_fn: PayloadTransformer | None = None,
        enrich_payload_fn: PayloadTransformer | None = None,
        collect_horse_details_fn: HorseBundleCollector | None = None,
        save_collection_fn: CollectionPayloadSaver | None = None,
        save_collection_failure_fn: CollectionFailureSaver | None = None,
    ):
        self.source = source
        self.races = races
        self.history = history
        self.preprocess_payload_fn = preprocess_payload_fn
        self.enrich_payload_fn = enrich_payload_fn
        self.collect_horse_details_fn = collect_horse_details_fn
        self.save_collection_fn = save_collection_fn
        self.save_collection_failure_fn = save_collection_failure_fn

    async def collect(self, cmd: CollectRaceCommand) -> CollectedRace:
        key = cmd.key
        race_info = await self.source.fetch_race_card(key)

        if not race_info or not KRAResponseAdapter.is_successful_response(race_info):
            await self._save_collection_failure(
                key,
                race_info,
                "KRA API returned an unsuccessful race response",
            )
            raise ValueError(
                f"Race data is unavailable for {key.race_date} {key.meet}-{key.race_number}"
            )

        normalized_race = KRAResponseAdapter.normalize_race_info(race_info)
        horses = normalized_race["horses"]
        if not horses:
            await self._save_collection_failure(
                key,
                race_info,
                "KRA API returned no race items",
            )
            raise ValueError(
                f"Race data is empty for {key.race_date} {key.meet}-{key.race_number}"
            )

        race_plan_data = await self._safe_fetch(
            "race plan",
            lambda: self.source.fetch_race_plan(key),
            default={},
        )
        track_data = await self._safe_fetch(
            "track info",
            lambda: self.source.fetch_track(key),
            default={},
        )
        cancelled_horses_data = await self._safe_fetch(
            "cancelled horses",
            lambda: self.source.fetch_cancelled_horses(key),
            default=[],
        )
        training_map = await self._safe_fetch(
            "training status",
            lambda: self.source.fetch_training_map(key.race_date),
            default={},
        )

        horses_data: list[dict[str, Any]] = []
        failed_horses: list[HorseFailure] = []
        for horse in horses:
            horse_converted = convert_api_to_internal(horse)
            try:
                horse_detail = await self._collect_horse_details(
                    horse_converted, meet=key.meet
                )
                horses_data.append(horse_detail)
            except Exception as exc:
                failed_horse = HorseFailure(
                    horse_no=horse_converted.get("hr_no"),
                    horse_name=horse_converted.get("hr_name"),
                    error=str(exc),
                )
                logger.warning(
                    "Skipping horse after detail collection failure",
                    race_date=key.race_date,
                    meet=key.meet,
                    race_no=key.race_number,
                    horse_no=failed_horse.horse_no,
                    error=failed_horse.error,
                )
                failed_horses.append(failed_horse)

        if not horses_data or (
            len(failed_horses) / len(horses) >= cmd.horse_failure_threshold
        ):
            reason = (
                "Too many horse detail collection failures: "
                f"{len(failed_horses)}/{len(horses)}"
            )
            await self._save_collection_failure(key, race_info, reason)
            raise ValueError(reason)

        self._attach_training(horses_data, training_map)
        payload = self._build_collected_payload(
            key=key,
            race_info=race_info,
            race_plan=race_plan_data,
            track=track_data,
            cancelled_horses=cancelled_horses_data,
            horses=horses_data,
            failed_horses=failed_horses,
        )
        collected = CollectedRace(
            race_id=key.race_id,
            key=key,
            payload=payload,
            status="partial_failure" if failed_horses else "success",
            failed_horses=tuple(failed_horses),
        )
        await self._save_collection(collected)
        return collected

    async def materialize(self, cmd: MaterializeRaceCommand) -> MaterializedRace:
        snapshot = await self.races.load(cmd.race_id)
        if snapshot is None:
            raise ValueError(f"Race not found: {cmd.race_id}")

        if cmd.target == "preprocessed":
            if self.preprocess_payload_fn is None:
                raise RuntimeError("preprocess_payload_fn is required")
            payload = await self.preprocess_payload_fn(snapshot.basic_data)
            await self.races.save_materialized(
                cmd.race_id, target="preprocessed", payload=payload
            )
            return MaterializedRace(
                race_id=cmd.race_id,
                target="preprocessed",
                payload=payload,
            )

        if self.enrich_payload_fn is None:
            raise RuntimeError("enrich_payload_fn is required")

        base_data = snapshot.enriched_data or snapshot.basic_data or snapshot.raw_data
        if snapshot.enriched_data is not None:
            enriched_input = snapshot.enriched_data
        elif (
            snapshot.basic_data is not None
            and self.preprocess_payload_fn is not None
            and self._should_preprocess_before_enrich(snapshot.basic_data)
        ):
            enriched_input = await self.preprocess_payload_fn(snapshot.basic_data)
        else:
            enriched_input = base_data

        payload = await self.enrich_payload_fn(enriched_input)
        await self.races.save_materialized(
            cmd.race_id, target="enriched", payload=payload
        )
        return MaterializedRace(
            race_id=cmd.race_id,
            target="enriched",
            payload=payload,
        )

    async def collect_odds(self, cmd: CollectOddsCommand) -> OddsCollectionResult:
        valid_sources = {"API160_1", "API301"}
        if cmd.source not in valid_sources:
            return OddsCollectionResult(
                race_id=cmd.key.race_id,
                inserted_count=0,
                source=cmd.source,
                error=f"Invalid source: {cmd.source}. Must be one of {valid_sources}",
            )

        response = await self.source.fetch_final_odds(cmd.key, source=cmd.source)
        if not KRAResponseAdapter.is_successful_response(response):
            return OddsCollectionResult(
                race_id=cmd.key.race_id,
                inserted_count=0,
                source=cmd.source,
                error="API response failed",
            )

        items = KRAResponseAdapter.extract_items(response)
        rows: list[dict[str, Any]] = []
        for item in items:
            pool_raw = item.get("pool", "")
            pool = POOL_NAME_MAP.get(pool_raw, pool_raw)
            if pool not in VALID_POOLS:
                continue
            rows.append(
                {
                    "race_id": cmd.key.race_id,
                    "pool": pool,
                    "chul_no": item.get("chulNo", 0),
                    "chul_no2": item.get("chulNo2", 0),
                    "chul_no3": item.get("chulNo3", 0),
                    "odds": item.get("odds", 0),
                    "rc_date": cmd.key.race_date,
                    "source": cmd.source,
                }
            )

        result = OddsCollectionResult(
            race_id=cmd.key.race_id,
            inserted_count=len(rows),
            source=cmd.source,
        )
        if rows:
            try:
                await self.races.upsert_odds(result, rows=rows)
            except Exception as exc:
                logger.error(
                    "Failed to upsert race odds",
                    race_id=cmd.key.race_id,
                    error=str(exc),
                )
                return OddsCollectionResult(
                    race_id=cmd.key.race_id,
                    inserted_count=0,
                    source=cmd.source,
                    error=str(exc),
                )
        return result

    async def _safe_fetch(
        self,
        label: str,
        fetcher: Callable[[], Awaitable[Any]],
        *,
        default: Any,
    ) -> Any:
        try:
            return await fetcher()
        except Exception as exc:
            logger.warning(f"Failed to get {label}", error=str(exc))
            return default

    async def _collect_horse_details(
        self, horse_basic: dict[str, Any], *, meet: int
    ) -> dict[str, Any]:
        if self.collect_horse_details_fn is not None:
            return await self.collect_horse_details_fn(horse_basic, meet)
        return await self.source.fetch_horse_bundle(horse_basic, meet=meet)

    def _attach_training(
        self, horses_data: list[dict[str, Any]], training_map: dict[str, dict[str, Any]]
    ) -> None:
        unmatched_horses = []
        for horse_data in horses_data:
            hr_name = horse_data.get("hr_name", "")
            if hr_name and hr_name in training_map:
                horse_data["training"] = training_map[hr_name]
            elif hr_name and training_map:
                unmatched_horses.append(hr_name)
        if unmatched_horses:
            logger.warning(
                "Training data unmatched horses",
                unmatched=unmatched_horses,
                available=list(training_map.keys())[:10],
            )

    def _build_collected_payload(
        self,
        *,
        key: RaceKey,
        race_info: dict[str, Any],
        race_plan: dict[str, Any],
        track: dict[str, Any],
        cancelled_horses: list[dict[str, Any]],
        horses: list[dict[str, Any]],
        failed_horses: list[HorseFailure],
    ) -> dict[str, Any]:
        return {
            "race_date": key.race_date,
            "race_no": key.race_number,
            "date": key.race_date,
            "meet": key.meet,
            "race_number": key.race_number,
            "race_info": race_info,
            "race_plan": race_plan,
            "track": track,
            "cancelled_horses": cancelled_horses,
            "horses": horses,
            "failed_horses": [
                {
                    "horse_no": failure.horse_no,
                    "horse_name": failure.horse_name,
                    "error": failure.error,
                }
                for failure in failed_horses
            ],
            "status": "partial_failure" if failed_horses else "success",
            "collected_at": datetime.now(UTC).isoformat(),
        }

    def _should_preprocess_before_enrich(self, data: dict[str, Any] | None) -> bool:
        if not data:
            return False
        horses = data.get("horses", [])
        return any("win_odds" in horse for horse in horses)

    async def _save_collection(self, collected: CollectedRace) -> None:
        if self.save_collection_fn is not None:
            await self.save_collection_fn(collected.payload)
            return
        await self.races.save_collection(collected)

    async def _save_collection_failure(
        self,
        key: RaceKey,
        race_info: dict[str, Any] | None,
        reason: str,
    ) -> None:
        if self.save_collection_failure_fn is not None:
            await self.save_collection_failure_fn(key, race_info, reason)
            return
        await self.races.save_collection_failure(
            key, race_info=race_info, reason=reason
        )


async def _default_preprocess_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return preprocess_data_helper(payload)


def _build_default_enrich_payload(kra_api, db: AsyncSession) -> PayloadTransformer:
    async def enrich_payload(payload: dict[str, Any]) -> dict[str, Any]:
        async def get_jockey_stats(
            jockey_no: str, race_date: str, _db: AsyncSession | None
        ) -> dict[str, Any]:
            return await get_jockey_stats_helper(kra_api, jockey_no, race_date, db)

        async def get_trainer_stats(
            trainer_no: str, race_date: str, _db: AsyncSession | None
        ) -> dict[str, Any]:
            return await get_trainer_stats_helper(kra_api, trainer_no, race_date, db)

        return await enrich_data_helper(
            payload,
            db,
            get_horse_past_performances=get_horse_past_performances_helper,
            calculate_performance_stats_fn=calculate_performance_stats_helper,
            get_default_stats_fn=get_default_stats_helper,
            get_jockey_stats=get_jockey_stats,
            get_trainer_stats=get_trainer_stats,
            analyze_weather_impact_fn=analyze_weather_impact_helper,
        )

    return enrich_payload


def build_race_processing_workflow(
    kra_api,
    db: AsyncSession,
    *,
    preprocess_payload_fn: PayloadTransformer | None = None,
    enrich_payload_fn: PayloadTransformer | None = None,
    collect_horse_details_fn: HorseBundleCollector | None = None,
    save_collection_fn: CollectionPayloadSaver | None = None,
    save_collection_failure_fn: CollectionFailureSaver | None = None,
) -> RaceProcessingWorkflow:
    """Build the default workflow for a given API client and DB session."""
    return RaceProcessingWorkflow(
        source=KraRaceSourceAdapter(kra_api),
        races=SQLAlchemyRaceRepository(db),
        history=SQLAlchemyRaceHistory(db),
        preprocess_payload_fn=preprocess_payload_fn or _default_preprocess_payload,
        enrich_payload_fn=enrich_payload_fn
        or _build_default_enrich_payload(kra_api, db),
        collect_horse_details_fn=collect_horse_details_fn,
        save_collection_fn=save_collection_fn,
        save_collection_failure_fn=save_collection_failure_fn,
    )
