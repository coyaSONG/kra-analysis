"""
데이터 수집 관련 데이터 모델
"""

from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum
import re


class CollectionOptions(BaseModel):
    """수집 옵션"""
    enrich: bool = Field(True, description="자동으로 상세 정보 보강")
    get_results: bool = Field(False, description="경주 결과도 수집")
    force_refresh: bool = Field(False, description="캐시 무시하고 새로 수집")
    parallel_count: int = Field(3, ge=1, le=10, description="병렬 처리 수")


class CollectionRequest(BaseModel):
    """데이터 수집 요청"""
    date: str = Field(..., description="날짜 (YYYYMMDD)")
    
    @validator("date")
    def validate_date(cls, v):
        if not re.match(r"^\d{8}$", v):
            raise ValueError("validation error: 날짜는 YYYYMMDD 형식이어야 합니다")
        try:
            # 유효한 날짜인지 확인
            year = int(v[:4])
            month = int(v[4:6])
            day = int(v[6:8])
            date(year, month, day)
            # 미래 날짜는 허용하지 않음
            if date(year, month, day) > date.today():
                raise ValueError("validation error: 미래 날짜는 허용되지 않습니다")
        except ValueError as e:
            raise ValueError(f"validation error: 유효하지 않은 날짜: {e}")
        return v
    meet: int = Field(..., ge=1, le=3, description="경마장 (1: 서울, 2: 제주, 3: 부산경남)")
    race_numbers: Optional[List[int]] = Field(
        None,
        description="수집할 경주 번호 리스트. 생략시 1-15R 전체"
    )
    options: Optional[CollectionOptions] = Field(
        None,
        description="추가 옵션"
    )
    
    @validator("race_numbers")
    def validate_race_numbers(cls, v):
        if v:
            for num in v:
                if num < 1 or num > 20:
                    raise ValueError(f"경주 번호는 1-20 사이여야 합니다: {num}")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "date": "20250622",
                "meet": 1,
                "race_numbers": [1, 2, 3],
                "options": {
                    "enrich": True,
                    "get_results": False
                }
            }
        }


class CollectionResponse(BaseModel):
    """수집 작업 응답"""
    job_id: Optional[str] = Field(None, description="작업 ID")
    status: str = Field(..., description="작업 상태")
    message: str = Field(..., description="응답 메시지")
    estimated_time: Optional[int] = Field(None, description="예상 소요 시간(초)")
    webhook_url: Optional[str] = Field(None, description="상태 확인 URL")
    data: Optional[List[Dict[str, Any]]] = Field(None, description="수집된 데이터")


class EnrichmentRequest(BaseModel):
    """데이터 보강 요청"""
    race_ids: List[str] = Field(
        ...,
        min_items=1,
        description="보강할 경주 ID 리스트"
    )
    enrich_types: List[str] = Field(
        ["horse", "jockey", "trainer"],
        description="보강 유형"
    )
    
    @validator("enrich_types")
    def validate_enrich_types(cls, v):
        valid_types = {"horse", "jockey", "trainer"}
        for t in v:
            if t not in valid_types:
                raise ValueError(f"유효하지 않은 보강 유형: {t}")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "race_ids": ["race_1_20250622_1", "race_1_20250622_2"],
                "enrich_types": ["horse", "jockey", "trainer"]
            }
        }


class EnrichmentResponse(BaseModel):
    """보강 작업 응답"""
    job_id: str
    status: str
    races_queued: int
    message: str


class ResultCollectionRequest(BaseModel):
    """경주 결과 수집 요청"""
    date: str = Field(..., description="날짜")
    
    @validator("date")
    def validate_date(cls, v):
        if not re.match(r"^\d{8}$", v):
            raise ValueError("validation error: 날짜는 YYYYMMDD 형식이어야 합니다")
        try:
            year = int(v[:4])
            month = int(v[4:6])
            day = int(v[6:8])
            date(year, month, day)
            if date(year, month, day) > date.today():
                raise ValueError("validation error: 미래 날짜는 허용되지 않습니다")
        except ValueError as e:
            raise ValueError(f"validation error: 유효하지 않은 날짜: {e}")
        return v
    meet: int = Field(..., ge=1, le=3, description="경마장")
    race_number: int = Field(..., ge=1, le=20, description="경주 번호")
    async_mode: bool = Field(False, description="비동기 실행 여부")
    
    class Config:
        json_schema_extra = {
            "example": {
                "date": "20250622",
                "meet": 1,
                "race_number": 1,
                "async_mode": False
            }
        }


class DataStatus(str, Enum):
    """데이터 상태"""
    PENDING = "pending"
    COLLECTED = "collected"
    ENRICHED = "enriched"
    FAILED = "failed"


class CollectionStatus(BaseModel):
    """수집 상태"""
    date: str = Field(..., description="날짜")
    meet: int = Field(..., description="경마장")
    total_races: int = Field(..., description="전체 경주 수")
    collected_races: int = Field(..., description="수집된 경주 수")
    enriched_races: int = Field(..., description="보강된 경주 수")
    status: str = Field(..., description="전체 상태")
    collection_status: Optional[DataStatus] = Field(None, description="수집 상태")
    enrichment_status: Optional[DataStatus] = Field(None, description="보강 상태")
    result_status: Optional[DataStatus] = Field(None, description="결과 상태")
    last_updated: Optional[datetime] = Field(None, description="마지막 업데이트")


class HorseData(BaseModel):
    """말 데이터"""
    chulNo: int = Field(..., description="출전 번호")
    hrNo: str = Field(..., description="말 번호")
    hrName: str = Field(..., description="말 이름")
    age: int = Field(..., description="나이")
    sex: str = Field(..., description="성별")
    wgBudam: int = Field(..., description="부담중량")
    jkNo: str = Field(..., description="기수 번호")
    jkName: str = Field(..., description="기수 이름")
    trNo: str = Field(..., description="조교사 번호")
    trName: str = Field(..., description="조교사 이름")
    winOdds: float = Field(..., ge=0, description="단승 배당률")
    plcOdds: float = Field(..., ge=0, description="복승 배당률")
    rating: Optional[int] = Field(None, description="레이팅")
    
    # 보강 데이터
    hrDetail: Optional[Dict[str, Any]] = Field(None, description="말 상세 정보")
    jkDetail: Optional[Dict[str, Any]] = Field(None, description="기수 상세 정보")
    trDetail: Optional[Dict[str, Any]] = Field(None, description="조교사 상세 정보")
    
    class Config:
        json_schema_extra = {
            "example": {
                "chulNo": 1,
                "hrNo": "041234",
                "hrName": "천년의질주",
                "age": 4,
                "sex": "암",
                "wgBudam": 54,
                "jkNo": "090123",
                "jkName": "문세영",
                "trNo": "070123",
                "trName": "김영관",
                "winOdds": 5.2,
                "plcOdds": 2.1
            }
        }


class RaceInfo(BaseModel):
    """경주 정보"""
    rcDate: str = Field(..., description="경주 날짜")
    rcNo: int = Field(..., description="경주 번호")
    rcName: str = Field(..., description="경주명")
    rcDist: int = Field(..., ge=800, le=3200, description="거리(m)")
    track: Optional[str] = Field(None, description="주로")
    weather: Optional[str] = Field(None, description="날씨")
    meet: int = Field(..., description="경마장")


class RaceData(BaseModel):
    """경주 데이터"""
    race_id: str = Field(..., description="경주 ID")
    race_info: RaceInfo = Field(..., description="경주 정보")
    horses: List[HorseData] = Field(..., description="출전마 목록")
    
    # 상태 정보
    collection_status: DataStatus = Field(..., description="수집 상태")
    enrichment_status: Optional[DataStatus] = Field(None, description="보강 상태")
    result_status: Optional[DataStatus] = Field(None, description="결과 수집 상태")
    
    # 결과 데이터
    result: Optional[Dict[str, Any]] = Field(None, description="경주 결과")
    
    # 타임스탬프
    collected_at: datetime = Field(..., description="수집 시간")
    enriched_at: Optional[datetime] = Field(None, description="보강 시간")
    result_collected_at: Optional[datetime] = Field(None, description="결과 수집 시간")
    
    # 메타데이터
    data_quality_score: Optional[float] = Field(None, ge=0, le=1, description="데이터 품질 점수")
    warnings: List[str] = Field(default_factory=list, description="경고 메시지")
