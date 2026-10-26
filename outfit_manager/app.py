"""Starts the app window and exposes Python functions to the web screens."""

import functools
import os
import shutil
import sys
import traceback
from pathlib import Path

import webview

from .db import Database, today
from .paths import data_dir, resource_dir
from .photos import IMAGE_TYPES, PhotoStore

DB_NAME = "outfits.db"


def api_call(func):
    """Return {"ok": true, "data": ...} or {"ok": false, "error": "..."} so the screens can show errors."""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return {"ok": True, "data": func(*args, **kwargs)}
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        except Exception:
            traceback.print_exc()
            return {"ok": False, "error": "Something went wrong. Please try again."}

    return wrapper


class Api:
    """Everything here is callable from JavaScript as window.pywebview.api.<name>(...).

    Attributes starting with "_" are hidden from JavaScript.
    """

    def __init__(self, db: Database, photos: PhotoStore):
        self._db = db
        self._photos = photos
        self._window = None

    def _with_photo(self, item: dict, thumb=True) -> dict:
        return {**item, "photo_url": self._photos.data_url(item.get("photo"), thumb)}

    # --- general ---

    @api_call
    def summary(self):
        return {"today": today(), "overdue_count": self._db.overdue_count()}

    # --- regions ---

    @api_call
    def list_regions(self):
        return [self._with_photo(r) for r in self._db.list_regions()]

    @api_call
    def add_region(self, name):
        return self._db.add_region(name)

    @api_call
    def rename_region(self, region_id, name):
        self._db.rename_region(region_id, name)

    @api_call
    def delete_region(self, region_id):
        self._db.delete_region(region_id)

    # --- costumes ---

    @api_call
    def list_costumes(self, region_id=None, search=""):
        costumes = self._db.list_costumes(region_id)
        if search := (search or "").strip().casefold():
            costumes = [
                c for c in costumes
                if any(search in (c[k] or "").casefold() for k in ("name", "inventory_no", "size", "borrower"))
            ]
        return [self._with_photo(c) for c in costumes]

    @api_call
    def get_costume(self, costume_id):
        costume = self._db.get_costume(costume_id)
        if not costume:
            raise ValueError("This costume no longer exists.")
        return {**self._with_photo(costume, thumb=False), "history": self._db.list_history(costume_id=costume_id)}

    @api_call
    def add_costume(self, data):
        return self._db.add_costume(
            data.get("region_id"), data.get("name"), data.get("inventory_no"),
            data.get("size"), data.get("description"), data.get("photo"),
        )

    @api_call
    def update_costume(self, costume_id, data):
        self._db.update_costume(
            costume_id, data.get("region_id"), data.get("name"), data.get("inventory_no"),
            data.get("size"), data.get("description"),
        )
        if "photo" in data:
            old = self._db.set_costume_photo(costume_id, data["photo"])
            if old != data["photo"]:
                self._photos.remove(old)

    @api_call
    def delete_costume(self, costume_id):
        self._db.delete_costume(costume_id)

    # --- photos ---

    @api_call
    def pick_photo(self):
        """Let the user choose an image file; returns {"photo", "photo_url"} or None if cancelled."""
        types = ("Images (" + ";".join(IMAGE_TYPES) + ")",)
        result = self._window.create_file_dialog(webview.FileDialog.OPEN, file_types=types)
        if not result:
            return None
        name = self._photos.add(result[0])
        return {"photo": name, "photo_url": self._photos.data_url(name, thumb=False)}

    @api_call
    def discard_photo(self, name):
        """Remove a photo picked in a form that was then cancelled."""
        self._photos.remove(name)

    # --- borrowers & rentals ---

    @api_call
    def borrower_names(self):
        return self._db.borrower_names()

    @api_call
    def rent(self, costume_id, data):
        return self._db.rent(
            costume_id, data.get("borrower"), data.get("borrowed_on"), data.get("due_on"), data.get("notes")
        )

    @api_call
    def return_rental(self, rental_id, returned_on=None):
        self._db.return_rental(rental_id, returned_on)

    @api_call
    def list_active_rentals(self):
        return [self._with_photo(r) for r in self._db.list_active_rentals()]

    @api_call
    def list_history(self, search=""):
        return [self._with_photo(r) for r in self._db.list_history(search)]


def _copy_legacy_db(target: Path):
    """When running from source, carry over the old outfits.db from the project folder once."""
    legacy = Path(__file__).resolve().parent.parent / DB_NAME
    if not target.exists() and legacy.exists():
        shutil.copy2(legacy, target)


FROZEN = getattr(sys, "frozen", False)  # True inside the PyInstaller build
IS_LINUX = sys.platform.startswith("linux")


def _gui():
    """Which window engine pywebview should use (None = its default)."""
    if IS_LINUX and FROZEN:
        # The Linux build bundles Qt; the system WebKitGTK is only used when running from source
        return "qt"
    return None


def self_test() -> int:
    """Check the build can start: bundled screens, database, photos and window engine. Returns an exit code."""
    import tempfile

    try:
        index = resource_dir() / "web" / "index.html"
        assert index.exists(), f"missing {index}"
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / DB_NAME)
            region = db.add_region("Test")
            costume = db.add_costume(region, "Test costume")
            db.rent(costume, "Tester", today(), today())
            assert db.list_active_rentals(), "rental not saved"
            PhotoStore(Path(tmp) / "photos")
        import importlib

        # (`from webview import guilib` would give pywebview's attribute of that name, not the module)
        importlib.import_module("webview.guilib").initialize(_gui())  # imports the window engine (WinForms/WebView2 or Qt)
        result, code = "self-test ok", 0
    except Exception:
        result, code = traceback.format_exc(), 1
    # The Windows build has no console, so the result can also go to a file
    if log := os.environ.get("OUTFIT_MANAGER_SELFTEST_LOG"):
        Path(log).write_text(result + "\n", encoding="utf-8")
    print(result)
    return code


def main():
    if IS_LINUX:
        # WebKitGTK's default renderer crashes on some setups (e.g. NVIDIA on Wayland)
        os.environ.setdefault("WEBKIT_DISABLE_DMABUF_RENDERER", "1")
        if FROZEN:
            # Qt's browser sandbox is blocked on some distros (e.g. Ubuntu's user-namespace rules).
            # The app only shows its own local screens, so it is safe to turn off.
            os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")
    folder = data_dir()
    db_path = folder / DB_NAME
    _copy_legacy_db(db_path)
    api = Api(Database(db_path), PhotoStore(folder / "photos"))
    api._window = webview.create_window(
        "Outfit Manager",
        str(resource_dir() / "web" / "index.html"),
        js_api=api,
        width=1280,
        height=820,
        min_size=(960, 640),
        background_color="#FAF7F2",
    )
    # Window icon (Linux; on Windows the icon comes from the .exe)
    webview.start(gui=_gui(), icon=str(resource_dir() / "assets" / "icon.png"))
