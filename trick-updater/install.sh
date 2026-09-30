#!/bin/bash
set -e
TRICK_DIR="$(cd "$(dirname "$0")" && pwd)"
H="${MANO_USER_DIR:-$HOME}"
mkdir -p "$H/app_support/com.mauricio.trick-updater"
chmod +x "$TRICK_DIR"/scripts/*.sh "$TRICK_DIR"/bin/*
# ~10:00 hora local del boss (TIMEZONE en ~/.env), convertida a la hora del servidor.
TZ_BOSS="$(grep -s '^TIMEZONE=' "$H/.env" | tail -1 | cut -d= -f2- | tr -d '"'"'")"
HOUR="$(TZB="${TZ_BOSS:-UTC}" python3 -c 'import os,datetime as d
from zoneinfo import ZoneInfo
try: z=ZoneInfo(os.environ["TZB"])
except Exception: z=ZoneInfo("UTC")
t=d.datetime.now(z).replace(hour=10,minute=0,second=0,microsecond=0)
print(t.astimezone().hour)')"
TAG="# mano-trick:com.mauricio.trick-updater:daily"
LINE="7 $HOUR * * * MANO_USER_DIR=$H bash $H/tricks/com.mauricio.trick-updater/bin/cron.sh >/dev/null 2>&1 $TAG"
( crontab -l 2>/dev/null | grep -vF "$TAG"; echo "$LINE" ) | crontab -
