"""add_teacher_progress_teacher_relationship_and_indexes

Revision ID: 49652649ad18
Revises: d77c712488e1
Create Date: 2025-11-05 13:13:01.502880

Adds teacher relationship and indexes to teacher_progress table:
- Adds teacher_id foreign key column for linking to Teacher model
- Adds indexes on email, academic_year, virtual_year, building for performance
- Adds composite indexes for common query patterns
- Adds unique constraint on (email, virtual_year) to prevent duplicates

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "49652649ad18"
down_revision: Union[str, Sequence[str], None] = "d77c712488e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add teacher relationship and indexes."""
    connection = op.get_bind()

    # Check if teacher_progress table exists
    result = connection.execute(
        sa.text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='teacher_progress'"
        )
    ).fetchone()

    if not result:
        # Table doesn't exist yet, skip migration
        print("WARNING: teacher_progress table does not exist, skipping migration")
        return

    # For SQLite, use batch_alter_table for adding columns
    # Note: Foreign key constraints in SQLite are handled at application level
    # SQLite foreign keys need to be explicitly enabled and may not work in batch_alter_table
    with op.batch_alter_table("teacher_progress", schema=None) as batch_op:
        # Add teacher_id column (nullable integer)
        # Foreign key relationship is handled by SQLAlchemy at application level
        batch_op.add_column(
            sa.Column(
                "teacher_id",
                sa.Integer(),
                nullable=True,
            )
        )

    # Add indexes on individual columns (if they don't exist)
    # Note: SQLite may have some indexes already, so we'll try/catch
    indexes_to_create = [
        ("ix_teacher_progress_email", "teacher_progress", ["email"]),
        ("ix_teacher_progress_academic_year", "teacher_progress", ["academic_year"]),
        ("ix_teacher_progress_virtual_year", "teacher_progress", ["virtual_year"]),
        ("ix_teacher_progress_building", "teacher_progress", ["building"]),
        ("ix_teacher_progress_teacher_id", "teacher_progress", ["teacher_id"]),
    ]

    for index_name, table_name, columns in indexes_to_create:
        try:
            op.create_index(
                index_name,
                table_name,
                columns,
                unique=False,
            )
        except Exception as e:
            # Index might already exist, which is fine
            print(f"Note: Index {index_name} may already exist: {e}")

    # Add composite indexes for common query patterns
    composite_indexes = [
        (
            "idx_teacher_progress_virtual_year_building",
            "teacher_progress",
            ["virtual_year", "building"],
        ),
        (
            "idx_teacher_progress_virtual_year_email",
            "teacher_progress",
            ["virtual_year", "email"],
        ),
    ]

    for index_name, table_name, columns in composite_indexes:
        try:
            op.create_index(
                index_name,
                table_name,
                columns,
                unique=False,
            )
        except Exception as e:
            print(f"Note: Index {index_name} may already exist: {e}")

    # Add unique constraint on (email, virtual_year) to prevent duplicates
    # For SQLite, we need to use batch_alter_table
    try:
        with op.batch_alter_table("teacher_progress", schema=None) as batch_op:
            batch_op.create_unique_constraint(
                "uix_teacher_progress_email_virtual_year",
                ["email", "virtual_year"],
            )
    except Exception as e:
        # Constraint might already exist or there might be duplicate data
        print(
            f"WARNING: Could not create unique constraint. "
            f"You may need to clean up duplicate records first: {e}"
        )


def downgrade() -> None:
    """Downgrade schema - remove teacher relationship and indexes."""
    # Remove unique constraint
    try:
        with op.batch_alter_table("teacher_progress", schema=None) as batch_op:
            batch_op.drop_constraint(
                "uix_teacher_progress_email_virtual_year", type_="unique"
            )
    except Exception:
        pass

    # Remove composite indexes
    composite_indexes = [
        "idx_teacher_progress_virtual_year_email",
        "idx_teacher_progress_virtual_year_building",
    ]

    for index_name in composite_indexes:
        try:
            op.drop_index(index_name, table_name="teacher_progress")
        except Exception:
            pass

    # Remove individual column indexes
    indexes_to_drop = [
        "ix_teacher_progress_teacher_id",
        "ix_teacher_progress_building",
        "ix_teacher_progress_virtual_year",
        "ix_teacher_progress_academic_year",
        "ix_teacher_progress_email",
    ]

    for index_name in indexes_to_drop:
        try:
            op.drop_index(index_name, table_name="teacher_progress")
        except Exception:
            pass

    # Remove teacher_id column
    with op.batch_alter_table("teacher_progress", schema=None) as batch_op:
        batch_op.drop_column("teacher_id")
