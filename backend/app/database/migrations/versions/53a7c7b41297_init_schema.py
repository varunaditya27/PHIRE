"""init schema

Revision ID: 53a7c7b41297
Revises:
Create Date: 2026-08-28 09:00:00.000000

Single init migration for the current (single-patient, ml/-integrated)
schema -- documents/chat_messages/claims/audit_log only. Collapsed from
an earlier two-migration chain (create the original patient_id-scoped
schema, then a second migration dropping patient_id and the
observations/evidence_passages tables) into one, since neither migration
had ever been applied to any real/shared database -- a fresh install
creating tables it immediately alters is pure churn, not real migration
history. Schema verified live against a real Postgres 16
instance (see docs/BACKEND_HANDOFF.md's testing section).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '53a7c7b41297'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'documents',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('content_type', sa.String(), nullable=False),
        sa.Column('storage_path', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('chunk_count', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'chat_messages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('claims', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_chat_messages_created_at'), 'chat_messages', ['created_at'], unique=False)
    op.create_table(
        'claims',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('chat_message_id', sa.UUID(), nullable=True),
        sa.Column('statement', sa.Text(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('confidence', sa.Numeric(), nullable=True),
        sa.Column('source_url', sa.String(), nullable=True),
        sa.Column('source_filename', sa.String(), nullable=True),
        sa.Column('source_span_start', sa.Integer(), nullable=True),
        sa.Column('source_span_end', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['chat_message_id'], ['chat_messages.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'audit_log',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('endpoint', sa.String(), nullable=False),
        sa.Column('method', sa.String(), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=True),
        sa.Column('client_host', sa.String(), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audit_log_occurred_at'), 'audit_log', ['occurred_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_log_occurred_at'), table_name='audit_log')
    op.drop_table('audit_log')
    op.drop_table('claims')
    op.drop_index(op.f('ix_chat_messages_created_at'), table_name='chat_messages')
    op.drop_table('chat_messages')
    op.drop_table('documents')
