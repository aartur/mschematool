CREATE KEYSPACE IF NOT EXISTS mtest WITH REPLICATION = { 'class' : 'SimpleStrategy', 'replication_factor' : 3 };
USE mtest;
CREATE TABLE article (id int, body text, PRIMARY KEY(id));
