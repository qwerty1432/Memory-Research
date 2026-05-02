"""add condition_id to sessions

Revision ID: 0001_add_session_condition_id
Revises: 
Create Date: 2026-05-02

Adds a nullable `condition_id` column to the `sessions` table so that
`cleanup_session_memories` can be gated on the condition the session
ran under (not whatever the user's condition was later changed to).

Existing rows are left at NULL; runtime callers use a fallback to
`User.condition_id` when the session's stored value is NULL, preserving
pre-migration behavior.
"""
from alembic import op
import sqlalchemy as sa


revision = "0001_add_session_condition_id"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("condition_id", sa.String(length=50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sessions", "condition_id")
