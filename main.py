import os
import sys
from db import init_db, get_connection
from gui import run_gui

DB_PATH = os.path.join(os.path.dirname(__file__), "outfits.db")


def main():
    # Ensure database exists and schema is ready
    init_db(DB_PATH)
    # Launch GUI
    run_gui(DB_PATH)


if __name__ == "__main__":
    main()
