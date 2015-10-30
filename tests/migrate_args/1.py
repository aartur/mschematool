def migrate(connection):
    cur = connection.cursor()
    cur.execute("""INSERT INTO article (id, body) VALUES (1, 'xxx')""")
