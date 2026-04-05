import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import evaluation.evaluate_prompt_v3 as eval_v3


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
        return {
            "source": "FakeLoader",
            "requested_limit": limit,
            "race_count": len(races),
            "race_ids": [race["race_id"] for race in races],
            "feature_schema_version": "fake-schema-v1",
            "with_past_stats": self.with_past_stats,
        }


class FakeDBClient:
    pass


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
    assert metadata["feature_schema_version"] == "fake-schema-v1"
