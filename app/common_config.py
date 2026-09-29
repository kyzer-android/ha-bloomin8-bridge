"""
Lecture de la config de l'add-on. Contrairement à l'ancien immich-scripts,
il n'y a plus de config.json modifiable depuis le dashboard : la config
vient des options d'add-on (onglet Configuration de HA), exportées en
variables d'environnement par run.sh. Ce module les relit et les type
proprement pour le reste de l'app.

L'état d'exécution (fichiers déjà traités, dernier run...) reste, lui,
sur disque dans /data/state — c'est un état interne, pas une config.
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(os.environ.get("DATA_DIR", "/data"))
STATE_DIR = DATA_DIR / "state"
LOG_DIR = DATA_DIR / "logs"


def _bool(v: str, default: bool = True) -> bool:
    if v is None or v == "":
        return default
    return str(v).lower() in ("1", "true", "yes", "on")


def _int(v: str, default: int) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _float(v: str, default: float) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def get_config() -> dict:
    """Reconstruit un dict de config à partir des variables d'environnement
    exportées par run.sh — évite de dépendre de /data/options.json direct
    (dont le format peut légèrement varier), et donne un seul point de
    lecture typé pour tout le reste de l'app."""
    links = []
    try:
        links = json.loads(os.environ.get("P2A_LINKS_JSON", "[]"))
    except json.JSONDecodeError:
        links = []

    return {
        "immich": {
            "server": os.environ.get("IMMICH_SERVER", "").rstrip("/"),
            "api_key": os.environ.get("IMMICH_API_KEY", ""),
        },
        "person_to_album": {
            "enabled": _bool(os.environ.get("P2A_ENABLED"), True),
            "schedule": os.environ.get("P2A_SCHEDULE", "*/30 * * * *"),
            "links": [
                link for link in links
                if link.get("person_id") and link.get("album_id")
            ],
        },
        "bloomin8": {
            "enabled": _bool(os.environ.get("BLOOMIN8_ENABLED"), True),
            "schedule": os.environ.get("BLOOMIN8_SCHEDULE", "0 4 * * *"),
            "album_id": os.environ.get("BLOOMIN8_ALBUM_ID", ""),
            "orientation": os.environ.get("BLOOMIN8_ORIENTATION", "landscape"),
            "destination_path": os.environ.get("BLOOMIN8_DEST_PATH", "/media/bloomin8"),
            "resolution": {
                "width": _int(os.environ.get("BLOOMIN8_RES_WIDTH"), 1600),
                "height": _int(os.environ.get("BLOOMIN8_RES_HEIGHT"), 1200),
            },
            "color": {
                "gamma": _float(os.environ.get("BLOOMIN8_COLOR_GAMMA"), 0.85),
                "saturation": _float(os.environ.get("BLOOMIN8_COLOR_SATURATION"), 1.15),
                "lift": _int(os.environ.get("BLOOMIN8_COLOR_LIFT"), 13),
                "liftThreshold": _int(os.environ.get("BLOOMIN8_COLOR_LIFT_THRESHOLD"), 90),
            },
        },
        "frame": {
            "ip": os.environ.get("FRAME_IP", ""),
            "token": os.environ.get("FRAME_TOKEN", ""),
        },
        "relance": {
            "ha_url": os.environ.get("RELANCE_HA_URL", "").rstrip("/"),
            "ha_yaml_path": os.environ.get("RELANCE_HA_YAML_PATH", "custom_yaml/bloomin8.yaml"),
            "ha_device_id": os.environ.get("RELANCE_HA_DEVICE_ID", ""),
            "auto_enabled": _bool(os.environ.get("RELANCE_AUTO_ENABLED"), True),
            "auto_after_hours": _int(os.environ.get("RELANCE_AUTO_AFTER_HOURS"), 12),
            "notify_service": os.environ.get("RELANCE_NOTIFY_SERVICE", ""),
        },
    }


def destination_dir(cfg: dict | None = None) -> Path:
    """Sous-dossier réellement utilisé (portrait/ ou landscape/), celui que
    bloomin8_pull 0.2.x attend sous destination_path."""
    cfg = cfg or get_config()
    base = Path(cfg["bloomin8"]["destination_path"])
    sub = "portrait" if cfg["bloomin8"]["orientation"] == "portrait" else "landscape"
    return base / sub


def load_state(name: str) -> dict:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = STATE_DIR / f"{name}.json"
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(name: str, state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    path = STATE_DIR / f"{name}.json"
    tmp_path = path.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
    tmp_path.replace(path)


def log(script: str, message: str, level: str = "INFO") -> None:
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    line = f"{ts} [{level}] {message}"
    print(line, flush=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_DIR / f"{script}.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def tail_log(script: str, lines: int = 200) -> list[str]:
    path = LOG_DIR / f"{script}.log"
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return f.readlines()[-lines:]
