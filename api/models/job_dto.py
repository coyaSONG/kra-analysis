"""
작업 관리 관련 데이터 모델
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class JobType(str, Enum):
    """작업 유형"""
    COLLECTION = "collection"
    ENRICHMENT = "enrichment"
    ANALYSIS = "analysis"
    PREDICTION = "prediction"
    IMPROVEMENT = "improvement"
    BATCH = "batch"


class JobStatus(str, Enum):
    """작업 상태"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class Job(BaseModel):
    """작업 기본 모델"""
    job_id: str = Field(..., description="작업 고유 ID")
    type: JobType = Field(..., description="작업 유형")
    status: JobStatus = Field(..., description="현재 상태")
    
    # 시간 정보
    created_at: datetime = Field(..., description="생성 시간")
    started_at: Optional[datetime] = Field(None, description="시작 시간")
    completed_at: Optional[datetime] = Field(None, description="완료 시간")
    
    # 진행 상황
    progress: int = Field(0, ge=0, le=100, description="진행률 (%)")
    current_step: Optional[str] = Field(None, description="현재 단계")
    total_steps: Optional[int] = Field(None, description="전체 단계 수")
    
    # 결과 및 에러
    result: Optional[Dict[str, Any]] = Field(None, description="작업 결과")
    error_message: Optional[str] = Field(None, description="에러 메시지")
    retry_count: int = Field(0, description="재시도 횟수")
    
    # 메타데이터
    parameters: Optional[Dict[str, Any]] = Field(None, description="작업 파라미터")
    created_by: Optional[str] = Field(None, description="생성자")
    tags: List[str] = Field(default_factory=list, description="태그")
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "col_20250622_1_abc123",
                "type": "collection",
                "status": "processing",
                "created_at": "2025-06-22T10:00:00Z",
                "started_at": "2025-06-22T10:00:05Z",
                "progress": 65,
                "current_step": "Enriching race 7 of 11",
                "parameters": {
                    "date": "20250622",
                    "meet": 1
                }
            }
        }


class JobDetailResponse(BaseModel):
    """작업 상세 응답"""
    job_id: str
    type: str
    status: JobStatus
    created_at: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    progress: int
    current_step: Optional[str]
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    logs: Optional[List[Dict[str, Any]]] = None
    
    # 추가 정보
    estimated_completion: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    resource_usage: Optional[Dict[str, Any]] = None


class JobListResponse(BaseModel):
    """작업 목록 응답"""
    jobs: List[Dict[str, Any]]
    pagination: Dict[str, Any]
    
    class Config:
        json_schema_extra = {
            "example": {
                "jobs": [
                    {
                        "job_id": "col_20250622_1_abc123",
                        "type": "collection",
                        "status": "processing",
                        "progress": 65,
                        "created_at": "2025-06-22T10:00:00Z"
                    }
                ],
                "pagination": {
                    "page": 1,
                    "limit": 20,
                    "total": 45,
                    "pages": 3
                }
            }
        }


class JobLog(BaseModel):
    """작업 로그 항목"""
    timestamp: datetime
    level: str  # INFO, WARNING, ERROR
    message: str
    metadata: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2025-06-22T10:00:05Z",
                "level": "INFO",
                "message": "Started collecting race 1",
                "metadata": {
                    "race_no": 1,
                    "horses": 12
                }
            }
        }