from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RaceStatus(str, Enum):
    PENDING = "pending"
    COLLECTED = "collected"
    ENRICHED = "enriched"
    FAILED = "failed"


class CollectRaceRequest(BaseModel):
    date: str = Field(..., description="날짜 (YYYYMMDD)")
    meet: int = Field(
        ..., ge=1, le=3, description="경마장 (1:서울, 2:제주, 3:부산경남)"
    )
    race_no: int | None = Field(None, ge=1, le=20, description="경주 번호")


class CollectRaceResponse(BaseModel):
    job_id: str
    status: str
    message: str


class HorseInfo(BaseModel):
    horse_no: str
    horse_name: str
    age: int
    gender: str
    country: str
    weight: float
    jockey_name: str
    trainer_name: str
    win_odds: float

    class Config:
        json_schema_extra = {
            "example": {
                "horse_no": "041234",
                "horse_name": "천년의질주",
                "age": 4,
                "gender": "암",
                "country": "한",
                "weight": 450.0,
                "jockey_name": "문세영",
                "trainer_name": "김영관",
                "win_odds": 5.2,
            }
        }


class RaceData(BaseModel):
    id: str | None = None
    date: str
    meet: int
    race_no: int
    race_name: str
    distance: int
    grade: str
    track_condition: str
    weather: str
    horses: list[HorseInfo]
    status: RaceStatus
    created_at: datetime | None = None
    updated_at: datetime | None = None
    raw_data: dict[str, Any] | None = None
    enriched_data: dict[str, Any] | None = None


class RaceResult(BaseModel):
    race_id: str
    date: str
    meet: int
    race_no: int
    winner: int  # 1위 말번호
    second: int  # 2위 말번호
    third: int  # 3위 말번호

    @property
    def result_list(self) -> list[int]:
        return [self.winner, self.second, self.third]


class RaceStatusResponse(BaseModel):
    race_id: str
    status: RaceStatus
    collected_at: datetime | None = None
    enriched_at: datetime | None = None
    error_message: str | None = None
    horse_count: int = 0
    enriched_count: int = 0
