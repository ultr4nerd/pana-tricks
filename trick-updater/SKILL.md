---
name: Actualizador de tricks
description: Instala tricks desde un link compartido, los revisa a diario y los actualiza (avisando o solo), y publica tricks propios para compartir. Úsalo cuando llegue un aviso "[trick-updater]", cuando el boss pegue un link github.com/.../tree/<carpeta>-v<versión>/<carpeta>, pregunte por versiones nuevas, pida actualizar o compartir un trick.
---
# Actualizador de tricks
Funciona con todo trick en ~/tricks/ cuyo manifest.json tenga `"source": {"repo":"owner/name","path":"carpeta","tag_prefix":"carpeta-v"}` y `version` semver. Tiene pantalla propia (instalar, lista con Actualizar y Avisarme/Actualizar solo, y Compartir si este Pana puede publicar).

API (`localhost:8443/tricks/com.mauricio.trick-updater/_api/...`):
- `GET queries/state` → `{tricks:[{id,name,installed,latest,update,mode,link}], publisher:{repo,tricks:[...]}|null}`. `queries/check` sigue igual.
- `POST events/install {"url":"https://github.com/<repo>/tree/<carpeta>-v<x.y.z>/<carpeta>"}` → baja esa carpeta en ese tag a ~/tricks/<id>, le escribe `source`, corre install.sh y refresh-tricks.sh. Si ya existía, la reemplaza (con rollback) y no toca ~/app_support/<id>/.
- `POST events/apply {"id":"<trick-id>"}` → actualiza a la última versión. `events/self_update {}` = apply del propio actualizador.
- `POST events/set_mode {"id":"<trick-id>","mode":"notify"|"auto"}` → guarda en ~/app_support/com.mauricio.trick-updater/prefs.json.
- `POST events/publish {"id":"<trick-id>","bump":"patch"|"minor"}` → solo si existe publish.json (abajo). Escanea credenciales (rechaza si encuentra), copia la carpeta sin .env/bases/logs/app_support al clon, sube versión en ambos manifests, commit, tag `<carpeta>-v<versión>`, push. Devuelve `link` para compartir.

## Aviso diario
Cron ~10:00 hora del boss corre `bin/cron.sh`. Por trick con versión nueva:
- modo `notify` (default): te despierta una vez por versión con `[trick-updater] Hay versión nueva…`. Dile al boss en UNA línea qué cambió y pregunta si actualizas. `apply` SOLO si dice que sí.
- modo `auto`: aplica solo y te despierta con `[trick-updater] Actualicé solo…`. Díselo al boss en una línea, sin preguntar.

## Publicar (opcional)
`~/app_support/com.mauricio.trick-updater/publish.json`: `{"repo","clone","branch","token_file","token_key","author_name","author_email"}`. El token se lee de `token_file` al vuelo; nunca se escribe en el repo ni en el remoto guardado.
