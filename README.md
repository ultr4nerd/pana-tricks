# pana-tricks

Tricks for Pana, one folder per trick (`super-compartido/`, ...), each with its full source (`manifest.json`, `SKILL.md`, `install.sh`, `uninstall.sh`, `scripts/`, `bin/`, `gui/`).

- Each trick's `manifest.json` has `"source": "https://github.com/ultr4nerd/pana-tricks"` and a semver `version`, so a Pana can tell where updates come from and whether it is behind.
- Releases are tagged `<trick>-v<version>` (e.g. `super-compartido-v0.1.0`) and carry the trick's `.trick` package as an asset when one exists.
- No state or credentials live here: each Pana keeps its own data in `~/app_support/<trick-id>/`.
