# USB and wireless connection notes

The current CarLink tests use the **regular charging/CarAuto USB port**, as
confirmed by the owner. The exact connector position/cable map has not been
photographed or inventoried.
Use a suitable data cable and a direct phone-to-car connection.

| Mode | Owner-observed result |
| --- | --- |
| iPhone CarPlay with cable | Worked perfectly |
| iPhone CarPlay wirelessly | Worked perfectly |
| Android Auto with cable | Working, fullscreen |
| Android Auto wirelessly | Unreliable |

Use **Device模式** for laptop ADB and keep it selected through setup/reboot.
Disconnect the laptop and select **Host模式** for the phone. [Car menu](car-menu.md).

Setup grants CarLink's runtime/special access and enables its built-in USB
confirmation service automatically. One car-side prompt still needed tapping
in the subsequent phone test. Its exact dialog type was not established; the
USB prompt issue remains unresolved. [Permission scope](permissions.md).

For a failed cable connection, distinguish no device, an access/chooser prompt,
a session startup failure and a later disconnect. Check USB role, data cable,
app identity and authorized ADB/host permissions before changes. Do not enable
network ADB as a workaround. Observe touch, sound and reconnect separately.

Owner-reported wireless success is a functional observation, not a long-duration
reliability or cold-ignition qualification. Microphone recognition remains
unresolved. Laptop supervision ends when it is unplugged.
