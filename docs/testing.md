# Testing and qualification

```sh
python3 -m unittest discover -s tests -v
```

Tests run offline with simulated ADB, network and clocks. Unrecognized device
commands fail the simulator. Software tests are separate from actual car results.

| Area | Checked behavior |
| --- | --- |
| Public setup | Factory → official CarLink directly, launcher/fullscreen/CarAuto setup, normal reboot and repeated no-op |
| Automatic permissions | Grants before first app launch, special access and battery exemption, enabled/bound USB service, other services preserved |
| Permission recovery | Original grants retained, owned grants reversed, later unrelated services kept, failed grants cannot claim success |
| Recovery | Same automatic/manual engine, original snapshots, partial failures, uncertain writes, unknown replacements retained, repeat restore no-op |
| Identity | Exact firmware/factory/active APKs, UID/version/default Home, root, user and USB mode |
| Transport | Unauthorized/offline/network/emulator rejection, explicit USB serial and local server port |
| Health | Actual foreground/process samples, fresh crash/ANR versus historical logs, permission pause and bounded observation |
| Artifacts | Pinned official download/checksum/size, launcher delta reconstruction and changed/corrupt inputs |
| Compatibility | Original journal ownership and recovery continue without requiring an older setup for new users |

CI runs Python 3.10/3.13 on Linux, Windows and macOS. Host-tool smoke checks only
run `adb version`, without car access. Source exports must contain code, profiles,
docs and required patches without needing Git metadata.

## Live evidence

The owner confirmed AA and CarPlay fullscreen and the large CarLink card/Home
return. The exact launcher/fullscreen configuration passed normal Android reboot
checks. Official CarLink was installed and its saved settings restored, with
app/launcher/layout verified after reboot. Automatic runtime/special grants,
battery exemption and the exact USB service binding also passed a live Android
reboot check. [Evidence](verified-findings.md).

The owner reports iPhone cable and wireless CarPlay working perfectly, Android
wireless unreliable, and the regular charging/CarAuto port as the working phone
port. A car-side prompt still needed tapping after the grant/service setup; full
USB prompt automation is unresolved. The new
direct-from-factory public setup/restore sequence has not completed a full live
cycle; its individual app/launcher/layout components have live evidence.

## Next controlled car cycle

On only the exact supported firmware, preserve the original private state and
keep the parked car powered with the laptop in Device mode.

1. Record original compatibility/settings and ownership; run setup with reboot
   verification. Confirm grants, bound USB service and app/Home/SystemUI health.
2. Repeat setup and verify no writes or changed original snapshot.
3. Disconnect laptop, select Host and attach actual phones. Observe USB dialogs,
   both projections, fullscreen, touch, sound, large card/Home and native controls.
4. Record reconnects and microphone results separately.
5. Regain Device mode and restore using the original journal. Check factory
   launcher, owned settings/permissions/CarAuto and preexisting app preservation.
6. Repeat restore without writes. Qualify recoverable interruptions only when
   Device access remains available; do not deliberately risk firmware/boot access.
7. Record cold ignition separately if later tested. Do not infer wireless or
   ignition reliability from a normal Android reboot.

Do not publish raw dumps, APKs, phone data, device identifiers or private backups.
