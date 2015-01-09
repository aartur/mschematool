#!/usr/bin/env python

"""This file contains integration tests. Tests invoke mschematool commands using
subprocess module and check command output and database contents.

To run it, you need a running PostgreSQL database and commands

$ createdb mtest1
$ dropdb mtest1

working without additional arguments.

To execute tests, run (CWD must be the directory of this file):

$ ./test_basic.py
"""

import unittest
import os
import shlex
import subprocess
import sys
import imp
import traceback

import psycopg2
import psycopg2.extras


sys.path.append('.')


class RunnerBase(object):

    def __init__(self, config, dbnick):
        self.config = config
        self.dbnick = dbnick
        self.config_module = imp.load_source('mschematool_config', self.config)

    def run(self, cmd):
        full_cmd = '../mschematool.py --config {self.config} {self.dbnick} {cmd}'.format(self=self,
                                                                                         cmd=cmd)
        sys.stderr.write(full_cmd + '\n')
        try:
            out = subprocess.check_output(shlex.split(full_cmd))
        except:
            print traceback.format_exc()
            return ''
        sys.stderr.write(out)
        return out.strip()

    def close(self):
        pass


class RunnerPostgres(RunnerBase):

    def __init__(self, config, dbnick):
        RunnerBase.__init__(self, config, dbnick)
        self.conn = psycopg2.connect(self.config_module.DATABASES[self.dbnick]['dsn'])

    def cursor(self):
        return self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    def close(self):
        self.conn.close()


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


class PostgresTestBasic(PostgresTestBase):

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


if __name__ == '__main__':
    unittest.main()
