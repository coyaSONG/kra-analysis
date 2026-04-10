"""Candidate runner filtering based on prereace abnormal status signals."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

RUNNER_STATUS_NORMAL = "normal"
RUNNER_STATUS_CANCELLED = "cancelled"
RUNNER_STATUS_WITHDRAWN = "withdrawn"
RUNNER_STATUS_EXCLUDED = "excluded"
RUNNER_STATUS_SCRATCHED = "scratched"
RUNNER_STATUS_INVALID_ENTRY = "invalid_entry"
RUNNER_STATUS_BURDEN_OUTLIER = "burden_outlier"
MINIMUM_PREDICTION_CANDIDATES = 3

SHORTAGE_REASON_OFFICIAL = "official_status"
SHORTAGE_REASON_MARKET = "market_signal"
SHORTAGE_REASON_DATA_QUALITY = "data_quality"
SHORTAGE_REASON_UNKNOWN = "unknown"

SHORTAGE_CLASS_SUFFICIENT = "sufficient_candidates"
SHORTAGE_CLASS_RAW_FIELD_TOO_SMALL = "raw_field_too_small"
SHORTAGE_CLASS_OFFICIAL = "official_status_reduced_below_minimum"
SHORTAGE_CLASS_MARKET = "market_signal_reduced_below_minimum"
SHORTAGE_CLASS_DATA_QUALITY = "data_quality_reduced_below_minimum"
SHORTAGE_CLASS_MIXED = "mixed_reasons_reduced_below_minimum"
SHORTAGE_CLASS_UNKNOWN = "unknown_reasons_reduced_below_minimum"

RULE_INVALID_ENTRY_MISSING_CHUL_NO = "invalid_entry_missing_chul_no"
RULE_WG_BUDAM_OUTLIER = "wg_budam_outlier"
RULE_MARKET_SIGNAL_MISSING = "market_signal_missing"
RULE_PLC_ODDS_MISSING = "plc_odds_missing"
RULE_RATING_PARSE_FAILED = "rating_parse_failed"
RULE_RATING_OUTLIER = "rating_outlier"
RULE_WEIGHT_MISSING = "weight_missing"
RULE_WEIGHT_PARSE_FAILED = "weight_parse_failed"
RULE_WEIGHT_OUTLIER = "weight_outlier"
RULE_WEIGHT_DELTA_MISSING = "weight_delta_missing"
RULE_WEIGHT_DELTA_PARSE_FAILED = "weight_delta_parse_failed"
RULE_WEIGHT_DELTA_OUTLIER = "weight_delta_outlier"
REINCLUSION_RULE_CANDIDATE_SHORTAGE_V1 = "candidate_shortage_reinclusion_v1"
MINIMUM_INFO_FALLBACK_RULE_V1 = "minimum_info_fallback_v1"
CANDIDATE_SELECTION_RULESET_V1 = "candidate_filter_minimum_info_fallback_v1"
REINCLUSION_PRIORITY_MARKET_SIGNAL = 10
REINCLUSION_PRIORITY_BURDEN_OUTLIER = 20

ABNORMAL_RUNNER_STATUSES = frozenset(
    {
        RUNNER_STATUS_CANCELLED,
        RUNNER_STATUS_WITHDRAWN,
        RUNNER_STATUS_EXCLUDED,
        RUNNER_STATUS_SCRATCHED,
        RUNNER_STATUS_INVALID_ENTRY,
        RUNNER_STATUS_BURDEN_OUTLIER,
    }
)


@dataclass(frozen=True, slots=True)
class RunnerStatusRecord:
    chul_no: int | None
    hr_no: str | None
    hr_name: str | None
    status_code: str
    source: str
    raw_reason: str | None = None
    applied_rules: tuple[str, ...] = ()
    quality_flags: tuple[str, ...] = ()
    exclusion_reason: str | None = None

    @property
    def candidate_excluded(self) -> bool:
        return self.status_code in ABNORMAL_RUNNER_STATUSES

    def to_dict(self) -> dict[str, Any]:
        return {
            "chul_no": self.chul_no,
            "hr_no": self.hr_no,
            "hr_name": self.hr_name,
            "status_code": self.status_code,
            "source": self.source,
            "raw_reason": self.raw_reason,
            "applied_rules": list(self.applied_rules),
            "quality_flags": list(self.quality_flags),
            "exclusion_reason": self.exclusion_reason,
            "candidate_excluded": self.candidate_excluded,
        }


@dataclass(frozen=True, slots=True)
class ReinclusionDecision:
    status_record: RunnerStatusRecord
    reinclusion_priority: int
    reinclusion_rule: str = REINCLUSION_RULE_CANDIDATE_SHORTAGE_V1

    def to_dict(self) -> dict[str, Any]:
        payload = self.status_record.to_dict()
        payload.update(
            {
                "reinclusion_priority": self.reinclusion_priority,
                "reinclusion_rule": self.reinclusion_rule,
            }
        )
        return payload


@dataclass(frozen=True, slots=True)
class CandidateFilterResult:
    eligible_runners: list[dict[str, Any]]
    status_records: list[RunnerStatusRecord]
    reinclusion_decisions: tuple[ReinclusionDecision, ...] = ()

    @property
    def _reincluded_identity_set(self) -> set[tuple[str, Any]]:
        return {
            _runner_identity(decision.status_record)
            for decision in self.reinclusion_decisions
        }

    @property
    def _final_excluded_records(self) -> list[RunnerStatusRecord]:
        reincluded_identities = self._reincluded_identity_set
        return [
            record
            for record in self.status_records
            if record.candidate_excluded
            and _runner_identity(record) not in reincluded_identities
        ]

    @property
    def excluded_runners(self) -> list[dict[str, Any]]:
        return [record.to_dict() for record in self._final_excluded_records]

    @property
    def reincluded_runners(self) -> list[dict[str, Any]]:
        return [decision.to_dict() for decision in self.reinclusion_decisions]

    @property
    def status_counts(self) -> dict[str, int]:
        counts = Counter(record.status_code for record in self.status_records)
        return dict(sorted(counts.items()))

    @property
    def flagged_runners(self) -> list[dict[str, Any]]:
        return [
            record.to_dict() for record in self.status_records if record.quality_flags
        ]

    @property
    def exclusion_rule_counts(self) -> dict[str, int]:
        counts = Counter(
            record.exclusion_reason
            for record in self._final_excluded_records
            if record.exclusion_reason
        )
        return dict(sorted(counts.items()))

    @property
    def initial_exclusion_rule_counts(self) -> dict[str, int]:
        counts = Counter(
            record.exclusion_reason
            for record in self.status_records
            if record.candidate_excluded and record.exclusion_reason
        )
        return dict(sorted(counts.items()))

    @property
    def reinclusion_rule_counts(self) -> dict[str, int]:
        counts = Counter(
            decision.status_record.exclusion_reason
            for decision in self.reinclusion_decisions
            if decision.status_record.exclusion_reason
        )
        return dict(sorted(counts.items()))

    @property
    def flag_counts(self) -> dict[str, int]:
        counts = Counter(
            flag for record in self.status_records for flag in record.quality_flags
        )
        return dict(sorted(counts.items()))

    @property
    def rule_logs(self) -> list[dict[str, Any]]:
        return [record.to_dict() for record in self.status_records]

    @property
    def race_diagnostics(self) -> dict[str, Any]:
        total_runner_count = len(self.status_records)
        initial_excluded_runner_count = sum(
            1 for record in self.status_records if record.candidate_excluded
        )
        initial_eligible_runner_count = (
            total_runner_count - initial_excluded_runner_count
        )
        initial_candidate_shortage_count = max(
            0, MINIMUM_PREDICTION_CANDIDATES - initial_eligible_runner_count
        )
        reincluded_runner_count = len(self.reinclusion_decisions)
        eligible_runner_count = len(self.eligible_runners)
        excluded_runner_count = len(self._final_excluded_records)
        candidate_shortage_count = max(
            0, MINIMUM_PREDICTION_CANDIDATES - eligible_runner_count
        )
        shortage_reason_counts = Counter(
            _classify_shortage_reason(record) for record in self._final_excluded_records
        )
        ordered_shortage_reason_counts = dict(sorted(shortage_reason_counts.items()))
        shortage_reason_classification = _classify_shortage_reason_summary(
            eligible_runner_count=eligible_runner_count,
            total_runner_count=total_runner_count,
            shortage_reason_counts=ordered_shortage_reason_counts,
        )
        primary_shortage_reason = (
            max(
                ordered_shortage_reason_counts.items(),
                key=lambda item: (item[1], item[0]),
            )[0]
            if candidate_shortage_count > 0 and ordered_shortage_reason_counts
            else None
        )
        return {
            "minimum_prediction_candidates": MINIMUM_PREDICTION_CANDIDATES,
            "total_runner_count": total_runner_count,
            "initial_eligible_runner_count": initial_eligible_runner_count,
            "initial_excluded_runner_count": initial_excluded_runner_count,
            "initial_candidate_shortage_count": initial_candidate_shortage_count,
            "reincluded_runner_count": reincluded_runner_count,
            "reinclusion_applied": reincluded_runner_count > 0,
            "eligible_runner_count": eligible_runner_count,
            "excluded_runner_count": excluded_runner_count,
            "candidate_shortage_count": candidate_shortage_count,
            "has_candidate_shortage": candidate_shortage_count > 0,
            "shortage_reason_counts": ordered_shortage_reason_counts,
            "shortage_reason_classification": shortage_reason_classification,
            "primary_shortage_reason": primary_shortage_reason,
        }

    def to_audit_dict(self) -> dict[str, Any]:
        return {
            "status_counts": self.status_counts,
            "excluded_runners": self.excluded_runners,
            "reincluded_runners": self.reincluded_runners,
            "flagged_runners": self.flagged_runners,
            "exclusion_rule_counts": self.exclusion_rule_counts,
            "initial_exclusion_rule_counts": self.initial_exclusion_rule_counts,
            "reinclusion_rule_counts": self.reinclusion_rule_counts,
            "flag_counts": self.flag_counts,
            "rule_logs": self.rule_logs,
            "race_diagnostics": self.race_diagnostics,
        }


@dataclass(frozen=True, slots=True)
class MinimumInfoFallbackDecision:
    runner: dict[str, Any]
    status_record: RunnerStatusRecord
    fallback_order: int
    fallback_rule: str = MINIMUM_INFO_FALLBACK_RULE_V1

    def to_dict(self) -> dict[str, Any]:
        payload = self.status_record.to_dict()
        payload.update(
            {
                "fallback_order": self.fallback_order,
                "fallback_rule": self.fallback_rule,
                "selection_stage": "minimum_info_fallback",
            }
        )
        return payload


@dataclass(frozen=True, slots=True)
class PredictionCandidateSelection:
    primary_filter_result: CandidateFilterResult
    eligible_runners: list[dict[str, Any]]
    minimum_info_fallback_decisions: tuple[MinimumInfoFallbackDecision, ...] = ()

    def to_audit_dict(self) -> dict[str, Any]:
        payload = self.primary_filter_result.to_audit_dict()
        reincluded_targets = [
            _trace_target_payload(
                decision.status_record, selection_stage="shortage_reinclusion"
            )
            for decision in self.primary_filter_result.reinclusion_decisions
        ]
        fallback_targets = [
            _trace_target_payload(
                decision.status_record, selection_stage="minimum_info_fallback"
            )
            for decision in self.minimum_info_fallback_decisions
        ]
        final_targets = [
            _trace_target_from_runner(runner) for runner in self.eligible_runners
        ]
        applied_rule_ids: list[str] = []
        if self.primary_filter_result.reinclusion_decisions:
            applied_rule_ids.append(REINCLUSION_RULE_CANDIDATE_SHORTAGE_V1)
        if self.minimum_info_fallback_decisions:
            applied_rule_ids.append(MINIMUM_INFO_FALLBACK_RULE_V1)

        final_candidate_count = len(self.eligible_runners)
        payload["minimum_info_fallback_runners"] = [
            decision.to_dict() for decision in self.minimum_info_fallback_decisions
        ]
        payload["final_candidate_validation"] = {
            "active_runner_rule": CANDIDATE_SELECTION_RULESET_V1,
            "minimum_prediction_candidates": MINIMUM_PREDICTION_CANDIDATES,
            "final_candidate_count": final_candidate_count,
            "minimum_candidate_met": final_candidate_count
            >= MINIMUM_PREDICTION_CANDIDATES,
            "remaining_candidate_gap": max(
                0, MINIMUM_PREDICTION_CANDIDATES - final_candidate_count
            ),
        }
        payload["race_trace"] = {
            "applied_rule_ids": applied_rule_ids,
            "reincluded_targets": reincluded_targets,
            "minimum_info_fallback_targets": fallback_targets,
            "reintroduced_targets": [*reincluded_targets, *fallback_targets],
            "final_candidates": final_targets,
            "final_candidate_chul_nos": [
                target["chul_no"]
                for target in final_targets
                if target["chul_no"] is not None
            ],
            "final_candidate_count": final_candidate_count,
        }
        return payload


def filter_candidate_runners(
    runners: list[dict[str, Any]] | None,
    *,
    cancelled_horses: list[dict[str, Any]] | None = None,
) -> CandidateFilterResult:
    runner_list = [runner for runner in (runners or []) if isinstance(runner, dict)]
    cancelled_lookup = _build_cancelled_lookup(cancelled_horses or [])

    status_records: list[RunnerStatusRecord] = []
    runner_status_pairs: list[tuple[dict[str, Any], RunnerStatusRecord]] = []
    for runner in runner_list:
        status = classify_runner_status(runner, cancelled_lookup=cancelled_lookup)
        status_records.append(status)
        runner_status_pairs.append((runner, status))

    initial_eligible_runner_count = sum(
        1 for _runner, status in runner_status_pairs if not status.candidate_excluded
    )
    shortage_count = max(
        0, MINIMUM_PREDICTION_CANDIDATES - initial_eligible_runner_count
    )
    reinclusion_decisions = _build_reinclusion_decisions(
        runner_status_pairs,
        shortage_count=shortage_count,
    )
    reinclusion_lookup = {
        _runner_identity(decision.status_record): decision
        for decision in reinclusion_decisions
    }
    eligible_runners: list[dict[str, Any]] = []
    for runner, status in runner_status_pairs:
        decision = reinclusion_lookup.get(_runner_identity(status))
        if not status.candidate_excluded or decision is not None:
            eligible_runners.append(
                _attach_runner_filter_audit(runner, status, reinclusion=decision)
            )

    return CandidateFilterResult(
        eligible_runners=eligible_runners,
        status_records=status_records,
        reinclusion_decisions=tuple(reinclusion_decisions),
    )


def select_prediction_candidates(
    runners: list[dict[str, Any]] | None,
    *,
    cancelled_horses: list[dict[str, Any]] | None = None,
) -> PredictionCandidateSelection:
    runner_list = [runner for runner in (runners or []) if isinstance(runner, dict)]
    primary_filter_result = filter_candidate_runners(
        runner_list,
        cancelled_horses=cancelled_horses,
    )
    eligible_runners = list(primary_filter_result.eligible_runners)
    selected_identities = {
        _runner_identity_from_runner(runner) for runner in eligible_runners
    }
    status_by_identity = {
        _runner_identity(record): record
        for record in primary_filter_result.status_records
    }
    fallback_decisions: list[MinimumInfoFallbackDecision] = []

    if len(eligible_runners) < MINIMUM_PREDICTION_CANDIDATES:
        for runner in runner_list:
            runner_identity = _runner_identity_from_runner(runner)
            if runner_identity in selected_identities:
                continue

            status = status_by_identity.get(runner_identity)
            if status is None:
                status = classify_runner_status(
                    runner,
                    cancelled_lookup=_build_cancelled_lookup(cancelled_horses or []),
                )

            if status.status_code in {
                RUNNER_STATUS_CANCELLED,
                RUNNER_STATUS_WITHDRAWN,
                RUNNER_STATUS_EXCLUDED,
            }:
                continue
            if not _meets_minimum_prediction_fallback(runner):
                continue

            decision = MinimumInfoFallbackDecision(
                runner=runner,
                status_record=status,
                fallback_order=len(fallback_decisions) + 1,
            )
            fallback_decisions.append(decision)
            eligible_runners.append(
                _attach_runner_filter_audit(
                    runner,
                    status,
                    selection_stage="minimum_info_fallback",
                    minimum_info_fallback=True,
                    fallback_rule=decision.fallback_rule,
                )
            )
            selected_identities.add(runner_identity)
            if len(eligible_runners) >= MINIMUM_PREDICTION_CANDIDATES:
                break

    return PredictionCandidateSelection(
        primary_filter_result=primary_filter_result,
        eligible_runners=eligible_runners,
        minimum_info_fallback_decisions=tuple(fallback_decisions),
    )


def classify_runner_status(
    runner: dict[str, Any],
    *,
    cancelled_lookup: dict[tuple[str, Any], RunnerStatusRecord] | None = None,
) -> RunnerStatusRecord:
    chul_no = _normalize_chul_no(
        runner.get("chulNo", runner.get("chul_no", runner.get("horse_no")))
    )
    hr_no = _normalize_identifier(runner.get("hrNo", runner.get("hr_no")))
    hr_name = _normalize_name(
        runner.get("hrName", runner.get("hr_name", runner.get("horse_name")))
    )
    quality_flags = _collect_quality_flags(runner)

    if chul_no is None:
        return RunnerStatusRecord(
            chul_no=None,
            hr_no=hr_no,
            hr_name=hr_name,
            status_code=RUNNER_STATUS_INVALID_ENTRY,
            source="missing_chul_no",
            applied_rules=(RULE_INVALID_ENTRY_MISSING_CHUL_NO, *quality_flags),
            quality_flags=quality_flags,
            exclusion_reason=RULE_INVALID_ENTRY_MISSING_CHUL_NO,
        )

    if cancelled_lookup:
        matched = _lookup_cancelled_status(
            cancelled_lookup, chul_no=chul_no, hr_no=hr_no, hr_name=hr_name
        )
        if matched is not None:
            return RunnerStatusRecord(
                chul_no=chul_no,
                hr_no=hr_no,
                hr_name=hr_name,
                status_code=matched.status_code,
                source=matched.source,
                raw_reason=matched.raw_reason,
                applied_rules=matched.applied_rules + quality_flags,
                quality_flags=quality_flags,
                exclusion_reason=matched.exclusion_reason,
            )

    raw_burden = runner.get("wgBudam", runner.get("wg_budam"))
    burden_value = _safe_float(raw_burden)
    if raw_burden not in (None, "", "-") and (
        burden_value is None or burden_value < 40 or burden_value > 65
    ):
        return RunnerStatusRecord(
            chul_no=chul_no,
            hr_no=hr_no,
            hr_name=hr_name,
            status_code=RUNNER_STATUS_BURDEN_OUTLIER,
            source="wg_budam_guardrail",
            raw_reason=_normalize_reason(f"wgBudam={raw_burden}"),
            applied_rules=(RULE_WG_BUDAM_OUTLIER, *quality_flags),
            quality_flags=quality_flags,
            exclusion_reason=RULE_WG_BUDAM_OUTLIER,
        )

    if _has_zero_market_signal(runner):
        return RunnerStatusRecord(
            chul_no=chul_no,
            hr_no=hr_no,
            hr_name=hr_name,
            status_code=RUNNER_STATUS_SCRATCHED,
            source="zero_market_signal",
            applied_rules=("zero_market_signal", *quality_flags),
            quality_flags=quality_flags,
            exclusion_reason="zero_market_signal",
        )

    return RunnerStatusRecord(
        chul_no=chul_no,
        hr_no=hr_no,
        hr_name=hr_name,
        status_code=RUNNER_STATUS_NORMAL,
        source="active_runner",
        applied_rules=("active_runner", *quality_flags),
        quality_flags=quality_flags,
    )


def _lookup_cancelled_status(
    cancelled_lookup: dict[tuple[str, Any], RunnerStatusRecord],
    *,
    chul_no: int | None,
    hr_no: str | None,
    hr_name: str | None,
) -> RunnerStatusRecord | None:
    keys = [
        ("chul_no", chul_no),
        ("hr_no", hr_no),
        ("hr_name", hr_name),
    ]
    for key in keys:
        if key[1] is None:
            continue
        matched = cancelled_lookup.get(key)
        if matched is not None:
            return matched
    return None


def _runner_identity(record: RunnerStatusRecord) -> tuple[str, Any]:
    if record.chul_no is not None:
        return ("chul_no", record.chul_no)
    if record.hr_no is not None:
        return ("hr_no", record.hr_no)
    if record.hr_name is not None:
        return ("hr_name", record.hr_name)
    return ("status_code", record.status_code)


def _runner_identity_from_runner(runner: dict[str, Any]) -> tuple[str, Any]:
    chul_no = _normalize_chul_no(
        runner.get("chulNo", runner.get("chul_no", runner.get("horse_no")))
    )
    hr_no = _normalize_identifier(runner.get("hrNo", runner.get("hr_no")))
    hr_name = _normalize_name(
        runner.get("hrName", runner.get("hr_name", runner.get("horse_name")))
    )
    if chul_no is not None:
        return ("chul_no", chul_no)
    if hr_no is not None:
        return ("hr_no", hr_no)
    if hr_name is not None:
        return ("hr_name", hr_name)
    return ("runner", id(runner))


def _build_reinclusion_decisions(
    runner_status_pairs: list[tuple[dict[str, Any], RunnerStatusRecord]],
    *,
    shortage_count: int,
) -> list[ReinclusionDecision]:
    if shortage_count <= 0:
        return []

    candidates: list[tuple[int, int, RunnerStatusRecord]] = []
    for index, (_runner, status) in enumerate(runner_status_pairs):
        priority = _reinclusion_priority(status)
        if priority is None:
            continue
        candidates.append((priority, index, status))

    selected = sorted(candidates)[:shortage_count]
    return [
        ReinclusionDecision(status_record=status, reinclusion_priority=priority)
        for priority, _index, status in selected
    ]


def _reinclusion_priority(record: RunnerStatusRecord) -> int | None:
    if record.exclusion_reason == "zero_market_signal":
        return REINCLUSION_PRIORITY_MARKET_SIGNAL
    if record.exclusion_reason == RULE_WG_BUDAM_OUTLIER:
        return REINCLUSION_PRIORITY_BURDEN_OUTLIER
    return None


def _classify_shortage_reason(record: RunnerStatusRecord) -> str:
    if record.status_code in {
        RUNNER_STATUS_CANCELLED,
        RUNNER_STATUS_WITHDRAWN,
        RUNNER_STATUS_EXCLUDED,
    }:
        return SHORTAGE_REASON_OFFICIAL
    if record.status_code == RUNNER_STATUS_SCRATCHED:
        return SHORTAGE_REASON_MARKET
    if record.status_code in {
        RUNNER_STATUS_INVALID_ENTRY,
        RUNNER_STATUS_BURDEN_OUTLIER,
    }:
        return SHORTAGE_REASON_DATA_QUALITY
    return SHORTAGE_REASON_UNKNOWN


def _classify_shortage_reason_summary(
    *,
    eligible_runner_count: int,
    total_runner_count: int,
    shortage_reason_counts: dict[str, int],
) -> str:
    if eligible_runner_count >= MINIMUM_PREDICTION_CANDIDATES:
        return SHORTAGE_CLASS_SUFFICIENT
    if total_runner_count < MINIMUM_PREDICTION_CANDIDATES:
        return SHORTAGE_CLASS_RAW_FIELD_TOO_SMALL

    present_reasons = {
        reason for reason, count in shortage_reason_counts.items() if count > 0
    }
    if not present_reasons:
        return SHORTAGE_CLASS_UNKNOWN
    if len(present_reasons) > 1:
        return SHORTAGE_CLASS_MIXED
    reason = next(iter(present_reasons))
    if reason == SHORTAGE_REASON_OFFICIAL:
        return SHORTAGE_CLASS_OFFICIAL
    if reason == SHORTAGE_REASON_MARKET:
        return SHORTAGE_CLASS_MARKET
    if reason == SHORTAGE_REASON_DATA_QUALITY:
        return SHORTAGE_CLASS_DATA_QUALITY
    return SHORTAGE_CLASS_UNKNOWN


def _build_cancelled_lookup(
    cancelled_horses: list[dict[str, Any]],
) -> dict[tuple[str, Any], RunnerStatusRecord]:
    lookup: dict[tuple[str, Any], RunnerStatusRecord] = {}
    for row in cancelled_horses:
        if not isinstance(row, dict):
            continue
        status_code = _canonicalize_cancelled_status(row)
        raw_reason = _normalize_reason(row.get("reason") or row.get("status"))
        record = RunnerStatusRecord(
            chul_no=_normalize_chul_no(row.get("chulNo", row.get("chul_no"))),
            hr_no=_normalize_identifier(row.get("hrNo", row.get("hr_no"))),
            hr_name=_normalize_name(row.get("hrName", row.get("hr_name"))),
            status_code=status_code,
            source="cancelled_horses_api9",
            raw_reason=raw_reason,
            applied_rules=(status_code,),
            exclusion_reason=status_code,
        )
        for key in (
            ("chul_no", record.chul_no),
            ("hr_no", record.hr_no),
            ("hr_name", record.hr_name),
        ):
            if key[1] is not None and key not in lookup:
                lookup[key] = record
    return lookup


def _canonicalize_cancelled_status(row: dict[str, Any]) -> str:
    raw_reason = _normalize_reason(row.get("reason") or row.get("status"))
    if raw_reason:
        if "기권" in raw_reason:
            return RUNNER_STATUS_WITHDRAWN
        if "제외" in raw_reason:
            return RUNNER_STATUS_EXCLUDED
        if "취소" in raw_reason:
            return RUNNER_STATUS_CANCELLED
    return RUNNER_STATUS_CANCELLED


def _normalize_reason(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return re.sub(r"\s+", " ", text) or None


def _normalize_name(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_identifier(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return re.sub(r"\.0+$", "", text)


def _normalize_chul_no(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _is_zero_like(value: Any) -> bool:
    if value is None:
        return False
    try:
        return float(value) == 0.0
    except (TypeError, ValueError):
        return False


def _has_zero_market_signal(runner: dict[str, Any]) -> bool:
    return _is_zero_like(
        runner.get("winOdds", runner.get("win_odds"))
    ) or _is_zero_like(runner.get("plcOdds", runner.get("plc_odds")))


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _attach_runner_filter_audit(
    runner: dict[str, Any],
    status: RunnerStatusRecord,
    *,
    reinclusion: ReinclusionDecision | None = None,
    selection_stage: str = "primary_filter",
    minimum_info_fallback: bool = False,
    fallback_rule: str | None = None,
) -> dict[str, Any]:
    enriched = dict(runner)
    candidate_filter = status.to_dict()
    candidate_filter["effective_candidate_excluded"] = False
    candidate_filter["selection_stage"] = selection_stage
    if reinclusion is not None:
        candidate_filter["reincluded_due_to_shortage"] = True
        candidate_filter["reinclusion_priority"] = reinclusion.reinclusion_priority
        candidate_filter["reinclusion_rule"] = reinclusion.reinclusion_rule
        candidate_filter["selection_stage"] = "shortage_reinclusion"
    if minimum_info_fallback:
        candidate_filter["minimum_info_fallback_applied"] = True
        candidate_filter["minimum_info_fallback_rule"] = (
            fallback_rule or MINIMUM_INFO_FALLBACK_RULE_V1
        )
    enriched["candidate_filter"] = candidate_filter
    if status.quality_flags:
        enriched["quality_flags"] = list(status.quality_flags)
    return enriched


def _trace_target_payload(
    status: RunnerStatusRecord,
    *,
    selection_stage: str,
) -> dict[str, Any]:
    return {
        "chul_no": status.chul_no,
        "hr_no": status.hr_no,
        "hr_name": status.hr_name,
        "status_code": status.status_code,
        "exclusion_reason": status.exclusion_reason,
        "selection_stage": selection_stage,
    }


def _trace_target_from_runner(runner: dict[str, Any]) -> dict[str, Any]:
    candidate_filter = runner.get("candidate_filter", {})
    return {
        "chul_no": _normalize_chul_no(
            runner.get("chulNo", runner.get("chul_no", runner.get("horse_no")))
        ),
        "hr_no": _normalize_identifier(runner.get("hrNo", runner.get("hr_no"))),
        "hr_name": _normalize_name(
            runner.get("hrName", runner.get("hr_name", runner.get("horse_name")))
        ),
        "selection_stage": candidate_filter.get("selection_stage", "primary_filter"),
    }


def _meets_minimum_prediction_fallback(runner: dict[str, Any]) -> bool:
    chul_no = _normalize_chul_no(
        runner.get("chulNo", runner.get("chul_no", runner.get("horse_no")))
    )
    if chul_no is None or chul_no <= 0:
        return False
    if not _normalize_name(
        runner.get("hrName", runner.get("hr_name", runner.get("horse_name")))
    ):
        return False
    if not _normalize_name(runner.get("sex")):
        return False
    age = _safe_float(runner.get("age"))
    if age is None or age <= 0:
        return False
    burden = _safe_float(runner.get("wgBudam", runner.get("wg_budam")))
    if burden is None or burden <= 0:
        return False
    return True


def _collect_quality_flags(runner: dict[str, Any]) -> tuple[str, ...]:
    flags: list[str] = []

    rating = _safe_float(runner.get("rating"))
    raw_rating = runner.get("rating")
    if raw_rating not in (None, "", "-") and rating is None:
        flags.append(RULE_RATING_PARSE_FAILED)
    elif rating is not None and (rating < 0 or rating > 140):
        flags.append(RULE_RATING_OUTLIER)

    weight_flags = _collect_weight_flags(runner.get("wgHr", runner.get("wg_hr")))
    flags.extend(weight_flags)

    win_odds = _safe_float(runner.get("winOdds", runner.get("win_odds")))
    if win_odds is None or win_odds <= 0 or win_odds > 300:
        flags.append(RULE_MARKET_SIGNAL_MISSING)

    plc_odds = _safe_float(runner.get("plcOdds", runner.get("plc_odds")))
    if plc_odds is None or plc_odds <= 0 or plc_odds > 100:
        flags.append(RULE_PLC_ODDS_MISSING)

    return tuple(dict.fromkeys(flags))


def _collect_weight_flags(value: Any) -> list[str]:
    if value is None:
        return [RULE_WEIGHT_MISSING, RULE_WEIGHT_DELTA_MISSING]

    text = str(value).strip()
    if not text or text in {"-", "0()", "0"}:
        return [RULE_WEIGHT_MISSING, RULE_WEIGHT_DELTA_MISSING]

    match = re.fullmatch(r"(?P<weight>\d+)(?:\((?P<delta>[+-]?\d+)\))?", text)
    if match is None:
        return [RULE_WEIGHT_PARSE_FAILED, RULE_WEIGHT_DELTA_PARSE_FAILED]

    flags: list[str] = []
    weight = _safe_float(match.group("weight"))
    if weight is None:
        flags.append(RULE_WEIGHT_PARSE_FAILED)
    elif weight < 200 or weight > 650:
        flags.append(RULE_WEIGHT_OUTLIER)

    delta_raw = match.group("delta")
    if delta_raw is None:
        flags.append(RULE_WEIGHT_DELTA_MISSING)
    else:
        delta = _safe_float(delta_raw)
        if delta is None:
            flags.append(RULE_WEIGHT_DELTA_PARSE_FAILED)
        elif delta < -40 or delta > 40:
            flags.append(RULE_WEIGHT_DELTA_OUTLIER)

    return flags
