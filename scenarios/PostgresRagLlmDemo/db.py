import os

from psycopg2 import connect


class VectorDatabase:
    def __init__(self, pguser, pghost, pgpassword, pgdatabase):
        self.conn = connect(user=pguser, password=pgpassword, host=pghost, port=5432, dbname=pgdatabase)

    def __exit__(self, exc_type, exc_value, traceback):
        self.conn.close()

    def save_embedding(self, _id: int, data: str, embedding: list[float]):
        with self.conn.cursor() as cursor:
            cursor.execute("INSERT INTO embeddings (id, data, embedding) VALUES (%s, %s, %s)", (_id, data, embedding))
            self.conn.commit()

    def search_documents(self, question_embedding):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT data FROM embeddings v ORDER BY v.embedding <#> (%s)::vector LIMIT 1",
            (question_embedding,),
        )
        results = cursor.fetchall()
        return list(map(lambda x: x[0], results))
