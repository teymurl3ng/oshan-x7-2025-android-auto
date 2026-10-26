# Testing and qualification

Software tests, artifact checks and actual car behavior are different evidence.
The v0.3 workflow has offline tests; its full live setup/restore cycle is pending.

## Offline checks

```sh
python3 -m unittest discover -s tests -v
```

The suite runs without a car, network or real ADB. Its stateful simulator fails
on unrecognized commands, records writes and supports failures before/after an
uncertain mutation. Clocks are simulated for bounded health/reboot tests.

| Area | Behaviors checked |
| --- | --- |
| Compatibility | Every firmware property, display/override, user/boot, factory base, active APK/UID/version/system flag/default Home, root, receiver identity |
| Transport | USB descriptor required, unauthorized/offline/network/emulator rejected, explicit target and ADB server port, host-mode refusal |
| Artifacts | Download bounds/checksum/cache, BSDIFF40 decompression/instructions/offsets/corruption, both launcher pins and factory pull |
| Stages | Original backup and incomplete journal before first write, failed activity despite exit 0, live foreground/process requirements, fresh crash/ANR, PID restart, history/unrelated events ignored |
| Permissions | Distinct pause/exit 3 before later stages, same backup and owned receiver retained across resume |
| Automatic recovery | Launcher crash rollback through the same full restore engine, failed-stage reporting, no rollback writes on identity change, deferred recovery after real simulated transport loss |
| Partial restore | Disabled exact receiver, unknown receiver kept, lost root, malformed preferences, independent eligible reversals, receiver retained when Home fails, retry without repeated launcher removal |
| Ownership | Preexisting apps/settings kept, legacy AA journals/upgrade, absent fullscreen default behavior, setup/restore no-ops, corrupt journal/identity/lock refusals |
| Reboot | New boot identity required, persisted state/UI checks, stalled boot failure/recovery, completed check does not reboot again |
| Host preparation | Existing tools, private complete SDK extraction, traversal/link rejection, failed executable validation |

CI runs Python 3.10/3.13 on Linux, Windows and macOS. Python 3.13 jobs also fetch
Google's real host tools and run only `adb version`; that smoke check does not
start a server or access a car. A source-ZIP check verifies the ordinary download
contains all code, docs and the patch without requiring Git metadata.

## Completed component tests on the car

The first launcher passed install/card/Home/native-control checks, factory
rollback/reinstall, a normal Android reboot and wired AA/Home. The exact final
menu-cleanup build passed install/hash/UID/HOME read-back, before/after-reboot icon
checks, large-card/Home and owner native-control checks. The owner reports wired
AA working on the recording USB port; the ordinary port remains unstable.
Microphone recognition is unresolved. Final phone feedback did not separately
list every sound/touch/popup check. [Full evidence](verified-findings.md).

Patch reconstruction was also compared byte for byte with the exact final APK.
That is an offline artifact check, not a new installation on the car.

## Controlled v0.3 car cycle still needed

Use only the exact supported firmware, while parked, with power and the private
backup preserved. Keep the laptop in Device mode until its stages finish. Do not
induce a firmware/boot failure merely to prove a recovery claim.

1. Record read-only compatibility, original settings/apps and current ownership.
   Qualify access back to Device mode before claiming any Host-mode rescue route.
2. Run setup with `--reboot-check`. Confirm each stage's read-back and the actual
   Android 9 health/permission observations. Record unexpected onboarding screens;
   never silently bypass them or relabel an unrecognized screen as a crash.
3. Complete visible permissions and resume the same command if paused. Check
   the large card, Home, icon cleanup and usual native controls. Confirm reboot
   state and health before laptop disconnection.
4. Repeat completed setup: no device writes or changes to the original snapshot.
5. Disconnect laptop, select Host, connect phone directly to the recording USB
   port. Record real Maps, sound, touch, reconnect, card/Home and native-control
   outcomes separately. Record unresolved microphone behavior honestly.
6. Disconnect phone, select Device, reconnect laptop and run unified restore.
   Confirm owned launcher returns to the exact factory base with data retained,
   owned CarAuto/fullscreen restored, and only an owned new receiver removed.
   Preexisting installs must remain. Repeat restore: no additional writes.
7. On a suitable controlled unit, qualify recoverable app failures and cable-loss
   resume without risking access to the factory menu. Confirm partial results
   never claim full success and the journal survives. Stop if USB/Android becomes
   inaccessible; this project has no qualified boot/firmware rescue.
8. Record a cold ignition/power-off cycle separately if later tested. Do not infer
   it from normal Android reboot success or conflate it with wireless qualification.

Report CLI read-back versus what was seen/heard and the exact command/version.
Do not publish APKs, serials, network settings or raw private backups.
