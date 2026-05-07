import sqlite3, uuid
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent / "spozywka.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id          TEXT PRIMARY KEY,
            created_at  TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'new',
            meta        TEXT
        );
        CREATE TABLE IF NOT EXISTS photos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT NOT NULL REFERENCES sessions(id),
            url         TEXT NOT NULL,
            filename    TEXT NOT NULL,
            uploaded_at TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()


def new_session() -> dict:
    sid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    conn = get_db()
    conn.execute("INSERT INTO sessions (id, created_at) VALUES (?, ?)", (sid, now))
    conn.commit()
    conn.close()
    return {"id": sid, "created_at": now, "status": "new"}


def get_sessions() -> list:
    conn = get_db()
    rows = conn.execute("""
        SELECT s.id, s.created_at, s.status, s.meta,
               COUNT(p.id) as photo_count
        FROM sessions s
        LEFT JOIN photos p ON p.session_id = s.id
        GROUP BY s.id
        ORDER BY s.created_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_session(sid: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (sid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_photo(session_id: str, url: str, filename: str):
    now = datetime.utcnow().isoformat()
    conn = get_db()
    conn.execute(
        "INSERT INTO photos (session_id, url, filename, uploaded_at) VALUES (?, ?, ?, ?)",
        (session_id, url, filename, now)
    )
    conn.commit()
    conn.close()


def get_photos(session_id: str) -> list:
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM photos WHERE session_id = ? ORDER BY uploaded_at",
        (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_meta(session_id: str, meta: dict):
    import json
    conn = get_db()
    conn.execute(
        "UPDATE sessions SET meta = ?, status = 'analyzed' WHERE id = ?",
        (json.dumps(meta, ensure_ascii=False), session_id)
    )
    conn.commit()
    conn.close()


def delete_session(sid: str):
    conn = get_db()
    conn.execute("DELETE FROM photos WHERE session_id = ?", (sid,))
    conn.execute("DELETE FROM sessions WHERE id = ?", (sid,))
    conn.commit()
    conn.close()
