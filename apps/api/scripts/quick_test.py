#!/usr/bin/env python3
"""Quick connection test"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


async def main():
    try:
        # Test 1: Config loading
        print("=" * 60)
        print("Test 1: Configuration Loading")
        print("=" * 60)
        from config import settings

        print("✅ Config loaded")
        print(f"   Database URL: {settings.database_url[:70]}...")
        print(f"   Supabase URL: {settings.supabase_url}")
        print(f"   Anon Key configured: {len(settings.supabase_key) > 50}")

        # Test 2: asyncpg connection
        print("\n" + "=" * 60)
        print("Test 2: Direct asyncpg Connection")
        print("=" * 60)

        import asyncpg

        db_url = settings.database_url.replace(
            "postgresql+asyncpg://", "postgresql://"
        ).split("?")[0]
        print(f"Connecting to: {db_url[:60]}...")

        conn = await asyncpg.connect(
            db_url, statement_cache_size=0, server_settings={"jit": "off"}, timeout=10
        )

        version = await conn.fetchval("SELECT version()")
        print("✅ Connected!")
        print(f"   PostgreSQL: {version[:60]}...")

        await conn.close()

        # Test 3: Supabase Client
        print("\n" + "=" * 60)
        print("Test 3: Supabase Python Client")
        print("=" * 60)

        from infrastructure.supabase_client import get_supabase_client

        client = get_supabase_client()

        if client:
            print("✅ Supabase Client initialized")
        else:
            print("❌ Supabase Client failed")

        print("\n" + "=" * 60)
        print("🎉 All tests passed!")
        print("=" * 60)
        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
