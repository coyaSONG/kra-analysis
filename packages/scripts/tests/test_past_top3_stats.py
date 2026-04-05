"""past top3 stats 기능 테스트"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from feature_engineering import compute_features
from shared.db_client import RaceDBClient


class TestGetPastTop3StatsForRace:
    """get_past_top3_stats_for_race 메서드 테스트"""

    def _make_client(self):
        """mock DB 연결이 설정된 RaceDBClient 생성"""
        with patch.object(RaceDBClient, "__init__", lambda self, **kw: None):
            db = RaceDBClient()
        db._conn = MagicMock()
        db._conn.closed = False  # conn 프로퍼티가 재연결 시도하지 않도록
        return db

    def _make_cursor(self, db, rows):
        """mock cursor 설정"""
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = rows
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        db._conn.cursor.return_value = mock_cursor
        return mock_cursor

    def test_basic_top3_stats(self):
        """top3 진입 통계가 정확히 계산되는지"""
        db = self._make_client()

        # 말 A: 3경주 - 1위 1회, 3위 1회, 4위이하 1회
        rows = [
            {"hr_no": "A", "chul_no": 1, "result_data": [1, 2, 3], "date": "20250101"},
            {"hr_no": "A", "chul_no": 5, "result_data": [4, 5, 6], "date": "20250108"},
            {"hr_no": "A", "chul_no": 3, "result_data": [1, 2, 4], "date": "20250115"},
        ]
        self._make_cursor(db, rows)

        result = db.get_past_top3_stats_for_race(
            hr_nos=["A"],
            race_date="20250201",
            lookback_days=90,
        )

        assert "A" in result
        stats = result["A"]
        assert stats["recent_race_count"] == 3
        assert stats["recent_win_count"] == 1  # 첫 번째만 1위
        assert stats["recent_top3_count"] == 2  # 첫, 두번째
        assert abs(stats["recent_top3_rate"] - 2 / 3) < 0.01
        assert abs(stats["recent_win_rate"] - 1 / 3) < 0.01

    def test_no_past_races(self):
        """과거 출전 기록이 없는 말은 결과에 포함되지 않음"""
        db = self._make_client()
        self._make_cursor(db, [])

        result = db.get_past_top3_stats_for_race(
            hr_nos=["X"],
            race_date="20250201",
            lookback_days=90,
        )

        assert "X" not in result

    def test_empty_hr_nos(self):
        """빈 hr_nos 리스트는 빈 dict 반환"""
        db = self._make_client()

        result = db.get_past_top3_stats_for_race(
            hr_nos=[],
            race_date="20250201",
        )

        assert result == {}

    def test_result_data_string_parsing(self):
        """result_data가 문자열로 올 경우 파싱"""
        db = self._make_client()

        rows = [
            {
                "hr_no": "B",
                "chul_no": 2,
                "result_data": "[2, 3, 4]",
                "date": "20250101",
            },
        ]
        self._make_cursor(db, rows)

        result = db.get_past_top3_stats_for_race(
            hr_nos=["B"],
            race_date="20250201",
        )

        assert result["B"]["recent_top3_count"] == 1

    def test_leakage_prevention(self):
        """race_date 이전 경주만 조회하는지 확인 (쿼리 파라미터 검증)"""
        db = self._make_client()
        mock_cursor = self._make_cursor(db, [])

        db.get_past_top3_stats_for_race(
            hr_nos=["A"],
            race_date="20250501",
            lookback_days=90,
        )

        call_args = mock_cursor.execute.call_args
        params = call_args[0][1]
        assert "20250501" in params  # race_date (상한, exclusive)
        assert "20250131" in params  # ~90일 전 (하한)

    def test_multiple_horses(self):
        """여러 말의 통계가 독립적으로 계산"""
        db = self._make_client()

        rows = [
            {"hr_no": "A", "chul_no": 1, "result_data": [1, 2, 3], "date": "20250101"},
            {"hr_no": "B", "chul_no": 2, "result_data": [1, 2, 3], "date": "20250101"},
            {"hr_no": "A", "chul_no": 4, "result_data": [5, 6, 7], "date": "20250108"},
        ]
        self._make_cursor(db, rows)

        result = db.get_past_top3_stats_for_race(
            hr_nos=["A", "B"],
            race_date="20250201",
        )

        assert result["A"]["recent_race_count"] == 2
        assert result["A"]["recent_top3_count"] == 1
        assert result["B"]["recent_race_count"] == 1
        assert result["B"]["recent_top3_count"] == 1


class TestPastStatsInFeatures:
    """compute_features가 past_stats를 computed_features에 반영하는지 테스트"""

    def test_past_stats_injected(self):
        """past_stats가 있으면 computed_features에 포함"""
        horse = {
            "chulNo": 1,
            "winOdds": 5.0,
            "rating": 50,
            "past_stats": {
                "recent_race_count": 5,
                "recent_win_count": 2,
                "recent_top3_count": 3,
                "recent_win_rate": 0.4,
                "recent_top3_rate": 0.6,
            },
        }
        features = compute_features(horse)
        assert features["recent_top3_rate"] == 0.6
        assert features["recent_win_rate"] == 0.4
        assert features["recent_race_count"] == 5

    def test_no_past_stats(self):
        """past_stats가 없으면 None"""
        horse = {"chulNo": 1, "winOdds": 5.0, "rating": 50}
        features = compute_features(horse)
        assert features["recent_top3_rate"] is None
        assert features["recent_win_rate"] is None
        assert features["recent_race_count"] is None
