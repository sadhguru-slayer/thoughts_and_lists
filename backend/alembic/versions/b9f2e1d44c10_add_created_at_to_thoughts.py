"""add created_at to thoughts

Revision ID: b9f2e1d44c10
Revises: a21e8c9f10d1
Create Date: 2026-04-23 17:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b9f2e1d44c10"
down_revision: Union[str, Sequence[str], None] = "a21e8c9f10d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("thoughts", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        """
        UPDATE thoughts
        SET created_at = COALESCE(updated_at, NOW())
        WHERE created_at IS NULL
        """
    )
    op.alter_column(
        "thoughts",
        "created_at",
        existing_type=sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )


def downgrade() -> None:
    op.drop_column("thoughts", "created_at")

