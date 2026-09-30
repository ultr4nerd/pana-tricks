# Súper compartido (com.mauricio.super-compartido)

A grocery list shared across several Panas. The data lives in a Cloudflare Worker + Durable Object (`https://super.leaveittoalfred.com`, source at `$HOME/state/workers/super-compartido/` on the author's box). Each list has an `id` plus a secret `key`, and the share code is `id.key`. The worker stores only the SHA-256 of the key.

- Local state: `app_support/com.mauricio.super-compartido/state.json` (0600) holds `{id,key,name}`. Never put the key in localStorage or logs.
- All traffic goes server -> worker through `bin/super.py` with a browser UA, because the GUI cannot fetch other domains.
- Events: `create_list{name}`, `join_list{code}`, `leave_list{}`, `rename_list{name}`, `add_item{name}`, `toggle_item{id}`, `delete_item{id}`, `clear_checked{}`.
- Query `list` returns `{configured:false}` or `{ok,name,rev,items[],code}`.
- To import items when creating a list: `python3 bin/super.py create items.json` (JSON of `[{name,checked,created_at}]`, name in `TRICK_PAYLOAD_NAME`).
- Redeploying the worker: PUT the script with metadata WITHOUT `migrations` (tag v1 is already applied), or with `old_tag:"v1"` if a new migration is needed.
- `SUPER_SHARED_URL` overrides the backend (for self-hosting).
