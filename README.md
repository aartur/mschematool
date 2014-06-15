mschematool
===========

mschematool is a simple tool for managing database migrations. Migrations are either SQL files or Python modules. They are ordered linearly using just lexicographical ordering of file names (with timestamp being a leading component). Information about executed migrations is stored inside a database for which migrations were executed using a simple table with file names only. The lightweight design enables changing the table contents manually, if necessery, and generally the tool tries to not enforce any hard rules.

Currently only PostgreSQL is supported.
