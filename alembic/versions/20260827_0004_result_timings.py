"""Store measured worker timing breakdowns.

Revision ID: 20260827_0004
Revises: 20260827_0003
"""

from alembic import op
import sqlalchemy as sa

revision = "20260827_0004"
down_revision = "20260827_0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("email_processing_results", sa.Column("classification_time", sa.Float(), nullable=True))
    op.add_column("email_processing_results", sa.Column("retrieval_time", sa.Float(), nullable=True))
    op.add_column("email_processing_results", sa.Column("llm_generation_time", sa.Float(), nullable=True))


def downgrade():
    op.drop_column("email_processing_results", "llm_generation_time")
    op.drop_column("email_processing_results", "retrieval_time")
    op.drop_column("email_processing_results", "classification_time")
