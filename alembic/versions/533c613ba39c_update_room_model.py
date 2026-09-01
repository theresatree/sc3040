"""update room model

Revision ID: 533c613ba39c
Revises: ff6c2967b2d1
Create Date: 2026-09-01 04:05:17.873274

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '533c613ba39c'
down_revision: Union[str, Sequence[str], None] = 'ff6c2967b2d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop FK before changing the referenced/referencing column types
    op.drop_constraint(
        "timetables_room_id_fkey",
        "timetables",
        type_="foreignkey",
    )

    op.add_column( "rooms", sa.Column("name", sa.String(length=255), nullable=False),)
    op.add_column( "rooms", sa.Column("latitude", sa.Float(), nullable=False),)
    op.add_column( "rooms", sa.Column("longitude", sa.Float(), nullable=False),)

    op.alter_column(
        "rooms",
        "id",
        existing_type=sa.INTEGER(),
        type_=sa.String(length=50),
        existing_nullable=False,
        postgresql_using="id::varchar",
    )

    op.alter_column(
        "timetables",
        "room_id",
        existing_type=sa.INTEGER(),
        type_=sa.String(length=50),
        existing_nullable=False,
        postgresql_using="room_id::varchar",
    )

    op.drop_column("rooms", "y")
    op.drop_column("rooms", "x")

    # Recreate FK after both types match
    op.create_foreign_key(
        "timetables_room_id_fkey",
        "timetables",
        "rooms",
        ["room_id"],
        ["id"],
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # Drop FK first
    op.drop_constraint( "timetables_room_id_fkey", "timetables", type_="foreignkey",)

    op.alter_column(
        "timetables",
        "room_id",
        existing_type=sa.String(length=50),
        type_=sa.INTEGER(),
        existing_nullable=False,
        postgresql_using="room_id::integer",
    )

    op.add_column(
        "rooms",
        sa.Column(
            "x",
            sa.DOUBLE_PRECISION(precision=53),
            nullable=False,
        ),
    )
    op.add_column(
        "rooms",
        sa.Column(
            "y",
            sa.DOUBLE_PRECISION(precision=53),
            nullable=False,
        ),
    )

    op.alter_column(
        "rooms",
        "id",
        existing_type=sa.String(length=50),
        type_=sa.INTEGER(),
        existing_nullable=False,
        postgresql_using="id::integer",
    )

    op.create_foreign_key(
        "timetables_room_id_fkey",
        "timetables",
        "rooms",
        ["room_id"],
        ["id"],
    )

    op.drop_column("rooms", "longitude")
    op.drop_column("rooms", "latitude")
    op.drop_column("rooms", "name")
    # ### end Alembic commands ###
