"""feedback: messages from Send feedback in Profile

Revision ID: a6147c496007
Revises: ca0a41b6cb56
Create Date: 2026-10-05 00:40:44.906717

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a6147c496007'
down_revision: Union[str, Sequence[str], None] = 'ca0a41b6cb56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('feedback',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('page', sa.String(length=120), nullable=False),
    sa.Column('app_version', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.CheckConstraint('length(message) BETWEEN 1 AND 1000', name=op.f('ck_feedback_message_length')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_feedback_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_feedback'))
    )
    with op.batch_alter_table('feedback', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_feedback_user_id'), ['user_id'], unique=False)




def downgrade() -> None:

    with op.batch_alter_table('feedback', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_feedback_user_id'))

    op.drop_table('feedback')
