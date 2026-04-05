"""RaceOdds 모델 단위 테스트"""

from models.database_models import RaceOdds


class TestRaceOddsModel:
    def test_tablename(self):
        assert RaceOdds.__tablename__ == "race_odds"

    def test_has_required_columns(self):
        cols = {c.name for c in RaceOdds.__table__.columns}
        required = {
            "id",
            "race_id",
            "pool",
            "chul_no",
            "chul_no2",
            "chul_no3",
            "odds",
            "rc_date",
            "source",
            "collected_at",
        }
        assert required.issubset(cols)

    def test_race_id_fk(self):
        col = RaceOdds.__table__.columns["race_id"]
        fk_targets = [fk.target_fullname for fk in col.foreign_keys]
        assert "races.race_id" in fk_targets

    def test_fk_cascade_delete(self):
        col = RaceOdds.__table__.columns["race_id"]
        for fk in col.foreign_keys:
            assert fk.ondelete == "CASCADE"

    def test_has_unique_constraint(self):
        unique_constraints = [
            c
            for c in RaceOdds.__table__.constraints
            if c.__class__.__name__ == "UniqueConstraint"
            and c.name == "uq_race_odds_entry"
        ]
        assert len(unique_constraints) == 1
        col_names = {col.name for col in unique_constraints[0].columns}
        assert col_names == {
            "race_id",
            "pool",
            "chul_no",
            "chul_no2",
            "chul_no3",
            "source",
        }

    def test_has_indexes(self):
        index_names = {idx.name for idx in RaceOdds.__table__.indexes}
        assert "idx_race_odds_race_pool" in index_names
        assert "idx_race_odds_date_pool_source" in index_names
