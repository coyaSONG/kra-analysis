#!/usr/bin/env python3
"""
Hybrid ML+LLM predictor for horse racing top-3 prediction.

Combines LightGBM model probabilities with Claude's analytical reasoning
for more accurate and interpretable predictions.

Architecture:
1. Load enriched race data
2. Run feature engineering
3. Get ML model predictions (top-3 probabilities per horse)
4. Construct prompt with race data + ML probability rankings
5. Call Claude (Haiku/Sonnet) for reasoning-augmented prediction
6. Return unified prediction with ML scores + LLM reasoning

Usage:
    uv run python3 hybrid_predictor.py <prompt_file> <date_or_race_file> [--model haiku]
"""
from __future__ import annotations

import glob
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))

from feature_engineering import compute_race_features
from ml.predict import FEATURE_COLUMNS, _horse_to_feature_row, load_model
from shared.claude_client import ClaudeClient

import numpy as np

# Claude CLI 모델 이름 (구독 플랜 전용, --model 플래그에 전달)
MODEL_MAP = {
    "haiku": "haiku",
    "sonnet": "sonnet",
    "opus": "opus",
}

DEFAULT_ML_MODEL_PATH = Path("data/models/lgbm_v1.pkl")


# ---------------------------------------------------------------------------
# Data loading (reuses patterns from predict_only_test.py)
# ---------------------------------------------------------------------------


def load_race_data(file_path: str) -> dict | None:
    """Load enriched JSON and return parsed race data with computed features."""
    try:
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        if "response" not in data or "body" not in data["response"]:
            return None

        items = data["response"]["body"]["items"]["item"]
        if not isinstance(items, list):
            items = [items]

        horses = []
        for item in items:
            if item.get("winOdds", 999) == 0:
                continue  # 기권/제외마 필터링

            # wgHr 파싱: "470(+5)" -> 470
            wg_hr_str = item.get("wgHr", "")
            wg_hr_match = re.match(r"(\d+)", str(wg_hr_str))
            wg_hr_value = int(wg_hr_match.group(1)) if wg_hr_match else None

            horse: dict[str, Any] = {
                "chulNo": item["chulNo"],
                "hrName": item["hrName"],
                "hrNo": item.get("hrNo", ""),
                "jkName": item.get("jkName", ""),
                "jkNo": item.get("jkNo", ""),
                "trName": item.get("trName", ""),
                "trNo": item.get("trNo", ""),
                "winOdds": item["winOdds"],
                "plcOdds": item.get("plcOdds"),
                "wgBudam": item.get("wgBudam"),
                "wgHr": wg_hr_value,
                "age": item.get("age"),
                "sex": item.get("sex", ""),
                "rank": item.get("rank", ""),
                "rating": item.get("rating"),
                "rcDist": item.get("rcDist"),
                "ilsu": item.get("ilsu"),
            }

            if "hrDetail" in item:
                horse["hrDetail"] = item["hrDetail"]
            if "jkDetail" in item:
                horse["jkDetail"] = item["jkDetail"]
            if "trDetail" in item:
                horse["trDetail"] = item["trDetail"]

            horses.append(horse)

        # Compute features
        horses = compute_race_features(horses)

        first = items[0] if items else {}
        return {
            "horses": horses,
            "raceInfo": {
                "distance": first.get("rcDist"),
                "grade": first.get("rank", ""),
                "track": first.get("track", ""),
                "budam": first.get("budam", ""),
            },
        }

    except Exception as e:
        print(f"[ERROR] Loading race data: {e}")
        return None


# ---------------------------------------------------------------------------
# ML prediction
# ---------------------------------------------------------------------------


def get_ml_predictions(horses: list[dict], artifact: dict) -> list[dict]:
    """Run ML model predictions and return ranked results."""
    model = artifact["model"]
    feature_columns = artifact.get("feature_columns", FEATURE_COLUMNS)

    feature_rows = []
    for horse in horses:
        row = _horse_to_feature_row(horse)
        feature_vec = [row.get(col) for col in feature_columns]
        feature_rows.append(feature_vec)

    X = np.array(feature_rows, dtype=np.float64)

    # NaN handling
    nan_mask = np.isnan(X)
    if nan_mask.any():
        X[nan_mask] = -1

    probabilities = model.predict_proba(X)[:, 1]

    results = []
    for i, horse in enumerate(horses):
        results.append({
            "chulNo": int(horse.get("chulNo", 0)),
            "hrName": horse.get("hrName", ""),
            "winOdds": horse.get("winOdds", 0),
            "probability": float(probabilities[i]),
        })

    # Sort by probability descending
    results.sort(key=lambda x: x["probability"], reverse=True)

    for rank, r in enumerate(results, start=1):
        r["rank"] = rank

    return results


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


def build_hybrid_prompt(
    prompt_template: str,
    race_data: dict,
    ml_predictions: list[dict],
) -> str:
    """Construct prompt with race data and ML predictions injected."""
    # Format ML predictions as XML block
    ml_lines = []
    for pred in ml_predictions:
        ml_lines.append(
            f"  #{pred['chulNo']} {pred['hrName']} "
            f"- ML확률: {pred['probability']:.3f} "
            f"(순위 {pred['rank']}, 배당 {pred['winOdds']})"
        )
    ml_section = "<ml_predictions>\n" + "\n".join(ml_lines) + "\n</ml_predictions>"

    # Add ML predictions to race data for the prompt
    race_data_with_ml = {**race_data, "ml_predictions": ml_predictions}
    race_data_json = json.dumps(race_data_with_ml, ensure_ascii=False, indent=2)

    # Inject into prompt template
    if "{{RACE_DATA}}" in prompt_template:
        prompt = prompt_template.replace("{{RACE_DATA}}", race_data_json)
    else:
        prompt = f"{prompt_template}\n\n<race_data>\n{race_data_json}\n</race_data>"

    # Append ML predictions section
    prompt += f"\n\n{ml_section}"

    # Append instruction for JSON output
    prompt += (
        "\n\nIMPORTANT: You must act as a prediction API. "
        "Analyze the race data AND the ML model predictions provided above. "
        "The ML model provides probability-based rankings - use them as one input "
        "alongside your own analysis. "
        "Output ONLY the JSON object as specified in <output_format>. "
        "Do not output any markdown code block markers, introductory text, "
        "or explanations. Just the raw JSON string."
    )

    return prompt


# ---------------------------------------------------------------------------
# LLM prediction
# ---------------------------------------------------------------------------


def run_llm_prediction(
    prompt: str,
    client: ClaudeClient,
    model_name: str = "sonnet",
) -> dict | None:
    """Call Claude and parse the prediction response."""
    claude_model = MODEL_MAP.get(model_name, MODEL_MAP["sonnet"])

    start_time = time.time()
    output = client.predict_sync(prompt, model=claude_model)
    elapsed = time.time() - start_time

    if output is None:
        print("[ERROR] Claude API call failed or timed out")
        return None

    # Parse JSON from response
    parsed = ClaudeClient.parse_json(output)
    if parsed is None:
        # Fallback: try regex extraction
        json_match = re.search(r"(\{.*\})", output, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

    if parsed is None:
        print("[ERROR] Could not parse JSON from Claude response")
        return None

    # Extract predicted top-3
    predicted = parsed.get(
        "predicted",
        parsed.get("trifecta_picks", {}).get("primary", []),
    )

    return {
        "predicted": predicted,
        "confidence": parsed.get("trifecta_picks", {}).get("confidence", 0),
        "reasoning": parsed.get("analysis_summary", ""),
        "execution_time": elapsed,
        "claude_model": claude_model,
    }


# ---------------------------------------------------------------------------
# Main hybrid prediction
# ---------------------------------------------------------------------------


def hybrid_predict(
    prompt_path: str,
    race_file: str,
    ml_model_path: Path = DEFAULT_ML_MODEL_PATH,
    claude_model: str = "sonnet",
) -> dict | None:
    """Run hybrid ML+LLM prediction on a single race file.

    Returns:
        dict with ml_predictions, llm_prediction, and combined results.
    """
    # 1. Load prompt template
    prompt_template = Path(prompt_path).read_text(encoding="utf-8")

    # 2. Load race data
    race_data = load_race_data(race_file)
    if race_data is None:
        print(f"[ERROR] Could not load race data from {race_file}")
        return None

    n_horses = len(race_data["horses"])
    print(f"  Horses: {n_horses}")

    # 3. ML prediction
    if ml_model_path.exists():
        artifact = load_model(ml_model_path)
        ml_predictions = get_ml_predictions(race_data["horses"], artifact)
        ml_top3 = [p["chulNo"] for p in ml_predictions[:3]]
        print(f"  ML Top-3: {ml_top3}")
    else:
        print(f"  [WARN] ML model not found at {ml_model_path}, skipping ML predictions")
        ml_predictions = []
        ml_top3 = []

    # 4. Build prompt with ML predictions
    prompt = build_hybrid_prompt(prompt_template, race_data, ml_predictions)

    # 5. LLM prediction
    client = ClaudeClient()
    llm_result = run_llm_prediction(prompt, client, claude_model)

    if llm_result is None:
        # Fall back to ML-only prediction
        return {
            "source": "ml_only",
            "ml_predictions": ml_predictions,
            "ml_top3": ml_top3,
            "llm_prediction": None,
            "predicted": ml_top3,
        }

    llm_top3 = llm_result.get("predicted", [])
    print(f"  LLM Top-3: {llm_top3}")
    print(f"  LLM time: {llm_result['execution_time']:.1f}s ({llm_result['claude_model']})")

    return {
        "source": "hybrid",
        "ml_predictions": ml_predictions,
        "ml_top3": ml_top3,
        "llm_prediction": llm_result,
        "llm_top3": llm_top3,
        "predicted": llm_top3,  # Use LLM prediction (ML-informed) as primary
        "confidence": llm_result.get("confidence", 0),
        "reasoning": llm_result.get("reasoning", ""),
    }


def find_enriched_files(date_filter: str | None = None) -> list[dict]:
    """Find enriched JSON files matching the date filter."""
    if date_filter and date_filter != "all":
        if date_filter.endswith(".json"):
            # Direct file path
            p = Path(date_filter)
            return [{"file_path": p, "race_id": p.stem}] if p.exists() else []
        pattern = f"data/races/*/*/{date_filter}/*/*_enriched.json"
    else:
        pattern = "data/races/*/*/*/*/*_enriched.json"

    files = sorted(glob.glob(pattern))
    results = []
    for f in files:
        path = Path(f)
        parts = path.name.replace("_enriched.json", "").split("_")
        if len(parts) >= 4:
            results.append({
                "file_path": path,
                "race_id": f"{parts[1]}_{parts[2]}_{parts[3]}",
                "race_date": parts[2],
                "race_no": parts[3],
                "venue": path.parent.name,
            })
    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Hybrid ML+LLM horse racing predictor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Predict a specific race file
  uv run python3 hybrid_predictor.py packages/prompts/prediction-template-v1.7.md \\
      data/races/2025/06/20250608/seoul/race_1_20250608_1_enriched.json

  # Predict all races for a date
  uv run python3 hybrid_predictor.py packages/prompts/prediction-template-v1.7.md 20250608

  # Use Haiku for lower cost
  uv run python3 hybrid_predictor.py packages/prompts/base-prompt-v1.5.md 20250608 --model haiku
        """,
    )
    parser.add_argument("prompt_file", help="Path to prompt template file")
    parser.add_argument(
        "date_or_file",
        help="Date (YYYYMMDD), 'all', or path to enriched JSON file",
    )
    parser.add_argument(
        "--model",
        default="sonnet",
        choices=["haiku", "sonnet", "opus"],
        help="Claude model to use (default: sonnet)",
    )
    parser.add_argument(
        "--ml-model",
        type=Path,
        default=DEFAULT_ML_MODEL_PATH,
        help=f"Path to trained ML model (default: {DEFAULT_ML_MODEL_PATH})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of races to predict",
    )
    args = parser.parse_args()

    # Validate prompt file
    if not Path(args.prompt_file).exists():
        print(f"[ERROR] Prompt file not found: {args.prompt_file}")
        sys.exit(1)

    # Find race files
    race_files = find_enriched_files(args.date_or_file)
    if not race_files:
        print(f"[ERROR] No enriched files found for: {args.date_or_file}")
        sys.exit(1)

    if args.limit:
        race_files = race_files[: args.limit]

    print(f"Hybrid Predictor: {len(race_files)} race(s)")
    print(f"  Model: {args.model} | ML: {args.ml_model}")
    print("=" * 60)

    all_results = []

    for rf in race_files:
        race_id = rf.get("race_id", rf["file_path"].stem)
        print(f"\nRace: {race_id}")

        result = hybrid_predict(
            prompt_path=args.prompt_file,
            race_file=str(rf["file_path"]),
            ml_model_path=args.ml_model,
            claude_model=args.model,
        )

        if result:
            all_results.append({"race_id": race_id, **result})
            predicted = result.get("predicted", [])
            source = result.get("source", "unknown")
            print(f"  Prediction ({source}): {predicted}")
        else:
            print("  [SKIP] No prediction")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Completed: {len(all_results)}/{len(race_files)} races predicted")

    if all_results:
        # Save results
        output_dir = Path("data/hybrid_predictions")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"hybrid_{timestamp}.json"

        # Sanitize for JSON (remove non-serializable objects)
        serializable = json.loads(json.dumps(all_results, default=str))
        output_file.write_text(
            json.dumps(serializable, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Results saved: {output_file}")


if __name__ == "__main__":
    main()
