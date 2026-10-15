"""add tide_env table + backfill KASM_SVC_* flags

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-10-15

Dynamic container env vars per tide. The hard-coded KASM_SVC_* flags are
migrated as rows so the runtime behaviour stays identical to the pre-refactor
version; the admin can tweak/remove them from the Environment tab afterwards.
"""
import alembic
import sqlalchemy
from sqlalchemy.dialects import postgresql

revision = 'd4e5f6a7b8c9'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None

create_table = getattr(alembic.op, "create_table")
drop_table = getattr(alembic.op, "drop_table")

_KASM_FLAGS = (
    'KASM_SVC_AUDIO',
    'KASM_SVC_AUDIO_INPUT',
    'KASM_SVC_UPLOADS',
    'KASM_SVC_GAMEPAD',
    'KASM_SVC_WEBCAM',
    'KASM_SVC_PRINTER',
    'KASM_SVC_SMARTCARD',
)


def upgrade():
    create_table(
        'tide_env',
        sqlalchemy.Column('id', sqlalchemy.Integer, primary_key=True, autoincrement=True),
        sqlalchemy.Column('tide_id', postgresql.UUID(), sqlalchemy.ForeignKey('tide.id', ondelete='CASCADE'), nullable=False),
        sqlalchemy.Column('key', sqlalchemy.String(128), nullable=False),
        sqlalchemy.Column('value', sqlalchemy.Text, nullable=False, server_default=''),
        sqlalchemy.UniqueConstraint('tide_id', 'key', name='uq_tide_env_tide_key'),
    )

    tide_env = sqlalchemy.table(
        'tide_env',
        sqlalchemy.column('tide_id', postgresql.UUID()),
        sqlalchemy.column('key', sqlalchemy.String),
        sqlalchemy.column('value', sqlalchemy.Text),
    )
    tide = sqlalchemy.table(
        'tide',
        sqlalchemy.column('id', postgresql.UUID()),
        sqlalchemy.column('tide_type', sqlalchemy.String),
    )
    conn = alembic.op.get_bind()
    rows = []
    for row in conn.execute(sqlalchemy.select(tide.c.id, tide.c.tide_type)):
        # Only KasmVNC-image tides had the hard-coded flags; guac-type tides
        # (vnc/rdp/ssh) don't need them.
        if row.tide_type in ('vnc', 'rdp', 'ssh'):
            continue
        for key in _KASM_FLAGS:
            rows.append({'tide_id': str(row.id), 'key': key, 'value': '0'})
    if rows:
        conn.execute(tide_env.insert(), rows)


def downgrade():
    drop_table('tide_env')
