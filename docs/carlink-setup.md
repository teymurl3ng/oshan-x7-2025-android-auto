# Manual installation

These instructions use the same installer as the AI-assisted workflow. Start on
the laptop you will connect directly to the car. You need internet access for
tools and the CarLink download, and a suitable USB data cable.

Check the [supported firmware](reference.md#exact-compatibility). The installer
uses the head unit's existing factory root access (`su 0`); it does not install
root or flash firmware.

## 1. Prepare the laptop

[Download and extract the repository ZIP](https://github.com/teymurl3ng/oshan-x7-2025-android-auto/archive/refs/heads/main.zip),
or reuse your existing copy. Keep any existing `.oshan-x7` folder and custom
backups. Git is not required.

Install [Python 3.10+](https://www.python.org/downloads/) if necessary. Open a
terminal in the repository folder. Commands below use `python3`; on Windows,
use `py -3` or the full path to your working Python executable.

```sh
python3 -c "import sys; print(sys.executable); print(sys.version); raise SystemExit(sys.version_info < (3, 10))"
python3 prepare.py --json
```

Preparation finds or downloads ADB, the tool used to communicate over USB. It
prints the verified executable's path. Use that path with `--adb` in subsequent
commands; it does not need to be added to PATH. See [tool setup](agent-setup.md#2-prepare-python-and-adb)
if preparation fails.

## 2. Connect the laptop to the car

Park the car and keep it powered. Leave your phone disconnected. If this laptop
already has working, authorized USB access, skip the menu steps.

1. On the **car's Phone dial pad**, enter **`*#*#888`**, tap **Call**, then enter
   **`1111`**. Open **`开发模式` (Development mode)**.
2. If that page separately asks for a PIN, its default in the factory app's code
   is **`3821`**. I have not tested entering this second PIN on the car; a changed
   password can override it. Stop if rejected.
3. Tap **Settings**, then Android **System → Advanced → Developer options** and
   enable **USB debugging / `USB 调试`**. If Developer options is hidden, tap
   **Build number** seven times in **About device/tablet** first.
4. Return to `开发模式`, select **Device模式**, connect the laptop with a USB data
   cable, and accept **Allow USB debugging** for this trusted laptop if prompted.

[Car menu pictures](car-menu.md) show the controls. Keep **Device模式** selected
throughout installation and the Android reboot. If the laptop cannot see an
authorized device, resolve the [USB connection](usb-reliability.md#laptop-cannot-connect)
before proceeding.

## 3. Check and install

Replace `/path/to/adb` with the executable returned by preparation:

```sh
python3 oshan_x7.py check --adb "/path/to/adb" --json
```

Stop if the check reports a mismatch. If compatible, run:

```sh
python3 oshan_x7.py setup --reboot-check --adb "/path/to/adb" --json
```

If you need `--adb-port`, `--serial` or `--state-dir`, pass the same values to
check, setup, status and restore. [Command reference](reference.md).

Setup downloads and verifies **CarLink 1.0.7**, saves original settings and the
factory launcher, then:

1. Checks that factory Home opens correctly.
2. Installs CarLink if absent, grants its permissions automatically and checks
   that the app opens.
3. Disables CarAuto and sets CarLink's fullscreen layout.
4. Installs the verified launcher update with the large CarLink card.
5. Checks the resulting settings and verifies them again after an Android reboot.

The factory launcher APK and Home/Back overlays remain. Setup uses no network
ADB or Google services. [Permission scope](permissions.md) · [Launcher details](launcher.md).

Keep the laptop connected until the command finishes. Normal CarLink permissions
need no manual walkthrough. If setup pauses on an unexpected permission screen,
inspect the screen and diagnose the missing access before responding. A failed
setup may automatically restore its changes; that is not a completed installation.
Use the reported status and [recovery guide](recovery.md).

For a previously downloaded CarLink APK, add `--apk /path/to/CarLink-1.0.7.apk`.
It must match the same [release hash and size](reference.md#artifact-pins).

## 4. Check the result and connect your phone

Proceed only when setup reports `android_reboot_verified=true` and
`next_action=phone_handoff`. Keep the laptop connected while you check the large
card, Home return and available native controls. Complete any welcome/car
settings CarLink shows; if it reaches phone pairing, continue after connecting
your phone. Inspect the actual options rather than guessing a profile.

Then follow [Connect your phone](../README.md#connect-your-phone): disconnect
the laptop, select Host mode and connect/pair the phone. Test projection and
controls yourself; an app launch is not a phone test.

Keep the reported backup folder. Installation normally uses `.oshan-x7` beside
the script. [Restore instructions](recovery.md) explain how to reconnect the
laptop and undo this installation.
