"""Physical API venues remain independent of verified PDF source profiles."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from shared.kra_race_card_pdf import parse_race_card_pdf, race_card_url
from shared.kra_race_identity import MEET_NAMES, validate_race_identity


@pytest.mark.parametrize("meet", [1, 2, 3, 4])
def test_physical_venues_accept_valid_race_identity(meet):
    validate_race_identity(meet, "20261011", 1)


@pytest.mark.parametrize("meet", [True, False, 0, 5, -1, 4.0, "4", None])
def test_unsupported_or_noninteger_venues_are_rejected(meet):
    with pytest.raises(ValueError, match="meet"):
        validate_race_identity(meet, "20261011", 1)


@pytest.mark.parametrize(
    "date", ["20260229", "20261301", "19991231", "21000101", "2026-10-11", 20261011]
)
def test_invalid_dates_are_rejected(date):
    with pytest.raises(ValueError):
        validate_race_identity(4, date, 1)


@pytest.mark.parametrize("number", [True, 0, 21, "1", 1.0, None])
def test_invalid_race_numbers_are_rejected(number):
    with pytest.raises(ValueError, match="race_no"):
        validate_race_identity(4, "20261011", number)


def test_venue_names_do_not_conflate_physical_venues_with_website_menu():
    assert MEET_NAMES["\uc601\ucc9c"] == 4
    assert MEET_NAMES["\ubd80\uacbd"] == 3
    assert "\uc601\ub0a8" not in MEET_NAMES


def test_api_venue_four_does_not_authorize_a_guessed_pdf_profile():
    with pytest.raises(ValueError, match="meet must be"):
        race_card_url(4, "20261011", 1)
    with pytest.raises(ValueError, match="meet must be"):
        parse_race_card_pdf(
            b"not a verified PDF", meet=4, race_date="20261011", race_no=1
        )


@pytest.mark.parametrize(
    "meet,directory,prefix", [(1, "seoul", "s"), (2, "jeju", "j"), (3, "busan", "b")]
)
def test_existing_pdf_urls_remain_canonical(meet, directory, prefix):
    assert race_card_url(meet, "20261011", 1) == (
        f"https://race.kra.co.kr/down/pdf/{directory}/chulma/"
        f"{prefix}_run_hr_261011_01.pdf"
    )
