"""longer rules_version and swap_kind (PostgreSQL enforces lengths; SQLite never did)

Revision ID: ca0a41b6cb56
Revises: 9c4a13242f74
Create Date: 2026-10-05 00:36:00.004043

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca0a41b6cb56'
down_revision: Union[str, Sequence[str], None] = '9c4a13242f74'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('plans', schema=None) as batch_op:
        batch_op.alter_column('rules_version', existing_type=sa.String(length=40), type_=sa.String(length=120), existing_nullable=False)
    with op.batch_alter_table('program_exercises', schema=None) as batch_op:
        batch_op.alter_column('swap_kind', existing_type=sa.String(length=8), type_=sa.String(length=12), existing_nullable=True)


def downgrade() -> None:
    with op.batch_alter_table('program_exercises', schema=None) as batch_op:
        batch_op.alter_column('swap_kind', existing_type=sa.String(length=12), type_=sa.String(length=8), existing_nullable=True)
    with op.batch_alter_table('plans', schema=None) as batch_op:
        batch_op.alter_column('rules_version', existing_type=sa.String(length=120), type_=sa.String(length=40), existing_nullable=False)
