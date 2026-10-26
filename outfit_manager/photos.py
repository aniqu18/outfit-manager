"""Costume photos: copied into the data folder as a large image plus a small thumbnail."""

import base64
import uuid
from pathlib import Path

from PIL import Image, ImageOps

FULL_SIZE = 1600
THUMB_SIZE = 480
IMAGE_TYPES = ("*.jpg", "*.jpeg", "*.png", "*.webp", "*.bmp", "*.gif")


class PhotoStore:
    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)

    def _paths(self, name: str):
        return self.folder / f"{name}.jpg", self.folder / f"{name}_thumb.jpg"

    def add(self, source) -> str:
        """Import an image file; returns the stored photo name."""
        try:
            with Image.open(source) as img:
                img = ImageOps.exif_transpose(img)  # respect phone camera rotation
                if img.mode != "RGB":
                    background = Image.new("RGB", img.size, "white")
                    rgba = img.convert("RGBA")
                    background.paste(rgba, mask=rgba.getchannel("A"))
                    img = background
                name = uuid.uuid4().hex
                full, thumb = self._paths(name)
                for path, size in ((full, FULL_SIZE), (thumb, THUMB_SIZE)):
                    copy = img.copy()
                    copy.thumbnail((size, size), Image.Resampling.LANCZOS)
                    copy.save(path, "JPEG", quality=85, optimize=True)
                return name
        except (OSError, ValueError) as e:
            raise ValueError(f"Could not open this image: {Path(source).name}") from e

    def remove(self, name):
        if name:
            for path in self._paths(name):
                path.unlink(missing_ok=True)

    def data_url(self, name, thumb: bool = True):
        """The photo as a data: URL the web screens can show directly, or None."""
        if not name:
            return None
        path = self._paths(name)[1 if thumb else 0]
        if not path.exists():
            return None
        return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode("ascii")
