# What I found while getting this working

These are my notes behind the setup, written up on 2026-10-26. They come from the
saved ADB output, screenshots, app inspection, and what I tested in the car. I've
kept the raw private dumps out of the repo and kept track of which results came
from the device and which came from looking at its software.

## Vehicle and firmware

My car is a **2025 Changan Oshan X7**. Its headunit reports
`F202_MCA`, `alps`, `spm8666p1_64`, MediaTek `mt6771`, Android 9 /
API 28, firmware `F202RHD_D1_20241022162756`, MCU `F202RHD_20240722_1`, and a 1920×720
physical display. The exact remaining properties are in the public profile.
These are the values read from my headunit, rather than specs assumed from the badge.

I kept an unmodified copy of the factory launcher. Its complete APK hash was
checked against the copy on the car. Here are its details:

- Package: `com.chinatsp.launcher`
- Version: `C_2024072610` / code `20240726`
- Path: `/system/app/F202_Launcher/F202_Launcher.apk`
- Bytes: `8256512`
- SHA-256: `0c50bad53fa2116e98928c74be78e1b9609a1d3f73d3ee42726b001ae7ddefb0`

I use this hash as another compatibility check. It doesn't prove every other
firmware file is identical. The saved SystemUI APK copy was incomplete, so I
haven't used its partial-file hash as if it were the full app's hash.

## Receiver and wired connection

The app I ended up with is **Open Headunit 3.5.0**, code **119**, GitHub flavor,
upstream commit `1c1b5b7261eb`, package `com.andrerinas.headunitrevived`.
The installed package is confirmed in the device records; you don't need the
separate Headunit Reloaded app.

The [official release](https://github.com/andreknieriem/open-headunit/releases/tag/v.3.5.0)
APK was checked against the release-asset digest:

```text
609ca23b4eb0deaad2a58f6463b26cbf58bdc602ac0775eb5e7adb293a75a14d
```

Its recorded size is `13903086` bytes. It installed as a normal user app.
I heard the speaker test, and wired AA worked without the lag I'd had over wireless.

After I disabled CarAuto (`com.eryanet.vlink`), wired AA worked reliably on my car.
The device records confirmed CarAuto was disabled and `OTG_MODE=2` (USB Host) was
set while wired projection worked. I'd also changed automatic-start and wireless
settings during troubleshooting, so I can't isolate the effect of each change.
I didn't record those phone settings well enough to automate them here.

Switching to Host mode got the wired connection working. The shared port needs
Device mode for the laptop and Host mode for the phone. The installer leaves the
role alone while it's connected.

## Factory fullscreen mechanism

My headunit already had root access: `su 0 id` returned `uid=0`.
It uses `su 0` rather than the usual `su -c` syntax. Installing Open Headunit
didn't need root; changing the factory SystemUI preference did.

Here's what the factory code inspection turned up:

- `com.chinatsp.custom.PageChangeHandler$6.onReceive` handles
  `com.chinatsp.systemui.ACTION_APP_INFO`, reads `packageName` and integer
  `appCentered`, and persists the per-app preference.
- For this firmware, `0` selects the third-party fullscreen behavior; `2` selects
  the system-style layout; `-1` falls back to the factory package classification.
- `com.chinatsp.activity.onpostresume` refreshes the named foreground app's layout.
- The preference is in device-protected SystemUI storage at the path in the CLI.

These are the commands that worked on my headunit:

```sh
adb -s YOUR_CAR_USB_SERIAL shell su 0 am broadcast --user 0 \
  -p com.android.systemui -a com.chinatsp.systemui.ACTION_APP_INFO \
  --es packageName com.andrerinas.headunitrevived --ei appCentered 0

adb -s YOUR_CAR_USB_SERIAL shell su 0 am broadcast --user 0 \
  -p com.android.systemui -a com.chinatsp.activity.onpostresume \
  --es packageName com.andrerinas.headunitrevived
```

I used a non-default ADB port and temporary Wi-Fi access during troubleshooting.
I've used placeholders above to keep private identifiers out of the repo. Use
the CLI for setup; it checks the firmware and backs up the original state first.

The saved key read back as `0`, and the recorded app bounds and rendered surface
grew from 1280×720 to 1920×720. I then connected the phone and confirmed AA filled
the width. The little factory Home/Back overlays stayed, and Home covered some
controls. I accepted that result and left the overlays alone.

The [before-and-after screenshots](../README.md#screenshots-from-my-car) show
Open Headunit's main screen with the factory side panels, then at full width.
They document the receiver layout change; they aren't captures of an active
Android Auto session.

The factory preference accepts a package name, but I haven't qualified other
apps for this release.

The changes also survived a full reboot on my car. I don't have a saved
post-reboot device capture or a separate cold ignition-cycle test here.
The installer won't reboot the car automatically.

## The later screenshot, and what's still untested

On 2026-10-26 I connected the laptop again with the USB-role screen open so it
could be captured for the guide. It shows the unlocked factory menu, selected
`开发模式` page, `Device模式` control, and Settings button on the matching model/build.
The USB check read back `OTG_MODE=1`. You can see the image in the
[car-screen guide](car-menu.md#2-open-the-development-page).
The page was already unlocked. No PIN was re-entered and no settings changed
for the screenshot, so it doesn't count as an installer test.

- I've tried the actual car changes on my car and this one firmware.
- I haven't retested wireless since disabling CarAuto.
- I haven't exhaustively tested every factory function.
- The new installer has software tests with simulated device responses, but I
  haven't completed its full setup-and-restore cycle on the car yet.

I've kept the remaining car-test checklist in [testing.md](testing.md).
