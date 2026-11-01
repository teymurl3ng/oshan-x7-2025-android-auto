# Automatic CarLink permissions

Runtime and special permissions run **inside `setup`**, after installing the pinned official app
and before its first launch. There is no owner-facing permission command and
no required walk through the runtime/special-access screens. **A car-side USB
prompt still needed tapping in the owner's test; full USB prompt automation is
unresolved.** This implementation is
specific to the verified Android 9/API 28 firmware and official CarLink 1.0.7.

## What setup configures

| Access | Setup action |
| --- | --- |
| Microphone, fine/coarse location, phone state, read/write external storage | Grant the six permissions declared by the tested app using Android package management |
| Display over apps | Set only CarLink's `SYSTEM_ALERT_WINDOW` app-op to allow |
| Modify settings | Set only CarLink's `WRITE_SETTINGS` app-op to allow |
| Usage access | Set only CarLink's `GET_USAGE_STATS` app-op to allow |
| Android Auto VPN consent | Set only CarLink's `ACTIVATE_VPN` app-op to allow |
| Battery optimization | Add CarLink to the app whitelist |
| Car-side USB prompts | Enable CarLink's existing `com.shilapi.xcertplay.UsbAutoConfirmService`, merging it into the current accessibility-service list |

Bluetooth permissions on this Android version are install-time grants. Newer
Android notification/nearby-device permission names are not blindly granted on
Android 9. Package-install access, network ADB, phone-side trust/pairing and
other apps' permissions are outside this grant set.

The USB service runs from the unchanged official APK. Its source checks matching
system USB dialog windows and text identifying this app and USB/iPhone/iPad,
selects the offered default/always-use option and confirms the prompt. It does
not grant every USB device to every app or suppress all system dialogs globally.
The installer checks that the service is enabled and actually bound.

Android USB device permissions are session-specific. Enabling the service is
verified separately from observing a real phone attach: a successful service
read-back alone cannot prove every vendor dialog is recognized. The phone's own
pairing/trust confirmations remain on the phone.

## Journaling and recovery

The original six grant states, four app-op modes, battery exemption and
accessibility settings are saved privately before writes. Each changed item
has a write-ahead operation; final read-back must verify all grants and a bound
USB service before setup reports success. An unknown APK, identity mismatch or
failed grant stops setup and uses the guarded recovery path.

Restore reverses only owned permission changes and preserves access already
granted before setup. Only the added USB service is removed; unrelated services,
including ones added afterwards, remain. It does not replace the global service
list with a stale snapshot. No root daemon or network ADB server is installed.

## Source evidence

- [CarLink setup permission registry](https://github.com/F-e-n-y-x/CarLink/blob/v1.0.7/app/src/main/java/com/carlink/app/ui/setup/SetupModel.kt)
  and [Android-version-aware app permissions](https://github.com/F-e-n-y-x/CarLink/blob/v1.0.7/vendor/diauto/app/src/main/java/com/andrerinas/openheadunit/utils/AppPermissions.kt).
- [Upstream USB permission setup](https://github.com/F-e-n-y-x/CarLink/blob/v1.0.7/vendor/diplay/common/src/main/java/com/shilapi/xcertplay/UsbPermissionSetup.kt)
  and [USB auto-confirm service](https://github.com/F-e-n-y-x/CarLink/blob/v1.0.7/vendor/diplay/common/src/main/java/com/shilapi/xcertplay/UsbAutoConfirmService.kt).
- [Android 9 VPN authorization](https://github.com/aosp-mirror/platform_frameworks_base/blob/android-9.0.0_r61/services/core/java/com/android/server/connectivity/Vpn.java)
  uses the `ACTIVATE_VPN` app-op for prior consent.
- [Android USB permission lifetime](https://developer.android.com/reference/android/hardware/usb/UsbManager#requestPermission(android.hardware.usb.UsbDevice,%20android.app.PendingIntent))
  is limited to the connected device/session unless a matching default applies.

[Implementation](../carlink_permissions.py) · [Testing](testing.md) · [Recovery](recovery.md).
