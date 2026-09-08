import sqlite3
import os
import json
import time

def get_db_path() -> str:
    """
    Returns the SQLite database path.
    Checks for DATA_DIR environment variable (useful for Railway Persistent Volumes).
    Defaults to './assistant_data.db'.
    """
    data_dir = os.getenv("DATA_DIR", ".").strip()
    if data_dir and data_dir != ".":
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "assistant_data.db")
    return "assistant_data.db"

def init_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Enable WAL mode for better concurrency and performance
    try:
        cursor.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass

    # Sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            created_at REAL NOT NULL
        )
    """)

    # Messages table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp REAL NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
        )
    """)

    # Indexes for fast querying
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at DESC);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id ASC);")

    conn.commit()
    conn.close()

def create_session(session_id: str, title: str = "New Session"):
    init_db()
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO sessions (id, title, created_at) VALUES (?, ?, ?)",
                   (session_id, title, time.time()))
    conn.commit()
    conn.close()

def get_all_sessions() -> list[dict]:
    init_db()
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, created_at FROM sessions ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "title": r[1], "created_at": r[2]} for r in rows]

def save_message(session_id: str, role: str, content: str):
    init_db()
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                   (session_id, role, content, time.time()))
    conn.commit()
    conn.close()

def get_session_messages(session_id: str) -> list[dict]:
    init_db()
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in rows]

def delete_session(session_id: str):
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()
