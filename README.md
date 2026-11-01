# Oshan X7 · CarPlay + Android Auto

**CarLink running fullscreen, launched from the large factory Home card** on
the reference 2025 right-hand-drive Oshan X7. The owner confirmed both Android
Auto and CarPlay fill the **1920 × 720** display, the large card opens CarLink,
and the factory Home button returns correctly. The launcher and fullscreen
setting also passed a normal Android reboot check.

![Factory Home with the large CarLink card](docs/images/launcher-carlink.png)

**CarPlay across the full display**

![CarPlay fullscreen on the reference car, with factory Home and Back overlays retained](docs/images/carplay-fullscreen.png)

**Android Auto across the full display**

![Android Auto dashboard fullscreen, captured before map labels loaded](docs/images/android-auto-fullscreen.png)

Actual headunit captures. [Reference screenshots and what each proves](docs/screenshots.md)
· [Live evidence and remaining tests](docs/verified-findings.md).

## Supported car and scope

- Exact **F202_MCA**, Android **9/API 28**, firmware
  **F202RHD_D1_20241022162756**, with the existing tested `su 0` access.
  The same badge or year is insufficient; the CLI checks exact firmware,
  immutable launcher, active APK, UID, default Home and USB identity.
- **CarLink 1.0.7**, using a locally signed variant that changes one conflicting
  manifest permission name. Its code and assets match the official release.
  [App artifact hashes and signing/update limitations](docs/carlink-trial.md).
- The current path migrates the previous qualified OpenHU setup through a
  recorded CarLink trial. **A one-command fresh CarLink install from stock has
  not been qualified.** The old installer remains a
  [separate historical guide](docs/openhu-setup.md).

CarAuto remains disabled; OpenHU is removed from active apps. Its exact APK,
the prior launcher and their original journals remain private for recovery.
The immutable factory launcher, Home/Back overlays and vehicle services remain.
No firmware flashing, Google services or network ADB is used.

## Use the current setup

Open the large **CarLink / CarPlay + Android Auto** card and connect one phone.
For the wired phone test, disconnect the laptop and select **Host模式** in the
factory development page. The **video-recording USB port** worked on the
reference car; the ordinary port was unstable. Its exact physical connector
map is not recorded. Use a data cable and accept the visible car/phone prompts.

For laptop work, disconnect the phone, return to **Device模式**, and reconnect
the laptop. Retain the same ADB executable, server port, USB target and original
CarLink state directory. Do not start a new baseline over an active cycle.

```sh
python3 prepare.py --json
python3 oshan_x7.py carlink-check --state-dir /path/to/original-carlink-state --json
```

Windows: use `py -3` instead of `python3`. Add the original `--adb`, `--adb-port`
and `--serial` options when needed. `carlink-check` is read-only; the promoted
setup reports **`carlink_configured`**.

## Reproduce the migration

Use the [guarded CarLink setup guide](docs/carlink-setup.md). From the exact
previous OpenHU baseline, the implemented stages are:

1. `carlink-trial --remove-openhu --reboot-check`: verify/copy OpenHU's installed
   APK, retain its data during removal, install the pinned CarLink variant and
   check app/Home health through a normal Android reboot.
2. Complete visible CarLink onboarding and permissions; test AA and CarPlay.
3. `carlink-fullscreen`: back up and set **CarLink's own** factory layout value,
   preserving OpenHU's value. Verify the connected picture at the new width.
4. `carlink-promote --reboot-check`: back up the old launcher and factory base,
   reconstruct/install the pinned CarLink launcher, then verify identity,
   fullscreen, Home and CarLink through another normal Android reboot.

All stages use the **same state directory**. Writes are journaled before
execution and read back; lost USB or an interrupted operation requires recovery
with that original journal. Do not repeat raw package or launcher mutations.

**For a local AI agent:** read [AGENTS.md](AGENTS.md),
[the laptop runbook](docs/agent-setup.md), [CarLink setup](docs/carlink-setup.md),
[car screens](docs/car-menu.md) and [recovery](docs/recovery.md). Prepare tools
and run the guarded CLI yourself; ask the owner only for physical/menu actions,
visible permissions and actual phone/control observations.

The owner-operated car sequence is **car Phone dial pad → `*#*#888` → Call →
`1111` → `开发模式`**. If that development page asks for its separate PIN, the
saved-code default is **`3821`**; the outer 1111 worked on the car, while 3821
has no recorded live-entry test and can be overridden by a changed password.
Stop if rejected. Use **Settings → System → Advanced → Developer options →
USB debugging / `USB 调试`** if needed. If Developer options is hidden, tap
**Build number** seven times in About device/tablet. Return to `开发模式`,
select **Device模式**, connect the trusted laptop, and accept its debugging
prompt. Keep Device mode throughout laptop commands and reboot checks.

## Recovery and remaining limits

Reconnect the laptop in Device mode and use the original CarLink journal:

```sh
python3 oshan_x7.py carlink-restore --state-dir /path/to/original-carlink-state --json
```

It restores the exact previous launcher backup, the owned CarLink layout value
and the saved OpenHU installation before removing only its owned CarLink app.
Do not use the historical OpenHU `restore` over the promoted launcher.
[Recovery scope and interruption handling](docs/carlink-setup.md#recovery).

Both projection modes, fullscreen, the large card and Home return are observed
results. Microphone/Siri/call audio, repeated reconnects, exhaustive native
controls and cold ignition cycles still need separate tests. The captured
CarPlay frame does not establish its transport or wireless reliability.
Recovery requires responsive Android/package management and authorized USB;
returning from Host with an unusable launcher remains unqualified.

## Project references

| Guide | Contents |
| --- | --- |
| [CarLink setup](docs/carlink-setup.md) | Current migration, launcher pins and recovery |
| [Trial and app details](docs/carlink-trial.md) | Permission conflict, exact variant and app ownership |
| [Screenshots](docs/screenshots.md) | Current reference frames and historical comparisons |
| [Car menu](docs/car-menu.md) | Codes, Chinese labels, USB roles and evidence |
| [Commands](docs/reference.md) | CLI options and current versus historical commands |
| [Verified findings](docs/verified-findings.md) | Observations, read-backs and limits |
| [Testing](docs/testing.md) | Offline tests and pending live checks |
| [Previous OpenHU setup](docs/openhu-setup.md) | Preserved old installer and recovery instructions |

Credit to [CarLink](https://github.com/F-e-n-y-x/CarLink),
[DiPlay](https://github.com/shihabal3amri/DiPlay) and
[Open Headunit](https://github.com/andreknieriem/open-headunit).
Original installer code/docs use the [MIT license](LICENSE); upstream software
and modifications retain their own licensing. See [third-party notices](THIRD_PARTY_NOTICES.md).
APKs, signing keys, phone data and private backups are not published.
[Contributing](CONTRIBUTING.md).
