# Connection troubleshooting

The shared USB role depends on what is connected:

| Connection | Car role | Other device |
| --- | --- | --- |
| Laptop for installation, reboot check or restore | **Device模式** | Phone disconnected |
| Phone for wired AA/CarPlay | **Host模式** | Laptop disconnected |

[How to switch roles](car-menu.md) · [My connection test results](verified-findings.md).

## Laptop cannot connect

Check the USB data cable, Device mode and whether the laptop's OS detects the
car. A charging-only cable cannot provide ADB access.

- **Unauthorized:** accept this trusted laptop's debugging request on the car.
- **No device/offline:** check role, cable/port, OS detection and the selected ADB
  server. Reuse a working server; do not blindly kill it.
- **Access denied/missing driver:** resolve the laptop's USB permissions or signed
  OEM driver. [Platform-specific guidance](agent-setup.md#3-establish-authorized-usb).
- **Multiple devices:** disconnect other ADB devices or explicitly select the
  car's verified serial.

Do not enable network ADB as a workaround. Once authorized, keep the laptop
connected in Device mode through the installer and Android reboot check.

## Phone does not project

Use **Host模式**, open CarLink and connect the unlocked phone directly with a
suitable data cable. I used the **regular charging/CarAuto USB port**. There is
no recorded connector-position map; these instructions do not assume left/right
placement or a particular cable connector.

Distinguish what happens: no detection, an access/default-app prompt, failure to
start a session, or a later disconnect. Inspect prompts on both the car and
phone. Setup handles CarLink's Android permissions, but a car-side USB prompt
may still need your response. Phone trust/pairing remains separate.

For wireless CarPlay, enable Bluetooth and Wi-Fi on the iPhone and follow
CarLink's pairing flow. Wireless Android Auto was unreliable in my tests; use a
cable. Phone USB debugging, developer mode and an Android Auto headunit server
are not needed for this wired workflow.

If laptop diagnostics are needed, **disconnect the phone → select Device模式 →
reconnect the laptop**, then run `status` with the original connection options
and state directory. Do not try ADB commands while the shared port is serving the
phone. Follow [recovery](recovery.md) if setup was interrupted.
