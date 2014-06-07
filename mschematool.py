#!/usr/bin/env python

import logging
import glob
import os.path
import sys
import re
import importlib
import shlex
import subprocess
import datetime

import psycopg2
import psycopg2.extensions
import psycopg2.extras

import click


log = logging.getLogger('schematool')


DEFAULT_CONFIG_MODULE_NAME = 'mschematool_config'

MIGRATION_PATTERN_SQL = 'm*.sql'
MIGRATION_PATTERN_PY = 'm*.py'


### Loading configuration

class Config(object):

    def __init__(self, verbose, config_module=None):
        self.verbose = verbose
        self.config_module = config_module
        self._module = None

    def setup_pythonpath_for_migrations(self, dbnick):
        sys.path.append(self.module.DATABASES[dbnick]['migrations_dir'])

    def _setup_logging(self):
        global log
        log.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)-15s %(message)s')
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.DEBUG)
        if self.verbose:
            log.addHandler(console_handler)
        if hasattr(self.module, 'LOG_FILE'):
            file_handler = logging.FileHandler(self.module.LOG_FILE)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            log.addHandler(file_handler)

    def _load_config(self):
        if self._module is not None:
            return

        module_from_env = os.getenv('MSCHEMATOOL_CONFIG_MODULE')
        if self.config_module is not None:
            module_name = self.config_module
        elif module_from_env:
            log.info('Importing config module from env. variable MSCHEMATOOL_CONFIG_MODULE: %s',
                    module_from_env)
            module_name = module_from_env
        else:
            log.info('Importing default config module %s', DEFAULT_CONFIG_MODULE_NAME)
            module_name = DEFAULT_CONFIG_MODULE_NAME

        try:
            self._module = importlib.import_module(module_name)
        except ImportError:
            msg = 'Cannot import mschematool config module'
            sys.stderr.write(msg + '\n')
            log.critical(msg)
            raise

        self._setup_logging()

    @property
    def module(self):
        self._load_config()
        return self._module


### Utility functions

def _simplify_whitespace(s):
    return ' '.join(s.split())


#### Database-independent interface for migration-related operations

class MigrationsBase(object):

    engine = 'unknown'

    def __init__(self, db_config): raise NotImplementedError()

    def initialize_db(self): raise NotImplementedError()

    def fetch_executed_migrations(self): raise NotImplementedError()

    def execute_python_migration(self, migration_file, module): raise NotImplementedError()

    def execute_sql_migration(self, migration_file): raise NotImplementedError()

    def execute_migration(self, migration_file_relative):
        migration_file = os.path.join(self.db_config['migrations_dir'], migration_file_relative)
        if migration_file.endswith('.sql'):
            return self.execute_sql_migration(migration_file)
        if migration_file.endswith('.py'):
            module = importlib.import_module(migration_file[:-len('.py')])
            return self.execute_python_migration(migration_file, module)
        assert False, 'Unknown migration type %s' % migration_file


    def dump_schema(self): raise NotImplementedError()


## Postgres

class PostgresLoggingDictCursor(psycopg2.extras.DictCursor):
    """Log all SQL executed in the database.
    """

    def __init__(self, *args, **kwargs):
        psycopg2.extras.DictCursor.__init__(self, *args, **kwargs)

    def execute(self, sql, args=None):
        global log
        if log.isEnabledFor(logging.INFO):
            realsql = self.mogrify(sql, args)
            log.info('Executing SQL: <<%s>>', _simplify_whitespace(realsql))
        try:
            psycopg2.extras.DictCursor.execute(self, sql, args)
        except:
            log.exception('Exception while executing SQL')
            raise


class PostgresMigrations(MigrationsBase):

    engine = 'postgres'

    def __init__(self, db_config):
        self.db_config = db_config
        self.conn = psycopg2.connect(self.db_config['dsn'])

    def cursor(self):
        return self.conn.cursor(cursor_factory=PostgresLoggingDictCursor)

    def initialize_db(self):
        with self.cursor() as cur:
            cur.execute("""CREATE TABLE schemamigration (
                migration_file TEXT,
                execution_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
            cur.connection.commit()

    def fetch_executed_migrations(self):
        with self.cursor() as cur:
            cur.execute("""SELECT migration_file FROM schemamigration
            ORDER BY execution_time""")
            return [row[0] for row in cur.fetchall()]

    def _migration_success(self, migration_file):
        with self.cursor() as cur:
            cur.execute("""INSERT INTO schemamigration (migration_file) VALUES (%s)""",
                    [migration_file])

    def execute_python_migration(self, migration_file, module):
        assert hasattr(module, 'do'), 'Python module must have `do` function accepting ' \
            'database connection'
        module.do(self.conn)
        self._migration_success(migration_file)
        self.conn.commit()

    # https://bitbucket.org/andrewgodwin/south/src/74742a1ba41ce6e9ea56cc694c824b7a93934ac6/south/db/generic.py?at=default
    def _sqlfile_to_statements(self, sql, regex=r"(?mx) ([^';]* (?:'[^']*'[^';]*)*)",
            comment_regex=r"(?mx) (?:^\s*$)|(?:--.*$)"):
        """
        Takes a SQL file and executes it as many separate statements.
        (Some backends, such as Postgres, don't work otherwise.)
        """
        # Be warned: This function is full of dark magic. Make sure you really
        # know regexes before trying to edit it.
        # First, strip comments
        sql = "\n".join([x.strip().replace("%", "%%") for x in re.split(comment_regex, sql) if x.strip()])
        # Now execute each statement
        return re.split(regex, sql)[1:][::2]

    def execute_sql_migration(self, migration_file):
        with open(migration_file) as f:
            content = f.read()
        for statement in self._sqlfile_to_statements(content):
            with self.cursor() as cur:
                cur.execute(statement)
        self._migration_success(migration_file)
        self.conn.commit()


    def dump_schema(self):
        if not self.db_config.get('schema_file'):
            return
        schema = subprocess.check_output(shlex.split(self.db_config['schema_dump_cmd']))
        with open(self.db_config['schema_file'], 'w') as f:
            f.write(schema)

#### Migration files repository


#### Parsing options

MIGRATIONS_IMPLS = [PostgresMigrations]
ENGINE_TO_IMPL = {m.engine: m for m in MIGRATIONS_IMPLS}


class RunContext(object):

    def __init__(self, config, dbnick):
        assert dbnick in config.module.DATABASES, 'Not found in DATABASES in config: %s' % dbnick
        self.config = config
        self.dbnick = dbnick
        self.db_config = config.module.DATABASES[dbnick]
        self.migrations = ENGINE_TO_IMPL[self.db_config['engine']](self.db_config)
        config.setup_pythonpath_for_migrations(self.dbnick)

    def not_executed_migration_files(self):
        executed = self.migrations.fetch_executed_migrations()
        available = self.get_filenames()
        not_executed = set(available) - set(executed)
        not_executed = sorted(not_executed)
        return not_executed

    def _get_all_filenames(self, base_dir):
        filenames = glob.glob(os.path.join(base_dir, MIGRATION_PATTERN_SQL)) + \
            glob.glob(os.path.join(base_dir, MIGRATION_PATTERN_PY))
        filenames.sort()
        return filenames

    def get_filenames(self):
        return self._get_all_filenames(self.db_config['migrations_dir'])

#### Commands

HELP = """Example usage:

$ ./mschematool.py my_db initdb

A database nickname defined in the configuration module must be passed as the first argument.
After it a command must be specified.

"""

@click.group(help=HELP)
@click.option('--config', type=str, envvar='MSCHEMATOOL', help='Configuration module, e.g. "mypkg.mschematool_config". Environment variable MSCHEMATOOL_CONFIG can be specified instead.')
@click.option('--verbose', type=bool, default=False, help='Print executed SQL')
@click.argument('dbnick', type=str)
@click.pass_context
def main(ctx, config, verbose, dbnick):
    config_obj = Config(verbose, config)
    run_ctx = RunContext(config_obj, dbnick)
    ctx.obj = run_ctx

@main.command(help='Create tables used for tracking migrations.')
@click.pass_context
def initdb(ctx):
    ctx.obj.migrations.initialize_db()

@main.command(help='Show synced migrations.')
@click.pass_context
def synced(ctx):
    migrations = ctx.obj.migrations.fetch_executed_migrations()
    for migration in migrations:
        click.echo(migration)


@main.command(help='Show migrations available for syncing.')
@click.pass_context
def to_sync(ctx):
    migrations = ctx.obj.not_executed_migration_files()
    for migration in migrations:
        click.echo(migration)

@main.command(help='Sync all available migrations.')
@click.pass_context
def sync(ctx):
    for migration_file in ctx.obj.not_executed_migration_files():
        msg = 'Executing migrations %s' % migration_file
        log.info(msg)
        click.echo(msg)
        ctx.obj.migrations.execute_migration(migration_file)
    ctx.obj.migrations.dump_schema()

@main.command(help='Sync a single migration, without syncing older ones.')
@click.argument('migration_file', type=str)
@click.pass_context
def force_sync_single(ctx, migration_file):
    msg = 'Force executing %s' % migration_file
    log.info(msg)
    click.echo(msg)
    ctx.obj.migrations.execute_migration(migration_file)
    ctx.obj.migrations.dump_schema()

@main.command(help='Print a filename for a new migration.')
@click.argument('name', type=str)
@click.pass_context
def print_new(ctx, name):
    '''Prints filename of a new migration'''
    print os.path.join(ctx.obj.db_config['migrations_dir'],
            'm{datestr}_{name}.sql'.format(
                datestr=datetime.datetime.now().strftime('%Y%m%d%H%M%S'),
                name=name.replace(' ', '_')))

@main.command(help='Show latest synced migration.')
@click.pass_context
def latest_synced(ctx):
    migrations = ctx.obj.migrations.fetch_executed_migrations()
    if not migrations:
        click.echo('No synced migrations')
    else:
        click.echo(executed[-1])

def dump_schema(dbnick):
    opts = ChoosenOptions(dbnick)
    opts.migrations.dump_schema()

if __name__ == '__main__':
    main()

