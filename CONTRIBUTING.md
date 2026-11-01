# Contributing

This project targets the exact head unit and firmware listed in the
[compatibility reference](docs/reference.md#exact-compatibility). If you have a
problem, include the installer version (`python3 oshan_x7.py --version`), command,
error message, firmware/MCU versions and whether setup had started changing the
car. Keep your backup. Redact serials, IP/MAC addresses, Wi-Fi names, account data
and private paths; do not attach raw dumps or backups.

## Changes and tests

Run `python3 -m unittest discover -s tests -v` for code changes. Cover meaningful
failure paths as well as successful setup, including uncertain writes, missing
USB, unexpected screens, lost root and partial recovery. Keep automatic failure
recovery and explicit restore on the same engine.

Preserve original journals and compatibility with older backups. An app or
launcher update already present before setup must never be claimed or removed
by a new installation. Keep legacy profiles/patches needed for recovery even
though they are not part of the current installation procedure.

Do not weaken identity checks to accept a different unit. Supporting another
firmware requires exact device properties, firmware/MCU identifiers, factory
package identities/hashes, existing root behavior and fullscreen semantics,
followed by actual projection, repeated setup, reboot, restore and factory-control
tests. Model/year or an AI prediction is insufficient.

## Launcher and published material

Read [launcher.md](docs/launcher.md) before launcher changes. Distribute only
verified deltas against the matching factory APK; keep full APKs and signing keys
private. Inspect and test a new build before changing its pins. Preserve the
factory-base checks and safe system-update rollback.

Write instructions directly to the reader. Use first person for my recorded
car tests and distinguish them from machine checks. Keep results in
[verified-findings.md](docs/verified-findings.md), with future checks in
[testing.md](docs/testing.md). Do not repeat development history in installation
steps or turn an offline test into a live-test claim.

Review screenshots for phone/account/location details. Publish selected frames
with accurate captions and provenance; keep raw capture records private.
Do not submit proprietary APKs, credentials or broad debloat lists. Installer
code/docs use MIT; retain the [upstream credits and licenses](THIRD_PARTY_NOTICES.md).
