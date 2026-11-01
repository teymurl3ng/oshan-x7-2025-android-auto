# Factory Home card for CarLink

Setup installs the exact pinned launcher as a signed system-app update under
`/data/app`. The immutable factory APK remains on the system partition. The
large card opens `com.carlink.app/com.carlink.app.ui.HomeActivity` and reads
**CarLink / CarPlay + Android Auto**. Existing navigation shortcuts target the
same app. Duplicate receiver/launcher menu entries are filtered.

The original Home/Back overlays, media and vehicle control methods remain.
The Bluetooth card retains its original size. The update does not repair
microphone routing or certify all vehicle functions.

![CarLink Home card](images/launcher-carlink.png)

## Exact build

The update SHA-256 is
`ffc81db01bb7d1645b6a9efd9d23960cafd6b671ba51b88d3816794597b30285`;
its size is 8,274,207 bytes. [Artifact pins](carlink-setup.md#artifact-pins).
Only the [factory-to-CarLink binary delta](../patches/f202-launcher-carlink.bsdiff)
and [readable source delta](../patches/launcher-carlink-source.patch) are shipped.
The factory base, output hash, system/shared UID 1000, version 20240726 and default
Home must match. Full APKs and signing inputs are private.

Offline comparison covered 8,280 compiled classes and 60,238 methods. Changes
were limited to CarLink launch/navigation references, app-menu filtering, labels
and icon. The manifest and other resource/asset payloads were unchanged. Factory
media and vehicle control methods were unchanged. Signature schemes v1/v2/v3,
ZIP alignment and exact binary reconstruction were verified.

The installed build, UID, Home and fullscreen value survived a normal Android
reboot. The owner confirmed that the large card opens CarLink and factory Home
returns correctly. Actual AA and CarPlay were confirmed fullscreen. These checks
do not establish microphone, all audio paths, cold ignition or wireless reliability.

Setup journals the update before installation and checks Home/SystemUI health.
Recovery removes only an exact update owned by that cycle, preserving launcher
data and any update already present before setup. Never remove or disable Home
for a single user. [Recovery](recovery.md).
