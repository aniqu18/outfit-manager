import sqlite3
from datetime import datetime

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS borrowers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS outfits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    description TEXT,
    size TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rentals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    borrower_id INTEGER NOT NULL,
    outfit_id INTEGER NOT NULL,
    borrowed_at TEXT NOT NULL,
    due_at TEXT NOT NULL,
    returned_at TEXT,
    notes TEXT,
    FOREIGN KEY(borrower_id) REFERENCES borrowers(id),
    FOREIGN KEY(outfit_id) REFERENCES outfits(id)
);
"""


def get_connection(path: str):
    conn = sqlite3.connect(path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(path: str):
    new_db = not os.path.exists(path)
    conn = get_connection(path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


# Simple helpers
import os

def add_borrower(path: str, name: str, phone: str = None, email: str = None):
    conn = get_connection(path)
    cur = conn.cursor()
    cur.execute("INSERT INTO borrowers (name, phone, email, created_at) VALUES (?, ?, ?, ?)",
                (name, phone, email, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def add_outfit(path: str, code: str, description: str = None, size: str = None):
    conn = get_connection(path)
    cur = conn.cursor()
    cur.execute("INSERT INTO outfits (code, description, size, created_at) VALUES (?, ?, ?, ?)",
                (code, description, size, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def checkout(path: str, borrower_id: int, outfit_id: int, due_at_iso: str, notes: str = None):
    conn = get_connection(path)
    cur = conn.cursor()
    cur.execute("INSERT INTO rentals (borrower_id, outfit_id, borrowed_at, due_at, notes) VALUES (?, ?, ?, ?, ?)",
                (borrower_id, outfit_id, datetime.utcnow().isoformat(), due_at_iso, notes))
    conn.commit()
    conn.close()


def return_rental(path: str, rental_id: int):
    conn = get_connection(path)
    cur = conn.cursor()
    cur.execute("UPDATE rentals SET returned_at = ? WHERE id = ?", (datetime.utcnow().isoformat(), rental_id))
    conn.commit()
    conn.close()


def list_borrowers(path: str):
    conn = get_connection(path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM borrowers ORDER BY name")
    rows = cur.fetchall()
    conn.close()
    return rows


def list_outfits(path: str):
    conn = get_connection(path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM outfits ORDER BY code")
    rows = cur.fetchall()
    conn.close()
    return rows


def list_active_rentals(path: str):
    conn = get_connection(path)
    cur = conn.cursor()
    cur.execute("""
    SELECT r.id, b.name as borrower, o.code as outfit_code, o.description, r.borrowed_at, r.due_at, r.returned_at
    FROM rentals r
    JOIN borrowers b ON r.borrower_id = b.id
    JOIN outfits o ON r.outfit_id = o.id
    WHERE r.returned_at IS NULL
    ORDER BY r.due_at ASC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def list_overdue(path: str):
    conn = get_connection(path)
    cur = conn.cursor()
    cur.execute("""
    SELECT r.id, b.name as borrower, o.code as outfit_code, o.description, r.borrowed_at, r.due_at
    FROM rentals r
    JOIN borrowers b ON r.borrower_id = b.id
    JOIN outfits o ON r.outfit_id = o.id
    WHERE r.returned_at IS NULL AND datetime(r.due_at) < datetime(?)
    ORDER BY r.due_at ASC
    """, (datetime.utcnow().isoformat(),))
    rows = cur.fetchall()
    conn.close()
    return rows


def get_borrower_by_name(path: str, name: str):
    conn = get_connection(path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM borrowers WHERE name = ?", (name,))
    row = cur.fetchone()
    conn.close()
    return row


def get_outfit_by_code(path: str, code: str):
    conn = get_connection(path)
    cur = conn.cursor()
    cur.execute("SELECT * FROM outfits WHERE code = ?", (code,))
    row = cur.fetchone()
    conn.close()
    return row
