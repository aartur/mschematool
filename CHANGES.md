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
