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
python3 oshan_x7.py setup --json
python3 oshan_x7.py status --json
python3 oshan_x7.py restore --json
```

On Windows, substitute `py -3` for `python3`. `prepare.py --verify-only` checks
existing host tools without downloading. Normal preparation downloads ADB if
needed; Python installation is handled by the agent using the
[host setup workflow](agent-setup.md), or by the person in manual mode.

`check` and `status` are read-only on the car. `setup` installs the pinned receiver
if absent, disables `com.eryanet.vlink`, saves the receiver's fullscreen preference,
installs the tested launcher update, and opens the receiver. `restore` reverses
that setup cycle, including its owned launcher update.

| Option | When to use it |
| --- | --- |
| `--adb /path/to/adb` | Use a specific verified ADB executable. Paths with spaces should be quoted. |
| `--adb-port 5038` | Your existing local ADB server uses 5038 rather than 5037. |
| `--serial YOUR_CAR_USB_SERIAL` | More than one USB device is attached. |
| `--state-dir .oshan-x7-next` | Keep a new setup cycle separate after a completed restore. Use the same value for its later restore. |
| `setup --apk /path/to/file.apk` | Use a previously downloaded official 3.5.0 APK. The fixed size/hash checks still apply. |
| `--json` | One stdout JSON object for agents; exit 0 = success, 2 = refusal/error, 130 = interruption. |

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

## Backups and recovery

Before the first device write, setup saves the original CarAuto enabled state,
per-app fullscreen value, receiver ownership, and operation journal to
`.oshan-x7/devices/…/backup.json`. A copy of the original SystemUI preferences XML
is retained alongside it. New cycles also save original launcher identity and,
when installing it, the verified factory and reconstructed APKs alongside the
journal. Keep this folder; it can contain device identifiers.
All private state, downloaded tools, and APKs are ignored by Git.

Reconnect the laptop in **Device** mode and run `restore` with the same ADB options
and state directory. Restore:

- Removes the modified launcher **only if this journal installed it over the
  factory base**. Android restores the untouched system APK; launcher data is
  retained. A preexisting exact update is kept. An uncertain completed install
  or interrupted rollback is resolved by exact current APK/UID/hash checks.
- Returns CarAuto to its exact original enabled state.
- Restores the original per-app layout behavior. An originally absent key becomes
  an explicit `-1`, which invokes the factory-default behavior; the entire SystemUI
  file is not overwritten.
- Removes Open Headunit only when this setup cycle installed it. Removing a newly
  installed receiver also removes its generated app data. A preexisting receiver
  and its settings are retained.

Repeated setup is a no-op after a completed matching setup. Repeated restore is
a no-op after a completed restore. A connection loss retains the journal: run
restore after reconnecting rather than retrying raw changes. Restore can itself
be retried after an interruption.

Backups from v0.1 remain usable. Restoring one retains its original AA-only
scope. Running v0.2 setup on a completed v0.1 cycle adds the launcher step while
preserving the original CarAuto/layout/receiver baseline. A matching launcher
already present at upgrade time is recorded as preexisting. Use v0.2 or later
for restore after installing this launcher; the old stock-only checker cannot
recognize the new update. [Full launcher and patch details](launcher.md).

Firmware or receiver replacement can cause restore's compatibility checks to
refuse writes; preserve the backup for diagnosis. After a completed restore, use
a new `--state-dir` for another cycle. If `operation.lock` remains after a computer
crash, establish that no setup/restore process is running before removing only
that lock. Never delete the original backup to silence an error.
