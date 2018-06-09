import os.path

BASE_DIR = os.path.dirname(os.path.realpath(__file__))

_postgres_dsn = 'dbname=mtest1'

DATABASES = {
        'default': {
            'migrations_dir': os.path.join(BASE_DIR, 'migrations1'),
            'engine': 'postgres',
            'dsn': _postgres_dsn,
            'after_sync': 'pg_dump mtest1 > /tmp/mtest1.sql',
        },

        'error': {
            'migrations_dir': os.path.join(BASE_DIR, 'migrations_error'),
            'engine': 'postgres',
            'dsn': _postgres_dsn,
        },

        'extensions1': {
            'migrations_dir': os.path.join(BASE_DIR, 'extensions1'),
            'engine': 'postgres',
            'dsn': _postgres_dsn,
        },

        'migrate_args': {
            'migrations_dir': os.path.join(BASE_DIR, 'migrate_args'),
            'engine': 'postgres',
            'dsn': _postgres_dsn,
        },

        'different_schema': {
            'migrations_dir': os.path.join(BASE_DIR, 'different_schema'),
            'engine': 'postgres',
            'dsn': _postgres_dsn,
            'migration_table': 'hooli.migration'
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
