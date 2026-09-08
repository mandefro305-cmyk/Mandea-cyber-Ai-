import sqlite3
import hashlib
import time

DB_PATH = "assistant_data.db"

def init_auth_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def register_user(username: str, password: str, role: str = "user") -> tuple[bool, str]:
    init_auth_db()
    if not username.strip() or not password.strip():
        return False, "Username and password cannot be empty."

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE username = ?", (username.strip(),))
    if cursor.fetchone():
        conn.close()
        return False, "Username already exists."

    pwd_hash = _hash_password(password)
    cursor.execute("INSERT INTO users (username, password_hash, role, created_at) VALUES (?, ?, ?, ?)",
                   (username.strip(), pwd_hash, role, time.time()))
    conn.commit()
    conn.close()
    return True, "User registered successfully."

def authenticate_user(username: str, password: str) -> tuple[bool, str, str]:
    """Returns (success, message, role)"""
    init_auth_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT password_hash, role FROM users WHERE username = ?", (username.strip(),))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return False, "Invalid username or password.", ""

    pwd_hash = _hash_password(password)
    if row[0] == pwd_hash:
        return True, "Authentication successful.", row[1]
    return False, "Invalid username or password.", ""
