# Oshan X7 · CarPlay + Android Auto

**Official CarLink, fullscreen, launched from the large factory Home card.**
Tested on the reference right-hand-drive Oshan X7 with a **1920 × 720** display.
The large CarLink card and factory Home return work.

![Factory Home with the large CarLink card](docs/images/launcher-carlink.png)

![Fullscreen CarPlay](docs/images/carplay-fullscreen.png)

![Fullscreen Android Auto](docs/images/android-auto-fullscreen.png)

The installer supports only the verified **F202_MCA, Android 9/API 28** unit,
firmware **F202RHD_D1_20241022162756**, MCU **F202RHD_20240722_1**, with its existing
`su 0` access. It checks exact firmware, launcher hashes/UID/Home, apps and USB.
A matching badge/year is insufficient. [Compatibility details](docs/reference.md).

## Automatic installation

On the laptop you will connect to the car, open a local AI coding agent with
terminal and internet access. **Paste this prompt to start.** The agent downloads
the project, gets any missing tools, checks the car and runs the installation.

```text
Install CarLink on my Oshan X7 using this project:
https://github.com/teymurl3ng/oshan-x7-2025-android-auto

Do the computer work yourself, from downloading the project through setup and
verification. Guide me through the parts that require my hands, one step at a time.

1. Inspect this laptop's OS/CPU and local USB access. Look for an existing copy
   of this project and its private backup first; preserve and reuse them. Otherwise
   download the project into a writable folder. Use Git if it already works, or
   download and extract this ZIP with the host's available tools:
   https://github.com/teymurl3ng/oshan-x7-2025-android-auto/archive/refs/heads/main.zip
   Handle the download and extraction yourself; Git is optional.

2. Read AGENTS.md, docs/agent-setup.md, docs/car-menu.md, docs/permissions.md and
   docs/recovery.md from that copy. Find and execute Python to verify 3.10+;
   install it if missing or too old. Install missing tools/dependencies from
   the trusted sources in the runbook. Run prepare.py --json to find or download
   ADB and verify the returned tools. Diagnose driver, USB or tool failures
   yourself. If an OS approval needs my action, explain exactly what I must
   approve and wait for that action.

3. Guide me through the car connection only when the laptop is ready. Ask for
   one physical action at a time, naming the device, screen and control. Wait
   for my reply or verified device read-back before the next action. Skip steps
   already completed; do not ask me to repeat working USB/debugging setup.
   Use these instructions inline when needed:
   - Park the car and keep it powered. On the car's Phone dial pad enter
     *#*#888, tap Call, enter the outer PIN 1111, then open 开发模式.
   - If that development page separately asks for a PIN, its code-only default
     is 3821. Outer 1111 worked on the reference car; separate 3821 has no
     recorded live-entry test and may have been changed. Stop if rejected.
   - Enable Settings → System → Advanced → Developer options → USB debugging
     (USB 调试) if needed. If Developer options is hidden, tap Build number
     seven times in About device/tablet first.
   - Return to 开发模式, select Device模式, connect this laptop by USB data cable,
     and have me accept its debugging authorization if shown.

4. Verify authorized USB access, then run check --json using oshan_x7.py. Stop
   on firmware/app/launcher mismatches and explain them; do not bypass checks.
   Use only the firmware's existing root; do not root/flash or enable network ADB.
   If compatible, run setup --reboot-check --json. Let the installer download
   and verify its app/launcher artifacts, save backups, configure permissions,
   fullscreen and the large Home card, and verify the Android reboot.
   Keep the same interpreter, ADB path/port, USB target and state directory.
   Keep the laptop connected in Device mode until these checks finish. Diagnose
   failures and use the original journal's recovery flow if needed; never
   replace an interrupted backup with a new baseline.

5. When installation and reboot checks pass, guide me through disconnecting
   the laptop, selecting Host模式 and connecting my phone to the regular
   charging/CarAuto USB port. Walk me through any car/profile onboarding or
   phone prompts that still need my action. A car-side USB prompt may still
   need tapping; do not claim every prompt is automated. Have me test projection,
   fullscreen, the large CarLink card, Home return, sound and native controls.
   Finish by reporting what passed, what remains untested, and the exact backup
   location and recovery instructions. Do not call an app launch a phone test.
```

The agent should handle downloads, commands and routine troubleshooting. Your
part is entering car codes, connecting cables, approving requests that need a
person and testing the result. It should explain each action when it is needed.
[Car menu pictures](docs/car-menu.md) · [Agent runbook](docs/agent-setup.md).

Setup installs the unchanged **official CarLink 1.0.7 APK**, grants its Android 9
runtime/special access automatically, disables the competing factory CarAuto
receiver, applies fullscreen and installs the pinned large-card launcher update.
It preserves the factory system APK and Home/Back overlays. It does not root or
flash the car, enable network ADB or install Google services.

Keep the private **`.oshan-x7`** folder, or the custom state directory used by
the agent. It contains the original settings and recovery journal. The direct
fresh-install workflow is tested offline; a complete fresh setup/restore cycle
still needs live qualification. [Setup details](docs/carlink-setup.md).

## How to use

After the laptop-side checks finish:

1. Disconnect the laptop, select **Host模式** in `开发模式`, and open the large
   **CarLink / CarPlay + Android Auto** card.
2. For a cable connection, use a data cable in the **regular charging/CarAuto
   USB port**. This is the working port in the current CarLink tests.
3. Complete CarLink's car/profile onboarding if shown, using right-hand drive.
   Accept the phone's own pairing/trust prompts. A car-side USB access prompt
   can still need a tap; the enabled auto-confirm service has not handled every
   observed prompt.
4. Use the factory **Home** button to return to the car launcher. Check sound,
   touch, radio/music, AC, phone and settings controls with your own phone.

| Connection | Reference-car result |
| --- | --- |
| iPhone CarPlay with cable | Owner reports working perfectly |
| iPhone wireless CarPlay | Owner reports working perfectly |
| Android Auto with cable | Working; fullscreen confirmed |
| Android Auto wirelessly | Unreliable in the owner's tests; use a cable for the reliable path |

For wireless CarPlay, keep the iPhone's Bluetooth and Wi-Fi enabled and complete
CarLink's on-screen pairing. These are owner-observed results, not a long-duration
reliability qualification. Microphone/Siri/call audio and cold ignition cycles
remain separate tests. [Evidence and limits](docs/verified-findings.md).

For later laptop work, disconnect the phone, return to **Device模式**, and
reconnect the laptop. Reuse the original state directory and connection options.

## Manual installation

Without an AI agent, run the same guarded installer yourself:

Commands below use **`python3`**. On Windows, use **`py -3`** instead.

1. [Download and extract the repository](https://github.com/teymurl3ng/oshan-x7-2025-android-auto/archive/refs/heads/main.zip).
   Install **Python 3.10+** from
   [python.org](https://www.python.org/downloads/) if needed.
2. Open a terminal in the extracted repository folder and prepare ADB:

   ```sh
   python3 prepare.py --json
   ```

   Preparation finds or downloads ADB locally.
3. Park the car and keep it powered. On its **Phone** dial pad enter
   **`*#*#888` → Call → `1111` → `开发模式`**. If the development page asks for
   its separate PIN, the code-only default is **3821**; that separate PIN has
   no recorded live-entry test and may have been changed. Stop if rejected.
4. Enable **Settings → System → Advanced → Developer options → USB debugging /
   `USB 调试`** if needed. If Developer options is hidden, tap **Build number**
   seven times in About device/tablet. Return to `开发模式`, select
   **Device模式**, connect the laptop with a USB data cable and accept its
   debugging authorization. [Car menu pictures](docs/car-menu.md).
5. Check compatibility:

   ```sh
   python3 oshan_x7.py check --json
   ```

   Stop if the check reports a mismatch. If the car is compatible, run:

   ```sh
   python3 oshan_x7.py setup --reboot-check --json
   ```

   Add `--adb`, `--adb-port`, `--serial` or `--state-dir` only as needed, and
   reuse them for later commands.
6. Keep the laptop connected until the reboot check finishes. Then follow
   **How to use** above. CarLink permissions are included in setup; there is no
   separate permission command.

The installer downloads and verifies the official APK itself. For an already
downloaded copy, add `--apk /path/to/CarLink-1.0.7.apk` to `setup`; the same exact
release hash is required. [Artifact pins and stages](docs/carlink-setup.md).

To inspect or recover, reconnect in Device mode and reuse the original backup:

```sh
python3 oshan_x7.py status --json
python3 oshan_x7.py restore --json
```

Restore reverses only recorded changes and preserves preexisting apps and
unrelated accessibility services. Recovery requires responsive Android/package
management and authorized USB. Returning to Device mode with an unusable
launcher/menu remains unqualified. [Recovery guide](docs/recovery.md).

[Reference screenshots](docs/screenshots.md) · [Automatic permissions](docs/permissions.md) ·
[Launcher](docs/launcher.md) · [Testing](docs/testing.md) · [Contributing](CONTRIBUTING.md)

Credit to [CarLink](https://github.com/F-e-n-y-x/CarLink) and its DiPlay/DiAuto
components. Original installer code/docs use [MIT](LICENSE); upstream software
retains its own licensing. [Third-party notices](THIRD_PARTY_NOTICES.md).
APKs, signing keys, phone data and private backups are not published.
