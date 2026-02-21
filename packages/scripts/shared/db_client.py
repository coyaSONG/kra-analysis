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

        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

        meet_map = {1: "서울", 2: "제주", 3: "부산경남"}
        return [
            {
                "race_id": row["race_id"],
                "race_date": row["date"],
                "race_no": str(row["race_number"]),
                "meet": meet_map.get(row["meet"], "서울"),
            }
            for row in rows
        ]

    def load_race_basic_data(self, race_id: str) -> dict | None:
        """경주 basic_data 로드 (raw JSON)

        Returns:
            basic_data dict 또는 None
        """
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT basic_data FROM races WHERE race_id = %s",
                (race_id,),
            )
            row = cur.fetchone()

        if not row or not row["basic_data"]:
            return None

        data = row["basic_data"]
        # psycopg2가 JSON을 자동 파싱하지 않는 경우 대비
        if isinstance(data, str):
            data = json.loads(data)
        return data

    def get_race_result(self, race_id: str) -> list[int]:
        """경주 결과 (1-3위 출전번호) 조회

        Returns:
            [1위번호, 2위번호, 3위번호] 또는 []
        """
        with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT result_data FROM races WHERE race_id = %s AND result_status = 'collected'",
                (race_id,),
            )
            row = cur.fetchone()

        if not row or not row["result_data"]:
            return []

        result_data = row["result_data"]
        if isinstance(result_data, str):
            result_data = json.loads(result_data)

        # result_data가 이미 [1위, 2위, 3위] 형태인 경우
        if isinstance(result_data, list):
            return result_data

        # result_data가 dict인 경우 top3 키 확인
        if isinstance(result_data, dict):
            return result_data.get("top3", [])

        return []

    def close(self):
        if self._conn and not self._conn.closed:
            self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
