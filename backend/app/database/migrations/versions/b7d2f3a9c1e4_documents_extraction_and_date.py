"""documents.extracted_data, document_date, needs_date

Revision ID: b7d2f3a9c1e4
Revises: a1c4e7f9b2d3
Create Date: 2026-10-05 10:00:00.000000

`extracted_data` keeps the structured extraction so a document's graph facts and search chunks can be
rebuilt (e.g. after the user supplies a missing date) without re-running the vision model.
`document_date` is the clinical date applied to its facts; `needs_date` marks a document where none
could be found and a provisional (upload) date is in use until the user confirms the real one.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b7d2f3a9c1e4'
down_revision: Union[str, Sequence[str], None] = 'a1c4e7f9b2d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('documents', sa.Column('extracted_data', postgresql.JSONB(), nullable=True))
    op.add_column('documents', sa.Column('document_date', sa.String(), nullable=True))
    op.add_column('documents', sa.Column('needs_date', sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade() -> None:
    op.drop_column('documents', 'needs_date')
    op.drop_column('documents', 'document_date')
    op.drop_column('documents', 'extracted_data')
