#!/usr/bin/env python3
"""Súper compartido: puente servidor -> Worker. id+llave viven sólo en state.json (0600)."""
import sys, os, json, re, urllib.request, urllib.error
BASE = os.environ.get("SUPER_SHARED_URL", "https://super.leaveittoalfred.com")
APP = os.environ.get("TRICK_APP_SUPPORT") or os.path.join(os.environ.get("MANO_USER_DIR", os.path.expanduser("~")), "app_support/com.mauricio.super-compartido")
ST = os.path.join(APP, "state.json")
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"

def out(o): print(json.dumps(o, ensure_ascii=False)); sys.exit(0)
def load():
    try: return json.load(open(ST))
    except Exception: return None
def save(s):
    os.makedirs(APP, exist_ok=True); tmp = ST + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f: json.dump(s, f)
    os.replace(tmp, ST)
def call(path, body, key=None):
    h = {"content-type": "application/json", "user-agent": UA}
    if key: h["x-list-key"] = key
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode(), headers=h, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=12) as r: return json.load(r)
    except urllib.error.HTTPError as e:
        try: return json.load(e)
        except Exception: return {"ok": False, "error": f"http_{e.code}"}
    except Exception as e: return {"ok": False, "error": "offline", "detail": str(e)[:120]}
def payload(name):
    v = os.environ.get("TRICK_PAYLOAD_" + name.upper(), "")
    try:
        j = json.loads(v)
        if isinstance(j, (str, int, bool)): return j
    except Exception: pass
    return v
def parse_code(c):
    m = re.search(r"([a-z0-9]{6,32})\.([a-z0-9]{16,64})", str(c).strip().lower())
    return (m.group(1), m.group(2)) if m else (None, None)
def op(s, body):
    r = call(f"/lists/{s['id']}", body, s["key"])
    if r.get("ok"):
        r["configured"] = True; r["code"] = f"{s['id']}.{s['key']}"
        if r.get("name") and r["name"] != s.get("name"): s["name"] = r["name"]; save(s)
    return r

cmd = sys.argv[1] if len(sys.argv) > 1 else "list"
s = load()
if cmd == "list":
    if not s: out({"ok": True, "configured": False})
    out(op(s, {"op": "get"}))
if cmd == "create":
    items = []
    if len(sys.argv) > 2:  # opcional: importar items desde un JSON [{name,checked,created_at}]
        items = json.load(open(sys.argv[2]))
    r = call("/lists", {"name": (payload("name") or "Súper").strip()[:80], "items": items})
    if not r.get("ok"): out(r)
    save({"id": r["id"], "key": r["key"], "name": r.get("name")})
    r.pop("key", None); r["configured"] = True; out(r)
if cmd == "join":
    i, k = parse_code(payload("code"))
    if not i: out({"ok": False, "error": "bad_code"})
    r = op({"id": i, "key": k}, {"op": "get"})
    if not r.get("ok"): out(r)
    save({"id": i, "key": k, "name": r.get("name")}); out(r)
if cmd == "leave":
    if os.path.exists(ST): os.remove(ST)
    out({"ok": True, "configured": False})
if not s: out({"ok": False, "error": "not_configured"})
if cmd == "add": out(op(s, {"op": "add", "name": str(payload("name"))}))
if cmd in ("toggle", "delete"):
    i = re.sub(r"\D", "", str(payload("id")))
    if not i: out({"ok": False, "error": "id"})
    out(op(s, {"op": cmd, "id": int(i)}))
if cmd == "clear_checked": out(op(s, {"op": "clear_checked"}))
if cmd == "rename": out(op(s, {"op": "rename", "name": str(payload("name"))}))
out({"ok": False, "error": "bad_cmd"})
