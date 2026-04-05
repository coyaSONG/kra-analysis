"""Tests targeting remaining uncovered lines across multiple modules."""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from pydantic import ValidationError

from adapters.kra_response_adapter import KRAResponseAdapter
from adapters.race_projection_adapter import RaceProjectionAdapter
from infrastructure.kra_api.core import (
    KRAApiRequestError,
    KRARequestPolicy,
    _retry_delay,
    request_json_with_retry,
)
from middleware.logging import get_request_count
from models.collection_dto import EnrichmentRequest
from models.database_models import APIKey, DataStatus, Race
from services.collection_preprocessing import preprocess_data


# ---------------------------------------------------------------------------
# 1. adapters/kra_response_adapter.py  lines 59-69
# ---------------------------------------------------------------------------
class TestKRAResponseAdapterExtractItemsException:
    def test_extract_items_type_error_body_is_int(self):
        # body is truthy int → `"items" not in 42` raises TypeError
        result = KRAResponseAdapter.extract_items({"response": {"body": 42}})
        assert result == []

    def test_extract_items_type_error_response_is_int(self):
        # response value is int → `"body" not in 5` raises TypeError
        result = KRAResponseAdapter.extract_items({"response": 5})
        assert result == []


# ---------------------------------------------------------------------------
# 2. adapters/race_projection_adapter.py  lines 132, 150
# ---------------------------------------------------------------------------
class TestRaceProjectionAdapterGaps:
    def test_normalize_horses_assigns_index_for_falsy_ord(self):
        horses = [
            {"chulNo": 5, "ord": 0},
            {"chulNo": 3, "ord": 2},
        ]
        result = RaceProjectionAdapter._normalize_horses(horses)
        horse5 = next(h for h in result if h["chulNo"] == 5)
        assert horse5["ord"] == 1  # gets index 1 as fallback

    def test_extract_top3_from_horses_chulNo_positive_ord_zero(self):
        # Line 150: horse where chulNo > 0 but ord == 0 → elif branch
        horses = [
            {"chulNo": 7, "ord": 0},  # triggers elif on line 149
        ]
        result = RaceProjectionAdapter._extract_top3_from_horses(None, horses)
        assert result == [7]


# ---------------------------------------------------------------------------
# 3. dependencies/auth.py  lines 100-102, 269, 277, 376-379, 385-391
# ---------------------------------------------------------------------------
class TestAuthVerifyApiKeySQLAlchemyError:
    @pytest.mark.asyncio
    async def test_verify_api_key_sqlalchemy_error(self, db_session):
        from sqlalchemy.exc import SQLAlchemyError

        from dependencies.auth import APIKeyBackendError, verify_api_key

        with patch.object(
            db_session, "execute", side_effect=SQLAlchemyError("db down")
        ):
            with pytest.raises(APIKeyBackendError):
                await verify_api_key("some-valid-key-format", db_session)


class TestAuthAdminWritePermissions:
    @pytest.mark.asyncio
    async def test_require_admin_permissions(self):
        from dependencies.auth import _require_admin_permissions
        from policy.principal import AuthenticatedPrincipal

        api_key_obj = APIKey(
            key="admin-key-123456",
            name="Admin",
            is_active=True,
            permissions=["admin", "read", "write"],
        )
        mock_db = AsyncMock()
        result = await _require_admin_permissions(api_key_obj=api_key_obj, db=mock_db)
        assert isinstance(result, AuthenticatedPrincipal)
        assert result.credential_id == "admin-key-123456"

    @pytest.mark.asyncio
    async def test_require_admin_permissions_denied(self):
        from fastapi import HTTPException

        from dependencies.auth import _require_admin_permissions

        api_key_obj = APIKey(
            key="readonly-key-1234",
            name="ReadOnly",
            is_active=True,
            permissions=["read"],
        )
        mock_db = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await _require_admin_permissions(api_key_obj=api_key_obj, db=mock_db)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_write_permissions(self):
        from dependencies.auth import _require_write_permissions
        from policy.principal import AuthenticatedPrincipal

        api_key_obj = APIKey(
            key="write-key-12345678",
            name="Writer",
            is_active=True,
            permissions=["read", "write"],
        )
        mock_db = AsyncMock()
        result = await _require_write_permissions(api_key_obj=api_key_obj, db=mock_db)
        assert isinstance(result, AuthenticatedPrincipal)
        assert result.credential_id == "write-key-12345678"


class TestRequireResourceAccess:
    @pytest.mark.asyncio
    async def test_resource_id_missing_from_path(self):
        from fastapi import HTTPException

        from dependencies.auth import require_resource_access

        dep_fn = require_resource_access("job", "job_id")
        mock_request = Mock()
        mock_request.path_params = {}
        mock_api_key = APIKey(
            key="key-for-resource-test",
            name="Test",
            is_active=True,
            permissions=["read"],
        )
        mock_db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await dep_fn(request=mock_request, api_key_obj=mock_api_key, db=mock_db)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_resource_access_denied(self):
        from fastapi import HTTPException

        from dependencies.auth import require_resource_access

        dep_fn = require_resource_access("job", "job_id")
        mock_request = Mock()
        mock_request.path_params = {"job_id": "some-job-id"}
        mock_api_key = APIKey(
            key="key-for-resource-test",
            name="Test",
            is_active=True,
            permissions=["read"],
        )
        mock_db = AsyncMock()

        with patch(
            "dependencies.auth.check_resource_access",
            new_callable=AsyncMock,
            return_value=False,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await dep_fn(request=mock_request, api_key_obj=mock_api_key, db=mock_db)
            assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_resource_access_granted(self):
        from dependencies.auth import require_resource_access
        from policy.principal import AuthenticatedPrincipal

        dep_fn = require_resource_access("job", "job_id")
        mock_request = Mock()
        mock_request.path_params = {"job_id": "some-job-id"}
        mock_api_key = APIKey(
            key="key-for-resource-test",
            name="Test",
            is_active=True,
            permissions=["admin"],
        )
        mock_db = AsyncMock()

        with patch(
            "dependencies.auth.check_resource_access",
            new_callable=AsyncMock,
            return_value=True,
        ):
            result = await dep_fn(
                request=mock_request, api_key_obj=mock_api_key, db=mock_db
            )
        assert isinstance(result, AuthenticatedPrincipal)
        assert result.credential_id == "key-for-resource-test"


# ---------------------------------------------------------------------------
# 4. infrastructure/kra_api/core.py  lines 127, 211
# ---------------------------------------------------------------------------
class TestKRAApiCoreGaps:
    def test_retry_delay_naive_datetime_retry_after(self):
        # Line 127: Retry-After is an HTTP-date WITHOUT timezone → naive datetime
        # "Sat, 22 Mar 2026 12:00:00" has no timezone suffix
        mock_response = Mock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "Sat, 22 Mar 2026 12:00:00"}

        delay = _retry_delay(0, response=mock_response)
        # Should be a non-negative float (the naive dt gets UTC assigned)
        assert isinstance(delay, float)
        assert delay >= 0.0

    @pytest.mark.asyncio
    async def test_request_json_with_retry_zero_retries(self):
        # Line 211 (229): max_retries=0 → loop body never executes,
        # falls through to "All retries exhausted"
        policy = KRARequestPolicy(
            base_url="http://example.com",
            api_key=None,
            timeout=5,
            max_retries=0,
            verify_ssl=False,
        )
        mock_client = AsyncMock(spec=httpx.AsyncClient)

        with pytest.raises(KRAApiRequestError, match="All retries exhausted"):
            await request_json_with_retry(
                mock_client, policy, "/test", params={"a": "1"}
            )

        # client.request should never have been called
        mock_client.request.assert_not_called()

    @pytest.mark.asyncio
    async def test_request_json_5xx_exhausts_retries(self):
        # Lines 211-213: HTTP 500 after all retries → KRAApiRetryableRequestError
        from infrastructure.kra_api.core import KRAApiRetryableRequestError

        policy = KRARequestPolicy(
            base_url="http://example.com",
            api_key=None,
            timeout=5,
            max_retries=1,
            verify_ssl=False,
        )

        mock_response = httpx.Response(
            status_code=500,
            request=httpx.Request("GET", "http://example.com/test"),
            text="Internal Server Error",
        )
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.request.side_effect = httpx.HTTPStatusError(
            "Server Error", request=mock_response.request, response=mock_response
        )

        with pytest.raises(KRAApiRetryableRequestError, match="HTTP 500"):
            await request_json_with_retry(mock_client, policy, "/test")


# ---------------------------------------------------------------------------
# 5. middleware/logging.py  line 62, 161-162
# ---------------------------------------------------------------------------
class TestLoggingMiddlewareGaps:
    def test_get_request_count(self):
        count = get_request_count()
        assert isinstance(count, int)

    @pytest.mark.asyncio
    async def test_non_json_body_logging(self, client):
        # Send a POST with non-JSON body to trigger lines 161-162
        response = await client.post(
            "/health",
            content=b"this is not json",
            headers={
                "Content-Type": "text/plain",
                "X-API-Key": "test-api-key-123",
            },
        )
        # We don't care about the response status; just that the middleware
        # path for non-JSON body logging was exercised.
        assert response.status_code in (200, 405, 404, 422)


# ---------------------------------------------------------------------------
# 6. middleware/rate_limit.py  lines 98-100
# ---------------------------------------------------------------------------
class TestRateLimitRedisFailure:
    @pytest.mark.asyncio
    async def test_check_rate_limit_redis_exception_returns_true(self):
        from middleware.rate_limit import RateLimitMiddleware

        middleware = RateLimitMiddleware(app=Mock(), calls=10, period=60)

        mock_redis = Mock()
        mock_redis.pipeline.side_effect = RuntimeError("redis down")

        result = await middleware._check_rate_limit_redis("test-client", mock_redis)
        assert result is True


# ---------------------------------------------------------------------------
# 7. models/collection_dto.py  line 96
# ---------------------------------------------------------------------------
class TestCollectionDtoEnrichmentValidation:
    def test_validate_enrich_types_valid_returns(self):
        # Line 96: the `return v` after the for-loop completes without error
        req = EnrichmentRequest(
            race_ids=["race_1"],
            enrich_types=["horse", "jockey", "trainer"],
        )
        assert req.enrich_types == ["horse", "jockey", "trainer"]

    def test_validate_enrich_types_invalid_raises(self):
        with pytest.raises(ValidationError):
            EnrichmentRequest(
                race_ids=["race_1"],
                enrich_types=["horse", "invalid_type"],
            )


# ---------------------------------------------------------------------------
# 8. models/database_models.py  lines 120-122, 200
# ---------------------------------------------------------------------------
class TestDatabaseModelsGaps:
    def test_data_status_missing_uppercase_name(self):
        # Line 120-122: _missing_ tries lowercase value first (fails),
        # then uppercase name (succeeds)
        result = DataStatus("COLLECTED")
        assert result == DataStatus.COLLECTED

    def test_data_status_missing_unknown_returns_none(self):
        result = DataStatus._missing_("nonexistent_value")
        assert result is None

    def test_data_status_missing_non_string(self):
        result = DataStatus._missing_(12345)
        assert result is None

    def test_race_race_date_property(self):
        race = Race(
            race_id="test_prop",
            date="20240101",
            meet=1,
            race_number=1,
        )
        assert race.race_date == "20240101"


# ---------------------------------------------------------------------------
# 9. pipelines/data_pipeline.py  lines 236-244
# ---------------------------------------------------------------------------
class TestPipelineOrchestratorBaseException:
    @pytest.mark.asyncio
    async def test_process_race_batch_handles_base_exception(self):
        from pipelines.data_pipeline import PipelineOrchestrator

        mock_kra = AsyncMock()
        mock_db = AsyncMock()
        orchestrator = PipelineOrchestrator(mock_kra, mock_db)

        race_requests = [
            {"race_date": "20240101", "meet": 1, "race_number": 1},
        ]

        # Patch asyncio.gather to return a BaseException result directly.
        # This simulates the scenario where gather captures an exception
        # that ends up in the results list as a BaseException instance.
        exc = Exception("simulated gather failure")

        async def fake_gather(*coros, return_exceptions=False):
            # Cancel the actual coroutines to avoid warnings
            for c in coros:
                c.close()
            return [exc]

        with patch.object(asyncio, "gather", side_effect=fake_gather):
            results = await orchestrator.process_race_batch(
                race_requests, max_concurrent=1
            )

        assert len(results) == 1
        assert results[0].metadata.get("failed") is True
        assert "simulated" in results[0].metadata.get("error", "")


# ---------------------------------------------------------------------------
# 10. services/collection_enrichment.py  lines 249-251
# ---------------------------------------------------------------------------
class TestCollectionEnrichmentTrainerException:
    @pytest.mark.asyncio
    async def test_get_trainer_stats_exception_returns_defaults(self):
        from services.collection_enrichment import get_trainer_stats

        mock_kra = AsyncMock()
        mock_kra.get_trainer_info.side_effect = RuntimeError("API error")

        result = await get_trainer_stats(mock_kra, "TR001", "20240101", None)
        assert result["recent_win_rate"] == 0.18
        assert result["career_win_rate"] == 0.16
        assert result["total_wins"] == 0


# ---------------------------------------------------------------------------
# 11. services/collection_preprocessing.py  lines 59-60
# ---------------------------------------------------------------------------
class TestCollectionPreprocessingOddsRatio:
    def test_preprocess_data_invalid_win_odds_for_odds_ratio(self):
        # horse has valid win_odds for filtering but non-numeric for ratio calc
        raw_data = {
            "horses": [
                {"win_odds": 5.0, "weight": 500, "rating": 80},
                {"win_odds": 3.0, "weight": 480, "rating": 75},
            ]
        }
        # First verify normal case works
        result = preprocess_data(raw_data)
        assert len(result["horses"]) == 2

        # Now create a horse that passes the float(win_odds) > 0 filter
        # but whose win_odds later causes ValueError in odds_ratio calc.
        # This requires a custom object that floats once but fails later.
        class BadOdds:
            """Returns 5.0 on first float() call, raises on second."""

            def __init__(self):
                self._calls = 0

            def __float__(self):
                self._calls += 1
                if self._calls <= 1:
                    return 5.0
                raise ValueError("bad odds")

            def __gt__(self, other):
                return True

        raw_data2 = {
            "horses": [
                {"win_odds": BadOdds(), "weight": 500, "rating": 80},
                {"win_odds": 3.0, "weight": 480, "rating": 75},
            ]
        }
        result2 = preprocess_data(raw_data2)
        # The horse with BadOdds should have odds_ratio = 0 due to ValueError
        bad_horse = result2["horses"][0]
        assert bad_horse.get("odds_ratio") == 0


# ---------------------------------------------------------------------------
# 12. services/collection_status_diagnostics.py  lines 32-33
# ---------------------------------------------------------------------------
class TestCollectionStatusDiagnosticsTableCheckFail:
    @pytest.mark.asyncio
    async def test_table_check_exception_sets_false(self, db_session):
        from services.collection_status_diagnostics import (
            gather_collection_diagnostics,
        )

        original_execute = db_session.execute

        async def patched_execute(statement, *args, **kwargs):
            stmt_str = str(statement)
            # Only fail the table existence checks (SELECT 1 FROM <table>)
            if "SELECT 1 FROM" in stmt_str:
                raise RuntimeError("table check failed")
            return await original_execute(statement, *args, **kwargs)

        with patch.object(db_session, "execute", side_effect=patched_execute):
            result = await gather_collection_diagnostics(db_session)

        assert result["tables"]["jobs"] is False
        assert result["tables"]["races"] is False


# ---------------------------------------------------------------------------
# 13. services/kra_collection_module.py  lines 137-138
# ---------------------------------------------------------------------------
class TestKRACollectionModuleCollectResult:
    @pytest.mark.asyncio
    async def test_collect_result_delegates(self):
        from services.kra_collection_module import (
            CollectionCommands,
            ResultCollectInput,
        )

        mock_result_service = AsyncMock()
        mock_result_service.collect_result = AsyncMock(
            return_value={"race_id": "20240101_1_1", "top3": [1, 2, 3]}
        )

        commands = CollectionCommands(
            result_collection_service=mock_result_service,
        )

        mock_kra_api = AsyncMock()
        with patch.object(commands, "_get_kra_api", return_value=mock_kra_api):
            result = await commands.collect_result(
                ResultCollectInput(race_date="20240101", meet=1, race_number=1),
                db=AsyncMock(),
            )

        assert result["race_id"] == "20240101_1_1"
        mock_result_service.collect_result.assert_called_once()


# ---------------------------------------------------------------------------
# 14. services/result_collection_service.py  lines 148, 182-183
# ---------------------------------------------------------------------------
class TestResultCollectionServiceOddsGaps:
    @pytest.mark.asyncio
    async def test_invalid_pool_name_skipped(self, db_session):
        from services.result_collection_service import ResultCollectionService

        service = ResultCollectionService()

        # Build a race in DB first
        race = Race(
            race_id="20240719_1_1",
            date="20240719",
            meet=1,
            race_number=1,
            collection_status=DataStatus.COLLECTED,
            result_status=DataStatus.PENDING,
        )
        db_session.add(race)
        await db_session.commit()

        mock_kra = AsyncMock()
        # get_race_result returns valid 3 results
        mock_kra.get_race_result = AsyncMock(
            return_value={
                "response": {
                    "header": {"resultCode": "00"},
                    "body": {
                        "items": {
                            "item": [
                                {"ord": 1, "chulNo": 1, "hrName": "H1"},
                                {"ord": 2, "chulNo": 2, "hrName": "H2"},
                                {"ord": 3, "chulNo": 3, "hrName": "H3"},
                            ]
                        }
                    },
                }
            }
        )
        # get_final_odds returns items with invalid pool names
        mock_kra.get_final_odds = AsyncMock(
            return_value={
                "response": {
                    "header": {"resultCode": "00"},
                    "body": {
                        "items": {
                            "item": [
                                {
                                    "pool": "INVALID_POOL",
                                    "chulNo": 1,
                                    "odds": 5.0,
                                },
                            ]
                        }
                    },
                }
            }
        )

        result = await service.collect_result(
            race_date="20240719",
            meet=1,
            race_number=1,
            db=db_session,
            kra_api=mock_kra,
        )
        assert result["top3"] == [1, 2, 3]
        # The invalid pool odds should have been skipped (count=0)
        assert result["odds"]["count"] == 0

    @pytest.mark.asyncio
    async def test_rollback_exception_silently_caught(self, db_session):
        from services.result_collection_service import ResultCollectionService

        service = ResultCollectionService()

        race = Race(
            race_id="20240719_1_2",
            date="20240719",
            meet=1,
            race_number=2,
            collection_status=DataStatus.COLLECTED,
            result_status=DataStatus.PENDING,
        )
        db_session.add(race)
        await db_session.commit()

        mock_kra = AsyncMock()
        mock_kra.get_race_result = AsyncMock(
            return_value={
                "response": {
                    "header": {"resultCode": "00"},
                    "body": {
                        "items": {
                            "item": [
                                {"ord": 1, "chulNo": 1},
                                {"ord": 2, "chulNo": 2},
                                {"ord": 3, "chulNo": 3},
                            ]
                        }
                    },
                }
            }
        )
        # get_final_odds raises to trigger the except block in _collect_odds_after_result
        mock_kra.get_final_odds = AsyncMock(side_effect=RuntimeError("odds API broke"))

        # Make rollback also raise to hit lines 182-183
        rollback_called = False

        async def failing_rollback():
            nonlocal rollback_called
            rollback_called = True
            raise RuntimeError("rollback failed")

        with patch.object(db_session, "rollback", side_effect=failing_rollback):
            result = await service.collect_result(
                race_date="20240719",
                meet=1,
                race_number=2,
                db=db_session,
                kra_api=mock_kra,
            )

        # Should still succeed - odds failure is non-blocking
        assert result["top3"] == [1, 2, 3]
        assert result["odds"]["collected"] is False
        assert rollback_called
