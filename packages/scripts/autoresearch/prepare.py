#!/usr/bin/env python3
"""KRA Autoresearch — 고정 평가 하네스

이 파일은 수정 금지. train.py만 에이전트가 수정합니다.
"""

import argparse
import ast
import json
import math
import subprocess
import sys
import time
from pathlib import Path

# ============================================================
# 프로젝트 경로 설정
# ============================================================

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
SNAPSHOTS_DIR = SCRIPT_DIR / "snapshots"
SNAPSHOT_DATASETS = ("mini_val", "holdout")

sys.path.insert(0, str(PROJECT_ROOT / "packages" / "scripts"))

try:
    import offline_evaluation_dataset_job as _offline_dataset_job  # noqa: E402
except (
    ModuleNotFoundError
):  # pragma: no cover - import path differs between script/test contexts
    from autoresearch import (
        offline_evaluation_dataset_job as _offline_dataset_job,  # noqa: E402
    )
from shared.model_score_status_schema import (  # noqa: E402
    STATUS_CODES,
    STATUS_SPEC_BY_CODE,
    ScoreComputationResult,
)

_build_snapshot_bundle_impl = _offline_dataset_job.build_snapshot_bundle
_build_snapshot_race_data = _offline_dataset_job.build_snapshot_race_data
_check_snapshot_reproducibility_impl = (
    _offline_dataset_job.check_snapshot_reproducibility
)
create_snapshot = _offline_dataset_job.create_offline_evaluation_dataset
strip_forbidden_fields = _offline_dataset_job.strip_forbidden_fields

# ============================================================
# Import Guard
# ============================================================

FORBIDDEN_MODULES = {
    "db_client",
    "os",
    "pathlib",
    "subprocess",
    "shutil",
    "urllib",
    "requests",
    "httpx",
    "supabase",
}


def check_train_imports(filepath: str) -> list[str]:
    """train.py의 import문을 AST로 검사, 금지 모듈 사용 시 반환"""
    with open(filepath) as f:
        tree = ast.parse(f.read())
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mod = alias.name.split(".")[0]
                if mod in FORBIDDEN_MODULES:
                    violations.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mod = node.module.split(".")[0]
            if mod in FORBIDDEN_MODULES:
                violations.append(node.module)
    return violations


# ============================================================
# Scoring
# ============================================================


def set_match_score(predicted: list[int], actual: list[int]) -> float:
    """set intersection score: len(pred[:3] & actual[:3]) / 3"""
    pred_set = set(predicted[:3])
    actual_set = set(actual[:3])
    if not actual_set:
        return 0.0
    return len(pred_set & actual_set) / 3


# ============================================================
# Snapshot Compatibility
# ============================================================


class _InlineSnapshotQueryPort:
    """prepare.py 내부 호환용 in-memory query port."""

    def __init__(self, race_snapshots: list[object]):
        self._race_snapshots = list(race_snapshots)
        self._snapshot_by_id = {
            snapshot.race_id: snapshot
            for snapshot in self._race_snapshots
            if hasattr(snapshot, "race_id")
        }

    def find_race_snapshots(
        self,
        date_filter: str | None = None,
        limit: int | None = None,
    ) -> list[object]:
        snapshots = self._race_snapshots
        if date_filter:
            snapshots = [
                snapshot
                for snapshot in snapshots
                if hasattr(snapshot, "race_date") and snapshot.race_date == date_filter
            ]
        if limit is not None:
            snapshots = snapshots[:limit]
        return list(snapshots)

    def load_race_basic_data(self, race_id: str, *, lookup) -> dict | None:
        snapshot = self._snapshot_by_id.get(race_id)
        if snapshot is None:
            return None
        if not hasattr(lookup, "race_id") or lookup.race_id != race_id:
            lookup_race_id = lookup.race_id if hasattr(lookup, "race_id") else None
            raise ValueError(
                f"lookup.race_id {lookup_race_id!r} does not match {race_id!r}"
            )
        return snapshot.basic_data if hasattr(snapshot, "basic_data") else None

    def close(self) -> None:
        return None


def _build_snapshot_bundle(
    race_snapshots: list[object],
    *,
    manifest_created_at=None,
    holdout_minimum_race_count: int = 50,
    mini_val_minimum_race_count: int = 20,
) -> dict:
    query_port = _InlineSnapshotQueryPort(race_snapshots)
    return _build_snapshot_bundle_impl(
        race_snapshots,
        query_port=query_port,
        manifest_created_at=manifest_created_at,
        holdout_minimum_race_count=holdout_minimum_race_count,
        mini_val_minimum_race_count=mini_val_minimum_race_count,
    )


def check_snapshot_reproducibility(
    race_snapshots: list[object],
    *,
    manifest_created_at=None,
    holdout_minimum_race_count: int = 50,
    mini_val_minimum_race_count: int = 20,
    reference_bundle: dict | None = None,
) -> dict:
    query_port = _InlineSnapshotQueryPort(race_snapshots)
    return _check_snapshot_reproducibility_impl(
        race_snapshots,
        query_port=query_port,
        manifest_created_at=manifest_created_at,
        holdout_minimum_race_count=holdout_minimum_race_count,
        mini_val_minimum_race_count=mini_val_minimum_race_count,
        reference_bundle=reference_bundle,
    )


# ============================================================
# Constants
# ============================================================

MODEL = "sonnet"
RACE_TIMEOUT = 120  # seconds
EXPERIMENT_TIMEOUT = 1800  # 30 minutes
DEFER_THRESHOLD = 0.3

# ============================================================
# LLM Callback
# ============================================================


def _call_llm(system: str, user: str) -> str:
    """Claude CLI 호출. system+user를 단일 prompt로 합쳐서 호출.

    --output-format json 사용 시 CLI는 {"type":"result","result":"..."}
    형태의 wrapper JSON을 반환하므로, result 필드를 추출해서 반환한다.
    (기존 ClaudeClient._extract_text()와 동일한 처리)
    """
    combined_prompt = f"[System]\n{system}\n\n[User]\n{user}"
    env = {**__import__("os").environ, "DISABLE_INTERLEAVED_THINKING": "true"}
    env.pop("CLAUDECODE", None)
    proc = subprocess.run(
        [
            "claude",
            "-p",
            combined_prompt,
            "--model",
            MODEL,
            "--output-format",
            "json",
            "--max-turns",
            "1",
        ],
        capture_output=True,
        text=True,
        timeout=RACE_TIMEOUT,
        env=env,
    )
    stdout = proc.stdout.strip()
    if not stdout:
        return ""
    # CLI wrapper JSON에서 실제 텍스트 추출
    try:
        wrapper = json.loads(stdout)
        if isinstance(wrapper, dict) and "result" in wrapper:
            return wrapper["result"]
    except json.JSONDecodeError:
        pass
    return stdout


# ============================================================
# Compute Score
# ============================================================


_STATUS_CODE_SET = frozenset(STATUS_CODES)
_STATUS_FAIL_ACTUAL_TOP3_MISSING = "FAIL_ACTUAL_TOP3_MISSING"
_STATUS_FAIL_ACTUAL_TOP3_INVALID = "FAIL_ACTUAL_TOP3_INVALID"
_STATUS_FAIL_PREDICTION_PAYLOAD_MISSING = "FAIL_PREDICTION_PAYLOAD_MISSING"
_STATUS_MISSING_PREDICTED_TOP3 = "MISSING_PREDICTED_TOP3"
_STATUS_FAIL_PREDICTED_TOP3_INVALID = "FAIL_PREDICTED_TOP3_INVALID"
_STATUS_MISSING_CONFIDENCE = "MISSING_CONFIDENCE"
_STATUS_FAIL_CONFIDENCE_INVALID = "FAIL_CONFIDENCE_INVALID"
_STATUS_DEFERRED_LOW_CONFIDENCE = "DEFERRED_LOW_CONFIDENCE"
_STATUS_SCORED_OK = "SCORED_OK"
_MISSING = object()


def _score_result(
    status_code: str,
    *,
    normalized_confidence: float | None = None,
    set_match: float = 0.0,
    correct_count: int = 0,
) -> dict:
    if status_code not in _STATUS_CODE_SET:
        raise ValueError(f"Unknown score status_code: {status_code}")
    return ScoreComputationResult(
        race_status=STATUS_SPEC_BY_CODE[status_code],
        normalized_confidence=normalized_confidence,
        set_match=set_match,
        correct_count=correct_count,
    ).to_dict()


def _empty_score(status_code: str) -> dict:
    return _score_result(status_code)


def _normalize_top3_numbers(value: object) -> list[int] | None:
    if not isinstance(value, list) or len(value) != 3:
        return None

    normalized: list[int] = []
    for item in value:
        try:
            number = int(item)
        except (TypeError, ValueError):
            return None
        if number <= 0:
            return None
        normalized.append(number)

    if len(set(normalized)) != 3:
        return None
    return normalized


def _normalize_confidence(value: object) -> float | None:
    if value in (_MISSING, None, ""):
        return None

    try:
        normalized = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(normalized):
        return None

    if normalized > 1.0:
        normalized = normalized / 100.0

    if normalized < 0.0 or normalized > 1.0:
        return None

    return normalized


def compute_score(prediction: dict, actual: list[int]) -> dict:
    """예측 결과를 채점"""
    normalized_actual = _normalize_top3_numbers(actual)
    if not isinstance(actual, list) or len(actual) != 3:
        return _empty_score(_STATUS_FAIL_ACTUAL_TOP3_MISSING)
    if normalized_actual is None:
        return _empty_score(_STATUS_FAIL_ACTUAL_TOP3_INVALID)

    if not isinstance(prediction, dict):
        return _empty_score(_STATUS_FAIL_PREDICTION_PAYLOAD_MISSING)
    if "predicted" not in prediction:
        return _empty_score(_STATUS_MISSING_PREDICTED_TOP3)

    normalized_predicted = _normalize_top3_numbers(prediction.get("predicted"))
    if normalized_predicted is None:
        return _empty_score(_STATUS_FAIL_PREDICTED_TOP3_INVALID)

    raw_confidence = prediction.get("confidence", _MISSING)
    if raw_confidence in (_MISSING, None, ""):
        return _empty_score(_STATUS_MISSING_CONFIDENCE)

    normalized_confidence = _normalize_confidence(raw_confidence)
    if normalized_confidence is None:
        return _empty_score(_STATUS_FAIL_CONFIDENCE_INVALID)

    # defer 판정
    deferred = normalized_confidence < DEFER_THRESHOLD

    # set_match 계산
    sm = set_match_score(normalized_predicted, normalized_actual)
    correct = len(set(normalized_predicted[:3]) & set(normalized_actual[:3]))
    status_code = _STATUS_DEFERRED_LOW_CONFIDENCE if deferred else _STATUS_SCORED_OK

    return _score_result(
        status_code,
        normalized_confidence=normalized_confidence,
        set_match=sm,
        correct_count=correct,
    )


def print_score_line(results: list[dict]) -> None:
    """한 줄 스코어 출력"""
    total = len(results)
    if total == 0:
        print("No results")
        return

    json_ok_count = sum(1 for r in results if r["json_ok"])
    valid = [r for r in results if r["json_ok"] and not r["deferred"]]
    coverage_validation = build_coverage_validation_result(results)

    sm = sum(r["set_match"] for r in valid) / len(valid) if valid else 0.0
    avg_correct = sum(r["correct_count"] for r in valid) / len(valid) if valid else 0.0
    json_ok_pct = json_ok_count / total * 100
    coverage_pct = coverage_validation["coverage_pct"]

    print(
        f"set_match={sm:.3f} | avg_correct={avg_correct:.2f} | "
        f"json_ok={json_ok_pct:.0f}% | coverage={coverage_pct:.0f}% | "
        f"races={total}"
    )


def build_coverage_validation_result(
    results: list[dict],
    *,
    races: list[dict] | None = None,
    threshold_pct: float = 80.0,
) -> dict:
    """커버리지 게이트용 구조화 결과를 생성한다."""

    total_count = len(results)
    race_lookup: dict[int, str] = {}
    if races:
        for index, race in enumerate(races):
            if not isinstance(race, dict):
                continue
            race_lookup[index] = str(race.get("race_id") or "unknown")

    missing_items: list[dict[str, object]] = []
    for index, result in enumerate(results):
        score_aggregated = bool(
            result.get(
                "score_aggregated", result.get("json_ok") and not result.get("deferred")
            )
        )
        if score_aggregated:
            continue

        race_id = race_lookup.get(index)
        if race_id is None:
            race_id = str(result.get("race_id") or "unknown")

        missing_items.append(
            {
                "result_index": index,
                "race_id": race_id,
                "status_code": result.get("status_code"),
                "status_class": result.get("status_class"),
                "status_reason": result.get("status_reason"),
                "fallback_action": result.get("fallback_action"),
            }
        )

    missing_count = len(missing_items)
    covered_count = total_count - missing_count
    coverage_pct = (covered_count / total_count * 100.0) if total_count else 0.0

    payload = {
        "gate": "coverage",
        "threshold_pct": threshold_pct,
        "total_count": total_count,
        "covered_count": covered_count,
        "missing_count": missing_count,
        "coverage_pct": coverage_pct,
        "passed": missing_count == 0 and coverage_pct >= threshold_pct,
        "missing_items": missing_items,
    }

    if missing_count > 0:
        payload["failure"] = {
            "reason_code": "COVERAGE_MISSING_ITEMS",
            "reason": "Coverage validation found one or more races without an aggregated prediction.",
            "missing_count": missing_count,
            "missing_items": missing_items,
        }

    return payload


# ============================================================
# Evaluate
# ============================================================


def load_snapshot(mode: str) -> tuple[list[dict], dict]:
    """snapshot과 answer_key 로드"""
    snapshot_path = SNAPSHOTS_DIR / f"{mode}.json"
    answer_key_path = SNAPSHOTS_DIR / "answer_key.json"

    with open(snapshot_path) as f:
        races = json.load(f)
    with open(answer_key_path) as f:
        answer_key = json.load(f)

    return races, answer_key.get(mode, {})


def evaluate(mode: str = "mini_val") -> None:
    """train.py의 predict()를 호출하여 평가"""
    # import guard 검사
    train_path = SCRIPT_DIR / "train.py"
    violations = check_train_imports(str(train_path))
    if violations:
        print(f"BLOCKED: train.py uses forbidden imports: {violations}")
        sys.exit(1)

    # train.py import
    from train import predict  # noqa: E402

    races, answer_key = load_snapshot(mode)
    print(f"Evaluating {len(races)} races ({mode})...")

    start = time.time()
    results: list[dict] = []
    timed_out = False
    for i, race in enumerate(races):
        race_id = race.get("race_id", "unknown")
        actual = answer_key.get(race_id, [])
        try:
            prediction = predict(race, call_llm=_call_llm)
            score = compute_score(prediction, actual)
        except Exception as e:
            print(f"  [{i + 1}/{len(races)}] {race_id}: ERROR - {e}")
            score = _empty_score(_STATUS_FAIL_PREDICTION_PAYLOAD_MISSING)
        else:
            status = "DEFER" if score["deferred"] else f"{score['correct_count']}/3"
            print(f"  [{i + 1}/{len(races)}] {race_id}: {status}")
        results.append(score)

        # wall-clock cap
        elapsed = time.time() - start
        if elapsed > EXPERIMENT_TIMEOUT:
            print(f"TIMEOUT: {elapsed:.0f}s > {EXPERIMENT_TIMEOUT}s")
            timed_out = True
            break

    elapsed = time.time() - start
    print(f"\nCompleted in {elapsed:.0f}s")
    print_score_line(results)

    # Hard gate 검사
    total = len(results)
    json_ok_pct = sum(1 for r in results if r["json_ok"]) / total * 100 if total else 0
    coverage_validation = build_coverage_validation_result(results, races=races)
    coverage_pct = coverage_validation["coverage_pct"]

    gates_passed = True
    if timed_out:
        print(
            f"HARD GATE FAIL: experiment timed out ({elapsed:.0f}s > {EXPERIMENT_TIMEOUT}s)"
        )
        gates_passed = False
    if json_ok_pct < 90:
        print(f"HARD GATE FAIL: json_ok={json_ok_pct:.0f}% < 90%")
        gates_passed = False
    if coverage_pct < 80:
        print(f"HARD GATE FAIL: coverage={coverage_pct:.0f}% < 80%")
        gates_passed = False
    if coverage_validation["missing_count"] > 0:
        print("HARD GATE FAIL: coverage missing items detected")
        print(
            json.dumps(
                coverage_validation["failure"],
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        gates_passed = False

    if gates_passed:
        print("All hard gates PASSED")
    sys.exit(0 if gates_passed else 1)


# ============================================================
# CLI
# ============================================================


def main():
    parser = argparse.ArgumentParser(description="KRA Autoresearch Harness")
    parser.add_argument("--holdout", action="store_true", help="holdout 50경주 평가")
    parser.add_argument("--create-snapshot", action="store_true", help="snapshot 생성")
    parser.add_argument("--force-recreate", action="store_true", help="snapshot 재생성")
    args = parser.parse_args()

    if args.create_snapshot:
        create_snapshot(force=args.force_recreate)
    else:
        mode = "holdout" if args.holdout else "mini_val"
        evaluate(mode)


if __name__ == "__main__":
    main()
