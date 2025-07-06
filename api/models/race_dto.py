from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class RaceStatus(str, Enum):
    PENDING = "pending"
    COLLECTED = "collected"
    ENRICHED = "enriched"
    FAILED = "failed"


class CollectRaceRequest(BaseModel):
    date: str = Field(..., description="날짜 (YYYYMMDD)")
    meet: int = Field(..., ge=1, le=3, description="경마장 (1:서울, 2:제주, 3:부산경남)")
    race_no: Optional[int] = Field(None, ge=1, le=20, description="경주 번호")


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
                "win_odds": 5.2
            }
        }


class RaceData(BaseModel):
    id: Optional[str] = None
    date: str
    meet: int
    race_no: int
    race_name: str
    distance: int
    grade: str
    track_condition: str
    weather: str
    horses: List[HorseInfo]
    status: RaceStatus
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    raw_data: Optional[Dict[str, Any]] = None
    enriched_data: Optional[Dict[str, Any]] = None


class RaceResult(BaseModel):
    race_id: str
    date: str
    meet: int
    race_no: int
    winner: int  # 1위 말번호
    second: int  # 2위 말번호
    third: int   # 3위 말번호
    
    @property
    def result_list(self) -> List[int]:
        return [self.winner, self.second, self.third]


class RaceStatusResponse(BaseModel):
    race_id: str
    status: RaceStatus
    collected_at: Optional[datetime] = None
    enriched_at: Optional[datetime] = None
    error_message: Optional[str] = None
    horse_count: int = 0
    enriched_count: int = 0