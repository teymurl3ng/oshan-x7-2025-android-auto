# Testing

Run the offline suite after code changes:

```sh
python3 -m unittest discover -s tests -v
```

It uses simulated ADB, network and clocks; unrecognized device commands fail the
simulator. Passing tests do not establish new results on the car.

| Area | Coverage |
| --- | --- |
| Installation | Factory-to-CarLink setup, permissions before opening the app, fullscreen, launcher and Android reboot |
| Current status | Configuration changes suppress phone-connection advice; status remains read-only |
| Permissions | Grant/app-op/battery/service read-back, silent command failures, other services preserved, absent-app recovery |
| Reboot | New boot identity, saved request/observation, permission-pause resumption without another reboot |
| Recovery | Shared automatic/manual engine, original records, partial failures, uncertain writes, unknown replacements retained, repeated restore |
| Compatibility | Exact firmware, APKs, launcher UID/version/Home, root, user and USB mode; legacy recovery records |
| Transport and health | Unauthorized/offline/network/emulator rejection, local server/serial selection, foreground/process checks and fresh crash/ANR detection |
| Artifacts | Downloads, hashes/sizes, bounded patch reconstruction and current/legacy patch-tool selection |

CI runs Python 3.10/3.13 on Linux, Windows and macOS. The separate
`tests/smoke_prepare.py` downloads actual host tools and runs `adb version` without
car access. A source ZIP must include code, profiles, docs and required patches;
installation must not depend on Git metadata.

Historical live observations are kept in [the test record](verified-findings.md).
The complete fresh install/restore cycle still needs a live test.

## Next controlled car test

Use only the exact supported firmware. Preserve existing private state and keep
the parked car powered. Do not create a new baseline over an unfinished cycle.

1. Record original compatibility, settings and existing apps/launcher. Keep the
   laptop in Device mode; run setup with reboot verification.
2. Check grants, bound USB service, Home/SystemUI/CarLink health. Repeat setup and
   verify it makes no changes and retains the original backup.
3. Complete available onboarding and check the large card/Home. Disconnect the
   laptop, select Host mode and attach phones. Record actual USB dialogs,
   projection, fullscreen, touch, sound and native controls.
4. Record microphone behavior and repeated reconnects separately.
5. Disconnect the phone, select Device mode and reconnect the laptop. Restore
   with the original journal. Check launcher, settings, permissions, CarAuto and
   preservation of preexisting apps. Repeat restore and verify no changes.
6. Test recoverable interruptions only while Device access remains available;
   do not deliberately risk boot or firmware access.
7. Record cold ignition separately; it is not an Android reboot check.

Keep raw dumps, APKs, phone data, identifiers and private backups unpublished.
