def migrate(connection, db_config):
    cur = connection.cursor()
    cur.execute("""INSERT INTO article (id, body) VALUES (2, 'xxx')""")
