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
}

LOG_FILE = '/tmp/mtest1.log'
