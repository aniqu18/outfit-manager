"""Start Outfit Manager (also the entry point for the Windows and Linux builds).

`--self-test` checks the app can start without opening a window (used by the build).
"""

import sys

from outfit_manager.app import main, self_test

if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    main()
