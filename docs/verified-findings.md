# Tests on my Oshan X7

These results apply to my **F202_MCA** head unit, firmware
**F202RHD_D1_20241022162756**, MCU **F202RHD_20240722_1**. They do not establish
support for every Oshan X7. The CarLink observations below were recorded on
**2026-11-02**.

## What I tested

| Test | Result |
| --- | --- |
| Wired Android Auto | Worked fullscreen |
| Wired CarPlay | Worked fullscreen |
| Wireless CarPlay | Worked with my iPhone 15 Pro Max, running iOS 27 as recorded at the time |
| Wireless Android Auto | Unreliable |
| Large CarLink card and factory Home | The card opened CarLink; Home returned to the car launcher |
| Wired phone port | I used the regular charging/CarAuto USB port |
| Car-side USB prompt | I still had to tap one prompt after automatic permissions/service setup; its exact dialog type was not established |

The screenshots show the fullscreen projection and launcher. They do not
establish every audio, touch or reconnect behavior. I have not recorded a
complete physical port/cable map.

## Recorded machine checks

- The head unit reported Android 9/API 28, ARM64/ARMv7 and a native 1920 × 720
  screen. Existing `su 0` root access worked.
- Official CarLink 1.0.7 was installed and checked by exact APK hash/version and
  UI health. Its settings were restored during that work.
- Factory/active launcher hashes, system/shared UID 1000, version 20240726,
  default Home and CarLink's fullscreen value `0` were checked after a normal
  Android reboot. The layout change is per-app, not a global resolution change.
- Six runtime grants, four app-ops, battery exemption and the USB service's
  binding to Android were read back after reboot.

[Artifact identities](reference.md#artifact-pins) · [Permission scope](permissions.md).
These checks establish saved settings and immediate app health; a bound service
alone does not prove it handled a real phone prompt.

## Screenshot provenance

The five [CarLink screenshots](screenshots.md) were captured on 2026-11-02 at
1920 × 720. They predate the change from the earlier locally signed APK to the
official signing identity. The recorded comparison found matching UI/code asset
payloads. Keep them as evidence of the displayed frames, not a new official-build
phone attach or permission-automation test. Hashes and captions are in the
[capture manifest](images/carlink-reference.json); raw capture records remain private.

The factory-menu capture is dated 2026-10-26. I used the dialer code and outer
PIN `1111`. The separate development-page default `3821` comes from factory-app
code inspection; I have not tested entering it on the car. [Menu guide](car-menu.md).

## Still to test or resolve

- Microphone/Gemini recognition remains unresolved. Siri/call audio and other
  sound paths need separate observations.
- Long sessions, repeated reconnects, cold ignition and a complete check of
  native vehicle/media controls remain untested as a set.
- The USB prompt still needs investigation; its exact type was not established.
- The complete fresh installation → Android reboot → phone tests → restore cycle
  has offline tests, but has not yet been completed on the car. Earlier component
  tests do not replace this test.
- Returning from Host to Device mode with an unusable launcher/menu has not been
  tested. Recovery requires responsive Android and authorized USB.

[Offline tests and next live checklist](testing.md) · [Recovery](recovery.md).
