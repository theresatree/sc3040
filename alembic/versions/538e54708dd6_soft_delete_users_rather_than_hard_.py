"""soft-delete users rather than hard-delete

Revision ID: 538e54708dd6
Revises: 2ff32e152cde
Create Date: 2026-09-03 09:16:05.330636

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '538e54708dd6'
down_revision: Union[str, Sequence[str], None] = '2ff32e152cde'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )

    op.alter_column(
        "users",
        "is_active",
        server_default=None,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "is_active")
