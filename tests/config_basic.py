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
}

LOG_FILE = '/tmp/mtest1.log'
