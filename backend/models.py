"""
models.py — PostgreSQL (Supabase) version.

Provides a DictCursor-based connection so existing route code that does
row['column_name'] and dict(row) keeps working unchanged.
"""

import psycopg2
import psycopg2.extras
from config import Config


def get_db():
    """
    Returns a psycopg2 connection configured with DictCursor as the
    default cursor factory, so conn.execute(...)-style calls in routes
    (which actually call cursor methods via a thin wrapper below) behave
    like the old sqlite3.Row-based code.
    """
    conn = psycopg2.connect(Config.DATABASE_URL, cursor_factory=psycopg2.extras.DictCursor)
    return _ConnWrapper(conn)


class _ConnWrapper:
    """
    Thin wrapper so existing code that calls conn.execute(...).fetchone()/
    fetchall() keeps working without rewriting every route file.
    Translates '?' placeholders to '%s' automatically.
    """
    def __init__(self, conn):
        self._conn = conn
        self._cursor = conn.cursor()

    def execute(self, query, params=None):
        # Translate SQLite '?' placeholders to psycopg2 '%s'
        pg_query = query.replace('?', '%s')
        self._cursor.execute(pg_query, params or [])
        return self._cursor

    def commit(self):
        self._conn.commit()

    def close(self):
        self._cursor.close()
        self._conn.close()


def init_db():
    conn = psycopg2.connect(Config.DATABASE_URL)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            SERIAL PRIMARY KEY,
            email         TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at    TIMESTAMP DEFAULT NOW()
        );
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id          SERIAL PRIMARY KEY,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            amount      DOUBLE PRECISION NOT NULL,
            category    TEXT NOT NULL DEFAULT 'Other',
            description TEXT NOT NULL,
            date        TEXT NOT NULL,
            source      TEXT NOT NULL DEFAULT 'manual',
            created_at  TIMESTAMP DEFAULT NOW()
        );
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id         SERIAL PRIMARY KEY,
            user_id    INTEGER NOT NULL REFERENCES users(id),
            month      INTEGER NOT NULL,
            year       INTEGER NOT NULL,
            amount     DOUBLE PRECISION NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(user_id, month, year)
        );
    """)

    conn.commit()
    c.close()
    conn.close()
