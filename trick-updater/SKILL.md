---
name: Actualizador de tricks
description: Revisa (a diario, solo) y aplica actualizaciones de tricks instalados desde GitHub. Úsalo cuando llegue un aviso "[trick-updater]", o cuando el boss pregunte por versiones nuevas o pida actualizar un trick.
---
# Actualizador de tricks
Aplica a todo trick en ~/tricks/ cuyo manifest.json tenga `"source": {"repo":"owner/name","path":"carpeta","tag_prefix":"carpeta-v"}` y un `version` semver.
- `GET localhost:8443/tricks/com.mauricio.trick-updater/_api/queries/check` → `{tricks:[{id,installed,latest,update}]}` (API pública de GitHub, sin token).
- `POST .../_api/events/apply {"id":"<trick-id>"}` → descarga la carpeta en el tag nuevo, reemplaza la carpeta del trick (respaldo + rollback si install.sh falla), corre install.sh y refresh-tricks.sh.
- `POST .../_api/events/self_update {}` → actualiza el propio actualizador (equivale a apply con su id).

## Aviso automático
install.sh deja un cron diario (~10:00 hora del boss, según TIMEZONE en ~/.env) que corre `bin/cron.sh`. Si un trick tiene versión nueva que no se ha avisado antes, despierta a tu Pana con un mensaje que empieza con `[trick-updater]` e incluye versión y cambios. Se avisa una sola vez por versión (estado en ~/app_support/com.mauricio.trick-updater/notified.json).

**Al recibir ese aviso:** dile al boss en UNA línea qué trick tiene versión nueva y qué cambió, y pregúntale si lo actualizas. Aplica (`apply`) SOLO después de que el boss diga que sí. Si no responde o dice que no, no hagas nada.

Nunca toca ~/app_support/<id>/ (los datos del boss).
