# CarLink: primary CarPlay and Android Auto setup

The owner selected CarLink 1.0.7 after testing both Android Auto and CarPlay,
then confirming both fill the 1920 × 720 display. The primary receiver is the
already approved local permission-coexistence variant. OpenHU is absent from
active packages; its verified APK backup and retained data remain for recovery.
CarAuto stays disabled. [App artifact and trial evidence](carlink-trial.md).
[Current reference screenshots](screenshots.md).

## Migrate the existing working setup

This is a migration of the recorded, working CarLink trial on the exact F202
firmware. It is not a fresh-firmware compatibility bypass. Keep the same USB
target, ADB server and original state directory; do not create another baseline.

When starting from the exact previous qualified OpenHU setup, use a new state
directory for the trial and retain it through the remaining stages:

```sh
python3 oshan_x7.py carlink-check --state-dir /path/to/new-carlink-state --json
python3 oshan_x7.py carlink-trial --remove-openhu --reboot-check --state-dir /path/to/new-carlink-state --json
```

Complete visible CarLink onboarding and test the phone. Regain Device mode and
reconnect the laptop before the next stage:

```sh
python3 oshan_x7.py carlink-fullscreen --state-dir /path/to/new-carlink-state --json
```

Confirm both projection modes at the new width before promotion. For an already
working trial, use its existing state directory directly:

```sh
python3 oshan_x7.py carlink-check --state-dir /path/to/original-carlink-state --json
python3 oshan_x7.py carlink-promote --reboot-check --state-dir /path/to/original-carlink-state --json
```

Retain the actual `--adb`, `--adb-port` and `--serial` options from that trial.
Keep the laptop connected in **Device模式** throughout. Already authorized USB
debugging needs no repeated onboarding; use the documented [car menu](car-menu.md)
if returning from the phone's Host mode.

Promotion requires the exact enabled CarLink APK, its fullscreen value `0`,
the journal-owned OpenHU removal, and the exact previously qualified OpenHU
launcher. It copies and verifies the prior active launcher and immutable factory
APK, reconstructs the pinned new launcher, journals the write, and installs it
through ordinary Android package management with the matching signing identity.
The factory system APK and launcher data remain. No firmware partitions, default
Home assignment, other app layouts or vehicle control behavior are changed.

The large card now reads **CarLink / CarPlay + Android Auto**, with a screen/phone
icon and **Tap to open CarLink**. Its explicit target is
`com.carlink.app/com.carlink.app.ui.HomeActivity`. Existing navigation shortcuts
target the same app. The small duplicate CarLink tile, retired OpenHU/CarAuto
rows and launcher/test-launcher entries are filtered while other menu entries
retain their behavior. This does not repair microphone routing.

The new build is accepted only by the CarLink journal's owned migration.
Historical OpenHU `setup`/`restore` does not accept or overwrite it. Use the
CarLink commands with the original state directory from now on.

## Pinned launcher

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| CarLink launcher APK | 8,274,207 | `ffc81db01bb7d1645b6a9efd9d23960cafd6b671ba51b88d3816794597b30285` |
| Factory-to-CarLink BSDIFF | 4,670,690 | `44399ba3e6aecf8c8d37fd3ddf494c7253b8e314ff6b222835303c5a85b2f7b7` |

The [pin file](../profiles/f202-carlink-launcher.json) separately identifies the
factory base and matching factory signing certificate. Only the binary/source
patches are distributed, never full APKs or private signing inputs.
[Readable source changes](../patches/launcher-carlink-source.patch).

Offline comparison covered 8,280 compiled classes and 60,238 methods. Changes
were limited to the explicit CarLink launch/navigation references, retired/menu
filtering, card strings and icon. The manifest and all other resource/assets
payloads were unchanged. Factory media and vehicle control methods were
unchanged. Signature schemes v1/v2/v3 and ZIP alignment verified. Reconstructing
the binary patch produced the exact signed output bytes.

The live migration installed that exact build and verified its active hash,
factory system/shared UID, default Home and UI health. A normal Android reboot
returned over USB with the new launcher, CarLink enabled, OpenHU absent and
CarLink's fullscreen value still `0`. A post-reboot screenshot showed the new
large card and the existing Music, Radio, Bluetooth phone and recorder cards.
The owner then confirmed that tapping the large card opens CarLink and the
factory Home button returns correctly. Both connected projection modes had
already been confirmed fullscreen. Other native controls and individual audio,
microphone or reconnect checks were not enumerated in this migration test.

## Recovery

Keep the original journal and backups. Reconnect the laptop in **Device模式**:

```sh
python3 oshan_x7.py carlink-restore --state-dir /path/to/original-carlink-state --json
```

This reinstalls the exact previous OpenHU launcher from its verified local
backup, returns CarLink's owned layout preference, reinstalls the saved OpenHU
APK, checks Home/OpenHU, and only then removes the owned CarLink app. It never
uninstalls the launcher for user 0. Unknown firmware or an unknown replacement
launcher blocks writes; an interrupted operation uses read-back and the same
journal. A lost USB connection requires this recovery command, not raw installs.

Recovery still requires responsive Android, package management and authorized
USB. Switching back from Host with a broken launcher is unqualified. Normal
Android reboot checks are separate from cold ignition cycles. Owner-observed
AA/CarPlay projection does not establish all audio, microphone, reconnect or
vehicle control behavior.

## Reference screenshots across the shared USB port

Direct captures work while the laptop is connected in Device mode. For a phone
session that needs Host mode, `carlink-reference-start` starts a bounded script
that saves six frames 15 seconds apart under a unique owned `/data/local/tmp`
directory. It does not change app, USB-role, root or network settings. Disconnect
the laptop, select Host, show a phone screen without personal details, and after
the capture window regain Device and reconnect. Use `carlink-reference-collect`
with the same state directory; it verifies the original capture identity,
pulls complete 1920 × 720 PNGs, then removes only its exact finished temporary
files. Review local private images before copying any to public documentation.
