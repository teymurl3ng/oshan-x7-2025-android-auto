# Agent workflow: take care of the laptop setup

I wrote this for the agent doing the setup. Please handle the laptop preparation
yourself instead of asking the person to install developer tools, find executable
paths, or fix PATH variables. Then use the firmware-gated CLI for the car changes.

## 1. Inspect the laptop and get the repository

- Identify the real host OS and CPU. Use native Windows tools for a Windows USB
  connection; do not assume a WSL container or a remote sandbox can see local USB.
- Use an existing checkout if available. Otherwise clone the repo if Git works.
- If Git is absent, **do not make Git a prerequisite**. Download
  [the repository ZIP](https://github.com/teymurl3ng/oshan-x7-2025-android-auto/archive/refs/heads/main.zip)
  using the host's downloader, extract it, and work in the extracted folder.
  PowerShell has `Invoke-WebRequest` and `Expand-Archive`; macOS has `curl` and
  `ditto`. On Linux, use available download/archive tools, or Python after step 2.
- Read this guide, AGENTS.md, and the car-screen guide. Check for an existing
  `.oshan-x7` backup before starting a new cycle. Preserve an existing checkout and
  its backup rather than downloading over it.

## 2. Find or install Python

Run the existing interpreter to verify **Python 3.10 or newer**; a command name
alone is insufficient. Check its ability to import `ssl`, `urllib.request`, and
`zipfile`. Record the interpreter's absolute executable path for subsequent calls:

```sh
python3 -c "import sys, ssl, urllib.request, zipfile; print(sys.executable); print(sys.version); raise SystemExit(sys.version_info < (3, 10))"
```

On Windows, also check `py -3` and `python`; a Microsoft Store alias which opens
the Store is not a working interpreter. Reuse a suitable existing installation.
**If Python is missing or too old, install it yourself** using an appropriate
official installer or the laptop's trusted package manager:

| Host | Agent action when Python is missing |
| --- | --- |
| Windows 10/11 with WinGet | Install the PSF package, for example `winget install --id Python.Python.3.13 --exact --source winget --accept-package-agreements --accept-source-agreements`. Then locate and execute the installed interpreter; refresh the process PATH or use its full path. |
| Windows without WinGet | Download a supported Windows installer from [python.org](https://www.python.org/downloads/windows/), verify its Python Software Foundation Authenticode signature, and run a per-user install. The [Python Windows documentation](https://docs.python.org/3/using/windows.html) also describes the official install manager. Do not require the owner to install WinGet first. |
| Ubuntu / Debian | Inspect `/etc/os-release`. Use the distribution's signed repositories to install `python3`, then check the resulting version. Ubuntu 22.04+ and Debian 12+ provide a suitable baseline. Do not repoint the system's Python symlinks. |
| Fedora / other Linux | Use the identified distribution's signed package manager for Python 3. Verify the result; do not guess an `apt` command on a different distribution. |
| macOS with an existing Homebrew | Reuse a suitable interpreter or install a supported Python with the existing package manager. Do not install Homebrew just to obtain Python. |
| macOS without a package manager | Download a supported signed/notarized `universal2` installer from [python.org](https://www.python.org/downloads/macos/), verify it with `pkgutil --check-signature`, and run the installer with the required OS approval. Complete its documented certificate setup and verify HTTPS works. [Official macOS installation instructions](https://docs.python.org/3/using/mac.html). |

Choose a currently supported compatible release from the source, rather than
inventing a versioned download URL. Python 3.13 is included in this repo's CI;
an already working newer compatible interpreter need not be replaced. No `pip`
dependencies, Java, full Android Studio, or phone-side debugging are required.

Carry out the installation within your available permissions. If an actual OS
administrator prompt or installer consent requires the owner, prepare the exact
installer/action first and ask only for that action. Do not hand back a generic
"install Python and try again" task. A managed laptop may require its administrator;
do not claim you can bypass those restrictions.

## 3. Find or download ADB automatically

Using the verified interpreter, run:

```sh
python3 prepare.py --json
```

Use the actual interpreter path or `py -3` on Windows. The helper:

1. Runs `adb version` against existing PATH, local, and common SDK installations.
2. If none works, downloads the complete official Google Platform Tools ZIP for
   the host OS over HTTPS, and extracts it privately under `.oshan-x7/tools/`.
3. Tests the extracted `adb version`, including the Windows DLLs kept alongside it.
4. Returns the Python/ADB paths and versions. It never connects to or changes the car.

The [official Google download page](https://developer.android.com/tools/releases/platform-tools)
is the source of these stable download links:

| OS | Official archive |
| --- | --- |
| Windows | `https://dl.google.com/android/repository/platform-tools-latest-windows.zip` |
| macOS | `https://dl.google.com/android/repository/platform-tools-latest-darwin.zip` |
| Linux x86_64 | `https://dl.google.com/android/repository/platform-tools-latest-linux.zip` |

The helper records the downloaded archive's SHA-256 for local auditing. That is
not an independently published integrity pin; host tools come from Google's HTTPS
endpoint. The receiver APK has its own fixed checksum in the firmware profile.

For Linux ARM, use the distribution's native `adb` / `android-tools` package;
Google's Linux ZIP is for x86_64. If a found binary fails, diagnose OS/CPU/library
compatibility rather than repeatedly downloading it. If HTTPS fails after a new
macOS Python install, finish that installer's certificate setup; do not disable TLS
verification. Re-run preparation to verify the repaired installation.

Use the returned absolute ADB path with the car CLI's `--adb` option. The CLI also
searches working system, private, and common SDK installations automatically.
Do not require a global PATH edit.

## 4. Guide the owner through the car screens

Use [car-menu.md](car-menu.md). Show the owner the short sequence first:

**Car Phone → dial `*#*#888` → Call → `1111` → factory menu.**

Then guide the exact Chinese labels for opening Android settings, enabling USB
debugging, and selecting Device mode. Ask for screen context only if it differs
from the documented controls. Do not invent coordinates or try another model's PIN.
The separate `开发模式` page's default `3821` is code-verified, not a new live test.

The owner connects the laptop and approves the car's debugging prompt. Do not
change the shared port to Host while laptop commands are still running.

## 5. Resolve the USB connection, then run setup

Use the verified ADB executable. Start with `adb devices -l` on the normal local
server port 5037. If the user's existing environment uses another port, inspect
that existing server; port 5038 was used in the reference session. Do not blindly
kill/restart servers or replace a working ADB installation.

If no authorized USB transport appears, diagnose it:

- **Unauthorized:** have the owner accept the car's debugging prompt.
- **No device:** check Device mode, cable/port, and OS detection first.
- **Linux access denied:** inspect the relevant USB group/udev permissions and
  follow the distribution's Android-device setup. Do not run the entire installer
  as root as a substitute for fixing USB access.
- **Windows driver missing:** inspect Device Manager / hardware IDs, then obtain
  an appropriate signed OEM driver through the manufacturer or Windows Update.
  [Android's official driver guidance](https://developer.android.com/studio/run/oem-usb).
  Do not install arbitrary driver packs, assume Google's driver fits this car,
  or disable Windows driver-signature enforcement.
- **Multiple devices:** disconnect phones or select the car's verified USB serial
  explicitly. Network transports and emulators are refused by the CLI.

Once authorized, retain the same interpreter, ADB executable, port, USB target
and state directory. Never change transport/USB role during a command.

## 6. Run the stages and act on their evidence

```sh
python3 oshan_x7.py check --json
python3 oshan_x7.py setup --reboot-check --json
python3 oshan_x7.py status --json
```

Add `--adb "/absolute/path/to/adb"`, `--adb-port 5038` and/or `--serial ...` only
as needed. Retain them for every later call. Setup must follow a successful
**strict check**, not merely a recovery-eligible status. No force flag exists.

| Stage | CLI evidence before proceeding | Agent action |
| --- | --- | --- |
| Compatibility | Exact firmware/MCU/display, factory and active launcher hash/UID/version/HOME, required apps, user 0, boot/root/receiver checks | Stop unknown configurations; diagnose rather than changing the profile |
| Artifacts and backup | Official receiver pin; factory pull and patch/output pins; durable original state | Preserve the state directory; do not expose private data |
| Baseline Home | Successful launch, resumed launcher, stable launcher/SystemUI processes, no fresh relevant crash/ANR | Stop and inspect a preexisting failure |
| Receiver | Install if absent, hash/version read-back, healthy receiver foreground | Guide visible onboarding/permissions; don't silently grant them |
| CarAuto | Exact disabled-user state read-back and SystemUI health | Continue automatically when verified |
| Fullscreen | Saved value 0 and SystemUI health | Continue automatically; stored value is not proof of rendered width |
| Launcher update | Exact reconstructed APK installed, hash/UID/version/HOME read-back, healthy foreground | Keep the factory base and journal; don't run a separate launcher installer |
| Final state | All configured values plus healthy receiver | Complete visible onboarding while laptop stays connected |
| Android reboot | One new boot identity, boot complete, configured state, Home/receiver health | Require `android_reboot_verified=true` before phone handoff |
| Owner checks | Large card, Home, icons and usual native controls | Record what the owner actually tried |
| Phone handoff | Disconnect laptop → Host模式 → phone on recording port | Owner tests real projection, sound, touch and reconnect |

Every journal operation is saved as incomplete before its action. Completion is
saved only after that action's verification. The original snapshot is retained.
There is one shared recovery engine for setup failure and the `restore` command.
New health observation uses Android 9 process/foreground records and fresh log
entries, without clearing logs. Three stable samples span roughly two seconds;
startup observation is bounded to 12 seconds, with individual read timeouts.
This detects some immediate failures; it does not prove long-term reliability.

### Permission pause

Exit **3**, `status=waiting_for_permissions`, is a deliberate pause. Tell the
owner which **car** prompt is visible, have them accept it, then rerun the same
`setup --reboot-check --json` command. The journal still owns any receiver
installed before the pause. Do not replace the backup or switch to Host.

The CLI recognizes standard Android runtime permission activities. An app's own
onboarding usually remains inside OpenHU and can pass the UI health check;
complete it visibly anyway. An unrecognized blocking system/app screen may be
reported as a health failure. Inspect it, rather than cycling launches or calling
it an app crash without logs. Use [the prompt table](car-menu.md#prompts-and-which-screen-to-use).

### Failure or interruption

Exit **2** can contain a failed stage and nested `recovery` result. Recovery may
have succeeded even though setup correctly still reports failure. Do not call it
a completed install. If recovery is incomplete or USB disappeared, retain the
journal, reconnect in Device mode and run `restore`. Do not automatically start
a fresh install after rollback; first diagnose the failed stage. Exit **130**
means an interruption outside the staged failure handler; also inspect status.
[Recovery procedure, partial results and lock handling](recovery.md).

## 7. Handoff and report

After `next_action=phone_handoff`, have the owner verify the large Android Auto
card, Home return, absent duplicate icons and their usual native controls. Then
ask for the physical laptop-disconnect/Host/phone sequence. Phone USB debugging
is not needed. The phone connects directly to the car, not through the laptop.

The video-recording port worked on the reference car. The ordinary port still
failed after about 10–15 seconds. Do not claim CarAuto disable alone explains all
USB failures. Guide phone Android Auto prompts and car USB-access prompts. Maps,
sound, touch, Home and reconnect need observation with the phone connected.
Microphone/Gemini remains unresolved; wireless is outside this qualified flow.
OpenHU's optional Show toast messages switch is a manual setting, not part of
installer ownership or restore.

Report the interpreter/ADB paths, compatibility result, changed stages, backup
location, Android reboot evidence and the owner's phone/native-control results.
Keep read-back, observed UI, owner reports and untested items distinct. Do not
claim a full ignition cycle, all vehicle functions, or the new unified workflow
has been live-qualified based on earlier component tests.

USB supervision stops when the laptop is unplugged. A launcher failure while
still in Device mode can be diagnosed through authorized USB if Android/ADB is
responsive. The route back to Device from Host with an unusable launcher has not
been tested. Explain that boundary before representing this as unattended rescue.
