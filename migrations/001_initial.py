"""Initial migration: create jobs table

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("type", sa.Enum("email", "image_resize", "report", name="jobtype"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "queued", "running", "success", "failed", "retrying", "revoked", name="jobstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("priority", sa.Integer(), server_default="5"),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("progress", sa.Float(), server_default="0.0"),
        sa.Column("queue", sa.String(), nullable=False),
        sa.Column("worker_id", sa.String(), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default="0"),
        sa.Column("max_retries", sa.Integer(), server_default="3"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("queued_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    # Indexes for common query patterns
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_type", "jobs", ["type"])
    op.create_index("ix_jobs_queue", "jobs", ["queue"])
    op.create_index("ix_jobs_created_at", "jobs", ["created_at"])


def downgrade():
    op.drop_table("jobs")
