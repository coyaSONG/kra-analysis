from __future__ import annotations

import pytest
from sqlalchemy import select

from models.database_models import Race
from services.prerace_postprocessing import normalize_and_validate_prerace_payload
from services.race_processing_workflow import (
    CollectedRace,
    RaceKey,
    SQLAlchemyRaceRepository,
)


def _make_race_info(items):
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


def _payload_for_storage_pipeline() -> dict:
    return {
        "race_date": "20260405",
        "race_no": 3,
        "date": "20260405",
        "meet": 1,
        "race_number": 3,
        "race_info": _make_race_info(
            [
                {
                    "rcDate": "20260405",
                    "rcNo": "3",
                    "meet": "서울",
                    "chulNo": 1,
                    "hrNo": "001",
                    "hrName": "말1",
                    "jkNo": "J01",
                    "jkName": "기수1",
                    "trNo": "T01",
                    "trName": "조교사1",
                    "owNo": "O01",
                    "owName": "마주1",
                    "age": 3,
                    "sex": "수",
                    "name": "한국",
                    "rank": "국6등급",
                    "rating": 31,
                    "wgBudam": 55,
                    "wgBudamBigo": "-",
                    "wgHr": "470(+2)",
                    "winOdds": 3.4,
                    "plcOdds": 1.4,
                    "ord": 1,
                    "diffUnit": "목",
                }
            ]
        ),
        "race_plan": {
            "rank": "국6등급",
            "budam": "별정A",
            "rcDist": "1200",
            "ageCond": "연령오픈",
            "schStTime": "1450",
        },
        "track": {
            "weather": "맑음",
            "track": "건조",
            "waterPercent": "4",
            "temperature": "18",
        },
        "cancelled_horses": [],
        "horses": [
            {
                "chulNo": 1,
                "hrNo": "001",
                "hrName": "말1",
                "jkNo": "J01",
                "jkName": "기수1",
                "trNo": "T01",
                "trName": "조교사1",
                "owNo": "O01",
                "owName": "마주1",
                "age": 3,
                "sex": "수",
                "name": "한국",
                "rank": "국6등급",
                "rating": 31,
                "wgBudam": 55,
                "wgBudamBigo": "-",
                "wgHr": "470(+2)",
                "winOdds": 3.4,
                "plcOdds": 1.4,
                "hrDetail": {"birth": "20210301", "cntT": 12},
                "training": {"remkTxt": "양호"},
            }
        ],
        "failed_horses": [],
        "status": "success",
        "collected_at": "2026-04-10T09:00:00+09:00",
    }


@pytest.mark.asyncio
@pytest.mark.integration
async def test_repository_storage_pipeline_separates_allowed_tagged_and_blocked_fields(
    db_session,
):
    repo = SQLAlchemyRaceRepository(db_session)
    payload = normalize_and_validate_prerace_payload(_payload_for_storage_pipeline())

    await repo.save_collection(
        CollectedRace(
            race_id="20260405_1_3",
            key=RaceKey("20260405", 1, 3),
            payload=payload,
            status="success",
        )
    )

    stored = (
        await db_session.execute(select(Race).where(Race.race_id == "20260405_1_3"))
    ).scalar_one()
    race_info_item = stored.basic_data["race_info"]["response"]["body"]["items"][
        "item"
    ][0]
    horse = stored.basic_data["horses"][0]
    horse_shadow = stored.raw_data["tagged_field_shadow"]["horses"][0]["fields"]

    assert "source_field_tags" not in stored.basic_data
    assert stored.basic_data["race_plan"]["sch_st_time"] == "1450"
    assert stored.basic_data["track"]["temperature"] == "18"
    assert race_info_item["rank"] == "국6등급"
    assert "ord" not in race_info_item
    assert "diffUnit" not in race_info_item
    assert race_info_item["winOdds"] == 3.4
    assert horse["hrDetail"] == {"birth": "20210301", "cntT": 12}
    assert horse["training"] == {"remkTxt": "양호"}
    assert "hrDetail" not in horse_shadow
    assert "training" not in horse_shadow
    assert horse_shadow["win_odds"] == 3.4
    assert (
        stored.raw_data["source_field_tags"]["summary"]["post_entry_field_count"] >= 2
    )
    assert (
        stored.raw_data["tagged_field_shadow"]["race_info_items"][0]["fields"]["ord"]
        == 1
    )
    assert (
        stored.raw_data["tagged_field_shadow"]["race_info_items"][0]["fields"][
            "diffUnit"
        ]
        == "목"
    )
    assert (
        stored.raw_data["tagged_field_shadow"]["race_info_items"][0]["fields"][
            "winOdds"
        ]
        == 3.4
    )
    assert "race_plan" not in stored.raw_data["tagged_field_shadow"]
    assert "track" not in stored.raw_data["tagged_field_shadow"]
