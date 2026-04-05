"""
Supabase DB 동기 클라이언트
평가/개선 스크립트에서 사용하는 동기 PostgreSQL 클라이언트
"""

import json
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras
from dotenv import dotenv_values

from shared.read_contract import RaceKey, RaceSnapshot, normalize_result_data


def _load_database_url() -> str:
    """apps/api/.env에서 DATABASE_URL 로드"""
    # packages/scripts/shared/db_client.py → apps/api/.env
    env_path = Path(__file__).parent.parent.parent.parent / "apps" / "api" / ".env"
    if not env_path.exists():
        raise FileNotFoundError(f".env 파일을 찾을 수 없습니다: {env_path}")

    env_values = dotenv_values(env_path)
    db_url = env_values.get("DATABASE_URL", "")
    if not db_url:
        raise ValueError("DATABASE_URL이 .env에 설정되지 않았습니다")

    # SQLAlchemy asyncpg prefix 제거 → psycopg2 호환 URL
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    # Supabase pooler는 port 6543 (transaction mode)
    # psycopg2는 prepared statement 이슈 없으므로 그대로 사용 가능
    return db_url


class RaceDBClient:
    """동기 PostgreSQL 클라이언트 - 평가 스크립트용"""

    def __init__(self, database_url: str | None = None):
        self._database_url = database_url or _load_database_url()
        self._conn = None

    @property
    def conn(self):
        if self._conn is None or self._conn.closed:
            self._conn = psycopg2.connect(self._database_url)
        return self._conn

    def _fetch_race_rows(
        self,
        query: str,
        params: list[Any],
    ) -> list[dict[str, Any]]:
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            return list(cur.fetchall())

    def _legacy_rows_to_race_keys(self, rows: list[dict[str, Any]]) -> list[RaceKey]:
        return [
            RaceKey(
                race_id=str(row["race_id"]),
                race_date=str(row["date"]),
                meet=int(row["meet"]),
                race_number=int(row["race_number"]),
            )
            for row in rows
        ]

    def find_race_keys(
        self,
        date_filter: str | None = None,
        limit: int | None = None,
    ) -> list[RaceKey]:
        """수집 완료된 경주를 공통 read DTO로 조회."""
        query = """
            SELECT race_id, date, meet, race_number
            FROM races
            WHERE collection_status = 'collected'
        """
        params: list[Any] = []

        if date_filter:
            query += " AND date = %s"
            params.append(date_filter)

        query += " ORDER BY date, meet, race_number"

        if limit:
            query += " LIMIT %s"
            params.append(limit)

        rows = self._fetch_race_rows(query, params)
        return self._legacy_rows_to_race_keys(rows)

    def find_races(
        self,
        date_filter: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """수집 완료된 경주 목록 조회

        Args:
            date_filter: 특정 날짜 필터 (YYYYMMDD)
            limit: 최대 조회 수

        Returns:
            [{race_id, race_date, race_no, meet}, ...]
        """
        return [key.to_legacy_dict() for key in self.find_race_keys(date_filter, limit)]

    def find_races_with_results(
        self,
        date_filter: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """수집 완료 + 결과 확정된 경주 목록 조회"""
        query = """
            SELECT race_id, date, meet, race_number
            FROM races
            WHERE collection_status = 'collected'
              AND result_status = 'collected'
        """
        params: list[Any] = []

        if date_filter:
            query += " AND date = %s"
            params.append(date_filter)

        query += " ORDER BY date, meet, race_number"

        if limit:
            query += " LIMIT %s"
            params.append(limit)

        rows = self._fetch_race_rows(query, params)
        return [key.to_legacy_dict() for key in self._legacy_rows_to_race_keys(rows)]

    def load_race_snapshot(self, race_id: str) -> RaceSnapshot | None:
        """공통 read DTO로 경주 row를 로드."""
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT race_id,
                       date,
                       meet,
                       race_number,
                       collection_status,
                       result_status,
                       basic_data,
                       result_data
                FROM races
                WHERE race_id = %s
            """,
                (race_id,),
            )
            row = cur.fetchone()

        if not row:
            return None

        return RaceSnapshot.from_row(row)

    def load_race_basic_data(self, race_id: str) -> dict | None:
        """경주 basic_data 로드 (raw JSON)

        Returns:
            basic_data dict 또는 None
        """
        snapshot = self.load_race_snapshot(race_id)
        if not snapshot or not snapshot.basic_data:
            return None

        data = snapshot.basic_data
        # psycopg2가 JSON을 자동 파싱하지 않는 경우 대비
        if isinstance(data, str):
            data = json.loads(data)
        return data

    def get_race_result(self, race_id: str) -> list[int]:
        """경주 결과 (1-3위 출전번호) 조회

        Returns:
            [1위번호, 2위번호, 3위번호] 또는 []
        """
        snapshot = self.load_race_snapshot(race_id)
        if not snapshot or snapshot.result_status != "collected":
            return []

        return normalize_result_data(snapshot.result_data)

    def get_past_top3_stats_for_race(
        self,
        hr_nos: list[str],
        race_date: str,
        lookback_days: int = 90,
    ) -> dict[str, dict[str, Any]]:
        """경주 출전마 전체의 최근 top3 통계를 한 번에 조회

        Args:
            hr_nos: 조회할 말 번호 리스트
            race_date: 기준 날짜 (YYYYMMDD) — 이 날짜 이전만 조회 (leakage 방지)
            lookback_days: 조회 기간 (일)

        Returns:
            {hr_no: {recent_race_count, recent_win_count, recent_top3_count,
                     recent_win_rate, recent_top3_rate}}
        """
        if not hr_nos:
            return {}

        from collections import defaultdict
        from datetime import datetime, timedelta

        dt = datetime.strptime(race_date, "%Y%m%d")
        start_date = (dt - timedelta(days=lookback_days)).strftime("%Y%m%d")

        # 중복 제거
        hr_nos = list(set(hr_nos))

        query = """
            SELECT elem->>'hr_no' as hr_no,
                   (elem->>'chul_no')::int as chul_no,
                   r.result_data,
                   r.date
            FROM races r, jsonb_array_elements(r.basic_data->'horses') as elem
            WHERE r.collection_status = 'collected'
              AND r.result_status = 'collected'
              AND r.result_data IS NOT NULL
              AND r.date >= %s AND r.date < %s
              AND elem->>'hr_no' = ANY(%s::text[])
              AND COALESCE((elem->>'win_odds')::numeric, 0) > 0
        """

        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, (start_date, race_date, hr_nos))
            rows = cur.fetchall()

        # 말별 집계
        counts: dict[str, dict[str, int]] = defaultdict(
            lambda: {"races": 0, "wins": 0, "top3": 0}
        )

        for row in rows:
            hr_no = row["hr_no"]
            chul_no = row["chul_no"]
            top3 = normalize_result_data(row["result_data"])

            counts[hr_no]["races"] += 1
            if top3 and chul_no in top3:
                counts[hr_no]["top3"] += 1
                if top3[0] == chul_no:
                    counts[hr_no]["wins"] += 1

        # 통계 계산
        stats: dict[str, dict[str, Any]] = {}
        for hr_no, c in counts.items():
            race_count = c["races"]
            stats[hr_no] = {
                "recent_race_count": race_count,
                "recent_win_count": c["wins"],
                "recent_top3_count": c["top3"],
                "recent_win_rate": c["wins"] / race_count if race_count > 0 else 0,
                "recent_top3_rate": c["top3"] / race_count if race_count > 0 else 0,
            }

        return stats

    def close(self):
        if self._conn and not self._conn.closed:
            self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
