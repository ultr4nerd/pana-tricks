#!/bin/bash
# Revisión diaria: avisa al Pana (una vez por versión) si algún trick tiene actualización.
H="${MANO_USER_DIR:-$HOME}"
mkdir -p "$H/app_support/com.mauricio.trick-updater"
MANO_USER_DIR="$H" python3 "$(dirname "$0")/updater.py" auto >> "$H/app_support/com.mauricio.trick-updater/cron.log" 2>&1
