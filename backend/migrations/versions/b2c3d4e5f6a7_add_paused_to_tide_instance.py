"""add paused to tide_instance

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-21

"""
import alembic
import sqlalchemy

revision = 'b2c3d4e5f6a7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None

add_column = getattr(alembic.op, "add_column")
drop_column = getattr(alembic.op, "drop_column")


def upgrade():
    add_column('tide_instance', sqlalchemy.Column(
        'paused', sqlalchemy.Boolean(), nullable=False, server_default='false'
    ))


def downgrade():
    drop_column('tide_instance', 'paused')
