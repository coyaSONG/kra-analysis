"""prepare.py 단위 테스트"""

import sys
import tempfile
import textwrap
from pathlib import Path
from unittest.mock import MagicMock

# packages/scripts/ 를 sys.path에 추가 (기존 evaluate_prompt_v3.py와 동일한 패턴)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_find_races_with_results_filters_result_status():
    """find_races_with_results()가 result_status='collected'로 필터링하는지"""
    from shared.db_client import RaceDBClient

    client = RaceDBClient.__new__(RaceDBClient)
    # SQL에 result_status 조건이 포함되는지 확인
    mock_conn = MagicMock()
    mock_conn.closed = False
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    client._conn = mock_conn

    client.find_races_with_results()

    executed_sql = mock_cursor.execute.call_args[0][0]
    assert "result_status" in executed_sql
    assert "collection_status" in executed_sql


def test_import_guard_blocks_forbidden_imports():
    """금지 모듈 import를 감지하는지"""
    from prepare import check_train_imports

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(
            textwrap.dedent("""\
            import os
            from pathlib import Path
            import json  # 이건 허용
        """)
        )
        f.flush()
        violations = check_train_imports(f.name)

    assert "os" in violations
    assert "pathlib" in violations
    assert "json" not in violations


def test_import_guard_allows_safe_imports():
    """허용된 모듈은 통과하는지"""
    from prepare import check_train_imports

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(
            textwrap.dedent("""\
            import json
            import re
            import math
        """)
        )
        f.flush()
        violations = check_train_imports(f.name)

    assert violations == []


def test_strip_forbidden_fields():
    """forbidden fields가 snapshot에서 제거되는지"""
    from prepare import strip_forbidden_fields

    race_data = {
        "chulNo": 1,
        "hrName": "테스트마",
        "winOdds": 5.0,
        "rank": "국6",  # forbidden → 제거 대상
        "rcTime": "1:23.4",  # forbidden → 제거 대상
    }
    cleaned = strip_forbidden_fields(race_data)
    assert "rank" not in cleaned
    assert "rcTime" not in cleaned
    assert cleaned["chulNo"] == 1
    assert cleaned["hrName"] == "테스트마"


def test_rename_rank_to_class_rank():
    """rank 필드가 class_rank로 rename되는지"""
    from prepare import strip_forbidden_fields

    race_data = {"rank": "국6", "chulNo": 1}
    cleaned = strip_forbidden_fields(race_data)
    assert "rank" not in cleaned
    assert cleaned["class_rank"] == "국6"


def test_set_match_score():
    """set_match 계산이 정확한지"""
    from prepare import set_match_score

    assert set_match_score([1, 2, 3], [1, 2, 3]) == 1.0  # 3/3
    assert set_match_score([1, 2, 3], [4, 5, 6]) == 0.0  # 0/3
    assert abs(set_match_score([1, 2, 3], [1, 4, 5]) - 1 / 3) < 0.01  # 1/3
    assert abs(set_match_score([1, 2, 3], [3, 2, 7]) - 2 / 3) < 0.01  # 2/3
