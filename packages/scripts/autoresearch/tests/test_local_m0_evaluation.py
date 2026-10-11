"""Source-backed synthetic forward evaluation; no historical accuracy claims."""

import asyncio
import base64
import hashlib
import sys
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import kra_result_snapshot
from autoresearch import local_m0_evaluation as e
from autoresearch import observed_history_seed as seed
from autoresearch import official_history_support as official
from autoresearch import prerace_hash_witness as witness
from autoresearch.observed_history_seed import save
from autoresearch.tests.test_kra_result_snapshot import envelope, row
from autoresearch.tests.test_kra_schedule import DATE, NOW, VENUES
from autoresearch.tests.test_local_m0_forward import environment as environment
from autoresearch.tests.test_observed_history_seed import execute
from autoresearch.tests.test_official_history_support import html

END = NOW + timedelta(days=3)


class ResultClock(datetime):
    @classmethod
    def now(cls, tz=None):
        return END


def files(root):
    return {
        str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()
    }


@pytest.fixture
def forward_case(environment, tmp_path, monkeypatch):
    data = environment
    run = data["run"]()
    monkeypatch.setattr(e, "CONTRACT_SHA", run["contract_sha256"])
    for module in (seed, official, kra_result_snapshot, witness):
        monkeypatch.setattr(module, "datetime", ResultClock)
    source = tmp_path / "results"
    source.mkdir()
    save(source / "plan.json", seed.make_plan(DATE, DATE))

    def result_response(request):
        meet = int(request.url.params["meet"])
        rows = [
            {
                **row(n, rank=n),
                "meet": meet,
                "rcDate": int(DATE),
                "hrNo": str(meet * 100 + n),
            }
            for n in range(1, 11)
        ]
        return httpx.Response(200, json=envelope(rows))

    asyncio.run(execute(source, result_response))
    frozen = seed.replay(source)
    sp = source / "seed.json"
    ss = save(sp, frozen)
    web = tmp_path / "official"

    def official_response(request):
        meet = int(request.url.params["meet"])
        records = [r for r in frozen["records"] if r["race_id"] == f"{DATE}_{meet}_1"]
        return httpx.Response(
            200,
            text=html(records, date=DATE, venue=VENUES[meet]),
            headers={"content-type": "text/html; charset=utf-8"},
        )

    async def collect():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(official_response)
        ) as client:
            return await official.collect(web, frozen, ss, client=client, delay=0)

    web_receipt = asyncio.run(collect())
    study = e.forward.read(data["root"] / DATE / "study.json")
    plan = {
        "format_version": "kra-versioned-result-observations-v1",
        "race_dates": [DATE],
        "seed_root": str(source),
        "seed_path": str(sp),
        "seed_sha256": ss,
        "official_directory": str(web),
        "official_archive_sha256": web_receipt["sha256"],
        "schedule_capture": study["schedule_capture"],
        "schedule_sha256": study["universe"]["capture_manifest_sha256"],
    }
    op = tmp_path / "outcome-plan.json"
    os = save(op, plan)
    cp = Path(run["commitment_path"])
    data.update(
        commitment=cp,
        commitment_sha=run["commitment_sha256"],
        outcome_plan=op,
        outcome_sha=os,
        evaluated=END + timedelta(hours=1),
    )
    return data


def publication(case, tmp_path, *, merged=None, raw=None):
    content = raw if raw is not None else case["commitment"].read_bytes()
    commit, doc, number = "a" * 40, "data/test-commitment.json", 123
    stamp = (merged or NOW + timedelta(hours=1)).isoformat()
    pull = {
        "merged": True,
        "state": "closed",
        "number": number,
        "base": {"repo": {"full_name": witness.REPOSITORY}},
        "html_url": f"https://github.com/{witness.REPOSITORY}/pull/{number}",
        "merge_commit_sha": commit,
        "merged_at": stamp,
    }
    body = {
        "type": "file",
        "encoding": "base64",
        "path": doc,
        "html_url": f"https://github.com/{witness.REPOSITORY}/blob/{commit}/{doc}",
        "content": base64.b64encode(content).decode(),
        "size": len(content),
        "sha": hashlib.sha1(
            b"blob " + str(len(content)).encode() + b"\0" + content
        ).hexdigest(),
    }
    directory = tmp_path / "witness"
    directory.mkdir()
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200, json=pull if "/pulls/" in str(request.url) else body
            )
        )
    ) as client:
        return witness.collect_publication(
            directory, number=number, document=doc, client=client
        )


def evaluate(case, **kwargs):
    return e.evaluate(
        case["root"],
        case["root"].parent,
        case["commitment"],
        case["commitment_sha"],
        outcome_plan=case["outcome_plan"],
        outcome_sha=case["outcome_sha"],
        evaluated_at=case["evaluated"],
        **kwargs,
    )


def test_source_backed_positive_comparison_and_no_archive_mutation(
    forward_case, tmp_path
):
    case = forward_case
    before = files(case["root"])
    result = evaluate(case, publication=publication(case, tmp_path))
    assert result["full_population_verified"]
    assert result["metrics"]["denominator"] == 4
    assert result["metrics"]["counts"] == {"verified_hit": 4}
    assert result["metrics"]["exact_hit_rate"] == 1
    assert not result["official_finality_verified"]
    assert files(case["root"]) == before


def test_local_matches_are_pending_without_independent_publication(forward_case):
    result = evaluate(forward_case)
    assert result["local_whole_block_replayed"]
    assert not result["full_population_verified"]
    assert all(r["local_combination_match_diagnostic"] for r in result["ledger"])
    assert result["metrics"]["counts"] == {"pending_evidence": 4}
    assert result["metrics"]["denominator"] is None
    assert result["metrics"]["exact_hit_rate"] is None
    assert not result["metrics"]["counts_as_70_percent_evidence"]


def test_publication_at_cutoff_is_not_timely(forward_case, tmp_path):
    case = forward_case
    study = e.forward.read(case["root"] / DATE / "study.json")
    cutoff = witness.timestamp(study["universe"]["races"][0]["feature_cutoff_at"])
    result = evaluate(case, publication=publication(case, tmp_path, merged=cutoff))
    assert not result["full_population_verified"]
    assert result["metrics"]["exact_hit_rate"] is None


def test_outcome_policy_changes_require_explicit_new_review(forward_case, monkeypatch):
    original = e.replay_plan

    def changed(*args):
        result = original(*args)
        result["observation_policy_sha256"] = "0" * 64
        return result

    monkeypatch.setattr(e, "replay_plan", changed)
    with pytest.raises(ValueError, match="outcome_policy_changed"):
        evaluate(forward_case)


def test_unrelated_published_document_cannot_witness_predictions(
    forward_case, tmp_path
):
    with pytest.raises(ValueError, match="not_selected_commitment"):
        evaluate(
            forward_case,
            publication=publication(
                forward_case, tmp_path, raw=b"source code is public"
            ),
        )


def test_tampered_packet_stays_in_full_population(forward_case, tmp_path):
    case = forward_case
    proof = publication(case, tmp_path)
    path = next((case["root"] / DATE).glob("prediction_*.json"))
    path.write_bytes(path.read_bytes() + b" ")
    result = evaluate(case, publication=proof)
    assert result["metrics"]["denominator"] == 4
    assert result["metrics"]["counts"] == {"verified_hit": 3, "pending_evidence": 1}
    assert result["metrics"]["evidence_identification_bounds"] == [0.75, 1.0]
    assert result["metrics"]["exact_hit_rate"] is None


def test_lost_readback_is_not_created_by_evaluation(forward_case, tmp_path):
    case = forward_case
    proof = publication(case, tmp_path)
    path = next((case["root"] / DATE).glob("observation_*.json"))
    path.unlink()
    result = evaluate(case, publication=proof)
    assert not path.exists()
    assert result["metrics"]["counts"]["pending_evidence"] == 1


def test_partial_block_never_becomes_smaller_study(environment, monkeypatch):
    case = environment
    monkeypatch.setattr(e.inference, "DATES", (DATE, "20261017", "20261018"))
    run = case["run"]()
    monkeypatch.setattr(e, "CONTRACT_SHA", run["contract_sha256"])
    result = e.evaluate(
        case["root"],
        case["root"].parent,
        Path(run["commitment_path"]),
        run["commitment_sha256"],
        evaluated_at=END,
    )
    assert len(result["days"]) == 3
    assert len(result["ledger"]) == 4
    assert result["metrics"]["denominator"] is None
    assert not result["local_whole_block_replayed"]


def test_historical_result_plan_rejected_before_comparison(forward_case, tmp_path):
    case = forward_case.copy()
    plan = e.forward.read(case["outcome_plan"])
    plan["race_dates"] = ["20261010"]
    case["outcome_plan"] = tmp_path / "historical.json"
    case["outcome_sha"] = save(case["outcome_plan"], plan)
    with pytest.raises(ValueError, match="historical_or_wrong_outcome_dates"):
        evaluate(case)


def test_historical_rehearsal_is_not_a_commitment(forward_case, tmp_path):
    case = forward_case.copy()
    case["commitment"] = tmp_path / "rehearsal.json"
    case["commitment_sha"] = save(
        case["commitment"], {"format_version": "historical-rehearsal"}
    )
    with pytest.raises(ValueError, match="commitment_contract_conflict"):
        evaluate(case)


@pytest.mark.parametrize(
    "states,exact,bounds",
    [
        (["verified_hit", "verified_miss"], 0.5, [0.5, 0.5]),
        (["verified_hit", "pending_evidence"], None, [0.5, 1]),
        (["verified_hit", "undefined_target"], None, None),
    ],
)
def test_full_denominator_and_undefined_target_semantics(states, exact, bounds):
    result = e.aggregate(
        [
            {"evaluation_status": s, "target_defined": s != "undefined_target"}
            for s in states
        ],
        full_population_verified=True,
    )
    assert result["denominator"] == 2
    assert result["exact_hit_rate"] == exact
    assert result["evidence_identification_bounds"] == bounds


def test_unknown_population_has_no_rate_even_with_observed_hit():
    result = e.aggregate(
        [{"evaluation_status": "verified_hit", "target_defined": True}],
        full_population_verified=False,
    )
    assert result["denominator"] is None
    assert result["exact_hit_rate"] is None
    assert result["evidence_identification_bounds"] is None


def test_missing_submission_is_failure_not_extra_upper_bound(forward_case, tmp_path):
    case = forward_case.copy()
    commit = e.forward.read(case["commitment"])
    slot = commit["days"][0]["races"][0]
    for kind, key in (
        ("prediction", "packet_sha256"),
        ("observation", "observation_sha256"),
    ):
        (case["root"] / DATE / f"{kind}_{slot['race_id']}.json").unlink()
        slot.pop(key)
    case["commitment"] = tmp_path / "missing-commitment.json"
    case["commitment_sha"] = save(case["commitment"], commit)
    result = evaluate(case, publication=publication(case, tmp_path))
    assert result["metrics"]["counts"] == {"verified_miss": 1, "verified_hit": 3}
    assert result["metrics"]["exact_hit_rate"] == 0.75


def test_published_snapshot_does_not_import_newer_unbound_prediction(
    forward_case, tmp_path
):
    case = forward_case.copy()
    commit = e.forward.read(case["commitment"])
    commit["days"][0]["races"][0].pop("packet_sha256")
    case["commitment"] = tmp_path / "earlier-commitment.json"
    case["commitment_sha"] = save(case["commitment"], commit)
    result = evaluate(case, publication=publication(case, tmp_path))
    assert result["metrics"]["counts"]["pending_evidence"] == 1


def test_unknown_live_card_is_not_zero_race_success(environment, monkeypatch):
    case = environment
    case["state"]["unpublished"] = True
    run = case["run"]()
    monkeypatch.setattr(e, "CONTRACT_SHA", run["contract_sha256"])
    result = e.evaluate(
        case["root"],
        case["root"].parent,
        Path(run["commitment_path"]),
        run["commitment_sha256"],
        evaluated_at=END,
    )
    assert result["metrics"]["denominator"] is None
    assert result["ledger"] == []
    assert not result["metrics"]["fully_evaluated"]


def test_unknown_target_is_not_assumed_to_have_a_binary_answer():
    result = e.aggregate(
        [
            {"evaluation_status": "verified_hit", "target_defined": True},
            {"evaluation_status": "pending_evidence", "target_defined": None},
        ],
        full_population_verified=True,
    )
    assert result["denominator"] == 2
    assert result["verified_hit_share_full_universe"] == 0.5
    assert result["exact_hit_rate"] is None
    assert result["evidence_identification_bounds"] is None
    assert result["target_definition_unknown_count"] == 1


def test_cli_cannot_write_into_canonical_archive(forward_case):
    case = forward_case
    before = files(case["root"])
    with pytest.raises(SystemExit):
        e.main(
            [
                "--root",
                str(case["root"]),
                "--model-dir",
                str(case["root"].parent),
                "--commitment",
                str(case["commitment"]),
                "--commitment-sha256",
                case["commitment_sha"],
                "--output",
                str(case["root"] / "new-evaluation.json"),
            ]
        )
    assert files(case["root"]) == before


def test_mismatch_is_exact_miss_and_void_is_not_binary_failure():
    prediction = {
        "status": "published_before_cutoff",
        "local_combination": ["1", "2", "3"],
    }
    race = {"feature_cutoff_at": NOW.isoformat()}
    for outcome, expected in (
        (
            {
                "status": "unique_top3_observed",
                "observed_top3_horse_ids": ["1", "2", "4"],
            },
            "verified_miss",
        ),
        ({"status": "void_reported_no_top3"}, "undefined_target"),
        ({"status": "source_conflict"}, "pending_evidence"),
        (None, "pending_evidence"),
    ):
        status, _ = e.classify(
            prediction, outcome, race, evaluated=END, population_verified=True
        )
        assert status == expected


def test_extra_result_does_not_replace_frozen_universe(
    forward_case, tmp_path, monkeypatch
):
    original = e.replay_plan

    def extra(*args):
        result = original(*args)
        result["extra_api_races"] = [f"{DATE}_1_2"]
        return result

    monkeypatch.setattr(e, "replay_plan", extra)
    result = evaluate(forward_case, publication=publication(forward_case, tmp_path))
    assert len(result["ledger"]) == 4
    assert not result["full_population_verified"]
    assert result["metrics"]["exact_hit_rate"] is None


def test_corrupted_universe_aborts_instead_of_scoring_a_subset(forward_case):
    case = forward_case
    path = case["root"] / DATE / "study.json"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="artifact_pin_mismatch"):
        evaluate(case)


def test_original_model_completion_after_target_is_rejected(forward_case):
    case = forward_case
    case["receipt"]["completed_at"] = END.isoformat()
    with pytest.raises(ValueError, match="model_fitted_after_target"):
        evaluate(case)
