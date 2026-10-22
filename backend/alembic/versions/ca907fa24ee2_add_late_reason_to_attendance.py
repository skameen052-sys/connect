"""add_late_reason_to_attendance

Revision ID: ca907fa24ee2
Revises: 777cd062c78d
Create Date: 2026-10-22 22:46:58.963102

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ca907fa24ee2'
down_revision: Union[str, Sequence[str], None] = '777cd062c78d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('attendance', sa.Column('late_reason', sa.String(length=500), nullable=True))
    op.add_column('attendance', sa.Column('late_reason_submitted_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('attendance', 'late_reason_submitted_at')
    op.drop_column('attendance', 'late_reason')
