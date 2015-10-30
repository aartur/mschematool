#!/usr/bin/env python

"""WARNING: running code from this file might destroy existing databases or tables.

This file contains integration tests. Tests invoke mschematool commands using
subprocess module and check command output and database contents.

For tests using SQLite3, it only requires write access in /tmp.

For tests using PostgreSQL, you need a locally running Postgres server and
commands:
$ createdb mtest1
$ dropdb mtest1
working without additional arguments.

For tests using Cassandra, you need a locally running Cassandra server that
accepts local connections without authorization. WARNING: running tests will
drop 'migrations' keyspace on the default cluster.

To execute tests, run (CWD must be the directory of this file):

$ ./test_basic.py # postgres + cassandra
$ ./test_basic CassandraTestBasic # cassandra
$ ./test_basic PostgresTestBasic # postgres
$ ./test_basic Sqlite3TestBasic # sqlite3
"""

import unittest
import os
import shlex
import subprocess
import sys
import imp
import traceback


sys.path.append('.')


class RunnerBase(object):

    def __init__(self, config, dbnick):
        self.config = config
        self.dbnick = dbnick
        self.config_module = imp.load_source('mschematool_config', self.config)
        self.last_retcode = None

    def run(self, cmd):
        os.environ['PYTHONPATH'] = '..'
        full_cmd = '../mschematool/cli.py --config {self.config} --verbose {self.dbnick} {cmd}'.format(self=self,
                                                                                         cmd=cmd)
        sys.stderr.write(full_cmd + '\n')
        try:
            out = subprocess.check_output(shlex.split(full_cmd))
        except subprocess.CalledProcessError as e:
            self.last_retcode = e.returncode
            out = e.output
        except:
            self.last_retcode = None
            sys.stderr.write(traceback.format_exc() + '\n')
            out = ''
        else:
            self.last_retcode = 0
        sys.stderr.write(out.decode('unicode_escape'))
        return out.decode('unicode_escape').strip()

    def close(self):
        pass


class RunnerPostgres(RunnerBase):

    def __init__(self, config, dbnick):
        import psycopg2
        RunnerBase.__init__(self, config, dbnick)
        self.conn = psycopg2.connect(self.config_module.DATABASES[self.dbnick]['dsn'])

    def cursor(self):
        import psycopg2.extras
        return self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    def close(self):
        self.conn.close()


class RunnerCassandra(RunnerBase):

    def __init__(self, config, dbnick):
        import cassandra.cluster

        RunnerBase.__init__(self, config, dbnick)

        assert self.config_module.DATABASES[dbnick]['engine'] == 'cassandra'
        self.cluster = cassandra.cluster.Cluster(**self.config_module.DATABASES[self.dbnick]\
                                                 ['cluster_kwargs'])
        self.keyspace = self.config_module.DATABASES[self.dbnick]['keyspace']
        s = self.cluster.connect()
        s.execute("""CREATE KEYSPACE IF NOT EXISTS {keyspace} WITH REPLICATION = {{ 'class' : 'SimpleStrategy', 'replication_factor' : 1 }}""".format(keyspace=self.keyspace))
        s.shutdown()

    def session(self):
        s = self.cluster.connect()
        return s

    def close(self):
        self.cluster.shutdown()

class RunnerSqlite3(RunnerBase):

    def __init__(self, config, dbnick):
        import sqlite3

        RunnerBase.__init__(self, config, dbnick)

        dbconfig = self.config_module.DATABASES[self.dbnick]
        try:
            os.unlink(dbconfig['database'])
        except OSError:
            pass
        assert dbconfig['engine'] == 'sqlite3'
        self.conn = sqlite3.connect(dbconfig['database'], **dbconfig['connect_kwargs'])

    def cursor(self):
        return self.conn.cursor()

    def close(self):
        try:
            dbconfig = self.config_module.DATABASES[self.dbnick]
            os.unlink(dbconfig['database'])
        except OSError:
            pass


### Tests common to all databases

class CommonTests(object):

    def testInitdbIdempotency(self):
        self.r.run('init_db')
        self.assertEqual(0, self.r.last_retcode)
        self.r.run('init_db')
        self.assertEqual(0, self.r.last_retcode)


### Postgres tests


class PostgresTestBase(unittest.TestCase):
    db = 'mtest1'
    dbnick = 'default'
    schema_file = '/tmp/mtest1.sql'

    def setUp(self):
        os.system('createdb %s' % self.db)
        self.r = RunnerPostgres('config_basic.py', self.dbnick)

    def tearDown(self):
        self.r.close()
        os.system('dropdb %s' % self.db)
        try:
            os.unlink(self.schema_file)
        except OSError:
            pass


class PostgresTestBasic(PostgresTestBase, CommonTests):

    def testInitdb(self):
        self.r.run('init_db')
        with self.r.cursor() as cur:
            cur.execute("""SELECT EXISTS(SELECT * FROM information_schema.tables
                           WHERE table_name='migration')""")
            self.assertTrue(cur.fetchone()[0])

    def testToSync(self):
        self.r.run('init_db')
        out = self.r.run('to_sync')
        self.assertEqual(5, len(out.split('\n')))

    def testSync(self):
        self.r.run('init_db')
        self.r.run('sync')
        with self.r.cursor() as cur:
            cur.execute("""SELECT COUNT(*) FROM article""")
            self.assertEqual(4, cur.fetchone()[0])

    def testLatestSynced(self):
        self.r.run('init_db')
        self.r.run('sync')
        out = self.r.run('latest_synced')
        assert out.endswith('m20140615135414_insert3.py')

    def testForceSyncSingle(self):
        self.r.run('init_db')
        self.r.run('force_sync_single m20140615132456_init2.sql')

        out = self.r.run('synced')
        self.assertEqual(1, len(out.split('\n')))

        out = self.r.run('latest_synced')
        assert out.endswith('m20140615132456_init2.sql')

    def testPrintNew(self):
        self.r.run('init_db')
        out = self.r.run('print_new xxx')
        assert out.endswith('_xxx.sql'), out

    def testPrintNewPy(self):
        self.r.run('init_db')
        out = self.r.run('print_new xxx py')
        assert out.endswith('_xxx.py'), out


class PostgresTestSpecial(PostgresTestBase):
    dbnick = 'error'

    def testSync(self):
        self.r.run('init_db')
        self.r.run('sync')
        with self.r.cursor() as cur:
            cur.execute("""SELECT COUNT(*) FROM article""")
            self.assertEqual(1, cur.fetchone()[0])


### Cassandra tests


class CassandraTestBasic(unittest.TestCase, CommonTests):

    def setUp(self):
        self.r = RunnerCassandra('config_basic.py', 'cass_default')

    def tearDown(self):
        s = self.r.session()
        s.execute("""DROP KEYSPACE IF EXISTS migrations""")
        s.execute("""DROP KEYSPACE IF EXISTS mtest""")
        self.r.close()

    def testInitdb(self):
        self.r.run('init_db')
        s = self.r.session()
        rows = s.execute("""SELECT columnfamily_name FROM system.schema_columnfamilies
            WHERE columnfamily_name=%s AND keyspace_name=%s""", ['migration', 'migrations'])
        self.assertEqual(1, len(rows))

    def testToSync(self):
        self.r.run('init_db')
        out = self.r.run('to_sync')
        self.assertEqual(6, len(out.split('\n')))

    def testSync(self):
        self.r.run('init_db')
        self.r.run('sync')
        s = self.r.session()
        rows = s.execute("""SELECT COUNT(*) FROM mtest.article""")
        self.assertEqual(4, rows[0].count)

    def testLatestSynced(self):
        self.r.run('init_db')
        self.r.run('sync')
        out = self.r.run('latest_synced')
        assert out.endswith('m20140615133009_insert2.cql'), repr(out)

    def testForceSyncSingle(self):
        self.r.run('init_db')
        self.r.run('force_sync_single m20140615132456_init2.cql')

        out = self.r.run('synced')
        self.assertEqual(1, len(out.split('\n')))

        out = self.r.run('latest_synced')
        assert out.endswith('m20140615132456_init2.cql')

    def testPrintNew(self):
        self.r.run('init_db')
        out = self.r.run('print_new xxx cql')
        assert out.endswith('_xxx.cql'), out


### Sqlite3 tests

class Sqlite3TestBasic(unittest.TestCase, CommonTests):

    def setUp(self):
        self.r = RunnerSqlite3('config_basic.py', 'sqlite3_default')

    def tearDown(self):
        self.r.close()

    def testInitdb(self):
        self.r.run('init_db')
        cur = self.r.cursor()
        cur.execute("""SELECT EXISTS(SELECT * FROM sqlite_master
        WHERE tbl_name='migration')""")
        self.assertTrue(cur.fetchone()[0])

    def testToSync(self):
        self.r.run('init_db')
        out = self.r.run('to_sync')
        self.assertEqual(5, len(out.split('\n')))

    def testSync(self):
        self.r.run('init_db')
        self.r.run('sync')
        cur = self.r.cursor()
        cur.execute("""SELECT COUNT(*) FROM article""")
        self.assertEqual(4, cur.fetchone()[0])

    def testLatestSynced(self):
        self.r.run('init_db')
        self.r.run('sync')
        out = self.r.run('latest_synced')
        assert out.endswith('m20140615135414_insert3.py')

    def testForceSyncSingle(self):
        self.r.run('init_db')
        self.r.run('force_sync_single m20140615132456_init2.sql')

        out = self.r.run('synced')
        self.assertEqual(1, len(out.split('\n')))

        out = self.r.run('latest_synced')
        assert out.endswith('m20140615132456_init2.sql')

    def testPrintNew(self):
        self.r.run('init_db')
        out = self.r.run('print_new xxx')
        assert out.endswith('_xxx.sql'), out

    def testPrintNewPy(self):
        self.r.run('init_db')
        out = self.r.run('print_new xxx py')
        assert out.endswith('_xxx.py'), out


if __name__ == '__main__':
    unittest.main()
