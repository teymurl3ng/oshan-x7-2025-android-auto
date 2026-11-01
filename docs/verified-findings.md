# Verified findings

These results concern the exact reference F202_MCA firmware, not every Oshan X7.
Reference captures and the CarLink work below were recorded on **2026-11-02**.

## Current CarLink results — 2026-11-02

| Result | Evidence | Limit |
| --- | --- | --- |
| Official CarLink 1.0.7 installed | Exact installed APK hash/version, original signing certificate and successful UI health check | Later releases need separate qualification |
| Android Auto and CarPlay work fullscreen | Owner reports for both; actual 1920 × 720 projection captures | Screenshots do not prove every audio/touch/reconnect behavior |
| iPhone wired and wireless CarPlay | Owner reports both worked perfectly, using iPhone 15 Pro Max / iOS 27 as reported | Long-duration reliability and all audio paths were not separately enumerated |
| Android wireless | Owner reports unreliable operation | Wired AA remains the working option |
| Current USB port | Owner identifies the regular charging/CarAuto USB port as the working port | Connector position and cable map are not recorded |
| Factory Home card opens CarLink | Owner tested card and Home return | Other native controls were not exhaustively enumerated |
| Launcher/fullscreen survive Android reboot | New boot identity, exact active/factory hashes, UID, default Home and layout read-back | A normal Android reboot is not an ignition cycle |
| Automatic permissions persist after reboot | All six runtime grants, four app-ops and battery exemption read back; exact USB auto-confirm service bound to Android's system process after reboot | One car-side prompt still needed tapping after setup; its type is unconfirmed |
| Direct public installation | Offline setup/recovery tests using official APK/launcher pins | Full fresh setup/restore cycle not yet car-qualified |

The official APK SHA-256 is
`16e8b98436a5c5f355aa4b49086e28d41bee9f9f874174658cafb682fd503e77`.
The launcher SHA-256 is
`ffc81db01bb7d1645b6a9efd9d23960cafd6b671ba51b88d3816794597b30285`.
The app uses its own package-specific factory fullscreen value `0`; it is not
a global resolution change. [Artifact pins](carlink-setup.md#artifact-pins).

The five public screenshots predate the change to the official APK signature;
code and UI asset payloads match. They remain evidence of those observed frames,
not proof that a new permission automation path handled a phone attach.
[Capture details](screenshots.md).

## Compatibility evidence

Android 9/API 28, ARM64/ARMv7 and native 1920 × 720 were read from the car.
Firmware is `F202RHD_D1_20241022162756`; MCU is `F202RHD_20240722_1`.
The exact factory APK, launcher update, system/shared UID 1000, version 20240726
and default Home were checked. Existing `su 0` worked. Outer menu PIN 1111 was
observed; the separate development-page default 3821 is code-only evidence.
[Full profile](../profiles/f202-carlink.json) · [Car menu](car-menu.md).

## Remaining qualification

All configured runtime/special grants, battery exemption and the USB service
binding were read back after a normal Android reboot. The subsequent owner
phone test still needed a tap on one car-side prompt. It was described as USB/
ADB-like, but its exact type was not established. USB prompt automation remains unresolved.

Microphone/Gemini recognition remains unresolved. Siri/call audio, all sound
paths, long-duration/repeated reconnect behavior, cold ignition and exhaustive
native controls need separate observations. iPhone cable and wireless success
and Android wireless unreliability are owner reports, independently of screenshots.
The regular charging/CarAuto USB port is the current working phone port. Exact
physical connector/cable mapping remains unrecorded.

The shared-port laptop supervision ends in Host mode. Regaining Device mode
with a broken launcher/menu has not been qualified. Recovery needs responsive
Android/package management and authorized USB. [Test checklist](testing.md).
