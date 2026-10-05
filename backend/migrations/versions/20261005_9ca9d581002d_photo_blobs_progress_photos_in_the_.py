"""photo blobs: progress photos in the database when the disk is wiped on deploy

Revision ID: 9ca9d581002d
Revises: a6147c496007
Create Date: 2026-10-05 00:47:31.915823

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9ca9d581002d'
down_revision: Union[str, Sequence[str], None] = 'a6147c496007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('photo_blobs',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.String(length=36), nullable=False),
    sa.Column('checkin_id', sa.String(length=36), nullable=False),
    sa.Column('view', sa.String(length=5), nullable=False),
    sa.Column('content_type', sa.String(length=20), nullable=False),
    sa.Column('data', sa.LargeBinary(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['checkin_id'], ['checkins.id'], name=op.f('fk_photo_blobs_checkin_id_checkins'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_photo_blobs_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_photo_blobs')),
    sa.UniqueConstraint('checkin_id', 'view', name=op.f('uq_photo_blobs_checkin_id_view'))
    )
    with op.batch_alter_table('photo_blobs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_photo_blobs_checkin_id'), ['checkin_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_photo_blobs_user_id'), ['user_id'], unique=False)




def downgrade() -> None:

    with op.batch_alter_table('photo_blobs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_photo_blobs_user_id'))
        batch_op.drop_index(batch_op.f('ix_photo_blobs_checkin_id'))

    op.drop_table('photo_blobs')
