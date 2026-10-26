# Android Auto on the factory launcher

The Home screen update replaces the large **Connection / CarAuto** card with
**Android Auto / Open Headunit**. Tapping it opens the pinned receiver directly.
It hides the redundant small OpenHU tile and launcher/test-launcher app-menu
entries, including saved rows. Music, Radio, Bluetooth phone, the app-menu
vehicle entries and the factory Home/Back overlays remain available.

[Before and after, captured on the car](../README.md#android-auto-on-the-factory-home-screen).
The Bluetooth card keeps its original size and position.

## How setup installs it

Run the usual `python3 oshan_x7.py setup`; there is no extra launcher command.
The same applies when following the agent workflow.

1. Read the exact firmware, MCU, hardware, physical display, Android user and
   boot state. Stop on a mismatch before root/private-preference access.
2. Require the immutable factory APK's exact hash, the active launcher's
   system/shared UID 1000, version 20240726 and original default HOME. Accept
   only the original APK or this exact tested update. Required factory packages
   and any existing OpenHU installation must still match the profile.
3. In USB Device mode, pull the original APK to private local backup storage.
   Check its size/hash again locally. Apply the bundled binary patch and require
   the exact tested output size/hash before any device write.
4. Save original AA settings, receiver and launcher ownership in the durable
   journal. Install the receiver if absent, disable only CarAuto and save its
   factory fullscreen setting. Recheck compatibility before the launcher write.
5. Install the launcher through normal Android package management as an update
   of the factory app. Android enforces the existing signing identity. Read back
   its exact APK hash, UID, version, update flag and default HOME. Open the Home
   activity, then OpenHU for visible onboarding and permissions.

The system-partition factory APK is retained. Firmware partitions, Google
services and the USB role are not changed. Within the launcher, retired CarAuto
shortcuts and its voice app targets are removed or redirected to OpenHU. There
is no microphone-routing repair. Setup does not reboot the unit or complete
Android Auto permissions for the owner.

## Exact artifacts

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Factory launcher | 8,256,512 | `0c50bad53fa2116e98928c74be78e1b9609a1d3f73d3ee42726b001ae7ddefb0` |
| Tested OpenHU launcher | 8,274,207 | `03ef3a861c43124f184f0d675400f9a6022b0100f1a96e3e498dc096041f66b8` |
| Bundled binary patch | 4,659,638 | `407e6292825edfb6dd55f7aae1109fd6e98771bc2b27c8bcd8184aabb789ed57` |

Package: `com.chinatsp.launcher`; HOME: `com.chinatsp.launcher/.MainAct`.
The factory certificate's SHA-256 is
`c8a2e9bccf597c2fb6dc66bee293fc13f2fc47ec77bc6b2b0d52c11f51192ab8`.
The tested update verifies with v1/v2/v3 signatures and four-byte alignment.
The firmware profile pins the complete output APK, not just its package/version.

The repo contains a [BSDIFF40 patch](../patches/f202-launcher-openhu.bsdiff), not
a full factory or modified APK. [`launcher_patch.py`](../launcher_patch.py) applies
the [bsdiff format](https://www.daemonology.net/bsdiff/) with bounded standard-library
decompression. No Java, apktool, signing key, pip package or bsdiff executable is
needed on the owner's laptop. The original APK must come from the matching car;
another firmware cannot be used to generate a replacement.

The reviewed changes are also provided as sequential readable patches:
[factory to the first OpenHU launcher](../patches/launcher-openhu-source.patch),
then [menu cleanup](../patches/launcher-menu-cleanup-source.patch). These describe
the changes; normal setup uses the pinned binary patch to produce the exact
car-tested APK, without recompilation differences.

## Restore and interrupted operations

Reconnect the laptop in Device mode and use `python3 oshan_x7.py restore` with
the original state directory. Keep the journal and local APK backups.

If this setup installed the update over the factory base, restore first removes
only that exact updated system APK. The tested command uses `pm uninstall -k`
**without `--user`**, so Android restores the immutable factory app and retains
launcher data. It is not the user-scoped removal used for the ordinary receiver
app. Unknown firmware, base APK, active hash or UID prevents removal.

A launcher already present before this setup is retained. An installation that
lost its USB connection is not blindly repeated: the pending journal requires
restore, which checks whether the factory or exact update is active. An
interrupted rollback can likewise be resumed. Restore does not depend on the
patch or generated update still being available; it uses the verified factory
base already on the car. AA settings and receiver ownership are then restored.

Legacy v0.1 backups retain their original AA-only restore scope. A completed
legacy setup can be extended by v0.2 while preserving its original AA baseline.
An exact launcher already installed at upgrade time is treated as preexisting.

## What has been tested

On the matching car, the earlier signed launcher passed installation, large-card
launch, Home return, owner checks of usual native controls, factory rollback and
reinstallation, a normal Android reboot, and a subsequent wired AA/Home test.
The final menu-cleanup APK pinned above was then installed and read back. Its
duplicate icons stayed absent after a normal Android reboot; large-card launch
and Home return were observed again. The owner confirmed the controls they
tried worked and AA worked on the video-recording USB port.

The ordinary USB port still failed after about 10–15 seconds. The latest phone
answer did not individually enumerate audio, touch or popup checks. Neither a
cold ignition power cycle nor wireless AA was tested, and vehicle controls were
not exhaustively audited. Microphone/Gemini recognition remains unresolved.

**The combined v0.2 public installer has offline compatibility, ownership,
artifact and interruption/recovery tests, but its full setup/restore cycle has
not yet been run on the car.** Its reconstructed APK is byte-for-byte identical
to the tested final build. Those are separate claims.

The owner's separate OpenHU “Show toast messages” preference was turned off and
a reconnection was confirmed without the large routine popup. The public CLI
leaves that preference alone; it can be changed during visible OpenHU setup.

## Maintainer reproduction

Keep both qualified APKs private. To reproduce the exact bundled patch, install
`bsdiff` through a trusted OS package manager and run:

```sh
python3 tools/make_launcher_patch.py --factory /path/to/original.apk \
  --modified /path/to/tested-update.apk --output /path/to/new-patch.bsdiff
```

The helper accepts only the pinned input and output APKs and checks the generated
patch against its pin. It refuses to overwrite an existing output. Changing a
launcher build requires new offline inspection and actual car qualification;
do not edit the profile just to pass a mismatch. Full APKs, signing keys,
serials, addresses and private journals must not be committed.
