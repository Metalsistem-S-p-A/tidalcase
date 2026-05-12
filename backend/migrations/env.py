import logging
import logging.config
import flask
import alembic.context

config = getattr(alembic.context, 'config')
configure = getattr(alembic.context, 'configure')
begin_transaction = getattr(alembic.context, 'begin_transaction')
run_migrations = getattr(alembic.context, 'run_migrations')
is_offline_mode = getattr(alembic.context, 'is_offline_mode')

logging.config.fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')


def get_engine():
    try:
        return flask.current_app.extensions['migrate'].db.get_engine()
    except (TypeError, AttributeError):
        return flask.current_app.extensions['migrate'].db.engine


def get_engine_url():
    try:
        return get_engine().url.render_as_string(hide_password=False).replace('%', '%%')
    except AttributeError:
        return str(get_engine().url).replace('%', '%%')


config.set_main_option('sqlalchemy.url', get_engine_url())
target_db = flask.current_app.extensions['migrate'].db


def get_metadata():
    if hasattr(target_db, 'metadatas'):
        return target_db.metadatas[None]
    return target_db.metadata


def run_migrations_offline():
    url = config.get_main_option('sqlalchemy.url')
    configure(
        url=url,
        target_metadata=get_metadata(),
        literal_binds=True,
        dialect_opts={'paramstyle': 'named'},
    )
    with begin_transaction():
        run_migrations()


def run_migrations_online():
    def process_revision_directives(_context, _revision, directives):
        if getattr(config, 'cmd_opts', None) and config.cmd_opts.autogenerate:
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info('No changes in schema detected.')

    conf_args = flask.current_app.extensions['migrate'].configure_args
    if conf_args.get('process_revision_directives') is None:
        conf_args['process_revision_directives'] = process_revision_directives

    connectable = get_engine()

    with connectable.connect() as connection:
        configure(
            connection=connection,
            target_metadata=get_metadata(),
            **conf_args,
        )
        with begin_transaction():
            run_migrations()


if is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
