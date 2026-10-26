# Restore and recover

There is **one restore command** for the changes made by this setup cycle. The
same engine runs automatically when a setup stage fails. It uses the saved
original state and ownership journal; it is not a factory reset.

## Normal restore, or resume after a lost cable

1. Keep the original repository and `.oshan-x7` folder. If you used a custom
   `--state-dir`, keep and reuse that directory instead.
2. Disconnect the phone. On the car, select **Device模式** in the factory
   development page. [Car menu and exact labels](car-menu.md).
3. Connect the laptop with the working USB data cable. Accept its debugging
   prompt on the car if shown. The agent diagnoses USB access before writes.
4. Run in the original repo folder, using the same interpreter, ADB path/port,
   USB target and state directory as setup:

   ```sh
   python3 oshan_x7.py status --json
   python3 oshan_x7.py restore --json
   ```

   Windows: use `py -3` instead of `python3`.
5. Read the result. **`restored`** means the owned changes were reversed and Home
   health checked. **`recovery_required`** means some work remains. Keep the
   journal, address the reported issue and rerun restore. Do not delete the
   backup or repeat raw shell mutations.

Repeated completed restore makes no device writes. After a completed restore,
keep that cycle and choose a new state directory for a later setup. Do not
replace the original baseline with a snapshot taken halfway through recovery.

## What the single restore covers

| Component | What is restored | What is kept |
| --- | --- | --- |
| Launcher | Removes only the exact known update this journal attempted over the factory base; Android falls back to the unchanged factory APK | Launcher data; any update already present before setup |
| Home | Opens and checks the original launcher after rollback | Unknown/default HOME is not forcibly reassigned |
| Fullscreen | Returns a changed receiver setting to its original behavior | Other SystemUI preferences; a setting this cycle never attempted |
| CarAuto | Returns a changed enabled state to the exact saved state | Other apps and vehicle services |
| Receiver | Removes the exact pinned receiver only if absent before this cycle and installation was attempted | A preexisting receiver and its preferences; unknown replacement APKs |

The system-launcher rollback uses `pm uninstall -k` **without `--user`**. Adding
`--user` would be a different operation. Use the CLI, not a copied raw command.
An originally absent fullscreen key is left absent if unchanged; if setup wrote
it, restore uses `-1` for the factory-default behavior. It does not overwrite all
SystemUI preferences. Removing a receiver newly installed by this cycle also
removes its generated app data.

Receiver onboarding choices, Show toast messages, phone permissions, USB role,
and earlier changes made outside this journal are not reverted. A preexisting
launcher from an earlier private installation is not owned by a new public cycle.
Legacy v0.1 backups retain their AA-only scope; v0.2/v0.3 launcher ownership is
preserved when those journals are loaded.

## How recovery decides what is safe

Setup needs the complete healthy configuration. Recovery uses separate component
checks so the broken thing does not prevent fixing an independently verified
thing. It still requires authorized **USB**, the saved device/profile identity,
matching firmware/display/user, known immutable factory and active launcher
hashes, UID/version/system-app registration, and **Device** mode. There is no
force/compatibility bypass.

A disabled receiver, malformed fullscreen XML or lost existing root can be
reported as a component issue while a journal-owned exact launcher update is
rolled back through standard package management. Root-dependent settings remain
blocked until their own checks pass. An unknown receiver APK is kept. An unknown
firmware or launcher identity blocks writes. An unexpected default Home can be
recovered only through a known owned launcher rollback, not by guessing a new Home.

Recovery verifies each eligible step and records errors without claiming full
success. It can reverse independent owned settings even if another component is
blocked. It retains a newly installed receiver until Home and any owned CarAuto
recovery have verified, so it does not remove that route during a Home failure.
An uncertain completed install or rollback is read back before deciding what
still needs doing; successful launcher removal is not blindly repeated.

## If Home is blank or crashing

**While the laptop is still connected in Device mode:** the agent can use
`status` and `restore` if Android, package management and authorized USB ADB still
respond. Setup's immediate crash/foreground checks attempt recovery automatically.
Keep the cable and power connected. A healthy process alone cannot prove every
part of the car UI works, so confirm Home and usual controls afterwards.

**After switching to Host and connecting the phone:** supervision has ended.
If the factory menu is accessible, disconnect the phone, return to Device and
reconnect the laptop. **We have not qualified a route to Device mode when the
launcher/menu cannot be opened in Host mode.** Do not promise an emergency button,
a second debugging port, automatic boot rollback or a guaranteed recovery menu.

**If Android/ADB/package management cannot respond:** this USB workflow cannot
execute rollback. Preserve the backup and stop improvising. Firmware flashing,
partition repair and hardware recovery are outside this project. The unchanged
system APK is useful only while Android can actually restore it.

`--reboot-check` checks a normal Android reboot before the phone handoff; it does
not install a resident watchdog and does not qualify a cold ignition cycle.
The complete v0.3 recovery/reboot flow still needs a controlled live test.

## Lock after a laptop crash

`operation.lock` prevents simultaneous setup/restore. An agent should inspect its
PID and the host's process list/command line to establish whether that operation
is still running. Wait for a real operation; do not kill it or remove its lock.
A PID alone can be reused. Only after verifying the lock is stale may the agent
remove **that lock file**, retain the backup, and resume with restore. Do not
silence an error by deleting `.oshan-x7`.
