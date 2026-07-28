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


def return_rental(path: str, rental_id: int, returned_at_iso: str = None):
    conn = get_connection(path)
    cur = conn.cursor()
    if returned_at_iso is None:
        returned_at_iso = datetime.utcnow().isoformat()
    cur.execute("UPDATE rentals SET returned_at = ? WHERE id = ?", (returned_at_iso, rental_id))
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


def update_borrower(path: str, borrower_id: int, name: str, phone: str = None, email: str = None):
    conn = get_connection(path)
    cur = conn.cursor()
    cur.execute("UPDATE borrowers SET name = ?, phone = ?, email = ? WHERE id = ?", (name, phone, email, borrower_id))
    conn.commit()
    conn.close()


def get_or_create_placeholder_borrower(path: str):
    """Return id of a placeholder borrower used when deleting a borrower with history."""
    conn = get_connection(path)
    cur = conn.cursor()
    cur.execute("SELECT id FROM borrowers WHERE name = ?", ("<deleted borrower>",))
    row = cur.fetchone()
    if row:
        pid = row['id']
    else:
        cur.execute("INSERT INTO borrowers (name, phone, email, created_at) VALUES (?, ?, ?, ?)",
                    ("<deleted borrower>", None, None, datetime.utcnow().isoformat()))
        pid = cur.lastrowid
        conn.commit()
    conn.close()
    return pid


def delete_borrower(path: str, borrower_id: int):
    conn = get_connection(path)
    cur = conn.cursor()
    # only count active (not returned) rentals
    cur.execute("SELECT COUNT(*) as c FROM rentals WHERE borrower_id = ? AND returned_at IS NULL", (borrower_id,))
    row = cur.fetchone()
    if row and row['c'] > 0:
        conn.close()
        raise Exception('Cannot delete borrower: borrower has active (not returned) rentals')
    # if borrower has historical rentals, reassign them to a placeholder borrower so FK stays valid
    cur.execute("SELECT COUNT(*) as c FROM rentals WHERE borrower_id = ?", (borrower_id,))
    row2 = cur.fetchone()
    if row2 and row2['c'] > 0:
        pid = get_or_create_placeholder_borrower(path)
        cur.execute("UPDATE rentals SET borrower_id = ? WHERE borrower_id = ?", (pid, borrower_id))
    cur.execute("DELETE FROM borrowers WHERE id = ?", (borrower_id,))
    conn.commit()
    conn.close()


def update_outfit(path: str, outfit_id: int, code: str, description: str = None, size: str = None):
    conn = get_connection(path)
    cur = conn.cursor()
    cur.execute("UPDATE outfits SET code = ?, description = ?, size = ? WHERE id = ?", (code, description, size, outfit_id))
    conn.commit()
    conn.close()


def get_or_create_placeholder_outfit(path: str):
    conn = get_connection(path)
    cur = conn.cursor()
    cur.execute("SELECT id FROM outfits WHERE code = ?", ("<deleted-outfit>",))
    row = cur.fetchone()
    if row:
        pid = row['id']
    else:
        cur.execute("INSERT INTO outfits (code, description, size, created_at) VALUES (?, ?, ?, ?)",
                    ("<deleted-outfit>", "Deleted outfit placeholder", None, datetime.utcnow().isoformat()))
        pid = cur.lastrowid
        conn.commit()
    conn.close()
    return pid


def delete_outfit(path: str, outfit_id: int):
    conn = get_connection(path)
    cur = conn.cursor()
    # only count active (not returned) rentals
    cur.execute("SELECT COUNT(*) as c FROM rentals WHERE outfit_id = ? AND returned_at IS NULL", (outfit_id,))
    row = cur.fetchone()
    if row and row['c'] > 0:
        conn.close()
        raise Exception('Cannot delete outfit: outfit has active (not returned) rentals')
    # if outfit has historical rentals, reassign them to a placeholder outfit so FK stays valid
    cur.execute("SELECT COUNT(*) as c FROM rentals WHERE outfit_id = ?", (outfit_id,))
    row2 = cur.fetchone()
    if row2 and row2['c'] > 0:
        pid = get_or_create_placeholder_outfit(path)
        cur.execute("UPDATE rentals SET outfit_id = ? WHERE outfit_id = ?", (pid, outfit_id))
    cur.execute("DELETE FROM outfits WHERE id = ?", (outfit_id,))
    conn.commit()
    conn.close()
