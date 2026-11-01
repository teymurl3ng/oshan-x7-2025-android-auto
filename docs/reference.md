# Commands and compatibility

| Command | Purpose |
| --- | --- |
| `python3 prepare.py --json` | Find or download local ADB tools; no car access |
| `python3 oshan_x7.py check --json` | Check setup compatibility without car writes |
| `python3 oshan_x7.py setup --reboot-check --json` | Install/configure CarLink and launcher, then verify an Android reboot |
| `python3 oshan_x7.py status --json` | Read current state and installation/recovery records |
| `python3 oshan_x7.py restore --json` | Undo recorded changes from this installation |

On Windows use `py -3` or the verified interpreter path. Keep the same interpreter,
ADB path, server port, USB target and state directory throughout setup and recovery.

| Option | Purpose |
| --- | --- |
| `--adb /path/to/adb` | Use the executable returned by `prepare.py` |
| `--adb-port PORT` | Use your existing local ADB server port; default 5037 |
| `--serial YOUR_CAR_USB_SERIAL` | Select the car when multiple USB devices are connected |
| `--state-dir /path/to/backup` | Select the private backup folder; default `.oshan-x7` beside the script |
| `setup --apk /path/to/CarLink-1.0.7.apk` | Use a downloaded APK; the same size/hash checks apply |
| `setup --reboot-check` | Verify an Android reboot; do not repeat a completed check |
| `--json` | Emit one JSON object on stdout |
| `--version` | Print the installer version |

## Exact compatibility

| Check | Supported value |
| --- | --- |
| Head unit | `F202_MCA`, `alps`, MediaTek `mt6771` |
| Android | 9 / API 28 |
| Firmware | `F202RHD_D1_20241022162756` |
| MCU | `F202RHD_20240722_1` |
| Screen | 1920 × 720, no resolution override |
| Factory launcher | Exact original APK hash |
| Active launcher | Factory or tested CarLink update; system/shared UID 1000, version 20240726, original default Home |
| Access | Existing factory root (`su 0`), authorized USB in Device mode, current user 0, completed boot |
| Apps | Required factory apps present; CarLink absent or the exact enabled official release |

[Full profile](../profiles/f202-carlink.json). Badge/year does not determine
compatibility. Unknown app versions, launcher replacements, competing enabled
projection apps or a conflicting permission owner stop setup.

## Results and exit codes

| Exit | Meaning |
| --- | --- |
| 0 | Command completed; inspect the result fields for its meaning |
| 2 | Refusal or failure; may include automatic/partial recovery |
| 3 | Unexpected visible permission screen; inspect it before responding/resuming |
| 130 | Interruption outside the staged failure handler; inspect status |

`setup_compatible` describes whether installation checks pass.
`recovery_eligible` only establishes the mandatory recovery identity checks.
`configured` in check/status means the current installation settings match; it
does not measure live projection. `android_reboot_verified` is saved evidence
of the installation's Android reboot, not proof of cold-ignition behavior.
`projection_tested=false` means real phone testing is still separate.

| `next_action` | Meaning |
| --- | --- |
| `phone_handoff` | Laptop setup/reboot checks passed; perform the card/Home checks, then connect the phone |
| `rerun_setup_with_reboot_check` | Keep Device mode and run setup with reboot verification |
| `inspect_permission_prompt` | Inspect the unexpected screen and diagnose missing access |
| `inspect_configuration_drift` | Current settings differ from a saved completed setup |
| `diagnose_identity_mismatch_no_writes` | Investigate the mismatch; do not bypass checks |
| `inspect_component_issues_and_restore_if_needed` | Inspect reported app/root/settings problems before choosing recovery |
| `restore` or a reconnect/restore action | Use the original state after resolving the reported problem |
| `restore_complete` | Recorded changes were reversed |

Failures may contain `failed_stage`, nested `recovery`, `component_issues` and
`recovery_errors`. `restored` is successful recovery, not successful installation.
See [recovery](recovery.md). Older records can return legacy result fields; their
recovery support is retained without making them part of new installation.

## Artifact pins

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| Official CarLink 1.0.7 | 16,747,592 | `16e8b98436a5c5f355aa4b49086e28d41bee9f9f874174658cafb682fd503e77` |
| Factory launcher base | 8,256,512 | `0c50bad53fa2116e98928c74be78e1b9609a1d3f73d3ee42726b001ae7ddefb0` |
| CarLink launcher update | 8,274,207 | `ffc81db01bb7d1645b6a9efd9d23960cafd6b671ba51b88d3816794597b30285` |
| Factory-to-CarLink BSDIFF | 4,670,690 | `44399ba3e6aecf8c8d37fd3ddf494c7253b8e314ff6b222835303c5a85b2f7b7` |

CarLink comes from the [official v1.0.7 release](https://github.com/F-e-n-y-x/CarLink/releases/tag/v1.0.7).
Its certificate SHA-256 is
`037468ca5beb70ea5f68543329b03368247dfb393d3f626a6b472d10e5657d21`.
The installer requires the exact APK hash, which includes its signature. Later
releases need separate testing and profile changes. The launcher is reconstructed
from the checked factory APK; full APKs and signing inputs are not distributed.
[Launcher source/build details](launcher.md).

## Maintainer capture tools

`carlink-reference-start`, `carlink-reference-collect` and
`carlink-reference-pages` are existing-journal capture helpers, not installation
commands. They require a ready legacy CarLink trial journal and are not a general
capture API for fresh installations. Timed capture saves six private frames over
90 seconds while the phone uses the shared port. Collection verifies identity
and removes only its finished temporary files. Review images before publishing.
