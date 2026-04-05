"""
Tests targeting uncovered lines in services/collection_service.py.

Covers: get_collection_status branches, collect_race_data failure paths,
_save_collection_failure branches, _collect_horse_details owner/exception paths,
collect_race_odds edge cases, _save_race_data exception, preprocess_race_data,
and _calculate_recent_form delegation.
"""

from unittest.mock import AsyncMock, Mock

import pandas as pd
import pytest

from models.database_models import DataStatus, Race
from services.collection_service import CollectionService
from services.kra_api_service import KRAAPIService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_kra_mock(**overrides) -> Mock:
    """Build a Mock(spec=KRAAPIService) with AsyncMock defaults."""
    mock = Mock(spec=KRAAPIService)
    mock.get_race_info = AsyncMock()
    mock.get_horse_info = AsyncMock()
    mock.get_jockey_info = AsyncMock()
    mock.get_trainer_info = AsyncMock()
    mock.get_jockey_stats = AsyncMock()
    mock.get_owner_info = AsyncMock()
    mock.get_race_plan = AsyncMock(return_value=None)
    mock.get_track_info = AsyncMock(return_value=None)
    mock.get_cancelled_horses = AsyncMock(return_value=None)
    mock.get_training_status = AsyncMock(return_value=None)
    mock.get_final_odds = AsyncMock()
    mock.get_final_odds_total = AsyncMock()
    for k, v in overrides.items():
        setattr(mock, k, v)
    return mock


def _successful_response(items):
    """Wrap items into a KRA-style successful API response."""
    return {
        "response": {
            "header": {"resultCode": "00"},
            "body": {"items": {"item": items}},
        }
    }


def _failed_response():
    return {"response": {"header": {"resultCode": "99"}}}


def _make_race(
    race_id="20240719_1_1",
    date="20240719",
    meet=1,
    race_number=1,
    collection_status=DataStatus.PENDING,
    enrichment_status=DataStatus.PENDING,
    result_status=DataStatus.PENDING,
    **kwargs,
) -> Race:
    return Race(
        race_id=race_id,
        date=date,
        race_date=date,
        meet=meet,
        race_number=race_number,
        race_no=race_number,
        collection_status=collection_status,
        enrichment_status=enrichment_status,
        result_status=result_status,
        **kwargs,
    )


# =====================================================================
# 1. get_collection_status branches
# =====================================================================


class TestGetCollectionStatusBranches:
    """Cover the overall/collection/enrichment/result status else-branches."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_all_enriched_returns_completed(self, db_session):
        """enriched_races == total_races -> overall_status = 'completed'."""
        race = _make_race(
            collection_status=DataStatus.ENRICHED,
            enrichment_status=DataStatus.ENRICHED,
            result_status=DataStatus.COLLECTED,
        )
        db_session.add(race)
        await db_session.commit()

        status = await CollectionService.get_collection_status(
            db_session, "20240719", 1
        )
        assert status["status"] == "completed"
        assert status["enrichment_status"] == DataStatus.ENRICHED.value
        assert status["result_status"] == DataStatus.COLLECTED.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_all_failed_returns_failed(self, db_session):
        """All races failed collection, none collected -> overall_status = 'failed'."""
        race = _make_race(
            collection_status=DataStatus.FAILED,
            enrichment_status=DataStatus.FAILED,
            result_status=DataStatus.FAILED,
        )
        db_session.add(race)
        await db_session.commit()

        status = await CollectionService.get_collection_status(
            db_session, "20240719", 1
        )
        assert status["status"] == "failed"
        assert status["collection_status"] == DataStatus.FAILED.value
        assert status["enrichment_status"] == DataStatus.FAILED.value
        assert status["result_status"] == DataStatus.FAILED.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_pending_overall_else_branch(self, db_session):
        """No collected, no enriched, not all failed -> overall_status = 'pending'.

        This hits the else branch at lines 111-112.
        To reach it: total_races > 0, enriched != total, failed != total (or collected > 0),
        and collected == 0 and enriched == 0.
        We need: collection_status = PENDING (not collected, not failed_all).
        """
        race = _make_race(
            collection_status=DataStatus.PENDING,
            enrichment_status=DataStatus.PENDING,
            result_status=DataStatus.PENDING,
        )
        db_session.add(race)
        await db_session.commit()

        status = await CollectionService.get_collection_status(
            db_session, "20240719", 1
        )
        assert status["status"] == "pending"
        assert status["collection_status"] == DataStatus.PENDING.value
        assert status["enrichment_status"] == DataStatus.PENDING.value
        assert status["result_status"] == DataStatus.PENDING.value


# =====================================================================
# 2. collect_race_data failure paths
# =====================================================================


class TestCollectRaceDataFailurePaths:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unsuccessful_race_response_saves_failure_and_raises(
        self, db_session
    ):
        """Lines 243-253: race_info is not successful -> save failure + raise ValueError."""
        mock_kra = _make_kra_mock()
        mock_kra.get_race_info.return_value = _failed_response()

        service = CollectionService(mock_kra)
        with pytest.raises(ValueError, match="Race data is unavailable"):
            await service.collect_race_data("20240719", 1, 1, db_session)

        # Verify failure was persisted
        row = await db_session.execute(
            "SELECT collection_status FROM races WHERE race_id = '20240719_1_1'"
        )
        assert row.first()[0] == DataStatus.FAILED.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_training_data_unmatched_horses_warning(self, db_session):
        """Lines 319-325: horses exist in training_map but names don't match."""
        mock_kra = _make_kra_mock()
        # Race info returns one horse
        mock_kra.get_race_info.return_value = _successful_response(
            [{"hrNo": "001", "hrName": "HorseA", "jkNo": "J1", "trNo": "T1"}]
        )
        # Horse/jockey/trainer detail responses
        mock_kra.get_horse_info.return_value = None
        mock_kra.get_jockey_info.return_value = None
        mock_kra.get_trainer_info.return_value = None
        mock_kra.get_jockey_stats.return_value = None
        mock_kra.get_owner_info.return_value = None

        # Training map has a DIFFERENT horse name
        mock_kra.get_training_status.return_value = _successful_response(
            [{"hrnm": "OtherHorse", "someField": "value"}]
        )

        service = CollectionService(mock_kra)
        result = await service.collect_race_data("20240720", 1, 1, db_session)

        # The horse should NOT have training data (unmatched)
        assert "training" not in result["horses"][0]


# =====================================================================
# 3. _save_collection_failure branches
# =====================================================================


class TestSaveCollectionFailure:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_existing_collected_race_just_updates_timestamp(self, db_session):
        """Lines 388-390: race already COLLECTED -> update timestamp only, return."""
        race = _make_race(collection_status=DataStatus.COLLECTED)
        db_session.add(race)
        await db_session.commit()

        mock_kra = _make_kra_mock()
        service = CollectionService(mock_kra)
        await service._save_collection_failure(
            "20240719", 1, 1, None, db_session, "some failure"
        )

        row = await db_session.execute(
            "SELECT collection_status FROM races WHERE race_id = '20240719_1_1'"
        )
        # Should still be COLLECTED, not overwritten to FAILED
        assert row.first()[0] == DataStatus.COLLECTED.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_existing_enriched_race_just_updates_timestamp(self, db_session):
        """Lines 388-390: race already ENRICHED -> update timestamp only, return."""
        race = _make_race(collection_status=DataStatus.ENRICHED)
        db_session.add(race)
        await db_session.commit()

        mock_kra = _make_kra_mock()
        service = CollectionService(mock_kra)
        await service._save_collection_failure(
            "20240719", 1, 1, None, db_session, "some failure"
        )

        row = await db_session.execute(
            "SELECT collection_status FROM races WHERE race_id = '20240719_1_1'"
        )
        assert row.first()[0] == DataStatus.ENRICHED.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_existing_pending_race_updates_to_failed(self, db_session):
        """Lines 399-401: existing race not COLLECTED/ENRICHED -> overwrite raw_data + FAILED."""
        race = _make_race(collection_status=DataStatus.PENDING)
        db_session.add(race)
        await db_session.commit()

        mock_kra = _make_kra_mock()
        service = CollectionService(mock_kra)
        await service._save_collection_failure(
            "20240719", 1, 1, {"some": "info"}, db_session, "api broke"
        )

        row = await db_session.execute(
            "SELECT collection_status FROM races WHERE race_id = '20240719_1_1'"
        )
        assert row.first()[0] == DataStatus.FAILED.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_exception_during_save_rolls_back(self, db_session):
        """Lines 418-427: exception in _save_collection_failure -> rollback + raise."""
        mock_kra = _make_kra_mock()
        service = CollectionService(mock_kra)

        # Force db.commit to raise by patching the inner session
        original_commit = db_session._inner.commit

        async def _boom():
            raise RuntimeError("db exploded")

        db_session._inner.commit = _boom

        with pytest.raises(RuntimeError, match="db exploded"):
            await service._save_collection_failure(
                "20240719", 1, 99, None, db_session, "reason"
            )

        # Restore so teardown doesn't break
        db_session._inner.commit = original_commit


# =====================================================================
# 4. _collect_horse_details: owner info + outer exception
# =====================================================================


class TestCollectHorseDetails:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_owner_info_collected_via_ow_no(self):
        """Lines 512-523: owner_no present in horse_basic -> fetch owDetail."""
        mock_kra = _make_kra_mock()
        mock_kra.get_horse_info.return_value = None
        mock_kra.get_jockey_info.return_value = None
        mock_kra.get_trainer_info.return_value = None
        mock_kra.get_jockey_stats.return_value = None
        mock_kra.get_owner_info.return_value = _successful_response(
            [{"owNo": "OW1", "owName": "Owner One"}]
        )

        service = CollectionService(mock_kra)
        result = await service._collect_horse_details(
            {"hr_no": "001", "ow_no": "OW1"}, meet=1
        )

        assert "owDetail" in result
        assert result["owDetail"]["ow_name"] == "Owner One"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_owner_info_collected_via_hr_detail(self):
        """Lines 509-510: owner_no from hrDetail when not in horse_basic."""
        mock_kra = _make_kra_mock()
        mock_kra.get_horse_info.return_value = _successful_response(
            [{"hrNo": "001", "owNo": "OW2"}]
        )
        mock_kra.get_jockey_info.return_value = None
        mock_kra.get_trainer_info.return_value = None
        mock_kra.get_jockey_stats.return_value = None
        mock_kra.get_owner_info.return_value = _successful_response(
            [{"owNo": "OW2", "owName": "Owner Two"}]
        )

        service = CollectionService(mock_kra)
        result = await service._collect_horse_details({"hr_no": "001"}, meet=1)

        assert "owDetail" in result
        mock_kra.get_owner_info.assert_called_once_with("OW2", meet="1")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_owner_info_exception_is_swallowed(self):
        """Lines 524-527: exception during owner info fetch -> logged, not raised."""
        mock_kra = _make_kra_mock()
        mock_kra.get_horse_info.return_value = None
        mock_kra.get_jockey_info.return_value = None
        mock_kra.get_trainer_info.return_value = None
        mock_kra.get_jockey_stats.return_value = None
        mock_kra.get_owner_info.side_effect = RuntimeError("owner api down")

        service = CollectionService(mock_kra)
        result = await service._collect_horse_details(
            {"hr_no": "001", "ow_no": "OW1"}, meet=1
        )

        # Should succeed without owDetail
        assert "owDetail" not in result

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_outer_exception_propagates(self):
        """Lines 531-537: exception in main try block -> logged and re-raised."""
        mock_kra = _make_kra_mock()
        mock_kra.get_horse_info.side_effect = RuntimeError("total failure")

        service = CollectionService(mock_kra)
        with pytest.raises(RuntimeError, match="total failure"):
            await service._collect_horse_details({"hr_no": "001"}, meet=1)


# =====================================================================
# 5. collect_race_odds edge cases
# =====================================================================


class TestCollectRaceOdds:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_source_returns_error(self, db_session):
        """Lines 554-558: source not in valid_sources -> return error dict."""
        mock_kra = _make_kra_mock()
        service = CollectionService(mock_kra)

        result = await service.collect_race_odds(
            "20240719", 1, 1, db_session, source="BAD_SOURCE"
        )
        assert result["error"].startswith("Invalid source")
        assert result["inserted_count"] == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_api301_source_calls_get_final_odds_total(self, db_session):
        """Lines 566-569: source == 'API301' -> calls get_final_odds_total."""
        mock_kra = _make_kra_mock()
        mock_kra.get_final_odds_total.return_value = _failed_response()

        service = CollectionService(mock_kra)
        result = await service.collect_race_odds(
            "20240719", 1, 1, db_session, source="API301"
        )

        mock_kra.get_final_odds_total.assert_called_once()
        mock_kra.get_final_odds.assert_not_called()
        assert result["error"] == "API response failed"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_invalid_pool_skipped(self, db_session):
        """Line 585: pool not in VALID_POOLS -> continue (skip row)."""
        mock_kra = _make_kra_mock()
        mock_kra.get_final_odds.return_value = _successful_response(
            [{"pool": "UNKNOWN_POOL", "chulNo": 1, "odds": 5.0}]
        )

        service = CollectionService(mock_kra)
        result = await service.collect_race_odds("20240719", 1, 1, db_session)

        assert result["inserted_count"] == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_upsert_exception_rolls_back(self, db_session):
        """Lines 608-613: exception during pg_insert -> rollback + return error."""
        mock_kra = _make_kra_mock()
        mock_kra.get_final_odds.return_value = _successful_response(
            [{"pool": "WIN", "chulNo": 1, "odds": 5.0}]
        )

        service = CollectionService(mock_kra)

        # Force db.execute to raise when the upsert statement is executed
        original_execute = db_session._inner.execute

        call_count = 0

        async def _failing_execute(stmt, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            # The first execute in collect_race_odds is the pg_insert
            # Let it fail to trigger the exception handler
            if call_count == 1:
                raise RuntimeError("upsert failed")
            return await original_execute(stmt, *args, **kwargs)

        db_session._inner.execute = _failing_execute

        result = await service.collect_race_odds("20240719", 1, 1, db_session)

        assert result["error"] == "upsert failed"
        assert result["inserted_count"] == 0

        db_session._inner.execute = original_execute


# =====================================================================
# 6. _save_race_data exception path
# =====================================================================


class TestSaveRaceDataException:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_save_race_data_exception_rolls_back(self, db_session):
        """Lines 663-666: exception in _save_race_data -> rollback + raise."""
        mock_kra = _make_kra_mock()
        service = CollectionService(mock_kra)

        original_commit = db_session._inner.commit

        async def _boom():
            raise RuntimeError("disk full")

        db_session._inner.commit = _boom

        data = {"date": "20240719", "meet": 1, "race_number": 1}
        with pytest.raises(RuntimeError, match="disk full"):
            await service._save_race_data(data, db_session)

        db_session._inner.commit = original_commit


# =====================================================================
# 7. preprocess_race_data
# =====================================================================


class TestPreprocessRaceData:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_preprocess_loads_race_and_saves_enriched(self, db_session):
        """Lines 681-707: full preprocess flow."""
        race = _make_race(
            collection_status=DataStatus.COLLECTED,
            basic_data={
                "horses": [
                    {"hrNo": "001", "win_odds": "5.5", "weight": "500", "rating": "85"},
                ]
            },
        )
        db_session.add(race)
        await db_session.commit()

        mock_kra = _make_kra_mock()
        service = CollectionService(mock_kra)
        result = await service.preprocess_race_data("20240719_1_1", db_session)

        assert result is not None
        assert "horses" in result

        # Verify the race was updated
        row = await db_session.execute(
            "SELECT enrichment_status FROM races WHERE race_id = '20240719_1_1'"
        )
        assert row.first()[0] == DataStatus.ENRICHED.value

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_preprocess_race_not_found_raises(self, db_session):
        """Line 687: race not found -> raise ValueError."""
        mock_kra = _make_kra_mock()
        service = CollectionService(mock_kra)

        with pytest.raises(ValueError, match="Race not found"):
            await service.preprocess_race_data("nonexistent_id", db_session)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_preprocess_exception_rolls_back(self, db_session):
        """Lines 704-707: exception during preprocessing -> rollback + raise."""
        race = _make_race(
            collection_status=DataStatus.COLLECTED,
            basic_data=None,  # will cause preprocess to fail
        )
        db_session.add(race)
        await db_session.commit()

        mock_kra = _make_kra_mock()
        service = CollectionService(mock_kra)

        with pytest.raises((TypeError, AttributeError)):
            await service.preprocess_race_data("20240719_1_1", db_session)


# =====================================================================
# 8. _calculate_recent_form delegation
# =====================================================================


class TestCalculateRecentForm:
    @pytest.mark.unit
    def test_delegates_to_helper(self):
        """Line 786: delegates to calculate_recent_form_helper."""
        mock_kra = _make_kra_mock()
        service = CollectionService(mock_kra)

        df = pd.DataFrame(
            {"position": [1, 3, 2], "date": ["20240701", "20240708", "20240715"]}
        )
        result = service._calculate_recent_form(df)
        assert isinstance(result, (int, float))

    @pytest.mark.unit
    def test_empty_dataframe_returns_zero(self):
        """Empty df -> 0."""
        mock_kra = _make_kra_mock()
        service = CollectionService(mock_kra)

        result = service._calculate_recent_form(pd.DataFrame())
        assert result == 0
