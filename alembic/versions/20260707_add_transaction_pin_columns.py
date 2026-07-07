"""add transaction_pin_hash and pin_set columns to users table

Revision ID: 20260707_add_transaction_pin
Revises: 
Create Date: 2026-07-07 13:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260707_add_transaction_pin"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add transaction_pin_hash and pin_set columns to users table."""
    # Add transaction_pin_hash column
    op.add_column(
        "users",
        sa.Column("transaction_pin_hash", sa.String(255), nullable=True)
    )
    
    # Add pin_set column
    op.add_column(
        "users",
        sa.Column("pin_set", sa.Boolean(), nullable=False, server_default="false")
    )


def downgrade() -> None:
    """Remove transaction_pin_hash and pin_set columns from users table."""
    op.drop_column("users", "pin_set")
    op.drop_column("users", "transaction_pin_hash")