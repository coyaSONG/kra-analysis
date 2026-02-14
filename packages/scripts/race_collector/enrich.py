"""
Enrich prerace JSON files with horse, jockey, and trainer details.

Uses asyncio.gather for parallel fetching with configurable concurrency.

Replaces enrich_race_data.js.
CLI: python3 enrich.py <file_or_date> [meet] [--concurrency N]
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from api_client import AsyncKRAClient, ensure_cache_dir

MEET_NAMES = {"1": "seoul", "2": "jeju", "3": "busan"}


async def enrich_race_data(input_path: str, client: AsyncKRAClient) -> dict:
    """Enrich a single prerace JSON file with detail data (async).

    Fetches horse, jockey, and trainer details in parallel using
    asyncio.gather, respecting the client's concurrency limit.
    """
    print(f"\nEnriching: {Path(input_path).name}")

    try:
        race_data = json.loads(Path(input_path).read_text(encoding="utf-8"))
        horses = race_data["response"]["body"]["items"]["item"]
        horse_array = horses if isinstance(horses, list) else [horses]

        print(f"  Horses: {len(horse_array)}")

        # Extract unique jockeys and trainers
        unique_jockeys: dict[str, str] = {}
        unique_trainers: dict[str, str] = {}
        for horse in horse_array:
            unique_jockeys[horse["jkNo"]] = horse["jkName"]
            unique_trainers[horse["trNo"]] = horse["trName"]

        print(f"  Unique jockeys: {len(unique_jockeys)}")
        print(f"  Unique trainers: {len(unique_trainers)}")

        # Fetch ALL details in parallel using asyncio.gather
        print("  Fetching all details in parallel...")

        # Horse details
        horse_tasks = [
            client.get_horse_detail(h["hrNo"], h["hrName"])
            for h in horse_array
        ]
        # Jockey details (unique only)
        jk_nos = list(unique_jockeys.keys())
        jockey_tasks = [
            client.get_jockey_detail(jk_no, unique_jockeys[jk_no])
            for jk_no in jk_nos
        ]
        # Trainer details (unique only)
        tr_nos = list(unique_trainers.keys())
        trainer_tasks = [
            client.get_trainer_detail(tr_no, unique_trainers[tr_no])
            for tr_no in tr_nos
        ]

        # Gather all at once
        all_results = await asyncio.gather(
            *horse_tasks, *jockey_tasks, *trainer_tasks,
            return_exceptions=True,
        )

        # Split results back
        n_horses = len(horse_tasks)
        n_jockeys = len(jockey_tasks)

        horse_details = all_results[:n_horses]
        jockey_results = all_results[n_horses : n_horses + n_jockeys]
        trainer_results = all_results[n_horses + n_jockeys :]

        # Attach horse details
        for horse, detail in zip(horse_array, horse_details):
            if isinstance(detail, dict):
                horse["hrDetail"] = detail

        # Build jockey/trainer lookup dicts
        jockey_details: dict[str, dict] = {}
        for jk_no, result in zip(jk_nos, jockey_results):
            if isinstance(result, dict):
                jockey_details[jk_no] = result

        trainer_details: dict[str, dict] = {}
        for tr_no, result in zip(tr_nos, trainer_results):
            if isinstance(result, dict):
                trainer_details[tr_no] = result

        # Attach jockey/trainer details to each horse
        for horse in horse_array:
            if horse["jkNo"] in jockey_details:
                horse["jkDetail"] = jockey_details[horse["jkNo"]]
            if horse["trNo"] in trainer_details:
                horse["trDetail"] = trainer_details[horse["trNo"]]

        # Save enriched data
        output_path = input_path.replace("_prerace.json", "_enriched.json")
        Path(output_path).write_text(
            json.dumps(race_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # Statistics
        enriched_horses = sum(1 for h in horse_array if "hrDetail" in h)
        enriched_jockeys = sum(1 for h in horse_array if "jkDetail" in h)
        enriched_trainers = sum(1 for h in horse_array if "trDetail" in h)

        print(f"  Enriched: {Path(output_path).name}")
        print(f"  - Horse info: {enriched_horses}/{len(horse_array)}")
        print(f"  - Jockey info: {enriched_jockeys}/{len(horse_array)}")
        print(f"  - Trainer info: {enriched_trainers}/{len(horse_array)}")

        return {
            "success": True,
            "stats": {
                "totalHorses": len(horse_array),
                "enrichedHorses": enriched_horses,
                "enrichedJockeys": enriched_jockeys,
                "enrichedTrainers": enriched_trainers,
            },
        }

    except Exception as e:
        print(f"  [ERROR] Enrichment failed: {e}")
        return {"success": False, "error": str(e)}


async def enrich_day_races(
    date_str: str, meet: str = "1", concurrency: int = 5
) -> None:
    """Enrich all prerace files for a given date and venue."""
    year = date_str[:4]
    month = date_str[4:6]
    meet_folder = MEET_NAMES.get(meet, f"meet{meet}")
    race_dir = Path(f"data/races/{year}/{month}/{date_str}/{meet_folder}")

    print(f"\n{'=' * 60}")
    print(f"  {date_str} {meet_folder} enrichment (concurrency={concurrency})")
    print(f"{'=' * 60}")

    try:
        prerace_files = sorted(race_dir.glob("*_prerace.json"))
        print(f"Found {len(prerace_files)} races")

        async with AsyncKRAClient(concurrency=concurrency) as client:
            results = []
            for file_path in prerace_files:
                result = await enrich_race_data(str(file_path), client)
                results.append({"file": file_path.name, **result})

        # Summary
        success_count = sum(1 for r in results if r.get("success"))
        print(f"\n{'=' * 60}")
        print(f"  Completed: {success_count}/{len(results)} races enriched")

    except FileNotFoundError:
        print(f"  [ERROR] Directory not found: {race_dir}")


async def enrich_single_file(input_path: str, concurrency: int = 5) -> None:
    """Enrich a single prerace JSON file."""
    async with AsyncKRAClient(concurrency=concurrency) as client:
        await enrich_race_data(input_path, client)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Enrich prerace data with horse/jockey/trainer details (async)"
    )
    parser.add_argument(
        "file_or_date",
        help="Path to prerace JSON file, or date in YYYYMMDD format",
    )
    parser.add_argument(
        "meet",
        nargs="?",
        default="1",
        help="Meet code: 1=seoul, 2=jeju, 3=busan (default: 1). "
        "Only used in date mode.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Max concurrent API requests (default: 5)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    ensure_cache_dir()

    if args.file_or_date.endswith(".json"):
        asyncio.run(enrich_single_file(args.file_or_date, args.concurrency))
    else:
        asyncio.run(
            enrich_day_races(args.file_or_date, args.meet, args.concurrency)
        )
