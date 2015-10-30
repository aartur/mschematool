def migrate(connection):
    cur = connection.cursor()
    cur.execute("""CREATE TABLE article (id int, body text)""")
