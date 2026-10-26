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

## Where the data lives

The database and photos are stored per user, outside the app folder, so
updating the app never touches them:

- Windows: `%APPDATA%\OutfitManager`
- Linux: `~/.local/share/OutfitManager`

Set `OUTFIT_MANAGER_DATA=/some/folder` to use a different folder. Back up this folder to back up everything.

## Project layout

```
main.py                    entry point
outfit_manager/
  app.py                   window + functions the screens call
  db.py                    SQLite storage and rules (incl. upgrade of old databases)
  photos.py                photo import, resizing, thumbnails
  paths.py                 data folder location
  web/                     the screens (index.html, styles.css, app.js)
```

## AI Usage Disclosure

AI tools were used to support code generation in this project.
