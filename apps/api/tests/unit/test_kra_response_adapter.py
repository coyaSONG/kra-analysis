"""
Tests for KRA Response Adapter
"""

from adapters.kra_response_adapter import KRAResponseAdapter


class TestKRAResponseAdapter:
    """Test KRA Response Adapter functionality"""

    def test_extract_items_successful_response(self):
        """extract_items should return items from successful KRA API response"""
        api_response = {
            "response": {
                "body": {
                    "items": {
                        "item": [
                            {"hrNo": "001", "hrName": "Test Horse 1"},
                            {"hrNo": "002", "hrName": "Test Horse 2"},
                        ]
                    }
                }
            }
        }

        items = KRAResponseAdapter.extract_items(api_response)
        assert len(items) == 2
        assert items[0]["hrNo"] == "001"
        assert items[1]["hrNo"] == "002"

    def test_extract_items_single_item(self):
        """extract_items should normalize single item to list"""
        api_response = {
            "response": {
                "body": {"items": {"item": {"hrNo": "001", "hrName": "Test Horse"}}}
            }
        }

        items = KRAResponseAdapter.extract_items(api_response)
        assert len(items) == 1
        assert items[0]["hrNo"] == "001"

    def test_extract_items_empty_response(self):
        """extract_items should return empty list for empty response"""
        test_cases = [
            {},
            {"response": {}},
            {"response": {"body": {}}},
            {"response": {"body": {"items": {}}}},
            None,
        ]

        for api_response in test_cases:
            items = KRAResponseAdapter.extract_items(api_response)
            assert items == []

    def test_extract_single_item_success(self):
        """extract_single_item should return first item"""
        api_response = {
            "response": {
                "body": {
                    "items": {
                        "item": [
                            {"hrNo": "001", "hrName": "First Horse"},
                            {"hrNo": "002", "hrName": "Second Horse"},
                        ]
                    }
                }
            }
        }

        item = KRAResponseAdapter.extract_single_item(api_response)
        assert item is not None
        assert item["hrNo"] == "001"

    def test_extract_single_item_empty(self):
        """extract_single_item should return None for empty response"""
        item = KRAResponseAdapter.extract_single_item({})
        assert item is None

    def test_normalize_race_info(self):
        """normalize_race_info should properly normalize race response"""
        api_response = {
            "response": {
                "body": {
                    "items": {
                        "item": [
                            {"hrNo": "001", "hrName": "Horse 1"},
                            {"hrNo": "002", "hrName": "Horse 2"},
                        ]
                    }
                }
            }
        }

        normalized = KRAResponseAdapter.normalize_race_info(api_response)
        assert normalized["horse_count"] == 2
        assert normalized["has_data"] is True
        assert len(normalized["horses"]) == 2

    def test_normalize_horse_info(self):
        """normalize_horse_info should properly normalize horse response"""
        api_response = {
            "response": {
                "body": {
                    "items": {
                        "item": {
                            "hrNo": "001",
                            "hrName": "Test Horse",
                            "win_rate_t": "15.5",
                            "place_rate_t": "35.2",
                        }
                    }
                }
            }
        }

        normalized = KRAResponseAdapter.normalize_horse_info(api_response)
        assert normalized is not None
        assert normalized["hr_no"] == "001"
        assert normalized["hr_name"] == "Test Horse"
        assert normalized["win_rate"] == 15.5
        assert normalized["place_rate"] == 35.2
        assert "raw_data" in normalized

    def test_normalize_jockey_info(self):
        """normalize_jockey_info should properly normalize jockey response"""
        api_response = {
            "response": {
                "body": {
                    "items": {
                        "item": {
                            "jkNo": "J001",
                            "jkName": "Test Jockey",
                            "win_rate_t": "20.0",
                            "rc_cnt_t": "100",
                            "win_cnt_t": "20",
                        }
                    }
                }
            }
        }

        normalized = KRAResponseAdapter.normalize_jockey_info(api_response)
        assert normalized is not None
        assert normalized["jk_no"] == "J001"
        assert normalized["jk_name"] == "Test Jockey"
        assert normalized["win_rate"] == 20.0
        assert normalized["race_count"] == 100
        assert normalized["win_count"] == 20

    def test_normalize_trainer_info(self):
        """normalize_trainer_info should properly normalize trainer response"""
        api_response = {
            "response": {
                "body": {
                    "items": {
                        "item": {
                            "trNo": "T001",
                            "trName": "Test Trainer",
                            "win_rate_t": "18.5",
                            "rc_cnt_t": "150",
                            "win_cnt_t": "28",
                        }
                    }
                }
            }
        }

        normalized = KRAResponseAdapter.normalize_trainer_info(api_response)
        assert normalized is not None
        assert normalized["tr_no"] == "T001"
        assert normalized["tr_name"] == "Test Trainer"
        assert normalized["win_rate"] == 18.5
        assert normalized["race_count"] == 150
        assert normalized["win_count"] == 28

    def test_is_successful_response(self):
        """is_successful_response should correctly identify successful responses"""
        successful_response = {
            "response": {
                "header": {"resultCode": "00"},
                "body": {"items": {"item": []}},
            }
        }

        unsuccessful_response = {
            "response": {
                "header": {"resultCode": "99", "resultMessage": "Error"},
                "body": {},
            }
        }

        empty_response = {}

        assert KRAResponseAdapter.is_successful_response(successful_response) is True
        assert KRAResponseAdapter.is_successful_response(unsuccessful_response) is False
        assert KRAResponseAdapter.is_successful_response(empty_response) is False

    def test_get_error_message(self):
        """get_error_message should extract error messages properly"""
        error_response = {
            "response": {
                "header": {"resultCode": "99", "resultMessage": "Invalid parameters"}
            }
        }

        empty_response = {}

        error_msg = KRAResponseAdapter.get_error_message(error_response)
        assert error_msg == "Invalid parameters"

        error_msg = KRAResponseAdapter.get_error_message(empty_response)
        assert "Empty API response" in error_msg

    def test_safe_conversions(self):
        """_safe_float and _safe_int should handle edge cases"""
        # Test _safe_float
        assert KRAResponseAdapter._safe_float("12.5") == 12.5
        assert KRAResponseAdapter._safe_float("invalid") == 0.0
        assert KRAResponseAdapter._safe_float(None) == 0.0
        assert KRAResponseAdapter._safe_float("") == 0.0

        # Test _safe_int
        assert KRAResponseAdapter._safe_int("10") == 10
        assert KRAResponseAdapter._safe_int("10.5") == 10
        assert KRAResponseAdapter._safe_int("invalid") == 0
        assert KRAResponseAdapter._safe_int(None) == 0
        assert KRAResponseAdapter._safe_int("") == 0
