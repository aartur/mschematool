mschematool
===========

mschematool is a simple tool for managing database migrations.
Migrations are native SQL/CQL scripts or Python modules. Configuration is a Python module. More details:

* migrations are ordered using lexicographical comparison. Sample suggested filenames:
  * `m20140615133521_add_column_author.sql`
  * `m20140615135414_insert_data.py`
* information about executed migrations is stored inside a database for which migrations were executed in a simple table with file names and execution time only (it can be manually modified if needed)
* a configuration module can specify multiple database connections

Why the tool was created when similar already exist? Actually they have drawbacks that make them unsuitable for some scenarios, like: no support for native SQL format, Java installation requirement, no support for multiple databases, lack of robustness.

Supported databases
===================
* PostgreSQL
* Apache Cassandra
* SQLite3

Installation
============
The tool is available as a Python 2.7 package, so the simplest method to install it is using `pip` (or `easy_install`):
```
$ sudo pip install mschematool
```

This step will not install packages needed for using specific databases:
* for PostgreSQL, `psycopg2` Python package must be installed
* for Cassandra, `cassandra-driver` Python package must be installed. The tool also requires access to local Cassandra installation (see the next point).

Configuration
=============
Configuration file is a Python module listing available databases and migration files locations. The following example lists two PostgreSQL databases:

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
            'migration_table': 'mother_migrations',
        },
}

LOG_FILE = '/tmp/mtest1.log'
```

For each "dbnick" (a short database name - `default` and `other` in the example) a dictionary specifies a database. The following entries are common to all engines (not only PostgreSQL):
* `migrations_dir` is a directory with migrations files (note that it's usually not a good idea to use a relative path here).
* `engine` specifies database type.
* `after_sync` optionally specifies a shell command to run after a migration is synced (executed). In the case of `other` database a schema dump is performed.
* `LOG_FILE` is an optional global paremeter that specifies a log file which will record all the executed commands and other information useful for debugging.

## PostgreSQL specific options

* `dsn` specifies database connection parameters for the `postgres` engine, as described here: http://www.postgresql.org/docs/current/static/libpq-connect.html#LIBPQ-CONNSTRING
* `migration_table` optionally specifies the name of the table that keeps track of which migrations are already applied. The default is `"public.migration"`.

The `migration_table` option allows implementing a "migration table per schema" use case by configuring multiple `DATABASES` pointing to the same database, but differing in `migration_table`.


## Sqlite3 specific options

An example sqlite3 config:

```
import os.path
import sqlite3

BASE_DIR = os.path.dirname(os.path.realpath(__file__))

DATABASES = {
        'default': {
            'migrations_dir': os.path.join(BASE_DIR, 'migrations'),
            'engine': 'sqlite3',
            'database': os.path.join(BASE_DIR, 'db.sqlite3'),
            'connect_kwargs': {
                'detect_types': sqlite3.PARSE_DECLTYPES,
            },
        }
```

* `connect_kwargs` is a dictionary with keyword arguments specifying special options to [sqlite3.connect](https://docs.python.org/3/library/sqlite3.html#sqlite3.connect).  For example, if you pass `'uri': true`, the `database` keyword will be interpreted as an URI instead of a filename (which allows you to pass [various other options](https://sqlite.org/uri.html) for controlling sqlite3).

## Cassandra specific options

An example Cassandra config:

```
import os.path

BASE_DIR = os.path.dirname(os.path.realpath(__file__))

DATABASES = {
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
        }
}

```

* `cqlsh_path` is a path to the `cqlsh` binary which is a part of Cassandra installaion.
* `pylib_path` is a path to `pylib` subdirectory of a local Cassandra installation.
* `keyspace` is a name of a keyspace in which `migration` column family (table) should be stored. You should create it manually, eg.:
  ```CREATE KEYSPACE IF NOT EXISTS migrations WITH REPLICATION = { 'class' : 'SimpleStrategy', 'replication_factor' : 3 };```
* `cluster_kwargs` is a dictionary with keyword arguments specifying a database connection (they are ``__init__`` arguments for the `Cluster` Python class), as specified here: http://datastax.github.io/python-driver/api/cassandra/cluster.html#cassandra.cluster.Cluster

## Specifying configuration file

Path to a configuration module can be specified using `--config` option or `MSCHEMATOOL_CONFIG` environment variable:
```
$ export MSCHEMATOOL_CONFIG=./config_tutorial.py
```
(again, it's better to use an absolute path so the `mschematool` command will work from any directory).

Tutorial
========
The tutorial uses the configuration with PostgreSQL databases, listed above (the usage of a Cassandra database looks identical, except `.sql` file extension should be replaced with `.cql`). The commands will work when executed from `example` subdirectory of the repository and when `config_tutorial.py` is specified as the configuration.

Assuming the `mtutorial` Postgres database is created, we first need to initialize it - create the table `migration` for storing names of executed migrations.
```
$ mschematool default init_db
```
All commands are specified this way - the first argument is a "dbnick" from a config, the second is an actual command (run `mschematool --help` to see a short summary of commands).

Now given that we have a few migration files:
```
$ ls migrations 
m20140615132455_create_article.sql
m20140615133521_add_column_author.sql
m20140615135414_insert_data.py
```
we want to execute ("sync") them. But let's first check what the tool thinks is not executed yet:
```
$ mschematool default to_sync
m20140615132455_create_article.sql
m20140615133521_add_column_author.sql
m20140615135414_insert_data.py
```
Ok, so it sees all the migrations, so let's execute some SQL and Python:
```
$ mschematool default sync   
Executing m20140615132455_create_article.sql
Executing m20140615133521_add_column_author.sql
Executing m20140615135414_insert_data.py
```
And now no migration should be waiting for an execution:
```
$ mschematool default to_sync
$
```
`sync` command executes all migrations that weren't yet executed. To execute a single migration without executing all the other available for syncing, use `force_sync_single`:
```
$ mschematool default force_sync_single m20140615132455_create_article.sql
```

For more fine-grained control, the table `migration` can be modified manually. The content is simple:
```
$ psql mtutorial -c 'SELECT * FROM migration'
                 file                  |          executed          
---------------------------------------+----------------------------
 m20140615133521_add_column_author.sql | 2014-06-15 19:19:42.100535
 m20140615135414_insert_data.py        | 2014-06-15 19:19:42.101006
(2 rows)
```

Migrations
==========
An SQL migration is a file with SQL statements. All statements are executed within a single database transaction. It means that when one of statements fail, all the changes made by previous statements are ROLLBACKed and a migration isn't recorded as executed.

**WARNING**. Due to [sqlite3 module behaviour](http://bugs.python.org/issue10740) Sqlite migrations might not work as described above.

A CQL migration (Apache Cassandra) is a file with CQL statements delimited with a `;` character. When execution of a statement fails, a migration isn't recorded as executed, but changes made by previous statements aren't canceled (due to no support for transactions).

A Python migration is a file with `migrate` method that accepts a `connection` object:
* for Postgres, it's a DBAPI 2.0 connection. When an exception does not happen during execution, COMMIT is issued on a connection, so it isn't necessary to call `commit()` inside `migrate()`.
* for Cassandra, it's a [Cluster](http://datastax.github.io/python-driver/api/cassandra/cluster.html#cassandra.cluster.Cluster) instance.

A migration is marked as executed when no exception is raised.

## Example Postgres migrations
```
$ cat migrations/m20140615132455_create_article.sql
CREATE TABLE article (id int, body text);
CREATE INDEX ON article(id);

$ cat migrations/m20140615135414_insert_data.py 
def migrate(connection):
    cur = connection.cursor()
    for i in range(10):
        cur.execute("""INSERT INTO article (id, body) VALUES (%s, %s)""", [i, str(i)])
```

## Example Cassandra migrations

```
$ cat m20140615132456_init2.cql 
CREATE KEYSPACE IF NOT EXISTS mtest WITH REPLICATION = { 'class' : 'SimpleStrategy', 'replication_factor' : 1 };
CREATE TABLE mtest.author (name text, PRIMARY KEY(name));

$ cat m20140615135414_insert3.py
def migrate(cluster):
    session = cluster.connect('mtest')
    session.execute("""INSERT INTO article (id, body) VALUES (%s, %s)""", [10, 'xx'])

```

## Creating new migrations

A helper `print_new` command is available for creating new migration files - it just prints a suggested migration file name based on a description, using the current UTC date and time as a timestamp:
```
$ mschematool default print_new 'more changes'    
./migrations/m20140615194820_more_changes.sql
```

The `m` prefix makes a Python module implementing a migration to have a valid name (it can't start with a digit). However, the tool will see all filenames ending with `sql`, `cql`, `py`, so you can use a different naming convention. Moreover, the migrations are sorted using ordinary lexicographical comparison, so instead of a timestamp, other ordering mechanisms can be used (sequences like `001.sql 002.sql 003.sql`, or two-component names like `branchA_001.sql branchB_001.sql`).

## Dealing with dialect differences

If you support multiple SQL databases in your project, you can have a single directory with migrations specified for multiple `DATABASES` in the config. You can then use engine-specific filename extensions. Migrations having the `.sql` extension will be seen by all SQL engines. Migration filenames ending with an engine's name will be seen by the engine only.

For example, if you have these files:
```
001.sql
002.sqlite3
002.postgres
003.sqlite3
004.py
```
a `postgres` engine will execute `001.sql 002.postgres 004.py`, while an `sqlite3` engine will execute `001.sql 002.sqlite3 003.sqlite3 004.py`.

Python files are always executed for every
supported database. If you need to know for which engine an execution is perfomed, specify a second argument to the `migrate` function:
```
def migrate(connection, db_config):
    if db_config['engine'] == 'postgres':
        # ...
```
The `db_config` argument is a dictionary specified in `DATABASES` for which the execution is performed.

Note than in most cases, you won't
have to detect an engine, because most databases support the common API, from
[PEP 0249](https://www.python.org/dev/peps/pep-0249/).


Contributing and extending
==========================
Most of the functionality is implemented in subclasses of `MigrationsRepository` and `MigrationsExecutor` in `mschematool/core.py` file.

`MigrationsRepository` represents a repository of migrations available for execution, with the default implementation `DirRepository`, which is just a directory with files. You might want to create an alternative implemention if you need something more sophisticated.

`MigrationsExecutor` represents a part that deals with executing migrations and storing results in a table. If you want to add support for a new database, you should implement a subclass of this class (see the modules inside the `executors` package for examples).

For running integration tests see `tests/test_basic.py` docstrings (warning: running tests might destroy existing databases or tables).
