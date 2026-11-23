"""Read the acquisition metadata for one already pinned result version."""

from collections import defaultdict
from pathlib import Path

import kra_walk_forward_fold as fold
from autoresearch import observed_history_seed as history
from autoresearch import official_history_support as official
from autoresearch import versioned_result_observations as results
from autoresearch.kra_race_card_pdf_replay import (
    MAX_MANIFEST_BYTES,
    checked_digest,
    read_bytes,
)
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import encoded, parse_json, sha256

FORMAT = "kra-result-observation-inventory-v1"
require = fold.require


def _path(root, location, *, parent=None):
    path = (root if parent is None else parent) / location
    return fold.private_path(root, path.relative_to(root).as_posix())


def _child(root, parent, ref):
    require(
        not Path(ref["path"]).is_absolute() and ".." not in Path(ref["path"]).parts,
        "observation_nonrelative_source_pin",
    )
    path = _path(root, ref["path"], parent=parent)
    return parse_json(fold._read_pin(path, ref["sha256"]))


def _at(value):
    return timestamp(value).isoformat()


def _api_capture(root, directory, pin, unit, source):
    manifest = _child(root, directory, pin)
    require(
        {k: manifest[v] for k, v in (("day", "race_date"), ("meet", "meet"))} == unit,
        "observation_api_unit_mismatch",
    )
    is_entry = source == "API26"
    ended = _at(manifest["collected_at" if is_entry else "capture_completed_at"])
    started = _at(manifest["fetch_started_at"])
    previous = timestamp(started)
    pages = []
    for number, page in enumerate(manifest["pages"], 1):
        start = previous if is_entry else timestamp(page["fetch_started_at"])
        end = timestamp(page["collected_at" if is_entry else "capture_completed_at"])
        require(
            page["page_no"] == number and previous <= start <= end <= timestamp(ended),
            "observation_api_page_clock_or_ordinal",
        )
        previous = end
        pages.append(
            {
                "page": number,
                "started_at": start.isoformat(),
                "completed_at": end.isoformat(),
                "sha256": checked_digest(page["sha256"]),
            }
        )
    require(timestamp(started) <= timestamp(ended), "observation_api_capture_clock")
    return {
        "source": source,
        "manifest": pin,
        "status": manifest["collection_status" if is_entry else "status"],
        "started_at": started,
        "completed_at": ended,
        "pages": pages,
    }


def _requests(root, directory, plan, digest, count, materialized):
    require(
        type(count) is int and 0 <= count <= plan["request_budget"],
        "observation_invalid_request_count",
    )
    units = {(item["day"], item["meet"]) for item in plan["units"]}
    tape, previous = [], None
    # The saved seed specifies the prefix this version saw; never adopt a later tail.
    for i in range(1, count + 1):
        path = _path(root, f"requests/{i:06d}.json", parent=directory)
        raw = read_bytes(path, limit=MAX_MANIFEST_BYTES)
        request = parse_json(raw)
        reserved = timestamp(request["reserved_at"])
        require(
            type(request["ordinal"]) is int
            and request["ordinal"] == i
            and request["plan_sha256"] == digest
            and type(request["meet"]) is int
            and (request["day"], request["meet"]) in units
            and request["source"] in ("API26", "API214")
            and type(request["page"]) is int
            and request["page"] > 0
            and reserved <= materialized
            and (previous is None or previous <= reserved),
            "observation_invalid_request_record",
        )
        previous = reserved
        tape.append(
            {
                "ordinal": i,
                "day": request["day"],
                "meet": request["meet"],
                "source": request["source"],
                "page": request["page"],
                "reserved_at": reserved.isoformat(),
                "sha256": sha256(raw),
            }
        )
    return tape


def _link_pages(units, requests):
    matching = defaultdict(list)
    for row in requests:
        matching[row["day"], row["meet"], row["source"], row["page"]].append(row)
    used = set()
    unlinked = 0
    for unit in units:
        for capture in unit["captures"]:
            for page in capture["pages"]:
                eligible = [
                    row["ordinal"]
                    for row in matching[
                        unit["day"], unit["meet"], capture["source"], page["page"]
                    ]
                    if timestamp(page["started_at"])
                    <= timestamp(row["reserved_at"])
                    <= timestamp(page["completed_at"])
                ]
                require(
                    len(eligible) <= 1 and not (used & set(eligible)),
                    "observation_ambiguous_request_binding",
                )
                page["local_request_ordinal"] = eligible[0] if eligible else None
                used.update(eligible)
                unlinked += not eligible
    return unlinked, [row["ordinal"] for row in requests if row["ordinal"] not in used]


def _official_captures(root, plan, seed, scope_ids):
    directory = _path(root, plan["official_directory"])
    index = parse_json(
        fold._read_pin(
            _path(root, "archive.json", parent=directory),
            plan["official_archive_sha256"],
        )
    )
    request_plan = _child(root, directory, index["plan"])
    require(
        index["format_version"] == official.FORMAT
        and encoded(request_plan)
        == encoded(official.request_plan(seed, plan["seed_sha256"])),
        "observation_official_request_plan_changed",
    )
    items = []
    for ref, request in zip(index["receipts"], request_plan["requests"], strict=True):
        receipt = _child(root, directory, ref)
        start, end = _at(receipt["started_at"]), _at(receipt["completed_at"])
        require(
            receipt["request"] == request
            and timestamp(start) <= timestamp(end)
            and (request["kind"] != "detail" or request["key"] in scope_ids),
            "observation_official_receipt_conflict",
        )
        items.append(
            {
                "key": request["key"],
                "kind": request["kind"],
                "receipt": ref,
                "status": receipt["status"],
                "started_at": start,
                "completed_at": end,
            }
        )
    seen = {item["key"] for item in items if item["kind"] == "detail"}
    return items, sorted(scope_ids - seen)


def inventory(root, plan_ref, *, race_dates, race_ids, schedule_sha256):
    """Return only selected source pins and clocks, not outcomes or authority."""
    root = root.resolve()
    _, raw = fold._pinned(root, plan_ref)
    plan = parse_json(raw)
    require(
        race_dates
        and race_ids
        and plan["format_version"] == results.FORMAT
        and plan["race_dates"] == race_dates
        and plan["schedule_sha256"] == schedule_sha256,
        "observation_result_plan_not_original_scope",
    )
    directory = _path(root, plan["seed_root"])
    _path(root, "plan.json", parent=directory)
    seed_plan, digest = history.load_plan(directory, require_current=False)
    require(
        seed_plan["start"] == race_dates[0] and seed_plan["end"] == race_dates[-1],
        "observation_seed_plan_not_original_dates",
    )
    seed = parse_json(
        fold._read_pin(_path(root, plan["seed_path"]), plan["seed_sha256"])
    )
    scope_ids = set(race_ids)
    require(
        seed["format_version"] == history.SEED_FORMAT
        and seed["plan_sha256"] == digest
        and {item["race_id"] for item in seed["records"]} <= scope_ids,
        "observation_seed_scope_conflict",
    )
    materialized = timestamp(seed["materialized_at"])
    requests = _requests(
        root, directory, seed_plan, digest, seed["request_reservations"], materialized
    )
    units = []
    for selected, unit in zip(seed["inventory"], seed_plan["units"], strict=True):
        require(
            all(selected[key] == val for key, val in unit.items()),
            "observation_seed_inventory_unit_conflict",
        )
        captures = [
            _api_capture(root, directory, selected[field], unit, source)
            for field, source in (("result", "API214"), ("entry", "API26"))
            if selected.get(field) is not None
        ]
        require(
            (selected["status"] == "not_attempted") == (not captures)
            and all(timestamp(c["completed_at"]) <= materialized for c in captures),
            "observation_seed_inventory_clock_or_state_conflict",
        )
        units.append(unit | {"status": selected["status"], "captures": captures})
    unlinked, unused = _link_pages(units, requests)
    official_captures, absent_details = _official_captures(root, plan, seed, scope_ids)
    return {
        "format": FORMAT,
        "result_plan": plan_ref,
        "schedule_sha256": schedule_sha256,
        "api_plan_sha256": digest,
        "api_seed_sha256": plan["seed_sha256"],
        "api_seed_materialized_at": materialized.isoformat(),
        "api_units": units,
        "local_api_requests": requests,
        "api_pages_without_local_request": unlinked,
        "local_api_request_ordinals_without_selected_pages": unused,
        "official_archive_sha256": plan["official_archive_sha256"],
        "official_captures": official_captures,
        "frozen_races_without_official_detail_request": absent_details,
        "independent_collection_clock_verified": False,
        "result_version_selection_verified": False,
        "training_approved": False,
    }


def window_holds(report, *, opens_at, closes_at):
    """Check recorded source clocks only, for a caller's fixed half-open window."""
    opening, closing = timestamp(opens_at), timestamp(closes_at)
    require(opening < closing, "observation_invalid_window")

    def inside(captures):
        return all(
            opening
            <= timestamp(row["started_at"])
            <= timestamp(row["completed_at"])
            < closing
            for row in captures
        )

    api = [c for unit in report["api_units"] for c in unit["captures"]]
    holds = []
    if not api:
        holds.append("no_selected_api_capture")
    if not inside(api):
        holds.append("api_capture_outside_window")
    if not inside(report["official_captures"]):
        holds.append("official_capture_outside_window")
    if not all(
        opening <= timestamp(row["reserved_at"]) < closing
        for row in report["local_api_requests"]
    ):
        holds.append("local_request_outside_window")
    if report["api_pages_without_local_request"]:
        holds.append("selected_api_page_has_no_window_request")
    if report["local_api_request_ordinals_without_selected_pages"]:
        holds.append("recorded_request_has_no_selected_page")
    if report["frozen_races_without_official_detail_request"]:
        holds.append("original_official_detail_not_requested")
    return holds
