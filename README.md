# Oshan X7 · Android Auto

I got **wired Android Auto working in full screen on my 2025 Changan Oshan X7**.
I'm putting the steps and scripts here so the next person doesn't have to figure
all of this out again.

Getting there took a bit of trial and error. Wireless was laggy, USB kept throwing
connection prompts, and even when Android Auto worked, the factory interface left
big bars on both sides. I ended up using **Open Headunit**, disabling the original
**CarAuto** app, and saving the factory's per-app fullscreen setting. Wired AA now
works on my car, and the changes survived a normal Android reboot.
[See the before-and-after screenshots](#screenshots-from-my-car).

I also changed the factory launcher's large **Connection / CarAuto** card into
an **Android Auto / Open Headunit** button. It opens the receiver directly, with
the duplicate small OpenHU tile and unwanted launcher entries hidden. Music,
Radio, Bluetooth phone and the factory Home button keep their usual roles.
[See the launcher before and after](#android-auto-on-the-factory-home-screen).

I've included an agent-friendly setup as the first option below. The script
checks the headunit before changing anything, installs this tested launcher
update automatically as part of setup, and keeps a backup so you can undo its
changes. There is no separate launcher installation step.

## Option 1 — Let your AI agent handle it

This is the easiest place to start if you already use a local AI agent. Give it
access to the **laptop you will connect to the car**. I've included instructions
for it to check and install Python and ADB, so you don't need to set those up
beforehand. You don't need Git or Android Studio either.

**Copy this to your agent:**

```text
Set up wired Android Auto on my 2025 Oshan X7. Read and follow AGENTS.md in this repo:
https://github.com/teymurl3ng/oshan-x7-2025-android-auto
```

Let the agent handle the downloads and commands. You'll still need to tap the
car's screen, connect the cables, and approve any computer permission prompts.
A browser-only chat won't have access to your laptop's USB port.

**To find the car's developer settings:** open its built-in **Phone → dial pad**,
enter **`*#*#888`**, tap **Call**, then enter **`1111`** at the factory PIN screen.
I've put the next taps, Chinese labels, and screenshots from my car in the
[car-screen guide](docs/car-menu.md).

## Option 2 — Set it up yourself

If you'd rather run the commands yourself, here's the same process without an agent.

1. Park the car and keep the headunit powered. Follow the
   [car-screen guide](docs/car-menu.md) to enable USB debugging and select
   **USB Device mode** for the laptop.
2. [Download the repository ZIP](https://github.com/teymurl3ng/oshan-x7-2025-android-auto/archive/refs/heads/main.zip)
   and extract it. If you use Git, you can clone this repo instead.
3. Check that **Python 3.10+** is installed. If needed, use the official
   [Windows](https://www.python.org/downloads/windows/) or
   [macOS](https://www.python.org/downloads/macos/) installer; on Linux, use your
   distribution's package manager.
4. Open a terminal **inside the extracted repository folder** and run the
   preparation command below. It finds ADB or downloads Google's official copy.

   **Linux / macOS**

   ```sh
   python3 prepare.py
   ```

   **Windows PowerShell**

   ```powershell
   py -3 prepare.py
   ```

   No Android Studio or `pip` packages are needed.
5. Connect the laptop to the car with a suitable **USB data cable** and accept
   **Allow USB debugging** on the car if shown. Disconnect phones from the laptop.
6. Run setup in the same terminal:

   ```sh
   python3 oshan_x7.py setup
   ```

   On Windows, use `py -3 oshan_x7.py setup`.

If it can't find your car, I've collected the common causes in
[connection help](docs/reference.md#connection-help).
For a read-only compatibility check, run `python3 oshan_x7.py check` (Windows:
`py -3 oshan_x7.py check`).

Setup checks the exact firmware, immutable factory launcher, active launcher
identity and default Home activity first. It then installs Open Headunit if
needed, disables CarAuto, saves fullscreen behavior and installs the tested
launcher as an Android app update. It keeps the original system APK in place.
Unknown firmware or launcher builds stop the process.

## Start Android Auto after setup

1. Complete **Open Headunit** onboarding on the car. Choose **USB**, allow its
   requested permissions, and use **right-hand drive**. On my car I used
   landscape, about 10 inches, **180 DPI**, and phone GPS.
2. Disconnect the laptop. In the factory menu, switch the USB role to
   **`Host模式` (Host mode)**. [See the exact menu labels](docs/car-menu.md#switch-to-host-for-the-phone).
3. Connect your Android phone directly to the car with a data cable. Accept the
   phone's Android Auto prompts and Open Headunit's USB access prompt.
4. Check the picture, audio, touch, voice input, and access to normal car controls.
   Check again after a normal reboot.
5. Press factory **Home** and try the large **Android Auto** card. It should open
   Open Headunit, and Home should return to the edited launcher.

This USB-role switch caught me out during testing: the shared port needs
**Device mode for the laptop** and **Host mode for the phone**.
The little factory Home/Back buttons still stay on screen. On mine, the Home
button overlaps some Android Auto controls; I left that alone for now.

On my car, wired AA stayed connected using the **video-recording USB port**.
The other port repeatedly disconnected, including after about 10–15 seconds.
If that happens, try the recording port with the same data cable. The cause of
that port difference is unresolved. **Gemini/microphone recognition is also
unresolved on my car**; this launcher update does not fix voice input.

## Android Auto on the factory Home screen

The factory Home screen had a large CarAuto card even after Open Headunit was
installed. Opening AA meant using its smaller app tile instead. This update
gives that large card to Android Auto, removes the redundant small OpenHU tile,
and hides the launcher/test-launcher entries from the app menu. It keeps the
existing Music, Radio and Bluetooth layout, including the factory Home overlay.

**Before:** the original Connection / CarAuto card, with OpenHU as a small tile.

![Factory Home screen with the large CarAuto card and smaller Open Headunit tile](docs/images/launcher-before.png)

**After:** the large Android Auto card opens Open Headunit directly. The small
duplicate is gone. This capture was taken after a normal Android reboot.

![Edited factory Home screen with the large Android Auto card and no duplicate OpenHU tile](docs/images/launcher-after.png)

The app menu also keeps its native entries without a second launcher icon:

![App menu after cleanup, showing file management, settings, voice assistant and car recorder](docs/images/launcher-app-menu.png)

These are actual launcher captures from my car, not pictures of an active AA
session. I separately tested the large card, Home return, usual native controls
and wired AA. The unified installer still needs its own full live setup/restore
test. [Launcher details, checks and recovery](docs/launcher.md).

## Screenshots from my car

These are the same Open Headunit main screen before and after I changed the
factory fullscreen setting.

**Before:** the app used the middle 1280×720, with the factory panels taking up
both sides of the 1920×720 display.

![Open Headunit before the fullscreen change, between the factory side panels](docs/images/open-headunit-before-fullscreen.png)

**After:** the app fills the full 1920×720 width. The small factory Home button
still sits over the bottom-left corner.

![Open Headunit filling the display after the fullscreen change](docs/images/open-headunit-fullscreen.png)

These captures show Open Headunit's main screen. I checked Android Auto's full
width separately with my phone connected.

## Undo the setup

Keep the `.oshan-x7` folder: it contains your original settings and restore journal.
Switch back to **Device mode**, reconnect the laptop, and run from the same folder:

```sh
python3 oshan_x7.py restore
```

On Windows, use `py -3 oshan_x7.py restore`. If setup was interrupted, reconnect
and run restore before trying a new setup. [Backup and recovery details](docs/reference.md#backups-and-recovery).

Restore first removes the launcher update **only if this setup cycle installed
it**, returning to the untouched factory APK while retaining launcher data. A
launcher update that was present before setup is kept. CarAuto, fullscreen and
receiver ownership are then restored from the same saved journal.

## What I've tested, and what I haven't

My car is a **2025 Changan Oshan X7**, right-hand drive, with an **F202_MCA /
Android 9** headunit running **`F202RHD_D1_20241022162756`**. That's the setup I
have evidence for. I don't want someone trying this on a different unit just
because it also says Oshan X7, so the script checks the firmware, MCU, hardware,
screen, and original launcher hash. It stops if they don't match.
[Full compatibility details](docs/reference.md#compatibility).

I've tested the individual changes on my car: wired Android Auto works on the
recording USB port and fills the width. The exact launcher build included here
was installed and its icons, large card and Home return survived a normal
Android reboot. The earlier launcher also passed a factory rollback/reinstall
test. **The unified v0.2 installer has not yet completed a full setup-and-restore
cycle on the car.** Its software tests pass; that is a separate check. I haven't
tested a cold ignition/power-off cycle or exhaustively tested every car function.

**I also haven't tried wireless again since disabling CarAuto.** It might be
worth investigating, but I can't tell you it works. After setup, check the actual
picture, audio, and controls on your own car; a successful command isn't that test.

## More help

- [Car-screen guide, Chinese labels, and actual PIN-screen image](docs/car-menu.md)
- [Agent workflow: install missing tools and complete the setup](docs/agent-setup.md)
- [Compatibility, connection help, commands, and recovery](docs/reference.md)
- [Verified findings](docs/verified-findings.md) · [Testing](docs/testing.md) · [Contributing](CONTRIBUTING.md)

Credit for the Android Auto receiver goes to
**[Open Headunit](https://github.com/andreknieriem/open-headunit)** and its maintainers.
I used **3.5.0 / code 119** here; the script downloads that official APK and checks
its checksum. The launcher patch is applied locally to the exact factory APK
read from the car, producing the pinned tested update. Full factory/modified
APKs and device backups stay private; only the patch and reviewed screenshots
are included here. Open Headunit itself still comes from its official release.

I'm not affiliated with Changan or Google. My installer code and documentation
are available under the [MIT license](LICENSE).
