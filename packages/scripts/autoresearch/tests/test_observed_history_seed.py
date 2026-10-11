"""Bounded actual collector composition, append-only resume and replay tests."""

import asyncio
import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from autoresearch import observed_history_seed as m
from autoresearch.tests.race_card_pdf_capture_fixture import entry
from autoresearch.tests.test_kra_result_snapshot import envelope, row

SECRET = "test-source+token/only="


def initialized(tmp_path, budget=2000):
    root = tmp_path / "source"
    root.mkdir()
    m.save(root / "plan.json", m.make_plan("20261011", "20261011", budget))
    return root


async def execute(root, handler, **kwargs):
    with m.exclusive(root):
        return await m.collect(
            root,
            SECRET,
            transport=httpx.MockTransport(handler),
            delay=0,
            **kwargs,
        )


def response(request, *, missing_venue=False, empty=False):
    assert request.url.params["serviceKey"] == SECRET
    meet = int(request.url.params["meet"])
    rows = [
        {
            **entry(i, count=3),
            **row(i, rank=i),
            "meet": meet,
            "rcDate": int(request.url.params["rc_date"]),
        }
        for i in (1, 2, 3)
    ]
    if missing_venue and str(request.url.copy_with(query=None)) == m.RESULT_URL:
        for item in rows:
            del item["meet"]
    return httpx.Response(200, json=envelope([] if empty else rows))


def test_plan_has_every_calendar_day_and_physical_venue():
    plan = m.make_plan("20260712", "20261011")
    assert len(plan["units"]) == 368
    assert plan["units"][0] == {"day": "20260712", "meet": 1}
    assert plan["units"][-1] == {"day": "20261011", "meet": 4}
    for budget in (True, 0, 2001):
        with pytest.raises(ValueError):
            m.make_plan("20261011", "20261011", budget)
    with pytest.raises(ValueError):
        m.days("20261011", "20261010")


def test_complete_resume_and_secret_free_journal(tmp_path):
    root = initialized(tmp_path)
    assert asyncio.run(execute(root, response))["request_reservations"] == 4
    first = m.replay(root)
    assert len(first["records"]) == 12
    assert first["status_counts"] == {"api_reported_rows": 4}
    assert not first["complete_actual_start_history_verified"]
    before = {str(p): p.read_bytes() for p in root.rglob("*.json")}

    def unexpected(request):
        pytest.fail("successful units must replay without new requests")

    assert asyncio.run(execute(root, unexpected))["new_units"] == 0
    assert before == {str(p): p.read_bytes() for p in root.rglob("*.json")}
    assert all(SECRET.encode() not in raw for raw in before.values())
    assert all(b"serviceKey" not in raw for raw in before.values())


def test_missing_venue_requires_full_api26_binding(tmp_path):
    root = initialized(tmp_path)
    asyncio.run(execute(root, lambda r: response(r, missing_venue=True)))
    seed = m.replay(root)
    assert seed["request_reservations"] == 8
    assert seed["status_counts"] == {"api_reported_rows": 4}
    assert all(r["entry"] for r in seed["inventory"])
    assert all(
        r["venue_identity_basis"] == "api26_full_day_roster" for r in seed["records"]
    )


def test_mismatched_binding_is_preserved_without_inventing_venue(tmp_path):
    root = initialized(tmp_path)

    def mismatch(request):
        result = response(request, missing_venue=True)
        if str(request.url.copy_with(query=None)) == m.ENTRY_URL:
            payload = result.json()
            rows = payload["response"]["body"]["items"]["item"][:2]
            for item in rows:
                item["dusu"] = 2
            return httpx.Response(200, json=envelope(rows))
        return result

    asyncio.run(execute(root, mismatch))
    seed = m.replay(root)
    assert seed["status_counts"] == {"identity_unresolved": 4}
    assert not seed["records"]
    assert all(r["reason"] == "result_entry_roster_mismatch" for r in seed["inventory"])


def test_budget_is_plan_wide_and_persists_across_resume(tmp_path):
    root = initialized(tmp_path, budget=2)
    asyncio.run(execute(root, response))
    seed = m.replay(root)
    assert seed["request_reservations"] == 2
    assert seed["status_counts"] == {"api_reported_rows": 2, "not_attempted": 2}
    assert asyncio.run(execute(root, response))["new_units"] == 0


def test_page_request_budget_is_not_just_unit_count(tmp_path):
    root = initialized(tmp_path, budget=1)

    def many(request):
        items = [
            {**row(g, race_no=r), "meet": 1} for r in range(1, 7) for g in range(1, 19)
        ]
        return httpx.Response(200, json=envelope(items[:100], total=108))

    asyncio.run(execute(root, many))
    seed = m.replay(root)
    assert seed["request_reservations"] == 1
    assert seed["status_counts"] == {"failed": 1, "not_attempted": 3}
    assert not seed["records"]


def test_failure_stop_retry_and_old_receipts_remain(tmp_path):
    root = initialized(tmp_path)
    asyncio.run(execute(root, lambda r: httpx.Response(503)))
    seed = m.replay(root)
    assert seed["status_counts"] == {"failed": 3, "not_attempted": 1}
    originals = {str(p): p.read_bytes() for p in (root / "receipts").rglob("*.json")}
    asyncio.run(execute(root, response, retry_failed=True))
    assert m.replay(root)["status_counts"] == {"api_reported_rows": 4}
    assert all(Path(p).read_bytes() == raw for p, raw in originals.items())
    assert m.replay(root)["request_reservations"] == 7


def test_empty_responses_are_not_no_race_certificates(tmp_path):
    root = initialized(tmp_path)
    asyncio.run(execute(root, lambda r: response(r, empty=True)))
    seed = m.replay(root)
    assert seed["status_counts"] == {"empty_unconfirmed": 4}
    assert not seed["records"] and not seed["historical_pre_race_availability_verified"]


@pytest.mark.parametrize("change", ["raw", "manifest", "journal", "plan", "receipt"])
def test_tamper_rejected_not_transformed_into_missing_history(tmp_path, change):
    root = initialized(tmp_path)
    asyncio.run(execute(root, response))
    if change == "raw":
        path = next((root / "results").rglob("page_*.json"))
        path.write_bytes(path.read_bytes() + b" ")
    elif change == "manifest":
        path = next((root / "results").rglob("capture.json"))
        path.write_bytes(path.read_bytes() + b" ")
    elif change == "journal":
        (root / "requests/000001.json").unlink()
    elif change == "plan":
        path = root / "plan.json"
        data = json.loads(path.read_bytes())
        data["units"].pop()
        path.write_text(json.dumps(data))
    else:
        path = next((root / "receipts").rglob("*.json"))
        data = json.loads(path.read_bytes())
        data["unit"]["meet"] = 4
        path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        m.replay(root)


def test_implementation_drift_and_parallel_process_lock(tmp_path, monkeypatch):
    root = initialized(tmp_path)
    with m.exclusive(root):
        with pytest.raises(BlockingIOError), m.exclusive(root):
            pytest.fail("second collector acquired the lock")
    monkeypatch.setattr(m, "implementation", lambda: {"changed": True})
    with pytest.raises(ValueError, match="implementation_changed"):
        m.load_plan(root)


def test_export_never_overwrites(tmp_path):
    path = tmp_path / "seed.json"
    m.save(path, {"first": True})
    with pytest.raises(FileExistsError):
        m.save(path, {"second": True})
    assert json.loads(path.read_bytes()) == {"first": True}
