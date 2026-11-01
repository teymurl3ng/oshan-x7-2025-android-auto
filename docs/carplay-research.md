# CarPlay research for the reference Oshan X7

**Historical research, superseded by live results:** the owner selected
CarLink, tested both AA and CarPlay, confirmed both fullscreen, and adopted
the CarLink launcher card. [Current setup](carlink-setup.md) ·
[Live findings](verified-findings.md). The untested/proposed statements below
describe the original research stage, not the current CarLink result.

Researched **2026-11-02**. This is offline research and a proposed trial scope,
not a qualified installer or a successful CarPlay test. No car connection,
installation, settings change or reboot was performed for this research.
The owner's intended phone is an **iPhone 15 Pro Max running iOS 27**
(owner-reported; exact minor version not recorded).

## Original recommendation

**Follow-up:** the owner selected CarLink for a combined AA/CarPlay trial.
The [app-only trial workflow](carlink-trial.md) now implements a separate
guarded CLI path. The DiPlay-first recommendation below records the original
CarPlay-only research; it is not a claim that CarLink has failed on this car.
The first official CarLink installation was subsequently rejected because it
redeclares OpenHU's navigation permission. Original OpenHU/Home were verified
after the rejected attempt. The owner authorized a manifest-only local
coexistence variant; see the trial document for exact artifact pins and limits.

**Try the official DiPlay 0.2.22 APK over USB first.** It is the closest
standalone CarPlay counterpart to the existing Open Headunit setup. Its actual
APK meets the saved unit's Android and CPU requirements. Whether CarPlay works
on this exact Oshan firmware remains unknown.

Keep the existing OpenHU installation and factory launcher arrangement. Install
DiPlay as a separate user app for a bounded trial, open it directly, and run one
projection app at a time. Launcher-card integration, firmware changes and
microphone modifications are separate work and are unnecessary to find out
whether basic CarPlay works.

## Options and their evidence

| Option | Requirements and limits | Assessment for this car |
| --- | --- | --- |
| **DiPlay 0.2.22**, package `com.shihab.diplay` | Standalone APK; wired and wireless; Android 7.0/API24+. Official support focuses on BYD; other brands are explicitly unsupported. | First software trial. Android/ABI fit is verified offline; Oshan operation is not. |
| **CarLink 1.0.7**, package `com.carlink.app` | Generic combined DiPlay/DiAuto fork; Android 7.1/API25+ on ARM. BYD extras are selected by brand. | A plausible second software trial. Its release README explicitly leaves Android 7.1–9 and other headunits untested; its documented real-device evidence is one Android 16 tablet. |
| **CarlinKit CPC200-CCPA + AutoKit** | A USB hardware receiver plus its Android app; manufacturer requires Android above 4.4.4 and passing AutoKit Detection. Product is marketed for aftermarket Android radios. | Hardware fallback only. Our OEM Android unit exceeds the OS minimum, but that does not establish manufacturer support. Test AutoKit detection and establish a returnable purchase before buying. |

Sources: [DiPlay at the reviewed tag](https://github.com/shihabal3amri/DiPlay/tree/v0.2.22),
[CarLink 1.0.7 README](https://github.com/F-e-n-y-x/CarLink/blob/v1.0.7/README.md),
[CarLink release](https://github.com/F-e-n-y-x/CarLink/releases/tag/v1.0.7),
[manufacturer CCPA specification](https://www.carlinkit.com/ccpa).

CarLink's vendored DiPlay README identifies a 0.2.21 base. This research did not
audit whether it separately incorporates every relevant 0.2.22 fix. Its generic
design is useful, but does not supply Oshan test evidence.
[Vendored README](https://github.com/F-e-n-y-x/CarLink/blob/v1.0.7/vendor/diplay/README.md).

ZLink/TLink/SpeedPlay APK names alone do not establish an authorized compatible
receiver for F202. No verified F202 package or installation procedure was found
for them. They are not selected for this trial. AutoKit alone is also not the
CCPA hardware solution: the manufacturer's flow uses both app and dongle.
Conventional wired-to-wireless CarPlay adapters must not be assumed to add a
CarPlay receiver to an Android screen; check the exact product's prerequisites.

## Compatibility against the actual saved unit

The local evidence identifies **F202_MCA**, Android **9/API28**, firmware
**F202RHD_D1_20241022162756**, `full_spm8666p1_64`, board platform `mt6771`,
physical display **1920×720**, and supported ABIs
`arm64-v8a,armeabi-v7a,armeabi`. These are historical car read-backs, not a fresh
inspection. See the [profile](../profiles/f202-mca-rhd-20241022.json) and
[verified findings](verified-findings.md).

| Area | Evidence | Conclusion |
| --- | --- | --- |
| Android | Actual DiPlay APK minimum API24; car API28 | OS requirement passes. A target SDK of 37 is not a minimum-OS requirement. |
| CPU | Actual APK contains `arm64-v8a` and `armeabi-v7a` native libraries | Both relevant ABIs match. |
| Installing user apps | OpenHU was installed as a normal user app on this firmware | APK installation is demonstrated for OpenHU; DiPlay installation has not been attempted. |
| USB host | Wired AA worked on the recording USB port in Host mode | Promising physical path; AA success does not verify DiPlay's different iPhone/USB transport. |
| iPhone/iOS | DiPlay issue #380 names an iPhone 15 Pro Max/iOS27 with a wireless session and channel/stutter problems | Relevant phone-side evidence, not proof of this car or a flawless experience. |
| Display | Car is ultrawide; DiPlay has resolution/frame-rate settings | Rendering and touch must be observed. The OpenHU-specific SystemUI fullscreen setting does not establish DiPlay fullscreen. |
| Microphone | This car's AA/native-assistant microphone recognition remains unresolved | Siri and calls are independent acceptance tests; no microphone fix is established. |
| Wireless | Android9 legacy Wi-Fi Direct is firmware-dependent; Android-accessible Bluetooth is required | Unknown on this unit. Working factory Bluetooth calls alone do not prove app-level RFCOMM access. |

[DiPlay phone report #380](https://github.com/shihabal3amri/DiPlay/issues/380),
[versioned compatibility notes](https://github.com/shihabal3amri/DiPlay/blob/v0.2.22/docs/COMPATIBILITY.md).

DiPlay's current release supports a legacy Android7–9 Wi-Fi Direct route; older
summaries saying wireless invariably requires Android10 are incomplete for this
version. That legacy route cannot verify the selected frequency. A manual car
hotspot is another option if this car exposes one and Android Bluetooth works.
Neither path has been qualified here. Network ADB remains outside this project.
[Android9 wireless limitations](https://github.com/shihabal3amri/DiPlay/blob/v0.2.22/docs/ANDROID9_WIFI_DIRECT.md).

## Important counterevidence and limits

Searching upstream DiPlay issues for `Oshan` and `F202` found no matches on the
research date. This is a search result, not proof that nobody has tested it.
Changan badge matching is insufficient: reports cover materially different
Allwinner and MediaTek units and different firmware.

On a Changan Ruicheng Plus/MT8666/Android9, an older/custom DiPlay build was
reported to encounter hotspot, repeated music-pause and microphone/echo
problems. The maintainer confirmed a software Opus fallback contribution, but
explicitly did not claim the other problems were solved. Do not copy that
report's Bluetooth-disabling workaround into this car.
[Issue #415 and maintainer response](https://github.com/shihabal3amri/DiPlay/issues/415).

An Eado Plus report names the closely related `spm8666p1_64_car` platform and
1920×720 display. Its initial microphone claims were subsequently qualified:
the reported wireless session had not started, so microphone behavior could
not yet be measured. It is useful evidence of possible wireless failure,
not a verified microphone diagnosis for this car.
[Issue #801, including follow-up comments](https://github.com/shihabal3amri/DiPlay/issues/801).

DiPlay is a public preview and is not Apple-certified. Its distributed APK uses
an experimental bundled accessory identity, so acceptance by future iOS
versions is unresolved. The official source archive deliberately omits those
runtime authentication inputs: an ordinary source build is not equivalent to
the standalone release APK. There is no need to extract or publish those inputs.
[Release notice](https://github.com/shihabal3amri/DiPlay/blob/v0.2.22/README.md),
[build documentation](https://github.com/shihabal3amri/DiPlay/blob/v0.2.22/docs/BUILD.md).

## Completed local groundwork

The official release was published **2026-10-28**, marked prerelease, at source
commit `28d6002ba00320f0ba745212160b08759e4f60b9`.
APK, source ZIP and published checksum list are stored under the existing
ignored `.oshan-x7/research/carplay-2026-11-02/` directory. Original state and
recovery journals were not replaced. Downloaded app/source code was not run.

| Artifact/check | Verified result |
| --- | --- |
| `DiPlay-0.2.22.apk` | 19,042,758 bytes; SHA-256 `7d04db263834f22010a86847766928113d3503a273e4d2d3440d21552e173139` matches the GitHub release asset digest and published checksum list |
| `DiPlay-0.2.22-source.zip` | 8,527,222 bytes; SHA-256 `81ba65e045dade0bd8d47ba0798851030233a8724aeaf27f490a8f984feeeb38` matches its GitHub asset digest and checksum list |
| Actual APK manifest | `com.shihab.diplay`, version0.2.22/code41, minSDK24, targetSDK37; no shared UID; no activity HOME intent filter |
| App entry | `com.shilapi.xcertplay.DiPlayActivity`, with a launcher intent filter |
| APK signature | `apksigner verify` passed; v2 signature verified; one signing certificate |
| Signing certificate SHA-256 | `87b38b12788dcb202a961215f2572e30ec2dc9d8ef4bc070d05f77e49291a363`, matching upstream's recorded signing identity |
| Source review | Wired USB/local VPN implementation, relevant manifests, startup defaults and published compatibility limits inspected |

The manifest's HOME query is package discovery, not an activity offering to
replace the car's Home screen. DiPlay auto-open-on-boot defaults to false in
the reviewed source. These observations do not prove all runtime behavior.

USB may request **local VPN consent on the car**, in addition to USB access and
iPhone Trust/CarPlay prompts. The reviewed VPN source scopes the tunnel to
DiPlay and its USB link-local route, rather than a remote VPN service.
Optional permissions for overlays, usage access, changing settings or package
installation are not prerequisites to grant blindly for this initial trial.
[Connection guide](https://github.com/shihabal3amri/DiPlay/blob/v0.2.22/docs/INSTALL.md),
[VPN source](https://github.com/shihabal3amri/DiPlay/blob/v0.2.22/shared/src/main/java/com/shilapi/xcertplay/network/CarPlayVpnService.kt).

## Proposed controlled trial — not performed

The existing `oshan_x7.py setup` is pinned to OpenHU and also owns other AA
changes. **It is not a DiPlay installer.** For a standalone DiPlay trial, implement and
offline-test an app-only trial in the deterministic CLI: exact firmware and
launcher checks, pinned APK/signature/version, original-state record, refusal
to overwrite an unknown existing DiPlay, app/UI health checks, and rollback
limited to the exact newly installed trial app. Preserve any preexisting app
and the original AA journals. Do not change the AA profile to disguise DiPlay
as its pinned receiver.

The intended later owner/agent sequence is:

1. Park and power the headunit. On the **car Phone dial pad**, enter
   **`*#*#888` → Call → `1111`**. Open **`开发模式`**. If a separate development
   PIN appears, the saved-code default is **`3821`**: unlike the observed outer
   `1111`, that second PIN has no recorded live-entry test and may have been
   changed. Stop if it is rejected. Tap **Settings → System → Advanced →
   Developer options** and enable **USB debugging / `USB 调试`** if needed;
   if Developer options is hidden, enable it with seven Build-number taps in
   About device/tablet. Return to `开发模式`, select **`Device模式`**, connect
   the trusted laptop by a data cable and accept its visible debugging prompt.
2. Use the future guarded app-only CLI to check exact compatibility, record the
   baseline, install only the verified DiPlay app and inspect its screen.
   Skip BYD setup/extras. Leave boot startup, network-ADB helpers, steering-wheel
   interception, cluster/HUD features and experimental processing off. Start
   with the ordinary display area and H.264/30fps.
3. Complete visible permissions needed for the chosen route. Check that Home,
   radio/music, AC, native phone and settings remain usable. A normal Android
   reboot with laptop still connected is a separate check from ignition.
4. After laptop checks finish, disconnect the laptop, return to the factory
   **`开发模式`** page and select **`Host模式`**. Keep other projection apps
   closed. Connect the iPhone using a suitable **USB-C data cable** to the
   **recording USB port** that worked for AA; identify the actual car connector
   rather than assuming its position/type. Select DiPlay's **Connect with USB**
   and accept relevant visible USB/local-VPN/iPhone prompts. Siri must be enabled
   on the iPhone. Never switch the shared USB role during laptop commands.
5. Observe projection, Maps, touch, music/navigation audio, Home return and one
   disconnect/reconnect. Test Siri separately and, if desired, a phone call with
   both ends checking audio. Record failure times and save DiPlay diagnostics
   locally. A picture is not evidence of working calls or microphone input.
6. If the trial fails, disconnect the phone, regain Device mode and use the
   original trial journal to remove only its owned exact DiPlay app. Check the
   existing OpenHU/Home/native controls. The present AA `restore` command does
   not own a separately installed DiPlay. Recovery still needs responsive
   Android/package management/authorized USB; return to Device with a broken
   launcher remains unqualified.

[Existing car-menu evidence](car-menu.md), [recovery limits](recovery.md),
[Apple's connection guidance](https://support.apple.com/en-au/102521).

Only after basic wired operation is demonstrated should wireless, fullscreen
integration or automatic startup be considered. The actual phone/firmware
pairing, Siri/call audio, reconnect reliability, cold ignition behavior and all
vehicle-control checks remain **untested**.
