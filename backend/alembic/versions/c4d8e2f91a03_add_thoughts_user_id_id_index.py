"""add thoughts user_id id index

Revision ID: c4d8e2f91a03
Revises: b9f2e1d44c10
Create Date: 2026-06-01 12:00:00.000000

Safe, non-destructive migration: only adds an index. No table or row data is modified.
Rollback: alembic downgrade -1 (drops the index only).
"""

from typing import Sequence, Union

from alembic import op


revision: str = "c4d8e2f91a03"
down_revision: Union[str, Sequence[str], None] = "b9f2e1d44c10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_thoughts_user_id_id",
        "thoughts",
        ["user_id", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_thoughts_user_id_id", table_name="thoughts")
