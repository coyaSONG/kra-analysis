"""
Fetch race results and extract top-3 finishers.

Replaces get_race_result.js.
CLI: python3 result.py <date> <venue> <race_no>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from api_client import ensure_cache_dir, get_race_result

MEET_CODES = {
    "seoul": "1",
    "jeju": "2",
    "busan": "3",
    "1": "1",
    "2": "2",
    "3": "3",
}

VENUE_NAMES = {
    "1": "seoul",
    "2": "jeju",
    "3": "busan",
}


def get_meet_code(meet_name: str) -> str:
    """Convert meet name or code to API meet code."""
    return MEET_CODES.get(meet_name.lower(), "1")


def extract_top3(race_data: dict) -> list[int] | None:
    """Extract top-3 finisher numbers from race data."""
    try:
        items = race_data["response"]["body"]["items"]["item"]
        horses = items if isinstance(items, list) else [items]

        # Filter out scratched/excluded horses (winOdds == 0)
        valid_horses = [h for h in horses if h.get("winOdds", 0) > 0]

        # Filter horses with valid finish position (ord > 0)
        finished_horses = [h for h in valid_horses if h.get("ord") and h["ord"] > 0]

        if not finished_horses:
            print("Race not finished yet or no results available.")
            return None

        # Sort by finish position
        finished_horses.sort(key=lambda h: h["ord"])

        # Extract top-3 chulNo (entry numbers)
        return [h["chulNo"] for h in finished_horses[:3]]

    except Exception as e:
        print(f"[ERROR] Result extraction failed: {e}")
        return None


def save_result(top3: list[int], rc_date: str, meet: str, rc_no: str) -> str | None:
    """Save top-3 result to cache file."""
    try:
        cache_dir = Path("data/cache/results")
        cache_dir.mkdir(parents=True, exist_ok=True)

        filename = f"top3_{rc_date}_{meet}_{rc_no}.json"
        filepath = cache_dir / filename

        filepath.write_text(json.dumps(top3), encoding="utf-8")

        print(f"Result saved: {filepath}")
        print(f"Top 1-2-3: {top3}")

        return str(filepath)

    except Exception as e:
        print(f"[ERROR] File save failed: {e}")
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch race results and extract top-3")
    parser.add_argument("date", help="Race date in YYYYMMDD format")
    parser.add_argument("meet", help="Meet name or code (seoul/1, jeju/2, busan/3)")
    parser.add_argument("race_no", help="Race number")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    ensure_cache_dir()

    meet_code = get_meet_code(args.meet)

    print(f"\nRace result collection: {args.date} {args.meet} race {args.race_no}")
    print("-" * 50)

    # 1. Fetch race data
    race_data = get_race_result(meet_code, args.date, int(args.race_no))
    if not race_data:
        print("[ERROR] Could not fetch race data.")
        sys.exit(1)

    # 2. Extract top-3
    top3 = extract_top3(race_data)
    if not top3:
        print("[ERROR] Could not extract race results.")
        sys.exit(1)

    # 3. Save result
    saved_file = save_result(top3, args.date, args.meet, args.race_no)
    if not saved_file:
        print("[ERROR] Failed to save results.")
        sys.exit(1)

    print("Race result collection complete.")
