# Testing

These are the checks I use for the scripts, followed by the car tests I still
need to complete. I don't want a passing software test to be mistaken for a
successful Android Auto session.

## Offline tests

Run with Python 3.10 or later:

```sh
python3 -m unittest discover -s tests -v
```

The tests simulate ADB responses and local state. They exercise compatibility
refusals, wrong/multiple transports, exact artifact checks, write-ahead backup,
setup read-back, repeated runs, restore, and interrupted operations. Launcher
cases cover both factory and exact update identities, an unchanged immutable
base, default HOME/UID/version checks, ownership of preexisting updates, USB
role refusals, legacy backup upgrade, disconnects before/after install and
rollback, and refusing unknown builds. Binary-patch cases exercise bounded
decompression, corrupt/truncated instructions, signed offsets, both artifact
pins and cache verification. These are
software checks, not a substitute for actual USB/projection testing.

Host preparation tests also exercise existing-tool reuse, private SDK extraction,
invalid archive paths, and failed binary validation. The CI additionally downloads
Google's real Platform Tools on each OS with Python 3.13 and runs only `adb version`.
That network smoke test neither starts an ADB server nor accesses a car.

## Completed launcher checks

The original launcher update passed installation, large-card/Home and native
control checks, factory rollback/reinstall, a normal Android reboot, and a wired
AA/Home test. The final menu-cleanup APK then passed installation/read-back,
before/after-reboot icon checks, large-card/Home tests and owner control checks.
The owner reports wired AA works on the video-recording USB port; the ordinary
port still drops after 10–15 seconds. The latest phone answer did not separately
enumerate audio/touch/popup checks. Microphone recognition remains unresolved.

Local reconstruction from the original APK and bundled patch was compared byte
for byte with the exact final APK tested on the car. No new APK was installed
during the public installer integration work.

## Unified installer car test still pending

The individual changes worked on my car, but I haven't run the new installer
through its full setup-and-restore cycle there yet. This is the checklist for
that test on the matching firmware:

1. Read-only check of identity, original enabled/layout states, and existing receiver.
2. Setup with a verified APK; retain the original backup and journal.
3. Repeat setup; confirm no additional device writes and the original backup unchanged.
4. Confirm the large AA card opens OpenHU, Home returns correctly, and the small
   duplicate/launcher menu entries are absent. Hand off to USB Host and check
   real wired AA: image, audio, touch, voice and navigation. Record unresolved
   voice input separately from successful projection.
5. Access to factory Home/Back, camera, climate controls, and other usual functions
   while parked. Do not operate vehicle systems through improvised ADB commands.
6. Normal reboot and repeat wired test; separately identify any cold ignition test.
7. Restore via USB Device mode; verify the exact factory launcher returns only
   when this cycle installed the update, with launcher data retained. Confirm
   original CarAuto/layout behavior and receiver ownership. Repeat restore and
   confirm no further writes. A preexisting launcher update must be kept.
8. Interrupted setup/restore recovery on a controlled test unit, if practical.

If you're helping test, please say what the script read back and what you actually
saw or heard on the car. Keep identifiers, APKs, network settings, and raw private
backups out of public reports.
