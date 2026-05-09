"""add updated_at to journals and thoughts

Revision ID: a21e8c9f10d1
Revises: 675c28784ace
Create Date: 2026-04-23 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a21e8c9f10d1"
down_revision: Union[str, Sequence[str], None] = "675c28784ace"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("journals", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("thoughts", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'journals' AND column_name = 'created_at'
            ) THEN
                UPDATE journals
                SET updated_at = COALESCE(created_at, NOW())
                WHERE updated_at IS NULL;
            ELSE
                UPDATE journals
                SET updated_at = NOW()
                WHERE updated_at IS NULL;
            END IF;
        END$$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'thoughts' AND column_name = 'created_at'
            ) THEN
                UPDATE thoughts
                SET updated_at = COALESCE(created_at, NOW())
                WHERE updated_at IS NULL;
            ELSE
                UPDATE thoughts
                SET updated_at = NOW()
                WHERE updated_at IS NULL;
            END IF;
        END$$;
        """
    )

    op.alter_column("journals", "updated_at", nullable=False)
    op.alter_column("thoughts", "updated_at", nullable=False)


def downgrade() -> None:
    op.drop_column("thoughts", "updated_at")
    op.drop_column("journals", "updated_at")

