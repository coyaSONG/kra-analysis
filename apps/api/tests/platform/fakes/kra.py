"""
Reusable fake KRA service for tests.
"""

from typing import Any


class MockKRAAPIService:
    """Mock KRA API service for testing."""

    def __init__(self):
        self._responses: dict[str, Any] = {}
        self.set_default_responses()

    def set_default_responses(self):
        """Reset fake methods to default success responses."""
        self._responses = {
            "race_info": self._default_race_info(),
            "horse_info": self._default_horse_info(),
            "jockey_info": self._default_jockey_info(),
            "trainer_info": self._default_trainer_info(),
            "race_result": self._default_race_result(),
        }

    def set_response(self, name: str, value: Any) -> None:
        self._responses[name] = value

    async def get_race_info(self, *args, **kwargs):
        return self._responses["race_info"]

    async def get_horse_info(self, *args, **kwargs):
        return self._responses["horse_info"]

    async def get_jockey_info(self, *args, **kwargs):
        return self._responses["jockey_info"]

    async def get_trainer_info(self, *args, **kwargs):
        return self._responses["trainer_info"]

    async def get_race_result(self, *args, **kwargs):
        return self._responses["race_result"]

    def _default_race_info(self) -> dict[str, Any]:
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
