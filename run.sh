#!/usr/bin/env bash
# Point d'entrée de l'add-on : exporte les options (/data/options.json) en
# variables d'environnement lues par les scripts Python/Node et le
# dashboard, installe la planification cron, puis démarre le serveur.
set -euo pipefail

OPTIONS=/data/options.json

json() { jq -r "$1 // \"\"" "$OPTIONS"; }

export IMMICH_SERVER="$(json '.immich.server')"
export IMMICH_API_KEY="$(json '.immich.api_key')"

export P2A_ENABLED="$(json '.person_to_album.enabled')"
export P2A_SCHEDULE="$(json '.person_to_album.schedule')"
export P2A_LINKS_JSON="$(jq -c '.person_to_album.links' "$OPTIONS")"

export BLOOMIN8_ENABLED="$(json '.bloomin8.enabled')"
export BLOOMIN8_SCHEDULE="$(json '.bloomin8.schedule')"
export BLOOMIN8_ALBUM_ID="$(json '.bloomin8.album_id')"
export BLOOMIN8_ORIENTATION="$(json '.bloomin8.orientation')"
export BLOOMIN8_DEST_PATH="$(json '.bloomin8.destination_path')"
export BLOOMIN8_RES_WIDTH="$(json '.bloomin8.resolution_width')"
export BLOOMIN8_RES_HEIGHT="$(json '.bloomin8.resolution_height')"
export BLOOMIN8_COLOR_GAMMA="$(json '.bloomin8.color_gamma')"
export BLOOMIN8_COLOR_SATURATION="$(json '.bloomin8.color_saturation')"
export BLOOMIN8_COLOR_LIFT="$(json '.bloomin8.color_lift')"
export BLOOMIN8_COLOR_LIFT_THRESHOLD="$(json '.bloomin8.color_lift_threshold')"

export FRAME_IP="$(json '.frame.ip')"
export FRAME_TOKEN="$(json '.frame.token')"

export RELANCE_HA_URL="$(json '.relance.ha_url')"
export RELANCE_HA_YAML_PATH="$(json '.relance.ha_yaml_path')"
export RELANCE_HA_DEVICE_ID="$(json '.relance.ha_device_id')"
export RELANCE_AUTO_ENABLED="$(json '.relance.auto_relance_enabled')"
export RELANCE_AUTO_AFTER_HOURS="$(json '.relance.auto_relance_after_hours')"
export RELANCE_NOTIFY_SERVICE="$(json '.relance.notify_service')"

# Fournis par Supervisor : token pour appeler http://supervisor/core/api
export SUPERVISOR_TOKEN="${SUPERVISOR_TOKEN:-}"

mkdir -p /data/state /data/logs

echo "[run.sh] Planification cron..."
python3 /app/regen_crontab.py
cron

echo "[run.sh] Démarrage du serveur (port 8099, Ingress)..."
exec python3 -m uvicorn dashboard.app:app --host 0.0.0.0 --port 8099 --app-dir /app
