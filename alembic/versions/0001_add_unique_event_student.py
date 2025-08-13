"""Add unique constraint on (event_id, student_id) for event_student_participation

Revision ID: 0001_add_unique_event_student
Revises:
Create Date: 2025-08-13 00:00:00

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_add_unique_event_student"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Use batch_alter_table to be compatible with SQLite
    with op.batch_alter_table("event_student_participation") as batch_op:
        batch_op.create_unique_constraint(
            "uq_event_student", ["event_id", "student_id"]
        )


def downgrade():
    with op.batch_alter_table("event_student_participation") as batch_op:
        batch_op.drop_constraint("uq_event_student", type_="unique")
