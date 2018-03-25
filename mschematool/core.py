import logging
import glob
import os
import os.path
import sys
import re
import subprocess
import datetime
import imp
import warnings
import traceback
import importlib
import inspect
import sqlparse

import click


log = logging.getLogger('mschematool')

DEFAULT_CONFIG_MODULE_NAME = 'mschematool_config'


# Ignore warnings about installation of optimized versions
# of packages - irrelevant for the use case.
warnings.filterwarnings('ignore')


### Utility functions

def _simplify_whitespace(s):
    return b' '.join(s.split())

def _assert_values_exist(d, *keys):
    for k in keys:
        assert d.get(k), 'No required value %r specified' % k

def _import_class(cls_path):
    modname, _, clsname = cls_path.rpartition('.')
    mod = importlib.import_module(modname)
    return getattr(mod, clsname)


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


def _sqlfile_to_statements(sql):
    """
    Takes a SQL string containing 0 or more statements and returns a 
    list of individual statements as strings. Comments and
    empty statements are ignored.
    """
    statements = (sqlparse.format(stmt, strip_comments=True).strip() for stmt in sqlparse.split(sql))
    return [stmt for stmt in statements if stmt]

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
                                datestr=datetime.datetime.utcnow().strftime('%Y%m%d%H%M%S'),
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
    :attr:`MigrationsExecutor.file_extensions` is a list of filename extensions
        specifying files which execution is supported, in addition to 'py' and
        the engine name.

    :param db_config: a dictionary with configuration for a single dbnick.
    :param repository: :class:`MigrationsRepository` implementation.
    """

    engine = 'unknown'
    filename_extensions = []

    def __init__(self, db_config, repository):
        self.db_config = db_config
        self.repository = repository

    @classmethod
    def supported_filename_globs(cls):
        def glob_from_ext(ext):
            return '*.%s' % ext
        default_globs = [glob_from_ext('py'), glob_from_ext(cls.engine)]
        custom_globs = [glob_from_ext(ext) for ext in cls.filename_extensions]
        return default_globs + custom_globs

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

    def _call_migrate(self, module, connection_param):
        """Subclasses should call this method instead of `module.migrate` directly,
        to support `db_config` optional argument.
        """
        args = [connection_param]
        spec = inspect.getargspec(module.migrate)
        if len(spec.args) == 2:
            args.append(self.db_config)
        return module.migrate(*args)

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



ENGINE_TO_IMPL = {
    'postgres': 'mschematool.executors.postgres.PostgresMigrations',
    'cassandra': 'mschematool.executors.cassandradb.CassandraMigrations',
    'sqlite3': 'mschematool.executors.sqlite3db.Sqlite3Migrations',
}



### Integrating all the classes

class MSchemaTool(object):

    def __init__(self, config, dbnick):
        self.config = config
        self.dbnick = dbnick

        if dbnick not in config.module.DATABASES:
            raise click.ClickException('Not found in DATABASES in config: %s, available: %s' % (dbnick, ', '.join(config.module.DATABASES.keys())))
        self.db_config = config.module.DATABASES[dbnick]

        if 'engine' not in self.db_config or self.db_config['engine'] not in ENGINE_TO_IMPL:
            raise click.ClickException('Unknown or invalid engine specified for the database %s, choose one of %s' % (dbnick, ENGINE_TO_IMPL.keys()))
        engine_cls = _import_class(ENGINE_TO_IMPL[self.db_config['engine']])

        self.repository = DirRepository(self.db_config['migrations_dir'], engine_cls.supported_filename_globs())
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

