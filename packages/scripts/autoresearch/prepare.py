#!/usr/bin/env python3
"""KRA Autoresearch — 고정 평가 하네스

이 파일은 수정 금지. train.py만 에이전트가 수정합니다.
"""

import argparse
import ast
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# ============================================================
# 프로젝트 경로 설정
# ============================================================

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
SNAPSHOTS_DIR = SCRIPT_DIR / "snapshots"

sys.path.insert(0, str(PROJECT_ROOT / "packages" / "scripts"))

from evaluation.leakage_checks import FORBIDDEN_POST_RACE_FIELDS  # noqa: E402
from feature_engineering import compute_race_features  # noqa: E402
from shared.data_adapter import convert_basic_data_to_enriched_format  # noqa: E402
from shared.db_client import RaceDBClient  # noqa: E402

# ============================================================
# Import Guard
# ============================================================

FORBIDDEN_MODULES = {
    "db_client",
    "os",
    "pathlib",
    "subprocess",
    "shutil",
    "urllib",
    "requests",
    "httpx",
    "supabase",
}


def check_train_imports(filepath: str) -> list[str]:
    """train.py의 import문을 AST로 검사, 금지 모듈 사용 시 반환"""
    with open(filepath) as f:
        tree = ast.parse(f.read())
    violations: list[str] = []
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
    cleaned: dict[str, Any] = {}
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

        if len(races) < 700:
            print(f"ERROR: Need >= 700 races, got {len(races)}")
            sys.exit(1)

        # walk-forward split: [...][mini_val 200][holdout 500]
        holdout_races = races[-500:]
        mini_val_races = races[-700:-500]

        answer_key: dict[str, Any] = {"meta": {}, "mini_val": {}, "holdout": {}}
        snapshots: dict[str, list[dict]] = {"mini_val": [], "holdout": []}

        for mode, race_list in [
            ("mini_val", mini_val_races),
            ("holdout", holdout_races),
        ]:
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
        if mv_count < 150:
            print(
                f"ERROR: mini_val has only {mv_count} races (need >= 150). "
                f"Check DB for missing basic_data or failed conversions."
            )
            sys.exit(1)
        if ho_count < 400:
            print(
                f"ERROR: holdout has only {ho_count} races (need >= 400). "
                f"Check DB for missing basic_data or failed conversions."
            )
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


# ============================================================
# Constants
# ============================================================

MODEL = "sonnet"
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
    env = {**__import__("os").environ, "DISABLE_INTERLEAVED_THINKING": "true"}
    env.pop("CLAUDECODE", None)
    proc = subprocess.run(
        [
            "claude",
            "-p",
            combined_prompt,
            "--model",
            MODEL,
            "--output-format",
            "json",
            "--max-turns",
            "1",
        ],
        capture_output=True,
        text=True,
        timeout=RACE_TIMEOUT,
        env=env,
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
# Compute Score
# ============================================================


def compute_score(prediction: dict, actual: list[int]) -> dict:
    """예측 결과를 채점"""
    # 스키마 검증
    if not isinstance(prediction, dict) or "predicted" not in prediction:
        return {
            "json_ok": False,
            "deferred": False,
            "set_match": 0.0,
            "correct_count": 0,
        }

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
        return {
            "json_ok": False,
            "deferred": False,
            "set_match": 0.0,
            "correct_count": 0,
        }

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
    from train import predict  # noqa: E402

    races, answer_key = load_snapshot(mode)
    print(f"Evaluating {len(races)} races ({mode})...")

    start = time.time()
    results: list[dict] = []
    timed_out = False
    for i, race in enumerate(races):
        race_id = race.get("race_id", "unknown")
        actual = answer_key.get(race_id, [])
        try:
            prediction = predict(race, call_llm=_call_llm)
            score = compute_score(prediction, actual)
        except Exception as e:
            print(f"  [{i + 1}/{len(races)}] {race_id}: ERROR - {e}")
            score = {
                "json_ok": False,
                "deferred": False,
                "set_match": 0.0,
                "correct_count": 0,
            }
        else:
            status = "DEFER" if score["deferred"] else f"{score['correct_count']}/3"
            print(f"  [{i + 1}/{len(races)}] {race_id}: {status}")
        results.append(score)

        # wall-clock cap
        elapsed = time.time() - start
        if elapsed > EXPERIMENT_TIMEOUT:
            print(f"TIMEOUT: {elapsed:.0f}s > {EXPERIMENT_TIMEOUT}s")
            timed_out = True
            break

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
        print(
            f"HARD GATE FAIL: experiment timed out ({elapsed:.0f}s > {EXPERIMENT_TIMEOUT}s)"
        )
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
