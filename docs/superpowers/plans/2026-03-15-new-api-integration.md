# 8개 신규 KRA API 통합 구현 계획

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 8개 신규 KRA 공공 API를 기존 수집 파이프라인에 통합하여 basic_data를 확장하고, 배당률 데이터용 race_odds 테이블을 추가한다.

**Architecture:** 기존 KRAAPIService에 8개 API 메서드 추가 → CollectionService의 collect_race_data에서 경주 단위/말 단위 데이터 수집 통합 → 배당률은 별도 collect_race_odds 메서드로 race_odds 테이블에 UPSERT. 기존 패턴(캐시, 어댑터, convert_api_to_internal)을 그대로 따른다.

**Tech Stack:** Python 3, FastAPI, SQLAlchemy (async), httpx, Supabase PostgreSQL

**설계 문서:** `docs/new-api-integration-design.md`
**Migration:** `apps/api/migrations/003_add_race_odds.sql` (이미 작성됨)

---

## 파일 구조

| 파일 | 변경 | 설명 |
|------|------|------|
| `apps/api/services/kra_api_service.py` | Modify | 8개 API 메서드 추가 |
| `apps/api/models/database_models.py` | Modify | RaceOdds 모델 추가 |
| `apps/api/services/collection_service.py` | Modify | 수집 파이프라인에 신규 API 통합 |
| `apps/api/tests/unit/test_kra_api_new_endpoints.py` | Create | 새 API 메서드 단위 테스트 |
| `apps/api/tests/unit/test_race_odds_model.py` | Create | RaceOdds 모델 테스트 |
| `apps/api/tests/unit/test_collection_new_apis.py` | Create | 통합 수집 테스트 |

---

## Task 1: KRAAPIService에 경주 단위 API 메서드 추가

**Files:**
- Modify: `apps/api/services/kra_api_service.py`
- Test: `apps/api/tests/unit/test_kra_api_new_endpoints.py`

API189_1(경주로정보), API72_2(경주계획표), API9_1(출전취소) 3개 경주 단위 메서드 추가.

- [ ] **Step 1: 테스트 파일 생성 - 경주 단위 API 3개**

```python
# apps/api/tests/unit/test_kra_api_new_endpoints.py
"""신규 KRA API 엔드포인트 단위 테스트"""
import pytest
from unittest.mock import AsyncMock, patch

from services.kra_api_service import KRAAPIService


def _make_api_response(items):
    """KRA API 표준 응답 생성 헬퍼"""
    return {
        "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE."},
            "body": {
                "items": {"item": items},
                "numOfRows": len(items),
                "pageNo": 1,
                "totalCount": len(items),
            },
        }
    }


@pytest.fixture
def kra_service():
    with patch.object(KRAAPIService, "__init__", lambda self: None):
        svc = KRAAPIService.__new__(KRAAPIService)
        svc._make_request = AsyncMock()
        svc._get_cached = AsyncMock(return_value=None)
        svc._set_cached = AsyncMock()
        return svc


class TestGetTrackInfo:
    @pytest.mark.asyncio
    async def test_returns_items(self, kra_service):
        kra_service._make_request.return_value = _make_api_response(
            [{"weather": "맑음", "track": "건조", "waterPercent": 3, "rcNo": 1}]
        )
        result = await kra_service.get_track_info("20260315", "1")
        assert result["response"]["body"]["items"]["item"][0]["weather"] == "맑음"
        kra_service._make_request.assert_called_once()
        call_kwargs = kra_service._make_request.call_args
        assert "API189_1/Track_1" in call_kwargs.kwargs.get("endpoint", call_kwargs.args[0] if call_kwargs.args else "")

    @pytest.mark.asyncio
    async def test_uses_cache(self, kra_service):
        cached = _make_api_response([{"weather": "흐림"}])
        kra_service._get_cached.return_value = cached
        result = await kra_service.get_track_info("20260315", "1")
        assert result == cached
        kra_service._make_request.assert_not_called()


class TestGetRacePlan:
    @pytest.mark.asyncio
    async def test_returns_items(self, kra_service):
        kra_service._make_request.return_value = _make_api_response(
            [{"rank": "국6등급", "rcDist": 1200, "rcNo": 1}]
        )
        result = await kra_service.get_race_plan("20260315", "1")
        assert result["response"]["body"]["items"]["item"][0]["rank"] == "국6등급"

    @pytest.mark.asyncio
    async def test_cache_ttl_24h(self, kra_service):
        kra_service._make_request.return_value = _make_api_response([{}])
        await kra_service.get_race_plan("20260315", "1")
        kra_service._set_cached.assert_called_once()
        assert kra_service._set_cached.call_args.args[2] == 86400  # 24시간


class TestGetCancelledHorses:
    @pytest.mark.asyncio
    async def test_returns_items(self, kra_service):
        kra_service._make_request.return_value = _make_api_response(
            [{"chulNo": 2, "hrName": "거센빅맨", "reason": "마체이상"}]
        )
        result = await kra_service.get_cancelled_horses("20260315", "1")
        items = result["response"]["body"]["items"]["item"]
        assert items[0]["chulNo"] == 2

    @pytest.mark.asyncio
    async def test_cache_ttl_30min(self, kra_service):
        kra_service._make_request.return_value = _make_api_response([{}])
        await kra_service.get_cancelled_horses("20260315", "1")
        assert kra_service._set_cached.call_args.args[2] == 1800  # 30분
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

```bash
cd apps/api && uv run python3 -m pytest tests/unit/test_kra_api_new_endpoints.py -v 2>&1 | head -30
```
Expected: FAIL — `get_track_info`, `get_race_plan`, `get_cancelled_horses` 미정의

- [ ] **Step 3: KRAAPIService에 3개 메서드 구현**

`apps/api/services/kra_api_service.py`의 `get_weather_info` 메서드 바로 앞에 추가:

```python
    async def get_track_info(
        self, race_date: str, meet: str, use_cache: bool = True
    ) -> dict[str, Any]:
        """경주로 정보 조회 (API189_1 - 주로상태/날씨)"""
        cache_key = f"track_info:{race_date}:{meet}"
        if use_cache:
            cached_data = await self._get_cached(cache_key)
            if cached_data:
                return cached_data
        params = {
            "meet": meet,
            "rc_date_fr": race_date,
            "rc_date_to": race_date,
            "numOfRows": 50,
            "pageNo": 1,
            "_type": "json",
        }
        result = await self._make_request(
            endpoint="API189_1/Track_1", params=params
        )
        if use_cache:
            await self._set_cached(cache_key, result, ttl=3600)
        return result

    async def get_race_plan(
        self, race_date: str, meet: str, use_cache: bool = True
    ) -> dict[str, Any]:
        """경주 계획표 조회 (API72_2)"""
        cache_key = f"race_plan:{race_date}:{meet}"
        if use_cache:
            cached_data = await self._get_cached(cache_key)
            if cached_data:
                return cached_data
        params = {
            "meet": meet,
            "rc_date": race_date,
            "numOfRows": 50,
            "pageNo": 1,
            "_type": "json",
        }
        result = await self._make_request(
            endpoint="API72_2/racePlan_2", params=params
        )
        if use_cache:
            await self._set_cached(cache_key, result, ttl=86400)
        return result

    async def get_cancelled_horses(
        self, race_date: str, meet: str, use_cache: bool = True
    ) -> dict[str, Any]:
        """출전 취소 정보 조회 (API9_1)"""
        cache_key = f"cancelled_horses:{race_date}:{meet}"
        if use_cache:
            cached_data = await self._get_cached(cache_key)
            if cached_data:
                return cached_data
        params = {
            "meet": meet,
            "rc_date": race_date,
            "numOfRows": 100,
            "pageNo": 1,
            "_type": "json",
        }
        result = await self._make_request(
            endpoint="API9_1/raceHorseCancelInfo_1", params=params
        )
        if use_cache:
            await self._set_cached(cache_key, result, ttl=1800)
        return result
```

- [ ] **Step 4: 테스트 실행 → 통과 확인**

```bash
cd apps/api && uv run python3 -m pytest tests/unit/test_kra_api_new_endpoints.py -v
```
Expected: 6 passed

- [ ] **Step 5: 커밋**

```bash
git add apps/api/services/kra_api_service.py apps/api/tests/unit/test_kra_api_new_endpoints.py
git commit -m "feat: add track info, race plan, cancelled horses API methods"
```

---

## Task 2: KRAAPIService에 말 단위 API 메서드 추가

**Files:**
- Modify: `apps/api/services/kra_api_service.py`
- Modify: `apps/api/tests/unit/test_kra_api_new_endpoints.py`

API11_1(기수성적), API14_1(마주정보), API329(조교현황) 3개 말 단위 메서드 추가.

- [ ] **Step 1: 테스트 추가**

`test_kra_api_new_endpoints.py`에 추가:

```python
class TestGetJockeyStats:
    @pytest.mark.asyncio
    async def test_returns_items(self, kra_service):
        kra_service._make_request.return_value = _make_api_response(
            [{"jkName": "문세영", "winRateT": 9.3, "qnlRateT": 18.8}]
        )
        result = await kra_service.get_jockey_stats("090123", "1")
        items = result["response"]["body"]["items"]["item"]
        assert items[0]["winRateT"] == 9.3

    @pytest.mark.asyncio
    async def test_cache_ttl_24h(self, kra_service):
        kra_service._make_request.return_value = _make_api_response([{}])
        await kra_service.get_jockey_stats("090123", "1")
        assert kra_service._set_cached.call_args.args[2] == 86400


class TestGetOwnerInfo:
    @pytest.mark.asyncio
    async def test_returns_items(self, kra_service):
        kra_service._make_request.return_value = _make_api_response(
            [{"owName": "(주)나스카", "owNo": 110034}]
        )
        result = await kra_service.get_owner_info("110034", "1")
        items = result["response"]["body"]["items"]["item"]
        assert items[0]["owName"] == "(주)나스카"


class TestGetTrainingStatus:
    @pytest.mark.asyncio
    async def test_returns_items(self, kra_service):
        kra_service._make_request.return_value = _make_api_response(
            [{"hrnm": "라온킹스맨", "remkTxt": "양호", "trngDt": 20260313}]
        )
        result = await kra_service.get_training_status("20260313")
        items = result["response"]["body"]["items"]["item"]
        assert items[0]["remkTxt"] == "양호"

    @pytest.mark.asyncio
    async def test_cache_ttl_6h(self, kra_service):
        kra_service._make_request.return_value = _make_api_response([{}])
        await kra_service.get_training_status("20260313")
        assert kra_service._set_cached.call_args.args[2] == 21600
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

- [ ] **Step 3: 3개 메서드 구현**

`kra_api_service.py`에 추가 (get_cancelled_horses 뒤):

```python
    async def get_jockey_stats(
        self, jockey_no: str, meet: str = "1", use_cache: bool = True
    ) -> dict[str, Any]:
        """기수 성적 정보 조회 (API11_1)"""
        cache_key = f"jockey_stats:{jockey_no}:{meet}"
        if use_cache:
            cached_data = await self._get_cached(cache_key)
            if cached_data:
                return cached_data
        params = {
            "jk_no": jockey_no,
            "meet": meet,
            "numOfRows": 10,
            "pageNo": 1,
            "_type": "json",
        }
        result = await self._make_request(
            endpoint="API11_1/jockeyResult_1", params=params
        )
        if use_cache:
            await self._set_cached(cache_key, result, ttl=86400)
        return result

    async def get_owner_info(
        self, owner_no: str, meet: str = "1", use_cache: bool = True
    ) -> dict[str, Any]:
        """마주 정보 조회 (API14_1)"""
        cache_key = f"owner_info:{owner_no}:{meet}"
        if use_cache:
            cached_data = await self._get_cached(cache_key)
            if cached_data:
                return cached_data
        params = {
            "ow_no": owner_no,
            "meet": meet,
            "numOfRows": 10,
            "pageNo": 1,
            "_type": "json",
        }
        result = await self._make_request(
            endpoint="API14_1/horseOwnerInfo_1", params=params
        )
        if use_cache:
            await self._set_cached(cache_key, result, ttl=86400)
        return result

    async def get_training_status(
        self, training_date: str, use_cache: bool = True
    ) -> dict[str, Any]:
        """서울 출발 조교 현황 조회 (API329)"""
        cache_key = f"training_status:{training_date}"
        if use_cache:
            cached_data = await self._get_cached(cache_key)
            if cached_data:
                return cached_data
        params = {
            "trng_dt": training_date,
            "numOfRows": 500,
            "pageNo": 1,
            "_type": "json",
        }
        result = await self._make_request(
            endpoint="API329/textDataSeGtscol", params=params
        )
        if use_cache:
            await self._set_cached(cache_key, result, ttl=21600)
        return result
```

- [ ] **Step 4: 테스트 실행 → 통과 확인**

- [ ] **Step 5: 커밋**

```bash
git add apps/api/services/kra_api_service.py apps/api/tests/unit/test_kra_api_new_endpoints.py
git commit -m "feat: add jockey stats, owner info, training status API methods"
```

---

## Task 3: KRAAPIService에 배당률 API 메서드 추가

**Files:**
- Modify: `apps/api/services/kra_api_service.py`
- Modify: `apps/api/tests/unit/test_kra_api_new_endpoints.py`

API160_1(확정배당율 통합), API301(확정배당율종합) 2개 메서드 추가. 배당률은 캐시 없음.

- [ ] **Step 1: 테스트 추가**

```python
class TestGetFinalOdds:
    @pytest.mark.asyncio
    async def test_returns_items(self, kra_service):
        kra_service._make_request.return_value = _make_api_response(
            [{"chulNo": 1, "odds": 5.0, "pool": "단승식", "rcNo": 1}]
        )
        result = await kra_service.get_final_odds("20260315", "1", pool="WIN")
        items = result["response"]["body"]["items"]["item"]
        assert items[0]["odds"] == 5.0

    @pytest.mark.asyncio
    async def test_no_cache(self, kra_service):
        kra_service._make_request.return_value = _make_api_response([{}])
        await kra_service.get_final_odds("20260315", "1")
        kra_service._get_cached.assert_not_called()
        kra_service._set_cached.assert_not_called()


class TestGetFinalOddsTotal:
    @pytest.mark.asyncio
    async def test_returns_items(self, kra_service):
        kra_service._make_request.return_value = _make_api_response(
            [{"chulNo": 5, "chulNo2": 1, "chulNo3": 11, "odds": 9999.9, "pool": "TRI"}]
        )
        result = await kra_service.get_final_odds_total("20260315", "1")
        items = result["response"]["body"]["items"]["item"]
        assert items[0]["pool"] == "TRI"

    @pytest.mark.asyncio
    async def test_no_cache(self, kra_service):
        kra_service._make_request.return_value = _make_api_response([{}])
        await kra_service.get_final_odds_total("20260315", "1")
        kra_service._get_cached.assert_not_called()
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

- [ ] **Step 3: 2개 메서드 구현**

```python
    async def get_final_odds(
        self, race_date: str, meet: str, pool: str | None = None,
        race_no: int | None = None,
    ) -> dict[str, Any]:
        """확정 배당률 통합 정보 조회 (API160_1) - 캐시 없음"""
        params: dict[str, Any] = {
            "meet": meet,
            "rc_date": race_date,
            "numOfRows": 1000,
            "pageNo": 1,
            "_type": "json",
        }
        if pool:
            params["pool"] = pool
        if race_no:
            params["rc_no"] = race_no
        return await self._make_request(
            endpoint="API160_1/integratedInfo_1", params=params
        )

    async def get_final_odds_total(
        self, race_date: str, meet: str, pool: str | None = None,
        race_no: int | None = None,
    ) -> dict[str, Any]:
        """경마시행당일 확정배당율종합 조회 (API301) - 캐시 없음"""
        params: dict[str, Any] = {
            "meet": meet,
            "rc_date": race_date,
            "numOfRows": 1000,
            "pageNo": 1,
            "_type": "json",
        }
        if pool:
            params["pool"] = pool
        if race_no:
            params["rc_no"] = race_no
        return await self._make_request(
            endpoint="API301/Dividend_rate_total", params=params
        )
```

참고: API301은 파라미터 키가 `serviceKey`가 아닌 소문자일 수 있음. `_make_request`가 `serviceKey`로 자동 추가하므로, 테스트 시 실제 호출 확인 필요.

- [ ] **Step 4: 테스트 실행 → 통과 확인**

- [ ] **Step 5: 커밋**

```bash
git add apps/api/services/kra_api_service.py apps/api/tests/unit/test_kra_api_new_endpoints.py
git commit -m "feat: add final odds API methods (API160_1, API301)"
```

---

## Task 4: RaceOdds 데이터베이스 모델 추가

**Files:**
- Modify: `apps/api/models/database_models.py`
- Test: `apps/api/tests/unit/test_race_odds_model.py`

- [ ] **Step 1: 테스트 파일 생성**

```python
# apps/api/tests/unit/test_race_odds_model.py
"""RaceOdds 모델 단위 테스트"""
from models.database_models import RaceOdds


class TestRaceOddsModel:
    def test_tablename(self):
        assert RaceOdds.__tablename__ == "race_odds"

    def test_has_required_columns(self):
        cols = {c.name for c in RaceOdds.__table__.columns}
        required = {"id", "race_id", "pool", "chul_no", "chul_no2", "chul_no3",
                     "odds", "rc_date", "source", "collected_at"}
        assert required.issubset(cols)

    def test_race_id_fk(self):
        col = RaceOdds.__table__.columns["race_id"]
        fk_targets = [fk.target_fullname for fk in col.foreign_keys]
        assert "races.race_id" in fk_targets

    def test_has_unique_constraint(self):
        constraints = [c for c in RaceOdds.__table__.constraints
                       if hasattr(c, "columns") and len(c.columns) > 1]
        unique_col_names = set()
        for c in constraints:
            unique_col_names.update(col.name for col in c.columns)
        assert "race_id" in unique_col_names
        assert "pool" in unique_col_names
        assert "source" in unique_col_names
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

- [ ] **Step 3: RaceOdds 모델 구현**

`apps/api/models/database_models.py` 끝에 추가:

```python
from sqlalchemy import Numeric, UniqueConstraint


class RaceOdds(Base):
    """배당률 데이터 모델 (API160_1 + API301)"""

    __tablename__ = "race_odds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    race_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("races.race_id", ondelete="CASCADE"), nullable=False
    )
    pool: Mapped[str] = mapped_column(String(10), nullable=False)
    chul_no: Mapped[int] = mapped_column(Integer, nullable=False)
    chul_no2: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    chul_no3: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    odds: Mapped[float] = mapped_column(Numeric(10, 1), nullable=False)
    rc_date: Mapped[str] = mapped_column(String(8), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    collected_at: Mapped[datetime | None] = mapped_column(
        DateTime, server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "race_id", "pool", "chul_no", "chul_no2", "chul_no3", "source",
            name="uq_race_odds_entry"
        ),
        Index("idx_race_odds_race_pool", "race_id", "pool"),
        Index("idx_race_odds_date_pool_source", "rc_date", "pool", "source"),
    )
```

참고: `Numeric` import 추가 필요, `UniqueConstraint` import 추가 필요.

- [ ] **Step 4: 테스트 실행 → 통과 확인**

- [ ] **Step 5: 커밋**

```bash
git add apps/api/models/database_models.py apps/api/tests/unit/test_race_odds_model.py
git commit -m "feat: add RaceOdds database model"
```

---

## Task 5: CollectionService에 경주 단위 데이터 통합

**Files:**
- Modify: `apps/api/services/collection_service.py`
- Test: `apps/api/tests/unit/test_collection_new_apis.py`

collect_race_data 흐름에 API72_2(race_plan), API189_1(track), API9_1(cancelled_horses) 통합.

- [ ] **Step 1: 테스트 파일 생성**

```python
# apps/api/tests/unit/test_collection_new_apis.py
"""신규 API 통합 수집 테스트"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from services.collection_service import CollectionService


def _make_api_response(items):
    return {
        "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE."},
            "body": {
                "items": {"item": items if isinstance(items, list) else [items]},
                "numOfRows": 1, "pageNo": 1, "totalCount": 1,
            },
        }
    }


@pytest.fixture
def mock_kra_api():
    api = MagicMock()
    # 기존 API 메서드들
    api.get_race_info = AsyncMock(return_value=_make_api_response([
        {"hrNo": "001", "hrName": "테스트마", "chulNo": 1, "winOdds": 5.0,
         "jkNo": "J01", "jkName": "기수1", "trNo": "T01", "trName": "조교사1", "ord": 1}
    ]))
    api.get_horse_info = AsyncMock(return_value=_make_api_response(
        {"hrNo": "001", "rcCntT": 10}
    ))
    api.get_jockey_info = AsyncMock(return_value=_make_api_response(
        {"jkNo": "J01", "winRateT": "10.0"}
    ))
    api.get_trainer_info = AsyncMock(return_value=_make_api_response(
        {"trNo": "T01", "winRateT": 15.0}
    ))
    # 신규 API 메서드들
    api.get_race_plan = AsyncMock(return_value=_make_api_response([
        {"rcNo": 1, "rank": "국6등급", "rcDist": 1200, "schStTime": 1035,
         "budam": "별정A", "chaksun1": 16500000, "ageCond": "연령오픈", "sexCond": "성별오픈"}
    ]))
    api.get_track_info = AsyncMock(return_value=_make_api_response([
        {"rcNo": 1, "weather": "맑음", "track": "건조", "waterPercent": 3}
    ]))
    api.get_cancelled_horses = AsyncMock(return_value=_make_api_response([]))
    api.get_jockey_stats = AsyncMock(return_value=_make_api_response(
        {"jkNo": "J01", "winRateT": 9.3, "qnlRateT": 18.8}
    ))
    api.get_owner_info = AsyncMock(return_value=_make_api_response(
        {"owNo": 110034, "owName": "(주)나스카", "ord1CntT": 205}
    ))
    api.get_training_status = AsyncMock(return_value=_make_api_response([
        {"hrnm": "테스트마", "remkTxt": "양호", "trngDt": 20260313}
    ]))
    return api


class TestCollectRaceDataWithNewAPIs:
    @pytest.mark.asyncio
    async def test_basic_data_includes_race_plan(self, mock_kra_api):
        service = CollectionService(mock_kra_api)
        db = AsyncMock()
        # _save_race_data를 모킹하여 저장된 데이터 캡처
        saved_data = {}
        async def capture_save(data, session):
            saved_data.update(data)
        service._save_race_data = capture_save

        await service.collect_race_data("20260315", 1, 1, db)

        assert "race_plan" in saved_data
        assert saved_data["race_plan"]["rank"] == "국6등급"

    @pytest.mark.asyncio
    async def test_basic_data_includes_track(self, mock_kra_api):
        service = CollectionService(mock_kra_api)
        db = AsyncMock()
        saved_data = {}
        async def capture_save(data, session):
            saved_data.update(data)
        service._save_race_data = capture_save

        await service.collect_race_data("20260315", 1, 1, db)

        assert "track" in saved_data
        assert saved_data["track"]["weather"] == "맑음"

    @pytest.mark.asyncio
    async def test_basic_data_includes_cancelled_horses(self, mock_kra_api):
        mock_kra_api.get_cancelled_horses.return_value = _make_api_response([
            {"chulNo": 2, "hrName": "취소마", "reason": "마체이상", "rcNo": 1}
        ])
        service = CollectionService(mock_kra_api)
        db = AsyncMock()
        saved_data = {}
        async def capture_save(data, session):
            saved_data.update(data)
        service._save_race_data = capture_save

        await service.collect_race_data("20260315", 1, 1, db)

        assert "cancelled_horses" in saved_data
        assert len(saved_data["cancelled_horses"]) == 1

    @pytest.mark.asyncio
    async def test_horse_includes_jk_stats(self, mock_kra_api):
        service = CollectionService(mock_kra_api)
        db = AsyncMock()
        saved_data = {}
        async def capture_save(data, session):
            saved_data.update(data)
        service._save_race_data = capture_save

        await service.collect_race_data("20260315", 1, 1, db)

        horse = saved_data["horses"][0]
        assert "jkStats" in horse
        assert horse["jkStats"]["qnlRateT"] == 18.8

    @pytest.mark.asyncio
    async def test_horse_includes_ow_detail(self, mock_kra_api):
        service = CollectionService(mock_kra_api)
        db = AsyncMock()
        saved_data = {}
        async def capture_save(data, session):
            saved_data.update(data)
        service._save_race_data = capture_save

        await service.collect_race_data("20260315", 1, 1, db)

        horse = saved_data["horses"][0]
        assert "owDetail" in horse
        assert horse["owDetail"]["owName"] == "(주)나스카"
```

- [ ] **Step 2: 테스트 실행 → 실패 확인**

- [ ] **Step 3: collect_race_data에 경주 단위 API 통합**

`collection_service.py`의 `collect_race_data` 메서드에서, `# 날씨 정보 수집` 부분을 대체:

```python
            # === 신규 경주 단위 API 수집 ===
            # 경주 계획표 (API72_2)
            race_plan_data = {}
            try:
                race_plan_response = await self.kra_api.get_race_plan(race_date, str(meet))
                if KRAResponseAdapter.is_successful_response(race_plan_response):
                    plans = KRAResponseAdapter.extract_items(race_plan_response)
                    for plan in plans:
                        if plan.get("rcNo") == race_no:
                            race_plan_data = convert_api_to_internal(plan)
                            break
            except Exception as e:
                logger.warning("Failed to get race plan", error=str(e))

            # 경주로 정보 (API189_1)
            track_data = {}
            try:
                track_response = await self.kra_api.get_track_info(race_date, str(meet))
                if KRAResponseAdapter.is_successful_response(track_response):
                    tracks = KRAResponseAdapter.extract_items(track_response)
                    for t in tracks:
                        if t.get("rcNo") == race_no:
                            track_data = convert_api_to_internal(t)
                            break
            except Exception as e:
                logger.warning("Failed to get track info", error=str(e))

            # 출전 취소 정보 (API9_1)
            cancelled_horses_data = []
            try:
                cancel_response = await self.kra_api.get_cancelled_horses(race_date, str(meet))
                if KRAResponseAdapter.is_successful_response(cancel_response):
                    cancels = KRAResponseAdapter.extract_items(cancel_response)
                    cancelled_horses_data = [
                        convert_api_to_internal(c) for c in cancels
                        if c.get("rcNo") == race_no
                    ]
            except Exception as e:
                logger.warning("Failed to get cancelled horses", error=str(e))

            # 조교 현황 (API329) - 경주 전날~당일 기준
            training_map = {}  # hrName -> training data
            try:
                training_response = await self.kra_api.get_training_status(race_date)
                if KRAResponseAdapter.is_successful_response(training_response):
                    trainings = KRAResponseAdapter.extract_items(training_response)
                    for tr in trainings:
                        hr_name = tr.get("hrnm", "")
                        if hr_name:
                            training_map[hr_name] = convert_api_to_internal(tr)
            except Exception as e:
                logger.warning("Failed to get training status", error=str(e))
```

그리고 `collected_data` 딕셔너리에 추가:

```python
            collected_data = {
                # ... 기존 필드들 ...
                "race_plan": race_plan_data,
                "track": track_data,
                "cancelled_horses": cancelled_horses_data,
                # ... 기존 필드들 ...
            }
```

- [ ] **Step 4: _collect_horse_details에 말 단위 API 통합**

`_collect_horse_details` 메서드에 추가 (trainer_info 수집 후):

```python
            # 기수 성적 (API11_1) → jkStats
            jockey_no = horse_basic.get("jk_no")
            if jockey_no:
                try:
                    jk_stats_info = await self.kra_api.get_jockey_stats(jockey_no)
                    if jk_stats_info and KRAResponseAdapter.is_successful_response(jk_stats_info):
                        jk_stats_item = KRAResponseAdapter.extract_single_item(jk_stats_info)
                        if jk_stats_item:
                            result["jkStats"] = convert_api_to_internal(jk_stats_item)
                except Exception as e:
                    logger.warning("Failed to get jockey stats", jockey_no=jockey_no, error=str(e))

            # 마주 정보 (API14_1) → owDetail
            # owNo는 API214_1 응답에 없을 수 있음 → hrDetail에서 추출 시도
            owner_no = horse_basic.get("ow_no")
            if not owner_no and "hrDetail" in result:
                owner_no = result["hrDetail"].get("ow_no")
            if owner_no:
                try:
                    owner_info = await self.kra_api.get_owner_info(str(owner_no))
                    if owner_info and KRAResponseAdapter.is_successful_response(owner_info):
                        owner_item = KRAResponseAdapter.extract_single_item(owner_info)
                        if owner_item:
                            result["owDetail"] = convert_api_to_internal(owner_item)
                except Exception as e:
                    logger.warning("Failed to get owner info", owner_no=owner_no, error=str(e))
```

training 매칭은 collect_race_data에서 training_map을 사용하여 수집 후 horse에 붙임:

```python
            # collect_race_data 내, horses_data 루프 후:
            # training 정보 매칭
            for horse_data in horses_data:
                hr_name = horse_data.get("hr_name", "")
                if hr_name in training_map:
                    horse_data["training"] = training_map[hr_name]
```

- [ ] **Step 5: 테스트 실행 → 통과 확인**

```bash
cd apps/api && uv run python3 -m pytest tests/unit/test_collection_new_apis.py -v
```

- [ ] **Step 6: 기존 테스트 회귀 확인**

```bash
cd apps/api && uv run python3 -m pytest tests/unit/test_collection_service.py -v
```

- [ ] **Step 7: 커밋**

```bash
git add apps/api/services/collection_service.py apps/api/tests/unit/test_collection_new_apis.py
git commit -m "feat: integrate new KRA APIs into collection pipeline"
```

---

## Task 6: 배당률 수집 메서드 (collect_race_odds)

**Files:**
- Modify: `apps/api/services/collection_service.py`
- Modify: `apps/api/tests/unit/test_collection_new_apis.py`

race_odds 테이블에 UPSERT하는 별도 메서드 추가.

- [ ] **Step 1: 테스트 추가**

```python
class TestCollectRaceOdds:
    @pytest.mark.asyncio
    async def test_upserts_odds_to_db(self, mock_kra_api):
        mock_kra_api.get_final_odds.return_value = _make_api_response([
            {"chulNo": 1, "chulNo2": 0, "chulNo3": 0, "odds": 5.0, "pool": "단승식",
             "rcDate": 20260315, "rcNo": 1},
        ])
        service = CollectionService(mock_kra_api)
        db = AsyncMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()

        result = await service.collect_race_odds("20260315", 1, 1, db, source="API160_1")

        assert result["inserted_count"] >= 0  # 구조 확인
        db.execute.assert_called()
```

- [ ] **Step 2: 구현**

`collection_service.py`에 `collect_race_odds` 메서드 추가:

```python
    async def collect_race_odds(
        self, race_date: str, meet: int, race_no: int,
        db: AsyncSession, source: str = "API160_1",
    ) -> dict[str, Any]:
        """배당률 데이터 수집 및 race_odds 테이블 UPSERT"""
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from models.database_models import RaceOdds

        race_id = f"{race_date}_{meet}_{race_no}"

        # API 호출
        if source == "API160_1":
            response = await self.kra_api.get_final_odds(race_date, str(meet), race_no=race_no)
        else:
            response = await self.kra_api.get_final_odds_total(race_date, str(meet), race_no=race_no)

        if not KRAResponseAdapter.is_successful_response(response):
            return {"race_id": race_id, "inserted_count": 0, "error": "API response failed"}

        items = KRAResponseAdapter.extract_items(response)
        # pool 이름 매핑 (한글 → 영문)
        pool_map = {
            "단승식": "WIN", "연승식": "PLC", "복승식": "QNL",
            "쌍승식": "EXA", "복연승식": "QPL", "삼복승식": "TLA",
            "삼쌍승식": "TRI", "쌍복승식": "XLA",
            "WIN": "WIN", "PLC": "PLC", "QNL": "QNL",
            "EXA": "EXA", "QPL": "QPL", "TLA": "TLA",
            "TRI": "TRI", "XLA": "XLA",
        }

        rows = []
        for item in items:
            pool_raw = item.get("pool", "")
            pool = pool_map.get(pool_raw, pool_raw)
            if pool not in ("WIN", "PLC", "QNL", "EXA", "QPL", "TLA", "TRI", "XLA"):
                continue
            rows.append({
                "race_id": race_id,
                "pool": pool,
                "chul_no": item.get("chulNo", 0),
                "chul_no2": item.get("chulNo2", 0),
                "chul_no3": item.get("chulNo3", 0),
                "odds": item.get("odds", 0),
                "rc_date": race_date,
                "source": source,
            })

        if rows:
            stmt = pg_insert(RaceOdds).values(rows)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_race_odds_entry",
                set_={"odds": stmt.excluded.odds, "collected_at": func.now()},
            )
            await db.execute(stmt)
            await db.commit()

        return {"race_id": race_id, "inserted_count": len(rows), "source": source}
```

- [ ] **Step 3: 테스트 실행 → 통과 확인**

- [ ] **Step 4: 커밋**

```bash
git add apps/api/services/collection_service.py apps/api/tests/unit/test_collection_new_apis.py
git commit -m "feat: add collect_race_odds method with UPSERT"
```

---

## Task 7: 전체 테스트 + 실제 API 호출 검증

**Files:** 없음 (기존 테스트 실행만)

- [ ] **Step 1: 전체 단위 테스트 실행**

```bash
cd apps/api && uv run python3 -m pytest tests/ -v --tb=short 2>&1 | tail -20
```

- [ ] **Step 2: 실제 API 1건 호출로 통합 검증 (선택)**

기존에 테스트한 curl 명령어로 각 API 응답 구조가 코드에서 기대하는 형태와 일치하는지 확인.

- [ ] **Step 3: 최종 커밋**

```bash
git add -A
git commit -m "feat: integrate 8 new KRA APIs into collection pipeline

- API189_1 (track), API72_2 (race plan), API9_1 (cancellations) → basic_data
- API11_1 (jockey stats) → jkStats, API14_1 (owner) → owDetail, API329 (training) → training
- API160_1 + API301 → race_odds table with UPSERT
- Migration: 003_add_race_odds.sql"
```
