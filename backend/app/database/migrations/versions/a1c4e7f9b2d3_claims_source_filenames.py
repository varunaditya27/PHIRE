"""claims.source_filenames

Revision ID: a1c4e7f9b2d3
Revises: 53a7c7b41297
Create Date: 2026-10-04 15:00:00.000000

A claim (a trend especially) can rest on several uploaded documents, so the
single `source_filename` column is no longer enough. `source_filenames` holds
the full list; `source_filename` stays as the first entry for existing queries.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'a1c4e7f9b2d3'
down_revision: Union[str, Sequence[str], None] = '53a7c7b41297'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('claims', sa.Column('source_filenames', postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column('claims', 'source_filenames')
