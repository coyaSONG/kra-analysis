"""Replay synthetic authoritative raw results on a separately witnessed fixed pair."""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import (
    fixed_pair_evaluation as evaluation,
)
from autoresearch import (
    fixed_pair_forward as forward,
)
from autoresearch import (
    kra_result_snapshot as result_source,
)
from autoresearch import (
    observed_history_seed as seed,
)
from autoresearch import (
    official_history_support as official,
)
from autoresearch import (
    versioned_result_observations as observation,
)
from autoresearch.restricted_cohort import encoded, parse_json, sha256
from autoresearch.tests import test_fixed_pair_forward as fixture
from autoresearch.tests.test_kra_entry_scope_intake import answer
from autoresearch.tests.test_official_history_support import html

VENUES = {
    1: "\uc11c\uc6b8",
    2: "\uc81c\uc8fc",
    3: "\ubd80\uacbd",
    4: "\uc601\ucc9c",
}
AFTER = fixture.DUE + timedelta(days=5)
EXCLUDED = "\ucd9c\uc804\uc81c\uc678"


@pytest.fixture
def reviewed(tmp_path, monkeypatch):
    model_rows = fixture.model_rows

    def complete_context(meet, n):
        return [
            r | ({"rcDist": 1800, "rank": "\uad6d3\ub4f1\uae09"} if meet == 4 else {})
            for r in model_rows(meet, n)
        ]

    monkeypatch.setattr(fixture, "model_rows", complete_context)
    card = fixture.card.__wrapped__(tmp_path, monkeypatch)
    fixture.run(card)
    _, protocol, raw, _ = fixture.local(card)
    verified = forward.inputs_for(card.root, card.receipt, protocol)
    saved = parse_json(raw)
    card.pair_sha = sha256(raw)
    card.races = {b["race"]["race_id"]: b for b in verified["bindings"]}
    card.slots = {row["race_id"]: row["predictions"] for row in saved["races"]}
    card.schedule = card.root / verified["schedule"]["path"]
    card.authority = card.ledger
    card.proofs = tuple(
        (
            pr,
            sha256(
                (
                    card.ledger / f"{role}-publication" / "published-document.md"
                ).read_bytes()
            ),
        )
        for role, pr in zip(("protocol", "approval"), fixture.PULLS[1:3], strict=True)
    )

    def publish(merged):
        pull = card.register(
            "prediction", fixture.PULLS[3], raw, merged, fixture.contract.OWNER
        )
        pull["created_at"] = fixture.at(3).isoformat()
        card.clock[0] = AFTER
        fixture.proof(card)

    card.publish = publish

    class Frozen(datetime):
        @classmethod
        def now(cls, tz=None):
            value = card.clock[0]
            return (
                value.astimezone(tz) if tz is not None else value.replace(tzinfo=None)
            )

    for module in (result_source, seed, official):
        monkeypatch.setattr(module, "datetime", Frozen)
    monkeypatch.setattr(evaluation, "now", lambda: card.clock[0])
    return card


def fake_result_sources(card, choice="M0", *, exceptions=False, extra=False):
    first, second, third, missing, conflict, wrong_roster, withdrawal, *_ = sorted(
        card.races
    )
    event_rows = {}
    for rid, binding in sorted(card.races.items()):
        if exceptions and rid == missing:
            continue
        roster = binding["shared_input"]["feature_rows"]
        horses = [r["horse_id"] for r in roster]
        chosen = card.slots[rid][choice]["horse_ids"] if rid == first else horses[-3:]
        ordering = [*chosen, *(h for h in horses if h not in chosen)]
        rows = []
        for item in roster:
            horse, gate = item["horse_id"], item["chul_no"]
            if exceptions and rid == withdrawal and gate == 1:
                continue
            rank = ordering.index(horse) + 1
            note, elapsed = "-", 60 + rank / 10
            if exceptions and rid == second and rank == 4:
                rank = 3
            if exceptions and rid == third:
                rank, note, elapsed = 98, observation.VOID_NOTE, 0
            if exceptions and rid == withdrawal and gate == 4:
                rank, note, elapsed = 94, EXCLUDED, 0
            if exceptions and rid == wrong_roster and gate == 1:
                horse = "99000111"
            rows.append(
                {
                    "chul_no": gate,
                    "horse_id": horse,
                    "raw_ord": rank,
                    "raw_rc_time": elapsed,
                    "raw_ord_bigo": note,
                }
            )
        event_rows[rid] = rows
    if extra:
        date, meet, _ = first.split("_")
        event_rows[f"{date}_{meet}_19"] = event_rows[first]
    official_rows = {rid: [dict(r) for r in rows] for rid, rows in event_rows.items()}
    if exceptions:
        official_rows[conflict][-1]["raw_ord"] = 6
    return event_rows, official_rows


def seal_results(
    card, name, choice="M0", *, exceptions=False, extra=False, captured_at=AFTER
):
    number = len(card.calls)
    card.clock[0] = captured_at
    event_rows, official_rows = fake_result_sources(
        card, choice, exceptions=exceptions, extra=extra
    )
    out = card.root / name
    history = out / "history"
    history.mkdir(parents=True)
    days = card.protocol["race_dates"]
    seed.save(history / "plan.json", seed.make_plan(days[0], days[-1], budget=12))

    def api_mock(request):
        day = request.url.params["rc_date"]
        meet = int(request.url.params["meet"])
        rows = [
            {
                "rcDate": int(day),
                "meet": meet,
                "rcNo": int(rid.split("_")[2]),
                "chulNo": r["chul_no"],
                "hrNo": r["horse_id"],
                "ord": r["raw_ord"],
                "ordBigo": r["raw_ord_bigo"],
                "rcTime": r["raw_rc_time"],
            }
            for rid, entries in event_rows.items()
            if rid.startswith(f"{day}_{meet}_")
            for r in entries
        ]
        return answer(rows, int(request.url.params["pageNo"]))

    asyncio.run(
        seed.collect(
            history, "fake-result-key", transport=httpx.MockTransport(api_mock), delay=0
        )
    )
    saved = seed.replay(history)
    seed_path = history / "selected-seed.json"
    seed_sha = seed.save(seed_path, saved)

    def official_mock(request):
        params = request.url.params
        if "realRcDate" in params:
            day, meet, number = (
                params[key] for key in ("realRcDate", "meet", "realRcNo")
            )
            rows = official_rows[f"{day}_{meet}_{number}"]
            body = html(rows, date=day, venue=VENUES[int(meet)]).replace(
                "\uc81c1\uacbd\uc8fc", f"\uc81c{number}\uacbd\uc8fc"
            )
            if all(r["raw_ord"] == 98 for r in rows):
                body = body.replace("<td>98</td>", "<td></td>").replace(
                    "<td>0:00.0</td>", "<td></td>"
                )
            if any(r["raw_ord"] == 94 for r in rows):
                body = body.replace("<td>94</td>", "<td></td>").replace(
                    "<td>0:00.0</td>", "<td></td>"
                )
        else:
            body = "<html></html>"
        return httpx.Response(
            200, text=body, headers={"content-type": "text/html; charset=utf-8"}
        )

    async def archive():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(official_mock)
        ) as client:
            return await official.collect(
                out / "official", saved, seed_sha, client=client, delay=0
            )

    archive_index = asyncio.run(archive())
    outcome = out / "outcome-plan.json"
    digest = seed.save(
        outcome,
        {
            "format_version": observation.FORMAT,
            "race_dates": days,
            "schedule_capture": str(card.schedule),
            "schedule_sha256": card.protocol["source"]["schedule_sha256"],
            "seed_root": str(history),
            "seed_path": str(seed_path),
            "seed_sha256": seed_sha,
            "official_directory": str(out / "official"),
            "official_archive_sha256": archive_index["sha256"],
        },
    )
    assert len(card.calls) == number
    return outcome, digest


def evaluate(card, **kwargs):
    return evaluation.evaluate(
        card.root,
        fixture.STUDY,
        card.receipt,
        card.authority,
        card.proofs,
        card.model_dirs,
        **kwargs,
    )


def test_report_is_read_only_and_one_target_correction_changes_the_winner(
    reviewed, monkeypatch
):
    card = reviewed
    card.publish(fixture.at(44))
    before = seal_results(card, "first-result-version")
    after = seal_results(card, "corrected-result-version", "API27")
    saved = {p: sha256(p.read_bytes()) for p in card.root.rglob("*") if p.is_file()}
    for name in ("Client", "AsyncClient"):
        monkeypatch.setattr(
            httpx, name, lambda **_: pytest.fail("evaluation must never fetch")
        )
    first = evaluate(card, pair_sha=card.pair_sha, plan=before)
    second = evaluate(card, pair_sha=card.pair_sha, plan=after, prior=before)
    assert first["fully_paired"] and second["fully_paired"]
    assert first["frozen_race_count"] == second["frozen_race_count"] == 14
    assert first["frozen_population_sha256"] == second["frozen_population_sha256"]
    assert first["prediction"] == second["prediction"]
    assert first["descriptive_winner"] == "M0"
    assert second["descriptive_winner"] == "API27"
    assert first["api27_minus_m0_pp"] == pytest.approx(-100 / 14)
    assert second["api27_minus_m0_pp"] == pytest.approx(100 / 14)
    assert second["arms"]["API27"]["exact_accuracy"] == pytest.approx(1 / 14)
    assert second["paired_counts"] == {
        "both": 0,
        "M0_only": 0,
        "API27_only": 1,
        "neither": 13,
    }
    correction = second["previous_version_comparison"]
    assert correction["descriptive_winner_changed"]
    assert (
        correction["changed_target_race_ids"]
        == correction["changed_evaluation_race_ids"]
    )
    assert correction["changed_target_race_ids"] == [min(card.races)]
    assert correction["prior_result_version"]["plan_sha256"] == before[1]
    assert second["result_version"]["plan_sha256"] == after[1]
    assert second["sample"]["blocks"] == 1 and second["sample"]["venue_days"] == 4
    groups = second["diagnostic_counts_only"]
    assert set(groups["distance_m"]) == {"1800", "unknown"}
    assert groups["distance_m"]["unknown"]["race_count"] == 13
    assert groups["class_text"]["\uad6d3\ub4f1\uae09"]["race_count"] == 1
    assert set(groups["physical_meet"]) == {"1", "2", "3", "4"}
    assert saved == {
        p: sha256(p.read_bytes()) for p in card.root.rglob("*") if p.is_file()
    }


def test_ties_void_missing_and_conflicts_never_become_verified_misses(reviewed):
    card = reviewed
    card.publish(fixture.at(44))
    plan = seal_results(card, "pending", exceptions=True)
    result = evaluate(card, pair_sha=card.pair_sha, plan=plan)
    assert result["frozen_race_count"] == 14
    assert not result["fully_paired"]
    assert (
        result["api27_minus_m0_pp"]
        is result["descriptive_winner"]
        is result["paired_counts"]
        is None
    )
    assert all(
        arm["denominator"] == 14 and arm["exact_accuracy"] is None
        for arm in result["arms"].values()
    )
    assert result["arms"]["M0"]["counts"] == {
        "verified_hit": 1,
        "verified_miss": 8,
        "undefined_target": 1,
        "pending_evidence": 4,
    }
    rows = result["ledger"]
    assert [row["outcome_status"] for row in rows[:7]] == [
        "unique_top3_observed",
        "top3_unresolved",
        "void_reported_no_top3",
        "source_missing",
        "source_conflict",
        "input_result_roster_conflict",
        "unique_top3_observed",
    ]
    assert rows[6]["roster_comparison"]["declared_not_in_api_result"] == 1
    assert rows[6]["result_exception_notes"] == {EXCLUDED: 1}
    assert rows[0]["official_result_evidence"]["capture"]["raw"]["sha256"]
    assert rows[0]["api_result_captures"][0]["capture_completed_at"]
    assert not result["official_finality_verified"]


def test_proven_late_only_misses_after_unique_results(reviewed):
    card = reviewed
    card.publish(fixture.DUE)
    unobserved = evaluate(card, pair_sha=card.pair_sha)
    assert unobserved["prediction"]["state"] == "proven_late_in_bound_slot"
    assert unobserved["arms"]["M0"]["counts"]["pending_evidence"] == 14
    assert unobserved["arms"]["M0"]["counts"]["verified_miss"] == 0
    plan = seal_results(card, "result-after-late")
    final = evaluate(card, pair_sha=card.pair_sha, plan=plan)
    assert final["descriptive_winner"] == "tie" and final["fully_paired"]
    assert final["paired_counts"]["neither"] == 14
    assert all(row["M0"]["selected_horse_ids"] is None for row in final["ledger"])


def test_missing_archive_and_runtime_drift_are_not_prediction_failures(
    reviewed, monkeypatch
):
    card = reviewed
    card.publish(fixture.at(44))
    plan = seal_results(card, "pending-proof")
    missing = evaluate(card, plan=plan)
    assert missing["arms"]["M0"]["counts"]["pending_evidence"] == 14
    assert missing["arms"]["M0"]["exact_accuracy"] is None
    monkeypatch.setattr(fixture.contract, "runtime_sha", lambda: "c" * 64)
    drift = evaluate(card, pair_sha=card.pair_sha, plan=plan)
    assert drift["prediction"]["state"] == "timely_public_bytes_inference_unverified"
    assert drift["prediction"]["external"]["document_sha256"] == card.pair_sha
    assert not drift["prediction"]["frozen_model_replay_verified"]
    assert drift["arms"]["M0"]["counts"] == missing["arms"]["M0"]["counts"]
    card.model_dirs = None
    no_models = evaluate(card, pair_sha=card.pair_sha, plan=plan)
    assert no_models["prediction"]["reason"] == "no_original_model_artifacts_selected"
    assert no_models["arms"] == drift["arms"]


def test_extra_result_and_wrong_scope_never_reduce_the_denominator(reviewed):
    card = reviewed
    card.publish(fixture.at(44))
    plan = seal_results(card, "extra", extra=True)
    result = evaluate(card, pair_sha=card.pair_sha, plan=plan)
    assert len(result["ledger"]) == result["frozen_race_count"] == 14
    assert not result["full_population_verified"]
    assert result["extra_api_result_ids"] == result["extra_official_result_ids"]
    assert len(result["extra_api_result_ids"]) == 1
    assert result["arms"]["M0"]["denominator"] is None
    assert result["arms"]["M0"]["counts"]["pending_evidence"] == 14
    wrong_scope = card.root / "wrong-outcome-plan.json"
    raw = encoded(parse_json(plan[0].read_bytes()) | {"schedule_sha256": "1" * 64})
    wrong_scope.write_bytes(raw)
    with pytest.raises(ValueError, match="result_plan_not_original_scope"):
        evaluate(card, pair_sha=card.pair_sha, plan=(wrong_scope, sha256(raw)))


def test_result_clock_before_original_start_cannot_be_used(reviewed):
    card = reviewed
    card.publish(fixture.at(44))
    plan = seal_results(card, "premature-result", captured_at=fixture.at(50))
    card.clock[0] = AFTER
    with pytest.raises(ValueError, match="result_identity_or_clock_conflict"):
        evaluate(card, pair_sha=card.pair_sha, plan=plan)
