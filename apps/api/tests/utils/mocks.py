"""
Mock utilities for testing
"""

from typing import Any
from unittest.mock import AsyncMock, Mock


class MockKRAAPIService:
    """Mock KRA API service for testing"""

    def __init__(self):
        self.get_race_info = AsyncMock()
        self.get_horse_info = AsyncMock()
        self.get_jockey_info = AsyncMock()
        self.get_trainer_info = AsyncMock()
        self.get_race_result = AsyncMock()

        # Set default responses
        self.set_default_responses()

    def set_default_responses(self):
        """Set default mock responses"""
        self.get_race_info.return_value = self._default_race_info()
        self.get_horse_info.return_value = self._default_horse_info()
        self.get_jockey_info.return_value = self._default_jockey_info()
        self.get_trainer_info.return_value = self._default_trainer_info()
        self.get_race_result.return_value = self._default_race_result()

    def _default_race_info(self) -> dict[str, Any]:
        """Default race info response"""
        return {
            "response": {
                "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
                "body": {
                    "items": {
                        "item": [
                            {
                                "rcDate": "20240719",
                                "meet": "1",
                                "rcNo": "1",
                                "hrNo": "001",
                                "hrName": "테스트말1",
                                "jkNo": "J001",
                                "jkName": "테스트기수1",
                                "trNo": "T001",
                                "trName": "테스트조교사1",
                                "win_odds": "5.5",
                                "weight": "500",
                                "rating": "85",
                                "age": "3",
                                "sex": "M",
                                "burden": "53",
                            },
                            {
                                "rcDate": "20240719",
                                "meet": "1",
                                "rcNo": "1",
                                "hrNo": "002",
                                "hrName": "테스트말2",
                                "jkNo": "J002",
                                "jkName": "테스트기수2",
                                "trNo": "T002",
                                "trName": "테스트조교사2",
                                "win_odds": "10.0",
                                "weight": "480",
                                "rating": "82",
                                "age": "4",
                                "sex": "F",
                                "burden": "51",
                            },
                        ]
                    },
                    "numOfRows": 2,
                    "pageNo": 1,
                    "totalCount": 2,
                },
            }
        }

    def _default_horse_info(self) -> dict[str, Any]:
        """Default horse info response"""
        return {
            "response": {
                "body": {
                    "item": {
                        "hrNo": "001",
                        "hrName": "테스트말1",
                        "birthDate": "20210315",
                        "sex": "M",
                        "color": "밤색",
                        "father": "부마명",
                        "mother": "모마명",
                        "trainer": "테스트조교사1",
                        "owner": "마주명",
                        "totalRaces": 20,
                        "totalWins": 5,
                        "totalSeconds": 3,
                        "totalThirds": 2,
                    }
                }
            }
        }

    def _default_jockey_info(self) -> dict[str, Any]:
        """Default jockey info response"""
        return {
            "response": {
                "body": {
                    "item": {
                        "jkNo": "J001",
                        "jkName": "테스트기수1",
                        "birthDate": "19900101",
                        "debut": "20100101",
                        "totalRaces": 1000,
                        "totalWins": 150,
                        "winRate": 0.15,
                        "placeRate": 0.35,
                    }
                }
            }
        }

    def _default_trainer_info(self) -> dict[str, Any]:
        """Default trainer info response"""
        return {
            "response": {
                "body": {
                    "item": {
                        "trNo": "T001",
                        "trName": "테스트조교사1",
                        "debut": "20000101",
                        "totalRaces": 2000,
                        "totalWins": 300,
                        "winRate": 0.15,
                        "placeRate": 0.40,
                    }
                }
            }
        }

    def _default_race_result(self) -> dict[str, Any]:
        """Default race result response"""
        return {
            "response": {
                "body": {
                    "items": {
                        "item": [
                            {"hrNo": "005", "ord": "1", "time": "1:23.5"},
                            {"hrNo": "002", "ord": "2", "time": "1:23.7"},
                            {"hrNo": "008", "ord": "3", "time": "1:23.9"},
                        ]
                    }
                }
            }
        }


class MockRedisClient:
    """Mock Redis client for testing"""

    def __init__(self):
        self._data = {}
        self.get = AsyncMock(side_effect=self._get)
        self.set = AsyncMock(side_effect=self._set)
        self.delete = AsyncMock(side_effect=self._delete)
        self.exists = AsyncMock(side_effect=self._exists)
        self.incr = AsyncMock(side_effect=self._incr)
        self.expire = AsyncMock(side_effect=self._expire)
        self.flushdb = AsyncMock(side_effect=self._flushdb)
        self.close = AsyncMock()

    async def _get(self, key: str) -> str | None:
        """Mock get operation"""
        return self._data.get(key)

    async def _set(self, key: str, value: str, ex: int | None = None) -> None:
        """Mock set operation"""
        self._data[key] = value

    async def _delete(self, key: str) -> None:
        """Mock delete operation"""
        self._data.pop(key, None)

    async def _exists(self, key: str) -> bool:
        """Mock exists operation"""
        return key in self._data

    async def _incr(self, key: str) -> int:
        """Mock increment operation"""
        current = int(self._data.get(key, 0))
        self._data[key] = str(current + 1)
        return current + 1

    async def _expire(self, key: str, seconds: int) -> None:
        """Mock expire operation (no-op for testing)"""
        pass

    async def _flushdb(self) -> None:
        """Mock flush database operation"""
        self._data.clear()

    # Additional methods used by APIKeyRateLimiter
    async def ttl(self, key: str) -> int:
        """Return remaining TTL; mock as full window when not tracked"""
        # Not tracking real TTL; return a positive number to simulate active key
        return 60


class MockCeleryTask:
    """Mock Celery task for testing"""

    def __init__(self, task_id: str = "test-task-id"):
        self.id = task_id
        self.status = "PENDING"
        self.result = None
        self.info = {}

    def get(self, timeout: int | None = None):
        """Mock get result"""
        if self.status == "SUCCESS":
            return self.result
        elif self.status == "FAILURE":
            raise Exception("Task failed")
        return None

    @property
    def state(self):
        """Get task state"""
        return self.status


def create_mock_celery_app():
    """Create mock Celery app"""
    mock_app = Mock()
    mock_app.send_task = Mock(return_value=MockCeleryTask())
    return mock_app
