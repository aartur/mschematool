import logging
import os

import sqlite3

from mschematool import core


log = core.log


class Sqlite3LoggingCursor(sqlite3.Cursor):
    """SQLite3 cursor subclass: log all SQL executed in the database.
    """

    def __init__(self, *args, **kwargs):
        sqlite3.Cursor.__init__(self, *args, **kwargs)

    def execute(self, sql, *args):
        if log.isEnabledFor(logging.INFO):
            log.info('Executing SQL: <<%s>> with args: <<%s>>', core._simplify_whitespace(sql), args)
        try:
            sqlite3.Cursor.execute(self, sql, *args)
        except:
            log.exception('Exception while executing SQL')
            raise


class Sqlite3Migrations(core.MigrationsExecutor):

    engine = 'sqlite3'
    filename_extensions = ['sql']

    TABLE = 'migration'

    def __init__(self, db_config, repository):
        core.MigrationsExecutor.__init__(self, db_config, repository)
        self.conn = sqlite3.connect(self.db_config['database'], **db_config.get('connect_kwargs', {}))
        # Ensure we return dict/tuple-based access instead of just tuples
        self.conn.row_factory = sqlite3.Row

    def cursor(self):
        return self.conn.cursor(Sqlite3LoggingCursor)

    def initialize(self):
        cur = self.cursor()
        cur.execute("""SELECT EXISTS(SELECT * FROM sqlite_master
                       WHERE tbl_name=?)""", (self.TABLE,))
        already_exists = cur.fetchone()[0]
        if not already_exists:
            cur.execute("""CREATE TABLE {table} (
                file TEXT,
                executed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""".format(table=self.TABLE))
            cur.connection.commit()

    def fetch_executed_migrations(self):
        cur = self.cursor()
        cur.execute("""SELECT file FROM {table}
                       ORDER BY executed""".format(table=self.TABLE))
        return [row[0] for row in cur.fetchall()]

    def _migration_success(self, migration_file):
        migration = os.path.split(migration_file)[1]
        self.cursor().execute("""INSERT INTO {table} (file) VALUES (?)""".format(table=self.TABLE),
                              (migration,))

    def execute_python_migration(self, migration_file, module):
        assert hasattr(module, 'migrate'), 'Python module must have `migrate` function accepting ' \
            'a database connection'
        self._call_migrate(module, self.conn)
        self._migration_success(migration_file)
        self.conn.commit()

    def execute_native_migration(self, migration_file):
        with open(migration_file) as f:
            content = f.read()
        for statement in core._sqlfile_to_statements(content):
            self.cursor().execute(statement)
        self._migration_success(migration_file)
        self.conn.commit()


