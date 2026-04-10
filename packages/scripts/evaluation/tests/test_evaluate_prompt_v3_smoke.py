import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import evaluation.evaluate_prompt_v3 as eval_v3
from shared.prediction_input_schema import build_alternative_ranking_dataset_metadata


class FakeLoader:
    def __init__(self, db_client, with_past_stats=False):
        self.db_client = db_client
        self.with_past_stats = with_past_stats
        self.calls = []

    def find_test_races(self, limit=None):
        self.calls.append(("find", limit))
        return [{"race_id": "race-1"}]

    def load_race_data(self, race_info):
        self.calls.append(("load", race_info["race_id"]))
        return {"raceInfo": {"rcDate": "20240719"}, "horses": []}

    def build_v5_race_data(self, race_data):
        self.calls.append(("v5", tuple(race_data.keys())))
        return {"entries": [], "race_info": race_data.get("raceInfo", {})}

    def build_dataset_metadata(self, races, *, limit=None):
        self.calls.append(("dataset", limit, len(races)))
        return build_alternative_ranking_dataset_metadata(
            source="FakeLoader",
            dataset_name="smoke_test_dataset",
            requested_limit=limit,
            race_ids=[race["race_id"] for race in races],
            with_past_stats=self.with_past_stats,
        )


class FakeDBClient:
    def get_race_result(self, race_id):
        if race_id == "race-1":
            return [3, 1, 2]
        return []


class FakeClaudeClient:
    def predict_sync_compat(self, *args, **kwargs):
        return '{"selected_horses":[{"chulNo":1}],"confidence":50}'

    def predict_sync(self, *args, **kwargs):
        return '{"predicted":[1],"confidence":50}'


class FakeTracker:
    def start_run(self, *args, **kwargs):
        return None

    def log_params(self, *args, **kwargs):
        return None

    def log_metrics(self, *args, **kwargs):
        return None

    def log_artifact(self, *args, **kwargs):
        return None

    def end_run(self):
        return None


def test_prompt_evaluator_uses_new_loader(monkeypatch, tmp_path):
    monkeypatch.setattr(eval_v3, "RaceDBClient", FakeDBClient)
    monkeypatch.setattr(eval_v3, "ClaudeClient", FakeClaudeClient)
    monkeypatch.setattr(eval_v3, "ExperimentTracker", FakeTracker)
    monkeypatch.setattr(eval_v3, "RaceEvaluationDataLoader", FakeLoader)

    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("PROMPT", encoding="utf-8")

    evaluator = eval_v3.PromptEvaluatorV3(
        prompt_version="v-test",
        prompt_path=str(prompt_file),
    )

    races = evaluator.find_test_races(limit=2)
    assert races == [{"race_id": "race-1"}]

    race_data = evaluator.load_race_data({"race_id": "race-1"})
    assert race_data == {"raceInfo": {"rcDate": "20240719"}, "horses": []}

    converted = evaluator._convert_race_data_for_v5(race_data)
    assert converted == {"entries": [], "race_info": {"rcDate": "20240719"}}

    metadata = evaluator._build_dataset_metadata(races, limit=2)
    assert metadata["race_ids"] == ["race-1"]
    assert metadata["feature_schema_version"] == "alternative-ranking-input-v1"
    assert (
        metadata["input_schema_contract"]["schema_version"]
        == "alternative-ranking-input-v1"
    )


def test_calculate_reward_uses_unordered_top3_exact_match(monkeypatch, tmp_path):
    monkeypatch.setattr(eval_v3, "RaceDBClient", FakeDBClient)
    monkeypatch.setattr(eval_v3, "ClaudeClient", FakeClaudeClient)
    monkeypatch.setattr(eval_v3, "ExperimentTracker", FakeTracker)
    monkeypatch.setattr(eval_v3, "RaceEvaluationDataLoader", FakeLoader)

    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("PROMPT", encoding="utf-8")

    evaluator = eval_v3.PromptEvaluatorV3(
        prompt_version="v-test",
        prompt_path=str(prompt_file),
    )

    reward = evaluator.calculate_reward([1, 2, 4, 3], [3, 1, 2])

    assert reward["correct_count"] == 2
    assert reward["unordered_top3_exact_match"] is False
    assert reward["ordered_top3_exact_match"] is False
    assert reward["bonus"] == 0


def test_evaluate_all_parallel_counts_load_failures_in_holdout_hit_rate(
    monkeypatch, tmp_path
):
    class MixedLoader(FakeLoader):
        def find_test_races(self, limit=None):
            return [{"race_id": "race-1"}, {"race_id": "race-2"}]

        def load_race_data(self, race_info):
            if race_info["race_id"] == "race-1":
                return {"raceInfo": {"rcDate": "20240719"}, "horses": []}
            return None

    class ExactHitClaudeClient(FakeClaudeClient):
        def predict_sync_compat(self, *args, **kwargs):
            return '{"selected_horses":[{"chulNo":1},{"chulNo":2},{"chulNo":3}],"confidence":90}'

    monkeypatch.setattr(eval_v3, "RaceDBClient", FakeDBClient)
    monkeypatch.setattr(eval_v3, "ClaudeClient", ExactHitClaudeClient)
    monkeypatch.setattr(eval_v3, "ExperimentTracker", FakeTracker)
    monkeypatch.setattr(eval_v3, "RaceEvaluationDataLoader", MixedLoader)

    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("PROMPT", encoding="utf-8")

    evaluator = eval_v3.PromptEvaluatorV3(
        prompt_version="v-test",
        prompt_path=str(prompt_file),
        asof_check="off",
    )
    evaluator.results_dir = tmp_path

    report = evaluator.evaluate_all_parallel(test_limit=2, max_workers=1)

    assert report["total_races"] == 2
    assert report["successful_predictions"] == 1
    assert report["success_rate"] == 50.0
    assert report["metrics_v2"]["prediction_coverage"] == 0.5
    assert report["metrics_v2"]["expected_race_count"] == 2
    assert report["metrics_v2"]["predicted_race_count"] == 1
    assert report["metrics_v2"]["missing_prediction_count"] == 1
    assert report["metrics_v2"]["missing_prediction_race_ids"] == ["race-2"]
    assert report["metrics_v2"]["race_hit_count"] == 1
    assert report["metrics_v2"]["race_hit_rate"] == 0.5
    assert report["metrics_v2"]["ordered_race_hit_count"] == 0
    assert report["metrics_v2"]["ordered_race_hit_rate"] == 0.0
    assert len(report["detailed_results"]) == 2
    assert sorted(result["hit"] for result in report["detailed_results"]) == [
        False,
        True,
    ]
    assert sorted(
        result.get("ordered_hit", False) for result in report["detailed_results"]
    ) == [False, False]


def test_evaluate_all_parallel_reports_ordered_exact_hits(monkeypatch, tmp_path):
    class OrderedHitLoader(FakeLoader):
        def find_test_races(self, limit=None):
            return [{"race_id": "race-ordered"}]

    class OrderedHitDBClient(FakeDBClient):
        def get_race_result(self, race_id):
            return [1, 2, 3]

    class OrderedHitClaudeClient(FakeClaudeClient):
        def predict_sync_compat(self, *args, **kwargs):
            return '{"selected_horses":[{"chulNo":1},{"chulNo":2},{"chulNo":3}],"confidence":90}'

    monkeypatch.setattr(eval_v3, "RaceDBClient", OrderedHitDBClient)
    monkeypatch.setattr(eval_v3, "ClaudeClient", OrderedHitClaudeClient)
    monkeypatch.setattr(eval_v3, "ExperimentTracker", FakeTracker)
    monkeypatch.setattr(eval_v3, "RaceEvaluationDataLoader", OrderedHitLoader)

    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("PROMPT", encoding="utf-8")

    evaluator = eval_v3.PromptEvaluatorV3(
        prompt_version="v-test",
        prompt_path=str(prompt_file),
        asof_check="off",
    )
    evaluator.results_dir = tmp_path

    report = evaluator.evaluate_all_parallel(test_limit=1, max_workers=1)

    assert report["metrics_v2"]["race_hit_count"] == 1
    assert report["metrics_v2"]["race_hit_rate"] == 1.0
    assert report["metrics_v2"]["ordered_race_hit_count"] == 1
    assert report["metrics_v2"]["ordered_race_hit_rate"] == 1.0
    assert report["detailed_results"][0]["reward"]["ordered_top3_exact_match"] is True
    assert report["detailed_results"][0]["ordered_hit"] is True


def test_evaluate_all_parallel_includes_top3_and_fallback_metadata(
    monkeypatch, tmp_path
):
    class FallbackAwareLoader(FakeLoader):
        def find_test_races(self, limit=None):
            return [{"race_id": "race-fallback"}]

    class FallbackAwareDBClient(FakeDBClient):
        def get_race_result(self, race_id):
            return [4, 6, 1]

    class FallbackAwareClaudeClient(FakeClaudeClient):
        def predict_sync_compat(self, *args, **kwargs):
            return """```json
{
  "predictions": [
    {"chulNo": 4, "win_probability": 0.88},
    {"chulNo": 1, "win_probability": "NaN"}
  ],
  "fallback_ranking": [
    {"rank": 1, "chulNo": 6, "source": "alternative_ranking_v1"},
    {"rank": 2, "chulNo": 4, "source": "alternative_ranking_v1"},
    {"rank": 3, "chulNo": 1, "source": "alternative_ranking_v1"}
  ],
  "confidence": 75
}
```"""

    monkeypatch.setattr(eval_v3, "RaceDBClient", FallbackAwareDBClient)
    monkeypatch.setattr(eval_v3, "ClaudeClient", FallbackAwareClaudeClient)
    monkeypatch.setattr(eval_v3, "ExperimentTracker", FakeTracker)
    monkeypatch.setattr(eval_v3, "RaceEvaluationDataLoader", FallbackAwareLoader)

    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("PROMPT", encoding="utf-8")

    evaluator = eval_v3.PromptEvaluatorV3(
        prompt_version="v-test",
        prompt_path=str(prompt_file),
        asof_check="off",
    )
    evaluator.results_dir = tmp_path

    report = evaluator.evaluate_all_parallel(test_limit=1, max_workers=1)

    detailed = report["detailed_results"][0]
    assert detailed["top3"] == [4, 6, 1]
    assert detailed["predicted"] == [4, 6, 1]
    assert detailed["fallback_used"] is True
    assert detailed["fallback_reason_code"] == "PRIMARY_SCORES_PARTIAL"
    assert detailed["fallback_reason"]
    assert detailed["fallback_meta"]["applied"] is True
    assert detailed["prediction"]["top3"] == [4, 6, 1]
    assert detailed["prediction"]["fallback_used"] is True
    assert detailed["prediction"]["prediction_output_format"] == {
        "version": "unordered-top3-unique-v1",
        "predicted_count": 3,
        "is_unique": True,
    }


def test_evaluate_all_parallel_keeps_top3_when_score_calculation_fails(
    monkeypatch, tmp_path
):
    class ScoreErrorLoader(FakeLoader):
        def find_test_races(self, limit=None):
            return [{"race_id": "race-score-error"}]

    class ScoreErrorDBClient(FakeDBClient):
        def get_race_result(self, race_id):
            return [4, 6, 1]

    class ScoreErrorClaudeClient(FakeClaudeClient):
        def predict_sync_compat(self, *args, **kwargs):
            return """```json
{
  "selected_horses": [
    {"chulNo": 4},
    {"chulNo": 6},
    {"chulNo": 1}
  ],
  "predicted": [4, 6, 1],
  "confidence": 81,
  "reasoning": "primary top3"
}
```"""

    monkeypatch.setattr(eval_v3, "RaceDBClient", ScoreErrorDBClient)
    monkeypatch.setattr(eval_v3, "ClaudeClient", ScoreErrorClaudeClient)
    monkeypatch.setattr(eval_v3, "ExperimentTracker", FakeTracker)
    monkeypatch.setattr(eval_v3, "RaceEvaluationDataLoader", ScoreErrorLoader)

    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("PROMPT", encoding="utf-8")

    evaluator = eval_v3.PromptEvaluatorV3(
        prompt_version="v-test",
        prompt_path=str(prompt_file),
        asof_check="off",
    )
    evaluator.results_dir = tmp_path

    def broken_calculate_reward(predicted, actual):
        raise RuntimeError("score explosion")

    monkeypatch.setattr(evaluator, "calculate_reward", broken_calculate_reward)

    report = evaluator.evaluate_all_parallel(test_limit=1, max_workers=1)

    assert report["total_races"] == 1
    assert report["valid_predictions"] == 1
    detailed = report["detailed_results"][0]
    assert detailed["error_type"] == "score_error"
    assert detailed["reward"]["status"] == "score_fallback"
    assert detailed["reward"]["correct_count"] == 0
    assert detailed["top3"] == [4, 6, 1]
    assert detailed["predicted"] == [4, 6, 1]
    assert detailed["actual"] == [4, 6, 1]
    assert detailed["prediction"]["top3"] == [4, 6, 1]
    assert detailed["prediction"]["selected_horses"] == [
        {"chulNo": 4},
        {"chulNo": 6},
        {"chulNo": 1},
    ]
    assert detailed["prediction"]["prediction_output_format"] == {
        "version": "unordered-top3-unique-v1",
        "predicted_count": 3,
        "is_unique": True,
    }


def test_evaluate_all_parallel_applies_same_corrected_top3_to_prediction_and_reward(
    monkeypatch, tmp_path
):
    class CorrectedTop3Loader(FakeLoader):
        def find_test_races(self, limit=None):
            return [{"race_id": "race-corrected-top3"}]

        def load_race_data(self, race_info):
            assert race_info["race_id"] == "race-corrected-top3"
            return {
                "raceInfo": {"rcDate": "20240719"},
                "horses": [
                    {"chulNo": 2},
                    {"chulNo": 3},
                    {"chulNo": 4},
                    {"chulNo": 5},
                ],
            }

    class CorrectedTop3DBClient(FakeDBClient):
        def get_race_result(self, race_id):
            assert race_id == "race-corrected-top3"
            return [4, 5, 2]

    class CorrectedTop3ClaudeClient(FakeClaudeClient):
        def predict_sync_compat(self, *args, **kwargs):
            return """```json
{
  "selected_horses": [
    {"chulNo": 5},
    {"chulNo": 5},
    {"chulNo": 0},
    {"chulNo": 4},
    {"chulNo": 3},
    {"chulNo": 2},
    {"chulNo": "bad"}
  ],
  "predictions": [
    {"chulNo": 5, "win_probability": 0.95},
    {"chulNo": 4, "win_probability": 0.89},
    {"chulNo": 2, "win_probability": 0.84},
    {"chulNo": 3, "win_probability": 0.35}
  ],
  "confidence": 80
}
```"""

    monkeypatch.setattr(eval_v3, "RaceDBClient", CorrectedTop3DBClient)
    monkeypatch.setattr(eval_v3, "ClaudeClient", CorrectedTop3ClaudeClient)
    monkeypatch.setattr(eval_v3, "ExperimentTracker", FakeTracker)
    monkeypatch.setattr(eval_v3, "RaceEvaluationDataLoader", CorrectedTop3Loader)

    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("PROMPT", encoding="utf-8")

    evaluator = eval_v3.PromptEvaluatorV3(
        prompt_version="v-test",
        prompt_path=str(prompt_file),
        asof_check="off",
    )
    evaluator.results_dir = tmp_path

    report = evaluator.evaluate_all_parallel(test_limit=1, max_workers=1)

    detailed = report["detailed_results"][0]
    assert detailed["top3"] == [5, 4, 2]
    assert detailed["predicted"] == [5, 4, 2]
    assert detailed["prediction"]["predicted"] == [5, 4, 2]
    assert detailed["prediction"]["top3"] == [5, 4, 2]
    assert detailed["prediction"]["selected_horses"] == [
        {"chulNo": 5},
        {"chulNo": 4},
        {"chulNo": 2},
    ]
    assert detailed["prediction"]["prediction_validation"]["issue_codes"] == []
    assert detailed["prediction"]["prediction_correction"]["repair_action_codes"] == []
    assert detailed["prediction"]["prediction_validation"]["normalized_candidates"] == [
        {
            "rank": 1,
            "chulNo": 5,
            "score": 0.95,
            "hrName": None,
            "source_field": "selected_horses",
            "raw_index": 1,
        },
        {
            "rank": 2,
            "chulNo": 4,
            "score": 0.89,
            "hrName": None,
            "source_field": "selected_horses",
            "raw_index": 2,
        },
        {
            "rank": 3,
            "chulNo": 2,
            "score": 0.84,
            "hrName": None,
            "source_field": "selected_horses",
            "raw_index": 3,
        },
    ]
    assert detailed["actual"] == [4, 5, 2]
    assert detailed["reward"]["correct_count"] == 3
    assert detailed["hit"] is True
    assert detailed["ordered_hit"] is False
