# Instructions for agents using this repository

I put this repo together after getting wired Android Auto working on my Oshan X7.
Only the firmware I tested is supported here. If you're an agent helping someone
use it, follow the workflow below rather than guessing at another unit's settings.
Read README.md, docs/agent-setup.md, and docs/car-menu.md before starting.

- Take responsibility for host preparation. Detect the local OS, verify Python
  3.10+ and ADB by running them, and install missing tools from the official or
  trusted OS sources in docs/agent-setup.md. Do not hand tool installation back to
  the owner when you can perform it. Use the repo ZIP if Git is absent.
- Once Python works, run `prepare.py --json` to find/download and verify ADB.
  Use the returned absolute tool path if needed; avoid requiring global PATH edits.
- Guide the native car dialer `*#*#888` → Call → `1111`, then the actual Chinese
  labels in docs/car-menu.md. Keep the separate development-page PIN and its
  evidence limits distinct. Ask only for physical/UI actions or unavoidable OS
  approvals, and diagnose missing USB access before attempting car changes.

- Use the deterministic `oshan_x7.py` CLI. Do not improvise shell changes on the car.
- Run `check --json` before `setup --json`; setup also performs the same check.
- Stop on any compatibility mismatch or error. Never bypass a check or add a
  profile based solely on a vehicle badge, year, model string, or another agent's claim.
- Use USB from the local connected laptop. Do not enable network ADB, root/flash
  a device, edit firmware partitions, or install Google services. The pinned
  launcher update is part of the supported CLI; do not replace, disable or remove
  a launcher outside that guarded setup/restore flow. Read docs/launcher.md before
  changing its implementation or qualifying another build.
- Preserve `.oshan-x7/` (or the chosen `--state-dir`), including its journal. Never
  commit it, APKs, raw device dumps, serial numbers, network addresses, or credentials.
- `check` and `status` make no device writes. `setup` installs the pinned receiver
  if absent, disables only `com.eryanet.vlink`, saves the receiver's factory
  fullscreen preference and installs the exact tested launcher update after
  backing up the original. Existing factory and active launcher hashes, UID,
  version, default HOME and USB Device mode are required. Unknown builds stop.
  `restore` removes only a launcher update owned by its journal before restoring
  the AA settings. Never add `--user` to that system-update rollback command.
- Ship the pinned binary patch, not a full factory/modified APK. Reconstruct it
  locally from the hash-checked factory base and require the exact tested output
  hash before installation. Do not publish signing keys or private deployment state.
- If setup is interrupted, reconnect USB and run restore. Do not rerun raw mutations.
  Do not delete a lock until you have established that no setup/restore process is running.
- Do not switch the shared USB port to Host while the laptop operation is running.
  Ask the person to disconnect the laptop, select Host, and connect the phone after setup.
- The person handles onboarding, visible permissions, phone connection, and actual
  projection checks. A successful CLI result is not proof of a working AA session.
- Check the large Android Auto card, Home return and usual native controls after
  setup and after a normal Android reboot. The recording USB port worked on the
  owner's car; the other port remained unstable. Voice recognition is unresolved;
  do not claim this launcher fixes it. Keep full ignition cycles distinct from
  Android reboots and the unified installer's offline tests distinct from car tests.
- Wireless AA is untested after disabling CarAuto. Do not claim it works.
- Do not remove the small factory Home/Back overlays or disable vehicle functions.
- For code changes, run `python3 -m unittest discover -s tests -v`. Device writes
  are not required for development. Keep device-test claims separate from offline tests.
