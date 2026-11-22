"""Prove new acquisition limits using only synthetic source responses."""

import asyncio
import json
import subprocess
import sys
from datetime import timedelta
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import api27_forward, local_m0_inference
from autoresearch import kra_entry_scope_intake as intake
from autoresearch.kra_entry_scope_inputs import preflight
from autoresearch.kra_entry_scope_intake import (
    LIVE_RESERVATIONS,
    MAX_DENIAL_BYTES,
    _capture_scope,
    capture_intake,
    plan_intake,
)
from autoresearch.kra_entry_sheet_snapshot import collect_entry_sheet_snapshot
from autoresearch.observed_history_seed import pin
from autoresearch.tests.test_kra_schedule import DATE, NOW, SOURCE_URLS, capture, page

DUE = NOW + timedelta(days=2, hours=-6, minutes=-30)
TEST_KEY = "synthetic-local-key"


def response_rows(meet, field_count=1):
    return [
        {
            "meet": meet,
            "rcDate": int(DATE),
            "rcNo": no,
            "hrNo": f"{(meet * 1000 + no * 20 + gate):07d}",
            "chulNo": gate,
            "hrName": f"Fixture {meet}.{no}.{gate}",
            "stTime": "1200",
            "dusu": 10,
        }
        for no in range(1, field_count + 1)
        for gate in range(1, 11)
    ]


def answer(rows, page_no):
    start = (page_no - 1) * 100
    return httpx.Response(
        200,
        json={
            "response": {
                "header": {"resultCode": "00"},
                "body": {
                    "totalCount": len(rows),
                    "pageNo": page_no,
                    "numOfRows": 100,
                    "items": {"item": rows[start : start + 100]},
                },
            }
        },
    )


def mock_gateway(request):
    date = int(request.url.params["rc_date"])
    return answer(
        [
            row | {"rcDate": date}
            for row in response_rows(int(request.url.params["meet"]))
        ],
        int(request.url.params["pageNo"]),
    )


def common_error(status, code):
    return httpx.Response(
        status,
        json={
            "OpenAPI_ServiceResponse": {
                "cmmMsgHeader": {"returnReasonCode": code, "returnAuthMsg": TEST_KEY}
            }
        },
    )


def make_intake_inputs(root, **schedule_options):
    subprocess.run(["git", "init", "-q", "--template=", str(root)], check=True)
    schedule = capture(root / "schedule", **schedule_options)
    return root, pin(root, schedule)


@pytest.fixture
def inputs(tmp_path):
    return make_intake_inputs(tmp_path)


def run(
    inputs,
    *,
    provide=mock_gateway,
    reuse=(),
    limit=4,
    clock=lambda: NOW,
    output="scoped",
    race_dates=(DATE,),
    first_cutoff=DUE.isoformat(),
):
    root, schedule = inputs
    calls = []

    def mock(request):
        calls.append(
            (int(request.url.params["meet"]), int(request.url.params["pageNo"]))
        )
        return provide(request)

    # The fixture uses a path with no real key.
    secret = root / "synthetic-secret.txt"
    secret.write_text(TEST_KEY)
    result = asyncio.run(
        capture_intake(
            root,
            root / output,
            schedule,
            race_dates,
            first_cutoff=first_cutoff,
            reuse=reuse,
            max_requests=limit,
            api_key_file=secret,
            clock=clock,
            transport=httpx.MockTransport(mock),
        )
    )
    return result, calls


def test_failed_scope_cannot_repeat_in_a_different_output_folder(inputs):
    (path, receipt), calls = run(inputs, provide=lambda _: httpx.Response(429))
    assert calls == [(1, 1)]
    assert receipt["stop_reason"] == "rate_limited"
    original = path.read_bytes()
    with pytest.raises(ValueError, match="scope_intake_window_already_reserved"):
        run(
            inputs,
            output="different-output",
            provide=lambda _: pytest.fail("same date reached transport again"),
        )
    assert path.read_bytes() == original


def test_live_collection_limit_is_shared_by_linked_worktrees(inputs):
    root, _ = inputs
    tree = root / "linked"
    for args in (
        (
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "-c",
            "core.hooksPath=/dev/null",
            "commit",
            "--allow-empty",
            "-qm",
            "Fixture",
        ),
        ("worktree", "add", "--detach", "-q", str(tree), "HEAD"),
    ):
        subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)
    other = tree, pin(tree, capture(tree / "schedule"))
    (_, first), calls = run(inputs)
    assert len(calls) == 4
    assert first["status"] == "captured_locally"
    with pytest.raises(ValueError, match="scope_intake_window_already_reserved"):
        run(other, provide=lambda _: pytest.fail("other worktree reached transport"))


def test_busy_shared_claim_lock_stops_before_network_or_output_reservation(inputs):
    root, _ = inputs
    shared = root / ".git" / LIVE_RESERVATIONS
    shared.mkdir()
    with intake.exclusive(shared):
        with pytest.raises(BlockingIOError):
            run(
                inputs,
                output="concurrent-output",
                provide=lambda _: pytest.fail("busy reservation reached transport"),
            )
        assert not list(shared.glob("window_*.json"))
        assert not list((root / "concurrent-output").glob("window_*"))

    (_, receipt), calls = run(inputs)
    assert calls == [(meet, 1) for meet in range(1, 5)]
    assert receipt["status"] == "captured_locally"


def test_shared_claim_survives_local_reservation_failure(inputs, monkeypatch):
    root, schedule = inputs
    real_save = intake.save

    def interrupt(path, value):
        if path.name == "reservation.json":
            raise OSError("local write interrupted")
        return real_save(path, value)

    def never(_):
        pytest.fail("transport reached after a failed local reservation")

    monkeypatch.setattr(intake, "save", interrupt)
    with pytest.raises(OSError, match="local write interrupted"):
        run(inputs, provide=never)
    claim = root / ".git" / LIVE_RESERVATIONS / f"window_{DATE}.json"
    before = claim.read_bytes()
    assert json.loads(before) == {
        "race_dates": [DATE],
        "schedule_sha256": schedule["sha256"],
        "first_block_cutoff": DUE.isoformat(),
        "max_http_requests": 4,
        "reserved_at": NOW.isoformat(),
    }
    assert not (root / "scoped" / f"window_{DATE}" / "receipt.json").exists()
    with pytest.raises(ValueError, match="scope_intake_window_already_reserved"):
        run(inputs, output="different-output", provide=never)
    assert claim.read_bytes() == before


def test_shared_claim_checks_date_overlap_not_filename_or_schedule(inputs):
    root, _ = inputs
    run(inputs)
    later = "2026/10/17(\ud1a0)"
    revised = capture(
        root / "overlap-schedule",
        pages={source: page(source, dates={4: later}) for source in SOURCE_URLS},
    )
    with pytest.raises(ValueError, match="scope_intake_window_already_reserved"):
        run(
            (root, pin(root, revised)),
            race_dates=(DATE, "20261017"),
            output="different-output",
            provide=lambda _: pytest.fail("overlapping dates reached transport"),
        )
    independent = capture(
        root / "independent-schedule",
        pages={
            source: page(source, dates=dict.fromkeys(range(1, 5), later))
            for source in SOURCE_URLS
        },
    )
    (_, receipt), calls = run(
        (root, pin(root, independent)),
        race_dates=("20261017",),
        first_cutoff=(DUE + timedelta(days=1)).isoformat(),
    )
    assert len(calls) == 4
    assert receipt["status"] == "captured_locally"


def test_live_capture_requires_verified_checkout(tmp_path):
    schedule = pin(tmp_path, capture(tmp_path / "schedule"))
    assert (
        plan_intake(tmp_path, schedule, [DATE], observed=NOW)["max_http_requests"] == 4
    )
    with pytest.raises(ValueError, match="scope_intake_requires_git_worktree_root"):
        run(
            (tmp_path, schedule),
            provide=lambda _: pytest.fail("unreserved checkout reached transport"),
        )
    assert not list((tmp_path / "scoped").glob("window_*"))


def model_rows(meet, fields=1):
    return [
        row
        | {
            "age": 4,
            "wgBudam": 52.5,
            "rating": None if row["chulNo"] == 1 else 40,
            "rcCntT": 10,
            "ord1CntT": 2,
            "ord2CntT": 2,
            "ord3CntT": 2,
        }
        for row in response_rows(meet, fields)
    ]


def model_gateway(request):
    return answer(
        model_rows(int(request.url.params["meet"])),
        int(request.url.params["pageNo"]),
    )


def readback(inputs, ref, *, first_cutoff=DUE.isoformat(), clock=lambda: NOW):
    root, schedule = inputs
    return preflight(
        root,
        ref,
        schedule_sha256=schedule["sha256"],
        first_cutoff=first_cutoff,
        clock=clock,
    )


def test_preflight_returns_the_whole_card_for_both_fixed_arms(tmp_path, monkeypatch):
    sources = ("national", "region_1", "region_2", "region_3")
    tested = make_intake_inputs(
        tmp_path, pages={s: page(s, fields={1: 11}) for s in sources}
    )
    ticks = iter(NOW + timedelta(milliseconds=n) for n in range(1000))

    def gateway(request):
        meet = int(request.url.params["meet"])
        return answer(
            model_rows(meet, 11 if meet == 1 else 1), int(request.url.params["pageNo"])
        )

    (path, receipt), calls = run(
        tested, provide=gateway, clock=lambda: next(ticks), limit=5
    )
    original = {p: p.read_bytes() for p in tmp_path.rglob("*.json")}

    def disabled(*args, **kwargs):
        pytest.fail("input review cannot collect or score")

    monkeypatch.setattr(httpx, "AsyncClient", disabled)
    monkeypatch.setattr(local_m0_inference, "score_capture", disabled)
    observed = NOW + timedelta(minutes=1)
    outcome = readback(tested, pin(tmp_path, path), clock=lambda: observed)
    assert calls == [(1, 1), (1, 2), (2, 1), (3, 1), (4, 1)]
    assert outcome["race_count"] == 14
    assert outcome["declaration_count"] == 140
    assert outcome["feature_missing_counts"] == dict.fromkeys(
        local_m0_inference.API_FIELDS, 0
    ) | {"rating": 14}
    assert outcome["local_readback_at"] == observed.isoformat()
    assert outcome["first_block_cutoff"] == DUE.isoformat()
    assert outcome["schedule"] == tested[1]
    assert outcome["http_requests_made"] == 0
    assert not outcome["study_registered"]
    assert not outcome["independent_publication_verified"]
    assert not outcome["predictions_computed"]
    assert {p: p.read_bytes() for p in tmp_path.rglob("*.json")} == original
    scoped = {r["meet"]: r["capture"] for r in receipt["scopes"]}
    day = tmp_path / DATE
    day.mkdir()
    for item in outcome["bindings"]:
        race = item["race"]
        source = item["entry_manifest"]
        assert source == scoped[race["meet"]]
        ref = {
            "study_sha256": "test-only",
            "manifest_path": source["path"],
            "manifest_sha256": source["sha256"],
        }
        (day / f"input_{race['race_id']}.json").write_text(json.dumps(ref))
        assert api27_forward.shared_source(tmp_path, race, "test-only") == (
            ref,
            item["shared_input"],
        )
    beyond_first_page = next(
        b for b in outcome["bindings"] if b["race"]["race_id"] == f"{DATE}_1_11"
    )
    assert len(beyond_first_page["shared_input"]["feature_rows"]) == 10
    assert len(beyond_first_page["shared_input"]["source"]["pages"]) == 2


def test_preflight_reuses_only_the_reserved_sources(inputs):
    root, _ = inputs
    (_, first), _ = run(inputs, provide=model_gateway)
    claims = (root / ".git" / LIVE_RESERVATIONS).glob("*.json")
    original_claims = {p: p.read_bytes() for p in claims}
    refs = [row["capture"] for row in first["scopes"]]
    (path, receipt), calls = run(
        inputs,
        provide=lambda _: pytest.fail("reuse made another request"),
        reuse=refs,
        limit=0,
        output="reuse",
    )
    prepared = readback(inputs, pin(root, path))
    assert calls == []
    assert receipt["actual_http_requests"] == 0
    assert [b["entry_manifest"] for b in prepared["bindings"]] == refs
    assert {
        p: p.read_bytes() for p in (root / ".git" / LIVE_RESERVATIONS).glob("*.json")
    } == original_claims


@pytest.mark.parametrize("issue", ["missing_key", "impossible_counts"])
def test_preflight_blocks_model_input_that_passed_roster_checks(inputs, issue):
    root, _ = inputs

    def gateway(request):
        meet = int(request.url.params["meet"])
        rows = model_rows(meet)
        if meet == 4:
            if issue == "missing_key":
                del rows[-1]["rating"]
            else:
                rows[-1]["rcCntT"] = 5
        return answer(rows, int(request.url.params["pageNo"]))

    (path, receipt), calls = run(inputs, provide=gateway)
    assert receipt["status"] == "captured_locally"
    assert len(calls) == 4
    reason = (
        "local_m0_missing_feature_key"
        if issue == "missing_key"
        else "career_places_exceed_starts"
    )
    with pytest.raises(
        ValueError, match=f"scope_inputs_invalid_features:{DATE}_4_1:{reason}"
    ):
        readback(inputs, pin(root, path))


@pytest.mark.parametrize(
    "change, error",
    [
        ("drop_scope", "reservation_does_not_replay"),
        ("replace_scope", "unexpected_scope"),
        ("changed_requests", "request_count_conflict"),
        ("late_request", "request_evidence_conflict"),
        ("late_receipt", "outside_deadline"),
    ],
)
def test_preflight_rejects_changed_scope_or_clock_even_if_repinned(
    inputs, change, error
):
    root, _ = inputs
    (path, receipt), _ = run(inputs, provide=model_gateway)
    original = pin(root, path)
    if change == "drop_scope":
        receipt["scopes"].pop()
    elif change == "replace_scope":
        receipt["scopes"][-1] = receipt["scopes"][0]
    elif change == "changed_requests":
        receipt["actual_http_requests"] += 1
    elif change == "late_request":
        receipt["scopes"][-1]["requests"][0]["completed_at"] = DUE.isoformat()
    else:
        receipt["completed_at"] = DUE.isoformat()
    path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="source_pin_mismatch"):
        readback(inputs, original)
    with pytest.raises(ValueError, match=error):
        readback(inputs, pin(root, path))


def test_preflight_keeps_the_original_cutoff_even_if_receipt_uses_a_later_one(inputs):
    root, _ = inputs
    (path, _), _ = run(inputs, provide=model_gateway)
    ref = pin(root, path)
    original = (DUE - timedelta(minutes=15)).isoformat()
    with pytest.raises(ValueError, match="original_cutoff_conflict"):
        readback(inputs, ref, first_cutoff=original)
    assert readback(inputs, ref)["first_block_cutoff"] == DUE.isoformat()


def test_preflight_requires_the_fixed_schedule_even_at_the_same_cutoff(inputs):
    root, _ = inputs
    sources = ("national", "region_1", "region_2", "region_3")
    revised = capture(
        root / "revised",
        pages={s: page(s, notes="Reissued card") for s in sources},
    )
    alternate = root, pin(root, revised)
    (path, _), _ = run(alternate, provide=model_gateway)
    ref = pin(root, path)
    with pytest.raises(ValueError, match="original_schedule_conflict"):
        readback(inputs, ref)
    matching = readback(alternate, ref)
    assert matching["first_block_cutoff"] == DUE.isoformat()
    assert matching["schedule"] == alternate[1]


def test_preflight_requires_an_unchanged_raw_page(inputs):
    root, _ = inputs
    (path, receipt), _ = run(inputs, provide=model_gateway)
    ref = pin(root, path)
    source = root / receipt["scopes"][-1]["capture"]["path"]
    page_path = Path(json.loads(source.read_bytes())["pages"][0]["raw_path"])
    page_path.write_bytes(page_path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="raw_.*mismatch"):
        readback(inputs, ref)
    assert pin(root, path) == ref


def test_preflight_cannot_admit_an_incomplete_receipt(inputs):
    root, _ = inputs
    (path, receipt), calls = run(inputs, provide=lambda _: httpx.Response(429))
    assert calls == [(1, 1)]
    assert receipt["stop_reason"] == "rate_limited"
    with pytest.raises(ValueError, match="requires_complete_local_receipt"):
        readback(inputs, pin(root, path))


def test_preflight_rejects_late_and_backwards_readback(inputs):
    root, _ = inputs
    (path, _), _ = run(inputs, provide=model_gateway)
    ref = pin(root, path)
    for timeline in ([DUE], [NOW, DUE], [NOW, NOW - timedelta(seconds=1)]):
        clock = iter(timeline)
        with pytest.raises(ValueError, match="outside_deadline"):
            readback(inputs, ref, clock=clock.__next__)


def test_whole_card_retained_and_same_window_cannot_fetch_again(inputs):
    (out, report), calls = run(inputs)
    assert calls == [(1, 1), (2, 1), (3, 1), (4, 1)]
    assert report["actual_http_requests"] == 4
    assert report["status"] == "captured_locally"
    assert not report["study_registered"]
    assert not report["independent_publication_verified"]
    assert all(r["state"] == "captured" for r in report["scopes"])
    assert json.loads(out.read_bytes()) == report
    assert TEST_KEY.encode() not in out.read_bytes()
    assert "serviceKey" not in out.read_text()
    original = out.read_bytes()
    with pytest.raises(ValueError, match="already_reserved"):
        run(inputs, provide=lambda _: pytest.fail("duplicate request"))
    assert original == out.read_bytes()


@pytest.mark.parametrize(
    ("provider", "failure", "http_code", "gateway_code"),
    [
        (lambda _: httpx.Response(401), "authentication_error", 401, None),
        (lambda _: httpx.Response(403), "access_denied", 403, None),
        (lambda _: httpx.Response(429), "rate_limited", 429, None),
        (lambda _: common_error(403, "30"), "authentication_error", 403, "30"),
        (lambda _: common_error(403, "22"), "rate_limited", 403, "22"),
        (lambda _: common_error(403, "03"), "access_denied", 403, "03"),
        (
            lambda _: httpx.Response(
                403, content=b"<error><returnReasonCode>30</returnReasonCode></error>"
            ),
            "authentication_error",
            403,
            "30",
        ),
        (
            lambda _: httpx.Response(
                403, json={"response": {"header": {"resultCode": TEST_KEY}}}
            ),
            "access_denied",
            403,
            None,
        ),
        (lambda _: common_error(200, "22"), "rate_limited", 200, "22"),
        (
            lambda _: httpx.Response(403, content=b" " * (MAX_DENIAL_BYTES + 1)),
            "access_denied",
            403,
            None,
        ),
        (
            lambda _: httpx.Response(
                200, content=b"<error><returnReasonCode>30</returnReasonCode></error>"
            ),
            "authentication_error",
            200,
            "30",
        ),
        (
            lambda _: httpx.Response(
                200, json={"response": {"header": {"resultCode": "22"}}}
            ),
            "rate_limited",
            200,
            "22",
        ),
        (
            lambda _: httpx.Response(
                200, json={"response": {"header": {"resultCode": "03"}}}
            ),
            "no_data_unconfirmed",
            200,
            "03",
        ),
        (lambda _: answer([], 1), "empty_unconfirmed", 200, "00"),
        (lambda _: httpx.Response(200, content=b" \n"), "empty_unconfirmed", 200, None),
        (
            lambda _: httpx.Response(200, content=b"<html>maintenance</html>"),
            "provider_error_or_invalid_body",
            200,
            None,
        ),
        (
            lambda _: httpx.Response(
                302, headers={"location": "https://example.invalid/away"}
            ),
            "http_error",
            302,
            None,
        ),
    ],
)
def test_failure_keeps_all_unattempted_scopes(
    inputs, provider, failure, http_code, gateway_code
):
    (out, report), calls = run(inputs, provide=provider)
    assert calls == [(1, 1)]
    assert report["status"] == "incomplete"
    scopes = report["scopes"]
    assert sum(len(s["races"]) for s in scopes) == 4
    assert scopes[0]["state"] == failure
    assert scopes[0]["requests"][0]["http_status"] == http_code
    assert scopes[0]["requests"][0].get("gateway_result_code") == gateway_code
    assert [s["state"] for s in scopes[1:]] == ["not_attempted"] * 3
    assert [s["stop_reason"] for s in scopes[1:]] == [failure] * 3
    assert TEST_KEY.encode() not in out.read_bytes()


def test_mixed_gateway_and_success_page_is_never_accepted(inputs):
    def mixed(_):
        body = json.loads(answer(response_rows(1), 1).content)
        body.update(json.loads(common_error(200, "22").content))
        return httpx.Response(200, json=body)

    (_, report), calls = run(inputs, provide=mixed)
    assert calls == [(1, 1)]
    assert report["status"] == "incomplete"
    assert report["scopes"][0]["state"] == "provider_error_or_invalid_body"
    assert report["scopes"][1]["state"] == "not_attempted"


def test_transport_error_does_not_retry_or_record_secret_message(inputs):
    def fail(request):
        raise httpx.ReadTimeout(f"do not retain {request.url}", request=request)

    (out, report), calls = run(inputs, provide=fail)
    assert calls == [(1, 1)]
    assert report["scopes"][0]["state"] == "transport_timeout"
    assert TEST_KEY.encode() not in out.read_bytes()
    assert "serviceKey" not in out.read_text()


def test_scope_finishing_at_first_cutoff_preserves_bytes_but_cannot_continue(inputs):
    current = NOW

    def late(request):
        nonlocal current
        current = DUE
        return mock_gateway(request)

    (_, report), calls = run(inputs, provide=late, clock=lambda: current)
    assert calls == [(1, 1)]
    assert report["status"] == "incomplete"
    assert report["stop_reason"] == "first_block_cutoff_passed"
    assert report["scopes"][0]["capture"]["sha256"]
    assert all(s["state"] == "not_attempted" for s in report["scopes"][1:])


def test_reuse_complete_original_scope_without_replacement(inputs):
    root, _ = inputs

    async def earlier():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(mock_gateway)
        ) as client:
            return await collect_entry_sheet_snapshot(
                meet=1,
                race_date=DATE,
                race_no=1,
                output_dir=root / "earlier",
                client=client,
                clock=lambda: NOW,
                **{"api_key": TEST_KEY},
            )

    source = asyncio.run(earlier())
    path = Path(source["manifest_path"])
    original = path.read_bytes()
    (_, report), calls = run(inputs, reuse=[pin(root, path)], limit=3)
    assert report["scopes"][0]["state"] == "reused"
    assert calls == [(2, 1), (3, 1), (4, 1)]
    assert report["status"] == "captured_locally"
    assert path.read_bytes() == original
    with pytest.raises(ValueError, match="source_pin_mismatch"):
        run(inputs, reuse=[pin(root, path) | {"sha256": "0" * 64}])


def test_late_low_budget_and_partial_schedule_do_not_make_requests(inputs, tmp_path):
    def never(_):
        pytest.fail("unexpected request")

    with pytest.raises(ValueError, match="budget_not_authorized"):
        run(inputs, provide=never, limit=3)
    with pytest.raises(ValueError, match="cutoff_passed"):
        run(inputs, provide=never, clock=lambda: DUE)
    path = capture(
        tmp_path / "two-days",
        pages={
            source: page(source, dates={4: "2026/10/17(\ud1a0)"})
            for source in ("national", "region_1", "region_2", "region_3")
        },
    )
    with pytest.raises(ValueError, match="whole_official_schedule"):
        plan_intake(tmp_path, pin(tmp_path, path), [DATE], observed=NOW)
    plan = plan_intake(tmp_path, pin(tmp_path, path), [DATE, "20261017"], observed=NOW)
    assert plan["race_dates"] == [DATE, "20261017"]
    assert plan["race_count"] == 4


@pytest.mark.parametrize("start, shift", [("12:15", 15), ("11:45", -15)])
def test_a_changed_first_post_cannot_move_the_cutoff(tmp_path, start, shift):
    sources = ("national", "region_1", "region_2", "region_3")
    revised = capture(
        tmp_path / "revised",
        pages={s: page(s, times=dict.fromkeys(range(1, 5), start)) for s in sources},
    )
    ref = pin(tmp_path, revised)
    preview = plan_intake(tmp_path, ref, [DATE], observed=NOW)
    assert preview["first_block_cutoff"] == (DUE + timedelta(minutes=shift)).isoformat()

    def never(_):
        pytest.fail("new schedule must not authorize a new request")

    with pytest.raises(ValueError, match="original_cutoff_conflict"):
        run((tmp_path, ref), provide=never)
    with pytest.raises(ValueError, match="cutoff_passed"):
        run((tmp_path, ref), provide=never, clock=lambda: DUE)
    assert not (tmp_path / "scoped").exists()


@pytest.mark.parametrize(
    ("fields", "observed", "state"),
    [
        (11, [1, 2], "captured"),
        (12, [1], "schedule_runner_count_conflict"),
        (1, [1], "schedule_runner_count_conflict"),
    ],
)
def test_next_page_is_only_used_for_the_reserved_exact_total(
    tmp_path, fields, observed, state
):
    calls = []
    scope = {
        "meet": 1,
        "race_date": DATE,
        "anchor_race_no": 1,
        "runner_count": 110,
        "request_page_limit": 2,
        "races": [
            {
                "race_no": n,
                "runners": 10,
                "scheduled_start_at": "2026-10-16T12:00:00+09:00",
            }
            for n in range(1, 12)
        ],
    }

    def mock(request):
        no = int(request.url.params["pageNo"])
        calls.append(no)
        return answer(response_rows(1, fields), no)

    async def collect():
        async with httpx.AsyncClient(transport=httpx.MockTransport(mock)) as client:
            return await _capture_scope(
                client, scope, tmp_path, tmp_path / "raw", DUE, lambda: NOW, TEST_KEY
            )

    out = asyncio.run(collect())
    assert calls == observed
    assert out["state"] == state
    assert len(out["requests"]) == len(calls)
    original = json.loads((tmp_path / out["capture"]["path"]).read_bytes())
    assert len(original["pages"]) == len(calls)
    assert all("serviceKey" not in p["request_parameters"] for p in original["pages"])


def test_equal_total_cannot_hide_extra_race(tmp_path):
    scope = {
        "meet": 1,
        "race_date": DATE,
        "anchor_race_no": 1,
        "runner_count": 20,
        "request_page_limit": 1,
        "races": [
            {
                "race_no": no,
                "runners": 10,
                "scheduled_start_at": "2026-10-16T12:00:00+09:00",
            }
            for no in (1, 2)
        ],
    }
    rows = response_rows(1, 2)
    rows[-1]["rcNo"] = 3

    async def collect():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _: answer(rows, 1))
        ) as client:
            return await _capture_scope(
                client, scope, tmp_path, tmp_path / "raw", DUE, lambda: NOW, TEST_KEY
            )

    assert asyncio.run(collect())["state"] == "scope_evidence_unverified"
