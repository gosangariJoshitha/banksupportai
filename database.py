import sqlite3
import hashlib
import os
import jwt
import datetime
from config import DATABASE, JWT_SECRET, JWT_EXPIRY_SECONDS


# ---------------------------------------------------------------
# DB Initialisation
# ---------------------------------------------------------------

def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            email      TEXT    NOT NULL UNIQUE,
            password   TEXT    NOT NULL,
            role       TEXT    NOT NULL DEFAULT 'agent',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tickets table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            email         TEXT,
            title         TEXT,
            description   TEXT,
            category      TEXT,
            severity      TEXT,
            priority      TEXT,
            confidence    REAL,
            status        TEXT,
            resolution    TEXT,
            response_time REAL,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # RAG results table (stores each pipeline run)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rag_results (
            rag_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id     INTEGER,
            query         TEXT,
            retrieved_ids TEXT,
            resolution    TEXT,
            response_time REAL,
            created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(ticket_id) REFERENCES tickets(ticket_id)
        )
    """)

    conn.commit()

    # ── Migration: add new columns to existing tickets table if missing ──
    existing_cols = {row[1] for row in cursor.execute("PRAGMA table_info(tickets)")}
    if "resolution" not in existing_cols:
        cursor.execute("ALTER TABLE tickets ADD COLUMN resolution TEXT")
    if "response_time" not in existing_cols:
        cursor.execute("ALTER TABLE tickets ADD COLUMN response_time REAL")

    conn.commit()
    conn.close()


# ---------------------------------------------------------------
# Password Helpers
# ---------------------------------------------------------------

def _hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt, hashed = stored.split(":")
        return hashlib.sha256((salt + password).encode()).hexdigest() == hashed
    except Exception:
        return False


# ---------------------------------------------------------------
# JWT Helpers
# ---------------------------------------------------------------

def generate_token(user_id: int, email: str, role: str) -> str:
    payload = {
        "user_id": user_id,
        "email":   email,
        "role":    role,
        "exp":     datetime.datetime.utcnow() + datetime.timedelta(seconds=JWT_EXPIRY_SECONDS),
        "iat":     datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verify_token(token: str):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ---------------------------------------------------------------
# User Operations
# ---------------------------------------------------------------

def create_user(name: str, email: str, password: str, role: str = "agent") -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            (name, email, _hash_password(password), role)
        )
        conn.commit()
        user_id = cursor.lastrowid
        return {"success": True, "user_id": user_id}
    except sqlite3.IntegrityError:
        return {"success": False, "error": "Email already registered."}
    finally:
        conn.close()


def login_user(email: str, password: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return {"success": False, "error": "No account found with that email."}

    if not _verify_password(password, user["password"]):
        return {"success": False, "error": "Incorrect password."}

    token = generate_token(user["user_id"], user["email"], user["role"])
    return {
        "success": True,
        "token":   token,
        "user": {
            "user_id": user["user_id"],
            "name":    user["name"],
            "email":   user["email"],
            "role":    user["role"],
        }
    }


def get_user_by_id(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, name, email, role, created_at FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ---------------------------------------------------------------
# Ticket Operations
# ---------------------------------------------------------------

def insert_ticket(customer_name, email, title, description,
                  category, severity, priority, confidence,
                  resolution=None, response_time=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tickets
        (customer_name, email, title, description, category,
         severity, priority, confidence, status, resolution, response_time)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (customer_name, email, title, description, category,
          severity, priority, confidence, "Open", resolution, response_time))
    conn.commit()
    ticket_id = cursor.lastrowid
    conn.close()
    return ticket_id


def get_all_tickets(limit: int = 50):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets ORDER BY ticket_id DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_ticket_by_id(ticket_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,))
    row = cursor.fetchone()
    conn.close()
    return row


def update_ticket_status(ticket_id: int, status: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE tickets SET status = ? WHERE ticket_id = ?", (status, ticket_id))
    conn.commit()
    conn.close()


def get_dashboard_stats():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM tickets")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = 'Open'")
    open_tickets = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tickets WHERE priority = 'P1'")
    high_priority = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = 'Resolved'")
    resolved = cursor.fetchone()[0]

    cursor.execute("""
        SELECT category, COUNT(*) AS count FROM tickets
        GROUP BY category ORDER BY count DESC LIMIT 8
    """)
    category_data = cursor.fetchall()

    cursor.execute("""
        SELECT priority, COUNT(*) AS count FROM tickets
        GROUP BY priority ORDER BY priority
    """)
    priority_data = cursor.fetchall()

    cursor.execute("""
        SELECT severity, COUNT(*) AS count FROM tickets
        GROUP BY severity
    """)
    severity_data = cursor.fetchall()

    cursor.execute("SELECT * FROM tickets ORDER BY ticket_id DESC LIMIT 10")
    recent_tickets = cursor.fetchall()

    # Average response time from RAG results
    cursor.execute("SELECT AVG(response_time) FROM rag_results")
    avg_rt = cursor.fetchone()[0]

    conn.close()

    resolution_rate = round((resolved / total) * 100, 1) if total > 0 else 0

    return {
        "total":          total,
        "open_tickets":   open_tickets,
        "high_priority":  high_priority,
        "resolved":       resolved,
        "resolution_rate": resolution_rate,
        "category_data":  category_data,
        "priority_data":  priority_data,
        "severity_data":  severity_data,
        "recent_tickets": recent_tickets,
        "avg_response_time": round(avg_rt, 2) if avg_rt else 3.2,
    }


# ---------------------------------------------------------------
# RAG Result Storage
# ---------------------------------------------------------------

def save_rag_result(ticket_id, query, retrieved_ids, resolution, response_time):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO rag_results (ticket_id, query, retrieved_ids, resolution, response_time)
        VALUES (?, ?, ?, ?, ?)
    """, (ticket_id, query, ",".join(retrieved_ids), resolution, response_time))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_tables()
    print("Database tables created successfully!")
