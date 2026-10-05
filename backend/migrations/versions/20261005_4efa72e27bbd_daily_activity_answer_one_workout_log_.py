"""daily activity answer; one workout log per person per day

profiles.daily_activity: "outside training, are you mostly sitting, on your feet part of the day, or in a physically
active job?" (empty for people who answered before; they count as "on my feet part of the day").

workout_logs: at most one per person per day. Before the rule is added, any duplicates (two saves that arrived at the
same moment, each starting a log) are merged into one: the finished one if there is one, else the earliest; exercises
only the duplicate has move over, its pain logs point at the kept log, and the duplicate is deleted.

Revision ID: 4efa72e27bbd
Revises: 46d696142439
Create Date: 2026-10-05 17:42:10.908425

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4efa72e27bbd'
down_revision: Union[str, Sequence[str], None] = '46d696142439'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def merge_duplicate_logs(conn) -> int:
    """Merges workout logs that share a person and a day; returns how many were removed."""
    logs = conn.execute(sa.text(
        "SELECT id, user_id, date, status, started_at FROM workout_logs ORDER BY user_id, date, started_at, id")).fetchall()
    groups: dict[tuple, list] = {}
    for row in logs:
        groups.setdefault((row.user_id, str(row.date)), []).append(row)
    removed = 0
    for rows in groups.values():
        if len(rows) < 2:
            continue
        keep = next((r for r in rows if r.status == "done"), rows[0])
        kept_exercises = {e for (e,) in conn.execute(
            sa.text("SELECT DISTINCT exercise_id FROM set_logs WHERE workout_log_id = :k"), {"k": keep.id})}
        for dup in (r for r in rows if r.id != keep.id):
            for (exercise_id,) in conn.execute(
                    sa.text("SELECT DISTINCT exercise_id FROM set_logs WHERE workout_log_id = :d"), {"d": dup.id}).fetchall():
                if exercise_id not in kept_exercises:
                    conn.execute(sa.text("UPDATE set_logs SET workout_log_id = :k WHERE workout_log_id = :d AND exercise_id = :e"),
                                 {"k": keep.id, "d": dup.id, "e": exercise_id})
                    kept_exercises.add(exercise_id)
            conn.execute(sa.text("DELETE FROM set_logs WHERE workout_log_id = :d"), {"d": dup.id})
            conn.execute(sa.text("UPDATE pain_logs SET workout_log_id = :k WHERE workout_log_id = :d"), {"k": keep.id, "d": dup.id})
            conn.execute(sa.text("DELETE FROM workout_logs WHERE id = :d"), {"d": dup.id})
            removed += 1
    return removed


def upgrade() -> None:
    with op.batch_alter_table('profiles', schema=None) as batch_op:
        batch_op.add_column(sa.Column('daily_activity', sa.String(length=10), nullable=True))

    merge_duplicate_logs(op.get_bind())
    with op.batch_alter_table('workout_logs', schema=None) as batch_op:
        batch_op.create_unique_constraint('uq_workout_logs_user_date', ['user_id', 'date'])


def downgrade() -> None:
    with op.batch_alter_table('workout_logs', schema=None) as batch_op:
        batch_op.drop_constraint('uq_workout_logs_user_date', type_='unique')

    with op.batch_alter_table('profiles', schema=None) as batch_op:
        batch_op.drop_column('daily_activity')
