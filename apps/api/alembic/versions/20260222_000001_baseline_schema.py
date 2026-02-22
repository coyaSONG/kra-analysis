"""baseline schema

Revision ID: 20260222_000001
Revises:
Create Date: 2026-02-22 01:30:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op
from infrastructure.database import Base
from models.database_models import DataStatus, JobStatus, JobType

# revision identifiers, used by Alembic.
revision = "20260222_000001"
down_revision = None
branch_labels = None
depends_on = None


def _create_postgres_enums(bind) -> None:
    bind.execute(sa.text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))

    data_status_values = ", ".join(f"'{item.value}'" for item in DataStatus)
    job_type_values = ", ".join(f"'{item.value}'" for item in JobType)
    job_status_values = ", ".join(f"'{item.value}'" for item in JobStatus)

    bind.execute(
        sa.text(
            f"""
DO $$
BEGIN
    CREATE TYPE data_status AS ENUM ({data_status_values});
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
"""
        )
    )
    bind.execute(
        sa.text(
            f"""
DO $$
BEGIN
    CREATE TYPE job_type AS ENUM ({job_type_values});
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
"""
        )
    )
    bind.execute(
        sa.text(
            f"""
DO $$
BEGIN
    CREATE TYPE job_status AS ENUM ({job_status_values});
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
"""
        )
    )


def _drop_postgres_enums(bind) -> None:
    bind.execute(sa.text("DROP TYPE IF EXISTS job_status"))
    bind.execute(sa.text("DROP TYPE IF EXISTS job_type"))
    bind.execute(sa.text("DROP TYPE IF EXISTS data_status"))


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        _create_postgres_enums(bind)

    Base.metadata.create_all(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()

    Base.metadata.drop_all(bind=bind, checkfirst=True)

    if bind.dialect.name == "postgresql":
        _drop_postgres_enums(bind)
