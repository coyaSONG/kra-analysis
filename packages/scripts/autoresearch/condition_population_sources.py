"""Pinned schedule observations, never final inventory or no-race evidence."""

from pathlib import Path

from shared.kra_schedule import (
    SOURCE_URLS,
    parse_schedule_html,
    reconcile_schedule_cards,
)

from autoresearch.condition_historical_publication import pin
from autoresearch.kra_schedule_snapshot import (
    FORMAT_VERSION,
    MAX_CAPTURE_SECONDS,
    MAX_SOURCE_BYTES,
)
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import parse_json


def snapshot(root, reference, recorded_at):
    raw = pin(root, reference)
    capture = parse_json(raw)
    if capture["format_version"] != FORMAT_VERSION or capture.get("error"):
        raise ValueError("population_capture_schema")
    started = timestamp(capture["fetch_started_at"])
    completed = timestamp(capture["capture_completed_at"])
    if (
        not started <= completed <= recorded_at
        or (completed - started).total_seconds() > MAX_CAPTURE_SECONDS
    ):
        raise ValueError("population_capture_clock")
    if set(capture["sources"]) != set(SOURCE_URLS):
        raise ValueError("population_capture_sources")
    directory = (root / reference["path"]).parent
    cards, failures, previous = {}, [], started
    for source_id, url in SOURCE_URLS.items():
        source = capture["sources"][source_id]
        if source["url"] != url:
            raise ValueError("population_source_url")
        if source["status"] != "captured":
            failures.append({"source": source_id, "status": source["status"]})
            continue
        request_at = timestamp(source["fetch_started_at"])
        observed_at = timestamp(source["capture_completed_at"])
        if not previous <= request_at <= observed_at <= completed:
            raise ValueError("population_source_clock")
        previous = observed_at
        filename = f"{source_id}_{source['sha256']}.html"
        if source["raw_file"] != filename or Path(filename).name != filename:
            raise ValueError("population_source_filename")
        try:
            content = pin(directory, {"path": filename, "sha256": source["sha256"]})
        except FileNotFoundError:
            failures.append({"source": source_id, "status": "missing_local_original"})
            continue
        if (
            type(source["byte_count"]) is not int
            or len(content) != source["byte_count"]
        ):
            raise ValueError("population_source_byte_count")
        if len(content) > MAX_SOURCE_BYTES:
            raise ValueError("population_source_too_large")
        try:
            cards[source_id] = parse_schedule_html(
                content, source_id=source_id, encoding=source["encoding"]
            )
        except (ValueError, LookupError) as exc:
            failures.append(
                {"source": source_id, "status": "unparsed_original", "reason": str(exc)}
            )
    dates = sorted({r.race_date for rows in cards.values() for r in rows})
    return {
        "capture_sha256": reference["sha256"],
        "capture_completed_at": completed.isoformat(),
        "source_failures": failures,
        "dates": [reconcile_schedule_cards(cards, race_date=day) for day in dates],
        "scope": "snapshot_membership_only",
        "full_population_verified": False,
    }
