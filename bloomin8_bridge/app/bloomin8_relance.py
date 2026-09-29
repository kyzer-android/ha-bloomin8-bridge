"""
Relance du pull BLOOMIN8 (remplace le package YAML rest_command/script/
automation qu'on avait mis directement dans Home Assistant) :

- send_relance(): envoie le PUT au cadre avec un cron_time proche (comme le
  script HA qu'on avait) pour le forcer à recontacter HA immédiatement.
- get_last_pull_success(): lit l'état du binary_sensor créé par
  bloomin8_pull via l'API Home Assistant (accessible depuis l'add-on sans
  configuration : Supervisor fournit un token avec accès à
  http://supervisor/core/api dès que `homeassistant_api: true` est déclaré
  dans config.yaml).
- auto_relance_loop(): tâche de fond — relance automatiquement si aucun
  pull réussi depuis N heures (configurable), avec notification HA native.
"""
import asyncio
import os
from datetime import datetime, timedelta, timezone

import requests
from slugify import slugify

from common_config import get_config, log
from bloomin8_yaml_editor import read_devices

SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
HA_API_BASE = "http://supervisor/core/api"


def _ha_headers() -> dict:
    return {
        "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
        "Content-Type": "application/json",
    }


def get_ha_state(entity_id: str) -> dict | None:
    try:
        resp = requests.get(f"{HA_API_BASE}/states/{entity_id}", headers=_ha_headers(), timeout=10)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        log("relance", f"Erreur lecture état HA {entity_id} : {e}", "ERROR")
        return None


def call_ha_service(domain: str, service: str, data: dict) -> bool:
    try:
        resp = requests.post(
            f"{HA_API_BASE}/services/{domain}/{service}",
            headers=_ha_headers(),
            json=data,
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except requests.RequestException as e:
        log("relance", f"Erreur appel service HA {domain}.{service} : {e}", "ERROR")
        return False


def detect_binary_sensor_entity_id(cfg: dict | None = None) -> str | None:
    """Dérive automatiquement l'entity_id binary_sensor créé par
    bloomin8_pull pour le device configuré, à partir de son `name` dans le
    YAML (même convention que l'intégration : bloomin8_pull_<slug(name)>_last_pull_success)."""
    cfg = cfg or get_config()
    device_id = cfg["relance"]["ha_device_id"]
    if not device_id:
        return None
    devices = read_devices(cfg["relance"]["ha_yaml_path"])
    device = devices.get(device_id)
    if not device:
        return None
    slug = slugify(device.get("name", device_id), separator="_")
    return f"binary_sensor.bloomin8_pull_{slug}_last_pull_success"


def get_last_pull_success(cfg: dict | None = None) -> dict:
    """Retourne {entity_id, last_seen (datetime|None), last_image_url}."""
    cfg = cfg or get_config()
    entity_id = detect_binary_sensor_entity_id(cfg)
    if not entity_id:
        return {"entity_id": None, "last_seen": None, "last_image_url": None}

    state = get_ha_state(entity_id)
    if not state:
        return {"entity_id": entity_id, "last_seen": None, "last_image_url": None}

    attrs = state.get("attributes", {})
    last_seen_raw = attrs.get("last_seen")
    last_seen = None
    if last_seen_raw:
        try:
            last_seen = datetime.fromisoformat(last_seen_raw.replace("Z", "+00:00"))
        except ValueError:
            pass

    return {
        "entity_id": entity_id,
        "last_seen": last_seen,
        "last_image_url": attrs.get("last_image_url"),
    }


def send_relance(cfg: dict | None = None, delay_minutes: int = 2) -> tuple[bool, str]:
    """Envoie le PUT au cadre. Retourne (succès, message)."""
    cfg = cfg or get_config()
    frame_ip = cfg["frame"]["ip"]
    frame_token = cfg["frame"]["token"]
    ha_url = cfg["relance"]["ha_url"]

    if not frame_ip or not frame_token or not ha_url:
        msg = "IP du cadre, token ou URL HA manquants dans la configuration de l'add-on."
        log("relance", msg, "ERROR")
        return False, msg

    cron_time = (datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)).strftime("%Y-%m-%dT%H:%M:00Z")
    payload = {
        "upstream_on": True,
        "upstream_url": ha_url,
        "token": frame_token,
        "cron_time": cron_time,
    }

    try:
        resp = requests.put(f"http://{frame_ip}/upstream/pull_settings", json=payload, timeout=15)
        resp.raise_for_status()
        log("relance", f"Relance envoyée au cadre {frame_ip}, cron_time={cron_time}")
        return True, f"Relance envoyée, prochain pull vers {cron_time}."
    except requests.RequestException as e:
        msg = f"Impossible de contacter le cadre ({frame_ip}) : {e}"
        log("relance", msg, "ERROR")
        return False, msg


async def auto_relance_loop() -> None:
    """Tâche de fond : vérifie périodiquement le dernier pull réussi, et
    relance automatiquement après N heures de silence (une seule tentative,
    puis notification — pas de boucle infinie en cas de cadre HS)."""
    already_alerted = False

    while True:
        cfg = get_config()
        if not cfg["relance"]["auto_enabled"]:
            await asyncio.sleep(600)
            continue

        threshold_hours = cfg["relance"]["auto_after_hours"]
        status = get_last_pull_success(cfg)
        last_seen = status["last_seen"]

        if last_seen is not None:
            silence = datetime.now(timezone.utc) - last_seen
            if silence > timedelta(hours=threshold_hours):
                if not already_alerted:
                    log("relance", f"Aucun pull depuis {silence}, relance automatique.", "WARN")
                    ok, _ = send_relance(cfg)
                    if ok:
                        await asyncio.sleep(600)  # 10 min pour laisser le cadre répondre
                        status_after = get_last_pull_success(cfg)
                        recovered = (
                            status_after["last_seen"] is not None
                            and status_after["last_seen"] > last_seen
                        )
                        notify_service = cfg["relance"]["notify_service"]
                        if notify_service:
                            domain, _, service = notify_service.partition(".")
                            if recovered:
                                call_ha_service(domain, service, {
                                    "title": "BLOOMIN8 ✅",
                                    "message": "Pull relancé automatiquement, le cadre a répondu.",
                                })
                            else:
                                call_ha_service(domain, service, {
                                    "title": "BLOOMIN8 ⚠️",
                                    "message": f"Relance auto sans réponse du cadre après 10 min (silence : {silence}).",
                                })
                    already_alerted = True
            else:
                already_alerted = False

        await asyncio.sleep(600)
