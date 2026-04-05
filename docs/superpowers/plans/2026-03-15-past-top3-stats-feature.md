# Past Top3 Stats Feature Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 각 출전마의 최근 경주 top3 진입 이력을 computed_features에 추가하여, 예측 정확도 향상 여부를 A/B 테스트할 수 있게 한다.

**Architecture:** `RaceDBClient`에 과거 top3 통계 조회 메서드를 추가하고, `feature_engineering.py`에서 이를 사용해 `recent_top3_rate`, `recent_win_rate`, `recent_race_count`를 계산한다. `evaluate_prompt_v3.py`에 `--with-past-stats` 플래그를 추가하여 기존 baseline과 비교 가능하게 한다.

**Tech Stack:** Python 3.13, psycopg2, pytest

**데이터 제약:**
- `result_data`는 `[1위번호, 2위번호, 3위번호]` 배열만 저장 (4위 이하 순위 없음)
- 따라서 정확한 착순/표준편차는 불가, top3 진입 여부만 계산 가능
- `basic_data.horses[*].hr_no` + `result_data` 교차 조회로 구현
- leakage 방지: 반드시 `race_date` 이전 경주만 조회

**성능 기준:** 쿼리 테스트 결과 12두 × 3개월 조회 = 0.154초 (허용 범위)

---

## File Structure

| 파일 | 역할 | 변경 |
|------|------|------|
| `packages/scripts/shared/db_client.py` | 과거 top3 통계 조회 메서드 | Modify |
| `packages/scripts/feature_engineering.py` | `recent_top3_rate` 등 피처 계산 | Modify |
| `packages/scripts/evaluation/evaluate_prompt_v3.py` | `--with-past-stats` 플래그, load_race_data에 past_stats 주입 | Modify |
| `packages/scripts/tests/test_past_top3_stats.py` | 단위 테스트 | Create |

---

## Task 1: RaceDBClient에 과거 top3 통계 조회 메서드 추가

**Files:**
- Modify: `packages/scripts/shared/db_client.py`
- Create: `packages/scripts/tests/test_past_top3_stats.py`

- [ ] **Step 1: 테스트 파일 생성 — get_horse_past_top3_stats 테스트**

```python
# packages/scripts/tests/test_past_top3_stats.py
"""past top3 stats 기능 테스트"""

import pytest
from unittest.mock import MagicMock, patch
from shared.db_client import RaceDBClient


class TestGetPastTop3StatsForRace:
    """get_past_top3_stats_for_race 메서드 테스트"""

    def _make_db_rows(self, rows):
        """DB 조회 결과 시뮬레이션용 row 생성"""
        return [
            {"hr_no": r[0], "chul_no": str(r[1]), "result_data": r[2], "date": r[3]}
            for r in rows
        ]

    @patch.object(RaceDBClient, "__init__", lambda self, **kw: None)
    def test_basic_top3_stats(self):
        """top3 진입 통계가 정확히 계산되는지"""
        db = RaceDBClient()
        db._conn = MagicMock()

        # 말 A: 3경주 중 2번 top3 (1번 1위)
        mock_rows = self._make_db_rows([
            ("A", 1, [1, 2, 3], "20250101"),  # 1위
            ("A", 5, [5, 6, 7], "20250108"),  # 1위
            ("A", 3, [1, 2, 4], "20250115"),  # 4위이하
        ])

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = mock_rows
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        db._conn.cursor.return_value = mock_cursor

        result = db.get_past_top3_stats_for_race(
            hr_nos=["A"],
            race_date="20250201",
            lookback_days=90,
        )

        assert "A" in result
        stats = result["A"]
        assert stats["recent_race_count"] == 3
        assert stats["recent_win_count"] == 2
        assert stats["recent_top3_count"] == 2
        assert abs(stats["recent_top3_rate"] - 2 / 3) < 0.01
        assert abs(stats["recent_win_rate"] - 2 / 3) < 0.01

    @patch.object(RaceDBClient, "__init__", lambda self, **kw: None)
    def test_no_past_races(self):
        """과거 출전 기록이 없는 말은 기본값 반환"""
        db = RaceDBClient()
        db._conn = MagicMock()

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        db._conn.cursor.return_value = mock_cursor

        result = db.get_past_top3_stats_for_race(
            hr_nos=["X"],
            race_date="20250201",
            lookback_days=90,
        )

        assert "X" not in result  # 기록 없으면 빈 dict

    @patch.object(RaceDBClient, "__init__", lambda self, **kw: None)
    def test_leakage_prevention(self):
        """race_date 이전 경주만 조회하는지 확인 (쿼리 파라미터 검증)"""
        db = RaceDBClient()
        db._conn = MagicMock()

        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock(return_value=False)
        db._conn.cursor.return_value = mock_cursor

        db.get_past_top3_stats_for_race(
            hr_nos=["A"],
            race_date="20250501",
            lookback_days=90,
        )

        # execute에 전달된 파라미터 확인
        call_args = mock_cursor.execute.call_args
        params = call_args[0][1]
        # params에 lookback 시작일과 race_date가 포함
        assert "20250501" in params  # race_date (상한)
        assert "20250131" in params  # ~90일 전 (하한)
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `uv run python3 -m pytest packages/scripts/tests/test_past_top3_stats.py -v`
Expected: FAIL — `get_past_top3_stats_for_race` 메서드 없음

- [ ] **Step 3: db_client.py에 get_past_top3_stats_for_race 메서드 구현**

`packages/scripts/shared/db_client.py`의 `RaceDBClient` 클래스에 추가:

```python
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

    from datetime import datetime, timedelta

    dt = datetime.strptime(race_date, "%Y%m%d")
    start_date = (dt - timedelta(days=lookback_days)).strftime("%Y%m%d")

    query = """
        SELECT elem->>'hr_no' as hr_no,
               elem->>'chul_no' as chul_no,
               r.result_data,
               r.date
        FROM races r, jsonb_array_elements(r.basic_data->'horses') as elem
        WHERE r.collection_status = 'collected'
          AND r.result_data IS NOT NULL
          AND r.date >= %s AND r.date < %s
          AND elem->>'hr_no' = ANY(%s)
    """

    with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(query, (start_date, race_date, hr_nos))
        rows = cur.fetchall()

    # 말별 집계
    from collections import defaultdict

    counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {"races": 0, "wins": 0, "top3": 0}
    )

    for row in rows:
        hr_no = row["hr_no"]
        chul_no = int(row["chul_no"])
        result = row["result_data"]
        top3 = result if isinstance(result, list) else []

        counts[hr_no]["races"] += 1
        if chul_no in top3:
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
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `uv run python3 -m pytest packages/scripts/tests/test_past_top3_stats.py -v`
Expected: 3 PASSED

- [ ] **Step 5: 커밋**

```bash
git add packages/scripts/shared/db_client.py packages/scripts/tests/test_past_top3_stats.py
git commit -m "feat(scripts): add past top3 stats query to RaceDBClient"
```

---

## Task 2: feature_engineering.py에 past_stats 피처 추가

**Files:**
- Modify: `packages/scripts/feature_engineering.py`
- Modify: `packages/scripts/tests/test_past_top3_stats.py`

- [ ] **Step 1: 테스트 추가 — compute_features에 past_stats 반영**

`packages/scripts/tests/test_past_top3_stats.py`에 추가:

```python
from feature_engineering import compute_features, compute_race_features


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
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

Run: `uv run python3 -m pytest packages/scripts/tests/test_past_top3_stats.py::TestPastStatsInFeatures -v`
Expected: FAIL — `recent_top3_rate` 키 없음

- [ ] **Step 3: feature_engineering.py에 past_stats 피처 추가**

`packages/scripts/feature_engineering.py`의 `compute_features()` 함수에서 `horse_consistency = None` 부분(130-134행) 뒤에 추가:

```python
    # --- 12-14. 최근 top3 통계 (past_stats에서 주입) ---
    past = horse.get("past_stats")
    if past and isinstance(past, dict):
        features["recent_top3_rate"] = past.get("recent_top3_rate")
        features["recent_win_rate"] = past.get("recent_win_rate")
        features["recent_race_count"] = past.get("recent_race_count")
    else:
        features["recent_top3_rate"] = None
        features["recent_win_rate"] = None
        features["recent_race_count"] = None
```

- [ ] **Step 4: 테스트 실행 — 통과 확인**

Run: `uv run python3 -m pytest packages/scripts/tests/test_past_top3_stats.py -v`
Expected: ALL PASSED

- [ ] **Step 5: 커밋**

```bash
git add packages/scripts/feature_engineering.py packages/scripts/tests/test_past_top3_stats.py
git commit -m "feat(scripts): add recent top3 stats to computed features"
```

---

## Task 3: evaluate_prompt_v3.py에 --with-past-stats 플래그 추가

**Files:**
- Modify: `packages/scripts/evaluation/evaluate_prompt_v3.py`

- [ ] **Step 1: argparse에 플래그 추가**

`main()` 함수의 argparse 섹션(`parser.add_argument` 블록들 뒤)에 추가:

```python
    parser.add_argument(
        "--with-past-stats",
        action="store_true",
        default=False,
        help="최근 top3 과거 성적 피처를 추가하여 평가 (A/B 테스트용)",
    )
```

`PromptEvaluatorV3.__init__`에 파라미터 추가:

```python
    def __init__(
        self,
        ...
        with_past_stats: bool = False,
    ):
        ...
        self.with_past_stats = with_past_stats
```

`main()`에서 인스턴스 생성 시 전달:

```python
    evaluator = PromptEvaluatorV3(
        ...
        with_past_stats=args.with_past_stats,
    )
```

- [ ] **Step 2: load_race_data()에 past_stats 주입 로직 추가**

`load_race_data()` 메서드에서 `compute_race_features(horses)` 호출 직전에 past_stats 주입:

```python
            # Past Stats 주입 (A/B 테스트용)
            if self.with_past_stats:
                hr_nos = [h["hrNo"] for h in horses if h.get("hrNo")]
                race_date = items[0]["rcDate"]
                past_stats = self.db_client.get_past_top3_stats_for_race(
                    hr_nos=hr_nos,
                    race_date=race_date,
                    lookback_days=90,
                )
                for horse in horses:
                    hr_no = horse.get("hrNo", "")
                    if hr_no in past_stats:
                        horse["past_stats"] = past_stats[hr_no]

            # Feature Engineering: 파생 피처 계산
            horses = compute_race_features(horses)
```

- [ ] **Step 3: 수동 검증 — dry run**

Run: `uv run python3 -c "
import sys; sys.path.insert(0, 'packages/scripts')
from shared.db_client import RaceDBClient
db = RaceDBClient()
races = db.find_races(limit=1)
if races:
    basic = db.load_race_basic_data(races[0]['race_id'])
    hr_nos = [h.get('hr_no') for h in basic.get('horses', []) if h.get('hr_no')]
    stats = db.get_past_top3_stats_for_race(hr_nos, basic['date'])
    print(f'Race: {races[0][\"race_id\"]}')
    print(f'Horses: {len(hr_nos)}')
    print(f'Past stats found: {len(stats)}')
    for k, v in list(stats.items())[:3]:
        print(f'  {k}: {v}')
db.close()
"`

Expected: 정상 출력, past stats 조회 결과

- [ ] **Step 4: 커밋**

```bash
git add packages/scripts/evaluation/evaluate_prompt_v3.py
git commit -m "feat(scripts): add --with-past-stats flag for A/B testing"
```

---

## Task 4: 통합 테스트 및 A/B 실험 가이드

- [ ] **Step 1: 전체 테스트 실행**

Run: `uv run python3 -m pytest packages/scripts/tests/test_past_top3_stats.py -v`
Expected: ALL PASSED

- [ ] **Step 2: A/B 실험 실행 방법 문서화 (터미널 출력)**

Baseline (past_stats 없이):
```bash
uv run python3 packages/scripts/evaluation/evaluate_prompt_v3.py \
  v-baseline prompts/base-prompt-v1.0.md 30 3
```

With past_stats:
```bash
uv run python3 packages/scripts/evaluation/evaluate_prompt_v3.py \
  v-with-past-stats prompts/base-prompt-v1.0.md 30 3 --with-past-stats
```

비교: 두 결과의 `success_rate`, `average_correct_horses`, `top3` 지표 비교

- [ ] **Step 3: 최종 커밋**

```bash
git add -A
git commit -m "feat(scripts): complete past top3 stats feature for ablation testing"
```
