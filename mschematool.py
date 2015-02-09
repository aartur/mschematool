#!/usr/bin/env python

import logging
import glob
import os
import os.path
import sys
import re
import shlex
import subprocess
import datetime
import imp
import warnings
import traceback

import click


log = logging.getLogger('schematool')


DEFAULT_CONFIG_MODULE_NAME = 'mschematool_config'

# Ignore warnings about installation of optimized versions
# of packages - irrelevant for the use case.
warnings.filterwarnings("ignore")


### Loading and processing configuration

class Config(object):

    def __init__(self, verbose, config_path):
        self.verbose = verbose
        self.config_path = config_path
        self._module = None

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

        if not os.path.exists(self.config_path):
            msg = 'Configuration module %r does not exist' % self.config_path
            sys.stderr.write(msg + '\n')
            log.critical(msg)
            raise Exception(msg)

        try:
            self._module = imp.load_source('mschematool_config', self.config_path)
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

def _assert_values_exist(d, *keys):
    for k in keys:
        assert d.get(k), 'No required value %r specified' % k

# Taken from https://bitbucket.org/andrewgodwin/south/src/74742a1ba41ce6e9ea56cc694c824b7a93934ac6/south/db/generic.py?at=default
def _sqlfile_to_statements(sql, regex=r"(?mx) ([^';]* (?:'[^']*'[^';]*)*)",
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


#### Migrations repositories

class MigrationsRepository(object):
    """A repository of migrations is a place where all available migrations are stored
    (for example a directory with migrations as files).
    """

    def get_migrations(self, exclude=None):
        """Return a sorted list of all migrations. In a common case a migration will be a filename,
        without a leading directory part.

        :param exclude: a list or set of migrations to exclude from the result
        """
        raise NotImplementedError()

    def generate_migration_name(self, name, suffix):
        """Returns a name of a new migration. It will usually be a filename with
        a valid and unique name.

        :param name: human-readable name of a migration
        :param suffix: file suffix (extension) - eg. 'sql'
        """
        return os.path.join(self.dir,
                            'm{datestr}_{name}.{suffix}'.format(
                                datestr=datetime.datetime.now().strftime('%Y%m%d%H%M%S'),
                                name=name.replace(' ', '_'),
                                suffix=suffix))

    def migration_type(self, migration):
        """Recognize migration type based on a migration (usually a filename).

        :return: 'native' or 'py'
        """
        if migration.endswith('.py'):
            return 'py'
        return 'native'


class DirRepository(MigrationsRepository):
    """:class:`MigrationsRepository` implementation with migrations being files
    inside a directory ``dir``. Example filenames:
    - m20140615132455_init.sql
    - m20140615135414_insert3.py

    :param migration_patterns: a list of glob expressions for selecting valid
        migration filenames, relative to ``dir``.
    """

    def __init__(self, dir, migration_patterns):
        self.dir = dir
        self.migration_patterns = migration_patterns

    def _get_all_filenames(self):
        filenames = []
        for pattern in self.migration_patterns:
            p_filenames = glob.glob(os.path.join(self.dir, pattern))
            filenames.extend(p_filenames)
        # lexicographical ordering
        filenames.sort()
        return filenames

    def get_migrations(self, exclude=None):
        filenames = self._get_all_filenames()
        filenames = [os.path.split(fn)[1] for fn in filenames]
        if exclude:
            filenames = set(filenames) - set(exclude)
            filenames = sorted(filenames)
        return filenames

#### Database-independent interface for migration-related operations

class MigrationsExecutor(object):
    """A class that executes migrations and stores information about execution.
    It will usually store this information inside a database for which migrations
    are tracked.

    :attr:`MigrationsExecutor.engine` is an engine name that can be referenced from
        a config module.
    :attr:`MigrationsExecutor.patterns` is a list of filename glob patterns
        specifying files which execution is supported.

    :param db_config: a dictionary with configuration for a single dbnick.
    :patam repository: :class:`MigrationsRepository` implementation.
    """

    engine = 'unknown'
    patterns = []

    def __init__(self, db_config, repository):
        self.db_config = db_config
        self.repository = repository

    def initialize(self):
        """Initialize resources needed for tracking migrations. It will usually
        create a database table for storing information about executed migrations.
        """
        raise NotImplementedError()

    def fetch_executed_migrations(self):
        """Return a list of executed migrations (filenames).
        """
        raise NotImplementedError()

    def execute_python_migration(self, migration, module):
        """Execute a migration written as Python code, and store information about it.

        :param migration: migration (filename) to be executed
        :param module: Python module imported from the migration
        """
        raise NotImplementedError()

    def execute_native_migration(self, migration):
        """Execute a migration in a format native to the DB (SQL file, CQL file etc.),
        and store information about it.

        :param migration: migration (filename) to be executed
        """
        raise NotImplementedError()

    def execute_migration(self, migration_file_relative):
        """This recognizes migration type and executes either
        :method:`execute_python_migration` or :method:`execute_native_migration`
        """
        migration_file = os.path.join(self.db_config['migrations_dir'], migration_file_relative)
        m_type = self.repository.migration_type(migration_file)
        if m_type == 'native':
            return self.execute_native_migration(migration_file)
        if m_type == 'py':
            module = imp.load_source('migration_module', migration_file)
            return self.execute_python_migration(migration_file, module)
        assert False, 'Unknown migration type %s' % migration_file



## Postgres


class PostgresMigrations(MigrationsExecutor):

    engine = 'postgres'

    patterns = ['m*.sql', 'm*.py']

    TABLE = 'migration'

    def __init__(self, db_config, repository):
        import psycopg2

        MigrationsExecutor.__init__(self, db_config, repository)

        self.conn = psycopg2.connect(self.db_config['dsn'])

    def cursor(self):
        import psycopg2.extras

        class PostgresLoggingDictCursor(psycopg2.extras.DictCursor):
            """Postgres cursor subclass: log all SQL executed in the database.
            """

            def __init__(self, *args, **kwargs):
                psycopg2.extras.DictCursor.__init__(self, *args, **kwargs)

            def execute(self, sql, args=None):
                if log.isEnabledFor(logging.INFO):
                    realsql = self.mogrify(sql, args)
                    log.info('Executing SQL: <<%s>>', _simplify_whitespace(realsql))
                try:
                    psycopg2.extras.DictCursor.execute(self, sql, args)
                except:
                    log.exception('Exception while executing SQL')
                    raise

        return self.conn.cursor(cursor_factory=PostgresLoggingDictCursor)

    def initialize(self):
        with self.cursor() as cur:
            cur.execute("""CREATE TABLE {table} (
                file TEXT,
                executed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""".format(table=self.TABLE))
            cur.connection.commit()

    def fetch_executed_migrations(self):
        with self.cursor() as cur:
            cur.execute("""SELECT file FROM {table}
            ORDER BY executed""".format(table=self.TABLE))
            return [row[0] for row in cur.fetchall()]

    def _migration_success(self, migration_file):
        migration = os.path.split(migration_file)[1]
        with self.cursor() as cur:
            cur.execute("""INSERT INTO {table} (file) VALUES (%s)""".format(table=self.TABLE),
                    [migration])

    def execute_python_migration(self, migration_file, module):
        assert hasattr(module, 'migrate'), 'Python module must have `migrate` function accepting ' \
            'a database connection'
        module.migrate(self.conn)
        self._migration_success(migration_file)
        self.conn.commit()

    def execute_native_migration(self, migration_file):
        with open(migration_file) as f:
            content = f.read()
        for statement in _sqlfile_to_statements(content):
            with self.cursor() as cur:
                cur.execute(statement)
        self._migration_success(migration_file)
        self.conn.commit()


### Cassandra

class CassandraMigrations(MigrationsExecutor):

    engine = 'cassandra'

    patterns = ['m*.cql', 'm*.py']

    TABLE = 'migration'

    def __init__(self, db_config, repository):
        MigrationsExecutor.__init__(self, db_config, repository)

        _assert_values_exist(db_config, 'cqlsh_path', 'pylib_path', 'keyspace', 'cluster_kwargs')

        if db_config['pylib_path'] not in sys.path:
            sys.path.append(db_config['pylib_path'])

        # Import cqlsh script as a module. Clear sys.argv when doing it to prevent
        # the script from parsing our command line.
        orig_sys_argv = sys.argv
        sys.argv = [db_config['cqlsh_path']]
        imp.load_source('cqlsh', db_config['cqlsh_path'])
        import cqlsh
        sys.argv = orig_sys_argv

        from cqlshlib import cql3handling
        cqlsh.setup_cqlruleset(cql3handling)
        
        import cassandra.cluster
        self.cluster = cassandra.cluster.Cluster(**self.db_config['cluster_kwargs'])

    def _session(self):
        return self.cluster.connect(self.db_config['keyspace'])

    def initialize(self):
        session = self._session()
        session.execute("""CREATE TABLE IF NOT EXISTS {table} (
            file text,
            executed timestamp,
            PRIMARY KEY (file))
            """.format(table=self.TABLE))

    def fetch_executed_migrations(self):
        session = self._session()
        rows = session.execute("""SELECT file, executed FROM {table}""".format(table=self.TABLE))
        rows.sort(key=lambda row: row.executed)
        return [row.file for row in rows]

    def _migration_success(self, migration_file):
        migration = os.path.split(migration_file)[1]
        session = self._session()
        session.execute("""INSERT INTO {table} (file, executed) VALUES (%s, %s)""".\
                        format(table=self.TABLE),
                        [migration, datetime.datetime.now()])

    def execute_python_migration(self, migration_file, module):
        assert hasattr(module, 'migrate'), 'Python module must have `migrate` function accepting ' \
            'a Cluster object'
        module.migrate(self.cluster)
        self._migration_success(migration_file)

    def execute_native_migration(self, migration_file):
        import cqlsh
        import cassandra.protocol

        with open(migration_file) as f:
            content = f.read()
        statements, _ = cqlsh.cqlruleset.cql_split_statements(content)
        to_execute = []
        for statement in statements:
            if not statement:
                continue
            _, _, (start, _) = statement[0]
            _, _, (_, end) = statement[-1]
            extracted = content[start:end]
            if not extracted:
                continue
            to_execute.append(extracted)
        session = self._session()
        for statement in to_execute:
            log.info('Executing CQL: <<%s>>', _simplify_whitespace(statement))
            try:
                session.execute(statement)
            except cassandra.protocol.ErrorMessage as e:
                click.echo('Error while executing statement %r' % statement)
                click.echo(repr(e))
                return
            except:
                log.exception('While executing statement %r', statement)
                raise
        self._migration_success(migration_file)


MIGRATIONS_IMPLS = [PostgresMigrations, CassandraMigrations]
ENGINE_TO_IMPL = {m.engine: m for m in MIGRATIONS_IMPLS}



### Integrating all the classes

class MSchemaTool(object):

    def __init__(self, config, dbnick):
        self.config = config
        self.dbnick = dbnick
        assert dbnick in config.module.DATABASES, 'Not found in DATABASES in config: %s' % dbnick
        self.db_config = config.module.DATABASES[dbnick]
        assert 'engine' in self.db_config and self.db_config['engine'] in ENGINE_TO_IMPL, \
            'Unknown or invalid engine specified, choose one of %s' % ENGINE_TO_IMPL.keys()
        engine_cls = ENGINE_TO_IMPL[self.db_config['engine']]
        self.repository = DirRepository(self.db_config['migrations_dir'], engine_cls.patterns)
        self.migrations = engine_cls(self.db_config, self.repository)

    def not_executed_migration_files(self):
        return self.repository.get_migrations(exclude=self.migrations.fetch_executed_migrations())

    def execute_after_sync(self):
        after_sync = self.db_config.get('after_sync')
        if not after_sync:
            return
        msg = 'Executing after_sync command %r' % after_sync
        log.info(msg)
        click.echo(msg)
        os.system(after_sync)

#### Commands

HELP = """Example usage:

$ ./mschematool.py default init_db

A database nickname defined in the configuration module must be passed as the first argument.
After it a command must be specified.

"""

@click.group(help=HELP)
@click.option('--config', type=click.Path(exists=True, dir_okay=False), envvar='MSCHEMATOOL_CONFIG', help='Path to configuration module, e.g. "mydir/mschematool_config.py". Environment variable MSCHEMATOOL_CONFIG can be specified instead.', required=True)
@click.option('--verbose/--no-verbose', default=False, help='Print executed SQL/CQL? Default: no.')
@click.argument('dbnick', type=str)
@click.pass_context
def main(ctx, config, verbose, dbnick):
    config_obj = Config(verbose, config)
    run_ctx = MSchemaTool(config_obj, dbnick)
    ctx.obj = run_ctx

@main.command(help='Creates a DB table used for tracking migrations.')
@click.pass_context
def init_db(ctx):
    ctx.obj.migrations.initialize()

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
    to_execute = ctx.obj.not_executed_migration_files()
    if not to_execute:
        click.echo('No migrations to sync')
        return
    for migration_file in to_execute:
        msg = 'Executing %s' % migration_file
        log.info(msg)
        click.echo(msg)
        ctx.obj.migrations.execute_migration(migration_file)
    ctx.obj.execute_after_sync()

@main.command(help='Sync a single migration, without syncing older ones.')
@click.argument('migration_file', type=str)
@click.pass_context
def force_sync_single(ctx, migration_file):
    if migration_file in ctx.obj.migrations.fetch_executed_migrations():
        click.echo('This migration is already executed')
        return
    msg = 'Force executing %s' % migration_file
    log.info(msg)
    click.echo(msg)
    ctx.obj.migrations.execute_migration(migration_file)
    ctx.obj.execute_after_sync()

@main.command(help='Print a filename for a new migration.')
@click.argument('name', type=str)
@click.argument('migration_type', type=click.Choice(['sql', 'cql', 'py']), default='sql')
@click.pass_context
def print_new(ctx, name, migration_type):
    """Prints filename of a new migration"""
    click.echo(ctx.obj.repository.generate_migration_name(name, migration_type))

@main.command(help='Show latest synced migration.')
@click.pass_context
def latest_synced(ctx):
    migrations = ctx.obj.migrations.fetch_executed_migrations()
    if not migrations:
        click.echo('No synced migrations')
    else:
        click.echo(migrations[-1])

if __name__ == '__main__':
    main()

