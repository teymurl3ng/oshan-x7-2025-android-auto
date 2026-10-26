# Commands and reference

I kept these details out of the [main setup instructions](../README.md) so they
don't get in the way of getting started. Come here if you need to check your
firmware, sort out a connection problem, or restore your original settings.

## Compatibility

My car: **2025 Changan Oshan X7, right-hand drive**. Another X7 with the same year
could have different headunit software, so I don't use the badge/year as the
compatibility check. Here's what the script looks for:

| Check | Supported value |
| --- | --- |
| Headunit | `F202_MCA` |
| Manufacturer / platform | `alps` / MediaTek `mt6771` |
| Android | 9 / API 28 |
| Firmware | `F202RHD_D1_20241022162756` |
| MCU | `F202RHD_20240722_1` |
| Physical screen | 1920 × 720, no resolution override |
| Factory launcher base | Original system-partition APK, matching the verified SHA-256 |
| Active launcher | Exact factory APK or pinned OpenHU update; system/shared UID 1000, version 20240726, original default HOME |
| Access | Existing `su 0` root, Android user 0, boot completed |
| Factory apps | Required packages present and supporting system apps enabled |
| Existing receiver | Absent, or the exact enabled Open Headunit 3.5.0 release APK |

The remaining exact properties and checksums are in the
[firmware profile](../profiles/f202-mca-rhd-20241022.json). Unknown firmware or
incomplete checks stop setup. I haven't added a force flag. These checks reduce
the risk of applying my setup to a different unit, but they aren't a manufacturer
certification. I don't have a verified full SystemUI APK hash to pin. Don't add
a profile just by copying another car's model/year.

The tool uses root already present on the tested firmware. It does not root or
flash the car, edit firmware partitions, install Google services, or apply a
general debloat list. It installs the pinned launcher as an Android system-app
update under `/data/app/`; the original system-partition APK stays intact.
Only CarAuto is disabled; vehicle/camera/climate/SystemUI services are not disabled.

## Host tools and command options

```sh
python3 prepare.py --json
python3 oshan_x7.py check --json
python3 oshan_x7.py setup --reboot-check --json
python3 oshan_x7.py status --json
python3 oshan_x7.py restore --json
```

On Windows, substitute `py -3` for `python3`. `prepare.py --verify-only` checks
existing host tools without downloading. Normal preparation downloads ADB if
needed; Python installation is handled by the agent using the
[host setup workflow](agent-setup.md), or by the person in manual mode.

`check` and `status` are read-only on the car. `setup` installs the pinned receiver
if absent, disables `com.eryanet.vlink`, saves the receiver's fullscreen preference,
installs the tested launcher update, and verifies Home/receiver health between
stages. With `--reboot-check`, it verifies a normal Android reboot before the
phone handoff. `restore` uses the same recovery engine as a failed setup,
reversing changes owned by that cycle.

| Option | When to use it |
| --- | --- |
| `--adb /path/to/adb` | Use a specific verified ADB executable. Paths with spaces should be quoted. |
| `--adb-port 5038` | Your existing local ADB server uses 5038 rather than 5037. |
| `--serial YOUR_CAR_USB_SERIAL` | More than one USB device is attached. |
| `--state-dir .oshan-x7-next` | Keep a new setup cycle separate after a completed restore. Use the same value for its later restore. |
| `setup --apk /path/to/file.apk` | Use a previously downloaded official 3.5.0 APK. The fixed size/hash checks still apply. |
| `setup --reboot-check` | Verify a normal Android reboot, saved state and Home/receiver health before phone handoff. Repeating a completed check does not reboot again. |
| `--json` | One stdout JSON object; exit 0 = success, 2 = refusal/error, 3 = visible permission pending, 130 = interruption outside the staged handler. |

The CLI finds working ADB installations automatically. Preparation keeps newly
downloaded Platform Tools inside `.oshan-x7/tools/`, including supporting DLLs and
libraries. Existing SDK installations can be reused without modifying global PATH.

## Connection help

| Symptom | Next step |
| --- | --- |
| Python/ADB missing | Agent: follow [agent-setup.md](agent-setup.md) and install it. Manual: install Python, then run `prepare.py`. |
| No authorized USB device | Select **Device** mode, use a data cable, accept debugging authorization, and inspect `adb devices -l`. |
| Car listed on 5038 only | Add `--adb-port 5038` to check/setup/status/restore. The tool does not kill other servers. |
| Windows detects hardware but ADB sees nothing | Agent should inspect Device Manager and obtain an appropriate signed OEM driver if needed. No generic driver pack is verified here. |
| Linux USB permission error | Agent should inspect udev/group permissions and use the distribution's documented Android-device setup. |
| Compatibility mismatch | Stop; compare the reported fields with the profile. Do not force it. |
| Another Open Headunit version is installed | This release refuses to overwrite/downgrade it. Retain its data and resolve the version difference deliberately. |
| Phone charges but AA stays absent | Disconnect laptop, switch to **Host** mode, use a data cable, open Open Headunit and choose USB. |
| Repeating USB prompts/disconnections | Check that CarAuto is disabled, Host mode is selected, and Open Headunit has USB permission. |
| AA drops after 10–15 seconds on the ordinary port | The owner's video-recording USB port worked with the same cable. Try that port; the underlying cause is unresolved. |
| Gemini opens/listens but recognizes no words | This remains unresolved on the owner's car, including its native voice assistant. The launcher update does not repair microphone routing. |
| Unknown launcher path/hash, UID or default HOME | Stop. Keep the journal and inspect the reported build. The CLI accepts only the factory base and the exact qualified update. |
| Launcher patch missing or changed | Download a complete matching repo ZIP/checkout. Do not substitute another APK or bypass the output hash. |
| Preference is saved but bars remain | Reopen Open Headunit and inspect actual projection. Stored preference verification is not a visual test. |
| Download unavailable | Obtain the [exact official 3.5.0 APK](https://github.com/andreknieriem/open-headunit/releases/tag/v.3.5.0) and use `setup --apk ...`. |

I also changed automatic-start and wireless settings while troubleshooting, but
I didn't keep a complete record of their final phone values. The script leaves
those alone. Several things changed along the way, so I can't say which individual
change fixed each problem. I haven't retested wireless since disabling CarAuto.

The workflow never enables network ADB. If it was enabled in earlier independent
debugging, arrange USB access and return to USB-only debugging separately using
Android's official guidance. Running this tool does not clear that earlier state.

## Machine-readable results

`check` applies the strict setup checks. `status` uses recovery inspection and
can succeed while `setup_compatible=false`; **do not use that as permission to
run setup**. `recovery_eligible` means only the critical identity gates matched.
Each remaining component still needs its own checks before a write.
`compatible` on a recovery/status report refers to those recovery identity
gates, while `setup_compatible` refers to the full setup configuration.

| Field/status | Meaning and next step |
| --- | --- |
| `mismatches` | Failed mandatory gates; stop setup, inspect exact values |
| `component_issues` | Receiver/root/preferences/boot or required-app issues; recovery evaluates each independently |
| `backup_phase`, `failed_stage` | Saved progress and setup failure location, when a journal exists |
| `waiting_for_permissions` | Exit 3; owner accepts visible car prompt, then rerun same setup command |
| `configured` / `already_configured` | Configured values read back; projection remains untested |
| `android_reboot_verified` | This cycle completed the CLI's normal Android reboot check; historical evidence, not an ignition-cycle claim |
| `rerun_setup_with_reboot_check` | Keep laptop in Device mode and add the reboot check |
| `phone_handoff` | Finish visible onboarding/native UI checks, disconnect laptop, select Host and connect phone |
| `recovery` | Nested result after setup failure; inspect its status, errors and next action even though setup exits with an error |
| `recovery_required` / `recovery_errors` | Some recovery is blocked or interrupted; preserve state, resolve reported issue, rerun restore |
| `restored` / `already_restored` | This cycle's owned mutations recovered; preexisting installs/settings are kept |
| `projection_tested=false` | CLI cannot certify real phone projection, audio, touch or native controls |

A configured no-op reads the current state but does not relaunch apps or repeat
historical health checks. Re-run checks and obtain actual observations when
investigating a new failure. No command installs a background watcher on the car.

## Backups and recovery

The private state directory contains original CarAuto/receiver/fullscreen/launcher
state, a SystemUI preference copy, the original factory and reconstructed launcher
APKs when needed, and a durable operation journal. An incomplete entry is saved
before each device action. Stage completion includes verification evidence;
failed actions retain their error and failed stage. The original snapshot is not
replaced during a resume or rollback.

Use **one** `restore` command with this same directory and ADB options. It reverses
only owned changes, rolls back the launcher before removing a newly installed
receiver, and preserves preexisting apps. Full procedure, missing-root/broken-app
recovery, legacy ownership, interrupted restores and stale locks are in
[recovery.md](recovery.md). Unknown firmware or launcher identity still blocks
writes. A broken receiver does not itself prevent a known owned launcher rollback.

The complete v0.3 staged setup/recovery/reboot workflow is tested offline, not yet
through a full live cycle. [Evidence](verified-findings.md) · [Test checklist](testing.md).
