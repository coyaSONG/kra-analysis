from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    payload = json.loads(Path(".ralph/outputs/research_clean.json").read_text())
    integrity = payload.get("integrity", {})
    missing_features = integrity.get("all_missing_features") or []
    normalized_match_rate = float(integrity.get("normalized_first3_match_rate", 0.0))
    market_feature_count = int(payload.get("market_feature_count", 0))

    if missing_features:
        print(0)
        return

    if normalized_match_rate > 0.05:
        print(0)
        return

    if market_feature_count > 0:
        print(0)
        return

    summary = payload.get("summary") or {}
    print(
        summary.get(
            "overfit_safe_exact_rate",
            summary.get(
                "early_primary_exact_rate", summary.get("robust_exact_rate", 0)
            ),
        )
    )


if __name__ == "__main__":
    main()
