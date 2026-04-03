"""users: add client_id; client_contacts: add portal_user_id

Revision ID: 008
Revises: 007
Create Date: 2026-04-02
"""

from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # users.client_id — для роли client_user
    op.add_column(
        "users",
        sa.Column(
            "client_id",
            sa.Integer(),
            sa.ForeignKey("clients.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # client_contacts.portal_user_id — обратная ссылка на созданный User
    op.add_column(
        "client_contacts",
        sa.Column(
            "portal_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("client_contacts", "portal_user_id")
    op.drop_column("users", "client_id")
