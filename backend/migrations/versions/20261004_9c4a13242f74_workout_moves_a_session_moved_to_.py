"""workout moves: a session moved to another day this week

Revision ID: 9c4a13242f74
Revises: 38c1e339409b
Create Date: 2026-10-04 23:37:36.317038

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9c4a13242f74'
down_revision: Union[str, Sequence[str], None] = '38c1e339409b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('workout_moves',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('week_start', sa.Date(), nullable=False),
    sa.Column('from_weekday', sa.String(length=3), nullable=False),
    sa.Column('to_date', sa.Date(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_workout_moves_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_workout_moves')),
    sa.UniqueConstraint('user_id', 'week_start', 'from_weekday', name=op.f('uq_workout_moves_user_id_week_start_from_weekday'))
    )
    with op.batch_alter_table('workout_moves', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_workout_moves_user_id'), ['user_id'], unique=False)




def downgrade() -> None:

    with op.batch_alter_table('workout_moves', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_workout_moves_user_id'))

    op.drop_table('workout_moves')
