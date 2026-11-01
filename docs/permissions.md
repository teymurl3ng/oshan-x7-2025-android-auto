# CarLink permissions

Setup configures CarLink's Android permissions automatically, before the
installer opens the app. You do not need a separate permission command or a
walkthrough of Android's access screens. This uses the head unit's existing
factory root and is specific to the tested Android 9 firmware and CarLink 1.0.7.

**A USB-access prompt may still appear on the car when you connect a phone.**
Automatic permission setup does not guarantee that every such dialog is handled.
Phone-side trust/pairing is also separate.

## What setup configures

| Access | Action |
| --- | --- |
| Microphone, fine/coarse location, phone state, read/write external storage | Grant the six declared runtime permissions |
| Display over apps | Allow CarLink's `SYSTEM_ALERT_WINDOW` app-op |
| Modify settings | Allow CarLink's `WRITE_SETTINGS` app-op |
| Usage access | Allow CarLink's `GET_USAGE_STATS` app-op |
| Android Auto VPN consent | Allow CarLink's `ACTIVATE_VPN` app-op |
| Battery optimization | Add CarLink to the battery exemption list |
| USB prompts on the car | Enable its existing `com.shilapi.xcertplay.UsbAutoConfirmService` accessibility service |

Bluetooth permissions on Android 9 are install-time grants. Setup does not grant
newer Android notification/nearby-device permissions, install-package access or
permissions to other apps. It preserves unrelated accessibility services.

The built-in USB service recognizes matching system dialog windows/text and
selects the offered default/confirmation controls. Setup checks both the setting
and the service's actual binding to Android. Real phone attachment must still be
tested separately; see [the test record](verified-findings.md).

## Records and restore

Original grants, app-op modes, battery exemption and accessibility settings are
saved before permission writes. Each attempted change is recorded first and
marked complete only after its resulting state is checked. A failed change,
unknown APK or identity mismatch stops setup and enters guarded recovery.

Restore reverses changes made by this installation, preserves earlier grants,
and removes only its added USB service. Services added later remain. If CarLink
is absent, restore checks remaining global service/battery changes without
issuing package-grant commands to the absent app. Unknown replacement APKs are
kept. Failed verification leaves recovery incomplete. [Recovery guide](recovery.md).

## Implementation sources

- [CarLink setup/permission model](https://github.com/F-e-n-y-x/CarLink/blob/v1.0.7/app/src/main/java/com/carlink/app/ui/setup/SetupModel.kt)
  and [Android-version-specific permissions](https://github.com/F-e-n-y-x/CarLink/blob/v1.0.7/vendor/diauto/app/src/main/java/com/andrerinas/openheadunit/utils/AppPermissions.kt).
- [USB permission setup](https://github.com/F-e-n-y-x/CarLink/blob/v1.0.7/vendor/diplay/common/src/main/java/com/shilapi/xcertplay/UsbPermissionSetup.kt)
  and [USB auto-confirm service](https://github.com/F-e-n-y-x/CarLink/blob/v1.0.7/vendor/diplay/common/src/main/java/com/shilapi/xcertplay/UsbAutoConfirmService.kt).
- [Android 9 VPN authorization](https://github.com/aosp-mirror/platform_frameworks_base/blob/android-9.0.0_r61/services/core/java/com/android/server/connectivity/Vpn.java)
  and [battery exemption commands](https://github.com/aosp-mirror/platform_frameworks_base/blob/android-9.0.0_r61/services/core/java/com/android/server/DeviceIdleController.java).
- [Android USB permission lifetime](https://developer.android.com/reference/android/hardware/usb/UsbManager#requestPermission(android.hardware.usb.UsbDevice,%20android.app.PendingIntent)).

[Installer implementation](../carlink_permissions.py) · [Tests](testing.md).
