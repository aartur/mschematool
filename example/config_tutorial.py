DATABASES = {
        'default': {
            'migrations_dir': './migrations/',
            'engine': 'postgres',
            'dsn': 'host=127.0.0.1 dbname=mtutorial',
        },

        'other': {
            'migrations_dir': './migrations_other/',
            'engine': 'postgres',
            'dsn': 'host=127.0.0.1 dbname=mother',
            'after_sync': 'pg_dump -s mother > /tmp/mother_schema.sql',
        },

        'cass': {
            'migrations_dir': './tests/cass1',
            'engine': 'cassandra',
            'cqlsh_path': '/opt/cassandra/bin/cqlsh',
            'pylib_path': '/opt/cassandra/pylib',
            'keyspace': 'migrations',
            'cluster_kwargs': {
                'contact_points': ['127.0.0.1'],
                'port': 9042,
            },
        }
}

LOG_FILE = '/tmp/mtest1.log'
