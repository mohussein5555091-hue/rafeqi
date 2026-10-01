"""program exercises: starting weight and the weekly review's one-time weight change

Revision ID: 8f3a1c2d4e5b
Revises: 5c1e0a7d9b21
Create Date: 2026-10-01 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8f3a1c2d4e5b'
down_revision: Union[str, Sequence[str], None] = '5c1e0a7d9b21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('program_exercises', schema=None) as batch_op:
        batch_op.add_column(sa.Column('start_weight_kg', sa.Float(), server_default='0', nullable=False))
        batch_op.add_column(sa.Column('weight_offset_kg', sa.Float(), server_default='0', nullable=False))


def downgrade() -> None:
    with op.batch_alter_table('program_exercises', schema=None) as batch_op:
        batch_op.drop_column('weight_offset_kg')
        batch_op.drop_column('start_weight_kg')
