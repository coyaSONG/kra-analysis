from __future__ import annotations

import json
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.prerace_standard_loader import StandardizedPreracePayload
from shared.read_contract import RaceKey, RaceSnapshot

from autoresearch.offline_evaluation_dataset_job import (
    build_entry_snapshot_lookup,
    build_snapshot_bundle,
    build_snapshot_race_data,
    write_snapshot_bundle,
)


def _make_snapshot_basic_data(
    race_date: str,
    race_number: int,
    *,
    weather: str,
    starters: tuple[int, ...] = (1, 2, 3),
) -> dict:
    collected_at = f"{race_date[:4]}-{race_date[4:6]}-{race_date[6:8]}T10:30:00+09:00"
    items = [
        {
            "rcDate": race_date,
            "rcNo": str(race_number),
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
            "wgBudam": 55,
            "wgBudamBigo": "-",
            "wgHr": "450(+2)",
            "winOdds": float(chul_no),
            "plcOdds": float(chul_no) + 0.2,
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
    race_date: str,
    meet: int,
    race_number: int,
    *,
    weather: str = "맑음",
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
        basic_data=_make_snapshot_basic_data(race_date, race_number, weather=weather),
        result_data={"top3": [1, 2, 3]},
        collected_at=f"{race_date[:4]}-{race_date[4:6]}-{race_date[6:8]}T10:30:00+09:00",
        updated_at=f"{race_date[:4]}-{race_date[4:6]}-{race_date[6:8]}T10:31:00+09:00",
    )


class _FakeSnapshotQueryPort:
    def __init__(self, race_snapshots: list[RaceSnapshot]):
        self._snapshot_by_id = {
            snapshot.race_id: snapshot for snapshot in race_snapshots
        }
        self.lookups: list[dict[str, str]] = []

    def find_race_snapshots(
        self, date_filter: str | None = None, limit: int | None = None
    ):
        snapshots = list(self._snapshot_by_id.values())
        if date_filter:
            snapshots = [
                snapshot for snapshot in snapshots if snapshot.race_date == date_filter
            ]
        if limit is not None:
            snapshots = snapshots[:limit]
        return snapshots

    def load_race_basic_data(self, race_id: str, *, lookup):
        self.lookups.append(lookup.to_dict())
        basic_data = deepcopy(self._snapshot_by_id[race_id].basic_data)
        items = basic_data["race_info"]["response"]["body"]["items"]["item"]
        for item in items:
            item["weather"] = "비"
        basic_data["track"]["weather"] = "비"
        return basic_data

    def get_past_top3_stats_for_race(self, hr_nos, *, lookup, lookback_days=90):
        assert lookup.race_id in self._snapshot_by_id
        assert lookback_days == 90
        return {
            hr_no: {
                "recent_race_count": 4,
                "recent_win_count": 1,
                "recent_top3_count": 2,
                "recent_win_rate": 0.25,
                "recent_top3_rate": 0.5,
            }
            for hr_no in hr_nos
        }

    def close(self) -> None:
        return None


def test_build_entry_snapshot_lookup_uses_entry_finalized_at():
    snapshot = _make_snapshot("20250101", 1, 1)

    lookup = build_entry_snapshot_lookup(snapshot)

    assert lookup.race_id == "20250101_1_1"
    assert lookup.race_date == "20250101"
    assert lookup.entry_snapshot_at == "2025-01-01T10:30:00+09:00"


def test_build_snapshot_race_data_delegates_to_shared_snapshot_and_schema_modules(
    monkeypatch,
):
    snapshot = _make_snapshot("20250101", 1, 1)
    calls: list[dict] = []

    def fake_loader(basic_data, **kwargs):
        calls.append({"basic_data": basic_data, **kwargs})
        return StandardizedPreracePayload(
            race_id=kwargs["race_id"],
            race_date=kwargs["race_date"],
            meet=kwargs["meet"],
            lookup=kwargs["lookup"],
            basic_data=basic_data,
            enriched_data={},
            standard_payload={
                "race_id": kwargs["race_id"],
                "race_date": kwargs["race_date"],
                "meet": kwargs["meet"],
                "race_info": {
                    "rcDate": "20250101",
                    "rcNo": 1,
                    "rcDist": 1200,
                    "track": "건조",
                    "weather": "맑음",
                    "meet": "서울",
                },
                "horses": [{"chulNo": 1, "class_rank": "국6"}],
                "candidate_filter": {"status_counts": {"normal": 1}},
                "input_schema": {"schema_version": "alternative-ranking-input-v1"},
            },
            candidate_filter={"status_counts": {"normal": 1}},
            field_policy={"blocked_paths": []},
            operational_cutoff_status={
                "passed": True,
                "reason": "ok",
            },
            entry_change_audit={"source_present": False},
            removed_post_race_paths=(),
            entry_resolution_audit={"source": "entry_resolution"},
        )

    monkeypatch.setattr(
        "autoresearch.offline_evaluation_dataset_job.build_standardized_prerace_payload",
        fake_loader,
    )

    race_data, timing_meta = build_snapshot_race_data(snapshot)

    assert race_data is not None
    assert calls[0]["race_id"] == snapshot.race_id
    assert calls[0]["race_date"] == snapshot.race_date
    assert calls[0]["meet"] == "서울"
    assert (
        timing_meta["source_lookup"]["entry_snapshot_at"] == "2025-01-01T10:30:00+09:00"
    )
    assert timing_meta["entry_resolution_audit"] == {"source": "entry_resolution"}
    assert timing_meta["operational_cutoff_status"]["passed"] is True
    assert timing_meta["entry_change_audit"] == {"source_present": False}


def test_build_snapshot_race_data_can_inject_strict_past_stats():
    snapshot = _make_snapshot("20250101", 1, 1)
    query_port = _FakeSnapshotQueryPort([snapshot])

    race_data, timing_meta = build_snapshot_race_data(
        snapshot,
        query_port=query_port,
        with_past_stats=True,
    )

    assert race_data is not None
    horse = race_data["horses"][0]
    assert horse["past_stats"]["recent_race_count"] == 4
    assert horse["computed_features"]["recent_top3_count"] == 2
    assert horse["computed_features"]["recent_win_rate"] == 0.25
    assert timing_meta["operational_cutoff_status"]["passed"] is True


def test_write_snapshot_bundle_writes_t30_release_gate_report(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "autoresearch.offline_evaluation_dataset_job.write_split_manifests",
        lambda _manifests: None,
    )
    race = {
        "race_id": "race-1",
        "race_date": "20250101",
        "race_info": {
            "rcDate": "20250101",
            "rcNo": 1,
            "rcDist": 1200,
            "track": "건조",
            "weather": "맑음",
            "meet": "서울",
        },
        "horses": [{"chulNo": 1, "changed_jockey_flag": None}],
        "snapshot_meta": {
            "race_id": "race-1",
            "replay_status": "strict",
            "include_in_strict_dataset": True,
            "operational_cutoff_status": {
                "passed": True,
                "reason": "ok",
            },
            "entry_change_audit": {"source_present": False},
        },
    }
    bundle = {
        "created_at": datetime.fromisoformat("2026-04-27T09:00:00+09:00"),
        "split_manifests": {},
        "snapshots": {"mini_val": [race], "holdout": []},
        "timing_manifests": {"mini_val": [race["snapshot_meta"]], "holdout": []},
        "answer_key": {"meta": {}, "mini_val": {}, "holdout": {}},
    }

    write_snapshot_bundle(bundle, snapshot_dir=tmp_path)

    report = json.loads(
        (tmp_path / "mini_val_t30_release_gate_report.json").read_text(encoding="utf-8")
    )
    assert report["schema_version"] == "t30-release-gate-report-v1"
    assert report["passed"] is True
    assert report["entry_change_coverage"]["source_missing_race_count"] == 1


def test_build_snapshot_bundle_reloads_basic_data_via_common_lookup_contract():
    race_snapshots: list[RaceSnapshot] = []
    for race_date in (
        "20250101",
        "20250102",
        "20250103",
        "20250104",
        "20250105",
        "20250106",
    ):
        race_snapshots.append(_make_snapshot(race_date, 1, 1, weather="맑음"))
        race_snapshots.append(_make_snapshot(race_date, 3, 1, weather="맑음"))

    query_port = _FakeSnapshotQueryPort(race_snapshots)
    bundle = build_snapshot_bundle(
        race_snapshots,
        query_port=query_port,
        manifest_created_at="2026-04-10T12:00:00+09:00",
        holdout_minimum_race_count=4,
        mini_val_minimum_race_count=4,
    )

    assert len(query_port.lookups) == 8

    sample = bundle["snapshots"]["mini_val"][0]
    lookup_by_race_id = {lookup["race_id"]: lookup for lookup in query_port.lookups}
    assert sample["race_info"]["weather"] == "비"
    assert (
        sample["snapshot_meta"]["source_lookup"] == lookup_by_race_id[sample["race_id"]]
    )
