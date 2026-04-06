from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.append(str(SCRIPT_ROOT))

from shared.llm_client import CodexClient, GeminiClient, LLMClient  # noqa: E402


@dataclass
class LLMProposal:
    params: dict
    positive_class_weight: float | None
    add_features: list[str]
    drop_features: list[str]
    rationale: str
    raw_text: str


def _get_client(name: str) -> LLMClient:
    normalized = (name or "codex").strip().lower()
    if normalized == "codex":
        return CodexClient(max_concurrency=1)
    if normalized == "gemini":
        return GeminiClient(max_concurrency=1)
    raise ValueError(f"Unsupported proposer client: {name}")


def _build_prompt(
    *,
    config: dict,
    allowed_optional_features: list[str],
    bundles: dict[str, list[str]],
    recent_runs: list[dict],
) -> str:
    features = config.get("features") or []
    params = ((config.get("model") or {}).get("params")) or {}
    positive_weight = (config.get("model") or {}).get("positive_class_weight")

    recent_summary = [
        {
            "runId": item.get("runId"),
            "value": item.get("value"),
            "mutation": item.get("mutation"),
        }
        for item in recent_runs
    ]

    prompt_payload = {
        "goal": "Improve leakage-free early prediction exact 3-of-3 metric.",
        "rules": [
            "Return JSON only. No markdown.",
            "Do not introduce market features or post-race features.",
            "Use at most 4 add_features and at most 3 drop_features.",
            "Do not propose unknown features.",
            "Keep changes bounded to HGB params, positive_class_weight, and feature toggles.",
            "Prefer non-obvious combinations that differ from recent rejected mutations.",
        ],
        "current": {
            "model_kind": (config.get("model") or {}).get("kind"),
            "params": params,
            "positive_class_weight": positive_weight,
            "features": features,
        },
        "allowed_optional_features": allowed_optional_features,
        "feature_bundles": bundles,
        "recent_rejected_candidates": recent_summary,
        "required_output_schema": {
            "params": {
                "max_depth": "one of [4,5,6,7,8,null]",
                "learning_rate": "one of [0.03,0.04,0.05,0.06,0.08]",
                "max_iter": "one of [400,500,600,700,800]",
                "min_samples_leaf": "one of [15,20,25,30,35,40]",
                "l2_regularization": "one of [0.2,0.3,0.4,0.5,0.6,0.8]",
            },
            "positive_class_weight": "one of [0.9,0.95,1.0,1.05,1.1,1.15] or null",
            "add_features": ["feature_a"],
            "drop_features": ["feature_b"],
            "rationale": "one short sentence",
        },
    }
    return json.dumps(prompt_payload, ensure_ascii=False, indent=2)


def _coerce_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def generate_llm_proposal(
    *,
    config: dict,
    allowed_optional_features: list[str],
    bundles: dict[str, list[str]],
    recent_runs: list[dict],
) -> LLMProposal:
    provider = os.environ.get("RRX_LLM_CLIENT", "codex")
    timeout_seconds = float(os.environ.get("RRX_LLM_TIMEOUT", "180"))
    client = _get_client(provider)
    prompt = _build_prompt(
        config=config,
        allowed_optional_features=allowed_optional_features,
        bundles=bundles,
        recent_runs=recent_runs,
    )
    response = client.predict_sync(prompt, timeout=timeout_seconds)
    if not response.success or not response.text:
        raise RuntimeError(response.error or "LLM proposer returned empty response")

    payload = client.parse_json(response.text)
    if not isinstance(payload, dict):
        raise RuntimeError("LLM proposer did not return parseable JSON")

    proposal = LLMProposal(
        params=payload.get("params") or {},
        positive_class_weight=payload.get("positive_class_weight"),
        add_features=_coerce_list(payload.get("add_features")),
        drop_features=_coerce_list(payload.get("drop_features")),
        rationale=str(payload.get("rationale") or "").strip(),
        raw_text=response.text,
    )

    allowed = set(allowed_optional_features)
    proposal.add_features = [
        feature for feature in proposal.add_features if feature in allowed
    ]
    proposal.drop_features = [
        feature for feature in proposal.drop_features if feature in allowed
    ]
    return proposal
