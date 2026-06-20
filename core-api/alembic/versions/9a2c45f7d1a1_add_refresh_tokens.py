"""add_refresh_tokens

Revision ID: 9a2c45f7d1a1
Revises: f8354f890d8f
Create Date: 2026-06-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9a2c45f7d1a1"
down_revision: Union[str, None] = "f8354f890d8f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("user_agent", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    with op.batch_alter_table("refresh_tokens", schema=None) as batch_op:
        batch_op.create_index("idx_refresh_tokens_hash", ["token_hash"], unique=False)
        batch_op.create_index("idx_refresh_tokens_user", ["user_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("refresh_tokens", schema=None) as batch_op:
        batch_op.drop_index("idx_refresh_tokens_user")
        batch_op.drop_index("idx_refresh_tokens_hash")
    op.drop_table("refresh_tokens")
