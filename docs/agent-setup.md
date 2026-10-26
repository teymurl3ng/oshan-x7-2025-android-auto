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

Once authorized, using the same interpreter, ADB path, port, and USB target:

```sh
python3 oshan_x7.py check --json
python3 oshan_x7.py setup --json
python3 oshan_x7.py status --json
```

Add `--adb /absolute/path/to/adb`, `--adb-port 5038`, and/or `--serial ...` only as
needed; keep these options for later status/restore calls. Run setup **only when
check succeeds**. Preserve the original backup. Never weaken firmware checks to
turn an unsupported car into a supported one.

Setup also installs the pinned Home-screen update after the exact factory and
active launcher checks pass. It builds it locally from the car's original APK
using the bundled patch; Python and ADB remain the only owner-side tools. Do not
download an arbitrary replacement launcher or run another installer alongside it.
An already installed exact update is preserved as preexisting unless this
setup's journal owns it. Keep that ownership distinction on restore.

## 6. Finish and report

Guide Open Headunit's visible onboarding and USB permissions. Then have the owner
disconnect the laptop, set **Host mode**, and attach the phone. Test actual image,
audio, touch, microphone, normal car controls, and reboot persistence with the owner.
Use available screen inspection to help with onboarding when practical; leave
authorization prompts to the person. Do not repeatedly send connect commands.

Check that the large Android Auto card opens OpenHU, the small duplicate and
launcher/test entries are absent, and factory Home returns to the launcher.
The owner's video-recording USB port worked; the ordinary port remained unstable.
Microphone recognition remains unresolved and must not be reported as fixed.
See [launcher details](launcher.md) for the actual build and live-test limits.

Report the tool paths, compatibility result, changed settings, backup location,
and outcome of the phone test. Separate read-back results from owner observations.
If interrupted, reconnect in Device mode and run restore using the saved cycle.
Wireless remains outside the supported workflow.
