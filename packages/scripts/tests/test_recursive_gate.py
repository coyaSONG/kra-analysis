from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from prompt_improvement.recursive_prompt_improvement_v5 import should_promote_challenger


def test_should_promote_challenger_when_all_strict_conditions_pass() -> None:
    decision = should_promote_challenger(
        champion_metrics={'log_loss': 0.80, 'ece': 0.08, 'topk': {'top_3': 0.52}, 'roi': {'avg_roi': 0.01}},
        challenger_metrics={'log_loss': 0.75, 'ece': 0.07, 'topk': {'top_3': 0.54}, 'roi': {'avg_roi': 0.01}},
        leakage_passed=True,
        selection_gate='strict',
    )

    assert decision['promote'] is True
    assert decision['reason'] == 'gate_passed'


def test_should_not_promote_when_ece_worsens() -> None:
    decision = should_promote_challenger(
        champion_metrics={'log_loss': 0.80, 'ece': 0.08, 'topk': {'top_3': 0.52}, 'roi': {'avg_roi': 0.01}},
        challenger_metrics={'log_loss': 0.75, 'ece': 0.10, 'topk': {'top_3': 0.60}, 'roi': {'avg_roi': 0.05}},
        leakage_passed=True,
        selection_gate='strict',
    )

    assert decision['promote'] is False
    assert decision['reason'] == 'ece_regressed'
