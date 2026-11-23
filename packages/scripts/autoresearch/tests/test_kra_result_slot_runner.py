"""Exercise the designated capture with existing parsers and no network."""

import asyncio
import sys
from datetime import timedelta
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "docs/research/tools"))

import kra_result_slot_runner as run

from autoresearch.kra_entry_sheet_snapshot import ENTRY_URL
from autoresearch.kra_result_snapshot import RESULT_URL
from autoresearch.observed_history_seed import pin, save
from autoresearch.restricted_cohort import parse_json
from autoresearch.tests import test_kra_walk_forward_enrollment as enrol
from autoresearch.tests import test_kra_walk_forward_fold as cases

study = cases.study
RULES_PULL = 1100


def _ref(root, path, payload):
    path = root / path
    return {"path": path.relative_to(root).as_posix(), "sha256": save(path, payload)}


@pytest.fixture
def operation(study, monkeypatch):
    monkeypatch.setattr(run.fold, "now", lambda: study.clock[0])
    root = study.root
    directory = root / ".cache/autoresearch"
    directory.mkdir(parents=True)
    policy = enrol._policy(root)
    before = study.training[0].cutoff - timedelta(seconds=10)
    cases.source.archive_publication(
        root / f"{run.enrollment.ARCHIVE_NAME}-{policy['sha256']}",
        run.enrollment.marker(policy["sha256"]),
        enrol.PULL,
        run.enrollment.publication_document(policy["sha256"]),
        before,
        before + timedelta(seconds=1),
    )

    def prepare(index=0, *, budget=12, policy_merge=before):
        slots = [
            {
                "week": week,
                "opens_at": card.result_time.isoformat(),
                "closes_at": (card.result_time + timedelta(minutes=10)).isoformat(),
                "receipt_pull": RULES_PULL + i,
                "api_request_budget": budget,
            }
            for i, (card, week) in enumerate(
                zip(study.training, enrol.WEEKS[:2], strict=True), 1
            )
        ]
        rules_path = directory / f"rules-{budget}-{policy_merge.timestamp()}.json"
        if rules_path.exists():
            rules = pin(root, rules_path)
        else:
            rules = _ref(
                root,
                rules_path,
                {
                    "format": run.witness.PLAN,
                    "enrollment_sha256": policy["sha256"],
                    "slots": slots,
                },
            )
            digest = rules["sha256"]
            cases.source.archive_publication(
                directory / f"result-slot-rules-publication-{digest}",
                run.witness.rule_marker(digest),
                RULES_PULL,
                run.witness.rule_document(digest),
                policy_merge,
                policy_merge + timedelta(seconds=1),
            )
        prefix_path = directory / f"prefix-{index}.json"
        inputs = (
            pin(root, prefix_path)
            if prefix_path.exists()
            else _ref(
                root,
                prefix_path,
                {
                    "format": run.INPUTS,
                    "training": [r.input_spec for r in study.training[: index + 1]],
                },
            )
        )
        study.clock[0] = study.training[index].result_time
        card = run.appointment(
            root,
            rules,
            policy,
            inputs,
            week=slots[index]["week"],
            rules_pull=RULES_PULL,
            enrollment_pull=enrol.PULL,
        )
        return card, rules

    return study, policy, prepare


def _sources(training, api_requests, web_requests, *, missing_venue=None):
    event_rows, official_rows = cases.results.fake_result_sources(training)

    def api(request):
        params = request.url.params
        day, meet, page = params["rc_date"], int(params["meet"]), int(params["pageNo"])
        base = str(request.url.copy_with(query=None))
        api_requests.append((base, day, meet, page))
        if base == ENTRY_URL:
            rows = [
                r | {"rcDate": int(day)}
                for r in cases.source.model_rows(meet, cases.source.FIELDS[meet])
            ]
        else:
            assert base == RESULT_URL
            rows = [
                {
                    "rcDate": int(day),
                    "rcNo": int(rid.split("_")[2]),
                    "chulNo": r["chul_no"],
                    "hrNo": r["horse_id"],
                    "ord": r["raw_ord"],
                    "ordBigo": r["raw_ord_bigo"],
                    "rcTime": r["raw_rc_time"],
                }
                | ({} if meet == missing_venue else {"meet": meet})
                for rid, entries in event_rows.items()
                if rid.startswith(f"{day}_{meet}_")
                for r in entries
            ]
        return cases.results.answer(rows, page)

    def web(request):
        params = request.url.params
        web_requests.append(str(request.url))
        if "realRcDate" in params:
            day, meet, number = (params[k] for k in ("realRcDate", "meet", "realRcNo"))
            rows = official_rows[f"{day}_{meet}_{number}"]
            body = cases.results.html(
                rows, date=day, venue=cases.results.VENUES[int(meet)]
            ).replace("\uc81c1\uacbd\uc8fc", f"\uc81c{number}\uacbd\uc8fc")
        else:
            body = "<html></html>"
        return httpx.Response(
            200, text=body, headers={"content-type": "text/html; charset=utf-8"}
        )

    return api, web


def _collect(card, api, web):
    return asyncio.run(
        run.collect(
            card,
            "synthetic-local-token",
            api_transport=httpx.MockTransport(api),
            official_transport=httpx.MockTransport(web),
            delays=(0, 0),
        )
    )


def _seal(study, card):
    study.clock[0] = run.timestamp(card.slot["closes_at"])
    marker = run.seal(card)
    terminal = card.folder / "terminal.json"
    assert parse_json(marker)["terminal_sha256"] == pin(card.root, terminal)["sha256"]
    assert run.seal(card) == marker
    return marker, parse_json(terminal.read_bytes())


def _no_request(_):
    pytest.fail("unexpected source request")


def test_whole_slot_closes_and_replays_the_same_versions_without_held_out_results(
    operation,
    monkeypatch,
):
    study, policy, prepare = operation
    selections = []
    for index in range(2):
        card, rules = prepare(index)
        api_calls, web_calls = [], []
        api, web = _sources(
            study.training[index], api_calls, web_calls, missing_venue=4
        )
        assert _collect(card, api, web)["state"] == "captured"
        assert len(api_calls) == 6  # Five result pages and one identity fallback.
        assert {(day, meet) for _, day, meet, _ in api_calls} == set(card.expected)
        assert len(web_calls) == len(set(web_calls)) == card.scope["race_count"] + 12
        assert all(day in card.scope["race_dates"] for _, day, _, _ in api_calls)
        assert not (card.folder / "terminal.json").exists()
        with pytest.raises(ValueError, match="result_slot_week_consumed"):
            _collect(card, _no_request, _no_request)
        marker, record = _seal(study, card)
        assert record["state"] == "observed"
        closed = study.clock[0]
        study.clock[0] += timedelta(seconds=2)

        def publish(
            directory,
            pull,
            document,
            digest,
            *,
            card=card,
            marker=marker,
            closed=closed,
        ):
            assert directory == card.folder / "terminal-publication"
            assert pull == card.slot["receipt_pull"]
            assert document == run.witness.slot_document(
                card.rule_sha, card.slot["week"]
            )
            assert digest == run.sha256(marker)
            return cases.source.archive_publication(
                directory,
                marker,
                pull,
                document,
                closed + timedelta(seconds=1),
                study.clock[0],
            )

        monkeypatch.setattr(run.publication, "capture", publish)
        assert (
            run.terminal_publication(card)["merged_at"]
            == (closed + timedelta(seconds=1)).isoformat()
        )
        path = card.folder / "outcome-plan.json"
        plan = pin(card.root, path)
        assert record["result_plan_sha256"] == plan["sha256"]
        report, candidate = cases.learning.seal(
            study.root,
            **study.training[index].input_spec,
            result_plan=(path, plan["sha256"]),
        )
        assert report["candidate_ready_for_review"] and not report["training_approved"]
        selections.append(
            study.plan["training"][index]
            | {"result_plan": plan, "candidate": candidate}
        )
    study.clock[0] = study.initial
    fold_plan = cases._plan(study, study.plan | {"training": selections})
    report = run.witness.verify(
        study.root,
        rules,
        policy,
        fold_plan,
        rules_pull=RULES_PULL,
        enrollment_pull=enrol.PULL,
    )
    assert report["selected_result_plans"] == [r["result_plan"] for r in selections]
    assert not report["training_approved"] and not report["result_targets_admitted"]
    assert (
        parse_json(run.fold.stage(study.root, fold_plan))["format"] == run.fold.MARKER
    )


@pytest.mark.parametrize(
    ("status", "body", "reason"),
    [
        (
            403,
            b'{"OpenAPI_ServiceResponse":{"cmmMsgHeader":{"returnReasonCode":"30"}}}',
            "authentication_error",
        ),
        (429, b"", "rate_limited"),
        (
            200,
            b'{"OpenAPI_ServiceResponse":{"cmmMsgHeader":{"returnReasonCode":"22"}}}',
            "rate_limited",
        ),
        (200, b"", "empty_unconfirmed"),
        (200, None, "empty_unconfirmed"),
    ],
)
def test_api_failure_stops_without_retry_or_successful_version(
    operation, status, body, reason
):
    study, _, prepare = operation
    card, _ = prepare()
    calls = []

    def failure(request):
        calls.append(request.url.params["pageNo"])
        return (
            cases.results.answer([], 1)
            if body is None
            else httpx.Response(status, content=body)
        )

    assert _collect(card, failure, _no_request)["reason"] == reason
    assert calls == ["1"]
    _, record = _seal(study, card)
    assert record["state"] == "failed" and record["result_plan_sha256"] is None
    assert "synthetic-local-token" not in (card.folder / "finish.json").read_text()


def test_budget_and_official_denial_stop_before_any_follow_up(operation):
    study, _, prepare = operation
    card, _ = prepare(budget=1)
    api_calls, web_calls = [], []
    api, _ = _sources(study.training[0], api_calls, web_calls)
    assert (
        _collect(card, api, _no_request)["reason"] == "result_slot_api_budget_exhausted"
    )
    assert len(api_calls) == 1
    assert _seal(study, card)[1]["state"] == "failed"

    card, _ = prepare(1)
    api, _ = _sources(study.training[1], api_calls, web_calls)

    def denied(request):
        web_calls.append(request.url)
        return httpx.Response(403)

    assert _collect(card, api, denied)["reason"] == "access_denied"
    assert len(web_calls) == 1
    assert _seal(study, card)[1]["state"] == "failed"


def test_consumed_interruption_cannot_be_reopened_under_another_rule(operation):
    study, _, prepare = operation
    card, _ = prepare()

    def interrupt(_):
        raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        _collect(card, interrupt, _no_request)
    assert card.claim.is_file()
    assert (card.folder / "history/requests/000001.json").is_file()
    assert not (card.folder / "finish.json").exists()
    other, _ = prepare(budget=13)
    assert other.claim == card.claim and other.folder != card.folder
    with pytest.raises(ValueError, match="result_slot_week_consumed"):
        _collect(other, _no_request, _no_request)
    assert _seal(study, card)[1]["state"] == "failed"
    with pytest.raises(ValueError, match="result_slot_other_week_claim"):
        run.seal(other)
    assert not other.folder.exists()


def test_missing_window_stays_not_run_and_cutoff_is_exclusive(operation):
    study, _, prepare = operation
    card, _ = prepare()
    study.clock[0] -= timedelta(microseconds=1)
    with pytest.raises(run.Stop, match="outside_designated_observation_window"):
        _collect(card, _no_request, _no_request)
    assert not card.claim.exists()
    with pytest.raises(ValueError, match="result_slot_not_closed"):
        run.seal(card)
    assert _seal(study, card)[1]["state"] == "not_run"
    with pytest.raises(run.Stop, match="outside_designated_observation_window"):
        _collect(card, _no_request, _no_request)


def test_crossing_close_during_first_reply_never_issues_next_request(operation):
    study, _, prepare = operation
    card, _ = prepare()
    api_calls = []
    api, _ = _sources(study.training[0], api_calls, [])

    def late(request):
        study.clock[0] = run.timestamp(card.slot["closes_at"])
        return api(request)

    assert (
        _collect(card, late, _no_request)["reason"]
        == "outside_designated_observation_window"
    )
    assert len(api_calls) == 1
    assert _seal(study, card)[1]["state"] == "failed"


def test_rule_published_at_original_cutoff_cannot_start(operation):
    study, _, prepare = operation
    with pytest.raises(ValueError, match="result_slot_rules_not_published_before"):
        prepare(policy_merge=study.training[0].cutoff)
    assert not (study.root / ".git" / run.CLAIMS).exists()


def test_changed_raw_body_after_capture_holds_the_closure(operation):
    study, _, prepare = operation
    card, _ = prepare()
    api, web = _sources(study.training[0], [], [])
    assert _collect(card, api, web)["state"] == "captured"
    raw = next((card.folder / "official").glob("*.html"))
    raw.write_bytes(b"untrusted replacement fixture")
    assert _seal(study, card)[1]["state"] == "failed"


def test_official_http_success_without_the_race_body_is_unconfirmed(operation):
    study, _, prepare = operation
    card, _ = prepare()
    api, _ = _sources(study.training[0], [], [])
    calls = []

    def pending(request):
        calls.append(request.url)
        return httpx.Response(
            200, text="<html>Pending</html>", headers={"content-type": "text/html"}
        )

    assert _collect(card, api, pending)["reason"] == "official_detail_unconfirmed"
    assert len(calls) == 1
    assert len(list((card.folder / "official").glob("*.html"))) == 1
    assert _seal(study, card)[1]["state"] == "failed"


def test_publication_capture_does_not_seal_an_unrun_slot(operation):
    study, _, prepare = operation
    card, _ = prepare()
    study.clock[0] = run.timestamp(card.slot["closes_at"])
    with pytest.raises(ValueError, match="result_slot_terminal_not_sealed"):
        run.terminal_publication(card)
    assert not card.claim.exists()
