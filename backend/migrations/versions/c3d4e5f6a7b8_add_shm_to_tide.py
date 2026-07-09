"""add shm to tide

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-09

"""
import alembic
import sqlalchemy

revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None

add_column = getattr(alembic.op, "add_column")
drop_column = getattr(alembic.op, "drop_column")


def upgrade():
    add_column('tide', sqlalchemy.Column(
        'container_shm', sqlalchemy.String(20), nullable=True
    ))


def downgrade():
    drop_column('tide', 'container_shm')
