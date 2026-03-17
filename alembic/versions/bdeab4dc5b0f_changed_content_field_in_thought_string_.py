"""Changed content field in Thought String -> Text

Revision ID: bdeab4dc5b0f
Revises: 8334150e398d
Create Date: 2026-03-15 14:26:16.708802

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'bdeab4dc5b0f'
down_revision: Union[str, Sequence[str], None] = '8334150e398d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Change content column to Text
    op.alter_column('thoughts', 'content',
                    type_=sa.Text(),
                    existing_type=sa.String())

def downgrade():
    # Revert content column to String
    op.alter_column('thoughts', 'content',
                    type_=sa.String(),
                    existing_type=sa.Text())