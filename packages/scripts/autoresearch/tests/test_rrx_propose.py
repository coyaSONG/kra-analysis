from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.prediction_input_schema import (
    ALTERNATIVE_RANKING_ALLOWED_FEATURES,  # noqa: E402
)

from autoresearch import rrx_propose  # noqa: E402


def test_mutate_features_drops_hold_fields_from_starting_config() -> None:
    mutated, notes = rrx_propose._mutate_features(
        ["rating", "winOdds", "plcOdds", "odds_rank"],
        rrx_propose.random.Random(7),
    )

    assert "rating" in mutated
    assert "winOdds" not in mutated
    assert "plcOdds" not in mutated
    assert "odds_rank" not in mutated
    assert set(mutated) <= set(ALTERNATIVE_RANKING_ALLOWED_FEATURES)
    assert notes


def test_apply_llm_mutation_rewrites_feature_list_to_operational_subset(
    monkeypatch,
) -> None:
    config = {
        "features": ["rating", "winOdds", "plcOdds_rr"],
        "model": {
            "positive_class_weight": 1.0,
            "params": {
                "max_depth": 6,
                "learning_rate": 0.05,
                "max_iter": 600,
                "min_samples_leaf": 30,
                "l2_regularization": 0.3,
            },
        },
    }

    class _Proposal:
        params = {}
        positive_class_weight = 1.0
        add_features = ["horse_win_rate"]
        drop_features = []
        rationale = "remove hold residues"

    monkeypatch.setattr(
        rrx_propose,
        "generate_llm_proposal",
        lambda **_kwargs: _Proposal(),
    )

    notes = rrx_propose._apply_llm_mutation(config, recent_runs=[])

    assert config["features"] == ["horse_win_rate", "rating"]
    assert set(config["features"]) <= set(ALTERNATIVE_RANKING_ALLOWED_FEATURES)
    assert all(
        feature not in config["features"] for feature in ("winOdds", "plcOdds_rr")
    )
    assert any(note.startswith("llm:rationale:") for note in notes)
