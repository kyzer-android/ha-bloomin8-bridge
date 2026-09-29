"""
Dashboard FastAPI de l'add-on — servi via Ingress HA (panneau intégré,
authentifié par la session HA, pas d'URL/port séparé à exposer).
"""
import asyncio
import signal
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

sys.path.insert(0, "/app")
from common_config import get_config, tail_log, log
import bloomin8_relance as relance
import bloomin8_yaml_editor as yaml_editor
import gallery

app = FastAPI(title="BLOOMIN8 Immich Bridge")

STATIC_DIR = Path(__file__).parent / "static"

SCRIPTS = {
    "person_to_album": ["python3", "/app/scripts/person_to_album.py"],
    "bloomin8_optimize": ["node", "/app/scripts/bloomin8_optimize.js"],
}

_running: dict[str, subprocess.Popen] = {}


@app.on_event("startup")
async def _startup():
    asyncio.create_task(relance.auto_relance_loop())


# ---------------------------------------------------------------- status --

@app.get("/api/status")
def api_status():
    cfg = get_config()
    return {
        "immich_server": cfg["immich"]["server"],
        "person_to_album": {
            "enabled": cfg["person_to_album"]["enabled"],
            "schedule": cfg["person_to_album"]["schedule"],
            "links_count": len(cfg["person_to_album"]["links"]),
            "running": "person_to_album" in _running,
        },
        "bloomin8": {
            "enabled": cfg["bloomin8"]["enabled"],
            "schedule": cfg["bloomin8"]["schedule"],
            "album_id": cfg["bloomin8"]["album_id"],
            "orientation": cfg["bloomin8"]["orientation"],
            "destination_path": cfg["bloomin8"]["destination_path"],
            "running": "bloomin8_optimize" in _running,
        },
    }


@app.get("/api/pull-status")
def api_pull_status():
    status = relance.get_last_pull_success()
    return {
        "entity_id": status["entity_id"],
        "last_seen": status["last_seen"].isoformat() if status["last_seen"] else None,
        "last_image_url": status["last_image_url"],
    }


# --------------------------------------------------------- run / logs -----

@app.post("/api/run/{script_name}")
def api_run(script_name: str):
    if script_name not in SCRIPTS:
        raise HTTPException(404, "Script inconnu")
    if script_name in _running:
        raise HTTPException(409, "Déjà en cours d'exécution")

    log_path = f"/data/logs/{script_name}.console.log"
    log_file = open(log_path, "a", encoding="utf-8")
    proc = subprocess.Popen(SCRIPTS[script_name], stdout=log_file, stderr=subprocess.STDOUT)
    _running[script_name] = proc
    log(script_name, "Exécution manuelle déclenchée depuis l'interface.")
    return {"status": "started"}


@app.post("/api/stop/{script_name}")
def api_stop(script_name: str):
    proc = _running.get(script_name)
    if not proc:
        raise HTTPException(409, "Pas en cours d'exécution")
    proc.send_signal(signal.SIGTERM)
    return {"status": "stopping"}


def _reap_finished():
    for name, proc in list(_running.items()):
        if proc.poll() is not None:
            del _running[name]


@app.get("/api/logs/{script_name}")
def api_logs(script_name: str, lines: int = 200):
    _reap_finished()
    safe_names = {"person_to_album", "bloomin8_optimize", "relance", "gallery"}
    if script_name not in safe_names:
        raise HTTPException(404, "Script inconnu")
    return {"lines": tail_log(script_name, lines), "running": script_name in _running}


# ------------------------------------------------------------- relance ----

@app.post("/api/relance")
def api_relance():
    ok, message = relance.send_relance()
    if not ok:
        raise HTTPException(400, message)
    return {"status": "ok", "message": message}


# -------------------------------------------------------- éditeur YAML ----

class DeviceUpdate(BaseModel):
    device_id: str
    name: str
    orientation: str
    wake_up_hours: str


@app.get("/api/yaml/devices")
def api_yaml_devices():
    cfg = get_config()
    try:
        devices = yaml_editor.read_devices(cfg["relance"]["ha_yaml_path"])
    except yaml_editor.Bloomin8YamlError as e:
        raise HTTPException(400, str(e))
    return {"path": cfg["relance"]["ha_yaml_path"], "devices": devices}


@app.post("/api/yaml/devices")
def api_yaml_devices_update(body: DeviceUpdate):
    cfg = get_config()
    try:
        resolved_path = yaml_editor.update_device(
            cfg["relance"]["ha_yaml_path"], body.device_id, body.name, body.orientation, body.wake_up_hours
        )
    except yaml_editor.Bloomin8YamlError as e:
        raise HTTPException(400, str(e))
    return {
        "status": "ok",
        "path": resolved_path,
        "restart_required": True,
        "message": "Fichier mis à jour. Redémarre Home Assistant pour que bloomin8_pull prenne en compte le changement (pas de rechargement à chaud disponible côté intégration).",
    }


@app.post("/api/ha/restart")
def api_ha_restart():
    """Redémarrage EXPLICITE, jamais automatique — déclenché uniquement par
    un clic volontaire dans l'interface."""
    ok = relance.call_ha_service("homeassistant", "restart", {})
    if not ok:
        raise HTTPException(502, "Échec de l'appel API HA pour le redémarrage.")
    return {"status": "restarting"}


# ------------------------------------------------------------- galerie ----

@app.get("/api/gallery")
def api_gallery():
    return {"images": gallery.list_images()}


@app.get("/api/gallery/thumb/{filename}")
def api_gallery_thumb(filename: str):
    try:
        data = gallery.get_thumbnail(filename)
    except gallery.GalleryError as e:
        raise HTTPException(404, str(e))
    return Response(content=data, media_type="image/jpeg")


@app.get("/api/gallery/full/{filename}")
def api_gallery_full(filename: str):
    try:
        data = gallery.get_full(filename)
    except gallery.GalleryError as e:
        raise HTTPException(404, str(e))
    return Response(content=data, media_type="image/jpeg")


class RotateRequest(BaseModel):
    filename: str
    degrees: int


@app.post("/api/gallery/rotate")
def api_gallery_rotate(body: RotateRequest):
    try:
        gallery.rotate_image(body.filename, body.degrees)
    except gallery.GalleryError as e:
        raise HTTPException(400, str(e))
    return {"status": "ok"}


# ------------------------------------------------------------- static -----

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))
