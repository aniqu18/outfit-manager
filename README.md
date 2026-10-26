# Outfit Manager

- **Costumes** are grouped by region each with a photo, inventory number and size.
- **Rent out** a costume to someone with a return-by date; **take it back** when it is returned.
- **Rentals** lists everything that is out, with overdue costumes first.
- **History** shows past rentals and whether they came back on time.

Built with Python, [pywebview](https://pywebview.flowrl.com/) (the window) and
SQLite. The screens are plain HTML/CSS/JS in `outfit_manager/web/`.

## Run from source

```sh
uv run main.py
```

On Linux, pywebview uses WebKitGTK: install `webkit2gtk-4.1` and
`gobject-introspection` from your distro.

## Download

Ready-to-run builds are attached to each
[GitHub release](../../releases):

- **Windows:** `OutfitManager-windows.exe` – double-click to start. Windows may
  show a SmartScreen warning the first time because the app isn't signed:
  click *More info → Run anyway*.
- **Linux (x86_64):** `OutfitManager-linux-x86_64.tar.gz` – unpack and run
  `./OutfitManager`. It brings its own browser engine (Qt), so it doesn't need
  WebKitGTK.

## Building

The builds are made by GitHub Actions (`.github/workflows/build.yml`):

To build locally (only for the system you're on – Windows builds need Windows):

```sh
uv sync --no-default-groups --group build                # Windows
uv sync --no-default-groups --group build --group qt     # Linux
uv run --no-sync pyinstaller --noconfirm OutfitManager.spec
dist/OutfitManager --self-test
```

Run `uv sync` afterwards to get the normal development setup back.

## Where the data lives

The database and photos are stored per user, outside the app folder, so
updating the app never touches them:

- Windows: `%APPDATA%\OutfitManager`
- Linux: `~/.local/share/OutfitManager`

Set `OUTFIT_MANAGER_DATA=/some/folder` to use a different folder. Back up this folder to back up everything.

## Project layout

```
main.py                    entry point (`--self-test` checks a build can start)
OutfitManager.spec         PyInstaller build recipe
.github/workflows/build.yml  Windows + Linux builds and releases
outfit_manager/
  app.py                   window + functions the screens call
  db.py                    SQLite storage and rules (incl. upgrade of old databases)
  photos.py                photo import, resizing, thumbnails
  paths.py                 data folder location
  web/                     the screens (index.html, styles.css, app.js)
  assets/                  app icon
```

## AI Usage Disclosure

AI tools were used to support code generation in this project.
