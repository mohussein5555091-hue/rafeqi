"""plans: the AI summary for Why this plan

Revision ID: 46d696142439
Revises: 9ca9d581002d
Create Date: 2026-10-05 00:59:10.058373

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '46d696142439'
down_revision: Union[str, Sequence[str], None] = '9ca9d581002d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('plans', schema=None) as batch_op:
        batch_op.add_column(sa.Column('ai_summary', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('ai_model', sa.String(length=80), nullable=True))




def downgrade() -> None:

    with op.batch_alter_table('plans', schema=None) as batch_op:
        batch_op.drop_column('ai_model')
        batch_op.drop_column('ai_summary')

