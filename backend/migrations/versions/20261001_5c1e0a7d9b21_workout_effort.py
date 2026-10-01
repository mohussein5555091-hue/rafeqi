"""workout effort: one "how hard was today's workout?" rating (1-10) per session

Workouts are now logged per exercise instead of set by set, so there is no RPE per set any more.

Revision ID: 5c1e0a7d9b21
Revises: 97434f9a2435
Create Date: 2026-10-01 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c1e0a7d9b21'
down_revision: Union[str, Sequence[str], None] = '97434f9a2435'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('workout_logs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('effort', sa.Integer(), nullable=True))
        batch_op.create_check_constraint(op.f('ck_workout_logs_effort_range'), 'effort BETWEEN 1 AND 10')


def downgrade() -> None:
    with op.batch_alter_table('workout_logs', schema=None) as batch_op:
        batch_op.drop_constraint(op.f('ck_workout_logs_effort_range'), type_='check')
        batch_op.drop_column('effort')
