#!/usr/bin/env python3
"""Génère /etc/cron.d/bloomin8-bridge à partir des schedules configurés."""
import sys

sys.path.insert(0, "/app")
from common_config import get_config

CRONTAB_PATH = "/etc/cron.d/bloomin8-bridge"


def main() -> None:
    cfg = get_config()
    lines = [
        "SHELL=/bin/bash",
        "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "",
    ]

    if cfg["person_to_album"]["enabled"]:
        sched = cfg["person_to_album"]["schedule"]
        lines.append(f"{sched} root cd /app && python3 scripts/person_to_album.py >> /data/logs/cron.log 2>&1")

    if cfg["bloomin8"]["enabled"]:
        sched = cfg["bloomin8"]["schedule"]
        lines.append(f"{sched} root cd /app && node scripts/bloomin8_optimize.js >> /data/logs/cron.log 2>&1")

    lines.append("")  # ligne finale requise par cron

    with open(CRONTAB_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[regen_crontab] Écrit {CRONTAB_PATH} :\n" + "\n".join(lines))


if __name__ == "__main__":
    main()
