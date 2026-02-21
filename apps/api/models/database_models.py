"""
SQLAlchemy 데이터베이스 모델
경주, 작업, 예측 등의 영구 저장용 모델
"""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TypeDecorator,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from infrastructure.database import Base


class PostgresEnum(TypeDecorator):
    """Custom enum type that handles case conversion between Python and Postgres"""

    impl = SQLEnum
    cache_ok = True

    def __init__(self, enum_class, name=None, **kw):
        self.enum_class = enum_class
        # Force lowercase values for PostgreSQL
        values = [
            e.value.lower() if hasattr(e.value, "lower") else e.value
            for e in enum_class
        ]
        super().__init__(name=name or enum_class.__name__.lower(), **kw)
        self.impl = SQLEnum(
            *values, name=name or enum_class.__name__.lower(), create_type=False
        )

    def process_bind_param(self, value, dialect):
        """Convert Python enum to database value (lowercase)"""
        if value is None:
            return None
        if isinstance(value, self.enum_class):
            return value.value.lower()
        if isinstance(value, str):
            # Try to get enum by value
            for item in self.enum_class:
                if item.value == value:
                    return value.lower()
            # Try to get enum by name
            try:
                return self.enum_class[value.upper()].value.lower()
            except KeyError:
                return value.lower()
        return value

    def process_result_value(self, value, dialect):
        """Convert database value (lowercase) to Python enum"""
        if value is None:
            return None
        # Find matching enum
        for item in self.enum_class:
            if item.value.lower() == value.lower():
                return item
        return value


class JobStatus(str, enum.Enum):
    """작업 상태"""

    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class JobType(str, enum.Enum):
    """작업 유형"""

    COLLECTION = "collection"
    ENRICHMENT = "enrichment"
    ANALYSIS = "analysis"
    PREDICTION = "prediction"
    IMPROVEMENT = "improvement"
    BATCH = "batch"


class DataStatus(str, enum.Enum):
    """데이터 상태"""

    PENDING = "pending"
    COLLECTED = "collected"
    ENRICHED = "enriched"
    FAILED = "failed"

    @classmethod
    def _missing_(cls, value):
        """Handle case-insensitive enum lookup"""
        if isinstance(value, str):
            # Try lowercase
            for item in cls:
                if item.value == value.lower():
                    return item
            # Try uppercase
            for item in cls:
                if item.name == value.upper():
                    return item
        return None


class Race(Base):
    """경주 데이터 모델 - 정규화된 버전"""

    __tablename__ = "races"

    # 기본 키
    race_id: Mapped[str] = mapped_column(
        String(50), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # 핵심 경주 정보 (정규화됨)
    date: Mapped[str] = mapped_column(String(8), index=True)  # YYYYMMDD 형식
    meet: Mapped[int] = mapped_column(Integer, index=True)  # 경마장 코드
    race_number: Mapped[int] = mapped_column(Integer)  # 경주 번호

    # 경주 세부 정보
    race_name: Mapped[str | None] = mapped_column(String(200), default=None)
    distance: Mapped[int | None] = mapped_column(Integer, default=None)
    track: Mapped[str | None] = mapped_column(String(50), default=None)
    weather: Mapped[str | None] = mapped_column(String(50), default=None)

    # 통합된 상태 정보
    collection_status: Mapped[str | None] = mapped_column(
        PostgresEnum(DataStatus, name="data_status"), default=DataStatus.PENDING
    )
    enrichment_status: Mapped[str | None] = mapped_column(
        PostgresEnum(DataStatus, name="data_status"), default=DataStatus.PENDING
    )
    result_status: Mapped[str | None] = mapped_column(
        PostgresEnum(DataStatus, name="data_status"), default=DataStatus.PENDING
    )

    # 데이터
    basic_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    enriched_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    result_data: Mapped[Any | None] = mapped_column(JSON, default=None)

    # 타임스탬프
    collected_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    result_collected_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # 메타데이터
    data_quality_score: Mapped[float | None] = mapped_column(Float, default=0.0)
    warnings: Mapped[list[Any] | None] = mapped_column(JSON, default=list)
    horse_count: Mapped[int | None] = mapped_column(Integer, default=0)

    # 관계
    predictions: Mapped[list["Prediction"]] = relationship(
        back_populates="race", cascade="all, delete-orphan"
    )

    # 인덱스
    __table_args__ = (
        Index("idx_race_date_meet", "date", "meet"),
        Index("idx_race_status", "collection_status", "enrichment_status"),
    )

    # 호환성을 위한 프로퍼티들 (기존 코드 지원)
    @property
    def id(self) -> str:
        """convenience alias for tests"""
        return self.race_id

    @property
    def race_date(self) -> str:
        """Legacy compatibility: race_date -> date"""
        return self.date

    @race_date.setter
    def race_date(self, value: str) -> None:
        """Legacy compatibility: allow setting via race_date"""
        self.date = value

    @property
    def race_no(self) -> int:
        """Legacy compatibility: race_no -> race_number"""
        return self.race_number

    @race_no.setter
    def race_no(self, value: int) -> None:
        """Legacy compatibility: allow setting via race_no"""
        self.race_number = value

    @property
    def status(self) -> str | None:
        """Legacy compatibility: general status -> collection_status"""
        return self.collection_status

    @status.setter
    def status(self, value: str | None) -> None:
        """Legacy compatibility: allow setting general status"""
        self.collection_status = value


class Job(Base):
    """작업 관리 모델"""

    __tablename__ = "jobs"

    # 기본 키
    job_id: Mapped[str] = mapped_column(
        String(100), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # 작업 정보
    type: Mapped[str] = mapped_column(
        PostgresEnum(JobType, name="job_type"), index=True
    )
    status: Mapped[str | None] = mapped_column(
        PostgresEnum(JobStatus, name="job_status"),
        default=JobStatus.QUEUED,
        index=True,
    )

    # 시간 정보
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.now(), index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    # 진행 상황
    progress: Mapped[int | None] = mapped_column(Integer, default=0)
    current_step: Mapped[str | None] = mapped_column(String(200), default=None)
    total_steps: Mapped[int | None] = mapped_column(Integer, default=None)

    # 결과 및 에러
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    retry_count: Mapped[int | None] = mapped_column(Integer, default=0)

    # 메타데이터
    parameters: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)
    created_by: Mapped[str | None] = mapped_column(String(100), default=None)
    tags: Mapped[list[Any] | None] = mapped_column(JSON, default=list)

    # 태스크 ID (background task tracking)
    task_id: Mapped[str | None] = mapped_column(String(200), default=None)

    # 관계
    job_logs: Mapped[list["JobLog"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )

    # 인덱스
    __table_args__ = (
        Index("idx_job_created_status", "created_at", "status"),
        Index("idx_job_type_status", "type", "status"),
    )


class JobLog(Base):
    """작업 로그 모델"""

    __tablename__ = "job_logs"

    # 기본 키
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 작업 참조
    job_id: Mapped[str] = mapped_column(
        String(100), ForeignKey("jobs.job_id"), index=True
    )

    # 로그 정보
    timestamp: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.now()
    )
    level: Mapped[str | None] = mapped_column(String(20), default=None)
    message: Mapped[str | None] = mapped_column(Text, default=None)
    log_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=None)

    # 관계
    job: Mapped["Job"] = relationship(back_populates="job_logs")


class Prediction(Base):
    """예측 결과 모델"""

    __tablename__ = "predictions"

    # 기본 키
    prediction_id: Mapped[str] = mapped_column(String(100), primary_key=True)

    # 경주 참조
    race_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("races.race_id"), index=True
    )

    # 예측 정보
    prompt_id: Mapped[str] = mapped_column(String(50), index=True)
    prompt_version: Mapped[str | None] = mapped_column(String(20), default=None)

    # 예측 결과
    predicted_positions: Mapped[list[Any] | None] = mapped_column(JSON, default=None)
    confidence: Mapped[int | None] = mapped_column(Integer, default=None)
    reasoning: Mapped[str | None] = mapped_column(Text, default=None)

    # 평가
    actual_result: Mapped[list[Any] | None] = mapped_column(JSON, default=None)
    accuracy_score: Mapped[float | None] = mapped_column(Float, default=None)
    correct_count: Mapped[int | None] = mapped_column(Integer, default=None)

    # 메타데이터
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.now()
    )
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, default=None)
    model_version: Mapped[str | None] = mapped_column(String(50), default=None)

    # 관계
    race: Mapped["Race"] = relationship(back_populates="predictions")

    # 인덱스
    __table_args__ = (
        Index("idx_prediction_prompt", "prompt_id", "created_at"),
        Index("idx_prediction_accuracy", "accuracy_score", "created_at"),
    )


class APIKey(Base):
    """API 키 관리 모델"""

    __tablename__ = "api_keys"

    # 기본 키
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 키 정보
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, default=None)

    # 상태
    is_active: Mapped[bool | None] = mapped_column(default=True)

    # 사용량 제한
    rate_limit: Mapped[int | None] = mapped_column(Integer, default=100)
    daily_limit: Mapped[int | None] = mapped_column(Integer, default=10000)

    # 권한
    permissions: Mapped[list[Any] | None] = mapped_column(JSON, default=list)

    # 타임스탬프
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.now()
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)

    # 사용량 추적
    total_requests: Mapped[int | None] = mapped_column(Integer, default=0)
    today_requests: Mapped[int | None] = mapped_column(Integer, default=0)

    # 메타데이터
    created_by: Mapped[str | None] = mapped_column(
        String(100), index=True, default=None
    )
    key_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)


class PromptTemplate(Base):
    """프롬프트 템플릿 관리 모델"""

    __tablename__ = "prompt_templates"

    # 기본 키
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 프롬프트 정보
    prompt_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    version: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text, default=None)

    # 내용
    template_content: Mapped[str] = mapped_column(Text)

    # 성능 지표
    total_uses: Mapped[int | None] = mapped_column(Integer, default=0)
    success_rate: Mapped[float | None] = mapped_column(Float, default=0.0)
    avg_accuracy: Mapped[float | None] = mapped_column(Float, default=0.0)

    # 상태
    is_active: Mapped[bool | None] = mapped_column(default=True)
    is_baseline: Mapped[bool | None] = mapped_column(default=False)

    # 타임스탬프
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # 메타데이터
    tags: Mapped[list[Any] | None] = mapped_column(JSON, default=list)
    template_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict)
