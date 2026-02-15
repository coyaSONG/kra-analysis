"""
Retry failed enrichment for enriched JSON files with missing details.

Replaces retry_failed_enrichment.js.
CLI: python3 retry_enrichment.py <file_or_date> [meet]
"""

import argparse
import json
import time
from pathlib import Path

from api_client import (
    ensure_cache_dir,
    get_horse_detail,
    get_jockey_detail,
    get_trainer_detail,
)

MEET_NAMES = {"1": "seoul", "2": "jeju", "3": "busan"}


def retry_failed_enrichment(file_path: str) -> dict:
    """Re-fetch missing horse/jockey/trainer details for an enriched file."""
    try:
        print(f"\nProcessing: {Path(file_path).name}")
        race_data = json.loads(Path(file_path).read_text(encoding="utf-8"))

        # Find items array (support multiple data structures)
        horse_array: list[dict] | None = None
        if (
            isinstance(race_data, dict)
            and race_data.get("response", {}).get("body", {}).get("items", {}).get("item")
        ):
            items = race_data["response"]["body"]["items"]["item"]
            horse_array = items if isinstance(items, list) else [items]
        elif isinstance(race_data, list):
            horse_array = race_data
        else:
            print("  [ERROR] Unknown data structure")
            return {"success": False, "error": "Unknown data structure"}

        # Filter valid horses (winOdds > 0)
        horses = [h for h in horse_array if h.get("winOdds", 0) > 0]
        print(f"  Horses: {len(horses)}")

        retry_count = 0

        # Retry missing horse details
        print("\n  Retrying missing horse details...")
        for horse in horses:
            if "hrDetail" not in horse:
                print(f"    Retry: {horse.get('hrName', '?')} ({horse.get('hrNo', '?')})")
                detail = get_horse_detail(horse["hrNo"], horse["hrName"])
                if detail:
                    horse["hrDetail"] = detail
                    retry_count += 1
                time.sleep(1.5)  # Longer delay for retries

        # Retry missing jockey details
        print("\n  Retrying missing jockey details...")
        for horse in horses:
            if "jkDetail" not in horse:
                print(f"    Retry: {horse.get('jkName', '?')} ({horse.get('jkNo', '?')})")
                detail = get_jockey_detail(horse["jkNo"], horse["jkName"])
                if detail:
                    horse["jkDetail"] = detail
                    retry_count += 1
                time.sleep(1.0)

        # Retry missing trainer details
        print("\n  Retrying missing trainer details...")
        for horse in horses:
            if "trDetail" not in horse:
                print(f"    Retry: {horse.get('trName', '?')} ({horse.get('trNo', '?')})")
                detail = get_trainer_detail(horse["trNo"], horse["trName"])
                if detail:
                    horse["trDetail"] = detail
                    retry_count += 1
                time.sleep(1.0)

        if retry_count > 0:
            # Overwrite file with updated data
            Path(file_path).write_text(
                json.dumps(race_data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            print(f"  {retry_count} details added")
        else:
            print("  No missing details to retry")

        # Statistics
        total_horses = len(horses)
        horse_details = sum(1 for h in horses if "hrDetail" in h)
        jockey_details = sum(1 for h in horses if "jkDetail" in h)
        trainer_details = sum(1 for h in horses if "trDetail" in h)

        print("\n  Final stats:")
        print(f"    - Horse info: {horse_details}/{total_horses}")
        print(f"    - Jockey info: {jockey_details}/{total_horses}")
        print(f"    - Trainer info: {trainer_details}/{total_horses}")

        return {"success": True, "retryCount": retry_count}

    except Exception as e:
        print(f"  [ERROR] Processing failed: {e}")
        return {"success": False, "error": str(e)}


def retry_day_races(date_str: str, meet: str = "1") -> None:
    """Retry enrichment for all enriched files of a given date and venue."""
    venue = MEET_NAMES.get(meet, f"meet{meet}")
    year = date_str[:4]
    month = date_str[4:6]
    race_dir = Path(f"data/races/{year}/{month}/{date_str}/{venue}")

    print(f"\n  {date_str} {venue} retry enrichment")
    print(f"  Directory: {race_dir}")

    try:
        enriched_files = sorted(race_dir.glob("*_enriched.json"))
        print(f"  Found {len(enriched_files)} enriched files")

        results = []
        for i, file_path in enumerate(enriched_files):
            result = retry_failed_enrichment(str(file_path))
            results.append({"file": file_path.name, **result})

            # Delay between files (not after the last one)
            if i < len(enriched_files) - 1:
                print("\n  Waiting 3s before next file...\n")
                time.sleep(3.0)

        # Summary
        success_count = sum(1 for r in results if r.get("success"))
        total_retries = sum(r.get("retryCount", 0) for r in results)
        print(f"\n{'=' * 60}")
        print(f"  Completed: {success_count}/{len(results)} files processed")
        print(f"  Total details added: {total_retries}")

    except FileNotFoundError:
        print(f"  [ERROR] Directory not found: {race_dir}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Retry failed enrichment for enriched race data files"
    )
    parser.add_argument(
        "file_or_date",
        help="Path to enriched JSON file, or date in YYYYMMDD format",
    )
    parser.add_argument(
        "meet",
        nargs="?",
        default="1",
        help="Meet code: 1=seoul, 2=jeju, 3=busan (default: 1). "
        "Only used in date mode.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    ensure_cache_dir()

    if args.file_or_date.endswith(".json"):
        retry_failed_enrichment(args.file_or_date)
    else:
        retry_day_races(args.file_or_date, args.meet)
