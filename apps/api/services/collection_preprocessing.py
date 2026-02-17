"""Collection preprocessing helpers."""

from datetime import datetime
from typing import Any

import pandas as pd
import structlog

logger = structlog.get_logger()


def preprocess_data(raw_data: dict[str, Any]) -> dict[str, Any]:
    """Apply preprocessing rules to collected race data."""
    try:
        horses = raw_data.get("horses", [])

        # Remove scratched horses with invalid/zero odds.
        active_horses = []
        for horse in horses:
            try:
                win_odds = float(horse.get("win_odds", 0))
                if win_odds > 0:
                    active_horses.append(horse)
            except (ValueError, TypeError):
                # Skip horses with invalid win_odds
                pass

        # Aggregate baseline statistics for active horses.
        if active_horses:
            df = pd.DataFrame(active_horses)
            for col in ["weight", "rating", "win_odds"]:
                if col in df:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            avg_weight = df["weight"].mean() if "weight" in df else 0
            avg_rating = df["rating"].mean() if "rating" in df else 0
            avg_win_odds = df["win_odds"].mean() if "win_odds" in df else 0

            for horse in active_horses:
                if avg_weight > 0:
                    try:
                        horse["weight_ratio"] = float(horse.get("weight", 0)) / avg_weight
                    except (ValueError, TypeError):
                        horse["weight_ratio"] = 0
                if avg_rating > 0:
                    try:
                        horse["rating_ratio"] = float(horse.get("rating", 0)) / avg_rating
                    except (ValueError, TypeError):
                        horse["rating_ratio"] = 0
                if avg_win_odds > 0:
                    try:
                        horse["odds_ratio"] = float(horse.get("win_odds", 0)) / avg_win_odds
                    except (ValueError, TypeError):
                        horse["odds_ratio"] = 0

        return {
            **raw_data,
            "horses": active_horses,
            "excluded_horses": len(horses) - len(active_horses),
            "preprocessing_timestamp": datetime.utcnow().isoformat(),
            "statistics": {
                "avg_weight": avg_weight if "avg_weight" in locals() else 0,
                "avg_rating": avg_rating if "avg_rating" in locals() else 0,
                "avg_win_odds": avg_win_odds if "avg_win_odds" in locals() else 0,
            },
        }
    except Exception as exc:
        logger.error("Preprocessing logic failed", error=str(exc))
        raise
