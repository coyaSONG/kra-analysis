"""
Fixed database connection for pgbouncer compatibility
pgbouncer 호환성을 위한 수정된 데이터베이스 연결
"""

from contextlib import asynccontextmanager

import asyncpg
import structlog
from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from config import settings

logger = structlog.get_logger()

# 데이터베이스 메타데이터 설정
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)

# Base 클래스 생성
Base = declarative_base(metadata=metadata)


# Custom connection creator for pgbouncer
async def create_pgbouncer_connection():
    """Create connection with pgbouncer-specific settings"""
    # Parse the database URL to get connection parameters
    db_url = settings.database_url
    # Remove the sqlalchemy prefix
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    # Remove query parameters
    base_url = db_url.split("?")[0]

    # Create connection with statement_cache_size=0
    conn = await asyncpg.connect(
        base_url,
        statement_cache_size=0,  # Disable prepared statements
        server_settings={"jit": "off"},
    )
    return conn


# Create async engine
database_url = settings.database_url

if "sqlite" in database_url:
    engine = create_async_engine(database_url, echo=settings.debug)
else:
    # For Supabase/pgbouncer, use NullPool to avoid connection pooling issues
    if "pooler.supabase.com" in database_url:
        from sqlalchemy.pool import NullPool

        # Create custom connection function that disables prepared statements
        async def get_async_connection():
            return await asyncpg.connect(
                database_url.replace("postgresql+asyncpg://", "postgresql://"),
                statement_cache_size=0,
                server_settings={"jit": "off"},
            )

        engine = create_async_engine(
            database_url,
            echo=settings.debug,
            poolclass=NullPool,
            async_creator=get_async_connection,
        )
    else:
        # Regular PostgreSQL connection
        engine = create_async_engine(
            database_url,
            echo=settings.debug,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,
            pool_recycle=3600,
        )

# 비동기 세션 팩토리
async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


async def init_db():
    """데이터베이스 초기화"""
    try:
        # 테이블 생성
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        logger.warning("API will run without database connection")


async def close_db():
    """데이터베이스 연결 종료"""
    await engine.dispose()
    logger.info("Database connections closed")


@asynccontextmanager
async def get_db_session():
    """데이터베이스 세션 컨텍스트 매니저"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db():
    """FastAPI 의존성 주입용 세션 생성기"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


# 헬스체크용 함수
async def check_database_connection(session: AsyncSession | None = None):
    """데이터베이스 연결 상태 확인"""
    try:
        if session is not None:
            await session.execute(text("SELECT 1"))
        else:
            async with async_session_maker() as session_obj:
                await session_obj.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
