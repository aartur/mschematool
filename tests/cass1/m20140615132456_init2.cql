CREATE KEYSPACE IF NOT EXISTS mtest WITH REPLICATION = { 'class' : 'SimpleStrategy', 'replication_factor' : 1 };
CREATE TABLE mtest.author (name text, PRIMARY KEY(name));
