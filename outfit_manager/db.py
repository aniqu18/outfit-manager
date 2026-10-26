"""SQLite storage for regions, costumes, borrowers and rentals.

All dates are stored as 'YYYY-MM-DD' text; timestamps as ISO text.
Functions return plain dicts so they can be passed straight to the web screens.
"""

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime

SCHEMA_VERSION = 2

SCHEMA = """
CREATE TABLE regions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE COLLATE NOCASE,
    created_at TEXT NOT NULL
);

CREATE TABLE borrowers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    created_at TEXT NOT NULL,
    deleted_at TEXT
);

CREATE TABLE costumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    region_id INTEGER REFERENCES regions(id),
    name TEXT NOT NULL,
    inventory_no TEXT COLLATE NOCASE,
    size TEXT,
    description TEXT,
    photo TEXT,
    created_at TEXT NOT NULL,
    deleted_at TEXT  -- deleted costumes are kept so rental history stays complete
);

CREATE TABLE rentals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    borrower_id INTEGER NOT NULL REFERENCES borrowers(id),
    costume_id INTEGER NOT NULL REFERENCES costumes(id),
    borrowed_on TEXT NOT NULL,
    due_on TEXT NOT NULL,
    returned_on TEXT,
    notes TEXT
);

-- Inventory numbers are unique among costumes that are not deleted
CREATE UNIQUE INDEX costumes_inventory_no ON costumes(inventory_no) WHERE deleted_at IS NULL;
"""

# A costume can only be rented out once at a time
ACTIVE_RENTAL_INDEX = """
CREATE UNIQUE INDEX one_active_rental_per_costume ON rentals(costume_id) WHERE returned_on IS NULL;
"""

NO_REGION = "No region"


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def today() -> str:
    return date.today().isoformat()


def _clean(text):
    """Trim text; empty becomes None."""
    text = (text or "").strip()
    return text or None


def _valid_date(text: str, label: str) -> str:
    try:
        return date.fromisoformat((text or "").strip()).isoformat()
    except ValueError:
        raise ValueError(f"{label} is not a valid date.") from None


class Database:
    def __init__(self, path):
        self.path = str(path)
        self._init_schema()

    @contextmanager
    def connect(self):
        """Open a connection, commit on success, roll back on error, always close."""
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # --- schema & migration ---

    def _init_schema(self):
        conn = sqlite3.connect(self.path)
        try:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            if version == SCHEMA_VERSION:
                return
            if version > SCHEMA_VERSION:
                raise RuntimeError("This database was made by a newer version of Outfit Manager.")
            has_old_tables = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'outfits'"
            ).fetchone()
            script = _MIGRATE_FROM_V1 if has_old_tables else SCHEMA + ACTIVE_RENTAL_INDEX
            conn.executescript(
                f"PRAGMA foreign_keys = OFF; BEGIN; {script} PRAGMA user_version = {SCHEMA_VERSION}; COMMIT;"
            )
        finally:
            conn.close()

    # --- regions ---

    def list_regions(self):
        """Regions with costume counts and a cover photo (the first costume photo)."""
        with self.connect() as conn:
            rows = conn.execute("""
                SELECT reg.id, reg.name,
                       COUNT(c.id) AS costume_count,
                       COUNT(c.id) - COUNT(r.id) AS available_count,
                       (SELECT photo FROM costumes
                        WHERE region_id = reg.id AND deleted_at IS NULL AND photo IS NOT NULL
                        ORDER BY id LIMIT 1) AS photo
                FROM regions reg
                LEFT JOIN costumes c ON c.region_id = reg.id AND c.deleted_at IS NULL
                LEFT JOIN rentals r ON r.costume_id = c.id AND r.returned_on IS NULL
                GROUP BY reg.id
                ORDER BY reg.name
            """).fetchall()
        return [dict(r) for r in rows]

    def add_region(self, name: str) -> int:
        name = _clean(name)
        if not name:
            raise ValueError("Region name is required.")
        with self.connect() as conn:
            if conn.execute("SELECT 1 FROM regions WHERE name = ?", (name,)).fetchone():
                raise ValueError(f"Region '{name}' already exists.")
            return conn.execute(
                "INSERT INTO regions (name, created_at) VALUES (?, ?)", (name, now_iso())
            ).lastrowid

    def rename_region(self, region_id: int, name: str):
        name = _clean(name)
        if not name:
            raise ValueError("Region name is required.")
        with self.connect() as conn:
            if conn.execute("SELECT 1 FROM regions WHERE name = ? AND id != ?", (name, region_id)).fetchone():
                raise ValueError(f"Region '{name}' already exists.")
            conn.execute("UPDATE regions SET name = ? WHERE id = ?", (name, region_id))

    def delete_region(self, region_id: int):
        with self.connect() as conn:
            if conn.execute(
                "SELECT 1 FROM costumes WHERE region_id = ? AND deleted_at IS NULL", (region_id,)
            ).fetchone():
                raise ValueError("Move or delete the costumes in this region first.")
            conn.execute("UPDATE costumes SET region_id = NULL WHERE region_id = ?", (region_id,))
            conn.execute("DELETE FROM regions WHERE id = ?", (region_id,))

    # --- costumes ---

    _COSTUME_SELECT = """
        SELECT c.id, c.region_id, reg.name AS region, c.name, c.inventory_no, c.size,
               c.description, c.photo,
               r.id AS rental_id, b.name AS borrower, r.borrowed_on, r.due_on, r.notes
        FROM costumes c
        LEFT JOIN regions reg ON reg.id = c.region_id
        LEFT JOIN rentals r ON r.costume_id = c.id AND r.returned_on IS NULL
        LEFT JOIN borrowers b ON b.id = r.borrower_id
        WHERE c.deleted_at IS NULL
    """

    @staticmethod
    def _costume(row) -> dict:
        c = dict(row)
        c["status"] = "rented" if c["rental_id"] else "available"
        c["overdue"] = bool(c["due_on"]) and c["due_on"] < today()
        return c

    def list_costumes(self, region_id: int = None):
        query, params = self._COSTUME_SELECT, ()
        if region_id is not None:
            query += " AND c.region_id = ?"
            params = (region_id,)
        with self.connect() as conn:
            rows = conn.execute(query + " ORDER BY c.name, c.inventory_no", params).fetchall()
        return [self._costume(r) for r in rows]

    def get_costume(self, costume_id: int):
        with self.connect() as conn:
            row = conn.execute(self._COSTUME_SELECT + " AND c.id = ?", (costume_id,)).fetchone()
        return self._costume(row) if row else None

    def _costume_fields(self, conn, costume_id, region_id, name, inventory_no, size, description):
        name, inventory_no = _clean(name), _clean(inventory_no)
        if not name:
            raise ValueError("Costume name is required.")
        if not conn.execute("SELECT 1 FROM regions WHERE id = ?", (region_id,)).fetchone():
            raise ValueError("Choose a region.")
        if inventory_no and conn.execute(
            "SELECT 1 FROM costumes WHERE inventory_no = ? AND deleted_at IS NULL AND id IS NOT ?",
            (inventory_no, costume_id),
        ).fetchone():
            raise ValueError(f"Inventory number '{inventory_no}' is already used.")
        return region_id, name, inventory_no, _clean(size), _clean(description)

    def add_costume(self, region_id, name, inventory_no=None, size=None, description=None, photo=None) -> int:
        with self.connect() as conn:
            fields = self._costume_fields(conn, None, region_id, name, inventory_no, size, description)
            return conn.execute(
                "INSERT INTO costumes (region_id, name, inventory_no, size, description, photo, created_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (*fields, photo, now_iso()),
            ).lastrowid

    def update_costume(self, costume_id, region_id, name, inventory_no=None, size=None, description=None):
        with self.connect() as conn:
            fields = self._costume_fields(conn, costume_id, region_id, name, inventory_no, size, description)
            conn.execute(
                "UPDATE costumes SET region_id = ?, name = ?, inventory_no = ?, size = ?, description = ?"
                " WHERE id = ?",
                (*fields, costume_id),
            )

    def set_costume_photo(self, costume_id: int, photo):
        """Store a new photo file name; returns the old one (so its files can be removed)."""
        with self.connect() as conn:
            row = conn.execute("SELECT photo FROM costumes WHERE id = ?", (costume_id,)).fetchone()
            conn.execute("UPDATE costumes SET photo = ? WHERE id = ?", (photo, costume_id))
        return row["photo"] if row else None

    def delete_costume(self, costume_id: int):
        with self.connect() as conn:
            if conn.execute(
                "SELECT 1 FROM rentals WHERE costume_id = ? AND returned_on IS NULL", (costume_id,)
            ).fetchone():
                raise ValueError("This costume is rented out. Take it back first.")
            conn.execute("UPDATE costumes SET deleted_at = ? WHERE id = ?", (now_iso(), costume_id))

    # --- borrowers ---

    def borrower_names(self):
        """Names for the borrow form's suggestions."""
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT name FROM borrowers WHERE deleted_at IS NULL ORDER BY name COLLATE NOCASE"
            ).fetchall()
        return [r["name"] for r in rows]

    @staticmethod
    def _borrower_id(conn, name: str) -> int:
        """Find a borrower by name (ignoring case and extra spaces) or create one."""
        name = " ".join(name.split())
        row = conn.execute(
            "SELECT id FROM borrowers WHERE name = ? COLLATE NOCASE AND deleted_at IS NULL ORDER BY id LIMIT 1",
            (name,),
        ).fetchone()
        if row:
            return row["id"]
        return conn.execute(
            "INSERT INTO borrowers (name, created_at) VALUES (?, ?)", (name, now_iso())
        ).lastrowid

    # --- rentals ---

    def rent(self, costume_id: int, borrower_name: str, borrowed_on: str, due_on: str, notes=None) -> int:
        borrower_name = _clean(borrower_name)
        if not borrower_name:
            raise ValueError("Enter the borrower's name.")
        borrowed_on = _valid_date(borrowed_on, "Borrow date")
        due_on = _valid_date(due_on, "Return-by date")
        if due_on < borrowed_on:
            raise ValueError("Return-by date can't be before the borrow date.")
        with self.connect() as conn:
            if not conn.execute(
                "SELECT 1 FROM costumes WHERE id = ? AND deleted_at IS NULL", (costume_id,)
            ).fetchone():
                raise ValueError("This costume no longer exists.")
            if conn.execute(
                "SELECT 1 FROM rentals WHERE costume_id = ? AND returned_on IS NULL", (costume_id,)
            ).fetchone():
                raise ValueError("This costume is already rented out.")
            borrower_id = self._borrower_id(conn, borrower_name)
            return conn.execute(
                "INSERT INTO rentals (borrower_id, costume_id, borrowed_on, due_on, notes) VALUES (?, ?, ?, ?, ?)",
                (borrower_id, costume_id, borrowed_on, due_on, _clean(notes)),
            ).lastrowid

    def return_rental(self, rental_id: int, returned_on: str = None):
        returned_on = _valid_date(returned_on or today(), "Return date")
        with self.connect() as conn:
            row = conn.execute(
                "SELECT borrowed_on, returned_on FROM rentals WHERE id = ?", (rental_id,)
            ).fetchone()
            if not row:
                raise ValueError("Rental not found.")
            if row["returned_on"]:
                raise ValueError("This costume was already returned.")
            if returned_on < row["borrowed_on"]:
                raise ValueError("Return date can't be before the borrow date.")
            conn.execute("UPDATE rentals SET returned_on = ? WHERE id = ?", (returned_on, rental_id))

    _RENTAL_SELECT = """
        SELECT r.id, r.costume_id, c.name AS costume, c.inventory_no, c.size, c.photo,
               reg.name AS region, b.name AS borrower,
               r.borrowed_on, r.due_on, r.returned_on, r.notes,
               c.deleted_at IS NOT NULL AS costume_deleted
        FROM rentals r
        JOIN costumes c ON c.id = r.costume_id
        JOIN borrowers b ON b.id = r.borrower_id
        LEFT JOIN regions reg ON reg.id = c.region_id
    """

    def list_active_rentals(self):
        """Costumes currently out, overdue first, then by return-by date."""
        with self.connect() as conn:
            rows = conn.execute(
                self._RENTAL_SELECT + " WHERE r.returned_on IS NULL ORDER BY r.due_on, c.name"
            ).fetchall()
        t = today()
        return [{**dict(r), "overdue": r["due_on"] < t} for r in rows]

    def list_history(self, search: str = "", costume_id: int = None):
        """Returned rentals, newest first. `search` matches borrower, costume name or inventory number."""
        query = self._RENTAL_SELECT + " WHERE r.returned_on IS NOT NULL"
        params = []
        if costume_id is not None:
            query += " AND r.costume_id = ?"
            params.append(costume_id)
        if search := (search or "").strip():
            query += " AND (b.name LIKE ? OR c.name LIKE ? OR c.inventory_no LIKE ?)"
            params += [f"%{search}%"] * 3
        with self.connect() as conn:
            rows = conn.execute(query + " ORDER BY r.returned_on DESC, r.id DESC", params).fetchall()
        return [{**dict(r), "late": r["returned_on"] > r["due_on"]} for r in rows]

    def overdue_count(self) -> int:
        with self.connect() as conn:
            return conn.execute(
                "SELECT COUNT(*) FROM rentals WHERE returned_on IS NULL AND due_on < ?", (today(),)
            ).fetchone()[0]


# Upgrade from the first version (tables borrowers/outfits/rentals, with
# '<deleted borrower>' / '<deleted-outfit>' placeholder rows).
_MIGRATE_FROM_V1 = f"""
ALTER TABLE borrowers RENAME TO old_borrowers;
ALTER TABLE rentals RENAME TO old_rentals;
{SCHEMA}

INSERT INTO regions (name, created_at)
SELECT '{NO_REGION}', datetime('now', 'localtime')
WHERE EXISTS (SELECT 1 FROM outfits WHERE code != '<deleted-outfit>');

INSERT INTO borrowers (id, name, phone, email, created_at, deleted_at)
SELECT id, name, phone, email, created_at,
       CASE WHEN name = '<deleted borrower>' THEN created_at END
FROM old_borrowers;

INSERT INTO costumes (id, region_id, name, inventory_no, size, description, created_at, deleted_at)
SELECT id,
       CASE WHEN code = '<deleted-outfit>' THEN NULL ELSE (SELECT id FROM regions WHERE name = '{NO_REGION}') END,
       CASE WHEN code = '<deleted-outfit>' THEN 'Deleted costume' ELSE code END,
       CASE WHEN code = '<deleted-outfit>' THEN NULL ELSE code END,
       size, description, created_at,
       CASE WHEN code = '<deleted-outfit>' THEN created_at END
FROM outfits;

INSERT INTO rentals (id, borrower_id, costume_id, borrowed_on, due_on, returned_on, notes)
SELECT id, borrower_id, outfit_id, substr(borrowed_at, 1, 10), substr(due_at, 1, 10),
       substr(returned_at, 1, 10), notes
FROM old_rentals;

-- The old app allowed renting one outfit twice at once. Keep only the newest
-- open rental per costume; older duplicates are closed on their borrow date.
UPDATE rentals SET returned_on = borrowed_on
WHERE returned_on IS NULL
  AND id NOT IN (SELECT MAX(id) FROM rentals WHERE returned_on IS NULL GROUP BY costume_id);

DROP TABLE old_rentals;
DROP TABLE old_borrowers;
DROP TABLE outfits;
{ACTIVE_RENTAL_INDEX}
"""
