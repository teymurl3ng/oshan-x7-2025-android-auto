# Oshan X7 · Android Auto

Full-screen wired Android Auto and an **Open Headunit button on the factory Home
screen**, tested on my 2025 right-hand-drive Oshan X7. This project installs the
receiver, disables CarAuto, saves fullscreen and updates the original launcher.

**Open Headunit across the full 1920 × 720 display**

![Open Headunit filling the car display, with USB and Settings controls and the small factory Home overlay](docs/images/open-headunit-fullscreen.png)

**The factory launcher, with Open Headunit in place of CarAuto**

![Updated factory launcher with a large Android Auto card labeled Open Headunit, alongside Music, Radio and Bluetooth phone](docs/images/launcher-after.png)

Actual captures from my car. The first shows OpenHU's main screen; full-width
Android Auto was checked separately with a connected phone. The second was taken
after a normal Android reboot. [Before/after comparisons and app menu](docs/screenshots.md).

## Before you start

- **Supported unit:** F202_MCA, Android 9, firmware **F202RHD_D1_20241022162756**.
  The installer checks the exact firmware and launcher; the same badge/year is
  not enough. The car must already have the tested root access.
- **You need:** the parked car with its headunit powered, a laptop with local USB
  access, an Android phone and suitable USB **data** cables. Android Auto runs on
  the phone; OpenHU receives it on the car. Phone USB debugging is not required.
- **Testing status:** the individual changes and exact launcher worked on my car,
  including a normal Android reboot. The combined v0.3 installer/recovery/reboot
  flow still needs a full live car cycle. [Evidence and limits](docs/verified-findings.md).

## Choose how to install

| Option | Who runs the laptop commands? | Start here |
| --- | --- | --- |
| **Automatic — local AI agent** | Your agent prepares the laptop, runs setup, checks each stage and handles recoverable failures | [Option 1](#option-1--automatic-setup-with-a-local-ai-agent) |
| **Manual — run it yourself** | You prepare the laptop and run the commands below; the same installer applies and verifies the car changes | [Option 2](#option-2--manual-setup) |

Both options use the same compatibility checks, backups and unified restore.
In **both**, you operate the car menus, connect cables, accept visible permissions
and test the phone. Automatic setup does not make those physical actions automatic.

## Option 1 — Automatic setup with a local AI agent

Choose this if you want your agent to handle the computer work. It must run on
**the laptop you will connect to the car**. A browser-only chat cannot access
that laptop's USB port. You do not need to install Python, ADB, Git or Android
Studio beforehand; the agent's guide covers finding or installing the needed tools.

**You still enter the car's dialer code and PINs, tap its menus and approve its
permissions.** The AI handles the laptop commands; follow the car steps below
when it asks.

**Copy this message to your local agent:**

```text
Set up wired Android Auto using this repository:
https://github.com/teymurl3ng/oshan-x7-2025-android-auto
Read AGENTS.md, README.md, docs/agent-setup.md, docs/car-menu.md and docs/recovery.md.
Handle the laptop preparation yourself, including missing Python/ADB. Check exact
compatibility, then use the supported setup with its Android reboot check.
Verify each stage before continuing. Use the unified recovery if a stage fails;
keep the original backup. Ask me for car-menu actions, cables, visible permissions
and actual phone/native-control tests. Do not ask me to run routine commands.
Give me the exact dialer code, PINs and Chinese menu labels when guiding those
car steps; do not replace the instructions with a documentation link.
Keep software checks separate from what we actually see and hear in the car.
```

**Your agent handles:** downloads, tool installation, USB diagnosis, firmware
checks, the backed-up installer, stage verification, the Android reboot check
and guarded recovery. [Detailed agent workflow](docs/agent-setup.md).

**Your car steps — including in AI mode:**

1. Park and keep the headunit powered. On the **car's built-in Phone / Bluetooth
   phone dial pad**, enter **`*#*#888`** and tap **Call**. At the black factory
   PIN keypad, enter **`1111`**. The menu opens after the fourth digit.
2. Select **`开发模式` (Development mode)** in the factory menu. If another PIN
   keypad appears, it is a separate gate: its saved factory-code default is
   **`3821`**. **1111 worked on my car. 3821 was found in the saved app's code;
   we have no recorded test of entering it on the car.** A changed development
   password can override that default. If it is rejected, stop and tell your agent.
3. Tap **Settings** beside the USB-role control. In Android settings, open
   **System → Advanced → Developer options** (labels may read
   **`系统` → `高级` → `开发者选项`**) and enable **USB debugging / `USB 调试`**.
   If Developer options is hidden, tap **Build number** seven times under
   **About device / About tablet**, then return. Accept the debugging confirmation.
4. Return to the factory **`开发模式`** page. Tap the USB-role control only if
   needed until it shows **`Device模式`**. Keep it in Device mode while the
   laptop runs setup and the normal Android reboot check. **`重启`** means
   Reboot; you do not need to tap it here.
5. Connect the laptop directly to the car with a suitable USB data cable. Accept
   **Allow USB debugging** on the car for your trusted laptop. Tell the agent it
   is connected; it checks ADB and compatibility. Approve any unavoidable trusted
   laptop-installer prompt when asked.
6. When OpenHU opens, complete its onboarding: **USB**, **right-hand drive**,
   landscape. My reference choices were about **10 inches, 180 DPI and phone GPS**.
   Accept the visible app permissions. If setup pauses for a permission, tell the
   agent after accepting it; the agent resumes the same backed-up setup.
7. After the agent verifies setup and the Android reboot, check the large Android
   Auto card, Home and your usual native controls. Then follow
   [the phone test below](#both-options-connect-the-phone-and-test): disconnect
   the laptop, select **Host模式**, connect the phone to the recording USB port
   and accept the car/phone prompts.

[Car-menu screenshots and full screen reference](docs/car-menu.md) are available
if you need to identify a screen. You carry out these car steps while the
agent prepares and runs the laptop side of setup.

**You can skip Option 2.** It is the alternative for people running the computer
steps themselves.

## Option 2 — Manual setup

Choose this if **you will prepare the laptop and run the commands yourself**.
The installer still performs the checked car changes automatically; manual here
means you run it without an AI agent. You do not need to copy raw ADB/root commands.

### 1. Download the project and prepare the laptop

Download [the repository ZIP](https://github.com/teymurl3ng/oshan-x7-2025-android-auto/archive/refs/heads/main.zip)
and extract it, or use an existing Git checkout. Keep any existing `.oshan-x7`
folder: that is your original settings and recovery journal.

Install **Python 3.10 or newer** if needed, using the official
[Windows](https://www.python.org/downloads/windows/) or
[macOS](https://www.python.org/downloads/macos/) installer, or your Linux package
manager. [More host-tool help](docs/agent-setup.md#2-find-or-install-python).
No Android Studio, Java or pip packages are needed.

Open a terminal **inside the extracted project folder**. On Windows, use
PowerShell. Run the commands for your operating system:

**Linux / macOS**

```sh
python3 --version
python3 prepare.py
```

**Windows PowerShell**

```powershell
py -3 --version
py -3 prepare.py
```

Confirm Python reports 3.10+. Preparation finds ADB or downloads Google's official
Platform Tools and verifies that it runs. If preparation fails, fix that before
continuing. If the car CLI later cannot find the prepared ADB, use its returned
path with `--adb "path to adb"`. [Command options](docs/reference.md#host-tools-and-command-options).

### 2. Put the car in Device mode and connect the laptop

1. On the **car's built-in Phone dial pad**, enter **`*#*#888`**, tap **Call**,
   then enter **`1111`** at the black factory PIN keypad.
2. Open **`开发模式` (Development mode)**. If a second PIN keypad appears, the
   saved factory-code default is **`3821`**. The outer **1111** worked on my car;
   **3821** was found in the saved app's code, with no recorded live entry test.
   A changed password can override it. Stop if rejected; do not guess.
3. Tap **Settings**. In Android settings, open **System → Advanced → Developer
   options** and enable **USB debugging / `USB 调试`**. If Developer options is
   hidden, tap **Build number** seven times under **About device / About tablet**,
   then return. Accept its confirmation.
4. Return to factory **`开发模式`** and leave the USB-role control showing
   **`Device模式`**. Tap it only if it needs changing.

[Car-menu screenshots and Chinese label reference](docs/car-menu.md).

Connect the laptop directly to the car using a suitable USB data cable. Accept
**Allow USB debugging** on the car; choose “Always allow from this computer” only
for your own trusted laptop. Disconnect other phones from the laptop.

**Keep Device mode and the laptop cable throughout installation and the Android
reboot check.** If the car is not detected or is unauthorized, resolve that first.
[Connection help](docs/reference.md#connection-help).

### 3. Check compatibility before installing

**Linux / macOS**

```sh
python3 oshan_x7.py check
```

**Windows PowerShell**

```powershell
py -3 oshan_x7.py check
```

Continue only when the result says **`"compatible": true`** and the command
succeeds. Unknown firmware, launcher builds or receiver versions stop setup.
Do not bypass a failed check. Retain the same ADB options and state directory
for all later setup/status/restore commands.

### 4. Install and verify, including a normal Android reboot

The next command backs up the original state, installs OpenHU if absent, disables
CarAuto, saves fullscreen and installs the exact tested launcher update. It
checks each stage and performs a **normal Android reboot** while USB stays connected.
It attempts guarded recovery if a stage fails. [What restore covers](docs/recovery.md).

Watch the car while it runs. Accept OpenHU's visible permission prompts. If the
result is **`waiting_for_permissions`** (exit 3), accept that car prompt and rerun
**the same command below**. Keep the existing backup and Device mode.

**Linux / macOS**

```sh
python3 oshan_x7.py setup --reboot-check
```

**Windows PowerShell**

```powershell
py -3 oshan_x7.py setup --reboot-check
```

Complete OpenHU's visible onboarding: **USB**, **right-hand drive**, landscape.
My receiver choices were about **10 inches, 180 DPI and phone GPS**. If a different
screen blocks progress, inspect it rather than repeatedly launching the app.

Continue only when setup reports **`configured`** or **`already_configured`**,
**`android_reboot_verified: true`** and **`next_action: phone_handoff`**. If it
reports an error or incomplete recovery, keep the journal and follow
[recovery.md](docs/recovery.md) before a phone test.

Before disconnecting, check that the large Android Auto card opens OpenHU, factory
Home returns to the edited launcher, duplicate small OpenHU/launcher icons are
absent, and your usual radio/music, AC, phone and settings controls respond.

## Both options: connect the phone and test

After the successful laptop stages and native-control checks:

1. **Disconnect the laptop.** To reopen the factory menu if needed, use the
   **car's Phone dial pad → `*#*#888` → Call → `1111` → `开发模式`**. If its
   separate development PIN is requested, the code-inspected default is **`3821`**,
   with the evidence/change-password limits described above. Select **`Host模式`**.
2. Connect the Android phone directly to the car's **video-recording USB port**
   with a data cable. Open the large **Android Auto** card and choose USB in OpenHU.
3. On the **car**, allow OpenHU's USB-device/access prompt; select its always-use
   option if offered. On the **phone**, unlock it and accept Android Auto setup
   and permission prompts. Exact wording varies by phone/software.
4. Test Maps, sound and touch. Press factory Home, reopen the large Android Auto
   card, then disconnect/reconnect the phone once. Check your usual native controls.

| Connection | Car USB role | What stays disconnected |
| --- | --- | --- |
| Laptop → car: install, Android reboot check or restore | **Device模式** | Phone |
| Phone → car: Android Auto | **Host模式** | Laptop |

The recording port worked on my car; the ordinary port repeatedly disconnected,
including after about **10–15 seconds with the same cable**. Repeated USB prompts
can accompany connection resets. Check Host mode, a data cable and the recording
port before repeatedly changing permissions. The underlying cause is unresolved.
A complete physical port/cable map was not recorded; identify your actual
connectors rather than assuming a position or cable type.

Optional: **OpenHU Settings → General → Show toast messages → Off → Save** removed
the large routine reconnect popup on my car. This visible app preference is
outside installer/restore ownership. Forced error messages can still appear.

**Known limits:** microphone/Gemini recognition remains unresolved, including the
native assistant. Wireless after disabling CarAuto and cold ignition cycles are
untested. The small factory Home/Back overlays stay and can cover some AA controls.
A successful installer result does not establish working phone projection or
exhaustive vehicle-function testing. [Actual test evidence](docs/verified-findings.md).

## Undo the setup — either option

Restore uses the **same repository and `.oshan-x7` folder** (or original custom
`--state-dir`). Disconnect the phone, select **Device模式** and reconnect the laptop.

**Automatic option:** ask your local agent to run the repo's unified restore with
your original backup, verify each recovered component and report anything blocked.

**Manual option:** run the command for your operating system in the repo folder:

**Linux / macOS**

```sh
python3 oshan_x7.py restore
```

**Windows PowerShell**

```powershell
py -3 oshan_x7.py restore
```

One restore covers the changes owned by that setup cycle: launcher update,
fullscreen behavior, CarAuto state and a newly installed receiver. Preexisting
apps remain; manually chosen receiver/phone settings are outside the journal.
A partial restore reports what is blocked and can be retried. Keep the backup.
[Full recovery guide](docs/recovery.md).

Recovery requires responsive Android, package management and authorized USB ADB.
Supervision ends when the laptop is unplugged. Regaining Device mode from Host
with an unusable launcher has not been qualified. [Pending car tests](docs/testing.md).

## More details

| Guide | Purpose |
| --- | --- |
| [Before/after screenshots](docs/screenshots.md) | Original layout, fullscreen result, launcher and app-menu changes |
| [Agent workflow](docs/agent-setup.md) | Laptop preparation, stage decisions and verification for Option 1 |
| [Car screens](docs/car-menu.md) | Exact menus, Chinese labels, roles, prompts and cables for either option |
| [Recovery](docs/recovery.md) | One restore, interrupted runs and recovery boundaries |
| [Reference](docs/reference.md) | Compatibility, CLI options and machine-readable states |
| [Launcher](docs/launcher.md) | Pinned patch, source changes and ownership |
| [Verified findings](docs/verified-findings.md) | Live evidence, owner reports, code findings and unknowns |
| [Testing](docs/testing.md) | Offline checks and the outstanding live test |

Credit to **[Open Headunit](https://github.com/andreknieriem/open-headunit)** and its
maintainers. Setup downloads their official 3.5.0/code119 APK and verifies its
checksum. Only the pinned launcher patch and reviewed screenshots are published;
full APKs, signing keys and private backups stay private. I'm not affiliated with
Changan or Google. Installer code and documentation use the [MIT license](LICENSE).
[Contributing](CONTRIBUTING.md).
