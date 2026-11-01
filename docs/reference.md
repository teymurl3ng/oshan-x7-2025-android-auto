# Commands and compatibility

| Command | Behavior |
| --- | --- |
| `python3 prepare.py --json` | Find or prepare local ADB tools |
| `python3 oshan_x7.py check --json` | Read-only setup compatibility |
| `python3 oshan_x7.py setup --reboot-check --json` | Install official CarLink, automatically configure permissions, fullscreen and launcher, then verify a normal Android reboot |
| `python3 oshan_x7.py status --json` | Read-only state and journal/recovery status |
| `python3 oshan_x7.py restore --json` | Reverse this cycle's owned changes from its original journal |

Windows uses `py -3`. Keep one interpreter, ADB executable, server port, USB
target and state directory throughout setup and recovery.

| Option | Purpose |
| --- | --- |
| `--adb /path/to/adb` | Select the verified ADB executable |
| `--adb-port 5038` | Reuse a local server port other than 5037 |
| `--serial YOUR_CAR_USB_SERIAL` | Select a car when multiple USB devices exist |
| `--state-dir /path/to/backup` | Reuse this private backup for the entire cycle |
| `setup --apk /path/to/CarLink-1.0.7.apk` | Use a local copy; the same official size/hash is required |
| `setup --reboot-check` | Verify an Android reboot before phone handoff; completed checks are not repeated |
| `--json` | One stdout JSON object; 0=success, 2=refusal/error, 3=unexpected visible permission pending, 130=interruption |

## Exact compatibility

| Check | Supported value |
| --- | --- |
| Headunit | `F202_MCA`, `alps`, MediaTek `mt6771` |
| Android | 9 / API 28 |
| Firmware | `F202RHD_D1_20241022162756` |
| MCU | `F202RHD_20240722_1` |
| Screen | 1920 × 720, no override |
| Factory launcher | Exact immutable APK hash |
| Active launcher | Exact factory or pinned CarLink update; system/shared UID 1000, version 20240726, original default Home |
| Access | Existing `su 0`, authorized USB in Device mode, user 0, completed boot |
| Apps | Required factory packages present; CarLink absent or exact pinned official release |

[Full profile](../profiles/f202-carlink.json). Unknown app versions, launcher
replacements, competing enabled receivers or a conflicting permission owner
stop setup. The tool does not overwrite them or weaken compatibility checks.

## Results

`check` requires setup compatibility. `status` also exposes recovery-eligible
states; `recovery_eligible=true` alone is not permission to run setup.
`projection_tested=false` means machine checks cannot prove real projection,
audio, touch or native controls. Owner observations are recorded separately.

A failure may include `failed_stage`, nested `recovery`, `component_issues`,
`recovery_errors` and `next_action`. Preserve the original journal, resolve the
reported issue and use `restore` after an interrupted setup. `restored` means
owned changes were reversed; `recovery_required` means work remains.

## Connection help

Use Device mode for the laptop and Host mode for the phone. The reference
regular charging/CarAuto USB port is the current working phone port. Diagnose data
cable, USB authorization and host driver/group permissions before car changes.
Do not kill another ADB server or enable network ADB to work around missing USB.
[USB checks](usb-reliability.md) · [Car menu](car-menu.md).

The capture helpers `carlink-reference-start`, `carlink-reference-collect` and
`carlink-reference-pages` are maintainer tools, separate from installation.
Timed capture saves six private 1920 × 720 frames over 90 seconds while the
shared port is used by the phone. Collection checks the recorded identity and
removes only its finished owned temporary files. Review captures before publishing.
