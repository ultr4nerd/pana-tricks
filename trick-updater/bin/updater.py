#!/usr/bin/env python3
"""Actualiza tricks con manifest.source = {repo, path, tag_prefix} desde tags de GitHub (repo público, sin token).
Sólo toca la carpeta del trick; app_support/<id>/ nunca se toca."""
import sys, os, json, re, io, shutil, tarfile, tempfile, subprocess, urllib.request
HOME = os.environ.get("MANO_USER_DIR", os.path.expanduser("~"))
TRICKS = os.path.join(HOME, "tricks")
REFRESH = "/opt/mano/system/scripts/refresh-tricks.sh"
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
def apply(tid):
    info = next((i for i in check() if tid in (i["id"], i["dir"])), None)
    if not info: out({"ok": False, "error": "not_found_or_no_source", "id": tid})
    if info.get("error"): out({"ok": False, "error": info["error"]})
    if not info["update"]: out({"ok": True, "updated": False, "version": info["installed"]})
    s = json.load(open(os.path.join(TRICKS, info["dir"], "manifest.json")))["source"]
    data = get(f"https://codeload.github.com/{s['repo']}/tar.gz/refs/tags/{info['tag']}")
    dest = os.path.join(TRICKS, info["dir"])
    stage = tempfile.mkdtemp(prefix=".upd-", dir=TRICKS)
    try:
        path = s["path"].strip("/")
        with tarfile.open(fileobj=io.BytesIO(data)) as tf:
            for mem in tf.getmembers():
                parts = mem.name.split("/", 1)
                if len(parts) < 2 or not (parts[1] == path or parts[1].startswith(path + "/")): continue
                rel = parts[1][len(path):].lstrip("/")
                if not rel or ".." in rel.split("/") or not (mem.isfile() or mem.isdir()): continue
                mem.name = rel
                tf.extract(mem, stage)
        new = json.load(open(os.path.join(stage, "manifest.json")))
        if new.get("id") != info["id"]: raise RuntimeError("id mismatch in downloaded manifest")
        for f in ("install.sh", "uninstall.sh"):
            if os.path.exists(os.path.join(stage, f)): os.chmod(os.path.join(stage, f), 0o755)
        for root, _, files in os.walk(stage):
            for f in files:
                if f.endswith((".sh", ".py")): os.chmod(os.path.join(root, f), 0o755)
    except Exception as e:
        shutil.rmtree(stage, ignore_errors=True); out({"ok": False, "error": "download: " + str(e)[:160]})
    backup = dest + ".bak-" + info["installed"]
    shutil.rmtree(backup, ignore_errors=True)
    os.rename(dest, backup); os.rename(stage, dest)
    r = subprocess.run(["bash", os.path.join(dest, "install.sh")], capture_output=True, text=True, timeout=300) \
        if os.path.exists(os.path.join(dest, "install.sh")) else None
    if r is not None and r.returncode != 0:
        shutil.rmtree(dest, ignore_errors=True); os.rename(backup, dest)
        out({"ok": False, "error": "install.sh failed, rolled back", "stderr": r.stderr[-300:]})
    shutil.rmtree(backup, ignore_errors=True)
    if os.path.exists(REFRESH): subprocess.run(["bash", REFRESH], capture_output=True, timeout=60)
    out({"ok": True, "updated": True, "id": info["id"], "from": info["installed"], "to": new.get("version")})

if __name__ == "__main__":
    if sys.argv[1] == "check": out({"ok": True, "tricks": check()})
    tid = os.environ.get("TRICK_PAYLOAD_ID", "")
    try: tid = json.loads(tid) if tid.startswith('"') else tid
    except Exception: pass
    apply(tid.strip())
