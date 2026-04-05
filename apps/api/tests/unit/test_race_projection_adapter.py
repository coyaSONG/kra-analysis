from adapters.race_projection_adapter import RaceProjectionAdapter


def test_normalize_result_projection_accepts_top3_list():
    projection = RaceProjectionAdapter.normalize_result_projection([3, 1, 5])

    assert projection["top3"] == [3, 1, 5]
    assert [horse["chulNo"] for horse in projection["horses"]] == [3, 1, 5]


def test_normalize_result_projection_accepts_horses_dict():
    projection = RaceProjectionAdapter.normalize_result_projection(
        {
            "horses": [
                {"hr_no": "H001", "ord": 1, "win_odds": "5.5"},
                {"hrNo": "H002", "ord": 2, "rating": "80"},
            ]
        }
    )

    assert projection["top3"] == [1, 2]
    assert projection["horses"][0]["hr_no"] == "H001"
    assert projection["horses"][1]["rating"] == 80


def test_build_result_projection_preserves_result_items():
    projection = RaceProjectionAdapter.build_result_projection(
        [3, 1, 5],
        result_items=[
            {"chulNo": 3, "ord": 1, "hrName": "말A", "winOdds": "4.2"},
            {"chulNo": 1, "ord": 2, "hrName": "말B", "rating": "81"},
        ],
    )

    assert projection["source"] == "result_collection_service"
    assert projection["horses"][0]["hr_name"] == "말A"
    assert projection["horses"][0]["win_odds"] == 4.2
    assert projection["horses"][1]["rating"] == 81
