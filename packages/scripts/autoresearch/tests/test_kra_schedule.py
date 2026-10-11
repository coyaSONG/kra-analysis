"""Whole-population and original-source regressions for future race freezing."""

import asyncio
import hashlib
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.kra_schedule import (
    SOURCE_URLS,
    parse_schedule_html,
    reconcile_schedule_cards,
)

from autoresearch.kra_schedule_snapshot import (
    collect_schedule_snapshot,
    freeze_universe_candidate,
    main,
    replay_schedule_snapshot,
)

NOW = datetime(2026, 10, 14, 9, tzinfo=UTC)
DATE = "20261016"
VENUES = {1: "\uc11c\uc6b8", 2: "\uc81c\uc8fc", 3: "\ubd80\uacbd", 4: "\uc601\ucc9c"}


def page(source, *, dates=None, times=None, numbers=None, notes=""):
    national = source == "national"
    venues = (
        [1, 2, 3, 4]
        if national
        else [1]
        if source == "region_1"
        else [2]
        if source == "region_2"
        else [3, 4]
    )
    dates, times, numbers = dates or {}, times or {}, numbers or {}
    if national:
        headers = [
            "\uc21c",
            "\uc9c0\uc5ed",
            "\uacbd\uc8fc\uc77c\uc790",
            "\uacbd\uc8fc",
            "\ub4f1\uae09",
            "\uac70\ub9ac",
            "\ucd9c\uc804",
            "\uacbd\uc8fc<br>\uad6c\ubd84",
            "\ucd9c\ubc1c<br>\uc2dc\uac01",
            "\uc624\ub298\uc758<br>\uacbd\uc8fc",
            "\ud310\ub9e4\uacbd\ub9c8\uacf5\uc6d0",
        ]
    else:
        headers = [
            "\uc21c",
            "\uacbd\uc8fc\uc77c\uc790",
            "\uacbd\uc8fc",
            "\ub4f1\uae09",
            "\uac70\ub9ac",
            "\ud3b8\uc131",
            "\ucd9c\uc804",
            "\uacbd\uc8fc\uba85",
            "\ucd9c\ubc1c\uc2dc\uac01",
            "\uac1c\ucd5c\uc9c0",
            "\ube44\uace0",
            "PDF",
        ]
    header = "<tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr>"
    if national:
        header += (
            "<tr>" + "".join(f"<th>{VENUES[v]}</th>" for v in (1, 3, 4, 2)) + "</tr>"
        )
    rows = []
    for ordinal, venue in enumerate(venues, 1):
        date = dates.get(venue, "2026/10/16(\uae08)")
        start = times.get(venue, "12:00")
        number = numbers.get(venue, 1)
        if national:
            cells = [
                ordinal,
                VENUES[venue],
                date,
                number,
                "class",
                "1200",
                "10",
                "ordinary",
                start,
                "",
                "Y",
                "Y",
                "Y",
                "Y",
            ]
        else:
            cells = [
                ordinal,
                date,
                number,
                "class",
                "1200M",
                "11\ub450",
                "10\ub450",
                "ordinary",
                start,
                VENUES[venue],
                notes,
                "",
            ]
        rows.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    return (
        "<html><table><caption>Official dated race card</caption><thead>"
        + header
        + "</thead><tbody>"
        + "".join(rows)
        + "</tbody></table></html>"
    ).encode()


def cards():
    return {
        key: parse_schedule_html(page(key), source_id=key, encoding="utf-8")
        for key in SOURCE_URLS
    }


def capture(tmp_path, *, pages=None, fail_source=None, clock=lambda: NOW):
    originals = {key: page(key) for key in SOURCE_URLS}
    originals.update(pages or {})

    def respond(request):
        source = next(
            key for key, url in SOURCE_URLS.items() if str(request.url) == url
        )
        if source == fail_source:
            return httpx.Response(503, request=request)
        return httpx.Response(
            200,
            content=originals[source],
            headers={"content-type": "text/html; charset=utf-8"},
            request=request,
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await collect_schedule_snapshot(
                output_dir=tmp_path, client=client, clock=clock
            )

    return asyncio.run(run())


def rewrite_manifest(path, change):
    manifest = json.loads(path.read_bytes())
    change(manifest)
    path.write_text(json.dumps(manifest))


def test_all_physical_venues_are_reconciled_without_result_or_feature_filtering():
    parsed = cards()
    assert [r.meet for r in parsed["region_3"]] == [3, 4]
    result = reconcile_schedule_cards(parsed, race_date=DATE)
    assert result["status"] == "reconciled"
    assert result["race_count"] == 4
    assert [r["race_id"] for r in result["races"]] == [
        f"{DATE}_{v}_1" for v in (1, 2, 3, 4)
    ]
    assert result["target_accuracy_verified"] is False


def test_cancelled_race_is_preserved_with_original_notes():
    parsed = cards()
    parsed["region_1"] = parse_schedule_html(
        page("region_1", notes="\ubd88\uc131\ub9bd"),
        source_id="region_1",
        encoding="utf-8",
    )
    result = reconcile_schedule_cards(parsed, race_date=DATE)
    assert result["race_count"] == 4
    assert (
        result["races"][0]["source_observations"]["region_1"]["notes"]
        == "\ubd88\uc131\ub9bd"
    )


def test_unknown_future_date_is_not_an_empty_complete_universe():
    result = reconcile_schedule_cards(cards(), race_date="20261023")
    assert result["status"] == "unknown" and result["race_count"] == 0
    assert {i["code"] for i in result["issues"]} == {"requested_date_not_published"}


@pytest.mark.parametrize("missing", SOURCE_URLS)
def test_missing_source_never_certifies_partial_population(missing):
    parsed = cards()
    del parsed[missing]
    result = reconcile_schedule_cards(parsed, race_date=DATE)
    assert result["status"] != "reconciled"
    assert result["race_count"] == 4


def test_time_conflict_preserves_both_versions_and_all_races():
    parsed = cards()
    parsed["region_1"] = parse_schedule_html(
        page("region_1", times={1: "12:05"}), source_id="region_1", encoding="utf-8"
    )
    result = reconcile_schedule_cards(parsed, race_date=DATE)
    assert result["status"] == "conflict" and result["race_count"] == 4
    issue = result["issues"][0]
    assert (
        issue["national"]["scheduled_start_at"]
        != issue["regional"]["scheduled_start_at"]
    )


def test_membership_conflict_detected_in_both_directions():
    parsed = cards()
    parsed["national"] = parsed["national"][:-1]
    result = reconcile_schedule_cards(parsed, race_date=DATE)
    assert result["status"] == "conflict" and result["race_count"] == 4
    parsed = cards()
    parsed["region_3"] = parsed["region_3"][:-1]
    result = reconcile_schedule_cards(parsed, race_date=DATE)
    assert result["status"] == "conflict" and result["race_count"] == 4


def test_conflicting_other_date_prevents_partial_week_acceptance():
    parsed = cards()
    parsed["region_2"] = parse_schedule_html(
        page("region_2", dates={2: "2026/10/23(\uae08)"}),
        source_id="region_2",
        encoding="utf-8",
    )
    result = reconcile_schedule_cards(parsed, race_date=DATE)
    assert result["status"] == "conflict"
    assert "mixed_or_missing_card_week" in {i["code"] for i in result["issues"]}


@pytest.mark.parametrize(
    "mutation,reason",
    [
        (lambda s: s.replace(b"<td>1</td>", b"<td>2</td>", 1), "ordinal"),
        (lambda s: s.replace(b"12:00", b"24:00"), "hour"),
        (lambda s: s.replace(b"2026/10/16", b"2026/02/30"), "day"),
        (lambda s: s.replace(b"2026/10/16", b"2026/10/17"), "weekday"),
        (lambda s: s.replace(b"</table>", b""), "incomplete"),
        (lambda s: s.replace(b"<td>", b'<td colspan="2">', 1), "incomplete"),
        (lambda s: s.replace(b"<td>class</td>", b""), "columns"),
        (lambda s: b"<html>Service unavailable</html>", "missing"),
        (lambda s: s + s, "duplicate"),
    ],
)
def test_malformed_source_cannot_silently_drop_or_shift_rows(mutation, reason):
    with pytest.raises(ValueError, match=reason):
        parse_schedule_html(
            mutation(page("region_1")), source_id="region_1", encoding="utf-8"
        )


def test_unknown_venue_and_wrong_region_are_rejected():
    for replacement in ("unknown", VENUES[4]):
        content = page("region_1").replace(VENUES[1].encode(), replacement.encode())
        with pytest.raises(ValueError):
            parse_schedule_html(content, source_id="region_1", encoding="utf-8")


def test_race_number_gap_is_rejected():
    with pytest.raises(ValueError, match="race_number_gap"):
        parse_schedule_html(
            page("region_1", numbers={1: 2}), source_id="region_1", encoding="utf-8"
        )


def test_source_runner_count_disagreement_is_conflict():
    parsed = cards()
    content = page("national").replace(b"<td>10</td>", b"<td>9</td>", 1)
    parsed["national"] = parse_schedule_html(
        content, source_id="national", encoding="utf-8"
    )
    assert reconcile_schedule_cards(parsed, race_date=DATE)["status"] == "conflict"


def test_original_bytes_capture_replay_and_future_local_freeze(tmp_path):
    path = capture(tmp_path)
    manifest = json.loads(path.read_bytes())
    for source, record in manifest["sources"].items():
        content = (path.parent / record["raw_file"]).read_bytes()
        assert content == page(source)
        assert record["sha256"] == hashlib.sha256(content).hexdigest()
    audit = replay_schedule_snapshot(path, race_date=DATE)
    assert audit["status"] == "reconciled" and len(audit["source_pins"]) == 4
    output = tmp_path / "frozen.json"
    receipt = freeze_universe_candidate(
        path, race_date=DATE, output=output, clock=lambda: NOW
    )
    frozen = json.loads(output.read_bytes())
    assert receipt["sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert frozen["race_count"] == 4
    assert frozen["registration_status"] == "pending_independent_server_receipt"
    assert not frozen["independent_time_verified"]


@pytest.mark.parametrize("source", SOURCE_URLS)
def test_fetch_failure_keeps_other_originals_and_all_known_races(tmp_path, source):
    path = capture(tmp_path, fail_source=source)
    report = replay_schedule_snapshot(path, race_date=DATE)
    assert len(report["source_pins"]) == 3
    assert report["race_count"] == 4
    assert report["status"] != "reconciled"
    with pytest.raises(ValueError, match="complete_reconciled"):
        freeze_universe_candidate(
            path,
            race_date=DATE,
            output=tmp_path / "not_created" / "frozen.json",
            clock=lambda: NOW,
        )
    assert not (tmp_path / "not_created").exists()


@pytest.mark.parametrize(
    "change",
    [
        lambda m: m["sources"]["national"].update(sha256="0" * 64),
        lambda m: m["sources"]["national"].update(byte_count=1),
        lambda m: m["sources"]["national"].update(raw_file="../other.html"),
        lambda m: m["sources"]["national"].update(url="https://example.org/"),
        lambda m: m["sources"]["national"].update(
            capture_completed_at="2026-10-14T09:00:00"
        ),
        lambda m: m["sources"]["national"].update(
            capture_completed_at="2026-10-14T10:00:00+00:00"
        ),
    ],
)
def test_bad_capture_pins_or_times_block_reconciliation(tmp_path, change):
    path = capture(tmp_path)
    rewrite_manifest(path, change)
    report = replay_schedule_snapshot(path, race_date=DATE)
    assert report["status"] != "reconciled"
    assert report["source_failures"][0]["source_id"] == "national"


def test_changed_original_bytes_are_detected(tmp_path):
    path = capture(tmp_path)
    record = json.loads(path.read_bytes())["sources"]["national"]
    (path.parent / record["raw_file"]).write_bytes(b"modified")
    assert (
        replay_schedule_snapshot(path, race_date=DATE)["source_failures"][0]["error"]
        == "schedule_source_hash_mismatch"
    )


@pytest.mark.parametrize(
    "at",
    [
        datetime(2026, 10, 16, 2, 30, tzinfo=UTC),
        datetime(2026, 10, 16, 3, 0, tzinfo=UTC),
        NOW - timedelta(seconds=1),
    ],
)
def test_late_or_backdated_freeze_cannot_create_output(tmp_path, at):
    path = capture(tmp_path)
    target = tmp_path / "forbidden" / "universe.json"
    with pytest.raises(ValueError, match="earliest_cutoff"):
        freeze_universe_candidate(path, race_date=DATE, output=target, clock=lambda: at)
    assert not target.parent.exists()


def test_unknown_date_does_not_create_frozen_file(tmp_path):
    path = capture(tmp_path)
    with pytest.raises(ValueError, match="complete_reconciled"):
        freeze_universe_candidate(
            path,
            race_date="20261023",
            output=tmp_path / "absent.json",
            clock=lambda: NOW,
        )
    assert not (tmp_path / "absent.json").exists()


def test_existing_frozen_file_is_never_replaced(tmp_path):
    path = capture(tmp_path)
    target = tmp_path / "universe.json"
    target.write_bytes(b"owner data")
    with pytest.raises(FileExistsError):
        freeze_universe_candidate(
            path, race_date=DATE, output=target, clock=lambda: NOW
        )
    assert target.read_bytes() == b"owner data"


def test_audit_cli_returns_nonzero_for_unpublished_future(tmp_path, capsys):
    path = capture(tmp_path)
    assert main(["audit", "--capture", str(path), "--race-date", "20261023"]) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "unknown"


def test_identical_capture_calls_preserve_distinct_original_bundles(tmp_path):
    first, second = capture(tmp_path), capture(tmp_path)
    assert first != second and first.exists() and second.exists()


@pytest.mark.parametrize("kind", ["redirect", "json", "oversized", "http_error"])
def test_noncanonical_or_oversized_responses_never_enter_a_freeze(
    tmp_path, monkeypatch, kind
):
    import autoresearch.kra_schedule_snapshot as module

    monkeypatch.setattr(module, "MAX_SOURCE_BYTES", 100)
    requests = []

    def respond(request):
        requests.append(str(request.url))
        if kind == "http_error":
            raise httpx.ReadTimeout("upstream timed out", request=request)
        if kind == "redirect":
            return httpx.Response(302, headers={"location": "https://example.org/"})
        return httpx.Response(
            200,
            headers={
                "content-type": "application/json" if kind == "json" else "text/html"
            },
            content=b"x" * 101,
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await collect_schedule_snapshot(
                output_dir=tmp_path, client=client, clock=lambda: NOW
            )

    path = asyncio.run(run())
    assert requests == list(SOURCE_URLS.values())
    report = replay_schedule_snapshot(path, race_date=DATE)
    assert report["status"] == "unknown"
    assert len(report["source_failures"]) == 4
    assert not list(path.parent.glob("*.html"))


def test_malformed_html_is_retained_but_never_accepted(tmp_path):
    path = capture(tmp_path, pages={"region_3": b"<html>Unavailable</html>"})
    record = json.loads(path.read_bytes())["sources"]["region_3"]
    assert (
        path.parent / record["raw_file"]
    ).read_bytes() == b"<html>Unavailable</html>"
    report = replay_schedule_snapshot(path, race_date=DATE)
    assert report["race_count"] == 4 and report["status"] != "reconciled"


def test_missing_source_manifest_cannot_be_treated_as_complete(tmp_path):
    path = capture(tmp_path)
    rewrite_manifest(path, lambda m: m["sources"].pop("region_3"))
    with pytest.raises(ValueError, match="incomplete_schedule_source_manifest"):
        replay_schedule_snapshot(path, race_date=DATE)


def test_source_symlink_is_not_a_pinned_original(tmp_path):
    path = capture(tmp_path)
    record = json.loads(path.read_bytes())["sources"]["national"]
    raw = path.parent / record["raw_file"]
    other = tmp_path / "other.html"
    raw.rename(other)
    raw.symlink_to(other)
    assert (
        replay_schedule_snapshot(path, race_date=DATE)["source_failures"][0]["error"]
        == "schedule_source_symlink"
    )


def test_capture_completion_in_past_or_excessive_window_is_rejected(tmp_path):
    for seconds in (-1, 301):
        path = capture(tmp_path)
        rewrite_manifest(
            path,
            lambda m, seconds=seconds: m.update(
                capture_completed_at=(NOW + timedelta(seconds=seconds)).isoformat()
            ),
        )
        with pytest.raises(ValueError, match="clock_window"):
            replay_schedule_snapshot(path, race_date=DATE)


def test_all_sources_same_datetime_has_explicit_kst_race_deadline(tmp_path):
    path = capture(tmp_path)
    target = tmp_path / "universe.json"
    freeze_universe_candidate(path, race_date=DATE, output=target, clock=lambda: NOW)
    row = json.loads(target.read_bytes())["races"][0]
    assert row["scheduled_start_at"] == "2026-10-16T12:00:00+09:00"
    assert row["feature_cutoff_at"] == "2026-10-16T02:30:00+00:00"


def test_empty_official_table_does_not_prove_no_racing():
    source = page("region_1")
    source = source.split(b"<tbody>")[0] + b"<tbody></tbody></table></html>"
    with pytest.raises(ValueError, match="incomplete_schedule_table"):
        parse_schedule_html(source, source_id="region_1", encoding="utf-8")


def test_slow_stream_has_whole_request_deadline_and_retains_failure(
    tmp_path, monkeypatch
):
    import autoresearch.kra_schedule_snapshot as module

    monkeypatch.setattr(module, "SOURCE_TIMEOUT_SECONDS", 0.01)

    class SlowStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"<html>"
            await asyncio.sleep(1)
            yield b"</html>"

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    200, headers={"content-type": "text/html"}, stream=SlowStream()
                )
            )
        ) as client:
            return await collect_schedule_snapshot(
                output_dir=tmp_path, client=client, clock=lambda: NOW
            )

    path = asyncio.run(run())
    manifest = json.loads(path.read_bytes())
    assert all(s["error_type"] == "TimeoutError" for s in manifest["sources"].values())
    assert not list(path.parent.glob("*.html"))
    assert replay_schedule_snapshot(path, race_date=DATE)["status"] == "unknown"
