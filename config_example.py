"""
Настройки подключения к PostgreSQL.

DSN собирается из переменных окружения (если заданы) или из значений
по умолчанию. Значения по умолчанию соответствуют локальной разработке:

    host     = localhost
    port     = 5432
    database = english_card
    user     = postgres
    password = postgres

Чтобы переопределить — задайте переменные окружения
PGHOST / PGPORT / PGDATABASE / PGUSER / PGPASSWORD
или скопируйте .env.example в .env и заполните своими значениями.

Формат DSN — URL для SQLAlchemy:
    postgresql+psycopg2://USER:PASSWORD@HOST:PORT/DATABASE
"""
import os

PG_HOST = os.getenv("PGHOST", "localhost")
PG_PORT = os.getenv("PGPORT", "5432")
PG_DATABASE = os.getenv("PGDATABASE", "english_card")
PG_USER = os.getenv("PGUSER", "postgres")
PG_PASSWORD = os.getenv("PGPASSWORD", "postgres")

DSN = (
    f"postgresql+psycopg2://{PG_USER}:{PG_PASSWORD}"
    f"@{PG_HOST}:{PG_PORT}/{PG_DATABASE}"
)