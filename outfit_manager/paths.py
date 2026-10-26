"""Where the app keeps its data and finds its bundled files."""

import os
import sys
from pathlib import Path

APP_NAME = "OutfitManager"


def data_dir() -> Path:
    """Per-user folder for the database and photos. Survives app updates.

    Windows: %APPDATA%\\OutfitManager, Linux: ~/.local/share/OutfitManager.
    Set OUTFIT_MANAGER_DATA to use another folder (handy for testing).
    """
    if override := os.environ.get("OUTFIT_MANAGER_DATA"):
        base = Path(override)
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming") / APP_NAME
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / APP_NAME
    (base / "photos").mkdir(parents=True, exist_ok=True)
    return base


def resource_dir() -> Path:
    """Folder holding the app's own files (web screens). Inside the .exe, PyInstaller unpacks them to _MEIPASS."""
    bundle = getattr(sys, "_MEIPASS", None)
    return Path(bundle) / "outfit_manager" if bundle else Path(__file__).parent
