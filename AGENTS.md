# Instructions for agents using this repository

For installation, read [README.md](README.md), [the agent runbook](docs/agent-setup.md),
[car menus](docs/car-menu.md), [permissions](docs/permissions.md) and
[recovery](docs/recovery.md) before accessing the car. Follow the runbook through
laptop preparation, connection, setup, reboot verification and phone testing.

## Carry out the installation

- Acquire/extract the repository yourself if necessary; Git is optional.
  Preserve an existing checkout, private state, original journals and backups.
- Detect the local laptop OS/CPU, execute Python to verify 3.10+, install missing
  tools from the runbook's trusted sources, and run `prepare.py --json`.
  Use its absolute ADB path. Reuse one interpreter, ADB server port, verified
  USB target and state directory throughout installation and recovery.
- Guide physical actions one at a time, naming the device, screen, control and
  expected result. Wait for a reply or verified device read-back. Handle routine
  computer work yourself. Skip menu onboarding when authorized USB already works.
- Give the actual car-menu steps inline when needed: car Phone → `*#*#888` → Call
  → `1111` → `开发模式`. If separately requested, the development-page default
  is `3821`, found in code but not tested by live entry. Stop if rejected.
  Enable Android USB debugging if needed, select Device模式, connect the laptop
  and have the user accept its debugging authorization.
- Diagnose missing USB before writes. Run `check --json`, then
  `setup --reboot-check --json`. Keep the laptop connected in Device mode until
  the command and reboot verification finish.
- CarLink permissions are automatic within setup. Do not request approval for
  individual grants or send the user through permission screens. Inspect and
  diagnose an unexpected visible blocking screen; exit 3 is a pause, not success.
  Do not guess buttons, cycle launches or bypass a failed identity check.
- On failure inspect `failed_stage`, `recovery`, `component_issues` and
  `next_action`. After USB loss, regain Device mode and use `restore` with the
  original state. Do not repeat raw mutations or replace an interrupted backup.
- `check` and `status` are read-only. Recovery eligibility does not authorize
  setup. An app/process check does not prove that a phone projects successfully.

## Device and recovery boundaries

- Use `oshan_x7.py` for car changes. Unknown firmware/apps/launchers stop writes;
  never weaken checks or add profiles based only on badge/year or AI claims.
- Use local USB and the head unit's existing factory root access (`su 0`). Do not
  install root, flash firmware, edit firmware partitions, enable network ADB or
  install Google services.
- Read [launcher.md](docs/launcher.md) before launcher implementation changes.
  Preserve factory Home/Back overlays and vehicle/media functions. Never remove
  or disable Home for a single user; never add `--user` to launcher rollback.
- Preserve exact firmware, factory/active launcher hashes, UID/version/Home,
  required-app, user-0, root, boot and Device-mode checks. Recovery keeps mandatory
  identity/USB/launcher checks and handles component failures separately. A
  broken receiver or lost root must not alone block a known owned launcher rollback.
- Keep unknown replacement apps. Partial recovery stays incomplete. Preserve old
  journal compatibility internally; do not expose trial/promotion as installation
  prerequisites. `status`/`restore` select the matching records automatically.
- Back up before writes. Publish only the pinned launcher deltas, reconstructed
  from the verified factory base with the exact tested output hash. Never publish
  APKs, raw private dumps, serials, network addresses, credentials or signing keys.
- Remove a lock only after verifying no setup/restore process is running. A stale
  lock can be removed without discarding its backup.

## Completion and development

- After successful setup/reboot checks, complete available car-side onboarding
  and check the card/Home before disconnecting. Then guide laptop disconnect →
  Host模式 → phone connection. Never switch USB roles during laptop commands.
- Use the regular charging/CarAuto USB port for wired projection; do not invent
  a connector position or cable type. Phone-side authorization is separate.
- Record actual AA/CarPlay, fullscreen, card/Home, sound, touch and native-control
  observations. Distinguish them from machine checks and remaining tests.
  Consult [the test record](docs/verified-findings.md) for existing results/limits.
- Do not claim all car-side USB prompts are automated, that Android reboot proves
  cold-ignition reliability, or that the complete fresh setup/restore cycle has
  passed a live test. Those limitations remain in the test record.
- Recovery needs responsive Android/package management and authorized USB.
  Supervision ends when the laptop disconnects. Returning from Host with an
  unusable launcher/menu is untested; do not promise a boot rescue route.
- For code changes run `python3 -m unittest discover -s tests -v`. No car writes
  are needed for development. Keep software-test and car-test claims separate.
