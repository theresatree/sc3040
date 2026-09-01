"""update timetable model

Revision ID: d06aeff2362b
Revises: 533c613ba39c
Create Date: 2026-09-01 06:41:27.169642

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd06aeff2362b'
down_revision: Union[str, Sequence[str], None] = '533c613ba39c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    day_of_week = sa.Enum(
        "MONDAY",
        "TUESDAY",
        "WEDNESDAY",
        "THURSDAY",
        "FRIDAY",
        name="day_of_week",
    )

    day_of_week.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "timetables",
        sa.Column("day_of_week", day_of_week, nullable=False),
    )

    op.add_column(
        "timetables",
        sa.Column("professor_id", sa.Integer(), nullable=False),
    )

    op.create_foreign_key(
        "timetables_professor_id_fkey",
        "timetables",
        "users",
        ["professor_id"],
        ["id"],
    )

def downgrade() -> None:
    op.drop_constraint(
        "timetables_professor_id_fkey",
        "timetables",
        type_="foreignkey",
    )

    op.drop_column("timetables", "professor_id")
    op.drop_column("timetables", "day_of_week")

    day_of_week = sa.Enum(
        "MONDAY",
        "TUESDAY",
        "WEDNESDAY",
        "THURSDAY",
        "FRIDAY",
        name="day_of_week",
    )

    day_of_week.drop(op.get_bind(), checkfirst=True)
