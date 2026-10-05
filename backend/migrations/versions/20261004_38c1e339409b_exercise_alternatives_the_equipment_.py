"""exercise alternatives: the equipment each uses (for the label "Different equipment: cable machine")

Revision ID: 38c1e339409b
Revises: 8a7f4ea34f9e
Create Date: 2026-10-04 23:18:57.570334

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '38c1e339409b'
down_revision: Union[str, Sequence[str], None] = '8a7f4ea34f9e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('exercise_substitutions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('equipment', sa.JSON(), nullable=False, server_default='[]'))


def downgrade() -> None:
    with op.batch_alter_table('exercise_substitutions', schema=None) as batch_op:
        batch_op.drop_column('equipment')
