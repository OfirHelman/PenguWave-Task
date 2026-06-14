"""SQLite database setup for PenguWave events."""
import os
import sqlite3

# Database file lives alongside this module: backend/penguwave.db
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "penguwave.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id            TEXT PRIMARY KEY,
    timestamp     TEXT NOT NULL,
    severity      TEXT NOT NULL CHECK (severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
    title         TEXT NOT NULL,
    description   TEXT NOT NULL DEFAULT '',
    assetHostname TEXT NOT NULL,
    assetIp       TEXT NOT NULL,
    sourceIp      TEXT,          -- nullable
    tags          TEXT NOT NULL DEFAULT '[]',  -- JSON-encoded list
    userId        TEXT           -- nullable
);

CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,  -- bcrypt hash; never store plaintext
    role          TEXT NOT NULL CHECK (role IN ('admin', 'analyst', 'viewer')),
    status        TEXT NOT NULL DEFAULT 'active'
);
"""


def get_connection():
    """Return a SQLite connection with row access by column name."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(conn=None):
    """Create the events table if it does not exist."""
    own = conn is None
    if own:
        conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        if own:
            conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Initialized database at {DB_PATH}")
