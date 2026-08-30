"""Create durable email-processing job records."""

from alembic import op
import sqlalchemy as sa

revision = "20260827_0003"
down_revision = "20260826_0002"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "email_processing_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_id", sa.String(50), nullable=False, unique=True),
        sa.Column("email_id", sa.Integer(), sa.ForeignKey("emails.id"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    for column in ("job_id", "email_id", "customer_id", "status"):
        op.create_index(f"ix_email_processing_jobs_{column}", "email_processing_jobs", [column])

def downgrade():
    op.drop_table("email_processing_jobs")
