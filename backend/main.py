"""PenguWave API — application entrypoint, auth, and events endpoints."""
import json
import os
import uuid
from datetime import datetime, timedelta, timezone

import jwt  # PyJWT
from fastapi import Body, FastAPI, Header
from fastapi.responses import JSONResponse
from passlib.context import CryptContext
from pydantic import BaseModel

from database import get_connection

app = FastAPI(title="PenguWave API")

# --- Auth configuration -----------------------------------------------------
# The signing secret is read from the environment so it never lives in code.
# The fallback is for local dev only; set PENGUWAVE_JWT_SECRET in real use.
JWT_SECRET = os.environ.get(
    "PENGUWAVE_JWT_SECRET", "dev-insecure-secret-change-me-in-production-please"
)
JWT_ALGORITHM = "HS256"
JWT_TTL_HOURS = 8  # how long an issued token stays valid

# bcrypt verifier — must use the same scheme seed.py hashed with.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# --- Request/response models ------------------------------------------------
class LoginRequest(BaseModel):
    email: str
    password: str


# --- Helpers ----------------------------------------------------------------
def create_token(user) -> str:
    """Build a signed JWT carrying the user's id, email, and role."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user["id"],          # subject = user id
        "email": user["email"],
        "role": user["role"],
        "iat": now,                 # issued-at
        "exp": now + timedelta(hours=JWT_TTL_HOURS),  # expiry
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_user_by_email(email: str):
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
    finally:
        conn.close()


def get_user_by_id(user_id: str):
    conn = get_connection()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()


# Roles allowed in the system (also enforced by the DB CHECK constraint).
VALID_ROLES = ("admin", "analyst", "viewer")

# 401 body shared by every endpoint that needs a valid token.
UNAUTHORIZED = JSONResponse(
    status_code=401, content={"error": "Authentication required"}
)

# 403 body shared by admin-only endpoints.
FORBIDDEN = JSONResponse(status_code=403, content={"error": "Forbidden"})


def get_authenticated_user(authorization):
    """Resolve a Bearer token to its user row, or None if auth fails.

    Returns None for a missing/malformed header, an invalid/expired token,
    or a token whose user no longer exists. Callers map None -> 401.
    """
    # Expect an "Authorization: Bearer <token>" header.
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ", 1)[1]

    # Verify signature + expiry. Any failure -> not authenticated.
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None

    # Re-read from the DB so role/status reflect current state, not the token.
    return get_user_by_id(payload.get("sub"))


def require_admin(authorization):
    """Authenticate and require the admin role.

    Returns (user, None) on success, or (None, error_response) where the
    error is 401 for missing/invalid tokens and 403 for non-admin users.
    """
    user = get_authenticated_user(authorization)
    if user is None:
        return None, UNAUTHORIZED
    if user["role"] != "admin":
        return None, FORBIDDEN
    return user, None


# --- Endpoints --------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/auth/login")
def login(body: LoginRequest):
    """Validate email + password and return a JWT plus basic user info."""
    user = get_user_by_email(body.email)

    # Same generic 401 whether the email is unknown or the password is wrong,
    # so we don't leak which emails exist.
    if user is None or not pwd_context.verify(body.password, user["password_hash"]):
        return JSONResponse(
            status_code=401, content={"error": "Invalid email or password"}
        )

    token = create_token(user)
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "email": user["email"],
            "role": user["role"],
        },
    }


@app.get("/api/auth/me")
def me(authorization: str = Header(default=None)):
    """Return the current user, identified by a valid Bearer token."""
    user = get_authenticated_user(authorization)
    if user is None:
        return UNAUTHORIZED

    return {
        "id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "status": user["status"],
    }


# --- Events -----------------------------------------------------------------
def serialize_event(row):
    """Convert an events row to a JSON-friendly dict (tags back into a list)."""
    event = dict(row)
    event["tags"] = json.loads(event["tags"])  # stored as a JSON string
    return event


@app.get("/api/events")
def list_events(authorization: str = Header(default=None)):
    """Return all events. Requires a valid Bearer token (any role)."""
    if get_authenticated_user(authorization) is None:
        return UNAUTHORIZED

    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM events").fetchall()
    finally:
        conn.close()

    return [serialize_event(row) for row in rows]


@app.get("/api/events/{event_id}")
def get_event(event_id: str, authorization: str = Header(default=None)):
    """Return one event by id. Requires a valid Bearer token (any role)."""
    if get_authenticated_user(authorization) is None:
        return UNAUTHORIZED

    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM events WHERE id = ?", (event_id,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return JSONResponse(status_code=404, content={"error": "Event not found"})

    return serialize_event(row)


# --- User management (admin only) -------------------------------------------
def serialize_user(row):
    """Public view of a user — never includes the password hash."""
    return {
        "id": row["id"],
        "email": row["email"],
        "role": row["role"],
        "status": row["status"],
    }


@app.get("/api/users")
def list_users(authorization: str = Header(default=None)):
    """List all users (admin only). Passwords are never returned."""
    _, error = require_admin(authorization)
    if error:
        return error

    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM users").fetchall()
    finally:
        conn.close()

    return [serialize_user(row) for row in rows]


@app.post("/api/users")
def create_user(
    authorization: str = Header(default=None), payload: dict = Body(default={})
):
    """Create a user (admin only). Hashes the password before storing."""
    _, error = require_admin(authorization)
    if error:
        return error

    email = (payload.get("email") or "").strip()
    password = payload.get("password") or ""
    role = payload.get("role")

    # Validate required fields and role before touching the DB.
    if not email or not password or not role:
        return JSONResponse(
            status_code=400,
            content={"error": "email, password, and role are required"},
        )
    if role not in VALID_ROLES:
        return JSONResponse(
            status_code=400,
            content={"error": f"role must be one of {', '.join(VALID_ROLES)}"},
        )
    if get_user_by_email(email) is not None:
        return JSONResponse(
            status_code=400, content={"error": "A user with that email already exists"}
        )

    user_id = "usr-" + uuid.uuid4().hex[:8]
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO users (id, email, password_hash, role, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, email, pwd_context.hash(password), role, "active"),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()

    # 201 Created, password never included.
    return JSONResponse(status_code=201, content=serialize_user(row))


@app.patch("/api/users/{user_id}")
def update_user(
    user_id: str,
    authorization: str = Header(default=None),
    payload: dict = Body(default={}),
):
    """Update a user's role and/or status (admin only)."""
    _, error = require_admin(authorization)
    if error:
        return error

    existing = get_user_by_id(user_id)
    if existing is None:
        return JSONResponse(status_code=404, content={"error": "User not found"})

    # Build the set of fields to update from whatever was provided.
    updates = {}
    if "role" in payload:
        if payload["role"] not in VALID_ROLES:
            return JSONResponse(
                status_code=400,
                content={"error": f"role must be one of {', '.join(VALID_ROLES)}"},
            )
        updates["role"] = payload["role"]
    if "status" in payload:
        updates["status"] = payload["status"]

    if not updates:
        return JSONResponse(
            status_code=400, content={"error": "Provide role and/or status to update"}
        )

    conn = get_connection()
    try:
        assignments = ", ".join(f"{field} = ?" for field in updates)
        conn.execute(
            f"UPDATE users SET {assignments} WHERE id = ?",
            (*updates.values(), user_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()

    return serialize_user(row)


@app.delete("/api/users/{user_id}")
def delete_user(user_id: str, authorization: str = Header(default=None)):
    """Delete a user (admin only)."""
    _, error = require_admin(authorization)
    if error:
        return error

    conn = get_connection()
    try:
        cur = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        deleted = cur.rowcount
    finally:
        conn.close()

    if not deleted:
        return JSONResponse(status_code=404, content={"error": "User not found"})

    return {"message": "User deleted"}


# --- Entrypoint -------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    # Default to port 3001 to match the Base URL in docs/api_contract.md
    # (http://localhost:3001). Override with the PORT env var if needed.
    port = int(os.environ.get("PORT", "3001"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
