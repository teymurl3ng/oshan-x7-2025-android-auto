# Instructions for agents using this repository

Read README.md, docs/agent-setup.md, docs/car-menu.md, docs/permissions.md and
docs/recovery.md before using the car. The public workflow installs official
CarLink directly on one exact tested firmware. No older receiver is a prerequisite.

## Work autonomously

- Automatic installation starts with the README prompt, before the owner has a
  checkout or tools. Acquire/extract the repository yourself, preserving any
  existing checkout and private state. Do not ask the owner to download the repo
  or install Git as a prerequisite.
- Detect the local laptop OS/CPU, execute Python to verify 3.10+, install missing
  tools from the trusted sources in agent-setup.md, then run `prepare.py --json`.
  Use its absolute ADB path. Git is optional; the repo ZIP is sufficient.
- Preserve existing state directories, original journals and backups. Use one
  interpreter, ADB server port, verified USB target and state directory throughout.
- Guide the owner through car Phone → `*#*#888` → Call → `1111` → `开发模式`.
  If that development page asks separately, the code-only default is `3821`;
  distinguish this untested live-entry default from the observed outer PIN 1111.
  Stop if rejected. Enable Android USB debugging if needed, select Device模式,
  connect the trusted laptop and have the owner accept debugging authorization.
  Keep these steps inline in owner-facing guidance; car-menu.md supplements them.
- Diagnose missing USB before writes. Existing authorized ADB needs no repeated
  menu onboarding. Run `check --json`, then `setup --reboot-check --json`.
- Request remaining owner actions one at a time, naming the device, screen,
  control and expected result. Wait for a reply or verified read-back before
  moving on; continue routine computer work yourself between those requests.
- CarLink permissions are automatic inside setup. Do not send the owner through
  the app's permission screens or ask approval for each grant. The pinned Android
  9 runtime/app-op/battery grants and built-in USB auto-confirm service are
  journaled, read back and restored through the supported flow.
- Complete routine guarded checks/recovery autonomously. Unexpected visible
  blocking screens still require inspection; never guess, cycle launches or
  bypass a failed identity check. Exit 3 remains a distinct unexpected permission
  pause, not the normal CarLink permission process.
- On failure inspect failed_stage, recovery, component_issues and next_action.
  Regain Device mode and use `restore` with the original state after USB loss.
  Do not repeat raw mutations or create a new baseline over an interrupted cycle.
- `check`/`status` are read-only. Recovery eligibility is not setup compatibility.
  A successful foreground/process check is not a phone projection test.

## Boundaries

- Use the deterministic `oshan_x7.py` CLI for car changes. Stop on mismatches;
  never weaken gates or add profiles based only on badge/year/model or AI claims.
- USB only from the local laptop. Do not enable network ADB, root/flash a unit,
  edit firmware partitions or install Google services. Use only existing `su 0`.
- Read docs/launcher.md before launcher implementation changes. Installation and
  rollback use guarded setup/restore. Preserve factory Home/Back overlays and
  vehicle/media functions. Never remove or disable Home for a single user.
- Require exact firmware, immutable and active launcher hashes, UID/version/Home,
  required apps, pinned official CarLink identity, user 0, root, completed boot
  and Device mode. Unknown builds stop.
- Recovery keeps mandatory firmware/USB/launcher gates and evaluates component
  failures separately. Unknown app replacements are kept. A broken receiver or
  lost root must not alone prevent a known owned launcher rollback. Partial
  recovery stays incomplete. Never add `--user` to launcher-update rollback.
- Back up before writes. Preserve `.oshan-x7/` or custom state and all original
  journals. Never publish APKs, raw private dumps, serials, network addresses,
  credentials or signing keys. Ship the pinned launcher delta, reconstruct from
  the verified factory base and require the exact tested output hash.
- Older journals retain recovery compatibility internally. Do not make a public
  user install an older receiver, run trial/promotion stages or reproduce private
  migration history. Status/restore select matching ownership automatically.
- Never remove a lock until no setup/restore process is running. A verified stale
  lock may be removed without discarding its backup.

## Evidence and completion

- Keep the laptop connected in Device mode through setup and the normal Android
  reboot check. Then disconnect it, select Host模式 and connect the phone. Never
  switch the shared role during laptop commands.
- Owner checks actual AA/CarPlay, fullscreen, large CarLink card, Home return,
  radio/music, AC, phone and settings controls. Distinguish owner observations,
  machine checks and remaining tests. Phone-side authorization is separate.
- The current CarLink tests use the regular charging/CarAuto USB port, as
  confirmed by the owner. Do not invent a connector position/cable type.
- AA and CarPlay fullscreen and large-card/Home behavior were owner-confirmed.
  iPhone cable and wireless CarPlay both worked perfectly in the owner's tests;
  Android wireless is unreliable. The launcher/fullscreen and permission grants
  passed normal Android reboot checks. Microphone/Siri/call audio, long-duration
  reliability, repeated reconnects and cold ignition remain separate tests.
- The enabled USB auto-confirm service did not handle every observed car-side
  prompt; one still needed tapping. Its exact dialog type was not established.
  Do not claim the car-side USB prompt problem is solved.
- The direct-from-factory public setup/restore sequence has offline tests; a
  complete live cycle remains pending. USB service binding alone does not prove
  every real phone prompt is handled; record an actual attach test separately.
- Recovery requires responsive Android/package management and authorized USB.
  Supervision ends when the laptop disconnects. Returning from Host with an
  unusable launcher/menu is unqualified; never promise a boot rescue route.
- For code changes run `python3 -m unittest discover -s tests -v`. No car writes
  are needed for development. Keep software-test and car-test claims separate.
