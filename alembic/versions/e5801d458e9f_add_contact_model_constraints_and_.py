"""add_contact_model_constraints_and_indexes

Revision ID: e5801d458e9f
Revises: 65611e539650
Create Date: 2025-11-01 10:52:49.286239

Adds constraints and indexes to Contact, Phone, Email, and Address models:
- Makes Phone.number and Email.email required (NOT NULL)
- Adds indexes on foreign keys (contact_id) for performance
- Adds indexes on primary flags for faster lookups
- Adds composite indexes for primary phone/email queries
- Adds index on Address.zip_code for local status calculations

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5801d458e9f"
down_revision: Union[str, Sequence[str], None] = "65611e539650"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema with constraints and indexes."""
    # Step 1: Check and clean up invalid data (NULL values) before adding constraints
    # Count invalid records for logging
    connection = op.get_bind()

    # Count invalid phones
    invalid_phone_count = connection.execute(
        sa.text("SELECT COUNT(*) FROM phone WHERE number IS NULL OR number = ''")
    ).scalar()

    # Count invalid emails
    invalid_email_count = connection.execute(
        sa.text("SELECT COUNT(*) FROM email WHERE email IS NULL OR email = ''")
    ).scalar()

    # Log the cleanup operation
    if invalid_phone_count > 0 or invalid_email_count > 0:
        print(
            f"WARNING: Cleaning up invalid records: {invalid_phone_count} phones, "
            f"{invalid_email_count} emails"
        )

    # Delete phone records with NULL or empty numbers (invalid data)
    # These records are invalid and cannot be fixed automatically
    op.execute(
        """
        DELETE FROM phone
        WHERE number IS NULL OR number = ''
    """
    )

    # Delete email records with NULL or empty email addresses (invalid data)
    # These records are invalid and cannot be fixed automatically
    op.execute(
        """
        DELETE FROM email
        WHERE email IS NULL OR email = ''
    """
    )

    # Step 2: Add indexes to phone table
    # Index on contact_id for foreign key lookups
    op.create_index(
        "ix_phone_contact_id",
        "phone",
        ["contact_id"],
        unique=False,
    )

    # Index on primary flag for primary phone lookups
    op.create_index(
        "ix_phone_primary",
        "phone",
        ["primary"],
        unique=False,
    )

    # Composite index for primary phone queries (contact_id + primary)
    op.create_index(
        "idx_phone_contact_primary",
        "phone",
        ["contact_id", "primary"],
        unique=False,
    )

    # Step 3: Add indexes to email table
    # Index on contact_id for foreign key lookups
    op.create_index(
        "ix_email_contact_id",
        "email",
        ["contact_id"],
        unique=False,
    )

    # Index on primary flag for primary email lookups
    op.create_index(
        "ix_email_primary",
        "email",
        ["primary"],
        unique=False,
    )

    # Composite index for primary email queries (contact_id + primary)
    op.create_index(
        "idx_email_contact_primary",
        "email",
        ["contact_id", "primary"],
        unique=False,
    )

    # Step 4: Add indexes to address table
    # Index on contact_id for foreign key lookups
    op.create_index(
        "ix_address_contact_id",
        "address",
        ["contact_id"],
        unique=False,
    )

    # Index on zip_code for local status calculations
    op.create_index(
        "ix_address_zip_code",
        "address",
        ["zip_code"],
        unique=False,
    )

    # Index on primary flag for primary address lookups
    op.create_index(
        "ix_address_primary",
        "address",
        ["primary"],
        unique=False,
    )

    # Composite index for primary address queries (contact_id + primary)
    op.create_index(
        "idx_address_contact_primary",
        "address",
        ["contact_id", "primary"],
        unique=False,
    )

    # Step 5: Add NOT NULL constraints using batch_alter_table for SQLite compatibility
    # For Phone.number
    with op.batch_alter_table("phone", schema=None) as batch_op:
        batch_op.alter_column(
            "number",
            existing_type=sa.String(20),
            nullable=False,
            existing_nullable=True,
        )

    # For Email.email
    with op.batch_alter_table("email", schema=None) as batch_op:
        batch_op.alter_column(
            "email",
            existing_type=sa.String(100),
            nullable=False,
            existing_nullable=True,
        )


def downgrade() -> None:
    """Downgrade schema - remove constraints and indexes."""
    # Remove NOT NULL constraints (make nullable again)
    with op.batch_alter_table("email", schema=None) as batch_op:
        batch_op.alter_column(
            "email",
            existing_type=sa.String(100),
            nullable=True,
            existing_nullable=False,
        )

    with op.batch_alter_table("phone", schema=None) as batch_op:
        batch_op.alter_column(
            "number",
            existing_type=sa.String(20),
            nullable=True,
            existing_nullable=False,
        )

    # Remove indexes
    op.drop_index("idx_address_contact_primary", table_name="address")
    op.drop_index("ix_address_primary", table_name="address")
    op.drop_index("ix_address_zip_code", table_name="address")
    op.drop_index("ix_address_contact_id", table_name="address")

    op.drop_index("idx_email_contact_primary", table_name="email")
    op.drop_index("ix_email_primary", table_name="email")
    op.drop_index("ix_email_contact_id", table_name="email")

    op.drop_index("idx_phone_contact_primary", table_name="phone")
    op.drop_index("ix_phone_primary", table_name="phone")
    op.drop_index("ix_phone_contact_id", table_name="phone")
