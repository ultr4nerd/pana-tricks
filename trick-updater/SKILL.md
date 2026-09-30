---
name: Actualizador de tricks
description: Revisa y aplica actualizaciones de tricks instalados desde GitHub. Úsalo cuando el boss pregunte si hay versiones nuevas de sus tricks o pida actualizar uno.
---
# Actualizador de tricks
Aplica a todo trick en ~/tricks/ cuyo manifest.json tenga `"source": {"repo":"owner/name","path":"carpeta","tag_prefix":"carpeta-v"}` y un `version` semver.
- `GET localhost:8443/tricks/com.mauricio.trick-updater/_api/queries/check` → `{tricks:[{id,installed,latest,update}]}` (API pública de GitHub, sin token).
- `POST .../_api/events/apply {"id":"<trick-id>"}` → descarga la carpeta en el tag nuevo, reemplaza la carpeta del trick (con respaldo y rollback si install.sh falla), corre install.sh y refresh-tricks.sh.
Nunca toca ~/app_support/<id>/ (los datos del boss). Confirma con el boss antes de aplicar.
