"""add report_date to documents

Revision ID: a1b2c3d4e5f6
Revises: 53a7c7b41297
Create Date: 2026-09-10 00:00:00.000000

Adds documents.report_date: the clinical date of the report itself
(user-selected at upload, defaulting to today), distinct from
uploaded_at (when the file was received). This is the date ml/'s graph
writers attach to every fact extracted from a document -- see
app/services/document_processor.py's process_document, which now passes
document.report_date instead of guessing a date from the document's own
text. Backfilled from uploaded_at's date for any pre-existing rows so
the column can be NOT NULL immediately.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '53a7c7b41297'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('documents', sa.Column('report_date', sa.Date(), nullable=True))
    op.execute("UPDATE documents SET report_date = uploaded_at::date WHERE report_date IS NULL")
    op.alter_column('documents', 'report_date', nullable=False)


def downgrade() -> None:
    op.drop_column('documents', 'report_date')
