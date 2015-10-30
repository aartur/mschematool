def migrate(connection, db_config):
    if db_config['engine'] == 'postgres':
        cur = connection.cursor()
        cur.execute("""INSERT INTO article (id, body) VALUES (3, 'xxx')""")
