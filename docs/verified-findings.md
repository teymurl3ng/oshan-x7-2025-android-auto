# Evidence from the reference car

These notes distinguish what was read or seen on the car, what the owner
reported, what was found in saved code, and what remains untested. Raw private
dumps, identifiers and APKs are not published. The latest component work and
screenshots were recorded on 2026-10-26.

## What the evidence supports

| Finding | Evidence | Limit |
| --- | --- | --- |
| Exact headunit/firmware in the public profile | Live ADB property, package, hash and display read-back | Model/year alone does not identify this firmware |
| Existing `su 0` root | Live `id` returned uid 0 | Tool does not root a unit; `su -c` was not the working syntax |
| Phone → `*#*#888` → Call → outer PIN 1111 | Worked during original setup; saved factory code agrees | Later screenshot was already unlocked, not another PIN test |
| Development-page default PIN 3821 | Saved factory APK code inspection | Not re-entered in a later live test; a changed password can override it |
| Device role 1 / Host role 2 | Factory callback inspection and live role read-back during laptop/phone work | No complete photo/connector map of all ports was recorded |
| Open Headunit 3.5.0/code119 | Official release APK hash and installed package read-back | Another APK/version is not qualified by this result |
| Fullscreen value 0, 1280×720 → 1920×720 bounds | Factory handler inspection, saved preference/bounds and actual receiver captures | Pictures show receiver Home, not an active phone projection frame |
| Android Auto filled the width and wired had no wireless lag | Owner's connected-phone test | Not a measured latency benchmark |
| CarAuto disabled-user, wired AA working | Live enabled state and owner projection tests | Automatic-start/wireless settings also changed; cannot isolate every cause |
| Recording USB port worked, ordinary port failed in roughly 10–15 seconds | Owner repeated tests with working cable | Physical/power/firmware cause unresolved; earlier logs had USB resets/error -71 |
| Routine large popup gone with Show toast messages off | Owner saved setting and confirmed reconnection | Manual app preference; forced errors remain possible |
| Factory Home overlay overlaps some AA controls | Owner full-width test | Accepted unchanged; overlay removal is outside this project |
| Gemini hears no words in AA; native assistant also cannot hear | Owner tests; Gemini works directly on phone | No microphone fix. Failed reversible AEC path experiment was rolled back |
| Launcher card, Home and controls | Tests described below | Owner tried usual controls, not an exhaustive vehicle audit |
| v0.3 staged checks/recovery/reboot flow | Offline simulated ADB fault tests | No full live v0.3 setup/restore cycle yet |

## Exact unit and artifacts

The headunit read back **F202_MCA**, `alps`, `full_spm8666p1_64` /
`spm8666p1_64`, MediaTek `mt6771`, Android **9/API28**, build
**`F202RHD_D1_20241022162756`**, MCU **`F202RHD_20240722_1`**, physical
**1920×720**. The remaining exact properties are in the
[profile](../profiles/f202-mca-rhd-20241022.json). The vehicle's 2025/right-hand-drive
identity is owner-reported; the software checks use the actual read-back.

| APK | Identity | SHA-256 |
| --- | --- | --- |
| Factory launcher | `com.chinatsp.launcher`, code20240726 / C_2024072610, 8,256,512 bytes | `0c50bad53fa2116e98928c74be78e1b9609a1d3f73d3ee42726b001ae7ddefb0` |
| Final menu-cleanup launcher | Same package/code, system/shared UID1000, 8,274,207 bytes | `03ef3a861c43124f184f0d675400f9a6022b0100f1a96e3e498dc096041f66b8` |
| Official receiver | `com.andrerinas.headunitrevived`, 3.5.0/code119, 13,903,086 bytes | `609ca23b4eb0deaad2a58f6463b26cbf58bdc602ac0775eb5e7adb293a75a14d` |

The factory launcher remains at `/system/app/F202_Launcher/F202_Launcher.apk`.
The update is under `/data/app/`; default Home remained
`com.chinatsp.launcher/.MainAct`. The final signed output was verified with
v1/v2/v3 signatures and four-byte alignment. Applying the bundled binary patch
to the exact original produced bytes identical to that car-tested update.
[Patch pins and readable source changes](launcher.md).

The receiver came from the [official Open Headunit release](https://github.com/andreknieriem/open-headunit/releases/tag/v.3.5.0),
GitHub flavor, upstream commit `1c1b5b7261eb`. Its APK was checked against the
release asset digest. It installed as a normal user app. Headunit Reloaded and
Google services on the car were not needed for this working receiver setup.

The immutable launcher hash does not prove all firmware files are identical.
The saved SystemUI copy was incomplete, so its partial hash is not used as a
complete-APK compatibility pin.

## Fullscreen mechanism and settings evidence

Saved factory code showed `com.chinatsp.custom.PageChangeHandler$6.onReceive`
handling `com.chinatsp.systemui.ACTION_APP_INFO`, reading `packageName` and integer
`appCentered`, then persisting the per-app value. In that implementation, `0`
selects third-party fullscreen behavior, `2` system-style layout and `-1` factory
package classification. `com.chinatsp.activity.onpostresume` refreshes the named
app's layout. The preference is in SystemUI's device-protected storage at the
path pinned in the CLI.

On the car, the receiver key read back as 0 and bounds/rendered surface expanded
to 1920×720. The owner then confirmed full-width connected Android Auto. The
[before/after pictures](../README.md#screenshots-from-my-car) document the
receiver's main screen. Other apps have not been qualified for this setting.
Normal Android reboot read-back persisted; a cold ignition cycle is untested.

Reference receiver choices were USB, right-hand drive, landscape, about 10-inch
screen, 180 DPI and phone GPS. A complete final record of all automatic-start,
wireless and phone values was not kept, so these are not silently reproduced by
the installer. Wireless experiments used extra phone developer/server steps;
those are not part of the working wired flow. Wireless has not been retested
since CarAuto was disabled.

## Launcher and menu evidence

The first signed launcher update passed installation, large-card opening,
Home return, owner checks of usual native controls, factory rollback/reinstall,
a normal Android reboot, and wired AA/Home tests.

The final menu-cleanup build pinned above was subsequently installed and read
back with exact hash/UID/version/HOME and unchanged factory base. After another
normal Android reboot, the unwanted duplicate OpenHU and launcher entries were
absent. Large-card launch and Home return were observed again. The owner said
the controls they tried worked normally and AA worked on the recording USB port.
The latest phone reply did not individually enumerate sound, touch or popup
checks; earlier tests must not be represented as that exact final test.

The launcher changes remove/redirect retired CarAuto shortcut/connection handling
and open OpenHU from the large card. The Bluetooth card retains its original
size/position. Music/Radio, native menu entries and Home/Back overlays remain.
The proposed enlarged Bluetooth/four-card layout was discarded and is not part
of this release. [Actual screenshots](../README.md#android-auto-on-the-factory-home-screen).

The factory USB-page screenshot on 2026-10-26 was a read-only capture of an
already unlocked menu. `开发模式`, `Device模式` and Settings were visible and
OTG_MODE read back as 1. It documents the page, not a new PIN/role-change test.
No separate Host-mode, debugging or complete onboarding-prompt screenshots exist.

## Public workflow qualification

The current v0.3 workflow adds stage health checks, a shared automatic/manual
recovery engine, permission pauses, component-specific recovery and an optional
normal Android reboot check. Tests simulate launches, crashes/ANRs, PID loss,
USB loss, missing root, malformed preferences, disabled/unknown receivers,
uncertain writes and interrupted rollbacks. These are software checks with no
car writes. Android's [ADB activity commands](https://developer.android.com/tools/adb#am)
and [logcat buffers](https://developer.android.com/tools/logcat) describe the
underlying interfaces; this firmware's new workflow still needs live qualification.

**Outstanding:** complete unified setup→reboot→phone test→restore on the car;
regaining Device mode from Host with an unusable launcher; controlled interrupted
recovery; cold ignition; wireless AA; microphone recognition; exhaustive vehicle
function checks; complete cable/port photos. No resident watchdog, offline boot
rescue or manufacturer recovery route has been qualified. [Test plan](testing.md).
