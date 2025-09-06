"""
SQLAlchemy 데이터베이스 모델
경주, 작업, 예측 등의 영구 저장용 모델
"""

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, 
    JSON, ForeignKey, Index, Text, Enum as SQLEnum, TypeDecorator
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid
import enum

from infrastructure.database import Base


class PostgresEnum(TypeDecorator):
    """Custom enum type that handles case conversion between Python and Postgres"""
    impl = SQLEnum
    cache_ok = True

    def __init__(self, enum_class, name=None, **kw):
        self.enum_class = enum_class
        # Force lowercase values for PostgreSQL
        values = [e.value.lower() if hasattr(e.value, 'lower') else e.value for e in enum_class]
        super().__init__(name=name or enum_class.__name__.lower(), **kw)
        self.impl = SQLEnum(*values, name=name or enum_class.__name__.lower(), create_type=False)

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
    """경주 데이터 모델"""
    __tablename__ = "races"
    
    # 기본 키
    race_id = Column(String(50), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # 경주 정보
    date = Column(String(8), nullable=True, index=True)  # Single column index for date queries
    # compatibility columns for tests
    race_date = Column(String(8), nullable=False, index=True)
    meet = Column(Integer, nullable=False, index=True)
    race_number = Column(Integer, nullable=True)
    race_no = Column(Integer, nullable=False)
    race_name = Column(String(200))
    distance = Column(Integer)
    track = Column(String(50))
    weather = Column(String(50))
    
    # 상태 정보
    collection_status = Column(PostgresEnum(DataStatus, name="data_status"), default=DataStatus.PENDING)
    status = Column(PostgresEnum(DataStatus, name="data_status"), default=DataStatus.PENDING)
    enrichment_status = Column(PostgresEnum(DataStatus, name="data_status"), default=DataStatus.PENDING)
    result_status = Column(PostgresEnum(DataStatus, name="data_status"), default=DataStatus.PENDING)
    
    # 데이터
    basic_data = Column(JSON)
    raw_data = Column(JSON)
    enriched_data = Column(JSON)
    result_data = Column(JSON)
    
    # 타임스탬프
    collected_at = Column(DateTime, nullable=True)
    enriched_at = Column(DateTime, nullable=True)
    result_collected_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 메타데이터
    data_quality_score = Column(Float, default=0.0)
    warnings = Column(JSON, default=list)
    horse_count = Column(Integer, default=0)
    
    # 관계
    predictions = relationship("Prediction", back_populates="race", cascade="all, delete-orphan")
    
    # 인덱스
    __table_args__ = (
        Index("idx_race_date_meet", "date", "meet"),
        Index("idx_race_status", "collection_status", "enrichment_status"),
    )

    # convenience alias for tests
    @property
    def id(self) -> str:
        return self.race_id


class Job(Base):
    """작업 관리 모델"""
    __tablename__ = "jobs"
    
    # 기본 키
    job_id = Column(String(100), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # 작업 정보
    type = Column(PostgresEnum(JobType, name="job_type"), nullable=False, index=True)
    status = Column(PostgresEnum(JobStatus, name="job_status"), default=JobStatus.QUEUED, index=True)
    
    # 시간 정보
    created_at = Column(DateTime, server_default=func.now(), index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # 진행 상황
    progress = Column(Integer, default=0)
    current_step = Column(String(200))
    total_steps = Column(Integer)
    
    # 결과 및 에러
    result = Column(JSON)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # 메타데이터
    parameters = Column(JSON)
    created_by = Column(String(100))
    tags = Column(JSON, default=list)
    
    # 관계
    job_logs = relationship("JobLog", back_populates="job", cascade="all, delete-orphan")
    
    # 인덱스
    __table_args__ = (
        Index("idx_job_created_status", "created_at", "status"),
        Index("idx_job_type_status", "type", "status"),
    )


class JobLog(Base):
    """작업 로그 모델"""
    __tablename__ = "job_logs"
    
    # 기본 키
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 작업 참조
    job_id = Column(String(100), ForeignKey("jobs.job_id"), nullable=False, index=True)
    
    # 로그 정보
    timestamp = Column(DateTime, server_default=func.now())
    level = Column(String(20))  # INFO, WARNING, ERROR
    message = Column(Text)
    log_metadata = Column(JSON)
    
    # 관계
    job = relationship("Job", back_populates="job_logs")


class Prediction(Base):
    """예측 결과 모델"""
    __tablename__ = "predictions"
    
    # 기본 키
    prediction_id = Column(String(100), primary_key=True)
    
    # 경주 참조
    race_id = Column(String(50), ForeignKey("races.race_id"), nullable=False, index=True)
    
    # 예측 정보
    prompt_id = Column(String(50), nullable=False, index=True)
    prompt_version = Column(String(20))
    
    # 예측 결과
    predicted_positions = Column(JSON)  # [1st, 2nd, 3rd]
    confidence = Column(Integer)
    reasoning = Column(Text)
    
    # 평가
    actual_result = Column(JSON)  # 실제 1, 2, 3위
    accuracy_score = Column(Float)
    correct_count = Column(Integer)  # 맞춘 개수
    
    # 메타데이터
    created_at = Column(DateTime, server_default=func.now())
    execution_time_ms = Column(Integer)
    model_version = Column(String(50))
    
    # 관계
    race = relationship("Race", back_populates="predictions")
    
    # 인덱스
    __table_args__ = (
        Index("idx_prediction_prompt", "prompt_id", "created_at"),
        Index("idx_prediction_accuracy", "accuracy_score", "created_at"),
    )


class APIKey(Base):
    """API 키 관리 모델"""
    __tablename__ = "api_keys"
    
    # 기본 키
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 키 정보
    key = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    
    # 상태
    is_active = Column(Boolean, default=True)
    
    # 사용량 제한
    rate_limit = Column(Integer, default=100)  # requests per minute
    daily_limit = Column(Integer, default=10000)
    
    # 권한
    permissions = Column(JSON, default=list)  # ["read", "write", "admin"]
    
    # 타임스탬프
    created_at = Column(DateTime, server_default=func.now())
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # 사용량 추적
    total_requests = Column(Integer, default=0)
    today_requests = Column(Integer, default=0)
    
    # 메타데이터
    created_by = Column(String(100), index=True)  # Index for filtering by creator
    key_metadata = Column(JSON, default=dict)


class PromptTemplate(Base):
    """프롬프트 템플릿 관리 모델"""
    __tablename__ = "prompt_templates"
    
    # 기본 키
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # 프롬프트 정보
    prompt_id = Column(String(50), unique=True, nullable=False, index=True)
    version = Column(String(20), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    # 내용
    template_content = Column(Text, nullable=False)
    
    # 성능 지표
    total_uses = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    avg_accuracy = Column(Float, default=0.0)
    
    # 상태
    is_active = Column(Boolean, default=True)
    is_baseline = Column(Boolean, default=False)  # 기준 프롬프트 여부
    
    # 타임스탬프
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # 메타데이터
    tags = Column(JSON, default=list)
    template_metadata = Column(JSON, default=dict)
