"""10개 시드 recent-holdout 실행 결과를 집계하는 후처리 리포트 helpers."""

from __future__ import annotations

import ast
import csv
import json
from collections import Counter
from datetime import UTC, datetime
from io import StringIO
from pathlib import Path
from typing import Any

from shared.execution_matrix import (
    TERMINAL_EXECUTION_STATUSES,
    ExecutionJournal,
    seed_result_repository_from_journal,
    validate_execution_journal_payload,
    validate_seed_result_record_payload,
    validate_seed_result_repository_payload,
)
from shared.seed_metric_normalization import (
    DEFAULT_SEED_METRIC_NAMES,
)
from shared.seed_performance_aggregation import (
    SEED_PERFORMANCE_AGGREGATION_VERSION,
    build_seed_metric_aggregate,
    summarize_seed_metric_distribution,
)

SUMMARY_REPORT_VERSION = "holdout-seed-summary-report-v2"
SUMMARY_REPORT_JSON_FILENAME = "holdout_seed_summary_report.json"
SUMMARY_REPORT_MARKDOWN_FILENAME = "holdout_seed_summary_report.md"
SUMMARY_REPORT_CSV_FILENAME = "holdout_seed_hit_rate_rows.csv"
DEFAULT_PASS_THRESHOLD = 0.70
PRIMARY_GATE_METRIC = "lowest_overall_holdout_hit_rate"
PRIMARY_GATE_SOURCE = "seed_result_repository.summary.lowest_overall_holdout_hit_rate"


def _normalize_datetime(value: datetime | str | None) -> datetime:
    if value is None:
        return datetime.now(UTC).astimezone()
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone()


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(f"{path.suffix}.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(path)


def _dedupe_keep_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _extract_missing_items(errors: list[str]) -> list[str]:
    missing: list[str] = []
    for error in errors:
        location, separator, detail = error.partition(": ")
        if not separator:
            continue
        if location.endswith("missing_required_fields"):
            try:
                parsed = ast.literal_eval(detail)
            except (ValueError, SyntaxError):
                continue
            if isinstance(parsed, list):
                missing.extend(str(item) for item in parsed)
            continue
        if detail == "Field required" and location:
            missing.append(location)
    return _dedupe_keep_order(missing)


def _validation_snapshot(
    *,
    payload: dict[str, Any],
    validator: Any,
) -> dict[str, Any]:
    ok, errors = validator(payload)
    return {
        "ok": ok,
        "missing_items": _extract_missing_items(errors),
        "errors": errors,
    }


def _metric_distribution(
    records: list[dict[str, Any]],
    metric_name: str,
) -> dict[str, Any]:
    values = [
        {
            "run_id": record["run_id"],
            "seed_index": record["seed_index"],
            "model_random_state": record["model_random_state"],
            "value": record[metric_name],
        }
        for record in records
        if record[metric_name] is not None
    ]
    distribution = summarize_seed_metric_distribution(
        float(item["value"]) for item in values
    )
    low_outlier_run_ids = [
        item["run_id"]
        for item in values
        if distribution["lower_fence"] is not None
        and float(item["value"]) < float(distribution["lower_fence"])
    ]
    high_outlier_run_ids = [
        item["run_id"]
        for item in values
        if distribution["upper_fence"] is not None
        and float(item["value"]) > float(distribution["upper_fence"])
    ]
    return {
        "count": distribution["sample_count"],
        "min": distribution["min"],
        "max": distribution["max"],
        "mean": distribution["mean"],
        "median": distribution["median"],
        "stddev": distribution["stddev"],
        "quantiles": distribution["quantiles"],
        "outlier_analysis": {
            "strategy": "iqr",
            "q1": distribution["quantiles"].get("p25"),
            "q3": distribution["quantiles"].get("p75"),
            "iqr": distribution["iqr"],
            "lower_fence": distribution["lower_fence"],
            "upper_fence": distribution["upper_fence"],
            "sample_count": distribution["sample_count"],
            "low_outlier_count": len(low_outlier_run_ids),
            "high_outlier_count": len(high_outlier_run_ids),
            "outlier_run_ids": low_outlier_run_ids + high_outlier_run_ids,
        },
        "values_by_run": values,
    }


def _normalized_metric_sections(
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for metric_name in DEFAULT_SEED_METRIC_NAMES:
        value_source_key = (
            "overall_holdout_hit_rate_source"
            if metric_name == "overall_holdout_hit_rate"
            else None
        )
        aggregate = build_seed_metric_aggregate(
            rows,
            metric_name=metric_name,
            value_source_key=value_source_key,
        )
        metrics[metric_name] = {
            "rule": aggregate["rule"],
            "summary": aggregate["summary"],
            "rows": aggregate["rows"],
        }
    return {
        "schema_version": SEED_PERFORMANCE_AGGREGATION_VERSION,
        "metrics": metrics,
    }


def _verification_verdict(
    *,
    repository_summary: dict[str, Any],
    summary: dict[str, Any],
    primary_metric_value: float | None,
    target_threshold: float,
) -> dict[str, Any]:
    margin = None
    if primary_metric_value is not None:
        margin = round(float(primary_metric_value) - float(target_threshold), 6)

    passed = (
        summary["all_expected_runs_completed"]
        and summary["all_runs_terminal"]
        and primary_metric_value is not None
        and float(primary_metric_value) >= float(target_threshold)
    )

    blockers: list[str] = []
    if not summary["all_expected_runs_completed"]:
        blockers.append("expected_runs_incomplete")
    if not summary["all_runs_terminal"]:
        blockers.append("non_terminal_runs_present")
    if primary_metric_value is None:
        blockers.append("lowest_hit_rate_missing")
    elif float(primary_metric_value) < float(target_threshold):
        blockers.append("below_threshold")

    return {
        "criterion": (
            "10개 랜덤 시드 recent-holdout 반복 평가의 최저 적중 비율이 0.70 이상이어야 함"
        ),
        "basis": PRIMARY_GATE_SOURCE,
        "status": "PASS" if passed else "FAIL",
        "passed": passed,
        "counted_seed_run_count": repository_summary["recorded_run_count"],
        "expected_seed_run_count": repository_summary["expected_run_count"],
        "all_expected_seed_results_recorded": repository_summary[
            "all_expected_runs_recorded"
        ],
        "lowest_hit_rate": primary_metric_value,
        "target_threshold": round(float(target_threshold), 6),
        "margin_vs_threshold": margin,
        "blockers": blockers,
    }


def _record_to_report_row(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": record["run_id"],
        "seed_index": record["seed_index"],
        "model_random_state": record["model_random_state"],
        "overall_holdout_hit_rate": record.get("overall_holdout_hit_rate"),
        "overall_holdout_hit_rate_source": record.get(
            "overall_holdout_hit_rate_source"
        ),
        "overfit_safe_exact_rate": record["overfit_safe_exact_rate"],
        "robust_exact_rate": record["robust_exact_rate"],
        "test_exact_3of3_rate": record["test_exact_3of3_rate"],
        "status": record["status"],
        "output_path": record["output_path"],
        "manifest_path": record["manifest_path"],
        "started_at": record["started_at"],
        "finished_at": record["finished_at"],
    }


def _completed_record_rows(journal: ExecutionJournal) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in journal.records:
        metrics = record.metrics
        if record.status != "completed" or metrics is None:
            continue
        artifacts = record.artifacts
        rows.append(
            {
                "run_id": record.run_id,
                "seed_index": record.seed_index,
                "model_random_state": record.model_random_state,
                "status": record.status,
                "started_at": (
                    record.started_at.isoformat()
                    if record.started_at is not None
                    else None
                ),
                "finished_at": (
                    record.finished_at.isoformat()
                    if record.finished_at is not None
                    else None
                ),
                "output_path": artifacts.output_path if artifacts is not None else None,
                "manifest_path": artifacts.manifest_path
                if artifacts is not None
                else None,
                "overall_holdout_hit_rate": (
                    record.common_result.overall_holdout_hit_rate
                    if record.common_result is not None
                    else None
                ),
                "overall_holdout_hit_rate_source": (
                    record.common_result.overall_holdout_hit_rate_source
                    if record.common_result is not None
                    else None
                ),
                "overfit_safe_exact_rate": metrics.overfit_safe_exact_rate,
                "robust_exact_rate": metrics.robust_exact_rate,
                "test_exact_3of3_rate": metrics.test_exact_3of3_rate,
            }
        )
    rows.sort(key=lambda item: (item["seed_index"], item["run_id"]))
    return rows


def _failed_record_rows(journal: ExecutionJournal) -> list[dict[str, Any]]:
    failed_rows: list[dict[str, Any]] = []
    for record in journal.records:
        if record.status != "failed":
            continue
        failure = record.failure
        failed_rows.append(
            {
                "run_id": record.run_id,
                "seed_index": record.seed_index,
                "model_random_state": record.model_random_state,
                "error_type": failure.error_type if failure is not None else None,
                "error_message": failure.error_message if failure is not None else None,
                "reason_code": failure.reason_code if failure is not None else None,
                "reason": failure.reason if failure is not None else None,
                "missing_count": failure.missing_count if failure is not None else None,
                "missing_items": (
                    list(failure.missing_items) if failure is not None else []
                ),
                "incomplete_top3_count": (
                    failure.incomplete_top3_count if failure is not None else None
                ),
                "incomplete_top3_race_ids": (
                    list(failure.incomplete_top3_race_ids)
                    if failure is not None
                    else []
                ),
                "expected_race_count": (
                    failure.expected_race_count if failure is not None else None
                ),
                "predicted_race_count": (
                    failure.predicted_race_count if failure is not None else None
                ),
                "evaluation_window": (
                    dict(failure.evaluation_window)
                    if failure is not None and failure.evaluation_window is not None
                    else None
                ),
                "finished_at": (
                    record.finished_at.isoformat()
                    if record.finished_at is not None
                    else None
                ),
            }
        )
    failed_rows.sort(key=lambda item: (item["seed_index"], item["run_id"]))
    return failed_rows


def _worst_completed_run(completed_rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    scored_rows = [
        row for row in completed_rows if row["overall_holdout_hit_rate"] is not None
    ]
    if scored_rows:
        worst = min(
            scored_rows,
            key=lambda item: (
                float(item["overall_holdout_hit_rate"]),
                item["seed_index"],
                item["run_id"],
            ),
        )
        return _record_to_report_row(worst)

    scored_rows = [
        row for row in completed_rows if row["overfit_safe_exact_rate"] is not None
    ]
    if not scored_rows:
        return None
    worst = min(
        scored_rows,
        key=lambda item: (
            float(item["overfit_safe_exact_rate"]),
            item["seed_index"],
            item["run_id"],
        ),
    )
    return _record_to_report_row(worst)


def _seed_completion_rows(journal: ExecutionJournal) -> list[dict[str, Any]]:
    records_by_run_id = {record.run_id: record for record in journal.records}
    rows: list[dict[str, Any]] = []

    for seed_index, (run_id, seed) in enumerate(
        zip(journal.expected_run_ids, journal.evaluation_seeds, strict=True),
        start=1,
    ):
        record = records_by_run_id.get(run_id)
        artifacts = record.artifacts if record is not None else None
        failure = record.failure if record is not None else None
        common_result_payload = (
            record.common_result.model_dump(mode="json")
            if record is not None and record.common_result is not None
            else None
        )
        common_result_ok = None
        common_result_errors: list[str] = []
        if common_result_payload is not None:
            common_result_ok, common_result_errors = (
                validate_seed_result_record_payload(common_result_payload)
            )

        missing_items: list[str] = []
        if record is None:
            missing_items.extend(
                [
                    "execution_record",
                    "terminal_status",
                    "metrics",
                    "common_result",
                    "output_path",
                    "manifest_path",
                ]
            )
        else:
            if record.status not in TERMINAL_EXECUTION_STATUSES:
                missing_items.append("terminal_status")
            if record.metrics is None:
                missing_items.append("metrics")
            if record.common_result is None:
                missing_items.append("common_result")
            if artifacts is None or not artifacts.output_path:
                missing_items.append("output_path")
            if artifacts is None or not artifacts.manifest_path:
                missing_items.append("manifest_path")
            missing_items.extend(_extract_missing_items(common_result_errors))

        deduped_missing_items = _dedupe_keep_order(missing_items)
        status = record.status if record is not None else "missing"
        rows.append(
            {
                "run_id": run_id,
                "seed_index": seed_index,
                "model_random_state": (
                    record.model_random_state
                    if record is not None and record.model_random_state is not None
                    else seed
                ),
                "status": status,
                "completion_state": (
                    "done"
                    if record is not None
                    and status == "completed"
                    and not deduped_missing_items
                    else status
                ),
                "format_check_passed": (
                    record is not None
                    and status == "completed"
                    and not deduped_missing_items
                    and common_result_ok is not False
                ),
                "missing_items": deduped_missing_items,
                "validation_errors": common_result_errors,
                "has_execution_record": record is not None,
                "has_metrics": record is not None and record.metrics is not None,
                "has_common_result": record is not None
                and record.common_result is not None,
                "has_output_path": artifacts is not None
                and bool(artifacts.output_path),
                "has_manifest_path": artifacts is not None
                and bool(artifacts.manifest_path),
                "common_result_schema_valid": common_result_ok,
                "failure": (
                    {
                        "error_type": failure.error_type
                        if failure is not None
                        else None,
                        "error_message": failure.error_message
                        if failure is not None
                        else None,
                        "reason_code": failure.reason_code
                        if failure is not None
                        else None,
                        "reason": failure.reason if failure is not None else None,
                        "missing_count": (
                            failure.missing_count if failure is not None else None
                        ),
                        "missing_items": (
                            list(failure.missing_items) if failure is not None else []
                        ),
                        "incomplete_top3_count": (
                            failure.incomplete_top3_count
                            if failure is not None
                            else None
                        ),
                        "incomplete_top3_race_ids": (
                            list(failure.incomplete_top3_race_ids)
                            if failure is not None
                            else []
                        ),
                    }
                    if failure is not None
                    else None
                ),
            }
        )

    return rows


def _completion_check_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    missing_item_counts = Counter(item for row in rows for item in row["missing_items"])
    failure_reason_counts = Counter(
        str(row["failure"]["reason_code"])
        for row in rows
        if row.get("failure") and row["failure"].get("reason_code")
    )
    done_run_count = sum(1 for row in rows if row["completion_state"] == "done")
    format_check_passed_run_count = sum(
        1 for row in rows if row["format_check_passed"] is True
    )
    failure_missing_total = sum(
        int(row["failure"].get("missing_count") or 0)
        for row in rows
        if row.get("failure")
    )
    return {
        "done_run_count": done_run_count,
        "format_check_passed_run_count": format_check_passed_run_count,
        "pending_or_blocked_run_count": len(rows) - done_run_count,
        "missing_item_counts": dict(sorted(missing_item_counts.items())),
        "failure_reason_counts": dict(sorted(failure_reason_counts.items())),
        "failure_missing_total": failure_missing_total,
    }


def _seed_hit_rate_rows(journal: ExecutionJournal) -> list[dict[str, Any]]:
    records_by_run_id = {record.run_id: record for record in journal.records}
    rows: list[dict[str, Any]] = []

    for seed_index, (run_id, seed) in enumerate(
        zip(journal.expected_run_ids, journal.evaluation_seeds, strict=True),
        start=1,
    ):
        record = records_by_run_id.get(run_id)
        metrics = record.metrics if record is not None else None
        common_result = record.common_result if record is not None else None
        artifacts = record.artifacts if record is not None else None
        rows.append(
            {
                "run_id": run_id,
                "seed_index": seed_index,
                "model_random_state": (
                    record.model_random_state
                    if record is not None and record.model_random_state is not None
                    else seed
                ),
                "status": record.status if record is not None else "missing",
                "overall_holdout_hit_rate": (
                    common_result.overall_holdout_hit_rate
                    if common_result is not None
                    else None
                ),
                "overall_holdout_hit_rate_source": (
                    common_result.overall_holdout_hit_rate_source
                    if common_result is not None
                    else None
                ),
                "overfit_safe_exact_rate": (
                    metrics.overfit_safe_exact_rate if metrics is not None else None
                ),
                "robust_exact_rate": (
                    metrics.robust_exact_rate if metrics is not None else None
                ),
                "blended_exact_rate": (
                    metrics.blended_exact_rate if metrics is not None else None
                ),
                "rolling_min_exact_rate": (
                    metrics.rolling_min_exact_rate if metrics is not None else None
                ),
                "rolling_mean_exact_rate": (
                    metrics.rolling_mean_exact_rate if metrics is not None else None
                ),
                "dev_test_gap": (metrics.dev_test_gap if metrics is not None else None),
                "dev_exact_3of3_rate": (
                    metrics.dev_exact_3of3_rate if metrics is not None else None
                ),
                "dev_avg_set_match": (
                    metrics.dev_avg_set_match if metrics is not None else None
                ),
                "test_exact_3of3_rate": (
                    metrics.test_exact_3of3_rate if metrics is not None else None
                ),
                "test_avg_set_match": (
                    metrics.test_avg_set_match if metrics is not None else None
                ),
                "run_at": (
                    common_result.run_at.isoformat()
                    if common_result is not None
                    else None
                ),
                "model_config_id": (
                    common_result.model_config_id if common_result is not None else None
                ),
                "output_path": artifacts.output_path if artifacts is not None else None,
                "manifest_path": (
                    artifacts.manifest_path if artifacts is not None else None
                ),
            }
        )

    return rows


def render_seed_hit_rate_csv(rows: list[dict[str, Any]]) -> str:
    fieldnames = [
        "run_id",
        "seed_index",
        "model_random_state",
        "status",
        "overall_holdout_hit_rate",
        "overall_holdout_hit_rate_source",
        "overfit_safe_exact_rate",
        "robust_exact_rate",
        "test_exact_3of3_rate",
        "run_at",
        "model_config_id",
        "output_path",
        "manifest_path",
    ]
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {key: "" if row.get(key) is None else row.get(key) for key in fieldnames}
        )
    return buffer.getvalue()


def build_seed_summary_report(
    journal: ExecutionJournal,
    *,
    journal_path: Path,
    target_threshold: float = DEFAULT_PASS_THRESHOLD,
    generated_at: datetime | str | None = None,
) -> dict[str, Any]:
    generated_at_dt = _normalize_datetime(generated_at)
    summary = journal.summary
    repository = seed_result_repository_from_journal(journal)
    summary_payload = summary.model_dump(mode="json")
    repository_summary_payload = repository.summary.model_dump(mode="json")
    completed_rows = _completed_record_rows(journal)
    failed_rows = _failed_record_rows(journal)
    seed_completion_rows = _seed_completion_rows(journal)
    seed_hit_rate_rows = _seed_hit_rate_rows(journal)
    normalized_metrics = _normalized_metric_sections(seed_hit_rate_rows)
    overall_holdout_distribution = _metric_distribution(
        seed_hit_rate_rows, "overall_holdout_hit_rate"
    )
    overfit_distribution = _metric_distribution(
        completed_rows, "overfit_safe_exact_rate"
    )
    robust_distribution = _metric_distribution(completed_rows, "robust_exact_rate")
    test_distribution = _metric_distribution(completed_rows, "test_exact_3of3_rate")
    primary_metric_value = repository.summary.lowest_overall_holdout_hit_rate
    verification_verdict = _verification_verdict(
        repository_summary=repository_summary_payload,
        summary=summary_payload,
        primary_metric_value=primary_metric_value,
        target_threshold=target_threshold,
    )
    return {
        "format_version": SUMMARY_REPORT_VERSION,
        "generated_at": generated_at_dt.isoformat(),
        "journal_path": str(journal_path),
        "group_id": journal.group_id,
        "expected_run_ids": list(journal.expected_run_ids),
        "execution_summary": summary_payload,
        "seed_result_repository_summary": repository_summary_payload,
        "validation_overview": {
            "execution_journal": _validation_snapshot(
                payload=journal.model_dump(mode="json"),
                validator=validate_execution_journal_payload,
            ),
            "seed_result_repository": _validation_snapshot(
                payload=repository.model_dump(mode="json"),
                validator=validate_seed_result_repository_payload,
            ),
        },
        "gate": {
            "metric": PRIMARY_GATE_METRIC,
            "metric_source": PRIMARY_GATE_SOURCE,
            "target_threshold": round(float(target_threshold), 6),
            "actual": primary_metric_value,
            "expected_run_count": summary.expected_run_count,
            "completed_run_count": summary.completed_run_count,
            "all_runs_terminal": summary.all_runs_terminal,
            "all_expected_runs_completed": summary.all_expected_runs_completed,
            "all_runs_completed_successfully": summary.all_runs_completed_successfully,
            "passed": verification_verdict["passed"],
        },
        "verification_verdict": verification_verdict,
        "aggregates": {
            "overall_holdout_hit_rate": overall_holdout_distribution,
            "overfit_safe_exact_rate": overfit_distribution,
            "robust_exact_rate": robust_distribution,
            "test_exact_3of3_rate": test_distribution,
        },
        "normalized_metrics": normalized_metrics,
        "worst_completed_run": _worst_completed_run(completed_rows),
        "completed_runs": [_record_to_report_row(row) for row in completed_rows],
        "failed_runs": failed_rows,
        "seed_hit_rate_rows": seed_hit_rate_rows,
        "completion_check": {
            **_completion_check_summary(seed_completion_rows),
            "rows": seed_completion_rows,
        },
    }


def render_seed_summary_markdown(report: dict[str, Any]) -> str:
    gate = report["gate"]
    summary = report["execution_summary"]
    verification_verdict = report["verification_verdict"]
    validation_overview = report["validation_overview"]
    completion_check = report["completion_check"]
    worst = report.get("worst_completed_run")
    lines = [
        "# Holdout 10-Seed Summary Report",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- group_id: `{report['group_id']}`",
        f"- journal_path: `{report['journal_path']}`",
        (
            f"- gate: `{gate['metric']}` {gate['actual']!r} / target {gate['target_threshold']:.2f}"
            f" -> `{'PASS' if gate['passed'] else 'FAIL'}`"
        ),
        (
            f"- completion: completed `{gate['completed_run_count']}` / expected `{gate['expected_run_count']}`"
            f" -> `{'DONE' if gate['all_expected_runs_completed'] else 'PENDING'}`"
        ),
        (
            f"- runs: completed `{summary['completed_run_count']}`, failed `{summary['failed_run_count']}`,"
            f" missing `{len(summary['missing_run_ids'])}`"
        ),
        (
            f"- completion_check: done `{completion_check['done_run_count']}` /"
            f" format-pass `{completion_check['format_check_passed_run_count']}` /"
            f" pending_or_blocked `{completion_check['pending_or_blocked_run_count']}`"
        ),
        (
            f"- coverage_failures: missing_total `{completion_check['failure_missing_total']}` /"
            f" reason_counts `{completion_check['failure_reason_counts'] or {}}`"
        ),
        "",
        "## Final Verification Verdict",
        "",
        f"- criterion: {verification_verdict['criterion']}",
        f"- basis: `{verification_verdict['basis']}`",
        (
            f"- lowest_hit_rate: `{verification_verdict['lowest_hit_rate']}` /"
            f" threshold `{verification_verdict['target_threshold']:.2f}` /"
            f" margin `{verification_verdict['margin_vs_threshold']}`"
        ),
        (
            f"- stored_seed_results: `{verification_verdict['counted_seed_run_count']}` /"
            f" expected `{verification_verdict['expected_seed_run_count']}`"
        ),
        f"- final_status: `{verification_verdict['status']}`",
        f"- blockers: `{', '.join(verification_verdict['blockers']) or '-'}`",
        "",
        "## Storage Validation",
        "",
        (
            f"- execution_journal: `{'PASS' if validation_overview['execution_journal']['ok'] else 'FAIL'}`"
            f" / missing `{', '.join(validation_overview['execution_journal']['missing_items']) or '-'}`"
        ),
        (
            f"- seed_result_repository: `{'PASS' if validation_overview['seed_result_repository']['ok'] else 'FAIL'}`"
            f" / missing `{', '.join(validation_overview['seed_result_repository']['missing_items']) or '-'}`"
        ),
        "",
        "## Seed Completion Check",
        "",
        "| run_id | status | completion | format | missing_items |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in completion_check["rows"]:
        status = row["status"]
        failure = row.get("failure") or {}
        if status == "failed" and failure.get("error_type"):
            status = f"{status}({failure['error_type']})"
        lines.append(
            f"| {row['run_id']} | {status} | {row['completion_state']} |"
            f" {'PASS' if row['format_check_passed'] else 'FAIL'} |"
            f" {', '.join(row['missing_items']) or '-'} |"
        )

        lines.extend(
            [
                "",
                "## Metric Summary",
                "",
                "| metric | min | max | mean | median | count |",
                "| --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
    for metric_name in (
        "overall_holdout_hit_rate",
        "overfit_safe_exact_rate",
        "robust_exact_rate",
        "test_exact_3of3_rate",
    ):
        metric = report["aggregates"][metric_name]
        lines.append(
            f"| {metric_name} | {metric['min']} | {metric['max']} | {metric['mean']} |"
            f" {metric['median']} | {metric['count']} |"
        )

    normalized_gap = (
        report.get("normalized_metrics", {}).get("metrics", {}).get("dev_test_gap", {})
    )
    gap_summary = normalized_gap.get("summary", {})
    lines.extend(
        [
            "",
            "## Normalization Summary",
            "",
            (
                f"- schema_version: `{report.get('normalized_metrics', {}).get('schema_version', '-')}`"
            ),
            (
                f"- dev_test_gap comparable_mean: `{gap_summary.get('comparable_mean')}` /"
                f" stddev `{gap_summary.get('comparable_stddev')}` /"
                f" sample_count `{gap_summary.get('comparable_sample_count')}` /"
                f" abnormal `{gap_summary.get('abnormal_count', 0)}` /"
                f" missing `{gap_summary.get('missing_count', 0)}`"
            ),
        ]
    )

    lines.extend(["", "## Worst Run", ""])
    if worst is None:
        lines.append("- completed run 이 없어 최저 성능을 계산할 수 없습니다.")
    else:
        lines.extend(
            [
                f"- run_id: `{worst['run_id']}`",
                f"- seed_index: `{worst['seed_index']}` / random_state `{worst['model_random_state']}`",
                f"- overall_holdout_hit_rate: `{worst['overall_holdout_hit_rate']}`",
                f"- overfit_safe_exact_rate: `{worst['overfit_safe_exact_rate']}`",
                f"- robust_exact_rate: `{worst['robust_exact_rate']}`",
                f"- test_exact_3of3_rate: `{worst['test_exact_3of3_rate']}`",
                f"- output_path: `{worst['output_path']}`",
            ]
        )

    failed_runs = report.get("failed_runs") or []
    if failed_runs:
        lines.extend(["", "## Failed Runs", ""])
        for row in failed_runs:
            lines.append(
                f"- `{row['run_id']}` seed `{row['model_random_state']}`: {row['error_type']} / {row['error_message']}"
            )
            lines.append(
                f"- reason_code: `{row['reason_code'] or '-'}` / missing_count: `{row['missing_count']}` /"
                f" missing_items: `{', '.join(row['missing_items']) or '-'}`"
            )
            lines.append(
                f"- incomplete_top3_count: `{row['incomplete_top3_count']}` /"
                f" incomplete_top3_race_ids: `{', '.join(row['incomplete_top3_race_ids']) or '-'}`"
            )
            if row.get("reason"):
                lines.append(f"- failure_reason: {row['reason']}")
            if row.get("evaluation_window"):
                lines.append(
                    "- evaluation_window: "
                    f"`{json.dumps(row['evaluation_window'], ensure_ascii=False, sort_keys=True)}`"
                )

    missing_run_ids = summary.get("missing_run_ids") or []
    if missing_run_ids:
        lines.extend(["", "## Missing Runs", ""])
        for run_id in missing_run_ids:
            lines.append(f"- `{run_id}`")

    missing_completed_run_ids = summary.get("missing_completed_run_ids") or []
    if missing_completed_run_ids:
        lines.extend(["", "## Missing Completed Runs", ""])
        for run_id in missing_completed_run_ids:
            lines.append(f"- `{run_id}`")

    lines.append("")
    return "\n".join(lines)


def sync_seed_summary_report(
    journal: ExecutionJournal,
    *,
    journal_path: Path,
    target_threshold: float = DEFAULT_PASS_THRESHOLD,
    generated_at: datetime | str | None = None,
) -> dict[str, Any] | None:
    json_path = journal_path.with_name(SUMMARY_REPORT_JSON_FILENAME)
    markdown_path = journal_path.with_name(SUMMARY_REPORT_MARKDOWN_FILENAME)
    csv_path = journal_path.with_name(SUMMARY_REPORT_CSV_FILENAME)

    report = build_seed_summary_report(
        journal,
        journal_path=journal_path,
        target_threshold=target_threshold,
        generated_at=generated_at,
    )
    _atomic_write_text(
        json_path,
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
    )
    _atomic_write_text(markdown_path, render_seed_summary_markdown(report))
    _atomic_write_text(csv_path, render_seed_hit_rate_csv(report["seed_hit_rate_rows"]))
    return {
        "json_path": str(json_path),
        "markdown_path": str(markdown_path),
        "csv_path": str(csv_path),
        "gate": report["gate"],
        "verification_verdict": report["verification_verdict"],
        "completion_check": {
            "done_run_count": report["completion_check"]["done_run_count"],
            "format_check_passed_run_count": report["completion_check"][
                "format_check_passed_run_count"
            ],
            "pending_or_blocked_run_count": report["completion_check"][
                "pending_or_blocked_run_count"
            ],
            "failure_reason_counts": report["completion_check"][
                "failure_reason_counts"
            ],
            "failure_missing_total": report["completion_check"][
                "failure_missing_total"
            ],
        },
    }
