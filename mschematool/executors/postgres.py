import logging
import os

import psycopg2
import psycopg2.extras

from mschematool import core


log = core.log


class PostgresLoggingDictCursor(psycopg2.extras.DictCursor):
    """Postgres cursor subclass: log all SQL executed in the database.
    """

    def __init__(self, *args, **kwargs):
        psycopg2.extras.DictCursor.__init__(self, *args, **kwargs)

    def execute(self, sql, args=None):
        if log.isEnabledFor(logging.INFO):
            realsql = self.mogrify(sql, args)
            log.info('Executing SQL: <<%s>>', core._simplify_whitespace(realsql))
        try:
            psycopg2.extras.DictCursor.execute(self, sql, args)
        except:
            log.exception('Exception while executing SQL')
            raise


class PostgresMigrations(core.MigrationsExecutor):

    engine = 'postgres'
    patterns = ['m*.sql', 'm*.py']

    TABLE = 'migration'

    def __init__(self, db_config, repository):
        core.MigrationsExecutor.__init__(self, db_config, repository)
        self.conn = psycopg2.connect(self.db_config['dsn'])

    def cursor(self):
        return self.conn.cursor(cursor_factory=PostgresLoggingDictCursor)

    def initialize(self):
        with self.cursor() as cur:
            cur.execute("""SELECT EXISTS(SELECT * FROM information_schema.tables
                           WHERE table_name=%s)""", [self.TABLE])
            already_exists = cur.fetchone()[0]
        if already_exists:
            return
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
        for statement in core._sqlfile_to_statements(content):
            with self.cursor() as cur:
                cur.execute(statement)
        self._migration_success(migration_file)
        self.conn.commit()


