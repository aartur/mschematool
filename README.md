mschematool
===========

mschematool is a simple tool for managing database migrations. Migrations are either SQL files or Python modules. They are ordered linearly using just lexicographical ordering of file names (with timestamp being a leading component). Information about executed migrations is stored inside a database for which migrations were executed in a simple table with file names only. The lightweight design enables changing the table contents manually, if necessary, and generally the tool tries to not enforce any hard rules.

Currently only PostgreSQL is supported.

Installation
============
The tool is available as a Python package, so the simplest method to install it is using `pip` (or `easy_install`):
```
$ pip install mschematool
```

Configuration
=============
Configuration file is a Python module listing available database and migration files locations:

```
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
```

We have two "dbnicks" (short database names): `default` and `other`. For each we specify options:
* `migrations_dir` is a directory with migrations files (note that it's usually not a good idea to use a relative path here).
* `engine` specifies database type
* `dsn` specifies database connection parameters for the `postgres` engine, as described here: http://www.postgresql.org/docs/current/static/libpq-connect.html#LIBPQ-CONNSTRING
* `after_sync` optionally specifies a shell command to run after a migration is synced (executed). In the case of `other` database a schema dump is performed.
* `LOG_FILE` optionally specifies a log file which will record all the executed SQL and other information useful for debugging.


Path to a configuration module can be specified using `--config` option or `MSCHEMATOOL_CONFIG` environment variable:
```
$ export MSCHEMATOOL_CONFIG=./config_tutorial.py
```
(again, it's better to use an absoulte path so the `mschematool` command will work from any directory).

Commands
========
Assuming the `mtutorial` database is created, we first need to initialize the database - create table `migration` for storing names of executed migrations.
```
$ mschematool default init_db
```
All commands are specified this way - the first argument is a "dbnick" from a config, the second is an actual command (run `mschematool --help` to see a short summary of commands).
