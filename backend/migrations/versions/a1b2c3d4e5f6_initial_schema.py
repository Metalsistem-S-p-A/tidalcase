"""initial schema

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-04-21

"""
import json
import alembic
import sqlalchemy

revision = 'a1b2c3d4e5f6'
down_revision = None
branch_labels = None
depends_on = None

create_table = getattr(alembic.op, "create_table")
bulk_insert = getattr(alembic.op, "bulk_insert")
drop_table = getattr(alembic.op, "drop_table")


def upgrade():
    create_table('tide',
        sqlalchemy.Column('id', sqlalchemy.UUID(), server_default=sqlalchemy.text("gen_random_uuid()"), nullable=False),
        sqlalchemy.Column('display_name', sqlalchemy.String(80), nullable=False),
        sqlalchemy.Column('description', sqlalchemy.String(255), nullable=True),
        sqlalchemy.Column('image_path', sqlalchemy.String(255), nullable=True),
        sqlalchemy.Column('tide_type', sqlalchemy.String(80), nullable=False),
        sqlalchemy.Column('container_docker_image', sqlalchemy.String(255), nullable=True),
        sqlalchemy.Column('container_docker_registry', sqlalchemy.String(255), nullable=True),
        sqlalchemy.Column('container_cores', sqlalchemy.Integer(), nullable=True),
        sqlalchemy.Column('container_memory', sqlalchemy.String(20), nullable=True),
        sqlalchemy.Column('container_swap', sqlalchemy.String(20), nullable=True),
        sqlalchemy.Column('container_persistent_profile_path', sqlalchemy.String(512), nullable=True),
        sqlalchemy.Column('container_network', sqlalchemy.String(255), nullable=True),
        sqlalchemy.Column('server_ip', sqlalchemy.String(255), nullable=True),
        sqlalchemy.Column('server_port', sqlalchemy.Integer(), nullable=True),
        sqlalchemy.Column('restricted_groups', sqlalchemy.String(255), nullable=True),
        sqlalchemy.Column('session_time_limit', sqlalchemy.Integer(), nullable=True, server_default='0'),
        sqlalchemy.Column('session_idle_time_limit', sqlalchemy.Integer(), nullable=True, server_default='0'),
        sqlalchemy.Column('agent_selection_mode', sqlalchemy.String(20), nullable=True),
        sqlalchemy.Column('vnc_user', sqlalchemy.String(80), nullable=True),
        sqlalchemy.Column('upload_path', sqlalchemy.Text, nullable=True),
        sqlalchemy.Column('download_path', sqlalchemy.Text, nullable=True),
        sqlalchemy.Column('open_mode', sqlalchemy.String(10), nullable=False, server_default='user'),
        sqlalchemy.Column('connection_settings', sqlalchemy.JSON(), nullable=True),
        sqlalchemy.PrimaryKeyConstraint('id'),
    )
    group_table = create_table('group',
        sqlalchemy.Column('id', sqlalchemy.UUID(), server_default=sqlalchemy.text("gen_random_uuid()"), nullable=False),
        sqlalchemy.Column('display_name', sqlalchemy.String(80), nullable=False),
        sqlalchemy.Column('created_at', sqlalchemy.DateTime(), server_default=sqlalchemy.text('CURRENT_TIMESTAMP'), nullable=True),
        sqlalchemy.Column('protected', sqlalchemy.Boolean(), nullable=False),
        sqlalchemy.Column('priority', sqlalchemy.Integer(), nullable=False, server_default='0'),
        sqlalchemy.Column('settings', sqlalchemy.JSON(), nullable=False),
        sqlalchemy.Column('perm_admin_panel', sqlalchemy.Boolean(), nullable=False),
        sqlalchemy.Column('perm_view_instances', sqlalchemy.Boolean(), nullable=False),
        sqlalchemy.Column('perm_edit_instances', sqlalchemy.Boolean(), nullable=False),
        sqlalchemy.Column('perm_view_users', sqlalchemy.Boolean(), nullable=False),
        sqlalchemy.Column('perm_edit_users', sqlalchemy.Boolean(), nullable=False),
        sqlalchemy.Column('perm_view_tides', sqlalchemy.Boolean(), nullable=False),
        sqlalchemy.Column('perm_edit_tides', sqlalchemy.Boolean(), nullable=False),
        sqlalchemy.Column('perm_view_registry', sqlalchemy.Boolean(), nullable=False),
        sqlalchemy.Column('perm_edit_registry', sqlalchemy.Boolean(), nullable=False),
        sqlalchemy.Column('perm_view_groups', sqlalchemy.Boolean(), nullable=False),
        sqlalchemy.Column('perm_edit_groups', sqlalchemy.Boolean(), nullable=False),
        sqlalchemy.Column('auto_start_tide_id', sqlalchemy.UUID(), nullable=True),

        sqlalchemy.PrimaryKeyConstraint('id'),
        sqlalchemy.ForeignKeyConstraint(['auto_start_tide_id'], ['tide.id'], ondelete='SET NULL', onupdate='SET NULL'),
    )
    create_table('user',
        sqlalchemy.Column('id', sqlalchemy.UUID(), server_default=sqlalchemy.text("gen_random_uuid()"), nullable=False),
        sqlalchemy.Column('username', sqlalchemy.String(80), nullable=False),
        sqlalchemy.Column('password', sqlalchemy.String(80), nullable=False),
        sqlalchemy.Column('auth_token', sqlalchemy.String(80), nullable=False),
        sqlalchemy.Column('created_at', sqlalchemy.DateTime(), server_default=sqlalchemy.text('CURRENT_TIMESTAMP'), nullable=True),
        sqlalchemy.Column('usertype', sqlalchemy.String(20), nullable=False, server_default='Internal'),
        sqlalchemy.Column('protected', sqlalchemy.Boolean(), nullable=False),
        sqlalchemy.Column('email', sqlalchemy.String(255), nullable=True),
        sqlalchemy.Column('preferred_language', sqlalchemy.String(8), nullable=False, server_default='en'),
        sqlalchemy.Column('mfa_secret', sqlalchemy.String(64), nullable=True),
        sqlalchemy.Column('mfa_enabled', sqlalchemy.Boolean(), nullable=False, server_default='0'),
        sqlalchemy.Column('mfa_trust_duration', sqlalchemy.Integer(), nullable=False, server_default='30'),
        sqlalchemy.Column('auto_start_tide_id', sqlalchemy.UUID(), nullable=True),
        sqlalchemy.PrimaryKeyConstraint('id'),
        sqlalchemy.UniqueConstraint('username'),
        sqlalchemy.ForeignKeyConstraint(['auto_start_tide_id'], ['tide.id'], ondelete='SET NULL', onupdate='SET NULL'),
    )
    create_table('refresh_token',
        sqlalchemy.Column('id', sqlalchemy.UUID(), server_default=sqlalchemy.text("gen_random_uuid()"), nullable=False),
        sqlalchemy.Column('user_id', sqlalchemy.UUID(), nullable=False),
        sqlalchemy.Column('token', sqlalchemy.String(64), nullable=False),
        sqlalchemy.Column('expires_at', sqlalchemy.DateTime(), nullable=False),
        sqlalchemy.Column('created_at', sqlalchemy.DateTime(), server_default=sqlalchemy.text('CURRENT_TIMESTAMP'), nullable=True),
        sqlalchemy.Column('auth_provider_id', sqlalchemy.UUID(), nullable=True),
        sqlalchemy.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE', onupdate='CASCADE'),
        sqlalchemy.ForeignKeyConstraint(['auth_provider_id'], ['auth_provider.id'], ondelete='SET NULL', onupdate='CASCADE'),
        sqlalchemy.PrimaryKeyConstraint('id'),
        sqlalchemy.UniqueConstraint('token'),
    )
    create_table('trusted_device',
        sqlalchemy.Column('id', sqlalchemy.UUID(), server_default=sqlalchemy.text("gen_random_uuid()"), nullable=False),
        sqlalchemy.Column('user_id', sqlalchemy.UUID(), nullable=False),
        sqlalchemy.Column('device_name', sqlalchemy.String(255), nullable=True),
        sqlalchemy.Column('ip_address', sqlalchemy.String(45), nullable=True),
        sqlalchemy.Column('last_used_at', sqlalchemy.DateTime(), server_default=sqlalchemy.text('CURRENT_TIMESTAMP'), nullable=True),
        sqlalchemy.Column('expires_at', sqlalchemy.DateTime(), nullable=False),
        sqlalchemy.Column('created_at', sqlalchemy.DateTime(), server_default=sqlalchemy.text('CURRENT_TIMESTAMP'), nullable=True),
        sqlalchemy.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE', onupdate='CASCADE'),
        sqlalchemy.PrimaryKeyConstraint('id'),
    )
    create_table('user_groups',
        sqlalchemy.Column('user_id', sqlalchemy.UUID(), nullable=False),
        sqlalchemy.Column('group_id', sqlalchemy.UUID(), nullable=False),
        sqlalchemy.PrimaryKeyConstraint('user_id', 'group_id'),
        sqlalchemy.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE', onupdate='CASCADE'),
        sqlalchemy.ForeignKeyConstraint(['group_id'], ['group.id'], ondelete='CASCADE', onupdate='CASCADE'),
    )
    registry_table = create_table('registry',
        sqlalchemy.Column('id', sqlalchemy.UUID(), server_default=sqlalchemy.text("gen_random_uuid()"), nullable=False),
        sqlalchemy.Column('created_at', sqlalchemy.DateTime(), server_default=sqlalchemy.text('CURRENT_TIMESTAMP'), nullable=True),
        sqlalchemy.Column('url', sqlalchemy.String(255), nullable=False),
        sqlalchemy.PrimaryKeyConstraint('id'),
    )
    create_table('log',
        sqlalchemy.Column('id', sqlalchemy.UUID(), server_default=sqlalchemy.text("gen_random_uuid()"), nullable=False),
        sqlalchemy.Column('created_at', sqlalchemy.DateTime(), server_default=sqlalchemy.text('CURRENT_TIMESTAMP'), nullable=True),
        sqlalchemy.Column('level', sqlalchemy.String(8), nullable=False),
        sqlalchemy.Column('message', sqlalchemy.String(1024), nullable=False),
        sqlalchemy.PrimaryKeyConstraint('id'),
    )
    auth_provider_table = create_table('auth_provider',
        sqlalchemy.Column('id', sqlalchemy.UUID(), server_default=sqlalchemy.text("gen_random_uuid()"), nullable=False),
        sqlalchemy.Column('name', sqlalchemy.String(80), nullable=False),
        sqlalchemy.Column('slug', sqlalchemy.String(80), nullable=False),
        sqlalchemy.Column('type', sqlalchemy.String(20), nullable=False),
        sqlalchemy.Column('priority', sqlalchemy.Integer(), nullable=False, server_default='0'),
        sqlalchemy.Column('enabled', sqlalchemy.Boolean(), nullable=False, server_default='1'),
        sqlalchemy.Column('settings', sqlalchemy.JSON(), nullable=True),
        sqlalchemy.Column('created_at', sqlalchemy.DateTime(), server_default=sqlalchemy.text('CURRENT_TIMESTAMP'), nullable=True),
        sqlalchemy.PrimaryKeyConstraint('id'),
        sqlalchemy.UniqueConstraint('slug'),
    )
    create_table('agent',
        sqlalchemy.Column('id', sqlalchemy.UUID(), server_default=sqlalchemy.text("gen_random_uuid()"), nullable=False),
        sqlalchemy.Column('display_name', sqlalchemy.String(80), nullable=False),
        sqlalchemy.Column('docker_host', sqlalchemy.String(255), nullable=False),
        sqlalchemy.Column('total_cores', sqlalchemy.Float(), nullable=True),
        sqlalchemy.Column('total_memory', sqlalchemy.Integer(), nullable=True),
        sqlalchemy.Column('enabled', sqlalchemy.Boolean(), nullable=False, server_default='1'),
        sqlalchemy.Column('prune_mode', sqlalchemy.String(20), nullable=False, server_default='off'),
        sqlalchemy.Column('api_url', sqlalchemy.String(255), nullable=True),
        sqlalchemy.Column('api_token', sqlalchemy.String(255), nullable=True),
        sqlalchemy.Column('healthy', sqlalchemy.Boolean(), nullable=True),
        sqlalchemy.Column('last_healthcheck_at', sqlalchemy.DateTime(), nullable=True),
        sqlalchemy.Column('created_at', sqlalchemy.DateTime(), server_default=sqlalchemy.text('CURRENT_TIMESTAMP'), nullable=True),
        sqlalchemy.PrimaryKeyConstraint('id'),
    )
    create_table('storage_provider',
        sqlalchemy.Column('id', sqlalchemy.UUID(), server_default=sqlalchemy.text("gen_random_uuid()"), nullable=False),
        sqlalchemy.Column('display_name', sqlalchemy.String(80), nullable=False),
        sqlalchemy.Column('enabled', sqlalchemy.Boolean(), nullable=False, server_default='1'),
        sqlalchemy.Column('provider_type', sqlalchemy.String(40), nullable=False, server_default='rclone'),
        sqlalchemy.Column('default_destination', sqlalchemy.String(255), nullable=False, server_default='/storage'),
        sqlalchemy.Column('volume_config', sqlalchemy.Text(), nullable=True),
        sqlalchemy.Column('created_at', sqlalchemy.DateTime(), server_default=sqlalchemy.text('CURRENT_TIMESTAMP'), nullable=True),
        sqlalchemy.PrimaryKeyConstraint('id'),
    )
    create_table('tide_agents',
        sqlalchemy.Column('tide_id', sqlalchemy.UUID(), nullable=False),
        sqlalchemy.Column('agent_id', sqlalchemy.UUID(), nullable=False),
        sqlalchemy.PrimaryKeyConstraint('tide_id', 'agent_id'),
        sqlalchemy.ForeignKeyConstraint(['tide_id'], ['tide.id'], ondelete='CASCADE', onupdate='CASCADE'),
        sqlalchemy.ForeignKeyConstraint(['agent_id'], ['agent.id'], ondelete='CASCADE', onupdate='CASCADE'),
    )
    create_table('tide_instance',
        sqlalchemy.Column('id', sqlalchemy.UUID(), server_default=sqlalchemy.text("gen_random_uuid()"), nullable=False),
        sqlalchemy.Column('tide_id', sqlalchemy.UUID(), nullable=False),
        sqlalchemy.Column('user_id', sqlalchemy.UUID(), nullable=False),
        sqlalchemy.Column('agent_id', sqlalchemy.UUID(), nullable=True),
        sqlalchemy.Column('vnc_password', sqlalchemy.String(32), nullable=True),
        sqlalchemy.Column('direct_url', sqlalchemy.String(512), nullable=True),
        sqlalchemy.Column('guac_token', sqlalchemy.String(), nullable=True),    
        sqlalchemy.Column('created_at', sqlalchemy.DateTime(), server_default=sqlalchemy.text('CURRENT_TIMESTAMP'), nullable=True),
        sqlalchemy.Column('updated_at', sqlalchemy.DateTime(), server_default=sqlalchemy.text('CURRENT_TIMESTAMP'), nullable=True),
        sqlalchemy.ForeignKeyConstraint(['tide_id'], ['tide.id'], ondelete='CASCADE', onupdate='CASCADE'),
        sqlalchemy.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE', onupdate='CASCADE'),
        sqlalchemy.ForeignKeyConstraint(['agent_id'], ['agent.id'], ondelete='CASCADE', onupdate='CASCADE'),
        sqlalchemy.PrimaryKeyConstraint('id'),
    )
    create_table('tide_storage_mount',
        sqlalchemy.Column('id', sqlalchemy.UUID(), server_default=sqlalchemy.text("gen_random_uuid()"), nullable=False),
        sqlalchemy.Column('tide_id', sqlalchemy.UUID(), nullable=False),
        sqlalchemy.Column('storage_provider_id', sqlalchemy.UUID(), nullable=False),
        sqlalchemy.Column('enabled', sqlalchemy.Boolean(), nullable=False, server_default='1'),
        sqlalchemy.Column('read_only', sqlalchemy.Boolean(), nullable=False, server_default='0'),
        sqlalchemy.Column('destination', sqlalchemy.String(255), nullable=True),
        sqlalchemy.PrimaryKeyConstraint('id'),
        sqlalchemy.ForeignKeyConstraint(['tide_id'], ['tide.id'], ondelete='CASCADE', onupdate='CASCADE'),
        sqlalchemy.ForeignKeyConstraint(['storage_provider_id'], ['storage_provider.id'], ondelete='CASCADE', onupdate='CASCADE'),
    )

    # Seed: default groups
    bulk_insert(group_table, [
        {
            'id': "00000000-0000-0000-0000-000000000000",
            'display_name': 'Admin',
            'protected': True,
            'perm_admin_panel': True,
            'perm_view_instances': True,
            'perm_edit_instances': True,
            'perm_view_users': True,
            'perm_edit_users': True,
            'perm_view_tides': True,
            'perm_edit_tides': True,
            'perm_view_registry': True,
            'perm_edit_registry': True,
            'perm_view_groups': True,
            'perm_edit_groups': True,
            'priority': 10000,
            'settings': {}
        },
        {
            'id': "00000000-0000-0000-0000-000000000001",
            'display_name': 'User',
            'protected': True,
            'perm_admin_panel': False,
            'perm_view_instances': False,
            'perm_edit_instances': False,
            'perm_view_users': False,
            'perm_edit_users': False,
            'perm_view_tides': False,
            'perm_edit_tides': False,
            'perm_view_registry': False,
            'perm_edit_registry': False,
            'perm_view_groups': False,
            'perm_edit_groups': False,
            'priority': 1,
            'settings': {}
        },
    ])

    # Seed: default registry
    bulk_insert(registry_table, [
        {'url': 'https://registry.kasmweb.com/1.1/'},
    ])

    # Seed: built-in local auth provider
    bulk_insert(auth_provider_table, [
        {
            'id': "00000000-0000-0000-0000-000000000000",
            'name': 'Local',
            'slug': 'local',
            'type': 'local',
            'priority': 0,
            'enabled': True,
            'settings': {},
        },
    ])


def downgrade():
    drop_table('tide_storage_mount')
    drop_table('tide_instance')
    drop_table('tide')
    drop_table('storage_provider')
    drop_table('agent')
    drop_table('auth_provider')
    drop_table('log')
    drop_table('registry')
    drop_table('user_groups')
    drop_table('trusted_device')
    drop_table('user')
    drop_table('group')
