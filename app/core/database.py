import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        self.host = os.getenv("DB_HOST", "").strip()
        self.database = os.getenv("DB_NAME", "").strip()
        self.user = os.getenv("DB_USER", "").strip()
        self.password = os.getenv("DB_PASSWORD", "")
        self.port = os.getenv("DB_PORT", "5432").strip()

    def get_connection(self):
        faltantes = [
            nombre for nombre, valor in (
                ("DB_HOST", self.host),
                ("DB_NAME", self.database),
                ("DB_USER", self.user),
                ("DB_PASSWORD", self.password),
            )
            if not valor
        ]
        if faltantes:
            raise RuntimeError(
                "Faltan variables de conexión a PostgreSQL: " + ", ".join(faltantes)
            )

        try:
            return psycopg2.connect(
                host=self.host,
                dbname=self.database,
                user=self.user,
                password=self.password,
                port=int(self.port or "5432"),
                sslmode="require",
                channel_binding="require",
                connect_timeout=10,
                cursor_factory=RealDictCursor
            )
        except (ValueError, psycopg2.Error) as error:
            raise RuntimeError(
                "No se pudo conectar a PostgreSQL. Verifica DB_HOST, DB_NAME, "
                "DB_USER, DB_PASSWORD y DB_PORT en el .env de la API."
            ) from error
