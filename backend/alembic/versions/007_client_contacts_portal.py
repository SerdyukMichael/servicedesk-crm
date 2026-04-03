"""client_contacts: add is_primary, portal_access, portal_role, created_by, timestamps

Revision ID: 007
Revises: 006
Create Date: 2026-04-02
"""

from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "client_contacts",
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "client_contacts",
        sa.Column("portal_access", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "client_contacts",
        sa.Column(
            "portal_role",
            sa.Enum("client_user", "client_admin", name="contact_portal_role_enum"),
            nullable=True,
        ),
    )
    op.add_column(
        "client_contacts",
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "client_contacts",
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.add_column(
        "client_contacts",
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    # Unique constraint: email must be unique per client (among active records only —
    # enforced in app layer, not DB, because NULL emails are allowed)


def downgrade() -> None:
    op.drop_column("client_contacts", "updated_at")
    op.drop_column("client_contacts", "created_at")
    op.drop_column("client_contacts", "created_by")
    op.drop_column("client_contacts", "portal_role")
    op.drop_column("client_contacts", "portal_access")
    op.drop_column("client_contacts", "is_primary")
    op.execute("DROP TYPE IF EXISTS contact_portal_role_enum")
