# Reference screenshots from the car

These are actual captures from the tested Oshan X7, checked before publication.
Current CarLink images were captured on **2026-11-02** at the native 1920 × 720
resolution. [Current setup](../README.md) · [Recorded evidence](verified-findings.md).

## Current CarLink launcher

The large factory Home card now targets CarLink and reads **CarPlay + Android
Auto**. This capture followed the normal Android reboot check. The owner
confirmed the large card opens CarLink and factory Home returns correctly.

![Factory Home with the large CarLink card, Music, Radio, Bluetooth phone and recorder cards](images/launcher-carlink.png)

The icon and labels changed with the explicit app target; card layout and
factory media/vehicle control code were preserved. A screenshot does not
establish every native control's behavior.

The native app-menu page remains available, with System settings, Voice
Assistant and File management. The redundant receiver/launcher entries
are absent; the recorder remains on the Home page.

![Current app menu with native settings, voice assistant and file management](images/launcher-carlink-app-menu.png)

## Fullscreen CarPlay

An actual CarPlay Search frame fills the screen. No routes, addresses or
contacts are shown. The small factory Home/Back overlays remain, including
their overlap with the projection's lower-left controls.

![CarPlay Search across the full 1920 × 720 headunit display](images/carplay-fullscreen.png)

This is a connected projection frame.
Its connection transport and wireless reliability are not established by the
picture. The owner separately confirmed both AA and CarPlay work fullscreen.

## Fullscreen Android Auto

A timed on-headunit capture records AA while the phone uses the shared USB
port. This early dashboard frame was selected because map/place labels have
not loaded and no personal route, contacts or media title appear. It documents
the full-width projection surface; it is not a complete Maps or music test.

![Android Auto dashboard across the full headunit display, captured before map labels loaded](images/android-auto-fullscreen.png)

Later raw frames and the capture record remain private. The owner separately
confirmed AA working fullscreen. The factory overlays remain visible.

## CarLink Home

The normal CarLink Home UI also fills the display. This is the receiver's
connection screen, not an active phone projection frame. A Wi-Fi Direct option
being displayed does not establish wireless reliability.

![CarLink Home fullscreen with the Android Auto connection option](images/carlink-home-fullscreen.png)

The [public capture manifest](images/carlink-reference.json) records date,
native size, SHA-256 and a precise caption for each of these five current
images. Raw capture journals and unused frames remain private.

The five frames predate the switch to the official signature. Their UI/code
content is unchanged; they do not by themselves establish new permission automation.
