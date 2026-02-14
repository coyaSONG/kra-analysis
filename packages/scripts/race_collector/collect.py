"""
Collect race data from KRA API214_1 and run smart preprocessing.

Replaces collect_and_preprocess.js.
CLI: python3 collect.py <date> [race_no] [--meet CODE]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from api_client import ensure_cache_dir, get_race_info

MEET_NAMES = {"1": "seoul", "2": "jeju", "3": "busan"}
MEET_LABELS = {"1": "Seoul", "2": "Jeju", "3": "Busan"}


def collect_and_preprocess_race(
    meet: str, rc_date: str, rc_no: int
) -> dict | None:
    """Collect a single race and run preprocessing."""
    print(f"\n{rc_no}R collecting... ", end="", flush=True)

    data = get_race_info(meet, rc_date, rc_no)

    if data is None:
        print("No data")
        return None

    items = data["response"]["body"]["items"]["item"]
    horses = items if isinstance(items, list) else [items]
    print(f"OK - {len(horses)} horses")

    # Save to temp file for preprocessing
    temp_path = Path(f"/tmp/temp_race_{meet}_{rc_date}_{rc_no}.json")
    temp_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Build output directory
    year = rc_date[:4]
    month = rc_date[4:6]
    meet_folder = MEET_NAMES.get(meet, f"meet{meet}")
    race_dir = Path(f"data/races/{year}/{month}/{rc_date}/{meet_folder}")
    race_dir.mkdir(parents=True, exist_ok=True)

    prerace_path = race_dir / f"race_{meet}_{rc_date}_{rc_no}_prerace.json"

    try:
        subprocess.run(
            [sys.executable, "race_collector/smart_preprocess_races.py", str(temp_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"  Preprocessed -> {prerace_path}")
    except subprocess.CalledProcessError as e:
        print(f"  [ERROR] Preprocessing failed: {e.stderr or e.stdout}")
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass

    return {
        "raceNo": rc_no,
        "horses": len(horses),
        "processed": True,
    }


def collect_and_preprocess_day(meet: str, rc_date: str) -> list[dict]:
    """Collect all races for a given day and venue, then preprocess."""
    print(f"\n{'=' * 60}")
    print(f"  {rc_date} {MEET_LABELS.get(meet, meet)} race data collection & preprocessing")
    print(f"{'=' * 60}")

    results: list[dict] = []

    for rc_no in range(1, 16):
        result = collect_and_preprocess_race(meet, rc_date, rc_no)

        if result is None:
            break

        results.append(result)

        # Rate limiting between API calls
        time.sleep(1.0)

    if results:
        print(f"\nCompleted: {len(results)} races collected and preprocessed")

    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect race data from KRA API and preprocess"
    )
    parser.add_argument(
        "date",
        nargs="?",
        default=None,
        help="Race date in YYYYMMDD format (default: today)",
    )
    parser.add_argument(
        "race_no",
        nargs="?",
        type=int,
        default=None,
        help="Specific race number (default: all 1-15)",
    )
    parser.add_argument(
        "--meet",
        default="1",
        help="Meet code: 1=seoul, 2=jeju, 3=busan (default: 1)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    ensure_cache_dir()

    rc_date = args.date or datetime.now().strftime("%Y%m%d")
    meet = args.meet

    print(f"Collecting: {rc_date} (meet: {meet})")

    if args.race_no is not None:
        # Collect specific race
        collect_and_preprocess_race(meet, rc_date, args.race_no)
    else:
        # Collect all races
        collect_and_preprocess_day(meet, rc_date)
