from __future__ import annotations

import sys
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from autoresearch.offline_evaluation_dataset_job import (  # noqa: E402
    build_entry_snapshot_lookup,
    build_snapshot_race_data,
)
from evaluation.data_loading import RaceEvaluationDataLoader  # noqa: E402
from evaluation.predict_only_test import PredictionTester  # noqa: E402
from shared.read_contract import RaceKey, RaceSnapshot  # noqa: E402


def _make_snapshot_basic_data(
    race_date: str,
    race_number: int,
    *,
    weather: str = "맑음",
    starters: tuple[int, ...] = (1, 2, 3),
) -> dict:
    collected_at = f"{race_date[:4]}-{race_date[4:6]}-{race_date[6:8]}T10:30:00+09:00"
    items = [
        {
            "rcDate": race_date,
            "rcNo": race_number,
            "rcName": "일반",
            "meet": "서울",
            "rcDist": 1200,
            "track": "건조",
            "weather": weather,
            "budam": "별정A",
            "ageCond": "3세",
            "schStTime": "1100",
            "chulNo": chul_no,
            "hrNo": f"H{race_number}{chul_no:02d}",
            "hrName": f"테스트마-{chul_no}",
            "jkName": f"기수-{chul_no}",
            "jkNo": f"JK{chul_no:03d}",
            "trName": f"조교사-{chul_no}",
            "trNo": f"TR{chul_no:03d}",
            "owName": f"마주-{chul_no}",
            "owNo": f"OW{chul_no:03d}",
            "sex": "수",
            "age": 3,
            "name": "한국",
            "rating": 80 - chul_no,
            "wgBudam": 54 + (3 - chul_no) * 0.5,
            "wgBudamBigo": "-",
            "wgHr": f"45{chul_no}(+1)",
            "winOdds": float(chul_no),
            "plcOdds": float(chul_no) + 0.2,
            "hrDetail": {"rcCntT": 5, "ord1CntT": 1, "ord2CntT": 1, "ord3CntT": 1},
            "jkDetail": {"rcCntT": 10, "ord1CntT": 2, "ord2CntT": 1, "ord3CntT": 1},
            "trDetail": {"rcCntT": 8, "ord1CntT": 1, "ord2CntT": 1, "ord3CntT": 1},
        }
        for chul_no in starters
    ]
    horses = [
        {
            "chul_no": chul_no,
            "hr_no": f"H{race_number}{chul_no:02d}",
            "hrDetail": {"name": f"테스트마-{chul_no}"},
            "jkDetail": {"name": f"기수-{chul_no}"},
            "trDetail": {"name": f"조교사-{chul_no}"},
        }
        for chul_no in starters
    ]
    return {
        "collected_at": collected_at,
        "race_info": {"response": {"body": {"items": {"item": items}}}},
        "race_plan": {"sch_st_time": "1100"},
        "track": {"weather": weather},
        "cancelled_horses": [],
        "horses": horses,
    }


def _make_snapshot(
    race_date: str = "20250101",
    meet: int = 1,
    race_number: int = 1,
) -> RaceSnapshot:
    return RaceSnapshot(
        key=RaceKey(
            race_id=f"{race_date}_{meet}_{race_number}",
            race_date=race_date,
            meet=meet,
            race_number=race_number,
        ),
        collection_status="collected",
        result_status="collected",
        basic_data=_make_snapshot_basic_data(race_date, race_number),
        result_data={"top3": [1, 2, 3]},
        collected_at=f"{race_date[:4]}-{race_date[4:6]}-{race_date[6:8]}T10:30:00+09:00",
        updated_at=f"{race_date[:4]}-{race_date[4:6]}-{race_date[6:8]}T10:31:00+09:00",
    )


class _RecordingDBClient:
    def __init__(self, snapshot: RaceSnapshot) -> None:
        self.snapshot = snapshot
        self.lookups: list[dict[str, str]] = []

    def load_race_basic_data(self, race_id: str, *, lookup):
        self.lookups.append(lookup.to_dict())
        assert race_id == self.snapshot.race_id
        return deepcopy(self.snapshot.basic_data)

    def get_past_top3_stats_for_race(self, hr_nos, *, lookup, lookback_days):
        return {}


class _StrictLookupDBClient(_RecordingDBClient):
    def load_race_basic_data(self, race_id: str, *, lookup):
        actual = lookup.to_dict()
        expected = build_entry_snapshot_lookup(self.snapshot).to_dict()
        self.lookups.append(actual)
        if actual != expected:
            raise ValueError(
                f"snapshot lookup mismatch: expected {expected}, got {actual}"
            )
        return deepcopy(self.snapshot.basic_data)


def _build_prediction_tester(db_client: _RecordingDBClient) -> PredictionTester:
    tester = PredictionTester.__new__(PredictionTester)
    tester.db_client = db_client
    return tester


def _schema_contract_summary(report: dict[str, object]) -> dict[str, object]:
    raw_leakage_report = report["raw_leakage_report"]
    operational_dataset_report = report["operational_dataset_report"]
    return {
        "schema_version": report["schema_version"],
        "row_count": report["row_count"],
        "feature_count": report["feature_count"],
        "required_top_level_fields": report["required_top_level_fields"],
        "required_race_info_fields": report["required_race_info_fields"],
        "missing_top_level_fields": report["missing_top_level_fields"],
        "unexpected_top_level_fields": report["unexpected_top_level_fields"],
        "missing_race_info_fields": report["missing_race_info_fields"],
        "unexpected_race_info_fields": report["unexpected_race_info_fields"],
        "canonical_path_mismatches": report["canonical_path_mismatches"],
        "unexpected_computed_feature_fields": report[
            "unexpected_computed_feature_fields"
        ],
        "raw_leakage_passed": raw_leakage_report["passed"],
        "raw_leakage_issues": raw_leakage_report["issues"],
        "operational_dataset_passed": operational_dataset_report["passed"],
        "operational_dataset_violations": operational_dataset_report["violating_paths"],
    }


def test_evaluation_and_operational_paths_share_snapshot_lookup_anchor() -> None:
    snapshot = _make_snapshot()
    db_client = _RecordingDBClient(snapshot)
    loader = RaceEvaluationDataLoader(db_client, with_past_stats=False)
    tester = _build_prediction_tester(db_client)

    canonical_lookup = build_entry_snapshot_lookup(snapshot).to_dict()

    evaluation_payload = loader.load_race_data(
        {
            "race_id": snapshot.race_id,
            "race_date": snapshot.race_date,
            "entry_finalized_at": canonical_lookup["entry_snapshot_at"],
        }
    )
    operational_payload = tester.load_race_data(snapshot)

    assert evaluation_payload is not None
    assert operational_payload is not None
    assert db_client.lookups == [canonical_lookup, canonical_lookup]
    assert operational_payload["analysis_payload"]["source_lookup"] == canonical_lookup


def test_offline_evaluation_and_operational_paths_share_same_input_schema_contract() -> (
    None
):
    snapshot = _make_snapshot()
    db_client = _RecordingDBClient(snapshot)
    loader = RaceEvaluationDataLoader(db_client, with_past_stats=False)
    tester = _build_prediction_tester(db_client)

    offline_payload, timing_meta = build_snapshot_race_data(snapshot)
    evaluation_payload = loader.load_race_data(
        {
            "race_id": snapshot.race_id,
            "race_date": snapshot.race_date,
            "entry_snapshot_at": build_entry_snapshot_lookup(
                snapshot
            ).entry_snapshot_at,
        }
    )
    operational_loaded = tester.load_race_data(snapshot)

    assert offline_payload is not None
    assert evaluation_payload is not None
    assert operational_loaded is not None

    operational_payload = operational_loaded["prompt_payload"]
    assert _schema_contract_summary(
        offline_payload["input_schema"]
    ) == _schema_contract_summary(evaluation_payload["input_schema"])
    assert _schema_contract_summary(
        offline_payload["input_schema"]
    ) == _schema_contract_summary(operational_payload["input_schema"])
    assert offline_payload["race_info"] == evaluation_payload["race_info"]
    assert offline_payload["race_info"] == operational_payload["race_info"]
    assert offline_payload["horses"] == evaluation_payload["horses"]
    assert offline_payload["horses"] == operational_payload["horses"]
    assert (
        timing_meta["source_lookup"]
        == operational_loaded["analysis_payload"]["source_lookup"]
    )
    assert timing_meta["candidate_filter"] == evaluation_payload["candidate_filter"]
    assert (
        timing_meta["candidate_filter"]
        == operational_loaded["analysis_payload"]["candidate_filter"]
    )


def test_evaluation_loader_detects_snapshot_lookup_anchor_mismatch() -> None:
    snapshot = _make_snapshot()
    db_client = _StrictLookupDBClient(snapshot)
    loader = RaceEvaluationDataLoader(db_client, with_past_stats=False)

    payload = loader.load_race_data(
        {
            "race_id": snapshot.race_id,
            "race_date": snapshot.race_date,
            "entry_finalized_at": "2025-01-01T10:45:00+09:00",
        }
    )

    assert payload is None
    assert db_client.lookups == [
        {
            "race_id": snapshot.race_id,
            "race_date": snapshot.race_date,
            "entry_snapshot_at": "2025-01-01T10:45:00+09:00",
        }
    ]
