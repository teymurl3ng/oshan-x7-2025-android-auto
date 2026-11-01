# CarLink setup

The public path installs official CarLink directly on the exact supported
factory firmware. No other receiver is an installation prerequisite.
[Car menu and USB roles](car-menu.md) · [Laptop preparation](agent-setup.md).

## Run setup

With the laptop authorized over USB in **Device模式**:

```sh
python3 prepare.py --json
python3 oshan_x7.py check --json
python3 oshan_x7.py setup --reboot-check --json
```

Use the same interpreter, ADB executable/server port, USB target and state
directory for subsequent commands. Windows uses `py -3`. Unknown firmware,
launcher builds or app replacements stop setup; there is no force flag.

Setup verifies the official APK and launcher patch before writes, saves the
original settings and factory launcher, installs CarLink if absent, applies
its permissions automatically, checks UI health, disables CarAuto, sets
CarLink's factory fullscreen value to `0`, installs the pinned launcher update,
and verifies the configured state through a normal Android reboot. Every
mutation is recorded before execution and checked afterwards.

CarLink's runtime and special permissions, battery exemption and its own
USB auto-confirm accessibility service are included automatically. Other
accessibility services remain enabled. One car-side prompt still needed tapping
in the owner's later phone test; full USB prompt automation is unresolved.
[Grant scope and recovery](permissions.md).

The factory Home card reads **CarLink / CarPlay + Android Auto** and targets
`com.carlink.app/com.carlink.app.ui.HomeActivity`. Factory Home/Back overlays,
media and vehicle controls remain. Duplicate receiver/launcher menu entries
are filtered. The tool does not root or flash the car, edit firmware partitions,
enable network ADB or install Google services.

Complete car/profile onboarding if shown. Once the reboot check passes,
disconnect the laptop, select **Host模式** and connect a phone with a data cable.
Check actual AA/CarPlay, fullscreen, touch, sound, the large card, Home and native
controls. Machine foreground checks do not establish these phone behaviors.

## Artifact pins

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Official CarLink 1.0.7 | 16,747,592 | `16e8b98436a5c5f355aa4b49086e28d41bee9f9f874174658cafb682fd503e77` |
| Factory launcher base | 8,256,512 | `0c50bad53fa2116e98928c74be78e1b9609a1d3f73d3ee42726b001ae7ddefb0` |
| CarLink launcher update | 8,274,207 | `ffc81db01bb7d1645b6a9efd9d23960cafd6b671ba51b88d3816794597b30285` |
| Factory-to-CarLink BSDIFF | 4,670,690 | `44399ba3e6aecf8c8d37fd3ddf494c7253b8e314ff6b222835303c5a85b2f7b7` |

The app comes unchanged from the [official v1.0.7 release](https://github.com/F-e-n-y-x/CarLink/releases/tag/v1.0.7).
Its signing certificate SHA-256 is
`037468ca5beb70ea5f68543329b03368247dfb393d3f626a6b472d10e5657d21`.
The installer accepts only the exact pinned APK; official later updates still
require qualification and new pins before this installer will adopt them.

The launcher is reconstructed locally from the verified factory APK. Only
binary/source deltas are distributed; full APKs and signing inputs stay private.
[Setup profile](../profiles/f202-carlink.json) ·
[Launcher pins](../profiles/f202-carlink-launcher.json) ·
[Source changes](../patches/launcher-carlink-source.patch).

## Recovery

```sh
python3 oshan_x7.py status --json
python3 oshan_x7.py restore --json
```

Reuse the original state directory and connection options. Recovery rolls back
its owned launcher update, layout, permissions and CarAuto state, then removes
CarLink only if this cycle installed it. Preexisting apps are retained.
Older journals are dispatched to their matching recovery engine automatically;
a new public setup never installs an older receiver to reach CarLink.
[Recovery details](recovery.md).

The direct-from-factory sequence is offline-tested. Component installation,
fullscreen, launcher/card/Home and normal Android reboot have live evidence;
a complete fresh setup/restore cycle remains pending. [Evidence](verified-findings.md).
