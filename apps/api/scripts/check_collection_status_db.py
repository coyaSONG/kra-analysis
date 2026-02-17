#!/usr/bin/env python3
"""
Collection status DB diagnostics.

Usage:
    uv run python scripts/check_collection_status_db.py
    uv run python scripts/check_collection_status_db.py --date 20260214 --meet 1
"""

import argparse
import asyncio
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

import asyncpg

# Add apps/api to module path for direct script execution.
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from infrastructure.database import async_session_maker
from services.collection_status_diagnostics import gather_collection_diagnostics


def _mask_database_url(raw_url: str) -> str:
    try:
        parsed = urlsplit(raw_url)
    except Exception:
        return "<invalid>"

    if "@" not in parsed.netloc:
        return raw_url

    auth, host = parsed.netloc.rsplit("@", 1)
    username = auth.split(":", 1)[0]
    safe_netloc = f"{username}:***@{host}"
    return urlunsplit((parsed.scheme, safe_netloc, parsed.path, parsed.query, parsed.fragment))


def _print_section(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def _print_diagnostics(payload: dict[str, Any]):
    _print_section("Collection Status DB Diagnostics")
    print(f"checked_at: {payload['checked_at']}")
    print(f"db_ok: {payload['db_ok']}")
    print(f"tables: {payload['tables']}")
    print(f"job_status_counts: {payload['job_status_counts']}")

    status = payload.get("collection_status")
    if status is not None:
        print("\ncollection_status:")
        print(
            "  date={date} meet={meet} total={total} collected={collected} enriched={enriched} status={status}".format(
                date=status["date"],
                meet=status["meet"],
                total=status["total_races"],
                collected=status["collected_races"],
                enriched=status["enriched_races"],
                status=status["status"],
            )
        )
        print(
            "  detail: collection={collection_status} enrichment={enrichment_status} result={result_status}".format(
                collection_status=status["collection_status"],
                enrichment_status=status["enrichment_status"],
                result_status=status["result_status"],
            )
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="DB 연결 및 수집 상태 집계 점검 스크립트"
    )
    parser.add_argument("--date", type=str, help="점검할 날짜 (YYYYMMDD)")
    parser.add_argument(
        "--meet", type=int, choices=[1, 2, 3], help="경마장 코드 (1:서울, 2:제주, 3:부산)"
    )
    return parser.parse_args()


def _validate_args(args: argparse.Namespace) -> tuple[str | None, int | None]:
    if bool(args.date) != bool(args.meet):
        raise ValueError("--date와 --meet는 함께 지정해야 합니다.")
    if args.date and not re.match(r"^\d{8}$", args.date):
        raise ValueError("--date는 YYYYMMDD 형식이어야 합니다.")
    return args.date, args.meet


async def _run():
    args = _parse_args()
    race_date, meet = _validate_args(args)

    _print_section("Current DB Config")
    print(f"environment: {settings.environment}")
    print(f"database_url: {_mask_database_url(settings.database_url)}")

    async with async_session_maker() as session:
        diagnostics = await gather_collection_diagnostics(session, race_date, meet)
    _print_diagnostics(diagnostics)


def main() -> int:
    try:
        asyncio.run(_run())
        return 0
    except asyncpg.exceptions.InvalidPasswordError:
        _print_section("DB Connection Error")
        print("password authentication failed")
        print("DATABASE_URL 비밀번호를 확인하세요.")
        return 1
    except asyncpg.exceptions.InvalidAuthorizationSpecificationError:
        _print_section("DB Connection Error")
        print("invalid authorization specification")
        print("DATABASE_URL 사용자명 형식(postgres.<project_id>)을 확인하세요.")
        return 1
    except ValueError as e:
        _print_section("Argument Error")
        print(str(e))
        return 2
    except Exception as e:
        _print_section("Unexpected Error")
        print(f"{type(e).__name__}: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
