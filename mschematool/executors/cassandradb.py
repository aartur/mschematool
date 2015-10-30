import os.path
import sys
import imp
import datetime

import cassandra.cluster
import cassandra.protocol
import click

from mschematool import core


log = core.log


class CassandraMigrations(core.MigrationsExecutor):

    engine = 'cassandra'
    filename_extensions = ['cql']

    TABLE = 'migration'

    def __init__(self, db_config, repository):
        core.MigrationsExecutor.__init__(self, db_config, repository)
        core._assert_values_exist(db_config, 'cqlsh_path', 'pylib_path', 'keyspace', 'cluster_kwargs')
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
        self._call_migrate(module, self.cluster)
        self._migration_success(migration_file)

    def execute_native_migration(self, migration_file):
        import cqlsh

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
            log.info('Executing CQL: <<%s>>', core._simplify_whitespace(statement))
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

