def migrate(connection):
    cur = connection.cursor()
    for i in range(10):
        cur.execute("""INSERT INTO article (id, body) VALUES (%s, %s)""", [i, str(i)])
