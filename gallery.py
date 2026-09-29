"""
Galerie des images déjà envoyées au cadre BLOOMIN8 : miniatures + rotation
manuelle 90°/-90°, sauvegardée en écrasant le fichier existant (pas
d'historique — cohérent avec le fonctionnement du reste de l'add-on)."""
import io
from pathlib import Path

from PIL import Image

from common_config import destination_dir, log

ALLOWED_EXT = {".jpg", ".jpeg"}


class GalleryError(Exception):
    pass


def _safe_path(filename: str) -> Path:
    """Empêche toute sortie du dossier de destination (../ etc.)."""
    directory = destination_dir()
    candidate = (directory / filename).resolve()
    if directory.resolve() not in candidate.parents:
        raise GalleryError("Nom de fichier invalide.")
    if candidate.suffix.lower() not in ALLOWED_EXT:
        raise GalleryError("Type de fichier non autorisé.")
    return candidate


def list_images() -> list[dict]:
    directory = destination_dir()
    if not directory.exists():
        return []
    items = []
    for f in sorted(directory.iterdir()):
        if f.is_file() and f.suffix.lower() in ALLOWED_EXT:
            stat = f.stat()
            items.append({
                "filename": f.name,
                "size_kb": round(stat.st_size / 1024, 1),
                "modified": stat.st_mtime,
            })
    return items


def get_thumbnail(filename: str, max_width: int = 320) -> bytes:
    path = _safe_path(filename)
    if not path.exists():
        raise GalleryError("Image introuvable.")
    with Image.open(path) as img:
        img = img.convert("RGB")
        ratio = max_width / img.width
        thumb = img.resize((max_width, max(1, round(img.height * ratio))))
        buf = io.BytesIO()
        thumb.save(buf, format="JPEG", quality=80)
        return buf.getvalue()


def get_full(filename: str) -> bytes:
    path = _safe_path(filename)
    if not path.exists():
        raise GalleryError("Image introuvable.")
    return path.read_bytes()


def rotate_image(filename: str, degrees: int) -> None:
    """degrees positif = horaire (sens visuel bouton "tourner à droite")."""
    if degrees not in (90, -90, 180):
        raise GalleryError("Rotation non supportée (90, -90 ou 180 uniquement).")

    path = _safe_path(filename)
    if not path.exists():
        raise GalleryError("Image introuvable.")

    with Image.open(path) as img:
        img = img.convert("RGB")
        # PIL.rotate() tourne dans le sens ANTI-horaire pour un angle positif
        # -> on inverse le signe pour que "+90" corresponde à une rotation
        # horaire, plus intuitive côté bouton dans l'interface.
        rotated = img.rotate(-degrees, expand=True)
        rotated.save(path, format="JPEG", quality=95)

    log("gallery", f"Image {filename} pivotée de {degrees}°.")
