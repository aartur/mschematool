#!/usr/bin/env python

import unittest
import os
import shlex
import subprocess
import sys
import importlib

import psycopg2
import psycopg2.extras


sys.path.append('.')


class Runner(object):

    def __init__(self, config, dbnick):
        self.config = config
        self.dbnick = dbnick

        self.config_module = importlib.import_module(self.config)
        self.conn = psycopg2.connect(self.config_module.DATABASES[self.dbnick]['dsn'])

    def run(self, cmd):
        full_cmd = '../mschematool.py --config {self.config} {self.dbnick} {cmd}'.format(self=self,
                                                                                         cmd=cmd)
        sys.stderr.write(full_cmd + '\n')
        out = subprocess.check_output(shlex.split(full_cmd))
        sys.stderr.write(out)
        return out

    def cursor(self):
        return self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    def close(self):
        self.conn.close()


class TestBasic(unittest.TestCase):

    def setUp(self):
        os.system('createdb mtest1')
        self.r = Runner('config_basic', 'default')

    def testInitdb(self):
        self.r.run('init_db')
        with self.r.cursor() as cur:
            cur.execute("""SELECT EXISTS(SELECT * FROM information_schema.tables
                           WHERE table_name='schemamigration')""")
            self.assertTrue(cur.fetchone()[0])

    def tearDown(self):
        self.r.close()
        os.system('dropdb mtest1')


if __name__ == '__main__':
    unittest.main()
