# PyInstaller recipe for a single-file Outfit Manager app (Windows .exe or Linux binary).
# Build with:  uv run pyinstaller --noconfirm OutfitManager.spec
# Output:      dist/OutfitManager.exe (Windows) or dist/OutfitManager (Linux)
import sys

a = Analysis(
    ["main.py"],
    # The screens and icon, unpacked next to the code at run time (see paths.resource_dir)
    datas=[
        ("outfit_manager/web", "outfit_manager/web"),
        ("outfit_manager/assets", "outfit_manager/assets"),
    ],
    # Not used by the app; keeps the build smaller. GTK is only for running from source on Linux.
    excludes=["tkinter", "gi"],
)
if sys.platform.startswith("linux"):
    # Trim the bundled Qt browser engine (the Linux build is large otherwise):
    # - browser UI translations except English, and the developer tools
    # - Qt's GTK theme plugin, plus the GTK libraries only it needs. A bundled GTK
    #   can also crash when it loads the user's own GTK modules.
    GTK_ONLY = (
        "libgtk-3.", "libgdk-3.", "libatk-1.0.", "libatk-bridge-2.0.", "libatspi.", "libcairo-gobject.",
        "libgdk_pixbuf-2.0.", "libglycin-", "libtinysparql-", "libcloudproviders.", "libepoxy.",
        "libpangocairo-", "libpangoft2-", "libpango-1.0.", "libjson-glib-", "libthai.", "libdatrie.",
        "libfribidi.", "libcairo.", "libpixman-", "libXi.", "libXcursor.", "libXinerama.",
    )

    def keep(entry):
        name = entry[0].replace("\\", "/")
        base = name.rsplit("/", 1)[-1]
        if "qtwebengine_locales/" in name:
            return base == "en-US.pak"
        if "qtwebengine_devtools_resources" in base or "platformthemes/libqgtk3" in name:
            return False
        from_system = str(entry[1]).startswith("/usr/")
        if from_system and base.startswith(GTK_ONLY + ("libicudata.so.", "libicuuc.so.", "libicui18n.so.")):
            return False  # system copies pulled in for GTK; Qt ships its own ICU
        return True

    a.binaries = [b for b in a.binaries if keep(b)]
    a.datas = [d for d in a.datas if keep(d)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="OutfitManager",
    console=False,  # no terminal window behind the app on Windows
    icon="outfit_manager/assets/icon.ico",
    upx=False,
)
