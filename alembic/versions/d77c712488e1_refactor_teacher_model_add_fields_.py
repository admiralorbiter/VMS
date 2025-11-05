"""refactor_teacher_model_add_fields_remove_sf_contact_id

Revision ID: d77c712488e1
Revises: 62eea7d37bc8
Create Date: 2025-11-05 11:56:31.956522

Refactors Teacher model:
- Adds status_change_date column for tracking status changes
- Adds local_status and local_status_last_updated columns for geographic analysis
- Removes salesforce_contact_id column (redundant, using salesforce_individual_id from Contact)

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d77c712488e1"
down_revision: Union[str, Sequence[str], None] = "62eea7d37bc8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add new teacher fields and remove redundant field."""
    connection = op.get_bind()

    # Clean up any leftover temporary tables from previous failed migrations
    try:
        connection.execute(sa.text("DROP TABLE IF EXISTS _alembic_tmp_teacher"))
    except Exception:
        pass

    # First, check if salesforce_contact_id column exists and drop indexes if needed
    result = connection.execute(sa.text("PRAGMA table_info(teacher)")).fetchall()
    column_names = [row[1] for row in result]
    has_sf_contact_id = "salesforce_contact_id" in column_names

    # Drop indexes on salesforce_contact_id if they exist
    if has_sf_contact_id:
        indexes_to_drop = [
            "ix_teacher_salesforce_contact_id",
            "ix_teacher_salesforce_contact_id_1",
        ]
        for index_name in indexes_to_drop:
            try:
                op.drop_index(index_name, table_name="teacher")
            except Exception:
                pass

    # For SQLite, we need to use batch_alter_table for most operations
    with op.batch_alter_table("teacher", schema=None) as batch_op:
        # Add status_change_date column (nullable DateTime for audit tracking)
        batch_op.add_column(
            sa.Column(
                "status_change_date",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )

        # Add local_status column (String for SQLite enum compatibility)
        # Default will be set to 'unknown' to match LocalStatusEnum.unknown
        batch_op.add_column(
            sa.Column(
                "local_status",
                sa.String(50),
                nullable=True,
                server_default="unknown",
            )
        )

        # Add local_status_last_updated column (nullable DateTime)
        batch_op.add_column(
            sa.Column(
                "local_status_last_updated",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )

        # Remove salesforce_contact_id column if it exists
        if has_sf_contact_id:
            batch_op.drop_column("salesforce_contact_id")

    # Add index on local_status for performance (similar to volunteer model)
    try:
        op.create_index(
            "ix_teacher_local_status",
            "teacher",
            ["local_status"],
            unique=False,
        )
    except Exception:
        # Index might already exist, which is fine
        pass


def downgrade() -> None:
    """Downgrade schema - remove new fields and restore salesforce_contact_id."""
    with op.batch_alter_table("teacher", schema=None) as batch_op:
        # Remove index first
        try:
            op.drop_index("ix_teacher_local_status", table_name="teacher")
        except Exception:
            pass

        # Remove new columns
        batch_op.drop_column("local_status_last_updated")
        batch_op.drop_column("local_status")
        batch_op.drop_column("status_change_date")

        # Restore salesforce_contact_id column (if it existed before)
        batch_op.add_column(
            sa.Column(
                "salesforce_contact_id",
                sa.String(18),
                nullable=True,
            )
        )
