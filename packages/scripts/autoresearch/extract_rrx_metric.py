from __future__ import annotations

import json
from pathlib import Path

REPORT_PATH = Path(".ralph/outputs/holdout_seed_summary_report.json")


def main() -> None:
    if not REPORT_PATH.exists():
        print(0)
        return

    payload = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    gate = payload.get("gate") or {}
    verification_verdict = payload.get("verification_verdict") or {}
    validation_overview = payload.get("validation_overview") or {}
    execution_journal_validation = validation_overview.get("execution_journal") or {}
    repository_validation = validation_overview.get("seed_result_repository") or {}

    if gate.get("metric") != "lowest_overall_holdout_hit_rate":
        print(0)
        return

    if verification_verdict.get("status") != "PASS":
        print(0)
        return

    if not execution_journal_validation.get("ok"):
        print(0)
        return

    if not repository_validation.get("ok"):
        print(0)
        return

    actual = gate.get("actual")
    if actual is None:
        print(0)
        return

    try:
        print(float(actual))
    except (TypeError, ValueError):
        print(0)


if __name__ == "__main__":
    main()
