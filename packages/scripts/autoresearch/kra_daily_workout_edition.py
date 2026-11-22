"""Replay the independently timed November 22 daily workout source edition."""

from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path

from autoresearch import condition_forward_publication as publication
from autoresearch.kra_daily_workout_navigation import (
    all_detail_request,
    dated_group_request,
)
from autoresearch.kra_daily_workout_source import (
    DETAIL,
    GROUPS,
    KST,
    WorkoutEvidence,
    index_path,
    read_scoped_workouts,
)
from autoresearch.kra_entry_scope_intake import _pinned
from autoresearch.kra_race_card_pdf_replay import archive_path
from autoresearch.prerace_hash_witness import timestamp
from autoresearch.restricted_cohort import encoded, parse_json

PULL = 176
DOCUMENT = "docs/research/2026-11-23-daily-workout-edition-witness.md"
DOCUMENT_SHA256 = "630f0ed56231dd330724de404925d1df40922116a4b5f1cde44b9d464da6b6b2"
EDITION_SHA256 = "34b8c15258cde336a7cfc7d9cb9b4cf935fa438428fb3a7ab73c2b279e3d3216"
EDITION_FORMAT = "kra-daily-workout-source-only-edition-v1"
DAY = date(2026, 11, 22)
ORIGIN = "https://race.kra.co.kr"


@dataclass(frozen=True)
class DailyEdition:
    day: date
    observed: datetime
    published: datetime
    identities: dict[str, tuple[int, WorkoutEvidence]]


def _source_response(root, source, url, lane, form, *, day):
    path, receipt_raw = _pinned(root, source["receipt"])
    receipt = parse_json(receipt_raw)
    reservation = receipt["reservation"]
    reservation_path = path.parent / reservation["path"]
    _, request_raw = _pinned(root, {**reservation, "path": reservation_path})
    request = parse_json(request_raw)
    raw_path, body = _pinned(root, source["raw"])
    observed = timestamp(receipt["completed_at"])
    method = "GET" if form is None else "POST"
    if (
        source["url"] != url
        or source["observed_at"] != receipt["completed_at"]
        or receipt["raw"]["sha256"] != source["raw"]["sha256"]
        or archive_path(path.parent / receipt["raw"]["path"], archive_root=root)
        != raw_path
        or receipt["status"] != "captured_unparsed"
        or receipt["http_status"] != 200
        or receipt["credentials_sent"] is not False
        or receipt["requests"] != request["max_attempts"]
        or receipt["requests"] != 1
        or receipt["retries"] != 0
        or receipt["byte_count"] != len(body)
        or receipt["headers"]["content-type"].lower() != "text/html; charset=euc-kr"
        or (request["url"], request["method"], request["form"]) != (url, method, form)
        or request["scope"][1:] != [str(lane)]
        or (form is not None and request["scope"][0] != day.strftime("%Y%m%d"))
        or not timestamp(request["reserved_at"])
        <= timestamp(receipt["started_at"])
        <= timestamp(receipt["connector_observed_at"])
        <= observed
    ):
        raise ValueError("workout_edition_response_mismatch")
    if form is not None and (
        _pinned(root, source["reservation"])[0] != reservation_path
        or source["reservation"]["sha256"] != reservation["sha256"]
        or source["http_status"] != 200
        or source["status"] != "captured_unparsed"
        or source["request_count"] != 1
    ):
        raise ValueError("workout_edition_request_reference_mismatch")
    return body.decode("euc-kr", errors="strict"), observed, request


def _menu(root, day, lane, source):
    index, index_at, _ = _source_response(
        root, source["index"], ORIGIN + index_path(lane), lane, None, day=day
    )
    form, count = dated_group_request(index, day, lane=lane)
    stages = source["stages"]
    if set(stages) != {"list", "report"}:
        raise ValueError("workout_edition_missing_stage")
    groups, group_at, _ = _source_response(
        root, stages["list"], ORIGIN + GROUPS, lane, form, day=day
    )
    all_form, group_counts = all_detail_request(
        groups, day, lane=lane, expected_count=count
    )
    detail, observed, request = _source_response(
        root, stages["report"], ORIGIN + DETAIL, lane, all_form, day=day
    )
    list_ref = stages["list"]["receipt"]
    if (
        request["parent"]
        != {"path": Path(list_ref["path"]).name, "sha256": list_ref["sha256"]}
        or source["index"]["validated_next_form"] != form
        or source["index"]["known_count"] != count
        or not index_at < group_at < observed
        or day >= index_at.astimezone(KST).date()
        or source["group_counts"] != {str(k): v for k, v in group_counts.items()}
    ):
        raise ValueError("workout_edition_navigation_or_clock_mismatch")
    weekday, records = read_scoped_workouts(
        detail,
        day,
        observed,
        lane=lane,
        expected_groups=group_counts,
        expected_count=count,
    )
    canonical = [
        asdict(r.workout)
        | {"clock_issue": r.clock_issue, "usable_minutes": r.usable_minutes}
        for r in records
    ]
    if (
        weekday != source["date_weekday"]
        or len(records) != source["horse_id_count"]
        or sum(r.clock_issue is not None for r in records) != source["clock_holds"]
        or encoded(canonical) != encoded(source["rows"])
    ):
        raise ValueError("workout_edition_rows_do_not_replay")
    return records, observed


def verify_source(root: Path, edition_path: Path) -> DailyEdition:
    """Bind the raw observations, parsed identities, and separate public clock."""
    root = root.resolve()
    path, raw = _pinned(root, {"path": edition_path, "sha256": EDITION_SHA256})
    edition = parse_json(raw)
    sources = edition["source_menus"]
    if (
        edition["format"] != EDITION_FORMAT
        or edition["workout_day_kst"] != DAY.isoformat()
        or edition["cutoff_or_race_roster_verified"] is not False
        or edition["feature_or_training_admitted"] is not False
        or edition["predictions_produced"] is not False
        or edition["new_anonymous_http_requests"] != 6
        or edition["retries"] != 0
        or set(sources) != {"1", "2", "3"}
    ):
        raise ValueError("workout_unexpected_source_edition")
    directory = path.with_name("public-note-witness")
    if directory.is_symlink() or any(
        (directory / name).is_symlink() for name in publication.ARCHIVE_FILES
    ):
        raise ValueError("workout_edition_publication_path_conflict")
    document, witness = publication.replay(directory, PULL, DOCUMENT, DOCUMENT_SHA256)
    if document.decode("utf-8").splitlines().count(f"`{EDITION_SHA256}`.") != 1:
        raise ValueError("workout_publication_does_not_bind_edition")
    published = timestamp(witness["merged_at"])
    identities, observations = {}, []
    for lane in (1, 2, 3):
        records, observed = _menu(root, DAY, lane, sources[str(lane)])
        for row in records:
            if row.workout.horse_id in identities:
                raise ValueError("workout_edition_cross_menu_identity_conflict")
            identities[row.workout.horse_id] = (lane, row)
        observations.append(observed)
    observed = max(observations)
    if (
        observed >= published
        or observed != timestamp(edition["last_response_at"])
        or len(identities) != edition["unique_horse_ids"]
    ):
        raise ValueError("workout_edition_witness_or_count_mismatch")
    return DailyEdition(DAY, observed, published, identities)
