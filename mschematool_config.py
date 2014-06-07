DATABASES = {
        'default': {
            'migrations_dir': '/tmp/m1',
            'engine': 'postgres',
            'dsn': 'host=127.0.0.1 dbname=nut',

            'after_sync': 'pg_dump nut > /tmp/schema.sql',
        },
}

LOG_FILE = '/tmp/schematool.log'
