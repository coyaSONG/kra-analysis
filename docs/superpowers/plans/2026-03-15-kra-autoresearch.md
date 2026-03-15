# KRA Autoresearch Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** karpathy/autoresearch 패턴을 KRA 경마 예측 시스템에 접합 — prepare.py(고정 하네스), train.py(에이전트 수정), program.md(에이전트 지시서) 3파일 구성

**Architecture:** prepare.py가 DB에서 고정 snapshot을 생성하고, train.py의 predict()를 호출하여 평가. train.py는 프롬프트+전략 함수만 포함하는 좁은 모듈. program.md는 autoresearch 원본 구조를 따르는 에이전트 지시서.

**Tech Stack:** Python 3.10+, uv, psycopg2 (기존 db_client.py), Claude CLI, argparse

**Spec:** `docs/superpowers/specs/2026-03-15-kra-autoresearch-design.md`

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `packages/scripts/autoresearch/prepare.py` | 고정 하네스: snapshot 생성, 평가 실행, 스코어 출력, import guard |
| Create | `packages/scripts/autoresearch/train.py` | 에이전트 수정 대상: 프롬프트 + 전략 함수 + predict() |
| Create | `packages/scripts/autoresearch/program.md` | 에이전트 지시서 |
| Modify | `packages/scripts/shared/db_client.py` | `find_races_with_results()` 메서드 추가 |
| Create | `packages/scripts/autoresearch/tests/test_prepare.py` | prepare.py 단위 테스트 |
| Create | `packages/scripts/autoresearch/tests/test_train.py` | train.py 단위 테스트 |
| Create | `packages/scripts/autoresearch/tests/__init__.py` | 패키지 init |
| Create | `packages/scripts/autoresearch/__init__.py` | 패키지 init |

---

## Chunk 1: db_client 확장 + import guard

### Task 1: db_client에 find_races_with_results() 추가

**Files:**
- Modify: `packages/scripts/shared/db_client.py:48-92`
- Test: `packages/scripts/autoresearch/tests/test_prepare.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/scripts/autoresearch/tests/test_prepare.py
"""prepare.py 단위 테스트"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# packages/scripts/ 를 sys.path에 추가 (기존 evaluate_prompt_v3.py와 동일한 패턴)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_find_races_with_results_filters_result_status():
    """find_races_with_results()가 result_status='collected'로 필터링하는지"""
    from shared.db_client import RaceDBClient

    client = RaceDBClient.__new__(RaceDBClient)
    # SQL에 result_status 조건이 포함되는지 확인
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    client._conn = mock_conn

    client.find_races_with_results()

    executed_sql = mock_cursor.execute.call_args[0][0]
    assert "result_status" in executed_sql
    assert "collection_status" in executed_sql
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/chsong/Developer/Personal/kra-analysis && uv run python3 -m pytest packages/scripts/autoresearch/tests/test_prepare.py::test_find_races_with_results_filters_result_status -v`
Expected: FAIL — `find_races_with_results` not found

- [ ] **Step 3: Write implementation**

`packages/scripts/shared/db_client.py` 에 `find_races` 메서드 뒤에 추가:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/chsong/Developer/Personal/kra-analysis && uv run python3 -m pytest packages/scripts/autoresearch/tests/test_prepare.py::test_find_races_with_results_filters_result_status -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/scripts/shared/db_client.py packages/scripts/autoresearch/tests/test_prepare.py packages/scripts/autoresearch/tests/__init__.py packages/scripts/autoresearch/__init__.py
git commit -m "feat(autoresearch): add find_races_with_results to db_client"
```

### Task 2: import guard 구현

**Files:**
- Create: `packages/scripts/autoresearch/prepare.py` (초기 골격)
- Test: `packages/scripts/autoresearch/tests/test_prepare.py`

- [ ] **Step 1: Write the failing test**

```python
# test_prepare.py에 추가
import tempfile
import textwrap


def test_import_guard_blocks_forbidden_imports():
    """금지 모듈 import를 감지하는지"""
    # prepare.py의 check_train_imports를 직접 테스트
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from prepare import check_train_imports

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(textwrap.dedent("""\
            import os
            from pathlib import Path
            import json  # 이건 허용
        """))
        f.flush()
        violations = check_train_imports(f.name)

    assert "os" in violations
    assert "pathlib" in violations
    assert "json" not in [v for v in violations]


def test_import_guard_allows_safe_imports():
    """허용된 모듈은 통과하는지"""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from prepare import check_train_imports

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(textwrap.dedent("""\
            import json
            import re
            import math
        """))
        f.flush()
        violations = check_train_imports(f.name)

    assert violations == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/chsong/Developer/Personal/kra-analysis && uv run python3 -m pytest packages/scripts/autoresearch/tests/test_prepare.py -k "import_guard" -v`
Expected: FAIL — `check_train_imports` not found

- [ ] **Step 3: Write implementation**

`packages/scripts/autoresearch/prepare.py` 초기 골격:

```python
#!/usr/bin/env python3
"""KRA Autoresearch — 고정 평가 하네스

이 파일은 수정 금지. train.py만 에이전트가 수정합니다.
"""

import ast
import sys

# ============================================================
# Import Guard
# ============================================================

FORBIDDEN_MODULES = {
    "db_client", "os", "pathlib", "subprocess", "shutil",
    "urllib", "requests", "httpx", "supabase",
}


def check_train_imports(filepath: str) -> list[str]:
    """train.py의 import문을 AST로 검사, 금지 모듈 사용 시 반환"""
    with open(filepath) as f:
        tree = ast.parse(f.read())
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name.split(".")[0]
                if mod in FORBIDDEN_MODULES:
                    violations.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mod = node.module.split(".")[0]
            if mod in FORBIDDEN_MODULES:
                violations.append(node.module)
    return violations
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/chsong/Developer/Personal/kra-analysis && uv run python3 -m pytest packages/scripts/autoresearch/tests/test_prepare.py -k "import_guard" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/scripts/autoresearch/prepare.py packages/scripts/autoresearch/tests/test_prepare.py
git commit -m "feat(autoresearch): add import guard for train.py safety"
```

---

## Chunk 2: snapshot 생성

### Task 3: snapshot 생성 로직

**Files:**
- Modify: `packages/scripts/autoresearch/prepare.py`
- Test: `packages/scripts/autoresearch/tests/test_prepare.py`

- [ ] **Step 1: Write the failing test**

```python
# test_prepare.py에 추가
import json


def test_strip_forbidden_fields():
    """forbidden fields가 snapshot에서 제거되는지"""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from prepare import strip_forbidden_fields

    race_data = {
        "chulNo": 1,
        "hrName": "테스트마",
        "winOdds": 5.0,
        "rank": "국6",       # forbidden → 제거 대상
        "rcTime": "1:23.4",  # forbidden → 제거 대상
    }
    cleaned = strip_forbidden_fields(race_data)
    assert "rank" not in cleaned
    assert "rcTime" not in cleaned
    assert cleaned["chulNo"] == 1
    assert cleaned["hrName"] == "테스트마"


def test_rename_rank_to_class_rank():
    """rank 필드가 class_rank로 rename되는지"""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from prepare import strip_forbidden_fields

    race_data = {"rank": "국6", "chulNo": 1}
    cleaned = strip_forbidden_fields(race_data)
    assert "rank" not in cleaned
    assert cleaned["class_rank"] == "국6"


def test_set_match_score():
    """set_match 계산이 정확한지"""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from prepare import set_match_score

    assert set_match_score([1, 2, 3], [1, 2, 3]) == 1.0   # 3/3
    assert set_match_score([1, 2, 3], [4, 5, 6]) == 0.0   # 0/3
    assert abs(set_match_score([1, 2, 3], [1, 4, 5]) - 1/3) < 0.01  # 1/3
    assert abs(set_match_score([1, 2, 3], [3, 2, 7]) - 2/3) < 0.01  # 2/3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/chsong/Developer/Personal/kra-analysis && uv run python3 -m pytest packages/scripts/autoresearch/tests/test_prepare.py -k "strip_forbidden or rename_rank or set_match_score" -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

`prepare.py`에 추가:

```python
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# 프로젝트 경로 설정
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
SNAPSHOTS_DIR = SCRIPT_DIR / "snapshots"

sys.path.insert(0, str(PROJECT_ROOT / "packages" / "scripts"))

from shared.db_client import RaceDBClient
from shared.data_adapter import convert_basic_data_to_enriched_format
from feature_engineering import compute_race_features
from evaluation.leakage_checks import FORBIDDEN_POST_RACE_FIELDS

# ============================================================
# Scoring
# ============================================================

def set_match_score(predicted: list[int], actual: list[int]) -> float:
    """set intersection score: len(pred[:3] & actual[:3]) / 3"""
    pred_set = set(predicted[:3])
    actual_set = set(actual[:3])
    if not actual_set:
        return 0.0
    return len(pred_set & actual_set) / 3


# ============================================================
# Snapshot
# ============================================================

def strip_forbidden_fields(data: dict) -> dict:
    """forbidden fields 제거 + rank→class_rank rename. 재귀적."""
    cleaned = {}
    for key, value in data.items():
        if key == "rank":
            # rank는 사전 등급(class rating) → class_rank로 보존
            cleaned["class_rank"] = value
        elif key in FORBIDDEN_POST_RACE_FIELDS:
            continue  # 제거
        elif isinstance(value, dict):
            cleaned[key] = strip_forbidden_fields(value)
        elif isinstance(value, list):
            cleaned[key] = [
                strip_forbidden_fields(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            cleaned[key] = value
    return cleaned


def _extract_race_data(enriched: dict) -> dict:
    """enriched 형식에서 flat race_data dict 추출.
    raw item의 전체 필드를 보존하고 forbidden fields만 제거."""
    items = enriched["response"]["body"]["items"]["item"]

    # raceInfo 구성 (첫 item의 경주 정보)
    first = items[0]
    race_info = {
        "rcDate": first.get("rcDate", ""),
        "rcNo": first.get("rcNo", ""),
        "meet": first.get("meet", ""),
        "rcDist": first.get("rcDist", ""),
        "track": first.get("track", ""),
        "weather": first.get("weather", ""),
        "budam": first.get("budam", ""),
        "ageCond": first.get("ageCond", ""),
    }

    # 말별 데이터 (raw 전체 보존 + winOdds=0 필터)
    horses = []
    for item in items:
        win_odds = item.get("winOdds", 0)
        try:
            if float(win_odds) == 0:
                continue  # 기권/제외마
        except (TypeError, ValueError):
            continue

        horse = strip_forbidden_fields(item)
        horses.append(horse)

    # compute_race_features: 개별 피처 + odds_rank, rating_rank 일괄 계산
    horses = compute_race_features(horses)

    return {
        "race_info": race_info,
        "horses": horses,
    }


def create_snapshot(force: bool = False) -> None:
    """DB에서 경주 데이터를 읽어 고정 snapshot 생성"""
    SNAPSHOTS_DIR.mkdir(exist_ok=True)

    if (SNAPSHOTS_DIR / "mini_val.json").exists() and not force:
        print("Snapshot already exists. Use --force-recreate to regenerate.")
        return

    db = RaceDBClient()
    try:
        races = db.find_races_with_results()
        print(f"Found {len(races)} races with results")

        if len(races) < 70:
            print(f"ERROR: Need >= 70 races, got {len(races)}")
            sys.exit(1)

        # walk-forward split: [...][mini_val 20][holdout 50]
        holdout_races = races[-50:]
        mini_val_races = races[-70:-50]

        answer_key = {"meta": {}, "mini_val": {}, "holdout": {}}
        snapshots = {"mini_val": [], "holdout": []}

        for mode, race_list in [("mini_val", mini_val_races), ("holdout", holdout_races)]:
            for race_meta in race_list:
                race_id = race_meta["race_id"]
                basic_data = db.load_race_basic_data(race_id)
                if not basic_data:
                    continue

                enriched = convert_basic_data_to_enriched_format(basic_data)
                if not enriched:
                    continue

                race_data = _extract_race_data(enriched)
                race_data["race_id"] = race_id
                race_data["race_date"] = race_meta["race_date"]
                race_data["meet"] = race_meta["meet"]
                snapshots[mode].append(race_data)

                # answer_key
                result = db.get_race_result(race_id)
                if result:
                    answer_key[mode][race_id] = result

        # 개수 검증
        mv_count = len(snapshots["mini_val"])
        ho_count = len(snapshots["holdout"])
        if mv_count < 15:
            print(f"ERROR: mini_val has only {mv_count} races (need >= 15). "
                  f"Check DB for missing basic_data or failed conversions.")
            sys.exit(1)
        if ho_count < 40:
            print(f"ERROR: holdout has only {ho_count} races (need >= 40). "
                  f"Check DB for missing basic_data or failed conversions.")
            sys.exit(1)

        # 메타데이터
        now = datetime.now().isoformat()
        for mode in ("mini_val", "holdout"):
            content = json.dumps(snapshots[mode], ensure_ascii=False)
            sha = hashlib.sha256(content.encode()).hexdigest()[:16]
            with open(SNAPSHOTS_DIR / f"{mode}.json", "w") as f:
                f.write(content)
            print(f"{mode}: {len(snapshots[mode])} races (sha256={sha})")

        answer_key["meta"] = {"created_at": now}
        with open(SNAPSHOTS_DIR / "answer_key.json", "w") as f:
            json.dump(answer_key, f, ensure_ascii=False, indent=2)

        print(f"Snapshot created at {SNAPSHOTS_DIR}")
    finally:
        db.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/chsong/Developer/Personal/kra-analysis && uv run python3 -m pytest packages/scripts/autoresearch/tests/test_prepare.py -k "strip_forbidden or rename_rank or set_match_score" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/scripts/autoresearch/prepare.py packages/scripts/autoresearch/tests/test_prepare.py
git commit -m "feat(autoresearch): add snapshot creation and scoring logic"
```

---

## Chunk 3: 평가 하네스 + CLI

### Task 4: evaluate() + _call_llm() + CLI

**Files:**
- Modify: `packages/scripts/autoresearch/prepare.py`
- Test: `packages/scripts/autoresearch/tests/test_prepare.py`

- [ ] **Step 1: Write the failing test**

```python
# test_prepare.py에 추가
def test_compute_score_perfect():
    """완벽한 예측의 스코어"""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from prepare import compute_score

    prediction = {"predicted": [1, 2, 3], "confidence": 0.8, "reasoning": "test"}
    actual = [1, 2, 3]
    score = compute_score(prediction, actual)
    assert score["json_ok"] is True
    assert score["deferred"] is False
    assert score["set_match"] == 1.0
    assert score["correct_count"] == 3


def test_compute_score_deferred():
    """confidence < 0.3이면 defer 처리"""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from prepare import compute_score

    prediction = {"predicted": [1, 2, 3], "confidence": 0.2, "reasoning": "low"}
    actual = [1, 2, 3]
    score = compute_score(prediction, actual)
    assert score["deferred"] is True


def test_compute_score_invalid_schema():
    """스키마 불일치 시 json_ok=False"""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from prepare import compute_score

    prediction = {"wrong_key": [1, 2, 3]}
    actual = [1, 2, 3]
    score = compute_score(prediction, actual)
    assert score["json_ok"] is False


def test_print_score_line(capsys):
    """스코어 라인 출력 형식"""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from prepare import print_score_line

    results = [
        {"json_ok": True, "deferred": False, "set_match": 1.0, "correct_count": 3},
        {"json_ok": True, "deferred": False, "set_match": 0.333, "correct_count": 1},
        {"json_ok": False, "deferred": False, "set_match": 0.0, "correct_count": 0},
    ]
    print_score_line(results)
    output = capsys.readouterr().out
    assert "set_match=" in output
    assert "json_ok=" in output
    assert "coverage=" in output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/chsong/Developer/Personal/kra-analysis && uv run python3 -m pytest packages/scripts/autoresearch/tests/test_prepare.py -k "compute_score or print_score_line" -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

`prepare.py`에 추가:

```python
import argparse
import subprocess
import time

# ============================================================
# Constants
# ============================================================

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 4096
RACE_TIMEOUT = 120  # seconds
EXPERIMENT_TIMEOUT = 1800  # 30 minutes
DEFER_THRESHOLD = 0.3

# ============================================================
# LLM Callback
# ============================================================

def _call_llm(system: str, user: str) -> str:
    """Claude CLI 호출. system+user를 단일 prompt로 합쳐서 호출.

    --output-format json 사용 시 CLI는 {"type":"result","result":"..."}
    형태의 wrapper JSON을 반환하므로, result 필드를 추출해서 반환한다.
    (기존 ClaudeClient._extract_text()와 동일한 처리)
    """
    combined_prompt = f"[System]\n{system}\n\n[User]\n{user}"
    proc = subprocess.run(
        ["claude", "--model", MODEL, "--max-tokens", str(MAX_TOKENS),
         "--output-format", "json", "--max-turns", "1",
         "-p", combined_prompt],
        capture_output=True, text=True, timeout=RACE_TIMEOUT,
    )
    stdout = proc.stdout.strip()
    if not stdout:
        return ""
    # CLI wrapper JSON에서 실제 텍스트 추출
    try:
        wrapper = json.loads(stdout)
        if isinstance(wrapper, dict) and "result" in wrapper:
            return wrapper["result"]
    except json.JSONDecodeError:
        pass
    return stdout


# ============================================================
# Scoring
# ============================================================

def compute_score(prediction: dict, actual: list[int]) -> dict:
    """예측 결과를 채점"""
    # 스키마 검증
    if not isinstance(prediction, dict) or "predicted" not in prediction:
        return {"json_ok": False, "deferred": False, "set_match": 0.0, "correct_count": 0}

    predicted = prediction.get("predicted", [])
    confidence = prediction.get("confidence", 0.0)

    # confidence 정규화: 72 → 0.72 (LLM이 0~100 스케일로 반환하는 경우 대응)
    try:
        confidence = float(confidence)
        if confidence > 1.0:
            confidence = confidence / 100.0
    except (TypeError, ValueError):
        confidence = 0.0

    if not isinstance(predicted, list) or len(predicted) != 3:
        return {"json_ok": False, "deferred": False, "set_match": 0.0, "correct_count": 0}

    # defer 판정
    deferred = confidence < DEFER_THRESHOLD

    # set_match 계산
    sm = set_match_score(predicted, actual)
    correct = len(set(predicted[:3]) & set(actual[:3]))

    return {
        "json_ok": True,
        "deferred": deferred,
        "set_match": sm,
        "correct_count": correct,
    }


def print_score_line(results: list[dict]) -> None:
    """한 줄 스코어 출력"""
    total = len(results)
    if total == 0:
        print("No results")
        return

    json_ok_count = sum(1 for r in results if r["json_ok"])
    deferred_count = sum(1 for r in results if r["deferred"])
    valid = [r for r in results if r["json_ok"] and not r["deferred"]]

    sm = sum(r["set_match"] for r in valid) / len(valid) if valid else 0.0
    avg_correct = sum(r["correct_count"] for r in valid) / len(valid) if valid else 0.0
    json_ok_pct = json_ok_count / total * 100
    coverage_pct = (total - deferred_count) / total * 100

    print(
        f"set_match={sm:.3f} | avg_correct={avg_correct:.2f} | "
        f"json_ok={json_ok_pct:.0f}% | coverage={coverage_pct:.0f}% | "
        f"races={total}"
    )


# ============================================================
# Evaluate
# ============================================================

def load_snapshot(mode: str) -> tuple[list[dict], dict]:
    """snapshot과 answer_key 로드"""
    snapshot_path = SNAPSHOTS_DIR / f"{mode}.json"
    answer_key_path = SNAPSHOTS_DIR / "answer_key.json"

    with open(snapshot_path) as f:
        races = json.load(f)
    with open(answer_key_path) as f:
        answer_key = json.load(f)

    return races, answer_key.get(mode, {})


def evaluate(mode: str = "mini_val") -> None:
    """train.py의 predict()를 호출하여 평가"""
    # import guard 검사
    train_path = SCRIPT_DIR / "train.py"
    violations = check_train_imports(str(train_path))
    if violations:
        print(f"BLOCKED: train.py uses forbidden imports: {violations}")
        sys.exit(1)

    # train.py import
    from train import predict

    races, answer_key = load_snapshot(mode)
    print(f"Evaluating {len(races)} races ({mode})...")

    start = time.time()
    results = []
    for i, race in enumerate(races):
        race_id = race.get("race_id", "unknown")
        actual = answer_key.get(race_id, [])
        try:
            prediction = predict(race, call_llm=_call_llm)
            score = compute_score(prediction, actual)
        except Exception as e:
            print(f"  [{i+1}/{len(races)}] {race_id}: ERROR - {e}")
            score = {"json_ok": False, "deferred": False, "set_match": 0.0, "correct_count": 0}
        else:
            status = "DEFER" if score["deferred"] else f"{score['correct_count']}/3"
            print(f"  [{i+1}/{len(races)}] {race_id}: {status}")
        results.append(score)

        # wall-clock cap
        elapsed = time.time() - start
        if elapsed > EXPERIMENT_TIMEOUT:
            print(f"TIMEOUT: {elapsed:.0f}s > {EXPERIMENT_TIMEOUT}s")
            timed_out = True
            break
    else:
        timed_out = False

    elapsed = time.time() - start
    print(f"\nCompleted in {elapsed:.0f}s")
    print_score_line(results)

    # Hard gate 검사
    total = len(results)
    json_ok_pct = sum(1 for r in results if r["json_ok"]) / total * 100 if total else 0
    deferred_count = sum(1 for r in results if r["deferred"])
    coverage_pct = (total - deferred_count) / total * 100 if total else 0

    gates_passed = True
    if timed_out:
        print(f"HARD GATE FAIL: experiment timed out ({elapsed:.0f}s > {EXPERIMENT_TIMEOUT}s)")
        gates_passed = False
    if json_ok_pct < 90:
        print(f"HARD GATE FAIL: json_ok={json_ok_pct:.0f}% < 90%")
        gates_passed = False
    if coverage_pct < 80:
        print(f"HARD GATE FAIL: coverage={coverage_pct:.0f}% < 80%")
        gates_passed = False

    if gates_passed:
        print("All hard gates PASSED")
    sys.exit(0 if gates_passed else 1)


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="KRA Autoresearch Harness")
    parser.add_argument("--holdout", action="store_true", help="holdout 50경주 평가")
    parser.add_argument("--create-snapshot", action="store_true", help="snapshot 생성")
    parser.add_argument("--force-recreate", action="store_true", help="snapshot 재생성")
    args = parser.parse_args()

    if args.create_snapshot:
        create_snapshot(force=args.force_recreate)
    else:
        mode = "holdout" if args.holdout else "mini_val"
        evaluate(mode)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/chsong/Developer/Personal/kra-analysis && uv run python3 -m pytest packages/scripts/autoresearch/tests/test_prepare.py -k "compute_score or print_score_line" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/scripts/autoresearch/prepare.py packages/scripts/autoresearch/tests/test_prepare.py
git commit -m "feat(autoresearch): add evaluate harness, scoring, and CLI"
```

---

## Chunk 4: train.py + program.md

### Task 5: train.py 초기 시드 작성

**Files:**
- Create: `packages/scripts/autoresearch/train.py`
- Test: `packages/scripts/autoresearch/tests/test_train.py`

- [ ] **Step 1: Write the failing test**

```python
# packages/scripts/autoresearch/tests/test_train.py
"""train.py 단위 테스트"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_predict_returns_correct_schema():
    """predict()가 올바른 스키마를 반환하는지"""
    from train import predict

    race_data = {
        "race_info": {
            "rcDate": "20250101", "rcNo": "1", "meet": "서울",
            "rcDist": "1200", "track": "건조", "weather": "맑음",
            "budam": "별정A", "ageCond": "3세이상",
        },
        "horses": [
            {"chulNo": 1, "hrName": "테스트1", "winOdds": 3.0,
             "computed_features": {"odds_rank": 1}},
            {"chulNo": 2, "hrName": "테스트2", "winOdds": 5.0,
             "computed_features": {"odds_rank": 2}},
            {"chulNo": 3, "hrName": "테스트3", "winOdds": 8.0,
             "computed_features": {"odds_rank": 3}},
        ],
    }

    # mock call_llm
    def mock_llm(system: str, user: str) -> str:
        return '{"predicted": [1, 2, 3], "confidence": 0.7, "reasoning": "test"}'

    result = predict(race_data, call_llm=mock_llm)
    assert "predicted" in result
    assert "confidence" in result
    assert "reasoning" in result
    assert len(result["predicted"]) == 3


def test_parse_response_handles_json():
    """parse_response가 JSON을 올바르게 파싱하는지"""
    from train import parse_response

    raw = '{"predicted": [1, 5, 3], "confidence": 0.72, "reasoning": "test"}'
    result = parse_response(raw)
    assert result["predicted"] == [1, 5, 3]
    assert result["confidence"] == 0.72


def test_parse_response_handles_code_block():
    """parse_response가 코드블록 안의 JSON도 파싱하는지"""
    from train import parse_response

    raw = '```json\n{"predicted": [1, 5, 3], "confidence": 0.72, "reasoning": "test"}\n```'
    result = parse_response(raw)
    assert result["predicted"] == [1, 5, 3]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/chsong/Developer/Personal/kra-analysis && uv run python3 -m pytest packages/scripts/autoresearch/tests/test_train.py -v`
Expected: FAIL

- [ ] **Step 3: Write implementation**

`packages/scripts/autoresearch/train.py`:

```python
"""KRA 삼복연승 예측 전략 — 에이전트가 수정하는 유일한 파일

이 파일은 에이전트(Claude Code, Codex 등)가 자유롭게 수정합니다.
단, 다음 규칙을 지켜야 합니다:
  - DB 접근 금지 (import db_client 금지)
  - 파일 I/O 금지 (os, pathlib 등 금지)
  - predict(race_data, call_llm)의 시그니처 유지
  - 출력 스키마 유지: {"predicted": [...], "confidence": float, "reasoning": str}
"""

import json
import re

# ============================================================
# 1. 프롬프트 템플릿
# ============================================================

SYSTEM_PROMPT = """당신은 한국마사회(KRA) 경마 데이터 분석 전문가입니다.
주어진 경주 데이터를 분석하여 1-3위 말을 예측하세요.

분석 시 다음을 고려하세요:
1. 배당률(winOdds) - 낮을수록 인기마
2. 최근 성적과 승률 (computed_features의 horse_win_rate, jockey_win_rate)
3. 거리 적성과 컨디션
4. 부담중량과 마체중

반드시 JSON 형식으로만 응답하세요."""

USER_PROMPT_TEMPLATE = """## 경주 정보
{race_info}

## 출전마 데이터
{horse_data}

## 분석 요청
위 데이터를 기반으로 1~3위를 예측하세요.
반드시 아래 JSON 형식으로만 응답하세요:

{output_schema}"""

# ============================================================
# 2. 전략 함수
# ============================================================

OUTPUT_SCHEMA = {
    "predicted": [0, 0, 0],
    "confidence": 0.0,
    "reasoning": "",
}


def select_features(race_data: dict) -> dict:
    """race_data에서 프롬프트에 포함할 필드 선택"""
    return race_data


def format_race_info(features: dict) -> str:
    """경주 정보를 프롬프트용 텍스트로 포맷"""
    info = features.get("race_info", {})
    lines = []
    for key in ("rcDate", "rcNo", "meet", "rcDist", "track", "weather", "budam", "ageCond"):
        val = info.get(key, "")
        if val:
            lines.append(f"- {key}: {val}")
    return "\n".join(lines)


def format_horse_data(horses: list[dict]) -> str:
    """말 데이터를 프롬프트용 텍스트로 포맷"""
    lines = []
    for h in horses:
        chul = h.get("chulNo", "?")
        name = h.get("hrName", "?")
        odds = h.get("winOdds", "?")
        cf = h.get("computed_features", {})
        odds_rank = cf.get("odds_rank", "?")
        lines.append(f"  {chul}번 {name} | 배당={odds} (순위={odds_rank})")
    return "\n".join(lines)


def build_prompt(features: dict) -> tuple[str, str]:
    """프롬프트 조립"""
    race_info = format_race_info(features)
    horse_data = format_horse_data(features.get("horses", []))
    user = USER_PROMPT_TEMPLATE.format(
        race_info=race_info,
        horse_data=horse_data,
        output_schema=json.dumps(OUTPUT_SCHEMA, ensure_ascii=False, indent=2),
    )
    return SYSTEM_PROMPT, user


def parse_response(llm_output: str) -> dict:
    """LLM 응답을 파싱하여 표준 형식으로 변환"""
    text = llm_output.strip()

    # 코드블록 추출
    code_block = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if code_block:
        text = code_block.group(1)

    # JSON 파싱
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # JSON 부분만 추출 시도
        match = re.search(r'\{[^{}]*"predicted"[^{}]*\}', text)
        if match:
            data = json.loads(match.group(0))
        else:
            return {"predicted": [], "confidence": 0.0, "reasoning": "parse_error"}

    return {
        "predicted": data.get("predicted", []),
        "confidence": float(data.get("confidence", 0.0)),
        "reasoning": str(data.get("reasoning", "")),
    }


# ============================================================
# 3. 엔트리포인트
# ============================================================

def predict(race_data: dict, call_llm) -> dict:
    """prepare.py가 호출하는 유일한 인터페이스.

    Args:
        race_data: enriched 형식의 경주 데이터
        call_llm: (system: str, user: str) -> str 콜백

    Returns:
        {"predicted": [1, 5, 3], "confidence": 0.72, "reasoning": "..."}
    """
    features = select_features(race_data)
    system, user = build_prompt(features)
    response = call_llm(system, user)
    return parse_response(response)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/chsong/Developer/Personal/kra-analysis && uv run python3 -m pytest packages/scripts/autoresearch/tests/test_train.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/scripts/autoresearch/train.py packages/scripts/autoresearch/tests/test_train.py
git commit -m "feat(autoresearch): add initial train.py with prompt and strategy"
```

### Task 6: program.md 작성

**Files:**
- Create: `packages/scripts/autoresearch/program.md`

- [ ] **Step 1: Write program.md**

```markdown
# KRA Autoresearch Program

## Setup
1. Run tag 합의: `autoresearch/{tag}` (예: `autoresearch/mar15`)
2. 브랜치 생성: `git checkout -b autoresearch/{tag}`
3. 파일 읽기:
   - `prepare.py` — 고정. 수정 금지.
   - `train.py` — 수정 대상. 프롬프트와 전략 함수.
   - 이 파일(`program.md`) — 실험 프로토콜.
4. Snapshot 확인: `ls snapshots/` — mini_val.json, holdout.json, answer_key.json이 있어야 함
   - 없으면: `cd packages/scripts/autoresearch && uv run prepare.py --create-snapshot`

## Constraints
- `train.py`만 수정할 것
- DB 접근, 파일 I/O, 외부 import 금지 (os, pathlib, subprocess, requests 등)
- 출력 스키마 변경 금지: `{"predicted": [...], "confidence": float, "reasoning": str}`
- `predict(race_data, call_llm)` 시그니처 유지

## Protocol
1. **Baseline 실행**: `cd packages/scripts/autoresearch && uv run prepare.py`
   - 현재 점수 기록
2. **가설 수립**
   - 무엇을 바꿀지, 왜 나아질 것으로 예상하는지 명확히 기술
3. **train.py 수정**
4. **실행**: `cd packages/scripts/autoresearch && uv run prepare.py`
5. **판정**:
   - Hard gate 통과 + set_match 개선 → `git commit -m "experiment: {가설 요약} set_match={점수}"`
   - Hard gate 실패 또는 set_match 악화 → `git checkout -- train.py`
6. **5회 keep마다**: `uv run prepare.py --holdout`으로 과적합 검증
   - holdout에서 mini_val 대비 set_match가 5%p 이상 하락 시 경고 → 최근 keep revert 고려
7. **반복**

## Metrics
- 주 지표: `set_match` (0.0~1.0, 높을수록 좋음)
- 보조: `avg_correct` (0.0~3.0)
- Hard gate: `json_ok >= 90%`, `coverage >= 80%`
- 목표: `set_match >= 0.50`

## Tips
- 프롬프트의 분석 단계(analysis steps)를 체계화하면 효과적
- 말 데이터 중 `computed_features` (odds_rank, win_rates 등)를 적극 활용
- 너무 많은 정보는 오히려 방해 — 핵심 피처만 선별
- `confidence` < 0.3은 자동 defer 처리됨
- `prediction-template-v1.7.md`의 13단계 분석 프로토콜을 참고하면 좋음
- v5 모듈의 failure taxonomy, extended thinking 등 아이디어 차용 가능

## Data Schema
`race_data` dict에 포함된 주요 필드:

```
race_data = {
    "race_id": "...",
    "race_date": "YYYYMMDD",
    "meet": "서울|부산경남|제주",
    "race_info": {rcDate, rcNo, meet, rcDist, track, weather, budam, ageCond},
    "horses": [
        {
            "chulNo": int,
            "hrName": str,
            "winOdds": float,
            "plcOdds": float,
            "class_rank": str,     # 등급 (원래 "rank" → rename)
            "wgBudam": float,      # 부담중량
            "wgHr": str,           # 마체중
            "age": int,
            "sex": str,
            "hrDetail": {...},     # 마필 상세 (camelCase)
            "jkDetail": {...},     # 기수 상세
            "trDetail": {...},     # 조교사 상세
            "computed_features": {
                "odds_rank": int,
                "rating_rank": int,
                "burden_ratio": float,
                "horse_win_rate": float,
                "horse_place_rate": float,
                "jockey_win_rate": float,
                "jockey_place_rate": float,
                "trainer_win_rate": float,
                "rest_days": int,
                "rest_risk": "high|medium|low",
                "age_prime": bool,
            }
        }
    ]
}
```
```

- [ ] **Step 2: Commit**

```bash
git add packages/scripts/autoresearch/program.md
git commit -m "feat(autoresearch): add program.md agent instructions"
```

---

## Chunk 5: 통합 테스트 + 최종 검증

### Task 7: 통합 테스트 (mock LLM)

**Files:**
- Test: `packages/scripts/autoresearch/tests/test_prepare.py`

- [ ] **Step 1: Write integration test**

```python
# test_prepare.py에 추가
import tempfile
import os


def test_end_to_end_with_mock_llm(tmp_path):
    """mock LLM으로 전체 파이프라인 통합 테스트"""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from prepare import compute_score, print_score_line, set_match_score

    # 시뮬레이션: 5경주 평가
    races = [
        {"predicted": [1, 2, 3], "confidence": 0.8, "reasoning": "good"},  # 3/3
        {"predicted": [1, 4, 5], "confidence": 0.7, "reasoning": "ok"},    # 1/3
        {"predicted": [4, 5, 6], "confidence": 0.6, "reasoning": "bad"},   # 0/3
        {"predicted": [1, 2, 3], "confidence": 0.1, "reasoning": "defer"}, # deferred
        {"wrong": "schema"},                                                # json_ok fail
    ]
    actuals = [[1, 2, 3], [1, 2, 3], [1, 2, 3], [1, 2, 3], [1, 2, 3]]

    results = [compute_score(pred, act) for pred, act in zip(races, actuals)]

    # 검증
    assert results[0]["set_match"] == 1.0
    assert results[1]["correct_count"] == 1
    assert results[2]["correct_count"] == 0
    assert results[3]["deferred"] is True
    assert results[4]["json_ok"] is False

    # json_ok: 3/5 = 60% (< 90% gate)
    json_ok_count = sum(1 for r in results if r["json_ok"])
    assert json_ok_count == 4  # deferred도 json_ok=True
```

- [ ] **Step 2: Run test**

Run: `cd /Users/chsong/Developer/Personal/kra-analysis && uv run python3 -m pytest packages/scripts/autoresearch/tests/test_prepare.py::test_end_to_end_with_mock_llm -v`
Expected: PASS

- [ ] **Step 3: Run full test suite**

Run: `cd /Users/chsong/Developer/Personal/kra-analysis && uv run python3 -m pytest packages/scripts/autoresearch/tests/ -v`
Expected: All PASS

- [ ] **Step 4: Commit**

```bash
git add packages/scripts/autoresearch/tests/
git commit -m "test(autoresearch): add integration test with mock LLM"
```

### Task 8: snapshot 생성 실행 (실제 DB)

- [ ] **Step 1: snapshot 생성**

Run: `cd /Users/chsong/Developer/Personal/kra-analysis/packages/scripts/autoresearch && uv run prepare.py --create-snapshot`
Expected: `Found N races with results`, `mini_val: 20 races`, `holdout: 50 races`

- [ ] **Step 2: snapshot 파일 확인**

Run: `ls -la packages/scripts/autoresearch/snapshots/`
Expected: `mini_val.json`, `holdout.json`, `answer_key.json` 존재

- [ ] **Step 3: snapshot을 git에 커밋**

```bash
git add packages/scripts/autoresearch/snapshots/
git commit -m "data(autoresearch): add initial evaluation snapshots"
```

### Task 9: baseline 실행

- [ ] **Step 1: baseline 평가 실행**

Run: `cd /Users/chsong/Developer/Personal/kra-analysis/packages/scripts/autoresearch && uv run prepare.py`
Expected: 20경주 평가 후 스코어 라인 출력

- [ ] **Step 2: baseline 결과 기록**

baseline 점수를 program.md Tips 섹션이나 실험 기록에 메모.

- [ ] **Step 3: baseline 커밋**

```bash
cd /Users/chsong/Developer/Personal/kra-analysis
git add packages/scripts/autoresearch/
git commit -m "feat(autoresearch): complete initial setup with baseline"
```

---

## Summary

| Task | Description | Est. |
|------|-------------|------|
| 1 | db_client.find_races_with_results() | 3min |
| 2 | import guard | 3min |
| 3 | snapshot 생성 로직 | 5min |
| 4 | evaluate + CLI | 5min |
| 5 | train.py 초기 시드 | 5min |
| 6 | program.md | 2min |
| 7 | 통합 테스트 | 3min |
| 8 | snapshot 생성 실행 | 2min |
| 9 | baseline 실행 | 5min |
