"""Exercise the source clocks and full declaration scopes with synthetic archives."""

from dataclasses import asdict, replace
from datetime import UTC, date, datetime, timedelta

import httpx
import pytest

from autoresearch import (
    kra_daily_workout_card_audit as audit,
)
from autoresearch import (
    kra_daily_workout_edition as edition,
)
from autoresearch import (
    local_m0_inference,
    prerace_hash_witness,
)
from autoresearch.kra_daily_workout_navigation import (
    all_detail_request,
    dated_group_request,
)
from autoresearch.kra_daily_workout_source import (
    DETAIL,
    GROUPS,
    Workout,
    WorkoutEvidence,
    index_path,
    read_scoped_workouts,
)
from autoresearch.observed_history_seed import pin, save
from autoresearch.restricted_cohort import horse_id, sha256
from autoresearch.tests.condition_forward_fixture import archive_publication
from autoresearch.tests.test_kra_daily_workout_navigation import _groups, _index
from autoresearch.tests.test_kra_daily_workout_source import _detail, _session
from autoresearch.tests.test_kra_entry_scope_intake import (
    DUE,
    answer,
    make_intake_inputs,
    model_rows,
    run,
)
from autoresearch.tests.test_kra_entry_scope_witness import AFTER, PULL, ProviderClock
from autoresearch.tests.test_kra_schedule import DATE, NOW

START = NOW + timedelta(hours=2)
FIRST_RESPONSE = datetime(2026, 11, 22, 19, tzinfo=UTC)
SOURCE_MERGE = FIRST_RESPONSE + timedelta(minutes=5)


class LaterClock(datetime):
    @classmethod
    def now(cls, tz=None):
        later = SOURCE_MERGE + timedelta(days=1)
        return later.astimezone(tz) if tz is not None else later.replace(tzinfo=None)


def _stage(root, folder, stage, url, html, at, lane, *, form=None, parent=None):
    body = html.encode("euc-kr")
    raw = folder / f"{stage}.html"
    raw.write_bytes(body)
    request = folder / f"{stage}-reservation.json"
    save(
        request,
        {
            "method": "GET" if form is None else "POST",
            "url": url,
            "form": form,
            "scope": ["20261122", str(lane)],
            "max_attempts": 1,
            "parent": parent,
            "reserved_at": (at - timedelta(seconds=1)).isoformat(),
        },
    )
    receipt = folder / f"{stage}-receipt.json"
    save(
        receipt,
        {
            "reservation": pin(folder, request),
            "raw": pin(folder, raw),
            "completed_at": at.isoformat(),
            "connector_observed_at": at.isoformat(),
            "started_at": (at - timedelta(milliseconds=300)).isoformat(),
            "credentials_sent": False,
            "requests": 1,
            "retries": 0,
            "byte_count": len(body),
            "status": "captured_unparsed",
            "http_status": 200,
            "headers": {"content-type": "text/html; charset=EUC-KR"},
        },
    )
    return {
        "receipt": pin(root, receipt),
        "raw": pin(root, raw),
        "reservation": pin(root, request),
        "url": url,
        "status": "captured_unparsed",
        "http_status": 200,
        "request_count": 1,
        "observed_at": at.isoformat(),
    }


@pytest.fixture
def edition_arc(tmp_path, monkeypatch):
    monkeypatch.setattr(edition.publication, "datetime", LaterClock)
    monkeypatch.setattr(prerace_hash_witness, "datetime", LaterClock)

    def prepare(*, merge=SOURCE_MERGE, alter=None, bind=True):
        sources = {}
        for lane in (1, 2, 3):
            folder = tmp_path / f"menu-{lane}"
            folder.mkdir()
            index, group = _index(lane), _groups(lane)
            detail = (
                _detail(
                    lane,
                    *[
                        _session(
                            lane,
                            i,
                            str(lane * 100 + i),
                            minutes="8" if lane == 3 and i == 1 else "9",
                        )
                        for i in range(1, 6)
                    ],
                )
                .replace("2026/11/18", "2026/11/22")
                .replace("2\uc870", "1\uc870")
            )
            detail = (
                detail.replace('name="Act" value="10"', 'name="Act" value="09"')
                if lane == 1
                else detail
            )
            at = FIRST_RESPONSE + timedelta(seconds=10 * lane)
            requested_day, count = dated_group_request(index, edition.DAY, lane=lane)
            request_all, counts = all_detail_request(
                group, edition.DAY, lane=lane, expected_count=count
            )
            index_record = _stage(
                tmp_path,
                folder,
                "index",
                edition.ORIGIN + index_path(lane),
                index,
                at,
                lane,
            )
            list_record = _stage(
                tmp_path,
                folder,
                "list",
                edition.ORIGIN + GROUPS,
                group,
                at + timedelta(seconds=3),
                lane,
                form=requested_day,
            )
            last = at + timedelta(seconds=6)
            report = _stage(
                tmp_path,
                folder,
                "report",
                edition.ORIGIN + DETAIL,
                detail,
                last,
                lane,
                form=request_all,
                parent=pin(folder, folder / "list-receipt.json"),
            )
            week, rows = read_scoped_workouts(
                detail,
                edition.DAY,
                last,
                lane=lane,
                expected_groups=counts,
                expected_count=count,
            )
            sources[str(lane)] = {
                "index": index_record
                | {"known_count": count, "validated_next_form": requested_day},
                "stages": {"list": list_record, "report": report},
                "group_counts": counts,
                "date_weekday": week,
                "horse_id_count": len(rows),
                "clock_holds": sum(r.clock_issue is not None for r in rows),
                "rows": [
                    asdict(r.workout)
                    | {"clock_issue": r.clock_issue, "usable_minutes": r.usable_minutes}
                    for r in rows
                ],
            }
        packet = {
            "format": edition.EDITION_FORMAT,
            "workout_day_kst": edition.DAY.isoformat(),
            "source_menus": sources,
            "cutoff_or_race_roster_verified": False,
            "feature_or_training_admitted": False,
            "predictions_produced": False,
            "new_anonymous_http_requests": 6,
            "retries": 0,
            "last_response_at": last.isoformat(),
            "unique_horse_ids": 15,
        }
        if alter is not None:
            alter(packet)
        path = tmp_path / "source-edition.json"
        sha = save(path, packet)
        note = f"\n`{sha}`.\n".encode() if bind else b"Not an edition digest.\n"
        monkeypatch.setattr(edition, "EDITION_SHA256", sha)
        monkeypatch.setattr(edition, "DOCUMENT_SHA256", sha256(note))
        archive_publication(
            tmp_path / "public-note-witness",
            note,
            edition.PULL,
            edition.DOCUMENT,
            merge,
            SOURCE_MERGE + timedelta(minutes=1),
        )
        return path

    return prepare


def test_source_replays_raw_canonical_rows_and_independent_clock(edition_arc, tmp_path):
    path = edition_arc()
    source = edition.verify_source(tmp_path, path)
    assert len(source.identities) == 15 and source.published == SOURCE_MERGE
    assert source.observed == FIRST_RESPONSE + timedelta(seconds=36)
    lane, row = source.identities["301"]
    assert lane == 3 and row.usable_minutes is None
    assert row.workout.minutes == 8


def test_source_link_requires_actual_body_and_not_replaced_snapshot(
    edition_arc, tmp_path
):
    path = edition_arc()
    (tmp_path / "menu-2" / "report.html").write_bytes(b"different report")
    with pytest.raises(ValueError, match="source_pin_mismatch"):
        edition.verify_source(tmp_path, path)


def test_witnessing_a_changed_projection_cannot_override_the_raw_rows(
    edition_arc, tmp_path
):
    path = edition_arc(
        alter=lambda p: p["source_menus"]["3"]["rows"][0].update(usable_minutes=8)
    )
    with pytest.raises(ValueError, match="workout_edition_rows_do_not_replay"):
        edition.verify_source(tmp_path, path)


def test_source_witness_must_bind_the_edition_not_just_a_nearby_note(
    edition_arc, tmp_path
):
    path = edition_arc(bind=False)
    with pytest.raises(ValueError, match="publication_does_not_bind"):
        edition.verify_source(tmp_path, path)


def test_source_observation_cannot_follow_its_public_clock(edition_arc, tmp_path):
    path = edition_arc(merge=FIRST_RESPONSE + timedelta(seconds=32))
    with pytest.raises(ValueError, match="workout_edition_witness_or_count_mismatch"):
        edition.verify_source(tmp_path, path)


@pytest.fixture
def card_archive(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, "now", lambda: START)
    monkeypatch.setattr(audit.card_witness, "now", lambda: START)
    monkeypatch.setattr(audit.card_witness.publication, "datetime", ProviderClock)
    monkeypatch.setattr(prerace_hash_witness, "datetime", ProviderClock)

    def make(*, merge=NOW + timedelta(hours=1)):
        def gateway(request):
            meet = int(request.url.params["meet"])
            rows = [
                r | {"rank": "\uad6d5\ub4f1\uae09", "rcDist": 1200}
                for r in model_rows(meet)
            ]
            if meet == 4:
                rows[0]["rcDist"] = None
            return answer(rows, int(request.url.params["pageNo"]))

        inputs = make_intake_inputs(tmp_path)
        (at, receipt), calls = run(inputs, provide=gateway)
        assert receipt["status"] == "captured_locally" and len(calls) == 4
        ref = pin(tmp_path, at)
        original = {
            "schedule_sha256": inputs[1]["sha256"],
            "first_cutoff": DUE.isoformat(),
        }
        marker = audit.card_witness.stage(tmp_path, ref, **original, clock=lambda: NOW)
        digest = pin(tmp_path, at.with_name(audit.card_witness.PACKET_NAME))["sha256"]
        archive_publication(
            at.with_name(audit.card_witness.ARCHIVE_NAME),
            marker,
            PULL,
            audit.card_witness.publication_document(digest),
            merge,
            AFTER,
        )
        ids = {}
        for meet, lane in audit.RACE_VENUE_TO_MENU.items():
            for r in model_rows(meet):
                gate, hid = int(r["chulNo"]), horse_id(r["hrNo"])
                if meet == 1 and gate == 1:
                    continue
                obs = Workout(
                    gate, 1, gate, hid, r["hrName"], 360, 370, 10, None, (None, None)
                )
                if meet == 2 and gate == 10:
                    obs = replace(obs, minutes=11, end_minute=371)
                if meet == 1 and gate == 2:
                    actual_lane = 2
                else:
                    actual_lane = lane
                if meet == 1 and gate == 3:
                    obs = replace(obs, horse_name="Other name")
                flag = "clock conflict" if meet == 1 and gate == 4 else None
                ids[hid] = (actual_lane, WorkoutEvidence(obs, flag))
        source = edition.DailyEdition(
            date(2026, 10, 13),
            NOW - timedelta(hours=1),
            NOW - timedelta(minutes=30),
            ids,
        )
        monkeypatch.setattr(audit, "verify_source", lambda *_: source)
        return (
            (tmp_path, tmp_path / "not_read_source.json", ref),
            {**original, "packet_sha256": digest, "pull": PULL},
            source,
        )

    return make


def test_both_timed_inputs_account_for_all_four_venues_without_writing(
    card_archive, monkeypatch
):
    args, kwargs, _ = card_archive()

    def forbidden(*_args, **_kwargs):
        pytest.fail("a source diagnostic cannot collect or predict")

    monkeypatch.setattr(httpx, "Client", forbidden)
    monkeypatch.setattr(httpx, "AsyncClient", forbidden)
    monkeypatch.setattr(local_m0_inference, "score_capture", forbidden)
    before = {p: p.read_bytes() for p in args[0].rglob("*") if p.is_file()}
    report = audit.audit(*args, **kwargs)
    assert report == audit.audit(*args, **kwargs)
    assert {p: p.read_bytes() for p in args[0].rglob("*") if p.is_file()} == before
    assert (report["race_count"], report["declaration_count"]) == (4, 40)
    assert {r["race_id"] for r in report["races"]} == {
        f"{DATE}_{meet}_1" for meet in range(1, 5)
    }
    assert report["declaration_state_counts"] == {
        audit.LINKED: 36,
        "not_in_observed_edition": 1,
        "different_source_menu_held": 1,
        "same_id_name_conflict_held": 1,
        "source_clock_conflict_held": 1,
    }
    assert report["complete_coverage_races"] == 3
    assert report["complete_varying_coverage_races"] == 1
    assert (
        report["coverage_by_original_context"]["distance_m"]["unknown"]["declarations"]
        == 10
    )
    assert report["races"][-1]["physical_meet"] == 4
    assert report["races"][-1]["expected_source_menu_lane"] == 3
    assert "minutes" not in report["races"][0]["declarations"][4]
    assert report["training_or_prediction_allowed"] is False


def test_source_at_deadline_and_future_to_this_run_are_distinct_from_usable(
    card_archive,
):
    _, _, source = card_archive()
    with pytest.raises(ValueError, match="not_witnessed_before_original_cutoff"):
        audit.require_source_before_cutoff(source, source.published, source.published)
    with pytest.raises(ValueError, match="not_witnessed_before_original_cutoff"):
        audit.require_source_before_cutoff(source, DUE, source.observed)


def test_entry_card_published_at_deadline_cannot_join(card_archive):
    args, kwargs, _ = card_archive(merge=DUE)
    with pytest.raises(ValueError, match="entry_packet_not_witnessed"):
        audit.audit(*args, **kwargs)


def test_missed_local_deadline_does_not_reduce_the_population(
    card_archive, monkeypatch
):
    args, kwargs, _ = card_archive()
    ticks = iter((START, DUE))
    monkeypatch.setattr(audit, "now", lambda: next(ticks))
    with pytest.raises(ValueError, match="original_cutoff_elapsed"):
        audit.audit(*args, **kwargs)


def test_changed_original_scope_is_rejected(card_archive):
    args, kwargs, _ = card_archive()
    with pytest.raises(ValueError, match="cutoff"):
        audit.audit(
            *args,
            **(kwargs | {"first_cutoff": (DUE + timedelta(minutes=1)).isoformat()}),
        )


def test_lost_race_or_declared_horse_is_never_optional(card_archive, monkeypatch):
    args, kwargs, _ = card_archive()
    real = audit._final_projections

    def incomplete(*inner):
        fields = real(*inner)
        fields.pop(f"{DATE}_4_1")
        return fields

    monkeypatch.setattr(audit, "_final_projections", incomplete)
    with pytest.raises(ValueError, match="population_scope_conflict"):
        audit.audit(*args, **kwargs)

    def short(*inner):
        fields = real(*inner)
        fields[f"{DATE}_4_1"]["roster"].pop()
        return fields

    monkeypatch.setattr(audit, "_final_projections", short)
    with pytest.raises(ValueError, match="roster_length_conflict"):
        audit.audit(*args, **kwargs)


def test_workout_edition_cannot_be_same_day_or_later_than_the_card(
    card_archive, monkeypatch
):
    args, kwargs, source = card_archive()
    same_day = datetime.strptime(DATE, "%Y%m%d").date()
    monkeypatch.setattr(
        audit, "verify_source", lambda *_: replace(source, day=same_day)
    )
    with pytest.raises(ValueError, match="not_earlier_than_event"):
        audit.audit(*args, **kwargs)


def test_canonical_horse_collision_does_not_turn_into_another_missing_row(
    card_archive, monkeypatch
):
    args, kwargs, _ = card_archive()
    real = audit._final_projections

    def duplicate(*inner):
        fields = real(*inner)
        roster = fields[f"{DATE}_1_1"]["roster"]
        roster[2]["hrNo"] = "0" + str(roster[1]["hrNo"])
        return fields

    monkeypatch.setattr(audit, "_final_projections", duplicate)
    with pytest.raises(ValueError, match="roster_identity_conflict"):
        audit.audit(*args, **kwargs)
