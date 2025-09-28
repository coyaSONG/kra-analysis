"""
Unit tests for collection service
"""

from unittest.mock import AsyncMock, Mock

import pytest

from models.database_models import DataStatus, Race
from services.collection_service import CollectionService
from services.kra_api_service import KRAAPIService


class TestCollectionService:
    """Test collection service functionality"""

    @pytest.fixture
    def mock_kra_api_service(self):
        """Create mock KRA API service"""
        mock = Mock(spec=KRAAPIService)
        mock.get_race_info = AsyncMock()
        mock.get_horse_info = AsyncMock()
        mock.get_jockey_info = AsyncMock()
        mock.get_trainer_info = AsyncMock()
        return mock

    @pytest.fixture
    def collection_service(self, mock_kra_api_service):
        """Create collection service with mocked dependencies"""
        return CollectionService(mock_kra_api_service)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collect_horse_details_enriches_fields(
        self, collection_service, mock_kra_api_service
    ):
        """_collect_horse_details should add hrDetail/jkDetail/trDetail when API returns structured data."""
        mock_kra_api_service.get_horse_info.return_value = {
            "response": {
                "body": {"items": {"item": [{"hrNo": "001", "win_rate_t": "12.5"}]}}
            }
        }
        mock_kra_api_service.get_jockey_info.return_value = {
            "response": {"body": {"items": {"item": {"jkNo": "J001", "rc_cnt_t": 10}}}}
        }
        mock_kra_api_service.get_trainer_info.return_value = {
            "response": {
                "body": {"items": {"item": {"trNo": "T001", "win_rate_t": "15.0"}}}
            }
        }

        horse_basic = {"hr_no": "001", "jk_no": "J001", "tr_no": "T001"}
        result = await collection_service._collect_horse_details(horse_basic)
        assert result.get("hrDetail") is not None
        assert result.get("jkDetail") is not None
        assert result.get("trDetail") is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_save_race_data_updates_existing(
        self, collection_service, db_session
    ):
        """_save_race_data should update existing race instead of inserting new one."""
        # Insert initial race
        from models.database_models import DataStatus, Race

        race = Race(
            race_id="20240719_1_1",
            date="20240719",
            meet=1,
            race_number=1,
            basic_data={"date": "20240719", "meet": 1, "race_number": 1},
            collection_status=DataStatus.COLLECTED,
        )
        db_session.add(race)
        await db_session.commit()

        # Update with new data
        data = {
            "date": "20240719",
            "meet": 1,
            "race_number": 1,
            "horses": [],
        }
        await collection_service._save_race_data(data, db_session)

        updated = await db_session.execute(
            "SELECT * FROM races WHERE date = '20240719' AND meet = 1 AND race_number = 1"
        )
        assert updated.first() is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_horse_past_performances(self, collection_service, db_session):
        from models.database_models import DataStatus, Race

        # Create two past races within 3 months window
        for d in ("20240701", "20240710"):
            race = Race(
                date=d,
                meet=1,
                race_number=1,
                result_status=DataStatus.COLLECTED,
                result_data={
                    "horses": [
                        {
                            "hr_no": "001",
                            "ord": 2,
                            "win_odds": 5.0,
                            "rating": 80,
                            "weight": 480,
                        }
                    ]
                },
            )
            db_session.add(race)
        await db_session.commit()

        perfs = await collection_service._get_horse_past_performances(
            "001", "20240719", db_session
        )
        assert len(perfs) >= 2
        assert perfs[0]["race_no"] == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_jockey_trainer_stats_fallbacks(
        self, collection_service, mock_kra_api_service, db_session
    ):
        # No data from API --> default fallbacks
        mock_kra_api_service.get_jockey_info.return_value = None
        mock_kra_api_service.get_trainer_info.return_value = None
        jk = await collection_service._get_jockey_stats("J001", "20240719", db_session)
        tr = await collection_service._get_trainer_stats("T001", "20240719", db_session)
        assert 0 <= jk["recent_win_rate"] <= 1
        assert 0 <= tr["plc_rate"] <= 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_enrich_data_with_past_performances(
        self, collection_service, db_session, monkeypatch
    ):
        """_enrich_data should include past_stats when past performances exist."""
        # Patch methods to control behavior
        from unittest.mock import AsyncMock

        collection_service._get_horse_past_performances = AsyncMock(
            return_value=[
                {"position": 1, "date": "20240701"},
                {"position": 3, "date": "20240708"},
            ]
        )
        collection_service._get_jockey_stats = AsyncMock(
            return_value={
                "recent_win_rate": 0.2,
                "career_win_rate": 0.15,
                "total_wins": 10,
                "total_races": 50,
                "recent_races": 10,
            }
        )
        collection_service._get_trainer_stats = AsyncMock(
            return_value={
                "recent_win_rate": 0.18,
                "career_win_rate": 0.12,
                "total_wins": 20,
                "total_races": 100,
                "recent_races": 20,
                "plc_rate": 0.3,
                "meet": "SEOUL",
            }
        )

        data = {
            "date": "20240719",
            "meet": 1,
            "horses": [{"hr_no": "001", "jk_no": "J001", "tr_no": "T001"}],
        }
        result = await collection_service._enrich_data(data, db_session)
        assert result["horses"][0]["past_stats"]["total_races"] == 2
        assert "jockey_stats" in result["horses"][0]
        assert "trainer_stats" in result["horses"][0]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collect_race_data_success(
        self, collection_service, mock_kra_api_service, db_session
    ):
        """Test successful race data collection"""
        # Setup mock response
        mock_kra_api_service.get_race_info.return_value = {
            "response": {
                "body": {
                    "items": {
                        "item": [
                            {
                                "hrNo": "001",
                                "hrName": "Test Horse 1",
                                "jkNo": "J001",
                                "trNo": "T001",
                                "win_odds": "5.5",
                                "weight": "500",
                                "rating": "85",
                            },
                            {
                                "hrNo": "002",
                                "hrName": "Test Horse 2",
                                "jkNo": "J002",
                                "trNo": "T002",
                                "win_odds": "10.0",
                                "weight": "480",
                                "rating": "82",
                            },
                        ]
                    }
                }
            }
        }

        mock_kra_api_service.get_horse_info.return_value = {"name": "Test Horse"}
        mock_kra_api_service.get_jockey_info.return_value = {"name": "Test Jockey"}
        mock_kra_api_service.get_trainer_info.return_value = {"name": "Test Trainer"}

        # Execute
        result = await collection_service.collect_race_data(
            race_date="20240719", meet=1, race_no=1, db=db_session
        )

        # Assert
        assert result is not None
        assert result["race_date"] == "20240719"
        assert result["meet"] == 1
        assert result["race_no"] == 1
        assert len(result["horses"]) == 2
        assert "collected_at" in result

        # Verify API calls
        mock_kra_api_service.get_race_info.assert_called_once_with("20240719", "1", 1)
        assert mock_kra_api_service.get_horse_info.call_count == 2
        assert mock_kra_api_service.get_jockey_info.call_count == 2
        assert mock_kra_api_service.get_trainer_info.call_count == 2

        # Verify database save
        saved_race = await db_session.execute(
            "SELECT * FROM races WHERE date = '20240719' AND meet = 1 AND race_number = 1"
        )
        race = saved_race.first()
        assert race is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collect_race_data_api_error(
        self, collection_service, mock_kra_api_service, db_session
    ):
        """Test race data collection with API error"""
        # Setup mock to raise error
        mock_kra_api_service.get_race_info.side_effect = Exception("API Error")

        # Execute and expect error
        with pytest.raises(Exception) as exc_info:
            await collection_service.collect_race_data(
                race_date="20240719", meet=1, race_no=1, db=db_session
            )

        assert "API Error" in str(exc_info.value)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_preprocess_data_filtering(self, collection_service):
        """Test data preprocessing with horse filtering"""
        # Test data with mixed win_odds values
        raw_data = {
            "horses": [
                {"hrNo": "001", "win_odds": "5.5", "weight": "500", "rating": "85"},
                {
                    "hrNo": "002",
                    "win_odds": "0",
                    "weight": "480",
                    "rating": "82",
                },  # Excluded
                {"hrNo": "003", "win_odds": "10.0", "weight": "490", "rating": "80"},
                {
                    "hrNo": "004",
                    "win_odds": None,
                    "weight": "485",
                    "rating": "81",
                },  # Excluded
                {
                    "hrNo": "005",
                    "win_odds": "invalid",
                    "weight": "495",
                    "rating": "83",
                },  # Excluded
            ]
        }

        # Execute
        result = await collection_service._preprocess_data(raw_data)

        # Assert
        assert len(result["horses"]) == 2  # Only horses with valid win_odds > 0
        assert result["excluded_horses"] == 3
        assert all(float(h.get("win_odds", 0)) > 0 for h in result["horses"])

        # Check calculated statistics
        assert "statistics" in result
        stats = result["statistics"]
        assert stats["avg_weight"] > 0
        assert stats["avg_rating"] > 0
        assert stats["avg_win_odds"] > 0

        # Check ratios calculated for active horses
        for horse in result["horses"]:
            assert "weight_ratio" in horse
            assert "rating_ratio" in horse
            assert "odds_ratio" in horse

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_preprocess_data_empty_horses(self, collection_service):
        """Test preprocessing with no horses"""
        raw_data = {"horses": []}

        result = await collection_service._preprocess_data(raw_data)

        assert result["horses"] == []
        assert result["excluded_horses"] == 0
        assert result["statistics"]["avg_weight"] == 0
        assert result["statistics"]["avg_rating"] == 0
        assert result["statistics"]["avg_win_odds"] == 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_enrich_race_data(self, collection_service, db_session):
        """Test race data enrichment"""
        # Create test race
        race = Race(
            date="20240719",
            meet=1,
            race_number=1,
            raw_data={
                "horses": [
                    {"horse_no": "001", "jockey_no": "J001", "trainer_no": "T001"}
                ]
            },
            collection_status=DataStatus.COLLECTED,
        )
        db_session.add(race)
        await db_session.commit()

        # Mock past performance methods
        collection_service._get_horse_past_performances = AsyncMock(return_value=[])
        collection_service._get_jockey_stats = AsyncMock(
            return_value={
                "recent_win_rate": 0.15,
                "meet_win_rate": 0.12,
                "total_wins": 150,
            }
        )
        collection_service._get_trainer_stats = AsyncMock(
            return_value={
                "recent_win_rate": 0.18,
                "meet_win_rate": 0.16,
                "total_wins": 200,
            }
        )

        # Execute
        result = await collection_service.enrich_race_data(race.id, db_session)

        # Assert
        assert result is not None
        assert "enrichment_timestamp" in result
        assert len(result["horses"]) == 1

        horse = result["horses"][0]
        assert "past_stats" in horse
        assert "jockey_stats" in horse
        assert "trainer_stats" in horse
        assert horse["jockey_stats"]["recent_win_rate"] == 0.15
        assert horse["trainer_stats"]["total_wins"] == 200

    @pytest.mark.unit
    def test_calculate_performance_stats(self, collection_service):
        """Test performance statistics calculation"""
        performances = [
            {"position": 1, "date": "20240701"},
            {"position": 3, "date": "20240708"},
            {"position": 2, "date": "20240715"},
            {"position": 5, "date": "20240722"},
            {"position": 1, "date": "20240729"},
        ]

        stats = collection_service._calculate_performance_stats(performances)

        assert stats["total_races"] == 5
        assert stats["wins"] == 2
        assert stats["win_rate"] == 0.4
        assert stats["avg_position"] == 2.4
        assert stats["recent_form"] > 0

    @pytest.mark.unit
    def test_analyze_weather_impact(self, collection_service):
        """Test weather impact analysis"""
        # Good track condition
        weather = {"track_condition": "good"}
        impact = collection_service._analyze_weather_impact(weather)
        assert impact["track_speed_factor"] == 1.0
        assert impact["stamina_importance"] == 1.0
        assert impact["weight_impact"] == 1.0

        # Heavy track condition
        weather = {"track_condition": "heavy"}
        impact = collection_service._analyze_weather_impact(weather)
        assert impact["track_speed_factor"] == 0.95
        assert impact["stamina_importance"] == 1.2
        assert impact["weight_impact"] == 1.1

        # Firm track condition
        weather = {"track_condition": "firm"}
        impact = collection_service._analyze_weather_impact(weather)
        assert impact["track_speed_factor"] == 1.05
        assert impact["stamina_importance"] == 0.9
        assert impact["weight_impact"] == 1.0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_collect_batch_races(
        self, collection_service, mock_kra_api_service, db_session
    ):
        """Test batch race collection"""
        # Setup mock for multiple races
        mock_kra_api_service.get_race_info.return_value = {
            "response": {"body": {"items": {"item": []}}}
        }

        # Execute batch collection
        results = await collection_service.collect_batch_races(
            race_date="20240719", meet=1, race_numbers=[1, 2, 3], db=db_session
        )

        # Assert
        assert len(results) == 3
        assert all(race_number in results for race_number in [1, 2, 3])

        # Verify API calls
        assert mock_kra_api_service.get_race_info.call_count == 3
