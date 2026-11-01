# Installation runbook for AI agents

Handle the computer work from repository acquisition through installation and
recovery. Ask the user only for actions that need their hands or actual OS
approval. Give **one physical action at a time**, naming the device, screen,
control and expected result. Wait for a reply or verified device read-back before
requesting the next action.

Read [AGENTS.md](../AGENTS.md), [car menus](car-menu.md),
[permissions](permissions.md) and [recovery](recovery.md) before car access.

## 1. Find or acquire the repository

Identify the laptop's OS/CPU and whether your terminal can access its local USB.
Use native Windows tools for Windows USB; do not assume WSL, a remote machine or
a container can see the car.

Look for an existing checkout and `.oshan-x7` or custom state directory. Reuse
these without overwriting backups. Otherwise acquire the repository yourself:
use Git if available, or download and extract
[the ZIP](https://github.com/teymurl3ng/oshan-x7-2025-android-auto/archive/refs/heads/main.zip).
PowerShell provides `Invoke-WebRequest` and `Expand-Archive`; macOS provides
`curl` and `ditto`. On Linux use available archive tools, or install Python as
below and use its standard library. Git is optional.

Do not ask the user to download the project, install Git, find executable paths
or repair PATH. Keep working in the acquired folder; a ZIP checkout is sufficient.

## 2. Prepare Python and ADB

Execute an existing Python to verify **3.10+**, its standard-library modules and
absolute executable path:

```sh
python3 -c "import sys, ssl, urllib.request, zipfile; print(sys.executable); print(sys.version); raise SystemExit(sys.version_info < (3, 10))"
```

On Windows also inspect `py -3` and `python`. An alias opening the Store is not
a working interpreter. Reuse a suitable installation. If Python is missing or
too old, install it yourself from a trusted source:

| Laptop | Installation source and checks |
| --- | --- |
| Windows | Use the official [Python install manager](https://docs.python.org/3/using/windows.html) from python.org or Microsoft Store, or an appropriate PSF package from an existing WinGet installation. Verify the publisher/signature of downloaded installers. Install a runtime, then execute it and record its absolute path. Do not install WinGet merely for this task. |
| macOS | Reuse an existing package manager, or download the signed `universal2` package from [python.org](https://www.python.org/downloads/macos/). Verify with `pkgutil --check-signature`, install and complete `Install Certificates.command` as described in the [official guide](https://docs.python.org/3/using/mac.html). Check HTTPS works. Do not install Homebrew just for this task. |
| Linux | Identify the distribution using `/etc/os-release`, then use its signed package repositories for Python 3. Check the installed version; do not change system Python symlinks. |

Choose an available supported release from the source, not an invented download
URL. CI covers Python 3.10 and 3.13; do not replace a working compatible Python
just to match those versions. There are no pip dependencies, Java or Android
Studio requirements.

If an installer/administrator approval requires the user, prepare the concrete
trusted action and ask for that action only. A managed laptop may need its
administrator. Continue preparation yourself after approval.

With the verified interpreter, run:

```sh
python3 prepare.py --json
```

The helper executes `adb version` for existing PATH/private/common SDK copies.
If none works, it downloads the complete official Google Platform Tools archive
and verifies that the extracted ADB runs. It returns absolute Python/ADB paths
and versions without accessing the car. Use its ADB path with `--adb` for every
car command; no global PATH change is needed.

The download links come from [Google's Platform Tools page](https://developer.android.com/tools/releases/platform-tools).
The recorded archive digest is a local audit record, not an independent integrity
pin. CarLink and the launcher have separate fixed artifact hashes.

On Linux ARM use the distribution's native `adb`/`android-tools` package; Google's
Linux ZIP is x86_64. Diagnose incompatible/broken binaries rather than repeatedly
downloading them. Preserve a broken private tools folder for diagnosis. Resolve
certificate setup if HTTPS fails; never disable TLS verification.

## 3. Establish authorized USB

Check existing USB access before repeating car-menu onboarding. Use the verified
ADB with `devices -l` on port **5037**, or reuse the environment's actual custom
server port. Do not blindly kill servers or replace working tools.

If the car is not already authorized, guide these actions individually, inline
in your messages, using [the pictures](car-menu.md):

1. Park and keep the car powered, with the phone disconnected.
2. On the car's Phone dial pad enter **`*#*#888`**, tap **Call**, then enter
   **`1111`** to open the factory menu.
3. Open **`开发模式` (Development mode)**. If it separately asks for a PIN,
   explain that **`3821`** is its code-inspected default, not a tested live entry.
   A changed password may override it. Stop if rejected.
4. Tap **Settings**. In Android **System → Advanced → Developer options**, enable
   **USB debugging / `USB 调试`**. If hidden, use the standard seven taps on
   **Build number** in **About device/tablet**; the exact About label may vary.
5. Return to `开发模式` and select **Device模式**. Have the user connect the USB
   data cable and accept **Allow USB debugging** for this trusted laptop.

Inspect a different screen rather than guessing coordinates or trying codes
from another model. Missing USB must be resolved before writes:

| Condition | Next step |
| --- | --- |
| Unauthorized | Ask the user to accept this laptop's debugging authorization on the car. |
| No device/offline | Inspect the USB role, data cable/port, OS detection and server. |
| Linux access denied | Check device permissions and the distribution's Android USB/udev setup. Do not run the entire installer as root to bypass host permissions. |
| Windows driver missing | Inspect hardware IDs; use a signed OEM driver from the manufacturer or Windows Update. Follow [Android's driver guidance](https://developer.android.com/studio/run/oem-usb); do not assume Google's driver fits or use arbitrary driver packs. |
| Multiple devices | Disconnect other devices or select the car's verified USB serial explicitly. Network transports and emulators are refused. |

Keep the same interpreter, ADB executable/server port, USB target and state folder
throughout. Never change the shared USB role while a laptop command is running.

## 4. Check and install

Use the verified executable paths. The following commands show the sequence;
replace the ADB placeholder and include any selected connection/state options
on **every** command:

```sh
python3 oshan_x7.py check --adb "/absolute/path/to/adb" --json
python3 oshan_x7.py setup --reboot-check --adb "/absolute/path/to/adb" --json
python3 oshan_x7.py status --adb "/absolute/path/to/adb" --json
```

Setup follows a successful strict `check`. Recovery-eligible status alone is
insufficient. Stop mismatches without modifying profiles or bypassing checks.
The head unit must provide its existing factory root (`su 0`); do not install root.

The installer performs these stages. Do not reproduce them with raw commands:

| Stage | Required result |
| --- | --- |
| Compatibility | Exact firmware/MCU/display, factory and active launcher identity/UID/version/Home, required apps, user 0, completed boot, root and Device mode |
| Artifacts and backup | Verified CarLink download, factory launcher backup, reconstructed update and saved original settings |
| Home | Healthy factory Home/SystemUI before installation |
| CarLink | Install if absent; verify app identity |
| Permissions | Grant and check runtime/special access, battery exemption and bound USB service before opening CarLink |
| App check | CarLink opens with stable processes and no fresh relevant crash/ANR |
| CarAuto/fullscreen | CarAuto disabled for user 0, CarLink layout value 0, SystemUI healthy |
| Launcher | Exact update installed; identity/Home and foreground checks pass |
| Final state/reboot | Current settings verified, new Android boot observed, settings and Home/CarLink checked after reboot |

The installer saves intent before writes and checks changes before completing
journal operations. Keep all journals and backups. Three stable process samples
can catch immediate failures; they do not prove phone projection or long sessions.

## 5. Handle pauses and failures

- **Exit 3 / `inspect_permission_prompt`:** keep the laptop connected. Inspect
  the actual permission screen and diagnose the missing access. Normal CarLink
  grants are automatic; do not start a generic permission walkthrough. After
  resolving the specific issue, rerun the same setup command. An already observed
  reboot is validated without requesting another one.
- **Exit 2:** inspect `failed_stage`, `recovery`, `component_issues`, errors and
  `next_action`. Automatic rollback may have succeeded; report installation as
  failed even then. Diagnose the cause before attempting a new installation.
- **USB loss or incomplete recovery:** preserve the original state, regain Device
  mode and run `restore`. Do not create a fresh baseline over the failed cycle.
- **Exit 130:** inspect status; an interruption may have occurred outside the
  staged recovery handler.
- **`inspect_configuration_drift`:** the current settings differ from the saved
  completed setup. Inspect the difference before phone connection or recovery.

Follow [recovery.md](recovery.md), including its stale-lock checks. Unknown
replacement apps remain untouched; partial recovery must not be called complete.

## 6. Finish with the user

Require `android_reboot_verified=true` and `next_action=phone_handoff` from
successful setup. While the laptop remains connected, have the user check the
large card/Home and available native controls. Complete available CarLink welcome
and car settings after the command finishes. The [upstream setup flow](https://github.com/F-e-n-y-x/CarLink/blob/v1.0.7/app/src/main/java/com/carlink/app/ui/setup/SetupModel.kt)
separates car selection from phone pairing. Inspect actual options; do not invent
a profile or insist on completing a phone-dependent step before connecting it.

Then guide one action at a time: disconnect laptop → select **Host模式** → open
CarLink → connect the phone. Wired projection uses the **regular charging/CarAuto
USB port**. For wireless CarPlay follow CarLink's pairing flow with iPhone Wi-Fi
and Bluetooth enabled. Use a cable for Android Auto. Phone USB debugging is not
required. Review [Connect your phone](../README.md#connect-your-phone) and record
projection, fullscreen, sound, touch, card/Home and native-control results.

A car-side USB prompt may still need a tap; enabling the service is not proof
that every dialog is handled. Historical results and unresolved tests belong in
[the test record](verified-findings.md).

Report what changed, machine checks, what the user actually tried, remaining
checks, the exact backup path and how to restore. Keep the interpreter/ADB paths
and connection options with that record so later commands can reuse them.
Supervision ends at laptop disconnection. Recovery requires responsive Android
and authorized USB; a return from Host with an unusable launcher/menu is untested.
