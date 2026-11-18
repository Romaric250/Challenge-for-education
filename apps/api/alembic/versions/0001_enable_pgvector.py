"""Enable pgvector and record the embedding dimension.

Revision ID: 0001_enable_pgvector
Revises:
Create Date: 2026-11-18

"""

import sqlalchemy as sa
from alembic import op

revision = "0001_enable_pgvector"
down_revision = None
branch_labels = None
depends_on = None

# Snapshot of the embedding width at the time this revision was created.
# Do not edit this value after the revision has been applied.
EMBEDDING_DIMENSION = "1024"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$
        """
    )
    op.create_table(
        "schema_meta",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value", sa.String(length=256), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("key", name="pk_schema_meta"),
    )
    op.execute(
        """
        CREATE TRIGGER schema_meta_set_updated_at
        BEFORE UPDATE ON schema_meta
        FOR EACH ROW
        EXECUTE FUNCTION set_updated_at()
        """
    )
    schema_meta = sa.table(
        "schema_meta",
        sa.column("key", sa.String),
        sa.column("value", sa.String),
    )
    op.bulk_insert(
        schema_meta,
        [{"key": "embedding_dimension", "value": EMBEDDING_DIMENSION}],
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS schema_meta_set_updated_at ON schema_meta")
    op.drop_table("schema_meta")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at()")
    # The vector extension is left in place. Later revisions may depend on it,
    # and dropping it would fail if any column still uses it.
