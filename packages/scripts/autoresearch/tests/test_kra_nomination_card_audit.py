"""The nomination audit counts every declaration and never collects or scores."""

import sys
from datetime import timedelta
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import kra_nomination_card_audit as audit
from autoresearch import local_m0_inference, prerace_hash_witness
from autoresearch.observed_history_seed import pin, save
from autoresearch.restricted_cohort import horse_id, sha256
from autoresearch.tests.condition_forward_fixture import archive_publication
from autoresearch.tests.test_kra_entry_scope_intake import (
    DUE,
    answer,
    make_intake_inputs,
    model_rows,
    run,
)
from autoresearch.tests.test_kra_entry_scope_witness import AFTER, PULL, ProviderClock
from autoresearch.tests.test_kra_schedule import DATE, NOW

MAINLAND = "\uad6d5\ub4f1\uae09"
JEJU = "\uc81c5\ub4f1\uae09"
AUDIT_TIME = NOW + timedelta(hours=2)


def declaration(meet, idx):
    return model_rows(meet)[idx]


def nominee(meet, idx, *, wrong_id=None, wrong_name=None):
    declared = declaration(meet, idx)
    printed = wrong_id or declared["hrNo"]
    return {
        "profile_id_as_printed": printed,
        "horse_id": horse_id(printed),
        "printed_name": wrong_name or declared["hrName"],
        "profile_navigation_meet": min(meet, 3),
        "rating_as_printed": None,
        **(
            dict(zip(audit.RANK_FIELDS, ["2026/10/11", "3.3", None, "4"], strict=True))
            if meet == 2
            else dict(zip(audit.PRIZE_FIELDS, [0, 6000], strict=True))
        ),
    }


def detail(meet, rows, source, *, distance="1200M"):
    return {
        "physical_meet": meet,
        "feature_layout": "jeju_printed_rank_summaries"
        if meet == 2
        else "appearance_prizes",
        "not_printed": list(audit.PRIZE_FIELDS if meet == 2 else audit.RANK_FIELDS),
        "printed_conditions": [f"{JEJU if meet == 2 else MAINLAND} {distance} rule"],
        "join_status": "profile_id_only_not_final_declared",
        "earlier_list_count": len(rows),
        "detail_count": len(rows),
        "rows": rows,
        "source": source,
    }


def source_packet(root, monkeypatch, *, merged=NOW - timedelta(minutes=5)):
    locate = root / "nomination"
    locate.mkdir()
    raw = locate / "source.html"
    raw.write_bytes(b"synthetic official packet receipt")
    ref = pin(root, raw)
    source = {
        **dict.fromkeys(("request", "receipt", "own_parent", "raw"), ref),
        "byte_count": raw.stat().st_size,
        "observed_at": (NOW - timedelta(minutes=10)).isoformat(),
        "http_status": 200,
    }
    details = {
        f"{DATE}_2_1": detail(2, [nominee(2, 0)], source),
        f"{DATE}_3_1": detail(
            3,
            [
                nominee(3, 0),
                nominee(3, 1, wrong_name="Old alias"),
                nominee(3, 2, wrong_id="1234567"),
            ],
            source,
        ),
        f"{DATE}_4_1": detail(4, [nominee(4, 0)], source, distance="1400M"),
    }
    without = [f"{DATE}_1_1", f"{DATE}_4_2"]
    path = locate / "nomination-input-packet.json"
    digest = save(
        path,
        {
            "format": audit.NOMINATION_FORMAT,
            "final_population_and_cutoff": None,
            "eligible_training_or_prediction": False,
            "observed_fields": sorted([*details, *without]),
            "detail_fields": details,
            "without_detail": without,
            "separate_weekly_reports": [source],
        },
    )
    note = ("`" + digest + "`.\n").encode()
    note = b"Nomination input packet SHA256: " + note
    monkeypatch.setattr(audit, "NOMINATION_PACKET_SHA", digest)
    monkeypatch.setattr(audit, "NOMINATION_DOCUMENT_SHA", sha256(note))
    archive_publication(
        locate / "public-note-witness",
        note,
        audit.NOMINATION_PULL,
        audit.NOMINATION_DOCUMENT,
        merged,
        AFTER,
    )
    return path


@pytest.fixture
def whole_card(tmp_path, monkeypatch):
    def gateway(request):
        meet = int(request.url.params["meet"])
        rows = [
            row | {"rank": JEJU if meet == 2 else MAINLAND, "rcDist": 1200}
            for row in model_rows(meet)
        ]
        return answer(rows, int(request.url.params["pageNo"]))

    def prepare(*, card_merged=NOW + timedelta(hours=1), **source_options):
        monkeypatch.setattr(audit, "now", lambda: AUDIT_TIME)
        monkeypatch.setattr(audit.card_witness, "now", lambda: AUDIT_TIME)
        monkeypatch.setattr(audit.publication, "datetime", ProviderClock)
        monkeypatch.setattr(prerace_hash_witness, "datetime", ProviderClock)
        scope = make_intake_inputs(tmp_path)
        (path, receipt), calls = run(scope, provide=gateway)
        assert receipt["status"] == "captured_locally" and len(calls) == 4
        reference = pin(tmp_path, path)
        original = {
            "schedule_sha256": scope[1]["sha256"],
            "first_cutoff": DUE.isoformat(),
        }
        marker = audit.card_witness.stage(
            tmp_path, reference, **original, clock=lambda: NOW
        )
        digest = pin(tmp_path, path.with_name(audit.card_witness.PACKET_NAME))["sha256"]
        archive_publication(
            path.with_name(audit.card_witness.ARCHIVE_NAME),
            marker,
            PULL,
            audit.card_witness.publication_document(digest),
            card_merged,
            AFTER,
        )
        nomination = source_packet(tmp_path, monkeypatch, **source_options)
        return (
            (tmp_path, nomination, reference),
            {
                **original,
                "packet_sha256": digest,
                "pull": PULL,
            },
            path,
        )

    return prepare


def test_audit_replays_both_witnesses_and_preserves_full_card(whole_card, monkeypatch):
    args, original, _ = whole_card()

    def disabled(*_args, **_kwargs):
        pytest.fail("a coverage diagnostic cannot collect or score")

    monkeypatch.setattr(httpx, "Client", disabled)
    monkeypatch.setattr(httpx, "AsyncClient", disabled)
    monkeypatch.setattr(local_m0_inference, "score_capture", disabled)
    before = {p: p.read_bytes() for p in args[0].rglob("*") if p.is_file()}
    result = audit.audit(*args, **original)
    assert result == audit.audit(*args, **original)
    assert {p: p.read_bytes() for p in args[0].rglob("*") if p.is_file()} == before
    assert result["race_count"] == 4 and result["declaration_count"] == 40
    assert result["training_or_prediction_allowed"] is False
    assert result["preliminary_keys_not_in_verified_card"] == [f"{DATE}_4_2"]
    assert result["declaration_state_counts"] == {
        "observed_preliminary_without_detail": 10,
        "corroborated_id_and_name": 2,
        "same_id_name_conflict": 1,
        "same_name_different_id": 1,
        "no_same_race_profile_id": 16,
        "final_condition_conflict": 10,
    }
    assert result["operand_state_counts"]["recent_3_appearance_prize_won"] == {
        "no_verified_join": 38,
        "not_printed": 1,
        "observed_zero": 1,
    }
    assert result["operand_state_counts"]["recent_5_rank_literal"] == {
        "no_verified_join": 38,
        "not_printed": 1,
        "missing": 1,
    }
    for race in result["races"]:
        meet = int(race["race_id"].split("_")[1])
        assert [(r["gate"], r["horse_id"]) for r in race["declarations"]] == [
            (entry["chulNo"], horse_id(entry["hrNo"])) for entry in model_rows(meet)
        ]
        assert race["final_weight_rule_checked"] is False
    assert result["races"][2]["nomination_only_profile_ids"] == ["1234567"]
    assert "Fixture" not in str(result)


@pytest.mark.parametrize(
    ("options", "error"),
    [
        ({"card_merged": DUE}, "nomination_final_card_not_witnessed_in_time"),
        ({"merged": DUE}, "nomination_packet_not_witnessed_in_time"),
    ],
)
def test_at_cutoff_publication_is_not_credited(whole_card, options, error):
    args, original, _ = whole_card(**options)
    with pytest.raises(ValueError, match=error):
        audit.audit(*args, **original)


@pytest.mark.parametrize("elapsed_before_start", [True, False])
def test_no_audit_after_original_cutoff(whole_card, monkeypatch, elapsed_before_start):
    args, original, _ = whole_card()
    times = iter([DUE] if elapsed_before_start else [AUDIT_TIME, DUE])
    monkeypatch.setattr(audit, "now", lambda: next(times))
    with pytest.raises(ValueError, match="nomination_audit_original_cutoff_elapsed"):
        audit.audit(*args, **original)


def test_original_receipt_cannot_be_replaced(whole_card):
    args, original, path = whole_card()
    path.write_bytes(b"{}")
    with pytest.raises(ValueError, match="scope_intake_source_pin_mismatch"):
        audit.audit(*args, **original)


@pytest.mark.parametrize(
    ("condition", "hold", "observed", "expected"),
    [
        ("unknown", False, NOW - timedelta(seconds=1), "final_condition_unknown"),
        ("observed", True, NOW - timedelta(seconds=1), "hold_nomination_detail"),
        ("observed", False, NOW, "nomination_not_earlier_than_final_observation"),
    ],
)
def test_unknown_conditions_and_source_stage_do_not_supply_operands(
    condition, hold, observed, expected
):
    field = detail(4, [nominee(4, 0)], {"observed_at": observed.isoformat()})
    if hold:
        field["earlier_list_count"] += 1
    projected = {
        "race_id": f"{DATE}_4_1",
        "meet": 4,
        "captured_at": NOW.isoformat(),
        "class_text": {"status": condition, "value": MAINLAND},
        "distance_m": {"status": "observed", "value": 1200},
        "roster": [declaration(4, 0)],
    }
    result = audit._compare(projected, field, True)
    assert result["state"] == expected
    assert set(result["declarations"][0]["operand_states"].values()) == {
        "no_verified_join"
    }
