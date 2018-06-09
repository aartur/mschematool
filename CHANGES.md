0.9
===

* new `postgres` option `migration_table` which allows configuring the name and the schema of the migration table (implemented by dirkgr)

**UPGRADING**. The default value of the new option is `public.migration`. If your existing migration table is already created in a different schema (e.g. you have specified default search path in `dsn`), you will need to set this option.


0.8
===

* use more robust SQL parsing using `sqlparse` (implemented by CrescentFresh)
* relax version dependency on `click` (previously, `==3.3` was specified, now no version is mentioned).


0.7.1
=====


* `print_new` commands uses a UTC datetime (see issue #6).

0.7
=====

**WARNING**. This release drops the requirement of migration files having the `m` prefix. All filenames ending with `.sql`, `.cql`, `.py`, `.postgres`, `.sqlite3` will be selected for execution. The tool might execute more files than previously (if your `migrations_dir` contains files that were previously skipped).

* SQLite3 support (implemented by Peter Bex)
* Support for engine-specific migrations
* `migrate` can receive the current `db_config`

0.6.5
=====

* Removed Python 3.4 from PyPI classifiers (Python 2.7 is required). Nonetheless, Postgres migrations will now work on Python 3.x.

0.6.4
=====

* setup.py from 0.6.3 was still broken, fixes and improvements by spinus

0.6.3
=====

* Fixed setup.py script, 0.6.2 version couldn't be properly installed

0.6.2
=====

* init\_db command is idempotent (can be called multiple times without errors)
* Internal refactoring

0.6.1
=====

* Fixed ordering migrations of mixed types (sql+py or cql+py).

0.6
===

* Apache Cassandra 2.x support
* Database specific packages (`psycopg2`, `cassandra-driver`) are not specified as dependencies. Required packages must be installed explicitly by a user. 

0.5
===
Initial release with PostgreSQL support.
