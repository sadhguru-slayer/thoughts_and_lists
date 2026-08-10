"""add_richtext_enum

Revision ID: d7369bee68ff
Revises: 3b78baa0b30e
Create Date: 2026-08-10 18:42:06.557142

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7369bee68ff'
down_revision: Union[str, Sequence[str], None] = '3b78baa0b30e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TYPE field_type ADD VALUE IF NOT EXISTS 'RICHTEXT'")
    op.execute("ALTER TYPE field_type ADD VALUE IF NOT EXISTS 'richtext'")


def downgrade() -> None:
    """Downgrade schema."""
    pass
