#!/usr/bin/env python3
"""Actualiza tricks con manifest.source = {repo, path, tag_prefix} desde tags de GitHub (repo público, sin token).
Sólo toca la carpeta del trick; app_support/<id>/ nunca se toca."""
import sys, os, json, re, io, shutil, tarfile, tempfile, subprocess, urllib.request
HOME = os.environ.get("MANO_USER_DIR", os.path.expanduser("~"))
TRICKS = os.path.join(HOME, "tricks")
REFRESH = "/opt/mano/system/scripts/refresh-tricks.sh"
APP = os.path.join(HOME, "app_support", "com.mauricio.trick-updater")
STATE = os.path.join(APP, "notified.json")
SELF = "com.mauricio.trick-updater"
UA = {"user-agent": "pana-trick-updater", "accept": "application/vnd.github+json"}

def out(o): print(json.dumps(o, ensure_ascii=False)); sys.exit(0)
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r: return r.read()
def semver(v):
    m = re.match(r"^v?(\d+)\.(\d+)\.(\d+)$", str(v).strip())
    return tuple(map(int, m.groups())) if m else None
def sources():
    for d in sorted(os.listdir(TRICKS)):
        p = os.path.join(TRICKS, d, "manifest.json")
        try: m = json.load(open(p))
        except Exception: continue
        s = m.get("source")
        if isinstance(s, dict) and s.get("repo") and s.get("path") and s.get("tag_prefix"):
            yield d, m, s
def latest(s):
    tags, page = [], 1
    while True:
        batch = json.loads(get(f"https://api.github.com/repos/{s['repo']}/tags?per_page=100&page={page}"))
        tags += [t["name"] for t in batch]
        if len(batch) < 100: break
        page += 1
    best = None
    for t in tags:
        if t.startswith(s["tag_prefix"]):
            v = semver(t[len(s["tag_prefix"]):])
            if v and (best is None or v > best[0]): best = (v, t)
    return best
def check():
    res = []
    for d, m, s in sources():
        item = {"id": m.get("id", d), "dir": d, "name": m.get("name"), "installed": m.get("version")}
        try:
            b = latest(s)
            item["latest"] = ".".join(map(str, b[0])) if b else None
            item["tag"] = b[1] if b else None
            cur = semver(m.get("version", "0.0.0")) or (0, 0, 0)
            item["update"] = bool(b and b[0] > cur)
        except Exception as e:
            item["error"] = str(e)[:160]; item["update"] = False
        res.append(item)
    return res
def fail(e, **k): return dict({"ok": False, "error": e}, **k)

def fetch_folder(repo, tag, path, stage):
    data = get(f"https://codeload.github.com/{repo}/tar.gz/refs/tags/{tag}")
    path = path.strip("/"); n = 0
    with tarfile.open(fileobj=io.BytesIO(data)) as tf:
        for mem in tf.getmembers():
            parts = mem.name.split("/", 1)
            if len(parts) < 2 or not (parts[1] == path or parts[1].startswith(path + "/")): continue
            rel = parts[1][len(path):].lstrip("/")
            if not rel or ".." in rel.split("/") or not (mem.isfile() or mem.isdir()): continue
            mem.name = rel; tf.extract(mem, stage); n += 1
    if not n: raise RuntimeError(f"la carpeta {path} no existe en {tag}")
    for f in ("install.sh", "uninstall.sh"):
        if os.path.exists(os.path.join(stage, f)): os.chmod(os.path.join(stage, f), 0o755)
    for root, _, files in os.walk(stage):
        for f in files:
            if f.endswith((".sh", ".py")): os.chmod(os.path.join(root, f), 0o755)
    return json.load(open(os.path.join(stage, "manifest.json")))

def swap_in(dest, stage, label):
    """Reemplaza la carpeta del trick por stage (con respaldo y rollback), corre install.sh y refresh."""
    backup = None
    if os.path.exists(dest):
        backup = dest + ".bak-" + str(label); shutil.rmtree(backup, ignore_errors=True); os.rename(dest, backup)
    os.rename(stage, dest)
    ins = os.path.join(dest, "install.sh")
    r = subprocess.run(["bash", ins], capture_output=True, text=True, timeout=300, env=dict(os.environ, MANO_USER_DIR=HOME)) \
        if os.path.exists(ins) else None
    if r is not None and r.returncode != 0:
        shutil.rmtree(dest, ignore_errors=True)
        if backup: os.rename(backup, dest)
        return "install.sh falló, se restauró la versión anterior: " + (r.stderr or r.stdout)[-300:]
    if backup: shutil.rmtree(backup, ignore_errors=True)
    if os.path.exists(REFRESH) and not os.environ.get("UPDATER_NO_REFRESH"):
        subprocess.run(["bash", REFRESH], capture_output=True, timeout=60)
    return None

def apply(tid):
    info = next((i for i in check() if tid in (i["id"], i["dir"])), None)
    if not info: return fail("not_found_or_no_source", id=tid)
    if info.get("error"): return fail(info["error"])
    if not info["update"]: return {"ok": True, "updated": False, "version": info["installed"]}
    s = json.load(open(os.path.join(TRICKS, info["dir"], "manifest.json")))["source"]
    stage = tempfile.mkdtemp(prefix=".upd-", dir=TRICKS)
    try:
        new = fetch_folder(s["repo"], info["tag"], s["path"], stage)
        if new.get("id") != info["id"]: raise RuntimeError("id mismatch in downloaded manifest")
    except Exception as e:
        shutil.rmtree(stage, ignore_errors=True); return fail("download: " + str(e)[:160])
    err = swap_in(os.path.join(TRICKS, info["dir"]), stage, info["installed"])
    if err: return fail(err)
    return {"ok": True, "updated": True, "id": info["id"], "from": info["installed"], "to": new.get("version")}

LINK = re.compile(r"^https?://github\.com/([\w.-]+/[\w.-]+)/tree/([^/]+?-v)(\d+\.\d+\.\d+)/(.+?)/?$")
def parse_link(url):
    m = LINK.match((url or "").strip())
    if not m: return None
    return {"repo": m.group(1), "tag_prefix": m.group(2), "version": m.group(3), "path": m.group(4),
            "tag": m.group(2) + m.group(3)}

def install(url):
    L = parse_link(url)
    if not L: return fail("El link no tiene la forma https://github.com/<dueño>/<repo>/tree/<carpeta>-v<versión>/<carpeta>")
    os.makedirs(TRICKS, exist_ok=True)
    stage = tempfile.mkdtemp(prefix=".upd-", dir=TRICKS)
    try:
        man = fetch_folder(L["repo"], L["tag"], L["path"], stage)
        tid = man.get("id") or ""
        if not re.match(r"^[a-z0-9][a-z0-9._-]+$", tid) or tid == ".": raise RuntimeError("manifest sin id válido")
        man["source"] = {"repo": L["repo"], "path": L["path"], "tag_prefix": L["tag_prefix"]}
        json.dump(man, open(os.path.join(stage, "manifest.json"), "w"), indent=2, ensure_ascii=False)
    except Exception as e:
        shutil.rmtree(stage, ignore_errors=True); return fail("descarga: " + str(e)[:200])
    dest = os.path.join(TRICKS, tid)
    prev = None
    try: prev = json.load(open(os.path.join(dest, "manifest.json"))).get("version")
    except Exception: pass
    err = swap_in(dest, stage, prev or "old")
    if err: return fail(err)
    return {"ok": True, "installed": tid, "name": man.get("name"), "version": man.get("version"), "replaced": prev}

def changes(s, old_tag, new_tag):
    """Mensajes de release/commits entre el tag instalado y el nuevo (API pública de GitHub)."""
    notes = []
    try:
        r = json.loads(get(f"https://api.github.com/repos/{s['repo']}/releases/tags/{new_tag}"))
        if r.get("body"): notes.append(r["body"].strip())
    except Exception: pass
    if not notes and old_tag:
        try:
            c = json.loads(get(f"https://api.github.com/repos/{s['repo']}/compare/{old_tag}...{new_tag}"))
            path = s["path"].strip("/")
            for cm in c.get("commits", []):
                msg = cm["commit"]["message"].split("\n")[0]
                notes.append("- " + msg)
        except Exception: pass
    return "\n".join(notes)[:600] or "(sin notas)"

def notify_agent(msg):
    if os.environ.get("UPDATER_NOTIFY_LOG"):
        open(os.environ["UPDATER_NOTIFY_LOG"], "a").write(msg + "\n---\n"); return True
    body = json.dumps({"msg": msg[:900], "spawn_session": True}).encode()
    last = None
    for port in [os.environ.get("WEBHOOK_PORT"), "8443", "8080"]:
        if not port: continue
        try:
            req = urllib.request.Request(f"http://localhost:{port}/tricks/{SELF}/_api/notify", data=body,
                                         method="POST", headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as r:
                if r.status < 300: return True
        except Exception as e: last = e
    raise RuntimeError(f"notify failed: {last}")

PREFS = os.path.join(APP, "prefs.json")
PUBCONF = os.path.join(APP, "publish.json")
def load_json(p, d):
    try: return json.load(open(p))
    except Exception: return d
def modes(): return load_json(PREFS, {}).get("modes", {})
def set_mode(tid, mode):
    if mode not in ("notify", "auto"): return fail("modo inválido")
    os.makedirs(APP, exist_ok=True)
    p = load_json(PREFS, {}); p.setdefault("modes", {})[tid] = mode
    json.dump(p, open(PREFS, "w"), indent=1)
    return {"ok": True, "id": tid, "mode": mode}

def link_for(s, version):
    return f"https://github.com/{s['repo']}/tree/{s['tag_prefix']}{version}/{s['path']}"

def auto():
    """Corre desde cron. Modo 'auto': aplica sin preguntar y avisa al Pana de lo hecho.
    Modo 'notify' (default): avisa una sola vez por versión y espera el sí del boss."""
    os.makedirs(APP, exist_ok=True)
    state = load_json(STATE, {}); md = modes()
    sent, applied = [], []
    for i in check():
        if not i.get("update"): continue
        s = json.load(open(os.path.join(TRICKS, i["dir"], "manifest.json")))["source"]
        notes = changes(s, s["tag_prefix"] + str(i["installed"]), i["tag"])
        label = f"«{i.get('name') or i['id']}» ({i['id']})"
        if md.get(i["id"]) == "auto":
            r = apply(i["id"])
            if r.get("ok") and r.get("updated"):
                applied.append(i["id"])
                msg = (f"[trick-updater] Actualicé solo el trick {label}: {i['installed']} → {i['latest']} "
                       f"(el boss lo dejó en 'Actualizar solo').\nCambios:\n{notes}\n"
                       f"Díselo al boss en una línea, sin pedir nada.")
            else:
                msg = (f"[trick-updater] Intenté actualizar solo {label} a {i['latest']} y falló: {r.get('error')}. "
                       f"Dile al boss en una línea.")
            try: notify_agent(msg)
            except Exception: pass
            continue
        if state.get(i["id"]) == i["latest"]: continue
        msg = (f"[trick-updater] Hay versión nueva del trick {label}: "
               f"{i['installed']} → {i['latest']}.\nCambios:\n{notes}\n"
               f"Dile al boss en una línea qué cambió y pregúntale si lo actualizas. SOLO si dice que sí: "
               f"POST localhost:8443/tricks/{SELF}/_api/events/apply {{\"id\":\"{i['id']}\"}}")
        notify_agent(msg)
        state[i["id"]] = i["latest"]; sent.append(i["id"])
        json.dump(state, open(STATE, "w"), indent=1)
    return {"ok": True, "notified": sent, "applied": applied}

# ---------------- publicar ----------------
SKIP_DIRS = {".git", "app_support", "node_modules", "__pycache__", "data", "state", ".venv", "venv"}
SKIP_FILE = re.compile(r"(^\.env.*|.*\.(db|sqlite3?|log|pyc|pem|key|p12|trick)$|^token.*|.*secret.*|.*credential.*|^config\.local.*|.*\.bak.*)", re.I)
SECRET = re.compile(r"(ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|gh[ousr]_[A-Za-z0-9]{30,}|sk-[A-Za-z0-9_-]{20,}|"
                    r"AKIA[0-9A-Z]{16}|xox[abprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{35}|"
                    r"eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY)")

def pubconf():
    c = load_json(PUBCONF, None)
    if not c or not c.get("repo") or not c.get("token_file"): return None
    return c
def token(c):
    t = load_json(c["token_file"], {}).get(c.get("token_key", "github_token"))
    return t if isinstance(t, str) and t else None

def local_tricks():
    res = []
    for d in sorted(os.listdir(TRICKS)) if os.path.isdir(TRICKS) else []:
        if d.startswith(".") or ".bak-" in d: continue
        m = load_json(os.path.join(TRICKS, d, "manifest.json"), None)
        if not m: continue
        res.append({"dir": d, "id": m.get("id", d), "name": m.get("name") or d, "version": m.get("version"),
                    "source": m.get("source") if isinstance(m.get("source"), dict) else None})
    return res

def folder_for(c, t):
    s = t.get("source")
    if s and s.get("repo") == c["repo"] and s.get("path"): return s["path"]
    base = t["id"].split(".")[-1]
    return re.sub(r"[^a-z0-9-]+", "-", base.lower()).strip("-") or t["dir"]

def bump(v, kind):
    a = list(semver(v or "0.0.0") or (0, 0, 0))
    if kind == "minor": a = [a[0], a[1] + 1, 0]
    elif kind == "major": a = [a[0] + 1, 0, 0]
    else: a[2] += 1
    return ".".join(map(str, a))

def git(clone, *args, check=True):
    r = subprocess.run(["git", "-C", clone, *args], capture_output=True, text=True, timeout=180)
    if check and r.returncode != 0: raise RuntimeError(f"git {args[0]}: " + (r.stderr or r.stdout)[-300:])
    return r.stdout.strip()

def publish(tid, kind):
    c = pubconf()
    if not c: return fail("Este Pana no tiene configuración para publicar")
    tok = token(c)
    if not tok: return fail("No encontré la credencial para publicar")
    t = next((x for x in local_tricks() if tid in (x["id"], x["dir"])), None)
    if not t: return fail("No encontré ese trick")
    src = os.path.join(TRICKS, t["dir"])
    folder = folder_for(c, t)
    newv = bump(t["version"], kind)
    tag_prefix = f"{folder}-v"; tag = tag_prefix + newv
    clone = c.get("clone") or os.path.join(HOME, "src", c["repo"].split("/")[-1])
    branch = c.get("branch", "main")
    remote = f"https://x:{tok}@github.com/{c['repo']}.git"
    # 1. escaneo antes de tocar nada
    files, hits = [], []
    for root, dirs, fs in os.walk(src):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        for f in fs:
            if SKIP_FILE.match(f): continue
            p = os.path.join(root, f); rel = os.path.relpath(p, src)
            if os.path.islink(p): continue
            try: txt = open(p, "rb").read()
            except Exception: continue
            s = txt.decode("utf-8", "ignore")
            if SECRET.search(s) or tok in s: hits.append(rel)
            files.append(rel)
    if hits: return fail("Encontré algo que parece una credencial; no publiqué nada", files=hits[:10])
    # 2. clone al día
    try:
        if not os.path.isdir(os.path.join(clone, ".git")):
            os.makedirs(os.path.dirname(clone), exist_ok=True)
            subprocess.run(["git", "-c", "credential.helper=", "clone", remote, clone], capture_output=True, text=True, timeout=180, check=True)
            git(clone, "remote", "set-url", "origin", f"https://github.com/{c['repo']}.git")
        git(clone, "checkout", branch)
        git(clone, "-c", "credential.helper=", "pull", "--ff-only", remote, branch)
        git(clone, "-c", "credential.helper=", "fetch", "--tags", remote)
        if git(clone, "tag", "-l", tag): return fail(f"La versión {newv} ya existe publicada ({tag})")
        # 3. copiar
        dst = os.path.join(clone, folder)
        shutil.rmtree(dst, ignore_errors=True)
        for rel in files:
            os.makedirs(os.path.dirname(os.path.join(dst, rel)), exist_ok=True)
            shutil.copy2(os.path.join(src, rel), os.path.join(dst, rel))
        source = {"repo": c["repo"], "path": folder, "tag_prefix": tag_prefix}
        for mp in (os.path.join(dst, "manifest.json"), os.path.join(src, "manifest.json")):
            m = json.load(open(mp)); m["version"] = newv; m["source"] = source
            json.dump(m, open(mp, "w"), indent=2, ensure_ascii=False); open(mp, "a").write("\n")
        # 4. commit, tag, push
        git(clone, "add", "-A", folder)
        name = c.get("author_name", "Pana"); email = c.get("author_email", "pana@users.noreply.github.com")
        git(clone, "-c", f"user.name={name}", "-c", f"user.email={email}", "commit", "-m", f"{folder} {newv}", "--allow-empty")
        git(clone, "tag", tag)
        git(clone, "-c", "credential.helper=", "push", remote, branch, tag)
    except Exception as e:
        return fail("publicar: " + str(e).replace(tok, "***")[:300])
    return {"ok": True, "id": t["id"], "version": newv, "tag": tag, "link": link_for(source, newv)}

def state():
    md = modes(); items = []
    for i in check():
        i["mode"] = md.get(i["id"], "notify")
        s = load_json(os.path.join(TRICKS, i["dir"], "manifest.json"), {}).get("source")
        if s and i.get("installed"): i["link"] = link_for(s, i["installed"])
        items.append(i)
    c = pubconf(); pub = None
    if c and token(c):
        pub = {"repo": c["repo"], "tricks": []}
        for t in local_tricks():
            s = t.get("source")
            t["link"] = link_for(s, t["version"]) if s and s.get("repo") == c["repo"] and t.get("version") else None
            t["folder"] = folder_for(c, t); t.pop("source", None)
            pub["tricks"].append(t)
    return {"ok": True, "tricks": items, "publisher": pub}

def payload(k):
    v = os.environ.get("TRICK_PAYLOAD_" + k.upper(), "")
    try: v = json.loads(v) if v[:1] in '"{[' else v
    except Exception: pass
    return str(v).strip()

if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "check": out({"ok": True, "tricks": check()})
    if cmd == "state": out(state())
    if cmd == "auto": out(auto())
    if cmd == "self_update": out(apply(SELF))
    if cmd == "install": out(install(sys.argv[2] if len(sys.argv) > 2 else payload("url")))
    if cmd == "set_mode": out(set_mode(payload("id"), payload("mode")))
    if cmd == "publish": out(publish(sys.argv[2] if len(sys.argv) > 2 else payload("id"), sys.argv[3] if len(sys.argv) > 3 else (payload("bump") or "patch")))
    out(apply(payload("id")))
