"""Whole-roster support is not an identity guess or retrospective approval."""

import asyncio
import copy
import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.official_result_support import (
    DETAIL_CAPTION,
    LIST_CAPTION,
    TIME_CAPTION,
    parse_detail,
    parse_list,
    reconcile_group,
)

from autoresearch import official_history_support as support
from autoresearch.frozen_history_view import replay_frozen
from autoresearch.observed_history_seed import digest, save
from autoresearch.tests.test_history_identity_audit import source
from autoresearch.tests.test_observed_result_history import fixture


def html(records, *, date="20261010", venue="\ubd80\uacbd"):
    head = f"{date[:4]}\ub144 {date[4:6]}\uc6d4 {date[6:]}\uc77c (\ud1a0) \uc81c1\uacbd\uc8fc {venue}"
    details, times = [], []
    for row in records:
        rank, gate, horse = row["raw_ord"], row["chul_no"], row["horse_id"]
        seconds = float(row["raw_rc_time"] or 0)
        time = f"{int(seconds // 60)}:{seconds % 60:04.1f}"
        details.append(
            f"<tr><td>{rank}</td><td>{gate}</td><td><a href=\"javascript:goHorse('{int(horse):07}','1')\">name</a></td></tr>"
        )
        times.append(f"<tr><td>{rank}</td><td>{gate}</td><td>{time}</td></tr>")
    return (
        f"<table><tr><td>{head}</td></tr></table>"
        f"<table><caption>{DETAIL_CAPTION}</caption><thead><tr><th>rank</th><th>gate</th><th>name</th></tr></thead><tbody>{''.join(details)}</tbody></table>"
        f"<table><caption>{TIME_CAPTION}</caption><thead><tr><th>rank</th><th>gate</th><th>time</th></tr></thead><tbody>{''.join(times)}</tbody></table>"
    )


def records():
    return [
        {
            "race_id": "20261010_3_1",
            "chul_no": n,
            "horse_id": str(100 + n),
            "raw_ord": n,
            "raw_rc_time": 60 + n / 10,
            "evidence": "ranked_finish_observed",
        }
        for n in (1, 2, 3)
    ]


def test_full_roster_and_fields_not_horse_link_venue():
    rows = records()
    parsed = parse_detail(html(rows))
    assert parsed["race_id"] == "20261010_3_1"
    assert [r["horse_id"] for r in parsed["rows"]] == ["101", "102", "103"]
    result = reconcile_group(rows, parsed)
    assert result["roster_support"] == "exact"
    assert all(r["ranked_feature_supported"] for r in result["rows"])


def test_multiple_timing_tables_must_agree():
    text = html(records())
    start = text.index(f"<table><caption>{TIME_CAPTION}")
    timing = text[start:]
    parsed = parse_detail(text + timing)
    assert len(parsed["rows"][0]["timing_locations"]) == 2
    with pytest.raises(ValueError, match="time_disagreement"):
        parse_detail(text + timing.replace("1:00.1", "1:00.2"))


@pytest.mark.parametrize(
    "change",
    [
        "id",
        "duplicate_gate",
        "duplicate_horse",
        "truncated",
        "span",
        "time_missing",
        "rank_disagree",
    ],
)
def test_incomplete_tables_never_certify_roster(change):
    text = html(records())
    if change == "id":
        text = text.replace("javascript:goHorse('0000101','1')", "#")
    elif change == "duplicate_gate":
        text = text.replace("<td>2</td><td>2</td>", "<td>2</td><td>1</td>")
    elif change == "duplicate_horse":
        text = text.replace("0000102", "0000101")
    elif change == "truncated":
        text = text[:-8]
    elif change == "span":
        text = text.replace("<td>2</td>", '<td colspan="2">2</td>')
    elif change == "time_missing":
        text = text.replace("<tr><td>2</td><td>2</td><td>1:00.2</td></tr>", "")
    else:
        text = text.replace(
            "<td>2</td><td>2</td><td>1:00.2", "<td>4</td><td>2</td><td>1:00.2"
        )
    with pytest.raises(ValueError):
        parse_detail(text)


def test_empty_template_request_fields_do_not_certify_event():
    text = '<input name="realRcDate" value="20261010"><script>2026\ub144 10\uc6d4 10\uc77c (\ud1a0) \uc81c1\uacbd\uc8fc \ubd80\uacbd</script>'
    parsed = parse_detail(text)
    assert parsed["event_support"] == "unknown"
    assert reconcile_group(records(), parsed)["official_event_support"] == "unknown"


def test_wrong_date_conflicts_without_relabeling():
    result = reconcile_group(records(), parse_detail(html(records(), date="20261011")))
    assert result["official_event_support"] == "conflict"
    assert result["race_id"] == "20261010_3_1"
    assert not result["rows"]


def test_roster_match_does_not_certify_changed_rank_or_time():
    parsed = parse_detail(html(records()))
    parsed["rows"][0]["rank_text"] = "4"
    parsed["rows"][1]["time_text"] = "1:00.9"
    result = reconcile_group(records(), parsed)
    assert result["official_event_support"] == "confirmed"
    assert result["roster_support"] == "exact"
    assert [r["ranked_feature_supported"] for r in result["rows"]] == [
        False,
        False,
        True,
    ]


def test_roster_difference_is_not_a_successful_intersection():
    result = reconcile_group(records(), parse_detail(html(records()[:2])))
    assert result["roster_support"] == "mismatch"
    assert not result["rows"]


def test_unresolved_and_nonconsecutive_ranks_preserve_all_rows():
    rows = records()
    rows[1].update(raw_ord="", raw_rc_time=0, evidence="unresolved")
    parsed = parse_detail(html(rows))
    result = reconcile_group(rows, parsed)
    assert result["roster_support"] == "exact"
    assert len(result["rows"]) == 3
    assert result["rows"][1]["event_linked_api_unresolved"]
    assert result["rows"][1]["status_support"] == "not_checked"


def test_same_roster_valid_on_two_dates_is_not_deduplicated():
    for day in ("20261010", "20261011"):
        rows = [{**r, "race_id": f"{day}_3_1"} for r in records()]
        assert all(
            r["ranked_feature_supported"]
            for r in reconcile_group(rows, parse_detail(html(rows, date=day)))["rows"]
        )
    assert (
        reconcile_group(records(), parse_detail("<html></html>"))[
            "official_event_support"
        ]
        == "unknown"
    )


def test_list_retains_void_links_and_physical_venue():
    text = f'<table><caption>{LIST_CAPTION}</caption><tr><th>order</th></tr><tr><td>1</td><td>\uc601\ucc9c</td><td>2026/10/11 (\uc77c)</td><td><a href="#open">1 \uc0c1\uc138\uc5f4\uae30</a> <a href="#">2</a></td></tr></table>'
    assert [r["race_id"] for r in parse_list(text)] == ["20261011_4_1", "20261011_4_2"]


def test_yeongcheon_detail_uses_physical_link_code_not_menu_code():
    from urllib.parse import parse_qs, urlsplit

    plan = support.request_plan({"records": [{"race_id": "20260913_4_1"}]}, "a" * 64)
    params = parse_qs(urlsplit(plan["requests"][0]["url"]).query)
    assert params["meet"] == ["4"]


def test_list_incident_numbers_are_not_race_members():
    text = f'<table><caption>{LIST_CAPTION}</caption><tr><td>1</td><td>\uc11c\uc6b8</td><td>2026/10/10</td><td><a href="#open">1 \uc0c1\uc138\uc5f4\uae30</a><div>7 incident 2026</div><a href="#">2</a></td></tr></table>'
    assert [r["race_id"] for r in parse_list(text)] == ["20261010_1_1", "20261010_1_2"]


def captured(tmp_path):
    root, path, sha = source(tmp_path)
    seed = replay_frozen(root, path, sha)
    directory = tmp_path / "official"

    def handler(request):
        return httpx.Response(
            200,
            text=html(seed["records"]),
            headers={"content-type": "text/html; charset=utf-8"},
        )

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await support.collect(directory, seed, sha, client=client, delay=0)

    receipt = asyncio.run(run())
    return root, path, sha, seed, directory, receipt


def test_capture_replay_and_resume_uses_pinned_bytes(tmp_path):
    root, path, sha, seed, directory, receipt = captured(tmp_path)
    result = support.replay_archive(directory, receipt["sha256"], seed, sha)
    assert result["20261010_3_1"]["parsed"]["event_support"] == "confirmed"

    async def run():
        def fail(request):
            raise AssertionError("resume must not fetch")

        async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as client:
            return await support.collect(directory, seed, sha, client=client, delay=0)

    assert asyncio.run(run()) == receipt
    with pytest.raises(ValueError, match="after_cutoff"):
        support.replay_archive(
            directory, receipt["sha256"], seed, sha, "2026-01-01T00:00:00Z"
        )
    raw = next(directory.glob("*.html"))
    raw.write_bytes(raw.read_bytes() + b" ")
    with pytest.raises(ValueError, match="pin_mismatch"):
        support.replay_archive(directory, receipt["sha256"], seed, sha)


def test_manifest_pin_and_membership_rejection(tmp_path):
    _, _, sha, seed, directory, receipt = captured(tmp_path)
    with pytest.raises(ValueError, match="archive_pin"):
        support.replay_archive(directory, "0" * 64, seed, sha)
    manifest = json.loads((directory / "archive.json").read_bytes())
    manifest["receipts"].pop()
    (directory / "archive.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="incomplete"):
        support.replay_archive(
            directory, digest((directory / "archive.json").read_bytes()), seed, sha
        )


def test_full_diagnostic_targets_no_labels_or_training_selection(tmp_path):
    root, path, sha, seed, directory, receipt = captured(tmp_path)
    race, _ = fixture()
    race["roster"] = [
        {"horse_id": r["horse_id"], "chul_no": r["chul_no"]} for r in seed["records"]
    ]
    corpus = {
        "ledger": [
            race,
            {
                **copy.deepcopy(race),
                "race_id": "20261012_1_1",
                "training_selected": False,
            },
        ]
    }
    cp = root / "corpus.json"
    cs = save(cp, corpus)
    args = (root, path, sha, directory, receipt["sha256"], cp, cs)
    before = path.read_bytes()
    result = support.materialize(*args)
    assert (result["race_count"], result["runner_count"]) == (2, 6)
    assert result["supported_ranked_rows"] == 3
    assert (
        not result["training_approved"] and not result["counts_as_70_percent_evidence"]
    )
    assert result["official_list_errors"]
    assert result == support.materialize(*args)
    corpus["ledger"][0]["label_top3"] = [19, 18, 17]
    cp2 = root / "new-corpus.json"
    cs2 = save(cp2, corpus)
    other = support.materialize(root, path, sha, directory, receipt["sha256"], cp2, cs2)
    assert result["races"] == other["races"]
    assert path.read_bytes() == before


def test_failed_fetch_preserved_as_unknown(tmp_path):
    seed = {"records": []}

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda r: httpx.Response(503))
        ) as client:
            return await support.collect(
                tmp_path, seed, "a" * 64, client=client, delay=0
            )

    receipt = asyncio.run(run())
    parsed = support.replay_archive(tmp_path, receipt["sha256"], seed, "a" * 64)
    assert len(parsed) == 12
    assert all(v["parsed"]["reason"] == "fetch_error" for v in parsed.values())
