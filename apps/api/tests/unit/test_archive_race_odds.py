from datetime import date

import pytest

from scripts import archive_race_odds


@pytest.mark.unit
def test_resolve_cutoff_accepts_explicit_before_date():
    assert archive_race_odds.resolve_cutoff("20260101", None) == "20260101"


@pytest.mark.unit
def test_resolve_cutoff_rejects_ambiguous_cutoff_options():
    with pytest.raises(ValueError, match="either --before or --keep-months"):
        archive_race_odds.resolve_cutoff("20260101", 6)


@pytest.mark.unit
def test_month_cutoff_keeps_current_month_plus_prior_months():
    assert archive_race_odds.month_cutoff(date(2026, 4, 26), 6) == "20251101"


@pytest.mark.unit
def test_normalize_database_url_for_asyncpg():
    assert (
        archive_race_odds.normalize_database_url("postgresql+asyncpg://user@host/db")
        == "postgresql://user@host/db"
    )
