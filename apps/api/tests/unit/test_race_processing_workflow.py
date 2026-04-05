from unittest.mock import AsyncMock

import pytest

from services.race_processing_workflow import (
    CollectOddsCommand,
    CollectRaceCommand,
    HorseFailure,
    MaterializeRaceCommand,
    OddsCollectionResult,
    RaceKey,
    RaceProcessingWorkflow,
    RaceSnapshot,
)


def _make_api_response(items):
    item_list = items if isinstance(items, list) else [items]
    return {
        "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE."},
            "body": {
                "items": {"item": item_list},
                "numOfRows": len(item_list),
                "pageNo": 1,
                "totalCount": len(item_list),
            },
        }
    }


class _FakeSource:
    def __init__(self):
        self.fetch_race_card = AsyncMock(
            return_value=_make_api_response(
                [
                    {"hrNo": "001", "hrName": "말1", "jkNo": "J01", "trNo": "T01"},
                    {"hrNo": "002", "hrName": "말2", "jkNo": "J02", "trNo": "T02"},
                ]
            )
        )
        self.fetch_race_plan = AsyncMock(return_value={"rank": "국6"})
        self.fetch_track = AsyncMock(return_value={"weather": "맑음"})
        self.fetch_cancelled_horses = AsyncMock(return_value=[])
        self.fetch_training_map = AsyncMock(return_value={"말1": {"remk_txt": "양호"}})
        self.fetch_final_odds = AsyncMock(
            return_value=_make_api_response(
                [
                    {
                        "pool": "단승식",
                        "chulNo": 1,
                        "chulNo2": 0,
                        "chulNo3": 0,
                        "odds": 5.0,
                    },
                    {
                        "pool": "UNKNOWN",
                        "chulNo": 2,
                        "chulNo2": 0,
                        "chulNo3": 0,
                        "odds": 3.0,
                    },
                ]
            )
        )


class _FakeRepo:
    def __init__(self, snapshot: RaceSnapshot | None = None):
        self.snapshot = snapshot
        self.saved_collection = None
        self.saved_failure = None
        self.saved_materialized = None
        self.odds_rows = None

    async def load(self, race_id: str):
        return self.snapshot

    async def save_collection(self, collected):
        self.saved_collection = collected

    async def save_collection_failure(self, key, *, race_info, reason):
        self.saved_failure = {"key": key, "race_info": race_info, "reason": reason}

    async def save_materialized(self, race_id, *, target, payload):
        self.saved_materialized = {
            "race_id": race_id,
            "target": target,
            "payload": payload,
        }

    async def upsert_odds(self, result, *, rows):
        self.odds_rows = {"result": result, "rows": rows}


@pytest.mark.asyncio
async def test_collect_uses_injected_horse_collector_and_save_hook():
    source = _FakeSource()
    repo = _FakeRepo()
    saved_payload = {}

    async def collect_horse_details(horse_basic, meet):
        if horse_basic["hr_no"] == "002":
            raise RuntimeError("horse detail failed")
        return {**horse_basic, "hrDetail": {"name": horse_basic["hr_name"]}}

    async def save_collection(payload):
        saved_payload.update(payload)

    workflow = RaceProcessingWorkflow(
        source=source,
        races=repo,
        collect_horse_details_fn=collect_horse_details,
        save_collection_fn=save_collection,
    )

    result = await workflow.collect(
        CollectRaceCommand(key=RaceKey("20260405", 1, 3), horse_failure_threshold=0.8)
    )

    assert result.status == "partial_failure"
    assert len(result.failed_horses) == 1
    assert result.failed_horses[0] == HorseFailure(
        horse_no="002", horse_name="말2", error="horse detail failed"
    )
    assert saved_payload["status"] == "partial_failure"
    assert saved_payload["race_plan"]["rank"] == "국6"
    assert saved_payload["horses"][0]["training"]["remk_txt"] == "양호"


@pytest.mark.asyncio
async def test_materialize_enriched_preprocesses_basic_data_before_enrichment():
    source = _FakeSource()
    repo = _FakeRepo(
        snapshot=RaceSnapshot(
            race_id="20260405_1_3",
            date="20260405",
            meet=1,
            race_number=3,
            basic_data={"horses": [{"hr_no": "001", "win_odds": 5.0}]},
            raw_data=None,
            enriched_data=None,
            result_data=None,
            collection_status="collected",
            enrichment_status="pending",
            result_status="pending",
        )
    )

    async def preprocess_payload(payload):
        return {**payload, "preprocessed": True}

    async def enrich_payload(payload):
        assert payload["preprocessed"] is True
        return {**payload, "enriched": True}

    workflow = RaceProcessingWorkflow(
        source=source,
        races=repo,
        preprocess_payload_fn=preprocess_payload,
        enrich_payload_fn=enrich_payload,
    )

    result = await workflow.materialize(
        MaterializeRaceCommand(race_id="20260405_1_3", target="enriched")
    )

    assert result.payload["enriched"] is True
    assert repo.saved_materialized["target"] == "enriched"
    assert repo.saved_materialized["payload"]["preprocessed"] is True


@pytest.mark.asyncio
async def test_collect_odds_upserts_only_valid_rows():
    source = _FakeSource()
    repo = _FakeRepo()
    workflow = RaceProcessingWorkflow(source=source, races=repo)

    result = await workflow.collect_odds(
        CollectOddsCommand(key=RaceKey("20260405", 1, 3), source="API160_1")
    )

    assert result == OddsCollectionResult(
        race_id="20260405_1_3",
        inserted_count=1,
        source="API160_1",
        error=None,
    )
    assert len(repo.odds_rows["rows"]) == 1
    assert repo.odds_rows["rows"][0]["pool"] == "WIN"
