INSERT INTO article (id, body) VALUES (1, 'xxx');

-- this will fail and should cause no inserts from this file to execute
INSERT INTO artice (id) VALUES (2);

INSERT INTO article (id, body) VALUES (3, 'yyy');
