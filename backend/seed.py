"""Load events from data/mock_events.json into the SQLite database.

Handles messy records:
  - Inserts every event, including content duplicates that have distinct ids
    (e.g. evt-002 and evt-056 are kept as separate rows).
  - Allows null sourceIp and null userId.
  - Allows empty description.
  - Stores future-dated timestamps (e.g. evt-057) as-is.
  - Uses INSERT OR IGNORE on id, so re-running won't double-insert.

Run with:  python seed.py
"""
import json
import os

from passlib.context import CryptContext

from database import get_connection, init_db

DATA_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data", "mock_events.json"
)

# bcrypt password hasher (shared scheme name with main.py's verifier)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Demo users to seed. Passwords are plaintext here only so we can hash them;
# the database only ever stores the bcrypt hash.
SEED_USERS = [
    {"id": "usr-admin", "email": "admin@penguwave.io", "password": "admin123", "role": "admin", "status": "active"},
    {"id": "usr-analyst", "email": "analyst@penguwave.io", "password": "analyst123", "role": "analyst", "status": "active"},
    {"id": "usr-viewer", "email": "viewer@penguwave.io", "password": "viewer123", "role": "viewer", "status": "active"},
]


def load_events(path=DATA_PATH):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def seed_users(conn):
    """Insert demo users with bcrypt-hashed passwords. Idempotent via id."""
    inserted = 0
    for u in SEED_USERS:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO users (id, email, password_hash, role, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                u["id"],
                u["email"],
                pwd_context.hash(u["password"]),  # store only the hash
                u["role"],
                u["status"],
            ),
        )
        if cur.rowcount:
            inserted += 1
    return inserted


def seed():
    init_db()
    events = load_events()

    inserted = 0
    skipped = 0

    conn = get_connection()
    try:
        for ev in events:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO events
                    (id, timestamp, severity, title, description,
                     assetHostname, assetIp, sourceIp, tags, userId)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ev["id"],
                    ev["timestamp"],
                    ev["severity"],
                    ev["title"],
                    ev.get("description") or "",
                    ev["assetHostname"],
                    ev["assetIp"],
                    ev.get("sourceIp"),  # may be None
                    json.dumps(ev.get("tags") or []),
                    ev.get("userId"),  # may be None
                ),
            )
            # rowcount is 0 when INSERT OR IGNORE skipped an existing id
            if cur.rowcount:
                inserted += 1
            else:
                skipped += 1
        users_inserted = seed_users(conn)
        conn.commit()
    finally:
        conn.close()

    print(f"Inserted {inserted} events, skipped {skipped}.")
    print(f"Inserted {users_inserted} users.")
    return inserted, skipped


if __name__ == "__main__":
    seed()
