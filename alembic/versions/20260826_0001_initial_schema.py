"""initial application schema"""
revision = "20260826_0001"
down_revision = None
branch_labels = None
depends_on = None
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table("users", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("email", sa.String(255), nullable=False, unique=True), sa.Column("password_hash", sa.String(255), nullable=False), sa.Column("role", sa.String(50), nullable=False), sa.Column("is_active", sa.Boolean(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("customers", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("customer_id", sa.String(30), nullable=False, unique=True), sa.Column("name", sa.String(255), nullable=False), sa.Column("email", sa.String(255), nullable=False, unique=True), sa.Column("phone", sa.String(50)), sa.Column("address", sa.Text()), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("products", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("product_id", sa.String(30), nullable=False, unique=True), sa.Column("product_name", sa.String(255), nullable=False), sa.Column("category", sa.String(100), nullable=False), sa.Column("description", sa.Text(), nullable=False), sa.Column("price", sa.Numeric(10,2), nullable=False), sa.Column("stock", sa.Integer(), nullable=False), sa.Column("warranty", sa.String(100)), sa.Column("available_sizes", sa.String(255)), sa.Column("available_colors", sa.String(255)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("orders", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("order_id", sa.String(30), nullable=False, unique=True), sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False), sa.Column("order_date", sa.Date(), nullable=False), sa.Column("status", sa.String(50), nullable=False), sa.Column("payment_status", sa.String(50), nullable=False), sa.Column("total_amount", sa.Numeric(10,2), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("order_items", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False), sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False), sa.Column("quantity", sa.Integer(), nullable=False), sa.Column("unit_price", sa.Numeric(10,2), nullable=False))
    op.create_table("emails", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("email_id", sa.String(30), nullable=False, unique=True), sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id")), sa.Column("subject", sa.String(500), nullable=False), sa.Column("body", sa.Text(), nullable=False), sa.Column("predicted_category", sa.String(100)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("email_processing_results", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("email_id", sa.Integer(), sa.ForeignKey("emails.id"), nullable=False), sa.Column("predicted_category", sa.String(100), nullable=False), sa.Column("generated_response", sa.Text(), nullable=False), sa.Column("processing_time", sa.Float(), nullable=False), sa.Column("retrieved_sources", postgresql.JSONB(astext_type=sa.Text()), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    for table, column in [("users","email"),("customers","customer_id"),("customers","email"),("products","product_id"),("orders","order_id"),("orders","customer_id"),("order_items","order_id"),("order_items","product_id"),("emails","email_id"),("emails","customer_id")]: op.create_index(f"ix_{table}_{column}", table, [column])

def downgrade():
    for table in ["email_processing_results","emails","order_items","orders","products","customers","users"]: op.drop_table(table)
