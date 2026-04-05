#!/usr/bin/env python3
"""
Supabase 데이터베이스 마이그레이션 적용 스크립트

사용법:
    python3 scripts/apply_migrations.py
    python3 scripts/apply_migrations.py --dry-run  # 실제 적용 없이 확인만
"""

import argparse
import asyncio
import hashlib
import sys
from pathlib import Path

import asyncpg
import structlog

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from infrastructure.migration_manifest import (
    get_active_migration_names,
    get_active_migration_paths,
    get_required_migration_head,
)

logger = structlog.get_logger()
MIGRATIONS_TABLE = "schema_migrations"


def compute_checksum(migration_file: Path) -> str:
    return hashlib.sha256(migration_file.read_bytes()).hexdigest()


async def get_connection():
    """데이터베이스 연결 생성"""
    db_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
    base_url = db_url.split("?")[0]

    return await asyncpg.connect(
        base_url, statement_cache_size=0, server_settings={"jit": "off"}, timeout=30
    )


async def check_migration_status(conn):
    """적용된 마이그레이션 확인"""
    print("\n" + "=" * 80)
    print("마이그레이션 상태 확인")
    print("=" * 80)

    applied = await fetch_applied_migrations(conn, create_if_missing=False)
    if applied:
        print(f"✅ 적용된 마이그레이션 {len(applied)}개:")
        for migration in applied:
            print(f"   - {migration['name']} ({migration['checksum'][:8]})")
    else:
        print("ℹ️  적용된 마이그레이션 기록이 없습니다.")

    # 테이블 존재 여부 확인
    tables = await conn.fetch(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
    """
    )

    if tables:
        print(f"✅ 기존 테이블 {len(tables)}개 발견:")
        for table in tables:
            print(f"   - {table['table_name']}")
        return True
    else:
        print("ℹ️  테이블이 없습니다. 새로운 데이터베이스입니다.")
        return False


async def ensure_schema_migrations_table(conn):
    await conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} (
            name VARCHAR(255) PRIMARY KEY,
            checksum VARCHAR(64) NOT NULL,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """
    )


async def fetch_applied_migrations(
    conn, *, create_if_missing: bool
) -> list[asyncpg.Record]:
    if create_if_missing:
        await ensure_schema_migrations_table(conn)
    else:
        exists = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = $1
            )
        """,
            MIGRATIONS_TABLE,
        )
        if not exists:
            return []
    return await conn.fetch(
        f"SELECT name, checksum, applied_at FROM {MIGRATIONS_TABLE} ORDER BY name"
    )


async def get_applied_migrations(
    conn, *, create_if_missing: bool = True
) -> dict[str, str]:
    rows = await fetch_applied_migrations(conn, create_if_missing=create_if_missing)
    return {row["name"]: row["checksum"] for row in rows}


async def apply_migration(conn, migration_file: Path, dry_run: bool = False):
    """마이그레이션 파일 적용"""
    print(f"\n{'[DRY RUN] ' if dry_run else ''}적용 중: {migration_file.name}")
    print("-" * 80)

    try:
        checksum = compute_checksum(migration_file)

        # SQL 파일 읽기
        sql_content = migration_file.read_text()

        # 주석과 빈 줄 제거한 미리보기
        preview_lines = [
            line
            for line in sql_content.split("\n")[:20]
            if line.strip() and not line.strip().startswith("--")
        ]
        print("SQL 미리보기:")
        for line in preview_lines[:10]:
            print(f"  {line}")
        if len(preview_lines) > 10:
            print(f"  ... (총 {len(sql_content.splitlines())}줄)")

        if dry_run:
            print("⚠️  DRY RUN 모드: 실제로 적용하지 않음")
            return True

        # 트랜잭션으로 실행
        async with conn.transaction():
            await ensure_schema_migrations_table(conn)
            await conn.fetchval(
                "SELECT pg_advisory_xact_lock(hashtext($1))", migration_file.name
            )
            existing = await conn.fetchrow(
                f"SELECT name, checksum FROM {MIGRATIONS_TABLE} WHERE name = $1",
                migration_file.name,
            )
            if existing and existing["checksum"] == checksum:
                print(f"⏭️  이미 적용됨: {migration_file.name}")
                return False
            if existing and existing["checksum"] != checksum:
                raise RuntimeError(
                    f"Checksum mismatch for applied migration {migration_file.name}"
                )
            await conn.execute(sql_content)
            await conn.execute(
                f"""
                INSERT INTO {MIGRATIONS_TABLE}(name, checksum)
                VALUES($1, $2)
                ON CONFLICT (name) DO NOTHING
            """,
                migration_file.name,
                checksum,
            )

        print(f"✅ {migration_file.name} 적용 완료")
        return True

    except asyncpg.exceptions.DuplicateTableError as e:
        print(f"⚠️  테이블이 이미 존재합니다: {e}")
        print("   이 마이그레이션은 이미 적용되었을 수 있습니다.")
        return False

    except asyncpg.exceptions.DuplicateObjectError as e:
        print(f"⚠️  객체가 이미 존재합니다: {e}")
        print("   이 마이그레이션은 이미 적용되었을 수 있습니다.")
        return False

    except Exception as e:
        print(f"❌ 마이그레이션 적용 실패: {type(e).__name__}")
        print(f"   {e}")
        raise


async def verify_schema(conn):
    """스키마 검증"""
    print("\n" + "=" * 80)
    print("스키마 검증")
    print("=" * 80)

    # 필수 테이블 목록
    required_tables = [
        "races",
        "predictions",
        "jobs",
        "job_logs",
        "api_keys",
        "prompt_templates",
        "usage_events",
    ]

    # 테이블 존재 확인
    tables = await conn.fetch(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
    """
    )

    existing_tables = {t["table_name"] for t in tables}

    print("\n필수 테이블 확인:")
    all_present = True
    for table in required_tables:
        if table in existing_tables:
            print(f"   ✅ {table}")
        else:
            print(f"   ❌ {table} (없음)")
            all_present = False

    # 추가 테이블
    extra_tables = existing_tables - set(required_tables)
    if extra_tables:
        print("\n추가 테이블:")
        for table in sorted(extra_tables):
            print(f"   ℹ️  {table}")

    # RLS 정책 확인
    print("\n\nRow Level Security 정책:")
    policies = await conn.fetch(
        """
        SELECT schemaname, tablename, policyname
        FROM pg_policies
        WHERE schemaname = 'public'
    """
    )

    if policies:
        for policy in policies:
            print(f"   ✅ {policy['tablename']}: {policy['policyname']}")
    else:
        print("   ⚠️  RLS 정책이 없습니다.")

    return all_present


async def get_migration_head(conn) -> str | None:
    applied = await get_applied_migrations(conn, create_if_missing=False)
    if not applied:
        return None
    return sorted(applied)[-1]


def validate_manifest_files() -> list[Path]:
    paths = get_active_migration_paths()
    missing = [path.name for path in paths if not path.exists()]
    if missing:
        raise RuntimeError(f"Manifest references missing migrations: {missing}")
    return paths


async def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="Supabase 마이그레이션 적용")
    parser.add_argument(
        "--dry-run", action="store_true", help="실제 적용 없이 확인만 수행"
    )
    args = parser.parse_args()

    print("=" * 80)
    print("Supabase 마이그레이션 적용")
    print("=" * 80)

    if args.dry_run:
        print("\n⚠️  DRY RUN 모드: 실제 변경 사항이 적용되지 않습니다.\n")

    # 설정 확인
    print(f"데이터베이스: {settings.database_url[:60]}...")
    print(f"환경: {settings.environment}")

    if settings.database_url.startswith("postgresql+asyncpg://kra_user:kra_password"):
        print("\n❌ 오류: 기본 DATABASE_URL 사용 중!")
        print("   .env 파일을 생성하고 실제 Supabase URL로 설정하세요.")
        sys.exit(1)

    # 마이그레이션 파일 찾기
    migrations_dir = Path(__file__).parent.parent / "migrations"
    if not migrations_dir.exists():
        print(f"\n❌ 마이그레이션 디렉토리가 없습니다: {migrations_dir}")
        sys.exit(1)

    migration_files = validate_manifest_files()
    if not migration_files:
        print(f"\n⚠️  마이그레이션 파일이 없습니다: {migrations_dir}")
        sys.exit(0)

    print(f"\n활성 마이그레이션 파일 {len(migration_files)}개:")
    for f in migration_files:
        print(f"   - {f.name}")
    inactive = sorted(
        path.name
        for path in migrations_dir.glob("*.sql")
        if path.name not in get_active_migration_names()
    )
    if inactive:
        print("\n비활성/legacy 마이그레이션 파일:")
        for name in inactive:
            print(f"   - {name}")

    # 연결
    print("\n데이터베이스 연결 중...")
    try:
        conn = await get_connection()
        print("✅ 연결 성공")
    except Exception as e:
        print(f"\n❌ 데이터베이스 연결 실패: {e}")
        print("\n연결 테스트 실행:")
        print("   python3 scripts/test_db_connection.py")
        sys.exit(1)

    try:
        # 현재 상태 확인
        has_tables = await check_migration_status(conn)
        required_head = get_required_migration_head()
        if required_head:
            print(f"\n정답 migration head: {required_head}")

        # 사용자 확인
        if not args.dry_run:
            if has_tables:
                print(
                    "\n⚠️  경고: 기존 테이블이 있습니다. 마이그레이션 적용 시 오류가 발생할 수 있습니다."
                )
                response = input("계속하시겠습니까? (yes/no): ")
                if response.lower() != "yes":
                    print("취소됨")
                    return
            else:
                response = input("\n마이그레이션을 적용하시겠습니까? (yes/no): ")
                if response.lower() != "yes":
                    print("취소됨")
                    return

        # 마이그레이션 적용
        success_count = 0
        for migration_file in migration_files:
            try:
                success = await apply_migration(conn, migration_file, args.dry_run)
                if success:
                    success_count += 1
            except Exception as e:
                print("\n❌ 마이그레이션 적용 중 오류 발생")
                print(f"   파일: {migration_file.name}")
                print(f"   오류: {e}")
                break

        # 검증
        if not args.dry_run and success_count > 0:
            await verify_schema(conn)

        # 결과 요약
        print("\n" + "=" * 80)
        print("결과 요약")
        print("=" * 80)
        print(f"총 마이그레이션: {len(migration_files)}개")
        print(f"성공: {success_count}개")
        print(f"실패/스킵: {len(migration_files) - success_count}개")

        if args.dry_run:
            print("\n✅ DRY RUN 완료. 실제 적용하려면 --dry-run 옵션 없이 실행하세요.")
        elif success_count == len(migration_files):
            print("\n🎉 모든 마이그레이션이 성공적으로 적용되었습니다!")
        elif success_count > 0:
            print("\n⚠️  일부 마이그레이션이 적용되었습니다. 위 메시지를 확인하세요.")
        else:
            print("\n❌ 마이그레이션 적용 실패")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
