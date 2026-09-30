#!/bin/bash
TAG="# mano-trick:com.mauricio.trick-updater:daily"
( crontab -l 2>/dev/null | grep -vF "$TAG" ) | crontab - || true
exit 0
