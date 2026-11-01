# USB reliability: diagnose before replacing cables

The port/cable observations below remain useful for the current
[CarLink setup](carlink-setup.md). The **Use Native USB Driver** experiment is
specific to the historical OpenHU receiver; it is not a CarLink setting or a
required step for the working CarLink configuration.

The reference car does not establish that only one special cable works. The
**same cable** worked on its video-recording USB port while the ordinary port
repeatedly disconnected after about 10–15 seconds. That points to a difference
between those connection paths, but does not identify whether the cause is
power, connectors, internal wiring, controller behavior or firmware.
[Recorded evidence and limits](verified-findings.md).

Earlier logs included USB resets/error `-71` (`EPROTO`). The
[Linux USB documentation](https://www.kernel.org/doc/html/v6.7/driver-api/usb/error-codes.html)
explains that protocol errors can involve hardware, device firmware or cables;
the controller often cannot distinguish the underlying faults. This is not a
cable diagnosis, and the saved observations do not prove every later disconnect
had the same cause.

## Two connections, with different failure modes

| Connection | Car role | What a successful check establishes |
| --- | --- | --- |
| Laptop → car, for setup/reboot/restore | Device模式 | Authorized USB ADB and the checked car state |
| Phone → car, for Android Auto | Host模式 | Only an actual phone test establishes projection and reconnect behavior |

The installer verifies firmware, packages, settings and immediate app health. It
does not operate the phone's USB session or measure its reliability. An ADB
connection working with the laptop does not qualify a phone cable or car port.
Keep the laptop in Device mode through setup and its Android reboot check;
disconnect it before selecting Host for the phone. [Exact car-menu steps](car-menu.md).

## Before buying another cable

1. Finish the supported setup and phone handoff in the [README](../README.md).
   Use Host mode for the phone, OpenHU's USB connection, and accept the visible
   car USB-access and phone Android Auto prompts. Phone USB debugging is not
   required. If setup failed, follow [recovery](recovery.md) first.
2. With the same phone and cable, try the **video-recording USB port** that worked
   on the reference car. Its exact physical position/connector map has not been
   recorded; identify it on the actual car. Do not assume all ports are equivalent.
3. Use a direct data cable. Charging alone does not establish a data connection.
   If uncertain, a file transfer between that phone and a computer can establish
   that the cable carries data in that combination; it cannot certify the car
   connection. Google's
   [Android Auto guidance](https://support.google.com/androidauto/answer/6348190?hl=en)
   recommends a cable under 1 metre without hubs or extensions. A short data
   cable you already own is a reasonable starting point; this repo has no
   qualified cable brand/model list.
4. Record what fails: no phone in OpenHU's USB list, permission denied, projection
   never starts, or an established session disconnects. Repeated USB prompts can
   accompany connection resets; repeatedly accepting them does not establish
   that permissions are the underlying fault.

Change one variable at a time. If one cable works on one port and fails on
another, stop treating cable replacement as the only troubleshooting route.

## A software compatibility experiment already available in OpenHU

OpenHU offers **Use Native USB Driver**: enabled selects `libusb`; disabled
selects Android's standard USB API. Upstream documents it as an alternative for
connection instability on some headunits and cables. This is an **untested
experiment on this car**, not an installer default or a verified fix.
[Upstream setting documentation](https://headunit.andrerinas.com/guides/settings/#use-native-usb-driver-v310).

The source revision recorded for this repo's pinned 3.5.0 receiver confirms the
setting and its effect:

- [Settings.kt](https://github.com/andreknieriem/open-headunit/blob/1c1b5b7261ebebde8000778ff2c06e3af3e3a326/app/src/main/java/com/andrerinas/openheadunit/utils/Settings.kt#L2478)
  defines `use-libusb`, defaulting to false when no value is saved. The reference
  car's final saved value was not recorded here.
- [CommManager.kt](https://github.com/andreknieriem/open-headunit/blob/1c1b5b7261ebebde8000778ff2c06e3af3e3a326/app/src/main/java/com/andrerinas/openheadunit/connection/CommManager.kt#L483)
  selects the corresponding transport for a new USB connection.

For a controlled parked-car experiment after successful setup:

1. Record the original driver setting. In OpenHU settings, locate **Use Native
   USB Driver**; use the Advanced view if needed. If it is absent or the screen
   differs, inspect it rather than substituting another APK.
2. Keep the same phone, cable, port and other settings. Test the existing driver,
   then disconnect the phone, change only this switch, save, and reconnect so a
   new connection uses the selected driver.
3. For each driver record time to connect, disconnects, Maps/sound/touch, Home
   return and repeated unplug/reconnect results. Then repeat on the other port
   with the same hardware. Start with one existing data cable; expand to other
   cables/phones only after establishing this baseline.
4. Return the setting to its original value after the experiment. This manual
   app preference is outside installer/restore ownership. Do not silently promote
   an experimental value to the public setup defaults.

Both drivers still depend on the car's USB hardware and kernel. A different
driver may address software compatibility; it cannot supply missing data wires
or repair an electrical fault. A single successful connection is insufficient
to qualify either driver as more reliable.

## What would make the repo more broadly usable

The next engineering work should capture the failing phone session, classify
where it fails, and qualify a repeatable driver/port configuration. OpenHU's own
file logging can help with app failures. Kernel evidence is needed to distinguish
bus resets from an app-only disconnect; its availability and retention across a
return to Device mode must be verified. Raw logs can contain private identifiers
and must not be published without inspection/redaction.

The laptop is disconnected during the Host-mode phone test. Do not claim live
ADB supervision of that session, enable network ADB to obtain it, or change the
shared role while laptop commands are running. Any future diagnostic command
must state which connection it actually measured and what it could not observe.

A driver fallback or receiver change should follow reproducible evidence and
retain the existing backup/recovery guarantees. Wireless projection is another
possible way to avoid the phone's data cable, but it has not been retested after
CarAuto was disabled and is not qualified by this repo. Neither a wireless
promise nor a stronger cable claim is supported by the current car tests.
