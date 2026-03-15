#!/usr/bin/env python3
"""KRA Autoresearch — 고정 평가 하네스

이 파일은 수정 금지. train.py만 에이전트가 수정합니다.
"""

import ast
import hashlib
import json
import sys
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

        if len(races) < 70:
            print(f"ERROR: Need >= 70 races, got {len(races)}")
            sys.exit(1)

        # walk-forward split: [...][mini_val 20][holdout 50]
        holdout_races = races[-50:]
        mini_val_races = races[-70:-50]

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
        if mv_count < 15:
            print(
                f"ERROR: mini_val has only {mv_count} races (need >= 15). "
                f"Check DB for missing basic_data or failed conversions."
            )
            sys.exit(1)
        if ho_count < 40:
            print(
                f"ERROR: holdout has only {ho_count} races (need >= 40). "
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
