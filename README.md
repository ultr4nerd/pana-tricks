# pana-tricks

Tricks for Pana, one folder per trick (`super-compartido/`, ...), each with its full source (`manifest.json`, `SKILL.md`, `install.sh`, `uninstall.sh`, `scripts/`, `bin/`, `gui/`).

- Each trick's `manifest.json` has `"source": {"repo": "ultr4nerd/pana-tricks", "path": "<folder>", "tag_prefix": "<folder>-v"}` and a semver `version`. The `trick-updater/` trick uses it to check and apply updates.
- Releases are tagged `<trick>-v<version>` (e.g. `super-compartido-v0.1.0`) and carry the trick's `.trick` package as an asset when one exists.
- No state or credentials live here: each Pana keeps its own data in `~/app_support/<trick-id>/`.
