DATABASES = {
        'default': {
            'migrations_dir': './migrations/',
            'engine': 'postgres',
            'dsn': 'host=127.0.0.1 dbname=mtutorial',
        },

        'sqlite3': {
            'migrations_dir': './migrations/',
            'engine': 'sqlite3',
            # First "database" argument to sqlite3.connect()
            'database': './dbname.sq3',
        },

        'sqlite3-readonly': {
            'migrations_dir': './migrations/',
            'engine': 'sqlite3',
            'database': 'file:./dbname.sq3?mode=ro',
            'connect_kwargs': {
                # Named "uri" argument to sqlite3.connect(), changes how
                # database argument is interpreted.
                'uri': True,
            },
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
