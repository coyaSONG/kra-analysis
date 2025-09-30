#!/usr/bin/env python3
"""
Supabase 데이터베이스 연결 테스트 스크립트

사용법:
    python3 scripts/test_db_connection.py
"""

import asyncio
import sys
from pathlib import Path

import asyncpg
import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings

logger = structlog.get_logger()


async def test_asyncpg_connection():
    """asyncpg로 직접 연결 테스트"""
    print("\n" + "=" * 80)
    print("1. asyncpg 직접 연결 테스트")
    print("=" * 80)

    try:
        # DATABASE_URL에서 postgresql+asyncpg:// 제거
        db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")

        # 쿼리 파라미터 제거 (asyncpg connect 함수에서는 별도 처리)
        base_url = db_url.split("?")[0]

        print(f"연결 시도: {base_url[:50]}...")

        # pgbouncer 호환 설정으로 연결
        conn = await asyncpg.connect(
            base_url,
            statement_cache_size=0,  # pgbouncer 필수
            server_settings={"jit": "off"},
            timeout=10,
        )

        print("✅ 연결 성공!")

        # 간단한 쿼리 테스트
        version = await conn.fetchval("SELECT version()")
        print(f"   PostgreSQL 버전: {version[:80]}...")

        # 현재 데이터베이스 확인
        current_db = await conn.fetchval("SELECT current_database()")
        print(f"   현재 데이터베이스: {current_db}")

        # 현재 사용자 확인
        current_user = await conn.fetchval("SELECT current_user")
        print(f"   현재 사용자: {current_user}")

        await conn.close()
        return True

    except asyncpg.exceptions.InvalidPasswordError as e:
        print(f"❌ 비밀번호 오류: {e}")
        print("\n해결 방법:")
        print("1. Supabase Dashboard > Settings > Database")
        print("2. 'Reset database password' 클릭")
        print("3. 새 비밀번호를 .env 파일의 DATABASE_URL에 입력")
        return False

    except asyncpg.exceptions.InvalidAuthorizationSpecificationError as e:
        print(f"❌ 인증 오류: {e}")
        print("\n확인 사항:")
        print("1. 사용자 이름이 postgres.{project_id} 형식인지 확인")
        print("2. Supabase Dashboard에서 정확한 connection string 복사")
        return False

    except asyncio.TimeoutError:
        print("❌ 연결 시간 초과 (10초)")
        print("\n확인 사항:")
        print("1. 네트워크 연결 확인")
        print("2. Supabase 프로젝트가 활성 상태인지 확인")
        print("3. 방화벽 설정 확인")
        return False

    except Exception as e:
        print(f"❌ 연결 실패: {type(e).__name__}: {e}")
        return False


async def test_sqlalchemy_connection():
    """SQLAlchemy 엔진으로 연결 테스트"""
    print("\n" + "=" * 80)
    print("2. SQLAlchemy 엔진 연결 테스트")
    print("=" * 80)

    try:
        # infrastructure/database.py와 동일한 설정
        db_url = settings.database_url

        if "pooler.supabase.com" in db_url:
            base_url = db_url.split("?")[0]
            from sqlalchemy.pool import NullPool

            engine = create_async_engine(
                base_url,
                echo=False,
                poolclass=NullPool,
                connect_args={
                    "statement_cache_size": 0,
                    "server_settings": {"jit": "off"},
                    "command_timeout": 10,
                },
            )
        else:
            engine = create_async_engine(db_url, echo=False)

        print(f"엔진 생성 완료: {engine.url.host}")

        # 연결 테스트
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            print(f"✅ 연결 성공! 테스트 쿼리 결과: {row[0]}")

        await engine.dispose()
        return True

    except Exception as e:
        print(f"❌ 연결 실패: {type(e).__name__}: {e}")
        return False


async def test_table_existence():
    """테이블 존재 여부 확인"""
    print("\n" + "=" * 80)
    print("3. 데이터베이스 테이블 확인")
    print("=" * 80)

    try:
        db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        base_url = db_url.split("?")[0]

        conn = await asyncpg.connect(
            base_url, statement_cache_size=0, server_settings={"jit": "off"}, timeout=10
        )

        # public 스키마의 테이블 목록 조회
        tables = await conn.fetch(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """
        )

        if tables:
            print(f"✅ {len(tables)}개 테이블 발견:")
            for table in tables:
                print(f"   - {table['table_name']}")
        else:
            print("⚠️  테이블이 없습니다. 마이그레이션을 실행해야 합니다.")
            print("\n마이그레이션 실행:")
            print("   python3 scripts/apply_migrations.py")

        await conn.close()
        return len(tables) > 0

    except Exception as e:
        print(f"❌ 테이블 조회 실패: {e}")
        return False


async def test_supabase_client():
    """Supabase Python Client 테스트"""
    print("\n" + "=" * 80)
    print("4. Supabase Python Client 테스트")
    print("=" * 80)

    try:
        from infrastructure.supabase_client import get_supabase_client

        client = get_supabase_client()

        if client is None:
            print("⚠️  Supabase Client가 초기화되지 않았습니다.")
            print("\n원인:")
            print("1. SUPABASE_URL 또는 SUPABASE_ANON_KEY가 설정되지 않음")
            print("2. .env 파일 확인 필요")
            return False

        print("✅ Supabase Client 초기화 성공!")
        print(f"   URL: {settings.supabase_url}")
        return True

    except Exception as e:
        print(f"❌ Supabase Client 초기화 실패: {e}")
        return False


def print_config_summary():
    """현재 설정 요약 출력"""
    print("\n" + "=" * 80)
    print("현재 설정 요약")
    print("=" * 80)

    print(f"환경: {settings.environment}")
    print(f"데이터베이스 URL: {settings.database_url[:60]}...")
    print(f"Supabase URL: {settings.supabase_url}")
    print(
        f"Supabase Key: {'설정됨' if settings.supabase_key != 'your_supabase_anon_key' else '미설정'}"
    )
    print(f"KRA API Key: {'설정됨' if settings.kra_api_key else '미설정'}")


async def main():
    """메인 함수"""
    print("=" * 80)
    print("Supabase 데이터베이스 연결 테스트")
    print("=" * 80)

    print_config_summary()

    # 설정 확인
    if settings.database_url.startswith("postgresql+asyncpg://kra_user:kra_password"):
        print("\n⚠️  경고: 기본 DATABASE_URL 사용 중!")
        print("   .env 파일을 생성하고 실제 Supabase URL로 설정하세요.")
        print("   cp .env.template .env")
        return

    results = {}

    # 테스트 실행
    results["asyncpg"] = await test_asyncpg_connection()
    results["sqlalchemy"] = await test_sqlalchemy_connection()
    results["tables"] = await test_table_existence()
    results["supabase_client"] = await test_supabase_client()

    # 최종 결과
    print("\n" + "=" * 80)
    print("테스트 결과 요약")
    print("=" * 80)

    all_passed = all(results.values())

    for test_name, passed in results.items():
        status = "✅ 통과" if passed else "❌ 실패"
        print(f"{test_name:20s}: {status}")

    if all_passed:
        print("\n🎉 모든 테스트 통과! 데이터베이스 연결이 정상입니다.")
        sys.exit(0)
    else:
        print("\n⚠️  일부 테스트 실패. 위 메시지를 확인하세요.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())