DATABASES = {
        'default': {
            'migrations_dir': '/tmp/m1',
            'engine': 'postgres',
            'schema_file': '/tmp/schema.sql',
            'dsn': 'host=127.0.0.1 dbname=nut',
            'schema_dump_cmd': 'pg_dump -s nut',
        },
}

LOG_FILE = '/tmp/schematool.log'
