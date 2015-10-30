import os.path

BASE_DIR = os.path.dirname(os.path.realpath(__file__))

DATABASES = {
        'default': {
            'migrations_dir': os.path.join(BASE_DIR, 'migrations1'),
            'engine': 'postgres',
            'dsn': 'host=127.0.0.1 dbname=mtest1',
            'after_sync': 'pg_dump mtest1 > /tmp/mtest1.sql',
        },

        'error': {
            'migrations_dir': os.path.join(BASE_DIR, 'migrations_error'),
            'engine': 'postgres',
            'dsn': 'host=127.0.0.1 dbname=mtest1',
        },

        'extensions1': {
            'migrations_dir': os.path.join(BASE_DIR, 'extensions1'),
            'engine': 'postgres',
            'dsn': 'host=127.0.0.1 dbname=mtest1',
        },

        'migrate_args': {
            'migrations_dir': os.path.join(BASE_DIR, 'migrate_args'),
            'engine': 'postgres',
            'dsn': 'host=127.0.0.1 dbname=mtest1',
        },

        'cass_default': {
            'migrations_dir': os.path.join(BASE_DIR, 'cass1'),
            'engine': 'cassandra',
            'cqlsh_path': '/opt/cassandra/bin/cqlsh',
            'pylib_path': '/opt/cassandra/pylib',
            'keyspace': 'migrations',
            'cluster_kwargs': {
                'contact_points': ['127.0.0.1'],
                'port': 9042,
            },
        },

        'sqlite3_default': {
            'migrations_dir': os.path.join(BASE_DIR, 'migrations1'),
            'engine': 'sqlite3',
            'database': '/tmp/sqlite3test.sql',
            'connect_kwargs': {
            },
        }
}

LOG_FILE = '/tmp/mtest1.log'
