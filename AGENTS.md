# Instructions for agents using this repository

Read [README.md](README.md), [docs/agent-setup.md](docs/agent-setup.md),
[docs/car-menu.md](docs/car-menu.md) and [docs/recovery.md](docs/recovery.md) before
using the car. This is an evidence-based workflow for one tested firmware.

## Current setup: CarLink

The reference car now uses CarLink. Read `docs/carlink-setup.md` and retain its
original state directory. Use `carlink-check` for its read-only status and
`carlink-restore` for its owned recovery; do not run the historical OpenHU
`setup`/`restore` over it. Both AA and CarPlay were owner-confirmed fullscreen;
the large CarLink card and factory Home return were owner-confirmed working.
The exact launcher and fullscreen value survived a normal Android reboot.
The OpenHU workflow below is retained for old journals and the previous baseline.

## Work autonomously within the supported flow

- Prepare the local connected laptop yourself: detect OS/CPU, execute Python to
  verify 3.10+, install missing tools from the trusted sources in agent-setup.md,
  then run `prepare.py --json`. Use the returned absolute ADB path when needed.
  Git is optional; use the repo ZIP. Do not hand routine tool setup to the owner.
- Preserve an existing state directory and journal. Use one interpreter, ADB
  server port, verified USB target and state directory through check/setup/restore.
- Guide the owner through car Phone → `*#*#888` → Call → `1111`, then the exact
  Chinese labels in car-menu.md. Keep the separate development-page default PIN
  and its code-only evidence distinct. Ask for physical/UI actions, visible
  permissions or unavoidable OS approvals. Diagnose missing USB before changes.
- AI-assisted setup still requires the owner to enter codes/PINs, operate the
  car menus and authorize debugging before ADB access exists. Give the exact
  sequence, each PIN's evidence limits and USB-role instructions directly when
  guiding them. In owner-facing AI setup documentation, keep those steps inline;
  a link to car-menu.md supplements them rather than replacing them.
- For the historical OpenHU workflow, run `check --json`, then
  `setup --reboot-check --json`. The CLI journals each
  step, reads back its state and checks app/SystemUI health before continuing.
  Let machine checks and guarded automatic recovery run without asking the owner
  to approve each routine step. Exit 3 means a visible permission prompt: explain
  it, let the owner accept it and rerun the same setup command. Inspect an unknown
  screen rather than guessing or repeatedly launching it.
- On failure, inspect `failed_stage`, `recovery`, `component_issues` and
  `next_action`. Setup uses the same recovery engine as `restore`. After a lost
  connection or incomplete recovery, regain USB Device mode and run `restore`
  with the original state. Do not repeat raw mutations or start a new cycle.
- `check`/`status` are read-only. A recovery-eligible status is not a setup
  compatibility pass. A successful process/foreground check is not a phone test.

## Keep the boundaries

- The experimental CarLink trial uses `carlink-check`,
  `carlink-trial --reboot-check` and `carlink-restore` in `oshan_x7.py`;
  read `docs/carlink-trial.md`. Its separate journal temporarily owns only
  pausing the exact pinned OpenHU and installing/removing the exact CarLink app.
  The owner-authorized `--remove-openhu` mode instead copies/verifies its exact
  installed APK, uninstalls it for user 0 with `-k` to retain data, and reinstalls
  that backup during trial restore. Preserve the APK backup and original journal;
  only the recorded removal plus a valid backup permits its absence in the trial.
  Keep OpenHU data and all existing journals. It does not modify the
  launcher or CarAuto. The owner's requested `carlink-fullscreen` stage owns
  only CarLink's per-app factory fullscreen value, backs it up before writes,
  and restores its original value (or factory-default -1 when absent) during
  trial restore. OpenHU's fullscreen key is unchanged.
  Restore the trial before AA setup/restore.
  The trial-only acceptance of its owned disabled OpenHU is not a full AA
  setup compatibility pass. Qualify projection with both actual phones.
  The owner has now authorized replacing the old setup. `carlink-promote
  --reboot-check` uses the existing journal and guarded launcher migration:
  back up the exact prior launcher and immutable factory APK, reconstruct and
  verify the separately pinned CarLink launcher, install as a signed update,
  check Home/CarLink and reboot. Its extra launcher identity is accepted only
  inside that journal's owned migration. `carlink-restore` first reinstalls the
  exact prior launcher backup, then reverses the owned app/layout changes.
  Preserve the migration journal and all backups even after making CarLink primary.

- Use the deterministic `oshan_x7.py` CLI. Do not improvise shell changes on the
  car. Stop setup on mismatches/errors. Never weaken a check or add a profile
  based only on badge, year, model string or another agent's assertion.
- USB only from the local laptop. Do not enable network ADB, root/flash a unit,
  edit firmware partitions or install Google services. Use only existing `su 0`.
- The pinned launcher update is part of guarded setup/restore. Do not replace,
  disable or remove launchers outside that flow. Read docs/launcher.md before
  implementation changes or qualifying another build. Preserve factory Home/Back
  overlays and all vehicle functions.
- Full setup checks require exact firmware, factory and active launcher hashes,
  UID/version/default HOME, required apps, pinned enabled receiver (if present),
  existing root, boot complete and USB Device mode. Unknown builds stop.
- Recovery has separate component gates: known firmware, factory/active launcher
  identities and authorized USB remain mandatory. A disabled/broken receiver or
  lost root must not by itself block removal of an owned, exact launcher update.
  Unknown receiver APKs are never removed. Partial recovery stays incomplete.
  Never add `--user` to the system launcher-update rollback command.
- Back up before writes. Preserve `.oshan-x7/` (or custom `--state-dir`) and its
  original journal; never commit APKs, private dumps, serials, network addresses,
  credentials or signing keys. Ship the pinned binary patch, reconstruct locally
  from the verified base and require the exact tested output hash.
- Never delete a lock until you establish no setup/restore process is running.
  A verified stale lock can be removed without discarding its backup.

## Finish with real evidence

- Keep the laptop connected in Device mode through setup and the normal Android
  reboot check. Then ask the owner to disconnect it, select Host模式 and connect
  the phone. Never switch the shared role during laptop commands.
- The owner completes onboarding/permissions and tests projection, large AA card,
  Home return, usual radio/music, AC, phone and settings controls. Use actual
  observations; do not infer them from hashes, PIDs or a successful CLI result.
- The video-recording USB port worked on the owner's car; the ordinary port stayed
  unstable. Exact cable/port mapping and some screen captures remain unrecorded.
  Do not invent positions, cable connectors, prompt text or screenshots.
- Microphone/Gemini recognition is unresolved. Wireless after CarAuto disable and
  cold ignition cycles are untested. Do not claim these work. Normal Android
  reboots are separate from ignition cycles. The v0.3 unified setup/recovery/
  reboot workflow has offline tests but still needs a complete live car cycle.
- Recovery needs responsive Android/package management/USB ADB. Supervision ends
  when the laptop disconnects. Returning from Host to Device with a broken
  launcher is unqualified; never promise a boot rescue or verified emergency route.
- For code changes run `python3 -m unittest discover -s tests -v`. No car writes
  are needed for development. Keep software-test claims separate from car tests.
