def migrate(cluster):
    session = cluster.connect('mtest')
    session.execute("""INSERT INTO article (id, body) VALUES (%s, %s)""", [10, 'xx'])
