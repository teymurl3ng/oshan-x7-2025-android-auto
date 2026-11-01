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

Use a local AI coding agent on the laptop you will connect to the car.
[Download this repository](https://github.com/teymurl3ng/oshan-x7-2025-android-auto/archive/refs/heads/main.zip),
extract it, open the folder in the agent, and give it this instruction:

> Set up this repository on my Oshan X7. Read AGENTS.md and the linked runbooks.
> Prepare Python and ADB on this laptop, run the read-only compatibility check,
> then run the guarded setup with its Android reboot check. Handle the automatic
> CarLink permissions, fullscreen and launcher update. Preserve the original
> backup and journal. Ask me only for physical car/USB actions, unavoidable OS
> authorization and actual phone/control tests. Stop on compatibility mismatches.

The agent handles laptop tools and runs the installer. You operate the car:

1. Park the car and keep it powered. Open **Phone → `*#*#888` → Call → `1111` →
   `开发模式`**. The outer PIN **1111** worked on the reference car. If the
   development page asks separately, its code-only default is **3821**; that
   separate PIN has no recorded live-entry test and may have been changed.
   Stop if rejected.
2. Enable **Settings → System → Advanced → Developer options → USB debugging /
   `USB 调试`** if needed. If Developer options is hidden, tap **Build number**
   seven times in About device/tablet.
3. Return to `开发模式`, select **Device模式**, connect the laptop with a data
   cable and accept its debugging authorization. Keep Device mode selected
   through installation and the normal Android reboot check.

[Car menu labels and pictures](docs/car-menu.md) · [Agent runbook](docs/agent-setup.md).

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

1. Download/extract the repository and install **Python 3.10+** from
   [python.org](https://www.python.org/downloads/) if needed.
2. Follow the car menu/debugging steps in Automatic installation above. Connect
   the laptop in **Device模式** and authorize it.
3. Open a terminal in the extracted repository folder and run:

   ```sh
   python3 prepare.py --json
   python3 oshan_x7.py check --json
   python3 oshan_x7.py setup --reboot-check --json
   ```

   On Windows, use **`py -3`** instead of `python3`. Preparation finds or downloads
   ADB locally. Stop if `check` reports a mismatch. Add `--adb`, `--adb-port`,
   `--serial` or `--state-dir` only as needed, and reuse them for later commands.
4. Keep the laptop connected until the reboot check finishes. Then follow
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
