"""Link application users to customers for JWT identities."""

from alembic import op
import sqlalchemy as sa


revision = "20260826_0002"
down_revision = "20260826_0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("customer_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_users_customer_id", "users", "customers", ["customer_id"], ["id"])
    op.create_index("ix_users_customer_id", "users", ["customer_id"], unique=True)


def downgrade():
    op.drop_index("ix_users_customer_id", table_name="users")
    op.drop_constraint("fk_users_customer_id", "users", type_="foreignkey")
    op.drop_column("users", "customer_id")
