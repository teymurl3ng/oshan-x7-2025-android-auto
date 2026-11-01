# Experimental CarLink trial alongside the existing setup

CarLink 1.0.7 can receive CarPlay and Android Auto. This app-only trial preserves
the original OpenHU APK/data for return, factory launcher update, Home/Back
overlays, OpenHU fullscreen setting and CarAuto state. It is separate from the AA installer. Android/CPU
requirements match the saved F202 profile; phone projection and vehicle behavior
still require observation. [Research](carplay-research.md).

**Live finding, 2026-11-02:** the official APK was rejected with
`INSTALL_FAILED_DUPLICATE_PERMISSION` because it redeclares OpenHU's
`com.andrerinas.openheadunit.permission.NAVIGATION_UPDATE`. The attempt stopped
before OpenHU was paused, and recovery checked the original setup. Disabling an
app does not free its globally declared permission name.

The owner authorized the prepared **local coexistence variant**. It renames
only that manifest permission to
`com.carlink.oshanx7trialapp.permission.NAVIGATION_UPDATE` and is signed with a
separate private trial key. All 1,232 APK entry payloads were compared: code and
assets are byte-identical; only the manifest differs by that same-length string.
Signature and alignment checks passed. This is not an official CarLink APK;
official APK updates cannot install over its different signing identity.
Do not update it through the app during the pinned trial.

The CLI reconstructs the exact variant using the pinned official base and
`patches/carlink-1.0.7-coexist.bsdiff`. No APK or private key is shipped. The
patch reconstructs the audited output byte for byte, and contains neither
unchanged bundled authentication input verbatim in its compressed nor decoded
payload. `tools/prepare_carlink_coexist.py` documents/audits the sole content edit.

| Local coexistence artifact | Pin |
| --- | --- |
| APK | 16,565,044 bytes; SHA-256 `a06e8ffcdcee0a1c555e39af9ea5f478addbb902b532f5b63a0c2c68d5f6a19e` |
| Signing certificate SHA-256 | `dbacadae126d332ea436912ff63fd396d46833dae763ea6562dc694c7fe6d28c` |
| BSDIFF patch | 252,089 bytes; SHA-256 `4e1f5d954bb24fd48a6766ebb1fdd38a2e3cd4754465a0367841b7305ecbc514` |

## How clashes are controlled

CarLink and OpenHU both handle phone USB attachment. CarLink also enables
Bluetooth auto-connect by default; boot startup and root mode default to off.
The trial therefore **temporarily disables the exact pinned OpenHU app for user
0**, after recording its original enabled state. It leaves its APK and data
installed. Restore returns that exact enabled state and verifies OpenHU/Home
before removing only the newly installed, exact CarLink APK for user 0.

The owner subsequently authorized removing OpenHU for the test and reinstalling
it afterwards. `carlink-trial --remove-openhu --reboot-check` copies the installed
OpenHU APK to `openhu-original.apk` beside this trial's journal and checks the
pinned hash/size before trial writes. It uses `pm uninstall -k --user 0` with the
pinned version code, requesting data/cache retention, and verifies absence for
user 0. The APK is a local backup; retained app data stays on the headunit and
is not a separate laptop data archive. The approved CarLink variant is unchanged.
Restore reinstalls the verified OpenHU backup with `-r`, restores its original
enabled state, and verifies OpenHU/Home before removing CarLink.

In the earlier disable-only live attempt, CarLink installed and opened, but
OpenHU was enabled again after Android reboot. Guarded recovery restored the
original setup and removed CarLink. The cause was not established; an OEM
service and delayed package-state persistence remain possible explanations.
Phone projection was not tested in that attempt.

**Removal-mode live result, 2026-11-02:** the installed OpenHU APK was copied
and verified. On this firmware, `pm uninstall -k` leaves a retained dumpsys
package record that still reports `installed=true`, while the active
`pm list packages --user 0` registration is absent. The first three removal
attempts conservatively rolled back this contradictory state and successfully
reinstalled the exact backup. The receiver check now also reads active package
registration, rejecting malformed output and still hashing any active APK.
The subsequent trial verified OpenHU absent, CarLink installed/open, and both
states persisting through a normal Android reboot. Home and CarLink health
checks passed; 36 KiB of retained OpenHU data was still present. A screenshot
showed CarLink setup step 2 of 5 with all required access allowed. Onboarding,
phone projection, native-control observations and ignition cycles remain
separate from those machine checks.

The owner subsequently reported both **Android Auto and CarPlay working**,
with the same restricted-width layout previously seen in OpenHU. This is an
owner projection observation; audio, microphone, reconnect and every native
control were not individually enumerated. The original per-app fullscreen
preference names OpenHU and therefore does not configure CarLink.

The owner requested the screen fix. `carlink-fullscreen`, run over USB with the
active trial's original state directory, backs up CarLink's existing value and
the SystemUI preference XML, then applies the same factory setting `0` to
`com.carlink.app`, refreshes its layout and checks SystemUI, Home and CarLink.
It preserves OpenHU's key. Its journal owns the new preference independently;
`carlink-restore` restores the exact original CarLink value, using `-1` for
factory behavior if originally absent. Fullscreen phone and reboot checks
remain separate from successful preference read-back.

**Fullscreen application result:** the live command read back CarLink's value
as `0`, left OpenHU's value at `0`, and passed SystemUI, Home and CarLink health
checks. `dumpsys window` reported CarLink Home's frame and parent as
`[0,0][1920,720]`. A screenshot showed its setup UI spanning the full display,
without the former side panels, with the factory Home/Back overlays retained.
The owner then reconnected the phones and confirmed **both Android Auto and
CarPlay fill the screen**. This establishes owner-observed connected fullscreen
projection for both modes on this car. Audio, microphone, reconnect behavior and
native controls were not individually enumerated. The fullscreen change has not
separately been checked through another Android reboot or cold ignition cycle.

The existing large AA card still targets OpenHU. During the trial, open CarLink
from its own icon. The fullscreen command does not redirect that card.
The subsequent owner-authorized [primary setup migration](carlink-setup.md)
replaced that launcher with the pinned CarLink card. It passed an Android
reboot check, and the owner confirmed large-card launch and Home return work.

Sources: [startup defaults](https://github.com/F-e-n-y-x/CarLink/blob/v1.0.7/carlink-core/src/main/java/com/carlink/core/settings/CarLinkPreferences.kt),
[USB/boot entry points](https://github.com/F-e-n-y-x/CarLink/blob/v1.0.7/carlink-core/src/main/AndroidManifest.xml),
[upstream troubleshooting](https://github.com/F-e-n-y-x/CarLink/blob/v1.0.7/docs/TROUBLESHOOTING.md).

## Laptop workflow

Use `prepare.py --json` and the returned Python/ADB paths. Keep the same ADB
server port, verified USB serial and state directory throughout. Existing state
and journals must be retained. Commands below omit connection options for
readability; retain the actual `--adb`, `--adb-port` and `--serial` when needed.

```sh
python3 oshan_x7.py check --json
python3 oshan_x7.py carlink-check --json
python3 oshan_x7.py carlink-trial --reboot-check --json
```

`carlink-check` is read-only. A fresh trial requires the complete exact AA
firmware/launcher/root/receiver gates, existing pinned OpenHU and already
disabled CarAuto. It refuses a preexisting CarLink, including an installation
registered for another Android user, and known enabled standalone DiPlay builds.
No existing CarLink is adopted or updated. The supplied/downloaded APK must
match the pinned local coexistence variant's complete hash and size. Its
downloaded base must separately match the official release hash and size.

The separate `carlink-trial.json` is stored beside the existing AA backup's
location under the chosen state directory; it never overwrites `backup.json`.
The shared state-directory operation lock serializes commands. Every change is
journaled before it is attempted and read back afterwards. Lost USB or an
uncertain operation requires restore, rather than a second installation.

The trial checks Home and OpenHU before installation, installs CarLink, pauses
OpenHU and checks the new app/SystemUI. `--reboot-check` performs a normal
Android reboot over USB and checks that isolation, original settings and UI
persist. It does not establish phone projection, cold ignition or a boot-rescue
route. A visible runtime-permission pause exits 3: accept the prompt and rerun
the same command, retaining the original journal. Inspect an unexpected screen.

Regular AA `check` correctly refuses setup compatibility while OpenHU is paused.
Only the trial's own narrow gate accepts the exact disabled receiver it owns.
In removal mode it accepts absence only after its recorded removal and with
the exact local OpenHU backup still verified.
This does not qualify an unknown APK or relax the AA setup profile. Complete
`carlink-restore` before running the original AA setup/restore.

## Owner actions

If USB ADB is already authorized, connect the cable and let the agent verify it.
Otherwise, while parked: car Phone dial pad → **`*#*#888` → Call → `1111` →
`开发模式`**. If its separate PIN is requested, the saved-code default is
**`3821`**. The outer `1111` was tested; `3821` has no recorded live-entry test
and a changed password can override it. Stop if rejected. Use **Settings →
System → Advanced → Developer options → USB debugging / `USB 调试`** if needed;
if hidden, enable Developer options with seven Build-number taps in About
device/tablet. Return to `开发模式`, select **Device模式**, connect the laptop
and accept its debugging prompt. No network ADB is used by this workflow.

Keep phones unplugged and their Bluetooth off during laptop stages to avoid
automatic projection. Complete visible CarLink onboarding when guided:

- Choose the actual brand or **Other**, never BYD for this car.
- Select right-hand drive. Use the default/automatic picture setting initially.
- Keep **Start with the car**, **Root mode**, experimental external-Bluetooth
  routing and BYD/cluster/HUD features off. Turn Bluetooth auto-connect off for
  the first wired trial; the exact control label must be checked on the app.
- Review actual permission prompts. Microphone is needed to test Siri/calls;
  wired CarPlay may request a local VPN on the car. Do not authorize optional
  network-ADB helpers, root tweaks or installation of another APK.

After laptop/reboot checks and native-control observations finish, disconnect
the laptop, select **Host模式** on the same factory `开发模式` page and connect
one phone to the working **video-recording USB port** with a data cable. The
iPhone 15 Pro Max needs a suitable USB-C data cable; do not assume the car-end
connector or physical port position. Use the visible app chooser without making
an unnecessary permanent default. Keep the other projection app paused.

Test picture, touch, Maps, music/navigation audio, Home return and reconnect.
Test Siri and call audio separately; the existing microphone problem remains
unresolved. Test the Android phone separately before describing this as an AA
replacement. Factory Home, radio/music, AC, native phone and settings need owner
observations. Initially accept the ordinary app width; full-width integration
is enabled only with the separately journaled `carlink-fullscreen` stage.

## Return to the existing system

Unplug the phone, regain **Device模式**, connect the laptop and use the same
state directory/USB target/ADB server:

```sh
python3 oshan_x7.py carlink-restore --json
```

This restores OpenHU's original enabled state, verifies Home/OpenHU and removes
only the owned exact CarLink app for user 0. OpenHU data, APK and original AA
journals remain. It preserves launchers, CarAuto and OpenHU's fullscreen value;
if the fullscreen stage was used, it restores its owned CarLink layout value.
If this cycle used `--remove-openhu`, the same restore command first reinstalls
its verified local OpenHU backup; do not run a fresh AA setup to recreate it.
If another APK replaced either receiver, stop and inspect; unknown apps are
never removed. Partial recovery keeps its journal and reports what remains.
After completion, preserve that cycle and use a new state directory for any
later trial. Phone-side pairing choices and manually chosen USB defaults are
outside automatic restoration; inspect them if a subsequent chooser differs.

Recovery needs responsive Android/package management and authorized USB. The
route back from Host mode with a broken launcher remains unqualified.
[Car-menu evidence](car-menu.md) · [Recovery boundaries](recovery.md).
