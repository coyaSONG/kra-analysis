"""Whole-roster inputs, source-backed joins and immutable learning slots."""

import copy
import importlib
from datetime import timedelta
from types import SimpleNamespace

import pytest

from autoresearch import prospective_training_inputs as p
from autoresearch.tests import test_local_m0_forward as m0_fixtures
from autoresearch.tests.test_official_history_support import captured

environment = m0_fixtures.environment
raw_entry = m0_fixtures.raw_entry


@pytest.fixture
def body(tmp_path, monkeypatch):
    clock = p.timestamp("2026-10-14T09:00:00Z")
    monkeypatch.setattr(p, "now", lambda: clock)
    monkeypatch.setattr(p.forward, "now", lambda: clock)
    api = {
        "race_id": "20261016_1_1",
        "source": {"available_at": "2026-10-14T08:00:00Z", "manifest_sha256": "a" * 64},
        "feature_rows": [
            {
                "chul_no": n,
                "horse_id": str(100 + n),
                "features": p.inference.api_features(raw_entry(n)),
            }
            for n in (1, 2, 3)
        ],
    }
    history = {
        "race_id": api["race_id"],
        "lookback_start": "20260718",
        "lookback_end_exclusive": "20261016",
        "recent_start": "20260916",
        "response_unit_status_counts": {"missing": 360},
        "missing_response_units": [],
        "feature_rows": [
            {
                "chul_no": n,
                "horse_id": str(100 + n),
                "features": {
                    **dict(
                        zip(p.recency.FIELDS, [0, None, None, None, None], strict=True)
                    ),
                    **{
                        f"{k}_missing": index != 0
                        for index, k in enumerate(p.recency.FIELDS)
                    },
                },
                "ranked_lineage": [],
                "withheld_lineage": [],
            }
            for n in (1, 2, 3)
        ],
    }
    item = {
        "race": {
            "race_id": api["race_id"],
            "feature_cutoff_at": "2026-10-16T02:30:00Z",
        },
        "projected": api,
        "study_sha256": "b" * 64,
    }
    publication = {
        "merged_at": "2026-10-12T00:00:00Z",
        "merge_commit_sha": p.HISTORY_COMMIT,
        "document_sha256": "c" * 64,
    }
    packet = p.packet_body(
        item,
        history,
        "d" * 64,
        p.timestamp("2026-10-11T20:00:00Z"),
        publication,
        "prospective",
    )
    return packet, item, history


def test_exact_24_columns_and_null_history_keeps_roster(body):
    packet, item, history = body
    before = copy.deepcopy((item, history))
    assert len(packet["feature_rows"]) == 3
    for row, source in zip(
        packet["feature_rows"], item["projected"]["feature_rows"], strict=True
    ):
        assert set(row["features"]) == set(p.COLUMNS)
        assert len(row["features"]) == 24
        assert {k: row["features"][k] for k in p.API_COLUMNS} == source["features"]
        assert row["features"][p.recency.FIELDS[1]] is None
    assert (item, history) == before
    assert packet["training_approved"] is False


@pytest.mark.parametrize("change", ["missing", "duplicate", "horse", "gate", "race"])
def test_history_roster_must_equal_entire_input(body, change):
    _, item, history = body
    if change == "missing":
        history["feature_rows"].pop()
    elif change == "duplicate":
        history["feature_rows"].append(history["feature_rows"][0])
    elif change in ("horse", "gate"):
        history["feature_rows"][0]["horse_id" if change == "horse" else "chul_no"] = (
            "999" if change == "horse" else 9
        )
    else:
        history["race_id"] = "20261016_1_2"
    with pytest.raises(ValueError, match="mismatch"):
        p.join_features(item["projected"], history)


def test_label_changes_do_not_enter_input(body):
    _, item, history = body
    expected = p.join_features(item["projected"], history)
    item["projected"].update(label_top3=["999"], training_selected=False)
    history.update(label_top3=["101", "102", "103"], ordinary_result=False)
    assert p.join_features(item["projected"], history) == expected


def test_missing_flag_is_not_an_arbitrary_value(body):
    _, item, history = body
    history["feature_rows"][0]["features"][p.recency.FIELDS[1] + "_missing"] = 1
    with pytest.raises(ValueError, match="missing_flag"):
        p.join_features(item["projected"], history)


def test_first_slot_is_immutable_on_retry(tmp_path, monkeypatch, body):
    packet = body[0]
    first = p.seal(tmp_path, packet)
    before = {path: path.read_bytes() for path in tmp_path.iterdir()}
    monkeypatch.setattr(p, "now", lambda: p.timestamp("2026-10-14T10:00:00Z"))
    monkeypatch.setattr(p.forward, "now", p.now)
    second = p.seal(tmp_path, packet)
    assert second == first
    assert {path: path.read_bytes() for path in tmp_path.iterdir()} == before
    changed = copy.deepcopy(packet)
    changed["feature_rows"][0]["features"]["rating"] = 100
    with pytest.raises(ValueError, match="occupied_slot"):
        p.seal(tmp_path, changed)
    assert {path: path.read_bytes() for path in tmp_path.iterdir()} == before


@pytest.mark.parametrize("which", ["api", "history", "publication", "computed"])
def test_late_sources_and_completion_do_not_seal(tmp_path, monkeypatch, body, which):
    packet = body[0]
    late = "2026-10-16T02:30:00Z"
    if which == "api":
        packet["api_source"]["available_at"] = late
    elif which == "history":
        packet["history_source"]["available_at"] = late
    elif which == "publication":
        packet["history_source"]["public_existence_bound_at"] = late
    else:
        monkeypatch.setattr(p, "now", lambda: p.timestamp(late))
    with pytest.raises(ValueError, match="not_timely"):
        p.seal(tmp_path, packet)
    assert not list(tmp_path.iterdir())


def test_historical_replay_cannot_become_prospective_input(tmp_path, body):
    packet = body[0]
    packet.update(
        mode="historical_diagnostic", feature_cutoff_at="2026-10-10T02:30:00Z"
    )
    result = p.seal(tmp_path, packet)
    assert result["status"] == "historical_diagnostic"
    assert "history_not_proven_before_cutoff" in result["timing_reasons"]
    assert result["independent_packet_publication_verified"] is False
    assert result["observation"]["status"] == "local_persistence_timeliness_unproven"


def test_late_readback_does_not_rewrite_or_backdate(tmp_path, monkeypatch, body):
    packet = {**body[0], "materialized_at": p.now().isoformat()}
    path = tmp_path / f"input_{packet['race_id']}.json"
    p.save(path, packet)
    before = path.read_bytes()
    monkeypatch.setattr(p, "now", lambda: p.timestamp("2026-10-16T03:00:00Z"))
    monkeypatch.setattr(p.forward, "now", p.now)
    result = p.seal(tmp_path, body[0])
    assert result["status"] == "local_timeliness_unproven"
    assert path.read_bytes() == before


def test_source_backed_parent_history_to_packets_preserves_parent(
    tmp_path, monkeypatch, environment
):
    env = environment
    env["run"]()
    parent_sha = p.inference.sha256((env["root"] / "contract.json").read_bytes())
    monkeypatch.setattr(p, "CONTRACT_SHA", parent_sha)

    class CaptureClock(p.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 12, tzinfo=p.UTC).astimezone(tz)

    for name in (
        "observed_history_seed",
        "kra_result_snapshot",
        "kra_entry_sheet_snapshot",
        "official_history_support",
    ):
        monkeypatch.setattr(
            importlib.import_module("autoresearch." + name), "datetime", CaptureClock
        )
    hist_root, seed_path, seed_sha, _, archive, receipt = captured(tmp_path)
    monkeypatch.setattr(p, "SEED_SHA", seed_sha)
    monkeypatch.setattr(p, "ARCHIVE_SHA", receipt["sha256"])
    monkeypatch.setattr(p, "now", lambda: env["state"]["time"])
    publication = {
        "merged_at": (env["state"]["time"] - timedelta(days=1)).isoformat(),
        "merge_commit_sha": p.HISTORY_COMMIT,
        "document_sha256": "a" * 64,
    }
    monkeypatch.setattr(p, "history_publication", lambda directory: publication)
    args = SimpleNamespace(
        command="run",
        parent_root=env["root"],
        model_dir=tmp_path / "model",
        history_root=hist_root,
        seed=seed_path,
        archive_dir=archive,
        output_dir=tmp_path / "learning",
    )
    before = {
        path: path.read_bytes() for path in env["root"].rglob("*") if path.is_file()
    }
    report, _, _ = p.run(args)
    assert report["packet_count"] == report["locally_timely_prospective_count"] == 4
    assert report["days"][0]["race_count"] == 4
    assert report["independently_published_packet_count"] == 0
    assert report["training_approved"] is False
    assert {
        path: path.read_bytes() for path in env["root"].rglob("*") if path.is_file()
    } == before
    packets = list((args.output_dir / p.inference.SERIES).glob("input_*.json"))
    assert len(packets) == 4
    assert sum(len(p.forward.read(path)["feature_rows"]) for path in packets) == 40
    assert all(
        len(r["features"]) == 24
        for path in packets
        for r in p.forward.read(path)["feature_rows"]
    )
    first = {path: path.read_bytes() for path in packets}
    report2, _, _ = p.run(args)
    assert report2["packet_count"] == 4
    assert {path: path.read_bytes() for path in packets} == first
    raw = next(archive.glob("*.html"))
    raw.write_bytes(raw.read_bytes() + b" ")
    with pytest.raises(ValueError, match="pin_mismatch"):
        p.run(args)
    assert {path: path.read_bytes() for path in packets} == first


def test_failed_parent_capture_remains_in_whole_ledger(
    tmp_path, monkeypatch, environment
):
    env = environment
    env["state"]["fail_venue"] = 2
    env["run"]()
    monkeypatch.setattr(
        p,
        "CONTRACT_SHA",
        p.inference.sha256((env["root"] / "contract.json").read_bytes()),
    )
    days, items = p.parent_inputs(env["root"], tmp_path)
    assert len(days[0]["ledger"]) == days[0]["race_count"] == 4
    assert len(items) == 3
    missing = [r for r in days[0]["ledger"] if r["race_id"].split("_")[1] == "2"]
    assert missing[0]["status"] == "missing_m0_selected_capture"


def test_awaiting_card_never_invents_empty_population(
    tmp_path, monkeypatch, environment
):
    env = environment
    env["state"]["unpublished"] = True
    env["run"]()
    monkeypatch.setattr(
        p,
        "CONTRACT_SHA",
        p.inference.sha256((env["root"] / "contract.json").read_bytes()),
    )
    days, items = p.parent_inputs(env["root"], tmp_path)
    assert not items
    assert days[0]["status"] == "awaiting_card"
    assert days[0]["race_count"] is None


def test_invalid_study_stays_unknown_instead_of_a_small_population(
    tmp_path, monkeypatch, environment
):
    env = environment
    env["run"]()
    monkeypatch.setattr(
        p,
        "CONTRACT_SHA",
        p.inference.sha256((env["root"] / "contract.json").read_bytes()),
    )
    path = env["root"] / p.inference.DATES[0] / "study.json"
    study = p.forward.read(path)
    study["universe"]["races"].pop()
    path.write_bytes(p.encoded(study))
    days, items = p.parent_inputs(env["root"], tmp_path)
    assert not items
    assert days[0]["status"] == "parent_study_conflict"
    assert days[0]["race_count"] is None


def test_tampered_occupied_packet_is_not_overwritten(tmp_path, body):
    original = p.seal(tmp_path, body[0])
    path = tmp_path / f"input_{body[0]['race_id']}.json"
    packet = p.forward.read(path)
    packet["feature_rows"][0]["horse_id"] = "999"
    path.write_bytes(p.encoded(packet))
    damaged = path.read_bytes()
    with pytest.raises(ValueError, match="occupied_slot_conflict"):
        p.seal(tmp_path, body[0])
    assert path.read_bytes() == damaged
    assert p.inference.sha256(damaged) != original["packet_sha256"]


@pytest.mark.parametrize("layout", ["inline", "command"])
def test_history_publication_accepts_exact_pins_in_original_document(
    tmp_path, monkeypatch, layout
):
    raw = (
        f"`{p.SEED_SHA}` `{p.ARCHIVE_SHA}`"
        if layout == "inline"
        else f"```sh\n --seed-sha256 {p.SEED_SHA} \\\n --archive-sha256 {p.ARCHIVE_SHA}\n```"
    ).encode()
    witness = {"merge_commit_sha": p.HISTORY_COMMIT}
    monkeypatch.setattr(
        p, "collect_publication", lambda *args, **kwargs: (raw, witness)
    )
    assert p.history_publication(tmp_path) == witness


@pytest.mark.parametrize("change", ["substring", "missing", "other_commit"])
def test_history_publication_rejects_wrong_pins_or_commit(
    tmp_path, monkeypatch, change
):
    seed = p.SEED_SHA + "f" if change == "substring" else p.SEED_SHA
    archive = "0" * 64 if change == "missing" else p.ARCHIVE_SHA
    raw = f"{seed} {archive}".encode()
    witness = {
        "merge_commit_sha": "a" * 40 if change == "other_commit" else p.HISTORY_COMMIT
    }
    monkeypatch.setattr(
        p, "collect_publication", lambda *args, **kwargs: (raw, witness)
    )
    with pytest.raises(ValueError, match="publication_conflict"):
        p.history_publication(tmp_path)
