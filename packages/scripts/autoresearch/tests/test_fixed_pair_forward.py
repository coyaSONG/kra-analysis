"""Exercise the whole fixed-pair path without authority, data or picks for a real race."""

import asyncio
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import (
    fixed_pair_forward as forward,
)
from autoresearch import (
    fixed_pair_forward_contract as contract,
)
from autoresearch import (
    kra_entry_scope_witness as inputs,
)
from autoresearch import (
    prerace_hash_witness as github,
)
from autoresearch.kra_entry_scope_intake import capture_intake
from autoresearch.observed_history_seed import pin
from autoresearch.restricted_cohort import API_COLUMNS, encoded, parse_json, sha256
from autoresearch.tests.condition_forward_fixture import (
    archive_publication,
    public_payload,
)
from autoresearch.tests.test_kra_entry_scope_intake import answer, model_rows
from autoresearch.tests.test_kra_schedule import SOURCE_URLS, capture, page

STUDY = "fictional-complete-card"
PULLS = (906, 907, 908, 909)  # input, protocol, approval, prediction
NOW = datetime(2099, 1, 1, 6, tzinfo=UTC)
DUE = datetime(2099, 1, 2, 2, 30, tzinfo=UTC)
DATES = {
    1: date(2099, 1, 2),
    2: date(2099, 1, 2),
    3: date(2099, 1, 3),
    4: date(2099, 1, 3),
}
FIELDS = {1: 11, 2: 1, 3: 1, 4: 1}
REVIEWER = "fictional-independent-reviewer"


def at(second):
    return NOW + timedelta(seconds=second)


def mock_source(root):
    names = "\uc6d4\ud654\uc218\ubaa9\uae08\ud1a0\uc77c"
    dates = {
        meet: f"{day:%Y/%m/%d}({names[day.weekday()]})" for meet, day in DATES.items()
    }
    days = sorted({day.strftime("%Y%m%d") for day in DATES.values()})
    pages = {key: page(key, dates=dates, fields=FIELDS) for key in SOURCE_URLS}
    schedule = pin(root, capture(root / "schedule", pages=pages, clock=lambda: NOW))
    secret = root / "fixture-key"
    secret.write_text("synthetic-only")

    def entries(req):
        meet = int(req.url.params["meet"])
        rows = [
            row | {"rcDate": int(req.url.params["rc_date"])}
            for row in model_rows(meet, FIELDS[meet])
        ]
        return answer(rows, int(req.url.params["pageNo"]))

    receipt, result = asyncio.run(
        capture_intake(
            root,
            root / "card",
            schedule,
            days,
            first_cutoff=DUE.isoformat(),
            reuse=(),
            max_requests=5,
            api_key_file=secret,
            clock=lambda: NOW,
            transport=httpx.MockTransport(entries),
        )
    )
    assert result["actual_http_requests"] == 5
    reference = pin(root, receipt)
    marker = inputs.stage(
        root,
        reference,
        schedule_sha256=schedule["sha256"],
        first_cutoff=DUE.isoformat(),
        clock=lambda: at(1),
    )
    digest = parse_json(marker)["packet_sha256"]
    archive_publication(
        receipt.with_name(inputs.ARCHIVE_NAME),
        marker,
        PULLS[0],
        inputs.publication_document(digest),
        at(5),
        at(6),
    )
    return reference, schedule, digest


def dummy_model(arm):
    coefficients = [0.0] * len(API_COLUMNS)
    coefficients[API_COLUMNS.index("rating_missing")] = 1.0 if arm == "M0" else -1.0
    return {
        "format_version": "kra-restricted-logistic-v1",
        "arm": "M0",
        "columns": list(API_COLUMNS),
        "imputer_statistics": [0.0] * len(API_COLUMNS),
        "scaler_mean": [0.0] * len(API_COLUMNS),
        "scaler_scale": [1.0] * len(API_COLUMNS),
        "coefficients": coefficients,
        "intercept": 0.0,
    }


@pytest.fixture
def card(tmp_path, monkeypatch):
    clock = [at(30)]

    def git(*args):
        return subprocess.run(
            ["git", *args], cwd=tmp_path, check=True, capture_output=True, timeout=15
        ).stdout

    class ProviderClock(datetime):
        @classmethod
        def now(cls, tz=None):
            value = clock[0]
            return (
                value.astimezone(tz) if tz is not None else value.replace(tzinfo=None)
            )

    for module in (contract, forward, inputs):
        monkeypatch.setattr(module, "now", lambda: clock[0])
    monkeypatch.setattr(forward.publication, "datetime", ProviderClock)
    monkeypatch.setattr(github, "datetime", ProviderClock)
    monkeypatch.setattr(contract, "runtime_sha", lambda: "b" * 64)
    git("init", "-q", "--template=")
    receipt, schedule, digest = mock_source(tmp_path)
    verified, binding = contract.source(
        tmp_path,
        receipt,
        schedule_sha256=schedule["sha256"],
        first_cutoff=DUE.isoformat(),
        packet_sha256=digest,
        input_pr=PULLS[0],
    )
    protocol = contract.protocol_for(
        STUDY,
        REVIEWER,
        PULLS[3],
        dict.fromkeys(contract.ANALYSIS_FIELDS, "fictional test specification"),
        verified,
        binding,
        at(10),
    )
    protocol_raw = encoded(protocol)
    approval = contract.approval_for(STUDY, protocol_raw, PULLS[1], REVIEWER, at(16))
    approval_raw = encoded(approval)
    routes = {}

    def register(role, number, body, clock_at, login):
        document = contract.path_for(STUDY, role)
        pull, content = public_payload(body, number, document, clock_at)
        pull["user"] = {"login": login}
        prefix = github.API_ROOT
        routes[f"{prefix}/pulls/{number}"] = pull
        routes[f"{prefix}/contents/{document}?ref={pull['merge_commit_sha']}"] = content
        return pull

    for n, role, body, merged, login in (
        (PULLS[1], "protocol", protocol_raw, at(14), contract.OWNER),
        (PULLS[2], "approval", approval_raw, at(20), REVIEWER),
    ):
        path = tmp_path / contract.path_for(STUDY, role)
        path.parent.mkdir(parents=True)
        path.write_bytes(body)
        register(role, n, body, merged, login)
    open_document = {
        "number": PULLS[3],
        "user": {"login": contract.OWNER},
        "state": "open",
        "merged": False,
        "created_at": at(3).isoformat(),
        "base": {"ref": "main", "repo": {"full_name": github.REPOSITORY}},
        "html_url": f"https://github.com/{github.REPOSITORY}/pull/{PULLS[3]}",
    }
    routes[f"{github.API_ROOT}/pulls/{PULLS[3]}"] = open_document

    git("add", "--", "docs")
    git(
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "-qm",
        "Fictional protocol and approval",
    )
    git(
        "update-ref",
        "refs/remotes/origin/main",
        git("rev-parse", "HEAD").decode().strip(),
    )
    ledger = forward.ledger_for(tmp_path, STUDY)

    calls = []

    def respond(req):
        assert "authorization" not in req.headers
        calls.append(str(req.url))
        return httpx.Response(200, json=routes[str(req.url)])

    client = httpx.Client
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kw: client(transport=httpx.MockTransport(respond), **kw),
    )
    for arm, module in (("M0", contract.m0), ("API27", contract.api27)):
        monkeypatch.setattr(
            module,
            "load_model",
            lambda _, label=arm: (
                dummy_model(label),
                {"completed_at": at(-100).isoformat()},
            ),
        )
    return SimpleNamespace(
        root=tmp_path,
        receipt=receipt,
        protocol=protocol,
        ledger=ledger,
        model_dirs=dict.fromkeys(contract.MODELS, tmp_path / "fixture"),
        clock=clock,
        calls=calls,
        register=register,
        routes=routes,
        open_document=open_document,
    )


def run(card):
    return forward.run(card.root, STUDY, card.receipt, PULLS[1:3], card.model_dirs)


def local(card):
    return forward.verify_local(card.root, STUDY, card.receipt, card.model_dirs)


def proof(card, *, collect=True):
    return forward.witness(
        card.root, STUDY, card.receipt, card.model_dirs, collect=collect
    )


def test_complete_two_day_same_input_pair_has_one_live_attempt_and_timely_publication(
    card,
):
    result = run(card)
    assert result["race_count"] == 14
    assert result["actual_fit_count"] == 0
    assert len(card.calls) == 5
    _, _, raw, report = local(card)
    assert report == result and sha256(raw) == result["pair_sha256"]
    value = parse_json(raw)
    assert [row["race_id"] for row in value["races"]] == card.protocol["race_ids"]
    for row in value["races"]:
        assert set(row["predictions"]) == {"M0", "API27"}
        assert (
            row["predictions"]["M0"]["horse_ids"]
            != row["predictions"]["API27"]["horse_ids"]
        )
        assert all(len(item["horse_ids"]) == 3 for item in row["predictions"].values())
    scope = parse_json(card.ledger.with_suffix(".reservation.json").read_bytes())
    assert scope["race_dates"] == ["20990102", "20990103"]
    assert scope["race_ids"] == card.protocol["race_ids"]
    assert forward.stage(card.root, STUDY, card.receipt, card.model_dirs) == raw
    with pytest.raises((ValueError, FileExistsError)):
        run(card)
    with pytest.raises(ValueError, match="overlapping_consumed_dates"):
        forward.reserve(card.ledger.with_name("alias"), scope)
    assert len(card.calls) == 5
    card.register("prediction", PULLS[3], raw, at(44), contract.OWNER)
    card.clock[0] = DUE + timedelta(seconds=1)
    observed = proof(card)
    assert observed["status"] == "published_before_cutoff"
    assert not observed["outcomes_verified"] and not observed["model_promoted"]
    assert observed == proof(card, collect=False)
    assert len(card.calls) == 7
    with pytest.raises(ValueError, match="original_deadline"):
        forward.stage(card.root, STUDY, card.receipt, card.model_dirs)


def refuse_score(monkeypatch):
    monkeypatch.setattr(
        forward.contract.m0,
        "score_capture",
        lambda *a: pytest.fail("scoring forbidden"),
    )


def test_owner_cannot_supply_the_separate_review(card, monkeypatch):
    refuse_score(monkeypatch)
    card.routes[f"{github.API_ROOT}/pulls/{PULLS[2]}"]["user"]["login"] = contract.OWNER
    with pytest.raises(ValueError, match="public_review_author_conflict"):
        run(card)
    assert len(card.calls) == 4
    failure = parse_json((card.ledger / "failure.json").read_bytes())
    assert (
        failure["race_ids"] == card.protocol["race_ids"]
        and not failure["retry_allowed"]
    )
    with pytest.raises(ValueError, match="not_publishable"):
        local(card)


@pytest.mark.parametrize("bad", ("state", "created_at"))
def test_prediction_slot_must_be_open_and_preexisting(card, monkeypatch, bad):
    refuse_score(monkeypatch)
    card.open_document[bad] = "closed" if bad == "state" else at(11).isoformat()
    with pytest.raises(ValueError, match="not_open_before_registration"):
        run(card)
    assert len(card.calls) == 5
    assert not (card.ledger / "paired.json").exists()


def test_cutoff_and_runtime_drift_stop_before_request_or_reservation(card, monkeypatch):
    refuse_score(monkeypatch)
    card.clock[0] = DUE
    with pytest.raises(ValueError, match="original_deadline"):
        run(card)
    card.clock[0] = at(30)
    monkeypatch.setattr(contract, "runtime_sha", lambda: "c" * 64)
    with pytest.raises(ValueError, match="protocol_or_runtime_changed"):
        run(card)
    assert not card.calls and not card.ledger.exists()


def test_other_published_protocol_cannot_register_the_same_dates(card, monkeypatch):
    refuse_score(monkeypatch)
    other_study = "different-name-same-card"
    other_path = contract.path_for(other_study, "protocol")
    original = contract.git
    other = card.protocol | {"study_id": other_study}

    def git(root, *args):
        if args[0] == "ls-tree":
            return other_path.encode() + b"\0"
        if args[:2] == ("show", f"refs/remotes/origin/main:{other_path}"):
            return encoded(other)
        return original(root, *args)

    monkeypatch.setattr(contract, "git", git)
    with pytest.raises(ValueError, match="scope_already_registered"):
        run(card)
    assert not card.calls and not card.ledger.exists()


def test_late_publication_keeps_complete_pair_as_late(card):
    run(card)
    _, _, raw, _ = local(card)
    card.register("prediction", PULLS[3], raw, DUE, contract.OWNER)
    card.clock[0] = DUE + timedelta(seconds=1)
    observed = proof(card)
    assert not observed["before_cutoff"]
    assert observed["status"] == "published_at_or_after_cutoff"
    assert observed["race_count"] == 14


def test_no_submitted_payload_can_be_substituted_in_public_slot(card):
    run(card)
    _, _, raw, _ = local(card)
    card.register("prediction", PULLS[3], raw + b" ", at(44), contract.OWNER)
    card.clock[0] = at(48)
    with pytest.raises(ValueError, match="forward_publication_evidence_conflict"):
        proof(card)
    assert (card.ledger / "prediction-publication" / "pull.json").is_file()


def test_consumed_interrupted_attempt_does_not_start_again(card, monkeypatch):
    def interrupted(*args):
        raise InterruptedError("fictional process interruption")

    monkeypatch.setattr(forward, "pair_rows", interrupted)
    with pytest.raises(InterruptedError):
        run(card)
    assert len(card.calls) == 5 and (card.ledger / "failure.json").exists()
    with pytest.raises((ValueError, FileExistsError)):
        run(card)
    assert len(card.calls) == 5


def test_one_known_model_error_retains_other_arm_and_every_race(card, monkeypatch):
    score = contract.m0.score_capture

    def nonfinite_one(model, projected):
        if (
            projected["race_id"] == card.protocol["race_ids"][0]
            and model["coefficients"][API_COLUMNS.index("rating_missing")] == 1.0
        ):
            raise ValueError("nonfinite_restricted_scores")
        return score(model, projected)

    # Inject through the exact model identity, not through a missing roster.
    monkeypatch.setattr(contract.m0, "score_capture", nonfinite_one)
    run(card)
    _, _, raw, _ = local(card)
    value = parse_json(raw)
    assert len(value["races"]) == 14
    first = value["races"][0]["predictions"]
    assert first["M0"]["status"] == "not_submitted" and first["M0"]["horse_ids"] is None
    assert first["API27"]["status"] == "submitted"
