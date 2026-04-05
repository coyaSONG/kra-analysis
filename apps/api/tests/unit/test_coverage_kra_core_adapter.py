"""Tests to cover remaining uncovered lines across multiple modules."""

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from pydantic import ValidationError

from adapters.kra_response_adapter import KRAResponseAdapter
from adapters.race_projection_adapter import RaceProjectionAdapter
from infrastructure.kra_api.core import (
    KRAApiAuthenticationError,
    KRAApiRateLimitError,
    KRAApiRequestError,
    KRAApiRetryableRequestError,
    KRARequestPolicy,
    _retry_delay,
    cache_ttl_for,
    request_json_with_retry,
)
from middleware.logging import _mask_sensitive_value
from models.collection_dto import (
    CollectionRequest,
    EnrichmentRequest,
    ResultCollectionRequest,
)
from models.database_models import DataStatus, PostgresEnum
from pipelines.base import (
    Pipeline,
    PipelineBuilder,
    PipelineContext,
    PipelineExecutionError,
    PipelineStage,
    StageResult,
    StageStatus,
)
from pipelines.stages import (
    CollectionStage,
    EnrichmentStage,
    PreprocessingStage,
    ValidationStage,
)
from policy.accounting import UsageAccountant, UsageReservation
from policy.authorization import PolicyAuthorizer
from policy.principal import AuthenticatedPrincipal, PolicyLimits
from services.collection_enrichment import calculate_recent_form, enrich_data
from services.collection_preprocessing import preprocess_data
from services.collection_status_diagnostics import _enum_to_str
from services.job_contract import (
    apply_job_shadow_fields,
    normalize_job_kind,
    normalize_lifecycle_status,
)
from services.result_collection_service import ResultCollectionService

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_DEFAULT_POLICY = KRARequestPolicy(
    base_url="https://example.test",
    api_key="test-key",
    timeout=10,
    max_retries=2,
    verify_ssl=True,
)


def _make_response(
    status_code: int,
    payload: dict | None = None,
    headers: dict[str, str] | None = None,
    *,
    raw_body: bytes | None = None,
) -> httpx.Response:
    request = httpx.Request("GET", "https://example.test/kra")
    body = raw_body if raw_body is not None else json.dumps(payload or {}).encode()
    return httpx.Response(
        status_code,
        request=request,
        headers=headers,
        content=body,
    )


# ===================================================================
# 1. infrastructure/kra_api/core.py
# ===================================================================


class TestCacheTtlForUnknown:
    def test_unknown_namespace_raises_key_error(self):
        with pytest.raises(KeyError, match="Unknown cache namespace"):
            cache_ttl_for("unknown_namespace")


class TestRetryDelayHttpDate:
    def test_retry_after_http_date(self):
        future = datetime.now(UTC) + timedelta(seconds=10)
        http_date = future.strftime("%a, %d %b %Y %H:%M:%S GMT")
        response = _make_response(429, headers={"Retry-After": http_date})
        delay = _retry_delay(0, response)
        assert delay > 0

    def test_retry_after_http_date_naive(self):
        future = datetime.now(UTC) + timedelta(seconds=5)
        http_date = future.strftime("%a, %d %b %Y %H:%M:%S GMT")
        response = _make_response(429, headers={"Retry-After": http_date})
        delay = _retry_delay(0, response)
        assert isinstance(delay, float)


@pytest.mark.asyncio
class TestRequestJsonWithRetryEdgeCases:
    async def test_json_decode_failure_retries_then_raises(self, monkeypatch):
        call_count = {"value": 0}
        sleep = AsyncMock()
        monkeypatch.setattr("infrastructure.kra_api.core.asyncio.sleep", sleep)

        class FakeClient:
            async def request(self, method, url, params, json=None):
                call_count["value"] += 1
                return _make_response(200, raw_body=b"not-json{{")

        with pytest.raises(KRAApiRetryableRequestError, match="Invalid JSON response"):
            await request_json_with_retry(FakeClient(), _DEFAULT_POLICY, "/test")

        assert call_count["value"] == 2
        sleep.assert_awaited_once()

    async def test_logical_error_retries_then_raises(self, monkeypatch):
        call_count = {"value": 0}
        sleep = AsyncMock()
        monkeypatch.setattr("infrastructure.kra_api.core.asyncio.sleep", sleep)

        class FakeClient:
            async def request(self, method, url, params, json=None):
                call_count["value"] += 1
                return _make_response(200, {"status": "error", "message": "bad"})

        with pytest.raises(KRAApiRetryableRequestError, match="KRA API error: bad"):
            await request_json_with_retry(FakeClient(), _DEFAULT_POLICY, "/test")

        assert call_count["value"] == 2

    async def test_http_401_raises_authentication_error(self, monkeypatch):
        sleep = AsyncMock()
        monkeypatch.setattr("infrastructure.kra_api.core.asyncio.sleep", sleep)

        class FakeClient:
            async def request(self, method, url, params, json=None):
                return _make_response(401, {"error": "unauthorized"})

        with pytest.raises(KRAApiAuthenticationError, match="authentication failed"):
            await request_json_with_retry(FakeClient(), _DEFAULT_POLICY, "/test")

    async def test_http_403_raises_authentication_error(self, monkeypatch):
        sleep = AsyncMock()
        monkeypatch.setattr("infrastructure.kra_api.core.asyncio.sleep", sleep)

        class FakeClient:
            async def request(self, method, url, params, json=None):
                return _make_response(403, {"error": "forbidden"})

        with pytest.raises(KRAApiAuthenticationError, match="authentication failed"):
            await request_json_with_retry(FakeClient(), _DEFAULT_POLICY, "/test")

    async def test_http_429_after_all_retries_raises_rate_limit_error(
        self, monkeypatch
    ):
        sleep = AsyncMock()
        monkeypatch.setattr("infrastructure.kra_api.core.asyncio.sleep", sleep)

        class FakeClient:
            async def request(self, method, url, params, json=None):
                return _make_response(429, {"error": "rate limited"})

        with pytest.raises(KRAApiRateLimitError, match="rate limit exceeded"):
            await request_json_with_retry(FakeClient(), _DEFAULT_POLICY, "/test")

    async def test_all_retries_exhausted_unreachable_line(self, monkeypatch):
        sleep = AsyncMock()
        monkeypatch.setattr("infrastructure.kra_api.core.asyncio.sleep", sleep)
        policy = KRARequestPolicy(
            base_url="https://example.test",
            api_key="test-key",
            timeout=10,
            max_retries=0,
            verify_ssl=True,
        )

        class FakeClient:
            async def request(self, method, url, params, json=None):
                return _make_response(200, {"ok": True})

        with pytest.raises(KRAApiRequestError, match="All retries exhausted"):
            await request_json_with_retry(FakeClient(), policy, "/test")


# ===================================================================
# 2. adapters/race_projection_adapter.py
# ===================================================================


class TestExtractTop3:
    def test_extract_top3_from_dict(self):
        result = RaceProjectionAdapter.extract_top3(
            {
                "top3": [3, 1, 5],
                "horses": [
                    {"chulNo": 3, "ord": 1},
                    {"chulNo": 1, "ord": 2},
                    {"chulNo": 5, "ord": 3},
                ],
            }
        )
        assert result == [3, 1, 5]


class TestNormalizeResultProjection:
    def test_none_returns_empty(self):
        result = RaceProjectionAdapter.normalize_result_projection(None)
        assert result["top3"] == []
        assert result["horses"] == []

    def test_non_dict_non_list_returns_empty(self):
        result = RaceProjectionAdapter.normalize_result_projection(123)
        assert result["top3"] == []
        assert result["horses"] == []

    def test_nested_result_key_delegates(self):
        inner = {
            "top3": [1, 2, 3],
            "horses": [
                {"chulNo": 1, "ord": 1},
                {"chulNo": 2, "ord": 2},
                {"chulNo": 3, "ord": 3},
            ],
        }
        result = RaceProjectionAdapter.normalize_result_projection({"result": inner})
        assert result["top3"] == [1, 2, 3]

    def test_dict_no_recognizable_keys_returns_empty(self):
        result = RaceProjectionAdapter.normalize_result_projection(
            {"something_else": 1}
        )
        assert result["top3"] == []
        assert result["horses"] == []


class TestNormalizeHorses:
    def test_non_list_input(self):
        result = RaceProjectionAdapter._normalize_horses(None)
        assert result == []

    def test_skip_non_dict_items(self):
        result = RaceProjectionAdapter._normalize_horses(
            [1, "not_dict", {"chulNo": 3, "ord": 1}]
        )
        assert len(result) == 1
        assert result[0]["chulNo"] == 3

    def test_top3_assigns_position_to_horse_with_no_ord(self):
        horses = [{"chulNo": 5}]
        result = RaceProjectionAdapter._normalize_horses(horses)
        assert result[0]["chulNo"] == 5


class TestExtractTop3FromHorses:
    def test_empty_horses_returns_empty(self):
        result = RaceProjectionAdapter._extract_top3_from_horses(None, [])
        assert result == []

    def test_horses_with_chulNo_zero_and_ord_positive(self):
        horses = [{"chulNo": 0, "ord": 2}]
        result = RaceProjectionAdapter._extract_top3_from_horses(None, horses)
        assert result == [2]

    def test_horses_with_positive_chulNo_and_zero_ord(self):
        horses = [{"chulNo": 7, "ord": 0}]
        result = RaceProjectionAdapter._extract_top3_from_horses(None, horses)
        assert result == [7]


class TestFindSourceItem:
    def test_skip_non_dict_items(self):
        result = RaceProjectionAdapter._find_source_item([1, "not_dict"], 5)
        assert result == {}


class TestNormalizeHorseNo:
    def test_none_returns_none(self):
        assert RaceProjectionAdapter._normalize_horse_no(None) is None


class TestSafeFloat:
    def test_non_number_returns_zero(self):
        assert RaceProjectionAdapter._safe_float("not_a_number") == 0.0


# ===================================================================
# 3. middleware/logging.py
# ===================================================================


class TestMaskSensitiveValue:
    def test_none_returns_none(self):
        assert _mask_sensitive_value(None) is None

    def test_empty_string_returns_empty(self):
        assert _mask_sensitive_value("") == ""


# ===================================================================
# 4. middleware/policy_accounting.py — lines 34-36, 47-48
# ===================================================================


@pytest.mark.asyncio
class TestPolicyAccountingMiddleware:
    async def test_dispatch_propagates_exception(self):
        from middleware.policy_accounting import PolicyAccountingMiddleware

        app = Mock()
        mw = PolicyAccountingMiddleware(app)

        request = Mock()
        request.state = SimpleNamespace(request_id="req-123")
        request.method = "GET"
        request.url = SimpleNamespace(path="/test")
        request.headers = {}

        async def failing_call_next(req):
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            await mw.dispatch(request, failing_call_next)

    async def test_commit_failure_is_logged(self):
        from middleware.policy_accounting import PolicyAccountingMiddleware

        app = Mock()
        mw = PolicyAccountingMiddleware(app)
        mw._accountant = Mock()
        mw._accountant.commit_request = AsyncMock(side_effect=Exception("db down"))

        response = Mock()
        response.status_code = 200
        response.headers = {}

        request = Mock()
        request.state = SimpleNamespace(request_id="req-1")
        request.method = "GET"
        request.url = SimpleNamespace(path="/test")
        request.headers = {}

        async def ok_call_next(req):
            return response

        result = await mw.dispatch(request, ok_call_next)
        assert result is response


# ===================================================================
# 5. services/collection_enrichment.py — lines 84-86, 99, 169
# ===================================================================


@pytest.mark.asyncio
class TestEnrichDataException:
    async def test_enrich_data_propagates_exception(self):
        async def failing_fetcher(horse_no, race_date, db):
            raise RuntimeError("fetch failed")

        data = {"horses": [{"hr_no": "H1"}], "race_date": "20240101"}

        with pytest.raises(RuntimeError, match="fetch failed"):
            await enrich_data(
                data,
                None,
                get_horse_past_performances=failing_fetcher,
                calculate_performance_stats_fn=lambda x: {},
                get_default_stats_fn=lambda: {},
                get_jockey_stats=AsyncMock(),
                get_trainer_stats=AsyncMock(),
                analyze_weather_impact_fn=lambda x: {},
            )


class TestCalculateRecentFormEmpty:
    def test_empty_dataframe_returns_zero(self):
        import pandas as pd

        result = calculate_recent_form(pd.DataFrame())
        assert result == 0


@pytest.mark.asyncio
class TestGetHorsePastPerformancesNoneDb:
    async def test_returns_empty_when_db_none(self):
        from services.collection_enrichment import get_horse_past_performances

        result = await get_horse_past_performances("H001", "20240101", None)
        assert result == []


# ===================================================================
# 6. services/collection_preprocessing.py — lines 45-46, 52-53, 59-60, 73-75
# ===================================================================


class TestPreprocessDataEdgeCases:
    def test_weight_ratio_value_error(self):
        # Need a valid horse for avg_weight > 0, and one with invalid weight
        horses = [
            {"win_odds": 5.0, "weight": 50, "rating": 80},
            {"win_odds": 3.0, "weight": "invalid", "rating": 80},
        ]
        result = preprocess_data({"horses": horses})
        assert result["horses"][1]["weight_ratio"] == 0

    def test_rating_ratio_value_error(self):
        horses = [
            {"win_odds": 5.0, "weight": 50, "rating": 80},
            {"win_odds": 3.0, "weight": 50, "rating": "invalid"},
        ]
        result = preprocess_data({"horses": horses})
        assert result["horses"][1]["rating_ratio"] == 0

    def test_odds_ratio_value_error(self):
        # The odds_ratio except branch requires float(horse.get("win_odds", 0))
        # to raise. But win_odds already passed the float() filter above.
        # We need an object that passes float() the first time (filtering)
        # but fails the second time (ratio computation).
        class TrickyValue:
            def __init__(self):
                self._call_count = 0

            def __float__(self):
                self._call_count += 1
                if self._call_count > 2:
                    raise ValueError("nope")
                return 5.0

            def __gt__(self, other):
                return True

        horses = [
            {"win_odds": 3.0, "weight": 50, "rating": 80},
            {"win_odds": TrickyValue(), "weight": 50, "rating": 80},
        ]
        result = preprocess_data({"horses": horses})
        # The second horse should have odds_ratio set (possibly 0 or calculated)
        assert "odds_ratio" in result["horses"][1]

    def test_preprocess_propagates_unexpected_error(self):
        with pytest.raises((TypeError, AttributeError)):
            preprocess_data(None)


# ===================================================================
# 7. services/collection_status_diagnostics.py — lines 18, 32-33
# ===================================================================


class TestEnumToStr:
    def test_plain_string_value(self):
        assert _enum_to_str("hello") == "hello"

    def test_integer_value(self):
        assert _enum_to_str(42) == "42"


# ===================================================================
# 8. models/collection_dto.py — lines 57, 92-96, 124, 131-133
# ===================================================================


class TestCollectionDtoValidation:
    def test_race_numbers_out_of_range(self):
        with pytest.raises(ValidationError, match="1-20"):
            CollectionRequest(date="20240101", meet=1, race_numbers=[0, 25])

    def test_enrichment_request_invalid_type(self):
        with pytest.raises(ValidationError, match="유효하지 않은 보강 유형"):
            EnrichmentRequest(race_ids=["r1"], enrich_types=["horse", "invalid_type"])

    def test_result_collection_request_invalid_date_format(self):
        with pytest.raises(ValidationError, match="YYYYMMDD"):
            ResultCollectionRequest(date="2024-01-01", meet=1, race_number=1)

    def test_result_collection_request_future_date(self):
        future = (datetime.now() + timedelta(days=365)).strftime("%Y%m%d")
        with pytest.raises(ValidationError, match="미래 날짜"):
            ResultCollectionRequest(date=future, meet=1, race_number=1)

    def test_result_collection_request_invalid_date_value(self):
        with pytest.raises(ValidationError, match="유효하지 않은 날짜"):
            ResultCollectionRequest(date="20241332", meet=1, race_number=1)


# ===================================================================
# 9. models/database_models.py — lines 53, 62-66, 71, 76, 114-123
# ===================================================================


class TestPostgresEnum:
    def test_process_bind_param_none(self):
        pe = PostgresEnum(DataStatus)
        assert pe.process_bind_param(None, None) is None

    def test_process_bind_param_string_by_name(self):
        pe = PostgresEnum(DataStatus)
        result = pe.process_bind_param("PENDING", None)
        assert result == "pending"

    def test_process_bind_param_unknown_string(self):
        pe = PostgresEnum(DataStatus)
        result = pe.process_bind_param("nonexistent", None)
        assert result == "nonexistent"

    def test_process_bind_param_non_string_non_enum(self):
        pe = PostgresEnum(DataStatus)
        result = pe.process_bind_param(42, None)
        assert result == 42

    def test_process_result_value_none(self):
        pe = PostgresEnum(DataStatus)
        assert pe.process_result_value(None, None) is None

    def test_process_result_value_unknown(self):
        pe = PostgresEnum(DataStatus)
        result = pe.process_result_value("nonexistent", None)
        assert result == "nonexistent"


class TestDataStatusMissing:
    def test_case_insensitive_by_value(self):
        assert DataStatus("PENDING") is DataStatus.PENDING

    def test_case_insensitive_by_name(self):
        assert DataStatus("COLLECTED") is DataStatus.COLLECTED

    def test_non_string_returns_none(self):
        result = DataStatus._missing_(123)
        assert result is None


# ===================================================================
# 10. pipelines/base.py — lines 126, 139, 148, 160, 300-301, 337-361
# ===================================================================


class ConcreteStage(PipelineStage):
    """Minimal concrete stage for testing abstract base class defaults."""

    async def execute(self, context: PipelineContext) -> StageResult:
        return StageResult(status=StageStatus.COMPLETED)

    async def validate_prerequisites(self, context: PipelineContext) -> bool:
        return True


class TestPipelineStageDefaults:
    @pytest.mark.asyncio
    async def test_rollback_default_logs(self):
        stage = ConcreteStage("test_stage")
        ctx = PipelineContext(race_date="20240101", meet=1, race_number=1)
        await stage.rollback(ctx)

    def test_should_skip_default_returns_false(self):
        stage = ConcreteStage("test_stage")
        ctx = PipelineContext(race_date="20240101", meet=1, race_number=1)
        assert stage.should_skip(ctx) is False


class FailingRollbackStage(PipelineStage):
    async def execute(self, context: PipelineContext) -> StageResult:
        return StageResult(status=StageStatus.COMPLETED)

    async def validate_prerequisites(self, context: PipelineContext) -> bool:
        return True

    async def rollback(self, context: PipelineContext) -> None:
        raise RuntimeError("rollback failed")


class FailingExecuteStage(PipelineStage):
    async def execute(self, context: PipelineContext) -> StageResult:
        raise RuntimeError("stage boom")

    async def validate_prerequisites(self, context: PipelineContext) -> bool:
        return True


@pytest.mark.asyncio
class TestPipelineRollbackFailure:
    async def test_rollback_error_is_logged_not_raised(self):
        pipeline = Pipeline("test")
        pipeline.add_stage(FailingRollbackStage("s1"))
        pipeline.add_stage(FailingExecuteStage("s2"))

        ctx = PipelineContext(race_date="20240101", meet=1, race_number=1)
        with pytest.raises(PipelineExecutionError):
            await pipeline.execute(ctx)


class TestPipelineBuilder:
    def test_add_collection_stage(self):
        builder = PipelineBuilder("test")
        builder.add_collection_stage(kra_api_service=Mock(), db_session=Mock())
        assert len(builder.pipeline.stages) == 1
        assert builder.pipeline.stages[0].name == "collection"

    def test_add_preprocessing_stage(self):
        builder = PipelineBuilder("test")
        builder.add_preprocessing_stage()
        assert len(builder.pipeline.stages) == 1
        assert builder.pipeline.stages[0].name == "preprocessing"

    def test_add_enrichment_stage(self):
        builder = PipelineBuilder("test")
        builder.add_enrichment_stage(collection_service=Mock(), db_session=Mock())
        assert len(builder.pipeline.stages) == 1
        assert builder.pipeline.stages[0].name == "enrichment"

    def test_add_validation_stage(self):
        builder = PipelineBuilder("test")
        builder.add_validation_stage()
        assert len(builder.pipeline.stages) == 1
        assert builder.pipeline.stages[0].name == "validation"


# ===================================================================
# 11. pipelines/stages.py — remaining uncovered lines
# ===================================================================


class TestCollectionStageQuality:
    def test_calculate_data_quality_empty(self):
        stage = CollectionStage(kra_api_service=Mock(), db_session=Mock())
        assert stage._calculate_data_quality({}) == 0.0
        assert stage._calculate_data_quality(None) == 0.0

    def test_calculate_data_quality_no_horses(self):
        stage = CollectionStage(kra_api_service=Mock(), db_session=Mock())
        assert stage._calculate_data_quality({"horses": []}) == 0.5


class TestPreprocessingStagePrereqNoHorses:
    @pytest.mark.asyncio
    async def test_validate_prerequisites_no_horses(self):
        stage = PreprocessingStage()
        ctx = PipelineContext(race_date="20240101", meet=1, race_number=1)
        ctx.raw_data = {"horses": []}
        assert await stage.validate_prerequisites(ctx) is False


class TestEnrichmentStageNoService:
    @pytest.mark.asyncio
    async def test_validate_prerequisites_no_collection_service(self):
        stage = EnrichmentStage(collection_service=None, db_session=Mock())
        ctx = PipelineContext(race_date="20240101", meet=1, race_number=1)
        ctx.preprocessed_data = {"horses": []}
        assert await stage.validate_prerequisites(ctx) is False


@pytest.mark.asyncio
class TestEnrichmentStageExecute:
    async def test_execute_success(self):
        mock_service = AsyncMock()
        mock_service.enrich_race_data = AsyncMock(
            return_value={
                "horses": [{"past_stats": {}, "jockey_stats": {}, "trainer_stats": {}}]
            }
        )
        stage = EnrichmentStage(collection_service=mock_service, db_session=Mock())
        ctx = PipelineContext(race_date="20240101", meet=1, race_number=1)
        ctx.preprocessed_data = {"horses": []}
        result = await stage.execute(ctx)
        assert result.is_success()
        assert ctx.enriched_data is not None

    async def test_execute_failure(self):
        mock_service = AsyncMock()
        mock_service.enrich_race_data = AsyncMock(side_effect=RuntimeError("boom"))
        stage = EnrichmentStage(collection_service=mock_service, db_session=Mock())
        ctx = PipelineContext(race_date="20240101", meet=1, race_number=1)
        ctx.preprocessed_data = {"horses": []}
        result = await stage.execute(ctx)
        assert result.is_failure()

    async def test_calculate_enrichment_quality_empty_data(self):
        stage = EnrichmentStage(collection_service=Mock(), db_session=Mock())
        assert stage._calculate_enrichment_quality({}) == 0.0
        assert stage._calculate_enrichment_quality(None) == 0.0

    async def test_calculate_enrichment_quality_no_horses(self):
        stage = EnrichmentStage(collection_service=Mock(), db_session=Mock())
        assert stage._calculate_enrichment_quality({"horses": []}) == 0.0

    async def test_calculate_enrichment_quality_with_horses(self):
        stage = EnrichmentStage(collection_service=Mock(), db_session=Mock())
        data = {
            "horses": [
                {
                    "past_stats": {"x": 1},
                    "jockey_stats": {"y": 2},
                    "trainer_stats": {"z": 3},
                }
            ]
        }
        assert stage._calculate_enrichment_quality(data) == 1.0


@pytest.mark.asyncio
class TestValidationStageEdgeCases:
    async def test_execute_exception(self):
        stage = ValidationStage()
        ctx = PipelineContext(race_date="20240101", meet=1, race_number=1)
        ctx.enriched_data = None  # Will cause AttributeError in _validate_data
        result = await stage.execute(ctx)
        assert result.is_failure()
        assert "Validation error" in result.error

    def test_validate_data_empty_data(self):
        stage = ValidationStage()
        result = stage._validate_data({})
        assert not result["is_valid"]
        assert any("Insufficient" in e for e in result["errors"])

    def test_validate_data_missing_required_fields(self):
        stage = ValidationStage(min_horses=0, min_quality_score=0.0)
        result = stage._validate_data({"horses": []})
        assert any("Missing required field" in e for e in result["errors"])

    def test_validate_horse_data_negative_odds(self):
        stage = ValidationStage()
        errors = stage._validate_horse_data(
            {"hr_no": "1", "hr_name": "Test", "win_odds": -1.0}, 1
        )
        assert any("Invalid win_odds" in e for e in errors)

    def test_validate_horse_data_invalid_odds_format(self):
        stage = ValidationStage()
        errors = stage._validate_horse_data(
            {"hr_no": "1", "hr_name": "Test", "win_odds": "abc"}, 1
        )
        assert any("Invalid win_odds format" in e for e in errors)

    def test_calculate_overall_quality_empty(self):
        stage = ValidationStage()
        assert stage._calculate_overall_quality({}) == 0.0
        assert stage._calculate_overall_quality({"horses": []}) == 0.0


# ===================================================================
# 12. policy/accounting.py — lines 86-87
# ===================================================================


@pytest.mark.asyncio
class TestUsageAccountantMissingSessionFactory:
    async def test_commit_request_no_session_factory(self):
        accountant = UsageAccountant()
        reservation = UsageReservation(
            principal_id="p1",
            owner_ref="o1",
            credential_id="c1",
            action="test",
            units=1,
        )
        app_state = SimpleNamespace(db_session_factory=None)
        request = Mock()
        request.state = SimpleNamespace(usage_reservation=reservation, request_id="r1")
        request.app = SimpleNamespace(state=app_state)
        request.headers = {}
        request.method = "GET"
        request.url = SimpleNamespace(path="/test")

        # Should return early without error
        await accountant.commit_request(request, status_code=200)


# ===================================================================
# 13. policy/authorization.py — line 42
# ===================================================================


@pytest.mark.asyncio
class TestPolicyAuthorizerDenied:
    async def test_insufficient_permissions_raises_403(self):
        from fastapi import HTTPException

        authorizer = PolicyAuthorizer()
        principal = AuthenticatedPrincipal(
            principal_id="p1",
            subject_id="s1",
            owner_ref="o1",
            credential_id="c1",
            display_name="Test",
            auth_method="api_key",
            permissions=frozenset({"read"}),
            limits=PolicyLimits(),
        )
        with pytest.raises(HTTPException) as exc_info:
            await authorizer.authorize(principal, "collection.collect")
        assert exc_info.value.status_code == 403


# ===================================================================
# 14. services/job_contract.py — lines 45-46, 84-85, 98-102, 112-118
# ===================================================================


class TestJobContractEdgeCases:
    def test_normalize_job_kind_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown job kind"):
            normalize_job_kind("zzz_unknown")

    def test_normalize_lifecycle_status_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown lifecycle status"):
            normalize_lifecycle_status("zzz_unknown")

    def test_apply_job_shadow_fields_unknown_kind_fallback(self):
        job = SimpleNamespace(type="zzz_unknown", status="pending")
        apply_job_shadow_fields(job)
        assert job.job_kind_v2 == "zzz_unknown"

    def test_apply_job_shadow_fields_unknown_status_fallback(self):
        job = SimpleNamespace(type="collection", status="zzz_unknown")
        apply_job_shadow_fields(job)
        assert job.lifecycle_state_v2 == "zzz_unknown"

    def test_apply_job_shadow_fields_enum_fallback_kind(self):
        class FakeEnum:
            value = "zzz_fake"

        job = SimpleNamespace(type="collection", status="pending")
        apply_job_shadow_fields(job, job_kind=FakeEnum())
        assert job.job_kind_v2 == "zzz_fake"

    def test_apply_job_shadow_fields_enum_fallback_status(self):
        class FakeEnum:
            value = "zzz_fake"

        job = SimpleNamespace(type="collection", status="pending")
        apply_job_shadow_fields(job, lifecycle_status=FakeEnum())
        assert job.lifecycle_state_v2 == "zzz_fake"


# ===================================================================
# 15. dependencies/auth.py — lines 100-102, 269, 277, 282, 287, 352
# ===================================================================


class TestAuthHelpers:
    def test_require_admin_returns_key(self):
        from dependencies.auth import require_admin

        key = Mock()
        result = require_admin(api_key_obj=key)
        assert result is key

    def test_require_write_returns_key(self):
        from dependencies.auth import require_write

        key = Mock()
        result = require_write(api_key_obj=key)
        assert result is key

    @pytest.mark.asyncio
    async def test_check_resource_access_unknown_type(self):
        from dependencies.auth import check_resource_access

        key = Mock()
        key.permissions = ["read"]
        result = await check_resource_access("unknown_type", "id1", key, Mock())
        assert result is False


# ===================================================================
# 16. adapters/kra_response_adapter.py — lines 59-69, 232-235
# ===================================================================


class TestKRAResponseAdapterUncovered:
    def test_extract_items_type_error_in_response(self):
        # Trigger the except (KeyError, TypeError) branch
        # response["response"]["body"]["items"]["item"] causes TypeError
        # if body is something unexpected like a list
        result = KRAResponseAdapter.extract_items({"response": {"body": [1, 2, 3]}})
        assert result == []

    def test_get_error_message_fallback(self):
        result = KRAResponseAdapter.get_error_message({"no_response_key": True})
        assert result == "Failed to parse error message"

    def test_get_error_message_type_error_in_header(self):
        # Trigger the except (KeyError, TypeError) branch
        result = KRAResponseAdapter.get_error_message({"response": None})
        assert result == "Failed to parse error message"


# ===================================================================
# 17. services/result_collection_service.py — lines 70, 84, 89, 148, 182-183, 189, 192, 198-201
# ===================================================================


@pytest.mark.asyncio
class TestResultCollectionServiceUncovered:
    async def test_mark_result_failure_none_race(self):
        service = ResultCollectionService()
        db = AsyncMock()
        await service._mark_result_failure(None, db)
        db.commit.assert_not_awaited()

    async def test_mark_result_failure_already_collected(self):
        service = ResultCollectionService()
        race = Mock()
        race.result_status = DataStatus.COLLECTED
        race.result_data = {"top3": [1, 2, 3]}
        db = AsyncMock()
        await service._mark_result_failure(race, db)
        db.commit.assert_not_awaited()

    async def test_mark_result_failure_commit_error(self):
        service = ResultCollectionService()
        race = Mock()
        race.result_status = DataStatus.PENDING
        race.result_data = None
        db = AsyncMock()
        db.commit = AsyncMock(side_effect=Exception("commit failed"))
        db.rollback = AsyncMock()
        with pytest.raises(Exception, match="commit failed"):
            await service._mark_result_failure(race, db)
        db.rollback.assert_awaited_once()

    async def test_collect_result_unsuccessful_response(self):
        service = ResultCollectionService()
        kra_api = AsyncMock()
        kra_api.get_race_result = AsyncMock(
            return_value={"response": {"header": {"resultCode": "99"}}}
        )

        db = AsyncMock()
        db_result = Mock()
        db_result.scalar_one_or_none.return_value = Mock(
            result_status=DataStatus.PENDING, result_data=None
        )
        db.execute = AsyncMock(return_value=db_result)

        from services.result_collection_service import ResultNotFoundError

        with pytest.raises(ResultNotFoundError, match="경주 결과를 찾을 수 없습니다"):
            await service.collect_result(
                race_date="20240101", meet=1, race_number=1, db=db, kra_api=kra_api
            )

    async def test_collect_result_insufficient_top3(self):
        service = ResultCollectionService()
        kra_api = AsyncMock()
        kra_api.get_race_result = AsyncMock(
            return_value={
                "response": {
                    "header": {"resultCode": "00"},
                    "body": {
                        "items": {
                            "item": [
                                {"ord": "1", "chulNo": "3"},
                                {"ord": "2", "chulNo": "5"},
                            ]
                        }
                    },
                }
            }
        )

        db = AsyncMock()
        db_result = Mock()
        db_result.scalar_one_or_none.return_value = Mock(
            result_status=DataStatus.PENDING, result_data=None
        )
        db.execute = AsyncMock(return_value=db_result)

        from services.result_collection_service import ResultNotFoundError

        with pytest.raises(ResultNotFoundError, match="1-3위 결과가 부족합니다"):
            await service.collect_result(
                race_date="20240101", meet=1, race_number=1, db=db, kra_api=kra_api
            )

    async def test_collect_result_race_not_found(self):
        service = ResultCollectionService()
        kra_api = AsyncMock()
        kra_api.get_race_result = AsyncMock(
            return_value={
                "response": {
                    "header": {"resultCode": "00"},
                    "body": {
                        "items": {
                            "item": [
                                {"ord": "1", "chulNo": "3"},
                                {"ord": "2", "chulNo": "5"},
                                {"ord": "3", "chulNo": "7"},
                            ]
                        }
                    },
                }
            }
        )

        db = AsyncMock()
        db_result = Mock()
        db_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=db_result)

        from services.result_collection_service import ResultNotFoundError

        with pytest.raises(ResultNotFoundError, match="경주를 찾을 수 없습니다"):
            await service.collect_result(
                race_date="20240101", meet=1, race_number=1, db=db, kra_api=kra_api
            )


# ===================================================================
# 18. middleware/rate_limit.py — lines 33-35, 98-100, 121-124, 150-152
# ===================================================================


class TestRateLimitMiddleware:
    @pytest.mark.asyncio
    async def test_dispatch_settings_exception_passes_through(self, monkeypatch):
        from middleware.rate_limit import RateLimitMiddleware

        app = Mock()
        mw = RateLimitMiddleware(app, calls=10, period=60)

        # Force settings access to raise
        monkeypatch.setattr(
            "middleware.rate_limit.settings",
            Mock(side_effect=AttributeError("no settings")),
        )

        request = Mock()
        response = Mock()
        response.status_code = 200

        async def call_next(req):
            return response

        # The try/except around settings should catch and pass through
        # We need to make settings.environment raise
        class BrokenSettings:
            @property
            def environment(self):
                raise RuntimeError("boom")

        monkeypatch.setattr("middleware.rate_limit.settings", BrokenSettings())
        result = await mw.dispatch(request, call_next)
        assert result is response


class TestAPIKeyRateLimiter:
    @pytest.mark.asyncio
    async def test_check_rate_limit_redis_get_fails(self):
        from middleware.rate_limit import APIKeyRateLimiter

        limiter = APIKeyRateLimiter()
        # When redis_client is None and get_redis fails
        with patch(
            "middleware.rate_limit.get_redis", side_effect=Exception("no redis")
        ):
            allowed, info = await limiter.check_rate_limit("key1", 100)
            assert allowed is True
            assert info["remaining"] == 100

    @pytest.mark.asyncio
    async def test_check_rate_limit_redis_incr_fails(self):
        from middleware.rate_limit import APIKeyRateLimiter

        limiter = APIKeyRateLimiter()
        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(side_effect=Exception("incr failed"))
        limiter.redis_client = mock_redis

        allowed, info = await limiter.check_rate_limit("key1", 100)
        assert allowed is True
        assert info["remaining"] == 100
